import os
import sys
import json
import socket
import uvicorn
import secrets
import asyncio
import importlib.util
import shutil
import time
import uuid

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from main import VaultOS_Terminal, TempVaultSession, VAULT_ROOT
from sqlmodel import Session, select
from db import engine, init_db
from fastapi.staticfiles import StaticFiles
from core_bus import bind_event_session, event_bus, reset_event_session
from agent_runner import spawn_agent_task, spawn_temp_agent_task
from trace_system import trace_emitter
from plugin_security import (
    PLUGIN_ROUTE_INTERNAL_HEADER,
    PLUGIN_UI_TOKEN_HEADER,
    normalize_manifest_security,
    plugin_security_manager,
)

app = FastAPI()
# 跨域资源共享 (CORS) 放行配置
# 允许前端 (localhost:1420) 通过 HTTP 拉取插件源码
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=False,
    allow_methods=["*"], 
    allow_headers=["*"], 
)

@app.middleware("http")
async def bind_plugin_session_context(request: Request, call_next):
    session_id = "main"
    if request.url.path.startswith("/api/plugins/"):
        parts = request.url.path.split("/")
        plugin_id = parts[3] if len(parts) > 3 else ""
        if plugin_id and not plugin_security_manager.is_first_party(plugin_id):
            internal_token = request.headers.get(PLUGIN_ROUTE_INTERNAL_HEADER, "")
            ui_token = request.headers.get(PLUGIN_UI_TOKEN_HEADER, "")
            if not (
                plugin_security_manager.verify_internal_token(internal_token)
                or plugin_security_manager.verify_plugin_ui_token(plugin_id, ui_token)
            ):
                raise HTTPException(status_code=401, detail="Plugin route requires scoped authorization")
        session_id = request.headers.get("X-Vault-Session-Id", "main") or "main"
    token = bind_event_session(session_id)
    try:
        return await call_next(request)
    finally:
        reset_event_session(token)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PLUGINS_DIR = os.path.join(VAULT_ROOT, "plugins")
os.makedirs(PLUGINS_DIR, exist_ok=True)

@app.get("/plugins/{plugin_id}/ui/{file_name}")
async def serve_plugin_ui(plugin_id: str, file_name: str):
    safe_plugin = os.path.basename(plugin_id)
    safe_file = os.path.basename(file_name)
    file_path = os.path.join(PLUGINS_DIR, safe_plugin, "ui", safe_file)
    
    if os.path.exists(file_path):
        return FileResponse(file_path)
    else:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="文件不存在")
    
def get_free_port(start_port=8000):
    for port in range(start_port, 9000):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            # 如果 connect_ex 返回非 0，说明这个端口是空闲的
            if s.connect_ex(('127.0.0.1', port)) != 0:
                return port
    raise RuntimeError(" 无法找到可用的本地端口！")

#  分配端口并写下“双重信物”
SERVER_PORT = get_free_port()
SECURITY_TOKEN = secrets.token_hex(16)

os.makedirs(VAULT_ROOT, exist_ok=True)
with open(os.path.join(VAULT_ROOT, ".run_token"), "w", encoding="utf-8") as f:
    f.write(SECURITY_TOKEN)
with open(os.path.join(VAULT_ROOT, ".server_port"), "w", encoding="utf-8") as f:
    f.write(str(SERVER_PORT))

trace_emitter.configure(VAULT_ROOT, event_bus=event_bus, run_token=SECURITY_TOKEN)
plugin_security_manager.configure(VAULT_ROOT, event_bus=event_bus, internal_token=SECURITY_TOKEN)

print("="*60)
print(f" [网关启动] Vault OS 后台服务已启动。")
print(f" [端口选择] 当前可用端口: {SERVER_PORT}")
print(f" [安全系统] 本次运行专属 Token: {SECURITY_TOKEN}")
print("="*60)

print(" 正在初始化大模型客户端和向量引擎...")
vault_os = VaultOS_Terminal()


