import asyncio
import json
from concurrent.futures import ThreadPoolExecutor
from core_bus import event_bus

# 创建一个专门跑重度 AI 任务的独立线程池
ai_executor = ThreadPoolExecutor(max_workers=3)

def _sync_real_brain_kickoff(payload_dict: dict, vault_os):
    """
    在这个子线程里，真正调用你原本 main.py 里的 AI 大脑
    """
    user_input = payload_dict.get("message", "")
    thread_id = payload_dict.get("thread_id", "global")
    display_message = payload_dict.get("display_message", user_input)
    
    # 💥 这里调用真实的 RAG 和大模型推理！
    # 因为跑在独立线程里，所以哪怕模型思考 30 秒，前端也依然能秒切页面
    result = vault_os.get_response(user_input, thread_id, display_message)
    return result


async def spawn_agent_task(raw_data: str, main_loop: asyncio.AbstractEventLoop, vault_os):
    """
    这个函数负责把任务丢给线程池，并处理最终结果和流式下发
    """
    payload = json.loads(raw_data)
    thread_id = payload.get("thread_id", "global")
    
    # 向前端汇报：大脑已激活，开始思考
    await event_bus.publish({
        "type": "status",
        "content": "thinking"
    })

    try:
        # 将阻塞的 AI 调用推入线程池
        result = await main_loop.run_in_executor(
            ai_executor, 
            _sync_real_brain_kickoff, 
            payload, 
            vault_os
        )
        
        # 🚀 恢复流式打字机效果！
        # 将完整生成的文本切片，以极快的速度源源不断地通过 Event Bus 推给前端
        chunk_size = 4
        for i in range(0, len(result), chunk_size):
            await asyncio.sleep(0.02) # 略微拉大间隔，保持丝滑的打字节奏
            await event_bus.publish({
                "type": "stream", 
                "content": result[i:i+chunk_size],
                "thread_id": thread_id
            })
            
    except Exception as e:
        await event_bus.publish({
            "type": "stream",
            "thread_id": thread_id,
            "content": f"\n\n🚨 [内核崩溃] 大脑推理层异常: {str(e)}"
        })
    finally:
        # 无论成功还是失败，关闭前端的 thinking (🧠) 动画
        await event_bus.publish({
            "type": "status",
            "content": "done"
        })