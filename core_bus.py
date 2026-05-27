import asyncio
import contextvars
from typing import Any

current_event_session_id = contextvars.ContextVar("vault_event_session_id", default="main")


def bind_event_session(session_id: str):
    return current_event_session_id.set(session_id or "main")


def reset_event_session(token):
    current_event_session_id.reset(token)

class NeuroLinkBus:
    def __init__(self):
        # 核心：一个异步队列，作为 Agent 和 WebSocket 之间的缓冲区
        self.queue = asyncio.Queue()

    async def publish(self, message: dict):
        """供异步函数调用的推送方法"""
        if isinstance(message, dict) and "session_id" not in message:
            message = {**message, "session_id": current_event_session_id.get()}
        await self.queue.put(message)
        
    def publish_sync(self, main_loop: asyncio.AbstractEventLoop, message: dict):
        """
        🚨 极其关键：供 CrewAI 的同步线程 (Callback) 调用的跨线程推送方法。
        如果不做跨线程调度，直接在子线程里 await 会报错！
        """
        if isinstance(message, dict) and "session_id" not in message:
            message = {**message, "session_id": current_event_session_id.get()}
        main_loop.call_soon_threadsafe(self.queue.put_nowait, message)

    async def subscribe(self):
        """WebSocket 持续监听这个生成器"""
        while True:
            # 当队列为空时，这里会自动挂起，绝不消耗 CPU
            yield await self.queue.get()

# 实例化全局单例
event_bus = NeuroLinkBus()
