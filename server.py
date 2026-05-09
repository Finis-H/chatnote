import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
import secrets
import json
import asyncio
import os

# 引入管家大脑与核心总线
from main import VaultOS_Terminal
from core_bus import event_bus
from agent_runner import spawn_agent_task

app = FastAPI()

# 🛡️ 核心防御
SECURITY_TOKEN = secrets.token_hex(16)
os.makedirs("vault", exist_ok=True)
with open("vault/.run_token", "w", encoding="utf-8") as f:
    f.write(SECURITY_TOKEN)

print("="*60)
print(f"🚀 [网关启动] Vault OS 后台微服务已点火！")
print(f"🔒 [安全系统] 本次运行专属 Token: {SECURITY_TOKEN}")
print("="*60)

print("⚙️  正在唤醒底层大模型和向量引擎...")
vault_os = VaultOS_Terminal()

@app.post("/api/rag/ingest")
async def api_rag_ingest(request: Request):
    # (此部分保持不变...)
    try:
        payload_data = await request.json()
        auth_header = request.headers.get("Authorization")
        if auth_header != f"Bearer {SECURITY_TOKEN}":
            return {"status": "error", "message": "未授权的访问拒绝进入 RAG 存储区"}  
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
                    with open("vault/pending_memory.json", "r", encoding="utf-8") as f:
                        await websocket.send_json({"type": "memory_data", "content": json.load(f).get("queue", [])})
                except Exception:
                    await websocket.send_json({"type": "memory_data", "content": []})

            # === [通道 B：中等耗时的后台 IO 任务] ===
            elif cmd_type == "memory_surgery":
                # 交给线程池处理，避免卡死当前通信
                async def run_surgery():
                    result = await asyncio.to_thread(vault_os.perform_memory_surgery, request.get("content", ""))
                    await event_bus.publish({"type": "system_toast", "content": result})
                    # 手术完触发一次记忆刷新
                    try:
                        with open("vault/pending_memory.json", "r", encoding="utf-8") as f:
                            await event_bus.publish({"type": "memory_data", "content": json.load(f).get("queue", [])})
                    except Exception: pass
                asyncio.create_task(run_surgery())

            elif cmd_type == "import_profile":
                async def run_import():
                    result = await asyncio.to_thread(vault_os.process_profile_import, request.get("content", ""))
                    await event_bus.publish({"type": "system_toast", "content": result})
                    try:
                        with open("vault/pending_memory.json", "r", encoding="utf-8") as f:
                            await event_bus.publish({"type": "memory_data", "content": json.load(f).get("queue", [])})
                    except Exception: pass
                asyncio.create_task(run_import())

            # === [通道 C：核心智能体网关 (重型推理)] ===
            elif "message" in request:
                if not request.get("message"): continue
                # 收到消息后，丢给独立引擎去跑，当前循环立刻进入下一次等待
                asyncio.create_task(spawn_agent_task(raw_data, real_loop, vault_os))

    except WebSocketDisconnect:
        print("🔴 [断开连接] 前端 UI 已下线/关闭。")
        consumer_task.cancel() # 安全清理消费者协程
    except Exception as e:
        print(f"🔴 [网关异常] 通信循环崩溃: {str(e)}")
        consumer_task.cancel()

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")