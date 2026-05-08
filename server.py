import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
import secrets
import json
import asyncio
import os
# 引入管家大脑
from main import VaultOS_Terminal

app = FastAPI()

# 🛡️ 核心防御：每次启动服务器，随机生成一个 32 位的动态 Token
SECURITY_TOKEN = secrets.token_hex(16)
os.makedirs("vault", exist_ok=True)
with open("vault/.run_token", "w", encoding="utf-8") as f:
    f.write(SECURITY_TOKEN)

print("="*60)
print(f"🚀 [网关启动] Vault OS 后台微服务已点火！")
print(f"🔒 [安全系统] 本次运行的专属 Token: {SECURITY_TOKEN}")
print(f"🔗 [前端直连] ws://127.0.0.1:8000/ws/{SECURITY_TOKEN}")
print("="*60)

print("⚙️  正在唤醒底层大模型和向量引擎...")
vault_os = VaultOS_Terminal()

@app.post("/api/rag/ingest")
async def api_rag_ingest(request: Request):
    """
    🗄️ 专属数据网关：留给外部仓管 Agent (如 Obsidian 插件/爬虫) 的 HTTP 注入接口
    """
    try:
        # 获取外部发来的 JSON 载荷
        payload_data = await request.json()
        # 可以在这里增加简单的 Header Token 校验（可选）
        auth_header = request.headers.get("Authorization")
        if auth_header != f"Bearer {SECURITY_TOKEN}":
            return {"status": "error", "message": "未授权的访问拒绝进入 RAG 存储区"}  
        # 丢给底层大脑处理
        success = await asyncio.to_thread(vault_os.receive_knowledge_payload, payload_data)
        if success:
            return {"status": "success", "message": "记忆切片同化完成"}
        else:
            return {"status": "error", "message": "载荷不合法或处理失败"}        
    except Exception as e:
        return {"status": "error", "message": f"网关异常: {str(e)}"}