def memory_data_payload():
    items = vault_os.gatekeeper.fetch_memory()
    return {
        "type": "memory_data",
        "content": items,
        "meta": vault_os.gatekeeper.get_memory_sync_status(),
    }


class SessionManager:
    def __init__(self, main_app):
        self.main_app = main_app
        self.temp_sessions = {}
        self.lock = asyncio.Lock()

    async def create_temp_session(self):
        session_id = f"temp:{uuid.uuid4().hex[:12]}"
        async with self.lock:
            self.temp_sessions[session_id] = {
                "runtime": TempVaultSession(self.main_app, session_id),
                "closed": False,
            }
        return session_id

    async def end_temp_session(self, session_id):
        async with self.lock:
            session = self.temp_sessions.get(session_id)
            if session:
                session["closed"] = True
                self.temp_sessions.pop(session_id, None)
        return True

    def get_temp_runtime(self, session_id):
        session = self.temp_sessions.get(session_id)
        if not session or session.get("closed"):
            return None
        return session.get("runtime")

    def is_temp_open(self, session_id):
        session = self.temp_sessions.get(session_id)
        return bool(session and not session.get("closed"))


session_manager = SessionManager(vault_os)

@app.get("/api/traces/{trace_id}/snapshot")
async def get_trace_snapshot(trace_id: str):
    snapshot = trace_emitter.get_snapshot(trace_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail="trace 不存在")
    return snapshot

@app.get("/api/traces/thread/{thread_id}/latest")
async def get_latest_thread_trace(thread_id: str):
    snapshot = trace_emitter.get_latest_snapshot(thread_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail="trace 不存在")
    return snapshot

