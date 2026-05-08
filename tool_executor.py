import subprocess
import requests
import json
import os
import shlex
from ddgs import DDGS

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
        # 通道 B：执行外部 VPM 插件生态 (Subprocess / HTTP)
        # 在注册表中寻找这个外部工具的完整契约
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
            # 动态参数注入
            for key, value in args.items():
                command = command.replace(f"{{{key}}}", shlex.quote(str(value)))
            
            try:
                # 🔪 保留你的神级操作：timeout 防止死循环卡死整个管家
                result = subprocess.run(
                    command, 
                    shell=True, 
                    capture_output=True, 
                    text=True,
                    cwd=os.getcwd(),
                    timeout=60 
                )
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

            # 稳定性修复：使用递归遍历字典进行参数替换，防止破坏 JSON 结构
            def replace_vars(node):
                if isinstance(node, str):
                    for k, v in args.items():
                        if f"{{{k}}}" == node:  # 全字匹配，保持原类型（如数字、布尔值）
                            return v
                        node = node.replace(f"{{{k}}}", str(v)) # 部分匹配转为字符串
                    return node
                elif isinstance(node, dict):
                    return {k: replace_vars(v) for k, v in node.items()}
                elif isinstance(node, list):
                    return [replace_vars(x) for x in node]
                return node
            # 动态组装 Payload
            payload_format = execution_config.get("payload_format")
            request_data = replace_vars(payload_format) if payload_format else args

            try:
                if method == "POST":
                    resp = requests.post(endpoint, json=request_data, headers=headers, timeout=15)
                else:
                    resp = requests.get(endpoint, params=request_data, headers=headers, timeout=15)
                    
                resp.raise_for_status() # 拦截 4xx 和 5xx 错误
                return resp.text
                
            except requests.exceptions.Timeout:
                return f"[SYSTEM_ERROR]: 请求 Agent 超时 (>15秒)。可能原因：对方服务器宕机或网络阻塞。"
            except requests.exceptions.ConnectionError:
                return f"[SYSTEM_ERROR]: 无法连接到外部 Agent ({endpoint})。可能原因：服务未启动或网络不通。"
            except requests.exceptions.HTTPError as err:
                return f"[SYSTEM_ERROR]: 第三方 Agent 拒绝服务。HTTP 状态码: {err.response.status_code}。"
        else:
            return f"[SYSTEM_ERROR]: 不支持的执行模式 '{execution_config['type']}'"
        
    # 具体的系统内置工具实现区 (Action)
    def action_web_search(self, query):
        """Mock 版本的网络搜索（后期可接 DuckDuckGo）"""
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
    # 真正的网络搜索实现，使用 duckduckgo-search 抓取最新信息
    def action_web_search(self, query):
        """真正的网络搜索：使用 duckduckgo-search 抓取最新信息"""
        print(f"\n🌐 [网络搜索] 正在激活 'web_search' 工具，搜索: '{query}'")
        
        try:
            # 建立搜索引擎会话
            with DDGS() as ddgs:
                # 限制为 top 3 的结果，避免搜索时间过长
                raw_results = list(ddgs.text(query, max_results=3))
            
            if not raw_results:
                return "【网络检索提示】: 未能在互联网上查找到与该关键词相关的最新内容。"

            # 结构化清洗搜索结果
            formatted_results = []
            for i, res in enumerate(raw_results):
                title = res.get('title', '未知内容相关标题')
                link = res.get('href', '无来源链接')
                body = res.get('body', '')
                
                # 为了保持上下文窗口整洁并控制 Token 消耗，严格控制摘要长度
                # 提取不超过 80 个字符的内容，拼上 URL 后整体确保在 100 字以内
                truncated_body = body[:80] + "..." if len(body) > 80 else body
                summary = f"{truncated_body} URL: {link}"
                
                formatted_results.append(f"{i+1}. 标题：{title}\n   摘要：{summary}")

            return "【最新网络搜索结果】:\n" + "\n\n".join(formatted_results)

        except Exception as e:
            return f"[SYSTEM_ERROR]: 网络外呼引擎发生异常: {e}"
