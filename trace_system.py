import contextvars
import json
import os
import queue
import re
import sqlite3
import threading
import time
import uuid
from typing import Any, Dict, Optional
from plugin_security import redact_text


TRACE_ROOT_TTL_SECONDS = 60
TRACE_SPAN_TTL_SECONDS = 60
TRACE_DETAILS_LIMIT = 4000

TERMINAL_STATUSES = {"SUCCESS", "DEGRADED", "FAILED", "TIMEOUT", "ABORTED", "BLOCKED"}

current_trace_id = contextvars.ContextVar("vault_trace_id", default=None)
current_thread_id = contextvars.ContextVar("vault_thread_id", default=None)
current_span_id = contextvars.ContextVar("vault_span_id", default=None)


def now_ms() -> int:
    return int(time.time() * 1000)


class TraceEmitter:
    def __init__(self):
        self.vault_root: Optional[str] = None
        self.db_path: Optional[str] = None
        self.event_bus = None
        self.main_loop = None
        self.run_token = ""
        self._queue: "queue.Queue[Dict[str, Any]]" = queue.Queue()
        self._writer_started = False
        self._watchdog_started = False
        self._active_lock = threading.Lock()
        self._active_spans: Dict[tuple, Dict[str, Any]] = {}
        self._active_runs: Dict[str, Dict[str, Any]] = {}

    def configure(self, vault_root: str, event_bus=None, run_token: str = ""):
        self.vault_root = vault_root
        self.event_bus = event_bus or self.event_bus
        self.run_token = run_token or self.run_token
        self.db_path = os.path.join(vault_root, "vault_trace.db")
        os.makedirs(vault_root, exist_ok=True)
        self._init_db()
        self._start_writer()
        self._start_watchdog()

    def bind_runtime(self, main_loop=None, event_bus=None):
        if main_loop is not None:
            self.main_loop = main_loop
        if event_bus is not None:
            self.event_bus = event_bus

    def _connect(self):
        if not self.db_path:
            raise RuntimeError("TraceEmitter is not configured.")
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._connect() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS trace_runs (
                    trace_id TEXT PRIMARY KEY,
                    thread_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    started_at INTEGER NOT NULL,
                    finished_at INTEGER,
                    root_span_id TEXT,
                    error_message TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS trace_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trace_id TEXT NOT NULL,
                    thread_id TEXT NOT NULL,
                    span_id TEXT NOT NULL,
                    parent_span_id TEXT,
                    step_code TEXT NOT NULL,
                    status TEXT NOT NULL,
                    message TEXT,
                    metrics_json TEXT,
                    details_json TEXT,
                    created_at INTEGER NOT NULL,
                    duration_ms INTEGER
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_trace_events_trace ON trace_events(trace_id, id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_trace_runs_thread ON trace_runs(thread_id, started_at)")
            conn.commit()

    def _start_writer(self):
        if self._writer_started:
            return
        self._writer_started = True
        thread = threading.Thread(target=self._writer_loop, name="vault-trace-writer", daemon=True)
        thread.start()

    def _start_watchdog(self):
        if self._watchdog_started:
            return
        self._watchdog_started = True
        thread = threading.Thread(target=self._watchdog_loop, name="vault-trace-watchdog", daemon=True)
        thread.start()

    def _writer_loop(self):
        while True:
            item = self._queue.get()
            try:
                self._write_item(item)
            except Exception as e:
                print(f" [Trace] 写入失败: {e}")
            finally:
                self._queue.task_done()

    def _write_item(self, item: Dict[str, Any]):
        if not self.db_path:
            return
        kind = item.get("kind")
        with self._connect() as conn:
            if kind == "run_start":
                conn.execute(
                    """
                    INSERT OR REPLACE INTO trace_runs
                    (trace_id, thread_id, status, started_at, finished_at, root_span_id, error_message)
                    VALUES (?, ?, ?, ?, NULL, ?, NULL)
                    """,
                    (item["trace_id"], item["thread_id"], "RUNNING", item["started_at"], item["root_span_id"]),
                )
            elif kind == "run_finish":
                conn.execute(
                    """
                    UPDATE trace_runs
                    SET status = ?, finished_at = ?, error_message = ?
                    WHERE trace_id = ?
                    """,
                    (item["status"], item["finished_at"], item.get("error_message"), item["trace_id"]),
                )
            elif kind == "event":
                conn.execute(
                    """
                    INSERT INTO trace_events
                    (trace_id, thread_id, span_id, parent_span_id, step_code, status, message,
                     metrics_json, details_json, created_at, duration_ms)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        item["trace_id"],
                        item["thread_id"],
                        item["span_id"],
                        item.get("parent_span_id"),
                        item["step_code"],
                        item["status"],
                        item.get("message", ""),
                        json.dumps(item.get("metrics") or {}, ensure_ascii=False),
                        json.dumps(item.get("details") or {}, ensure_ascii=False),
                        item["timestamp"],
                        item.get("duration_ms"),
                    ),
                )
            conn.commit()

    def _mask_text(self, text: str) -> str:
        masked = redact_text(text)
        if self.run_token:
            masked = masked.replace(self.run_token, "******")
        for path in (self.vault_root, os.path.expanduser("~")):
            if path:
                masked = masked.replace(path, "~")
                masked = masked.replace(path.replace("\\", "/"), "~")
        if self.vault_root:
            project_root = os.path.dirname(self.vault_root)
            masked = masked.replace(project_root, "~")
            masked = masked.replace(project_root.replace("\\", "/"), "~")
        return masked

    def _mask_payload(self, value: Any) -> Any:
        if isinstance(value, str):
            return self._mask_text(value)
        if isinstance(value, dict):
            return {str(k): self._mask_payload(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self._mask_payload(v) for v in value[:50]]
        return value

    def _bounded_json_payload(self, value: Any) -> Any:
        masked = self._mask_payload(value or {})
        encoded = json.dumps(masked, ensure_ascii=False, default=str)
        if len(encoded) <= TRACE_DETAILS_LIMIT:
            return masked
        return {"truncated": True, "preview": encoded[:TRACE_DETAILS_LIMIT]}

    def _publish_trace_event(self, event: Dict[str, Any]):
        if not self.event_bus or not self.main_loop:
            return
        message = {
            "type": "trace_event",
            "trace_id": event["trace_id"],
            "thread_id": event["thread_id"],
            "span_id": event["span_id"],
            "parent_span_id": event.get("parent_span_id"),
            "step_code": event["step_code"],
            "status": event["status"],
            "message": event.get("message", ""),
            "metrics": event.get("metrics") or {},
            "details": event.get("details") or {},
            "timestamp": event["timestamp"],
            "duration_ms": event.get("duration_ms"),
        }
        try:
            self.event_bus.publish_sync(self.main_loop, message)
        except Exception:
            pass

    def start_trace(self, thread_id: str, message: str = ""):
        trace_id = f"tr_{uuid.uuid4().hex[:16]}"
        root_span_id = f"sp_{uuid.uuid4().hex[:12]}"
        started_at = now_ms()
        self._queue.put({
            "kind": "run_start",
            "trace_id": trace_id,
            "thread_id": thread_id,
            "root_span_id": root_span_id,
            "started_at": started_at,
        })
        with self._active_lock:
            self._active_runs[trace_id] = {
                "thread_id": thread_id,
                "root_span_id": root_span_id,
                "started_at": started_at,
                "status": "RUNNING",
                "background_pending": 0,
                "response_done": False,
                "response_status": "SUCCESS",
                "response_error": "",
                "has_degraded": False,
            }
        tokens = bind_trace_context(trace_id, thread_id, root_span_id)
        self.emit_event(
            step_code="ROOT",
            status="RUNNING",
            message="智能体任务已启动",
            span_id=root_span_id,
            parent_span_id=None,
            details={"input": message},
        )
        return trace_id, root_span_id, tokens

    def begin_background_task(self, trace_id: Optional[str] = None):
        trace_id = trace_id or current_trace_id.get()
        if not trace_id:
            return
        with self._active_lock:
            run = self._active_runs.get(trace_id)
            if run and run.get("status") not in TERMINAL_STATUSES:
                run["background_pending"] = int(run.get("background_pending", 0) or 0) + 1

    def finish_background_task(self, trace_id: Optional[str] = None):
        trace_id = trace_id or current_trace_id.get()
        if not trace_id:
            return
        should_finish = False
        tokens = None
        with self._active_lock:
            run = self._active_runs.get(trace_id)
            if not run or run.get("status") in TERMINAL_STATUSES:
                return
            run["background_pending"] = max(0, int(run.get("background_pending", 0) or 0) - 1)
            should_finish = bool(run.get("response_done")) and run["background_pending"] == 0
            if should_finish:
                tokens = bind_trace_context(trace_id, run.get("thread_id"), run.get("root_span_id"))
        if should_finish and tokens:
            try:
                self.finish_trace(
                    self._final_status_for_trace(trace_id),
                    "任务与后台流程已完成",
                    self._final_error_for_trace(trace_id),
                )
            finally:
                reset_trace_context(tokens)

    def mark_response_done(self, status: str = "SUCCESS", message: str = "", error_message: str = ""):
        trace_id = current_trace_id.get()
        thread_id = current_thread_id.get()
        if not trace_id or not thread_id:
            return
        self.emit_event(
            "RESPONSE_DONE",
            status,
            message or ("主回复已完成" if status == "SUCCESS" else "主回复失败"),
            details={"status": status},
        )
        should_finish = False
        with self._active_lock:
            run = self._active_runs.get(trace_id)
            if not run or run.get("status") in TERMINAL_STATUSES:
                return
            run["response_done"] = True
            run["response_status"] = status
            run["response_error"] = self._mask_text(error_message or "")
            should_finish = int(run.get("background_pending", 0) or 0) == 0
        if should_finish:
            self.finish_trace(
                self._final_status_for_trace(trace_id),
                "任务与后台流程已完成",
                self._final_error_for_trace(trace_id),
            )

    def _final_status_for_trace(self, trace_id: str) -> str:
        with self._active_lock:
            run = self._active_runs.get(trace_id) or {}
            response_status = run.get("response_status") or "SUCCESS"
            if response_status == "SUCCESS" and run.get("has_degraded"):
                return "DEGRADED"
            return response_status

    def _final_error_for_trace(self, trace_id: str) -> str:
        with self._active_lock:
            run = self._active_runs.get(trace_id) or {}
            return run.get("response_error") or ""

    def finish_trace(self, status: str = "SUCCESS", message: str = "", error_message: str = ""):
        trace_id = current_trace_id.get()
        thread_id = current_thread_id.get()
        root_span_id = None
        if trace_id:
            with self._active_lock:
                run = self._active_runs.get(trace_id)
                if run and run.get("status") in TERMINAL_STATUSES:
                    return
                root_span_id = run.get("root_span_id") if run else current_span_id.get()
        if not trace_id or not thread_id or not root_span_id:
            return
        self.emit_event(
            step_code="ROOT",
            status=status,
            message=message or ("任务完成" if status == "SUCCESS" else "任务已中止"),
            span_id=root_span_id,
            parent_span_id=None,
            details={"error": error_message} if error_message else {},
        )
        finished_at = now_ms()
        self._queue.put({
            "kind": "run_finish",
            "trace_id": trace_id,
            "status": status,
            "finished_at": finished_at,
            "error_message": self._mask_text(error_message or ""),
        })
        with self._active_lock:
            run = self._active_runs.get(trace_id)
            if run:
                run["status"] = status
                run["finished_at"] = finished_at
            for key in [key for key in self._active_spans if key[0] == trace_id]:
                self._active_spans.pop(key, None)

    def emit_event(
        self,
        step_code: str,
        status: str,
        message: str = "",
        span_id: Optional[str] = None,
        parent_span_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        metrics: Optional[Dict[str, Any]] = None,
        duration_ms: Optional[int] = None,
    ):
        trace_id = current_trace_id.get()
        thread_id = current_thread_id.get()
        if not trace_id or not thread_id:
            return
        with self._active_lock:
            run = self._active_runs.get(trace_id)
            if run and run.get("status") in TERMINAL_STATUSES:
                return
        span_id = span_id or f"sp_{uuid.uuid4().hex[:12]}"
        if parent_span_id is None and step_code != "ROOT":
            parent_span_id = current_span_id.get()
        event = {
            "kind": "event",
            "trace_id": trace_id,
            "thread_id": thread_id,
            "span_id": span_id,
            "parent_span_id": parent_span_id,
            "step_code": step_code,
            "status": status,
            "message": self._mask_text(message or ""),
            "details": self._bounded_json_payload(details),
            "metrics": self._bounded_json_payload(metrics),
            "timestamp": now_ms(),
            "duration_ms": duration_ms,
        }
        with self._active_lock:
            key = (trace_id, span_id)
            if status == "DEGRADED" and run:
                run["has_degraded"] = True
            if status == "RUNNING":
                self._active_spans[key] = {
                    "thread_id": thread_id,
                    "span_id": span_id,
                    "parent_span_id": parent_span_id,
                    "step_code": step_code,
                    "started_at": event["timestamp"],
                }
            elif status in TERMINAL_STATUSES:
                self._active_spans.pop(key, None)
        self._queue.put(event)
        self._publish_trace_event(event)

    def start_span(self, step_code: str, message: str = "", details: Optional[Dict[str, Any]] = None):
        trace_id = current_trace_id.get()
        thread_id = current_thread_id.get()
        parent_span_id = current_span_id.get()
        if not trace_id or not thread_id:
            return NullTraceSpan()
        span_id = f"sp_{uuid.uuid4().hex[:12]}"
        self.emit_event(step_code, "RUNNING", message, span_id=span_id, parent_span_id=parent_span_id, details=details)
        return ActiveTraceSpan(self, step_code, span_id, parent_span_id, message)

    def timeout_trace(self, error_message: str):
        self._timeout_current_trace(error_message)

    def _timeout_current_trace(self, error_message: str):
        trace_id = current_trace_id.get()
        thread_id = current_thread_id.get()
        if not trace_id or not thread_id:
            return
        self._abort_running_spans(trace_id, "任务超过硬熔断时间，已中止等待。")
        self.finish_trace("TIMEOUT", "任务执行超时，已启动硬熔断。", error_message)

    def _abort_running_spans(self, trace_id: str, message: str):
        with self._active_lock:
            items = [span.copy() for key, span in self._active_spans.items() if key[0] == trace_id]
        for span in items:
            if span.get("step_code") == "ROOT":
                continue
            tokens = bind_trace_context(trace_id, span["thread_id"], span["parent_span_id"])
            try:
                self.emit_event(
                    span["step_code"],
                    "ABORTED",
                    message,
                    span_id=span["span_id"],
                    parent_span_id=span["parent_span_id"],
                    duration_ms=now_ms() - span["started_at"],
                )
            finally:
                reset_trace_context(tokens)

    def _watchdog_loop(self):
        while True:
            time.sleep(5)
            cutoff = now_ms() - TRACE_SPAN_TTL_SECONDS * 1000
            expired = []
            with self._active_lock:
                for key, span in self._active_spans.items():
                    if span.get("started_at", now_ms()) < cutoff:
                        expired.append((key, span.copy()))
            for (trace_id, _), span in expired:
                tokens = bind_trace_context(trace_id, span["thread_id"], span["parent_span_id"])
                try:
                    if span["step_code"] == "ROOT":
                        self._abort_running_spans(trace_id, "根任务超时，子任务已中止等待。")
                        self.finish_trace("TIMEOUT", "任务执行超时，已启动硬熔断。", "Trace watchdog timeout")
                    else:
                        self.emit_event(
                            span["step_code"],
                            "TIMEOUT",
                            "Span 超过硬熔断时间，已自动标记超时。",
                            span_id=span["span_id"],
                            parent_span_id=span["parent_span_id"],
                            duration_ms=now_ms() - span["started_at"],
                        )
                finally:
                    reset_trace_context(tokens)

    def flush(self, timeout: float = 0.5):
        deadline = time.time() + timeout
        while self._queue.unfinished_tasks and time.time() < deadline:
            time.sleep(0.01)

    def get_snapshot(self, trace_id: str) -> Optional[Dict[str, Any]]:
        self.flush()
        with self._connect() as conn:
            run_row = conn.execute("SELECT * FROM trace_runs WHERE trace_id = ?", (trace_id,)).fetchone()
            if not run_row:
                return None
            rows = conn.execute(
                "SELECT * FROM trace_events WHERE trace_id = ? ORDER BY id ASC",
                (trace_id,),
            ).fetchall()
        return self._snapshot_from_rows(run_row, rows)

    def get_latest_snapshot(self, thread_id: str) -> Optional[Dict[str, Any]]:
        self.flush()
        with self._connect() as conn:
            run_row = conn.execute(
                "SELECT * FROM trace_runs WHERE thread_id = ? ORDER BY started_at DESC LIMIT 1",
                (thread_id,),
            ).fetchone()
            if not run_row:
                return None
            rows = conn.execute(
                "SELECT * FROM trace_events WHERE trace_id = ? ORDER BY id ASC",
                (run_row["trace_id"],),
            ).fetchall()
        return self._snapshot_from_rows(run_row, rows)

    def _snapshot_from_rows(self, run_row, event_rows):
        events = []
        for row in event_rows:
            events.append({
                "id": row["id"],
                "trace_id": row["trace_id"],
                "thread_id": row["thread_id"],
                "span_id": row["span_id"],
                "parent_span_id": row["parent_span_id"],
                "step_code": row["step_code"],
                "status": row["status"],
                "message": row["message"],
                "metrics": json.loads(row["metrics_json"] or "{}"),
                "details": json.loads(row["details_json"] or "{}"),
                "timestamp": row["created_at"],
                "duration_ms": row["duration_ms"],
            })
        return {
            "run": {
                "trace_id": run_row["trace_id"],
                "thread_id": run_row["thread_id"],
                "status": run_row["status"],
                "started_at": run_row["started_at"],
                "finished_at": run_row["finished_at"],
                "root_span_id": run_row["root_span_id"],
                "error_message": run_row["error_message"],
            },
            "events": events,
            "tree": build_trace_tree(events),
        }


class ActiveTraceSpan:
    def __init__(self, emitter: TraceEmitter, step_code: str, span_id: str, parent_span_id: str, message: str):
        self.emitter = emitter
        self.step_code = step_code
        self.span_id = span_id
        self.parent_span_id = parent_span_id
        self.message = message
        self.started_at = now_ms()
        self._finished = False
        self._tokens = None

    def __enter__(self):
        self._tokens = bind_trace_context(current_trace_id.get(), current_thread_id.get(), self.span_id)
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc is not None:
            self.finish("FAILED", f"{self.message}失败", {"error": str(exc)})
            return False
        self.finish("SUCCESS", f"{self.message}完成")
        return False

    def finish(self, status: str = "SUCCESS", message: str = "", details: Optional[Dict[str, Any]] = None, metrics: Optional[Dict[str, Any]] = None):
        if self._finished:
            return
        self._finished = True
        self.emitter.emit_event(
            self.step_code,
            status,
            message or self.message,
            span_id=self.span_id,
            parent_span_id=self.parent_span_id,
            details=details,
            metrics=metrics,
            duration_ms=now_ms() - self.started_at,
        )
        if self._tokens:
            reset_trace_context(self._tokens)
            self._tokens = None


class NullTraceSpan:
    span_id = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def finish(self, *args, **kwargs):
        return None


def bind_trace_context(trace_id: Optional[str], thread_id: Optional[str], span_id: Optional[str]):
    return (
        current_trace_id.set(trace_id),
        current_thread_id.set(thread_id),
        current_span_id.set(span_id),
    )


def reset_trace_context(tokens):
    trace_token, thread_token, span_token = tokens
    current_span_id.reset(span_token)
    current_thread_id.reset(thread_token)
    current_trace_id.reset(trace_token)


def copy_current_context():
    return contextvars.copy_context()


def traced_span(step_code: str, message: str = "", details: Optional[Dict[str, Any]] = None):
    return trace_emitter.start_span(step_code, message, details)


def build_trace_tree(events):
    latest = {}
    order = []
    for event in events:
        span_id = event["span_id"]
        if span_id not in latest:
            order.append(span_id)
        latest[span_id] = event.copy()
        latest[span_id]["children"] = []
    roots = []
    for span_id in order:
        node = latest[span_id]
        parent_id = node.get("parent_span_id")
        if parent_id and parent_id in latest:
            latest[parent_id]["children"].append(node)
        else:
            roots.append(node)
    return roots


trace_emitter = TraceEmitter()