@app.post("/api/rag/ingest")
async def api_rag_ingest(request: Request):
    try:
        payload_data = await request.json()
        auth_header = request.headers.get("Authorization")
        if auth_header != f"Bearer {SECURITY_TOKEN}":
            return {"status": "error", "message": "未授权的访问拒绝进入 RAG 存储区"}  
        # 核心边界：路径沙盒验证 (Path Sandbox)
        source_file = payload_data.get("source_file", "")
        # 1. 防御路径穿越攻击 (防范诸如 ../knowledge/xxx.md 的恶意路径)
        safe_source = os.path.normpath(source_file)
        if ".." in safe_source:
            print(f" [安全拦截] 检测到恶意路径穿越攻击: {source_file}")
            return {"status": "error", "message": "非法路径！系统已拦截。"} 
        # 2. 权限隔离：外来 HTTP 请求只能操作 plugins 目录下的文件。
        allowed_prefix = os.path.normpath(PLUGINS_DIR)
        if not safe_source.startswith(allowed_prefix):
            print(f" [权限拦截] 第三方 Agent 请求访问非插件目录: {safe_source}")
            return {"status": "error", "message": "权限不足：第三方插件仅允许操作自己的沙盒数据。"}
        rel_source = os.path.relpath(safe_source, allowed_prefix)
        source_parts = rel_source.split(os.sep)
        source_plugin_id = source_parts[0] if source_parts and source_parts[0] != "." else ""
        for chunk in payload_data.get("payload", []) or []:
            metadata = chunk.get("metadata", {}) if isinstance(chunk, dict) else {}
            metadata_plugin_id = metadata.get("plugin_id")
            if metadata_plugin_id and metadata_plugin_id != source_plugin_id:
                return {"status": "error", "message": "RAG metadata.plugin_id must match the plugin source path"}
            if source_plugin_id and not metadata_plugin_id:
                metadata["plugin_id"] = source_plugin_id
                chunk["metadata"] = metadata
            
        success = await asyncio.to_thread(vault_os.receive_knowledge_payload, payload_data)
        return {"status": "success"} if success else {"status": "error"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/plugins/{plugin_id}/rag/search")
async def api_plugin_rag_search(plugin_id: str, request: Request):
    safe_plugin = os.path.basename(plugin_id)
    if not safe_plugin:
        raise HTTPException(status_code=400, detail="plugin_id required")
    payload = await request.json()
    query = str(payload.get("query") or "").strip()
    if not query:
        return {"status": "success", "plugin_id": safe_plugin, "results": []}
    try:
        top_k = max(1, min(int(payload.get("top_k", 5)), 20))
    except (TypeError, ValueError):
        top_k = 5
    domain = str(payload.get("domain") or "").strip()
    plugin_root = os.path.normcase(os.path.normpath(os.path.join(PLUGINS_DIR, safe_plugin)))

    def belongs_to_plugin(item):
        metadata = item.get("metadata") or {}
        source = os.path.normcase(os.path.normpath(item.get("source") or metadata.get("source") or ""))
        metadata_plugin_id = metadata.get("plugin_id")
        if metadata_plugin_id and metadata_plugin_id != safe_plugin:
            return False
        if domain and metadata.get("domain") != domain:
            return False
        return bool(source and source.startswith(plugin_root))

    try:
        try:
            raw_results = await asyncio.to_thread(
                vault_os.vector_db.search,
                query,
                max(top_k * 4, 20),
                {"plugin_id": safe_plugin},
            )
        except Exception as filter_error:
            print(f" [RAG] 插件私有过滤查询降级: {filter_error}")
            raw_results = []
        results = [item for item in raw_results if belongs_to_plugin(item)]
        if not results:
            raw_results = await asyncio.to_thread(vault_os.vector_db.search, query, max(top_k * 4, 20))
            results = [item for item in raw_results if belongs_to_plugin(item)]
        safe_results = []
        for item in results[:top_k]:
            metadata = item.get("metadata") or {}
            safe_results.append({
                "score": item.get("score", 0),
                "content": item.get("content", ""),
                "source": item.get("source", ""),
                "metadata": {
                    "plugin_id": metadata.get("plugin_id"),
                    "domain": metadata.get("domain"),
                    "source_type": metadata.get("source_type"),
                    "artist": metadata.get("artist"),
                    "url": metadata.get("url"),
                },
            })
        return {"status": "success", "plugin_id": safe_plugin, "results": safe_results}
    except Exception as e:
        return {"status": "error", "plugin_id": safe_plugin, "message": str(e)}

@app.websocket("/ws/{client_token}")
async def websocket_endpoint(websocket: WebSocket, client_token: str):
    if client_token != SECURITY_TOKEN:
        await websocket.close(code=1008, reason="Unauthorized")
        return
        
    await websocket.accept()
    real_loop = asyncio.get_running_loop()
    plugin_security_manager.bind_runtime(main_loop=real_loop, event_bus=event_bus)

    # 1. 启动 Event Bus 监听协程：让后台任务能够把结果推给前端
    async def consume_events():
        async for event in event_bus.subscribe():
            await websocket.send_json(event)
    consumer_task = asyncio.create_task(consume_events())

    print(" [连接成功] WebSocket 已连接，正在同步初始状态...")
    
    # 2. 连接刚建立时，立刻下发一次初始数据
    if hasattr(vault_os, 'threads') and vault_os.threads:
        await websocket.send_json({"type": "history_all", "content": vault_os.threads})

    # 3. 核心大循环：唯一的数据分发口
    try:
        while True:
            raw_data = await websocket.receive_text()
            request = json.loads(raw_data) 
            cmd_type = request.get("type")
            thread_id = request.get("thread_id", "global")
            session_mode = request.get("session_mode", "main")
            session_id = request.get("session_id", "main")

            if cmd_type == "start_temp_session":
                new_session_id = await session_manager.create_temp_session()
                await websocket.send_json({"type": "temp_session_started", "session_id": new_session_id})
                continue

            if cmd_type == "plugin_permission_response":
                plugin_security_manager.resolve_permission(
                    request.get("request_id", ""),
                    request.get("decision", "deny")
                )
                continue

            if cmd_type == "end_temp_session":
                await session_manager.end_temp_session(session_id)
                await websocket.send_json({"type": "temp_session_ended", "session_id": session_id})
                continue

            if session_mode == "temp" and cmd_type in {
                "fetch_memory",
                "resolve_memory_conflict",
                "memory_surgery",
                "import_profile",
                "fetch_profile_import_state",
                "prepare_profile_import",
                "commit_profile_import",
                "cancel_profile_import",
                "save_config",
                "delete_note",
                "uninstall_plugin",
            }:
                await websocket.send_json({
                    "type": "system_toast",
                    "session_id": session_id,
                    "content": "临时会话处于无记忆隔离模式，此操作不可用。"
                })
                continue

            # === [通道 A：轻量级 UI 数据同步] ===
            if cmd_type == "fetch_news":
                local_news = vault_os.get_local_news_list()
                await websocket.send_json({"type": "news_list", "content": local_news}) 
                
            elif cmd_type == "fetch_favorites":
                local_favorites = vault_os.get_favorite_list()
                await websocket.send_json({"type": "favorites_list", "content": local_favorites})   
                
            elif cmd_type == "fetch_note_detail":
                path = request.get("path")
                content = vault_os.get_note_content(path)
                await websocket.send_json({"type": "note_content", "content": content})
                
            elif cmd_type == "delete_note":
                success = vault_os.delete_note(request.get("path"), request.get("id"))
                if success:
                    await websocket.send_json({"type": "delete_success", "id": request.get("id")})
                    
            elif cmd_type == "get_config":
                await websocket.send_json({"type": "config_data", "content": vault_os.llm_config})
                
            elif cmd_type == "save_config":
                result = await asyncio.to_thread(vault_os.save_config, request.get("content"))
                await websocket.send_json({"type": "config_save_result", "content": result})
                
            elif cmd_type == "fetch_memory":
                try:
                    await websocket.send_json(memory_data_payload())
                except Exception:
                    await websocket.send_json({"type": "memory_data", "content": [], "meta": {}})
                await websocket.send_json({"type": "profile_import_state", "content": vault_os.get_profile_import_state()})
            elif cmd_type == "resolve_memory_conflict":
                result = await asyncio.to_thread(
                    vault_os.resolve_memory_conflict,
                    request.get("id"),
                    request.get("decision")
                )
                await event_bus.publish({"type": "system_toast", "content": result.get("message", "")})
                await event_bus.publish({"type": "SYSTEM_STATE_CHANGED", "memory_pending_count": len([m for m in vault_os.gatekeeper.fetch_memory() if m.get("status") == "PENDING"])})
                await event_bus.publish({"type": "profile_import_state", "content": vault_os.get_profile_import_state()})
                try:
                    await event_bus.publish(memory_data_payload())
                except Exception:
                    await event_bus.publish({"type": "memory_data", "content": [], "meta": {}})
            # VPM 插件列表刷新指令
            elif cmd_type == "fetch_plugins":
                plugins_info = []
                if os.path.exists(PLUGINS_DIR):
                    for p in os.listdir(PLUGINS_DIR):
                        p_path = os.path.join(PLUGINS_DIR, p)
                        manifest_file = os.path.join(p_path, "manifest.json")
                        # 只有包含 manifest.json 的才算作合规插件
                        if os.path.isdir(p_path) and os.path.exists(manifest_file):
                            try:
                                with open(manifest_file, 'r', encoding='utf-8') as mf:
                                    info = json.load(mf)
                                    declared_plugin_id = info.get("plugin_id")
                                    if declared_plugin_id and declared_plugin_id != p:
                                        print(f" [VPM] 插件 {p} 的 plugin_id 与目录名不一致，已跳过。")
                                        continue
                                    info['plugin_id'] = p # 将插件目录名作为唯一 ID
                                    normalize_manifest_security(info, p)
                                    info['plugin_ui_token'] = plugin_security_manager.plugin_ui_token(p)
                                    plugins_info.append(info)
                            except Exception as e:
                                print(f" [VPM] 解析插件 {p} 契约失败: {e}")
                                
                await websocket.send_json({"type": "plugins_list", "content": plugins_info})
            # VPM 插件卸载指令
            elif cmd_type == "uninstall_plugin":
                plugin_id = request.get("plugin_id")
                safe_id = os.path.basename(plugin_id) 
                plugin_path = os.path.join(PLUGINS_DIR, safe_id)
                api_file = os.path.join(plugin_path, "api.py")
                
                if os.path.exists(plugin_path):
                    try:
                        # 0. 卸载前由主系统清理该插件的向量记录。
                        # 不经过 HTTP API，直接调用主系统的内存函数。
                        knowledge_dir = os.path.join(plugin_path, "knowledge")
                        if os.path.exists(knowledge_dir):
                            for md_file in os.listdir(knowledge_dir):
                                if md_file.endswith(".md"):
                                    filepath = os.path.join(knowledge_dir, md_file)
                                    purge_payload = {
                                        "command": "RAG_UPSERT",
                                        "source_file": filepath,
                                        "hash": "uninstall_purge",
                                        "payload": [] # 空载荷触发删除该来源的向量记录
                                    }
                                    vault_os.receive_knowledge_payload(purge_payload)
                            print(f" [VPM 卸载] 插件 [{safe_id}] 的关联向量记录已清理。")

                        # 1. 尝试调用插件专属的卸载钩子 (Lifecycle Hook)
                        if os.path.exists(api_file):
                            import importlib.util
                            spec = importlib.util.spec_from_file_location(f"vpm.temp.{safe_id}", api_file)
                            plugin_module = importlib.util.module_from_spec(spec)
                            spec.loader.exec_module(plugin_module)
                            
                            if hasattr(plugin_module, "uninstall_hook"):
                                plugin_module.uninstall_hook(engine)
                        
                        # 2. 删除插件目录。
                        shutil.rmtree(plugin_path) 
                        
                        await websocket.send_json({"type": "plugin_uninstalled_success", "plugin_id": safe_id})
                        await websocket.send_json({"type": "system_toast", "content": f" 插件 [{safe_id}] 已卸载。"})
                    except Exception as e:
                        await websocket.send_json({"type": "system_toast", "content": f" 卸载失败: {e}"})
            # === [通道 B：中等耗时的后台 IO 任务] ===
            elif cmd_type == "memory_surgery":
                # 交给线程池处理，避免卡死当前通信
                async def run_surgery():
                    result = await asyncio.to_thread(vault_os.perform_memory_surgery, request.get("content", ""))
                    await event_bus.publish({"type": "system_toast", "content": result})
                    await event_bus.publish({"type": "SYSTEM_STATE_CHANGED", "memory_pending_count": len([m for m in vault_os.gatekeeper.fetch_memory() if m.get("status") == "PENDING"])})
                    try:
                        await event_bus.publish(memory_data_payload())
                    except Exception: pass
                asyncio.create_task(run_surgery())

            elif cmd_type == "import_profile":
                async def run_import():
                    result = await asyncio.to_thread(vault_os.process_profile_import, request.get("content", ""))
                    await event_bus.publish({"type": "system_toast", "content": result})
                    await event_bus.publish({"type": "profile_import_state", "content": vault_os.get_profile_import_state()})
                    await event_bus.publish({"type": "SYSTEM_STATE_CHANGED", "memory_pending_count": len([m for m in vault_os.gatekeeper.fetch_memory() if m.get("status") == "PENDING"])})
                    try:
                        await event_bus.publish(memory_data_payload())
                    except Exception: pass
                asyncio.create_task(run_import())

            elif cmd_type == "fetch_profile_import_state":
                await websocket.send_json({"type": "profile_import_state", "content": vault_os.get_profile_import_state()})

            elif cmd_type == "prepare_profile_import":
                async def run_prepare_import():
                    result = await asyncio.to_thread(vault_os.prepare_profile_import, request.get("content", ""))
                    event_type = "profile_import_preview" if result.get("ok") else "profile_import_error"
                    await event_bus.publish({"type": event_type, "content": result})
                    await event_bus.publish({"type": "profile_import_state", "content": result.get("state", vault_os.get_profile_import_state())})
                    if result.get("message"):
                        await event_bus.publish({"type": "system_toast", "content": result.get("message")})
                asyncio.create_task(run_prepare_import())

            elif cmd_type == "commit_profile_import":
                async def run_commit_import():
                    result = await asyncio.to_thread(vault_os.commit_profile_import, request.get("session_id", ""))
                    event_type = "profile_import_done" if result.get("ok") else "profile_import_error"
                    await event_bus.publish({"type": event_type, "content": result})
                    await event_bus.publish({"type": "profile_import_state", "content": result.get("state", vault_os.get_profile_import_state())})
                    await event_bus.publish({"type": "system_toast", "content": result.get("message", "")})
                    await event_bus.publish({"type": "SYSTEM_STATE_CHANGED", "memory_pending_count": len([m for m in vault_os.gatekeeper.fetch_memory() if m.get("status") == "PENDING"])})
                    try:
                        await event_bus.publish(memory_data_payload())
                    except Exception: pass
                asyncio.create_task(run_commit_import())

            elif cmd_type == "cancel_profile_import":
                result = await asyncio.to_thread(vault_os.cancel_profile_import, request.get("session_id", ""))
                await websocket.send_json({"type": "profile_import_state", "content": result.get("state", vault_os.get_profile_import_state())})
                await websocket.send_json({"type": "system_toast", "content": result.get("message", "")})

            # === [通道 C：核心智能体网关 (重型推理)] ===
            elif "message" in request:
                user_msg = request.get("message", "")
                if not user_msg: continue
                if session_mode == "temp":
                    temp_runtime = session_manager.get_temp_runtime(session_id)
                    if not temp_runtime:
                        await websocket.send_json({
                            "type": "system_toast",
                            "session_id": session_id,
                            "content": "临时会话已结束，请重新开启。"
                        })
                        continue
                    request["thread_id"] = session_id
                    request["session_id"] = session_id
                    asyncio.create_task(
                        spawn_temp_agent_task(
                            request,
                            real_loop,
                            temp_runtime,
                            session_manager.is_temp_open
                        )
                    )
                else:
                    # 收到消息后，丢给独立引擎去跑，当前循环立刻进入下一次等待
                    asyncio.create_task(spawn_agent_task(json.dumps(request, ensure_ascii=False), real_loop, vault_os))

    except WebSocketDisconnect:
        print(" [断开连接] 前端 UI 已下线/关闭。")
        consumer_task.cancel() # 安全清理消费者协程
    except Exception as e:
        print(f" [网关异常] 通信循环异常: {str(e)}")
        consumer_task.cancel()
# 2. 动态扫描并挂载第三方后端 API
def mount_vpm_plugins():
    for plugin_name in os.listdir(PLUGINS_DIR):
        plugin_path = os.path.join(PLUGINS_DIR, plugin_name)
        api_file = os.path.join(plugin_path, "api.py")
        
        # 如果插件包含后端路由文件
        if os.path.isdir(plugin_path) and os.path.exists(api_file):
            try:
                if not plugin_security_manager.is_first_party(plugin_name):
                    print(f" [VPM Security] Skipping third-party api.py import for plugin: {plugin_name}")
                    continue
                # 动态导入 Python 模块
                spec = importlib.util.spec_from_file_location(f"vpm.plugins.{plugin_name}", api_file)
                plugin_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(plugin_module)
                # 触发插件的初始化钩子 (建表、传参)
                if hasattr(plugin_module, "init_plugin"):
                    plugin_module.init_plugin(engine)
                # 挂载插件的路由，自动分配隔离前缀
                if hasattr(plugin_module, "router"):
                    app.include_router(
                        plugin_module.router, 
                        prefix=f"/api/plugins/{plugin_name}", 
                        tags=[f"Plugin: {plugin_name}"]
                    )
                    print(f" [VPM 内核] 成功挂载插件后端路由: /api/plugins/{plugin_name}")
                    
            except Exception as e:
                print(f" [VPM 内核] 挂载插件 {plugin_name} 失败: {e}")
mount_vpm_plugins()
init_db()

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=SERVER_PORT,
        log_level="warning",
        log_config=None,
        access_log=False,
    )