@app.websocket("/ws/{client_token}")
async def websocket_endpoint(websocket: WebSocket, client_token: str):
    """双向流式通信管道"""
    if client_token != SECURITY_TOKEN:
        await websocket.close(code=1008, reason="Unauthorized Token")
        print(f"🚨 [拦截] 发现未授权的恶意连接尝试！已熔断！")
        return
    await websocket.accept()
    print("🟢 [连接成功] 正在同步历史记忆...")
    # 🚨 修复 1：使用最新的 threads 属性进行同步
    if hasattr(vault_os, 'threads') and vault_os.threads:
        await websocket.send_text(json.dumps({
            "type": "history_all", 
            "content": vault_os.threads
        }))   
    try:
        while True:
            data = await websocket.receive_text()
            request = json.loads(data) 
            # 获取前端传来的线程 ID，默认为 global
            thread_id = request.get("thread_id", "global")
            cmd_type = request.get("type")
            # 路由分发
            if cmd_type == "fetch_news":
                local_news = vault_os.get_local_news_list()
                await websocket.send_text(json.dumps({"type": "news_list", "content": local_news})) 
            elif cmd_type == "fetch_favorites":
                local_favorites = vault_os.get_favorite_list()
                await websocket.send_text(json.dumps({"type": "favorites_list", "content": local_favorites}))   
            elif cmd_type == "fetch_note_detail":
                path = request.get("path")
                content = vault_os.get_note_content(path)
                await websocket.send_text(json.dumps({"type": "note_content", "content": content}))
            # 分支 D: 删除笔记指令
            elif cmd_type == "delete_note":
                path = request.get("path")
                note_id = request.get("id")
                success = vault_os.delete_note(path, note_id)
                if success:
                    # 通知前端删除成功，让 UI 自动移除卡片
                    await websocket.send_text(json.dumps({
                        "type": "delete_success", 
                        "id": note_id
                    }))
            # 分支 E: 前端请求拉取当前配置
            elif cmd_type == "get_config":
                await websocket.send_text(json.dumps({
                    "type": "config_data",
                    "content": vault_os.llm_config
                }))
            # 分支 F: 前端保存新配置
            elif cmd_type == "save_config":
                new_config = request.get("content")
                vault_os.save_config(new_config) # 写入并热重载
                await websocket.send_text(json.dumps({
                    "type": "status",
                    "content": "✅ 系统核心已切换！"
                }))
            elif "message" in request:
                user_input = request.get("message", "")
                display_message = request.get("display_message", user_input)
                if not user_input: 
                    continue 
                await websocket.send_text(json.dumps({"type": "status", "content": "thinking"}))
                try: 
                    # 将原来的同步等待，改为异步后台任务
                    task = asyncio.create_task(
                        asyncio.to_thread(vault_os.get_response, user_input, thread_id, display_message)
                    )
                    # 心跳循环：在大模型思考期间，每 2 秒发一次隐形脉冲，防止 WS 假死断开！
                    while not task.done():
                        try:
                            # 发送一个前端 Vue 不会渲染的 ping 信号
                            await websocket.send_text(json.dumps({"type": "ping", "content": "keep-alive"}))
                        except Exception:
                            pass 
                        await asyncio.sleep(2)   
                    # 任务完成，获取最终生成的文本
                    result = task.result()

                    chunk_size = 4
                    for i in range(0, len(result), chunk_size):
                        await asyncio.sleep(0.02) # 略微拉大间隔，保持丝滑的打字节奏
                        await websocket.send_text(json.dumps({
                            "type": "stream", 
                            "content": result[i:i+chunk_size],
                            "thread_id": thread_id
                        }))   
                    await websocket.send_text(json.dumps({"type": "status", "content": "done"}))   
                except Exception as e:
                    await websocket.send_text(json.dumps({"type": "stream", "content": f"\n[引擎异常] {e}", "thread_id": thread_id}))
                    await websocket.send_text(json.dumps({"type": "status", "content": "done"}))
            # 分支：前端请求拉取潜意识缓冲区
            elif cmd_type == "fetch_memory":
                try:
                    with open("vault/pending_memory.json", "r", encoding="utf-8") as f:
                        memory_data = json.load(f)
                    await websocket.send_text(json.dumps({
                        "type": "memory_data", 
                        "content": memory_data.get("queue", [])
                    }))
                except Exception as e:
                    await websocket.send_text(json.dumps({"type": "memory_data", "content": []}))
            # 🚨 拦截专属记忆手术指令 (修复串台和红点不消失)
            elif cmd_type == "memory_surgery":
                user_content = request.get("content", "")
                # 1. 呼叫大模型执行记忆手术 (在 main.py 里实现)
                surgery_result = await asyncio.to_thread(vault_os.perform_memory_surgery, user_content)
                # 2. 手术成功后，重新读取一遍最新的 JSON，推给前端刷新红点！
                try:
                    with open("vault/pending_memory.json", "r", encoding="utf-8") as f:
                        memory_data = json.load(f)
                    # 推送最新的记忆队列，前端收到后红点自动重新计算
                    await websocket.send_text(json.dumps({
                        "type": "memory_data", 
                        "content": memory_data.get("queue", [])
                    }))
                except Exception as e:
                    pass
                # 3. 可选：可以在前端弹个系统通知，告诉 Boss 手术完成
                await websocket.send_text(json.dumps({
                    "type": "system_toast", 
                    "content": surgery_result
                }))
            elif cmd_type == "import_profile":
                user_content = request.get("content", "")
                # 极其致命：必须用 asyncio.to_thread 把任务推到后台！绝不能堵死主线程！
                import_result = await asyncio.to_thread(vault_os.process_profile_import, user_content)
                # 任务完成后，给前端发送轻量级 Toast 汇报
                await websocket.send_text(json.dumps({"type": "system_toast", "content": import_result}))
                # 修复：前端需要更新小红点，必须从后端的物理硬盘重新读取缓冲队列
                try:
                    with open("vault/pending_memory.json", "r", encoding="utf-8") as f:
                        memory_data = json.load(f)
                    await websocket.send_text(json.dumps({
                        "type": "memory_data", 
                        "content": memory_data.get("queue", [])
                    }))
                except Exception as e:
                    pass
    except WebSocketDisconnect:
        print("🔴 [断开连接] 前端 UI 已下线/关闭。后台引擎继续潜伏。")
    except Exception as e:
        print(f"🔴 [网关致命异常] {str(e)}")
        
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")