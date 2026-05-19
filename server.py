from fastapi.responses import FileResponse
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import secrets
import json
import asyncio
import os
import importlib.util
import shutil
import time

from main import VaultOS_Terminal, VAULT_ROOT
from sqlmodel import Session, select
from db import engine, init_db
from fastapi.staticfiles import StaticFiles
from core_bus import event_bus
from agent_runner import spawn_agent_task

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
# 核心防御
SECURITY_TOKEN = secrets.token_hex(16)
os.makedirs("vault", exist_ok=True)
with open(os.path.join(VAULT_ROOT, ".run_token"), "w", encoding="utf-8") as f:
    f.write(SECURITY_TOKEN)

print("="*60)
print(f"🚀 [网关启动] Vault OS 后台微服务已点火！")
print(f"🔒 [安全系统] 本次运行专属 Token: {SECURITY_TOKEN}")
print("="*60)

print("⚙️  正在唤醒底层大模型和向量引擎...")
vault_os = VaultOS_Terminal()

@app.post("/api/rag/ingest")
async def api_rag_ingest(request: Request):
    try:
        payload_data = await request.json()
        auth_header = request.headers.get("Authorization")
        if auth_header != f"Bearer {SECURITY_TOKEN}":
            return {"status": "error", "message": "未授权的访问拒绝进入 RAG 存储区"}  
        # 核心防线：路径沙盒验证 (Path Sandbox)
        source_file = payload_data.get("source_file", "")
        # 1. 防御路径穿越攻击 (防范诸如 ../knowledge/xxx.md 的恶意路径)
        safe_source = os.path.normpath(source_file)
        if ".." in safe_source:
            print(f"🚨 [安全拦截] 检测到恶意路径穿越攻击: {source_file}")
            return {"status": "error", "message": "非法路径！系统已拦截。"} 
        # 2. 权限隔离：外来 HTTP 请求【只能】操作 plugins 目录下的文件！
        allowed_prefix = os.path.normpath(PLUGINS_DIR)
        if not safe_source.startswith(allowed_prefix):
            print(f"🚨 [越权拦截] 第三方 Agent 试图篡改系统核心记忆: {safe_source}")
            return {"status": "error", "message": "越权操作：第三方插件仅允许操作自己的沙盒数据！"}
            
        success = await asyncio.to_thread(vault_os.receive_knowledge_payload, payload_data)
        return {"status": "success"} if success else {"status": "error"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.websocket("/ws/{client_token}")
async def websocket_endpoint(websocket: WebSocket, client_token: str):
    if client_token != SECURITY_TOKEN:
        await websocket.close(code=1008, reason="Unauthorized")
        return
        
    await websocket.accept()
    real_loop = asyncio.get_running_loop()

    # 1. 启动 Event Bus 监听协程：让后台任务能够把结果推给前端
    async def consume_events():
        async for event in event_bus.subscribe():
            await websocket.send_json(event)
    consumer_task = asyncio.create_task(consume_events())

    print("🟢 [连接成功] 神经链路已打通，正在同步初始状态...")
    
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
                vault_os.save_config(request.get("content")) 
                await websocket.send_json({"type": "system_toast", "content": "✅ 系统核心已热重载！"})
                
            elif cmd_type == "fetch_memory":
                try:
                    pending_path = os.path.join(VAULT_ROOT, "pending_memory.json")
                    with open(pending_path, "r", encoding="utf-8") as f:
                        await websocket.send_json({"type": "memory_data", "content": json.load(f).get("queue", [])})
                except Exception:
                    await websocket.send_json({"type": "memory_data", "content": []})
            # VPM 雷达扫描指令
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
                                    info['plugin_id'] = p # 强行把物理文件夹名注入进去，作为唯一 ID
                                    plugins_info.append(info)
                            except Exception as e:
                                print(f"🚨 [VPM] 解析插件 {p} 契约失败: {e}")
                                
                await websocket.send_json({"type": "plugins_list", "content": plugins_info})
            # VPM 物理卸载指令
            elif cmd_type == "uninstall_plugin":
                plugin_id = request.get("plugin_id")
                safe_id = os.path.basename(plugin_id) 
                plugin_path = os.path.join(PLUGINS_DIR, safe_id)
                api_file = os.path.join(plugin_path, "api.py")
                
                if os.path.exists(plugin_path):
                    try:
                        # 0. 在物理销毁前，由主引擎接管并强制注销该插件的所有向量记忆！
                        # 绝对安全：不经过 HTTP API，直接调用主系统的内存函数
                        knowledge_dir = os.path.join(plugin_path, "knowledge")
                        if os.path.exists(knowledge_dir):
                            for md_file in os.listdir(knowledge_dir):
                                if md_file.endswith(".md"):
                                    filepath = os.path.join(knowledge_dir, md_file)
                                    purge_payload = {
                                        "command": "RAG_UPSERT",
                                        "source_file": filepath,
                                        "hash": "uninstall_purge",
                                        "payload": [] # 空载荷触发彻底删除
                                    }
                                    vault_os.receive_knowledge_payload(purge_payload)
                            print(f"🧹 [系统屠魔] 插件 [{safe_id}] 的所有孤儿向量记忆已被主系统强行注销！")

                        # 1. 尝试调用插件专属的自毁钩子 (Lifecycle Hook)
                        if os.path.exists(api_file):
                            import importlib.util
                            spec = importlib.util.spec_from_file_location(f"vpm.temp.{safe_id}", api_file)
                            plugin_module = importlib.util.module_from_spec(spec)
                            spec.loader.exec_module(plugin_module)
                            
                            if hasattr(plugin_module, "uninstall_hook"):
                                plugin_module.uninstall_hook(engine)
                        
                        # 2. 主引擎执行最终的物理抹杀：连根拔起插件文件夹
                        shutil.rmtree(plugin_path) 
                        
                        await websocket.send_json({"type": "plugin_uninstalled_success", "plugin_id": safe_id})
                        await websocket.send_json({"type": "system_toast", "content": f"💥 插件 [{safe_id}] 已彻底卸载！"})
                    except Exception as e:
                        await websocket.send_json({"type": "system_toast", "content": f"🚨 卸载崩溃: {e}"})
            # === [通道 B：中等耗时的后台 IO 任务] ===
            elif cmd_type == "memory_surgery":
                # 交给线程池处理，避免卡死当前通信
                async def run_surgery():
                    result = await asyncio.to_thread(vault_os.perform_memory_surgery, request.get("content", ""))
                    await event_bus.publish({"type": "system_toast", "content": result})
                    # 手术完触发一次记忆刷新
                    try:
                        pending_path = os.path.join(VAULT_ROOT, "pending_memory.json")
                        with open(pending_path, "r", encoding="utf-8") as f:
                            await event_bus.publish({"type": "memory_data", "content": json.load(f).get("queue", [])})
                    except Exception: pass
                asyncio.create_task(run_surgery())

            elif cmd_type == "import_profile":
                async def run_import():
                    result = await asyncio.to_thread(vault_os.process_profile_import, request.get("content", ""))
                    await event_bus.publish({"type": "system_toast", "content": result})
                    try:
                        pending_path = os.path.join(VAULT_ROOT, "pending_memory.json")
                        with open(pending_path, "r", encoding="utf-8") as f:
                            await event_bus.publish({"type": "memory_data", "content": json.load(f).get("queue", [])})
                    except Exception: pass
                asyncio.create_task(run_import())

            # === [通道 C：核心智能体网关 (重型推理)] ===
            elif "message" in request:
                user_msg = request.get("message", "")
                if not user_msg: continue
                # 收到消息后，丢给独立引擎去跑，当前循环立刻进入下一次等待
                asyncio.create_task(spawn_agent_task(raw_data, real_loop, vault_os))

    except WebSocketDisconnect:
        print("🔴 [断开连接] 前端 UI 已下线/关闭。")
        consumer_task.cancel() # 安全清理消费者协程
    except Exception as e:
        print(f"🔴 [网关异常] 通信循环崩溃: {str(e)}")
        consumer_task.cancel()
# 2. 动态扫描并挂载第三方后端 API
def mount_vpm_plugins():
    for plugin_name in os.listdir(PLUGINS_DIR):
        plugin_path = os.path.join(PLUGINS_DIR, plugin_name)
        api_file = os.path.join(plugin_path, "api.py")
        
        # 如果插件包含后端路由文件
        if os.path.isdir(plugin_path) and os.path.exists(api_file):
            try:
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
                    print(f"✅ [VPM 内核] 成功挂载插件后端路由: /api/plugins/{plugin_name}")
                    
            except Exception as e:
                print(f"🚨 [VPM 内核] 挂载插件 {plugin_name} 失败: {e}")
mount_vpm_plugins()
init_db()

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")