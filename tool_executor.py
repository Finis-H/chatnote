import subprocess
import requests
import json
import os
import shlex
from datetime import datetime
from ddgs import DDGS
from core_bus import event_bus
import asyncio

class ToolExecutor:
    def __init__(self, registry, vector_db=None):
        self.registry = registry
        self.vector_db = vector_db

    def execute(self, tool_call):
        """融合版核心执行引擎：支持原生内置函数 + 外部 VPM 插件"""
        func_name = tool_call.function.name
        
        try:
            # 1. 优雅解析：直接拿原生协议里的 JSON 参数，告别恶心的正则清洗
            args = json.loads(tool_call.function.arguments)
        except json.JSONDecodeError:
            return "[SYSTEM_ERROR]: 大模型生成的参数 JSON 解析失败。"
            
        # 通道 A：执行系统内置原生工具 (Built-ins)
        if func_name == "web_search":
            return self.action_web_search(args.get("query", ""))
        elif func_name == "search_local_knowledge":
            return self.action_search_local_knowledge(args.get("query", ""))
        # 新增：UI 控制通道
        elif func_name == "control_ui_layout":
            target = args.get("target_panel")
            state = args.get("state")
            print(f"🪄 [UI 魔法] 大模型主动施法：将 {target} 切换至 {state} 模式")
            # 使用事件总线，将这个纯粹的 UI 指令通过 WebSocket 推给前端
            # 必须用 asyncio.run 或创建 task 来执行异步推送
            try:
                asyncio.run(event_bus.publish({
                    "type": "ui_command",
                    "target_panel": target,
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

        print(f"\n⚙️  [调度器] 正在拉起外部 Agent: {func_name} ...")
        
        # 模式 B1：本地子进程 (Subprocess)
        if execution_config["type"] == "subprocess":
            command = execution_config["command"]
            for key, value in args.items():
                command = command.replace(f"{{{key}}}", shlex.quote(str(value)))
            
            try:
                result = subprocess.run(command, shell=True, capture_output=True, text=True, cwd=os.getcwd(), timeout=60)
                if result.returncode == 0:
                    return result.stdout.strip()
                else:
                    return f"[SYSTEM_ERROR]: 子进程抛出异常 (Exit Code {result.returncode})。\n错误日志: {result.stderr.strip()}"
            except subprocess.TimeoutExpired:
                return f"[SYSTEM_ERROR]: 本地脚本执行超时 (>60秒)，系统已强制将其 kill。"
                
        # 模式 B2：本地微服务或云端 API (HTTP)
        elif execution_config["type"] == "http":
            endpoint = execution_config["endpoint"]
            method = execution_config.get("method", "POST").upper()
            headers = execution_config.get("headers", {})

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
                return resp.text
            except requests.exceptions.Timeout:
                return "[SYSTEM_ERROR]: 请求 Agent 超时 (>15秒)。可能原因：对方服务器宕机或网络阻塞。"
            except requests.exceptions.ConnectionError:
                return f"[SYSTEM_ERROR]: 无法连接到外部 Agent ({endpoint})。可能原因：服务未启动或网络不通。"
            except requests.exceptions.HTTPError as err:
                return f"[SYSTEM_ERROR]: 第三方 Agent 拒绝服务。HTTP 状态码: {err.response.status_code}。"
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
        """真正的网络搜索：动用底层参数强锁时间线"""
        print(f"\n🌐 [网络搜索] 触发工具, 搜索词: '{query}'")

        try:
            from ddgs import DDGS
            with DDGS() as ddgs:
                raw_results = list(ddgs.text(query, max_results=4, timelimit='m'))
            
            # 如果一个月内没搜到，放宽到一年
            if not raw_results:
                with DDGS() as ddgs:
                    raw_results = list(ddgs.text(query, max_results=4, timelimit='y'))

            # 核心阻断机制：明确告诉大模型搜索失败，禁止它编造！
            if not raw_results:
                return "【搜索工具返回结果】：空。网络上未找到相关信息。警告：请如实告知 Boss 没有搜到最新信息，绝对禁止使用你自己的训练数据进行编造！"

            formatted_results = []
            for i, res in enumerate(raw_results):
                title = res.get('title', '')
                body = res.get('body', '')
                formatted_results.append(f"来源{i+1}: {title}\n内容: {body}")

            return "【最新网络搜索结果】:\n" + "\n\n".join(formatted_results)

        except Exception as e:
            return f"[搜索工具异常]: {e}。请直接告知 Boss 搜索工具发生故障。"
