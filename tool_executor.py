import subprocess
import requests
import json
import os
import shlex
from datetime import datetime
from core_bus import event_bus
import asyncio
from trace_system import trace_emitter
from plugin_security import PLUGIN_ROUTE_INTERNAL_HEADER, plugin_security_manager, redact_sensitive, redact_text

class ToolExecutor:
    def __init__(self, registry, vector_db=None, config_getter=None, session_id="main"):
        self.registry = registry
        self.vector_db = vector_db
        self.config_getter = config_getter or (lambda: {})
        self.session_id = session_id

    def execute(self, tool_call):
        """融合版核心执行引擎：支持原生内置函数 + 外部 VPM 插件"""
        func_name = tool_call.function.name
        
        try:
            # 1. 优雅解析：直接拿原生协议里的 JSON 参数，告别恶心的正则清洗
            args = json.loads(tool_call.function.arguments)
        except json.JSONDecodeError:
            return "[SYSTEM_ERROR]: 大模型生成的参数 JSON 解析失败。"

        span = trace_emitter.start_span("TOOL_EXEC", f"执行工具: {func_name}", {"tool": func_name, "args": redact_sensitive(args)})
        try:
            result = self._execute_impl(func_name, args)
            status = "SUCCESS"
            if str(result).startswith("[SYSTEM_ERROR]") or str(result).startswith("[搜索工具异常]"):
                status = "TIMEOUT" if "超时" in str(result) else "FAILED"
            span.finish(status, f"工具 {func_name} 执行完成", {"result_preview": redact_text(str(result)[:800])})
            return result
        except Exception as e:
            span.finish("FAILED", f"工具 {func_name} 执行失败", {"error": redact_text(str(e))})
            return f"[SYSTEM_ERROR]: 工具 '{func_name}' 执行异常: {redact_text(str(e))}"

    def _execute_impl(self, func_name, args):
        # 通道 A：执行系统内置原生工具 (Built-ins)
        if func_name == "web_search":
            return self.action_web_search(args.get("query", ""))
        elif func_name == "search_local_knowledge":
            return self.action_search_local_knowledge(args.get("query", ""))
        # 新增：UI 控制通道
        elif func_name == "control_ui_layout":
            target = args.get("target_panel")
            component = args.get("target_component", "")
            state = args.get("state")
            print(f"🪄 [UI 魔法] 大模型主动施法：将 {target} 切换至 {state} 模式")
            # 使用事件总线，将这个纯粹的 UI 指令通过 WebSocket 推给前端
            # 必须用 asyncio.run 或创建 task 来执行异步推送
            try:
                asyncio.run(event_bus.publish({
                    "type": "ui_command",
                    "session_id": self.session_id,
                    "target_panel": target,
                    "target_component": component,
                    "state": state
                }))
                print(f"✅ [UI 魔法] 成功通过 WebSocket 下发 {state} 指令！")
            except RuntimeError as e:
                print(f"🚨 [UI 魔法崩溃]: 跨线程下发异常 -> {e}")
            # 告诉大模型：你已经成功改变了现实，继续你的表演
            return f"[SYSTEM_SUCCESS]: 已经成功将前端 {target} 面板切换为 {state} 模式。【系统最高指令】：你的任务已完美完成！前端已响应。现在，请你直接回复并且只能回复这四个字：'已为您开启'。多一个字、多一句话解释、或输出任何链接，都会导致系统崩溃重启！绝对闭嘴！"
            
        # 通道 B：执行外部 VPM 插件生态 (Subprocess / HTTP)
        tool_manifest = next((t for t in self.registry.tools if t.get("function", {}).get("name") == func_name), None)
        
        if not tool_manifest:
            return f"[SYSTEM_ERROR]: 找不到已注册的工具契约 '{func_name}'"

        execution_config = tool_manifest.get("execution")
        if not execution_config:
            return f"[SYSTEM_ERROR]: 外部插件 '{func_name}' 缺少 VPM execution 物理执行配置"

        auth = plugin_security_manager.authorize_tool_call(tool_manifest, args, self.session_id)
        if not auth.get("allowed"):
            return auth.get("message", "[PLUGIN_SECURITY_BLOCKED]: Plugin call was blocked by Vault OS security policy.")

        print(f"\n⚙️  [调度器] 正在拉起外部 Agent: {func_name} ...")
        
        # 模式 B1：本地子进程 (Subprocess)
        if execution_config["type"] == "subprocess":
            command = execution_config["command"]
            for key, value in args.items():
                command = command.replace(f"{{{key}}}", shlex.quote(str(value)))
            
            try:
                result = subprocess.run(command, shell=True, capture_output=True, text=True, cwd=os.getcwd(), timeout=60)
                if result.returncode == 0:
                    return plugin_security_manager.wrap_untrusted_result(tool_manifest, result.stdout.strip())
                else:
                    return f"[SYSTEM_ERROR]: 子进程抛出异常 (Exit Code {result.returncode})。\n错误日志: {redact_text(result.stderr.strip())}"
            except subprocess.TimeoutExpired:
                return f"[SYSTEM_ERROR]: 本地脚本执行超时 (>60秒)，系统已强制将其 kill。"
                
        # 模式 B2：本地微服务或云端 API (HTTP)
        elif execution_config["type"] == "http":
            endpoint = execution_config["endpoint"]
            method = execution_config.get("method", "POST").upper()
            headers = dict(execution_config.get("headers", {}))
            headers.setdefault("X-Vault-Session-Id", self.session_id)
            if endpoint.startswith("/api/plugins/"):
                headers[PLUGIN_ROUTE_INTERNAL_HEADER] = plugin_security_manager.internal_token

            from main import VAULT_ROOT
            try:
                with open(os.path.join(VAULT_ROOT, ".server_port"), "r", encoding="utf-8") as f:
                    actual_port = f.read().strip()
                if endpoint.startswith("/"):
                    endpoint = f"http://127.0.0.1:{actual_port}{endpoint}"
            except Exception:
                # 容错降级
                if endpoint.startswith("/"):
                    endpoint = f"http://127.0.0.1:8000{endpoint}"

            def replace_vars(node):
                if isinstance(node, str):
                    if node == "{args}":
                        return args
                    for k, v in args.items():
                        if f"{{{k}}}" == node:
                            return v
                        node = node.replace(f"{{{k}}}", str(v))
                    return node
                elif isinstance(node, dict):
                    return {k: replace_vars(v) for k, v in node.items()}
                elif isinstance(node, list):
                    return [replace_vars(x) for x in node]
                return node

            payload_format = execution_config.get("payload_format")
            request_data = replace_vars(payload_format) if payload_format else args

            try:
                if method == "POST":
                    resp = requests.post(endpoint, json=request_data, headers=headers, timeout=15)
                else:
                    resp = requests.get(endpoint, params=request_data, headers=headers, timeout=15)
                resp.raise_for_status() 
                return plugin_security_manager.wrap_untrusted_result(tool_manifest, resp.text)
            except requests.exceptions.Timeout:
                return "[SYSTEM_ERROR]: 请求 Agent 超时 (>15秒)。可能原因：对方服务器宕机或网络阻塞。"
            except requests.exceptions.ConnectionError:
                return f"[SYSTEM_ERROR]: 无法连接到外部 Agent ({redact_text(endpoint)})。可能原因：服务未启动或网络不通。"
            except requests.exceptions.HTTPError as err:
                return f"[SYSTEM_ERROR]: 第三方 Agent 拒绝服务。HTTP 状态码: {err.response.status_code}。"
            except Exception as e: # 扩大异常捕获，防止 URL 解析错误导致线程崩溃
                return f"[SYSTEM_ERROR]: 请求外部 Agent 失败 ({redact_text(endpoint)})。错误信息: {redact_text(str(e))}"
        else:
            return f"[SYSTEM_ERROR]: 不支持的执行模式 '{execution_config['type']}'"
        
    # 具体的系统内置工具实现区 (Action)
    def action_search_local_knowledge(self, query):
        """本地知识库检索 (RAG)"""
        print(f"\n📚 [本地检索] 正在激活 'search_local_knowledge' 工具，寻找: '{query}'")
        if not self.vector_db:
            return "[SYSTEM_ERROR]: 本地向量数据库未挂载，无法执行检索。"
        try:
            search_results = self.vector_db.search(query, top_k=3)
            if search_results:
                context_lines = [f"- 【来源: {r['source']} | 匹配度: {r['score']}】\n{r['content']}" for r in search_results]
                return "【本地档案库检索结果】:\n" + "\n\n".join(context_lines)
            else:
                return "本地档案库未检索到与查询相关的内容。"
        except Exception as e:
            return f"[SYSTEM_ERROR]: 本地检索引擎发生异常: {e}"

    # 网络搜索底层拦截器
    def action_web_search(self, query):
        """Resilient DDGS web search with recent-first fallbacks."""
        print(f"\n[网络搜索] 触发工具, 搜索词: '{query}'")
        query = str(query or "").strip()
        if not query:
            return "[搜索工具失败]: 查询词为空。请直接告知 Boss 搜索工具没有收到可执行的查询词。"
        try:
            from ddgs import DDGS
        except Exception as e:
            return f"[搜索工具失败]: 无法加载 ddgs 依赖: {e}。请直接告知 Boss 搜索工具不可用，绝对不要使用训练数据补编最新信息。"

        config = self._web_search_config()
        attempts = self._web_search_attempts(config)
        errors = []
        empty_attempts = []

        for attempt in attempts:
            try:
                raw_results = self._run_ddgs_attempt(DDGS, query, attempt, config)
            except Exception as e:
                errors.append(f"{attempt['label']}: {type(e).__name__}: {e}")
                continue

            if not raw_results:
                empty_attempts.append(attempt["label"])
                continue

            normalized = self._normalize_web_results(raw_results, attempt, config["max_results"])
            if normalized:
                return self._format_web_search_results(query, normalized, attempt)
            empty_attempts.append(f"{attempt['label']}: 无可用字段")

        if len(errors) == len(attempts):
            details = "; ".join(errors[:4])
            if len(errors) > 4:
                details += f"; 另有 {len(errors) - 4} 次失败"
            return f"[搜索工具失败]: 所有 DDGS 搜索通道都失败。失败摘要: {details}。请直接告知 Boss 搜索工具发生故障，绝对不要使用训练数据补编最新信息。"

        searched = "、".join(empty_attempts) if empty_attempts else "全部通道"
        return f"【搜索工具返回结果】：空。已尝试 {searched}，网络上未找到相关信息。警告：请如实告知 Boss 没有搜到最新信息，绝对禁止使用你自己的训练数据进行编造！"

    def _web_search_config(self):
        raw_config = self.config_getter() or {}

        def read_int(key, default, minimum=1):
            try:
                return max(minimum, int(raw_config.get(key, default)))
            except (TypeError, ValueError):
                return default

        return {
            "provider": raw_config.get("web_search_provider", "ddgs"),
            "region": raw_config.get("web_search_region", "wt-wt"),
            "safesearch": raw_config.get("web_search_safesearch", "moderate"),
            "backend": raw_config.get("web_search_backend", "bing,brave,duckduckgo,google"),
            "timeout": read_int("web_search_timeout", 8),
            "max_results": read_int("web_search_max_results", 5),
        }

    def _web_search_attempts(self, config):
        return [
            {"method": "news", "timelimit": "d", "backend": None, "label": "news/daily", "freshness": "最近一天新闻"},
            {"method": "text", "timelimit": "m", "backend": config["backend"], "label": "text/month", "freshness": "最近一个月网页"},
            {"method": "text", "timelimit": "y", "backend": config["backend"], "label": "text/year", "freshness": "最近一年网页"},
            {"method": "text", "timelimit": None, "backend": "auto", "label": "text/auto", "freshness": "未验证时效性"},
        ]

    def _run_ddgs_attempt(self, DDGS, query, attempt, config):
        kwargs = {
            "region": config["region"],
            "safesearch": config["safesearch"],
            "max_results": config["max_results"],
        }
        if attempt["timelimit"]:
            kwargs["timelimit"] = attempt["timelimit"]
        if attempt["backend"]:
            kwargs["backend"] = attempt["backend"]

        try:
            ddgs_context = DDGS(timeout=config["timeout"])
        except TypeError:
            ddgs_context = DDGS()

        with ddgs_context as ddgs:
            search_method = getattr(ddgs, attempt["method"])
            return list(search_method(query, **kwargs))

    def _normalize_web_results(self, raw_results, attempt, max_results):
        normalized = []
        seen = set()
        for res in raw_results or []:
            if not isinstance(res, dict):
                continue
            url = str(res.get("href") or res.get("url") or "").strip()
            title = str(res.get("title") or "").strip()
            body = str(res.get("body") or res.get("snippet") or res.get("description") or "").strip()
            dedupe_key = (url.rstrip("/").lower() if url else f"{title}\n{body}".lower())
            if not dedupe_key or dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            normalized.append({
                "title": title or "无标题",
                "url": url,
                "body": body,
                "date": str(res.get("date") or res.get("published") or "").strip(),
                "source": str(res.get("source") or res.get("publisher") or "").strip(),
                "provider": attempt["label"],
            })
            if len(normalized) >= max_results:
                break
        return normalized

    def _format_web_search_results(self, query, results, attempt):
        searched_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        freshness = attempt["freshness"]
        freshness_note = "（未验证时效性，请勿声称这是最新信息）" if freshness == "未验证时效性" else ""
        lines = [
            "【网络搜索结果】",
            f"query: {query}",
            f"searched_at: {searched_at}",
            f"freshness_window: {freshness}{freshness_note}",
            f"provider: ddgs/{attempt['label']}",
            "",
        ]
        for i, res in enumerate(results, start=1):
            meta = []
            if res["date"]:
                meta.append(f"date={res['date']}")
            if res["source"]:
                meta.append(f"source={res['source']}")
            meta.append(f"provider={res['provider']}")
            lines.extend([
                f"来源{i}: {res['title']}",
                f"URL: {res['url'] or '未提供'}",
                f"metadata: {' | '.join(meta)}",
                f"内容: {res['body'] or '未提供摘要'}",
                "",
            ])
        return "\n".join(lines).strip()
