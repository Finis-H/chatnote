import os
import json

class ToolRegistry:
    def __init__(self, tools_dir="vault/tools"):
        self.tools_dir = tools_dir
        self.registered_names = set()
        self.system_warnings = []
        
        # 1. 内置系统级原生工具 (System Built-ins)
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "web_search",
                    # ✅ 方案 A 的核心：重写工具描述 (Description)
                    # 在这里给大模型下达最高指令，强迫它在调用搜索前先充当翻译官！
                    "description": "这是一个强大的全球网络搜索引擎。【最高指令】：当检索全球前沿科技动态、AI大模型进展、外企新闻时，你 **必须** 将搜索词翻译为纯英文再传入！例如：不要传入 'openai大模型最新版本'，必须传入 'OpenAI latest model release'。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "需要搜索引擎执行的精确搜索关键词"
                            }
                        },
                        "required": ["query"]
                    }
                }
            },
            # 本地 RAG 封装为原生工具
            {
                "type": "function",
                "function": {
                    "name": "search_local_knowledge",
                    "description": "检索本地知识库。当 Boss 询问他自己的笔记、历史记忆、代码习惯、日程安排、财报记录或人际关系时，必须调用此工具。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "用于在向量空间中执行模糊匹配的核心搜索短语"
                            }
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "control_ui_layout",
                    "description": "控制 Vault OS 前端界面的物理空间与布局。当 Boss 想要听歌、看图表，或者明确需要【沉浸式体验】时，你【只需且必须只】调用此单一工具！绝对禁止再组合调用 web_search 搜索推荐！",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "target_panel": {
                                "type": "string",
                                "description": "要控制的目标面板名称，例如 'music_agent', 'invest_agent'"
                            },
                            "state": {
                                "type": "string",
                                "enum": ["mini", "immersive", "closed"],
                                "description": "面板的目标形态：mini(侧边栏静默陪伴), immersive(全屏沉浸覆盖), closed(关闭)"
                            }
                        },
                        "required": ["target_panel", "state"]
                    }
                }
            }
        ]
        self.registered_names.add("web_search")
        self.registered_names.add("search_local_knowledge")
        # 2. 动态加载外部插件生态 (VPM 雏形)
        self._load_external_tools()

    def _load_external_tools(self):
        """物理扫描 tools 目录，加载第三方 MCP/Agent 契约并执行防撞校验"""
        os.makedirs(self.tools_dir, exist_ok=True)
        # 1. 扫描公共工具目录 (vault/tools/*.json)
        self._scan_folder(self.tools_dir)
        # 2. 扫描插件私有工具目录 (vault/plugins/*/tools/*.json)
        plugins_root = "vault/plugins"
        if os.path.exists(plugins_root):
            for plugin_name in os.listdir(plugins_root):
                plugin_tool_dir = os.path.join(plugins_root, plugin_name, "tools")
                if os.path.exists(plugin_tool_dir):
                    self._scan_folder(plugin_tool_dir)
        
    def _scan_folder(self, folder_path):
        if not os.path.exists(folder_path):
            return
        for filename in os.listdir(folder_path):
            if not filename.endswith(".json"): continue
            
            filepath = os.path.join(folder_path, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                try:
                    tool_manifest = json.load(f)
                    
                    # 容错：处理被包在数组里的 JSON
                    if isinstance(tool_manifest, dict):
                        manifests = [tool_manifest]
                    elif isinstance(tool_manifest, list):
                        manifests = tool_manifest
                    else:
                        print(f"⚠️ [跳过] {filename} 格式不正确（需为字典或列表）。")
                        continue
                        
                    for tool_manifest in manifests:
                        # 按照 OpenAI 原生 Tool Calling 标准提取 name
                        if "function" not in tool_manifest or "name" not in tool_manifest["function"]:
                            print(f"⚠️ [跳过] {filename} 中的某项不符合原生 Tool Schema 标准。")
                            continue       
                        name = tool_manifest["function"]["name"]
                        
                        # 这段防撞击拦截必须缩进到 for 循环内部！
                        if name in self.registered_names:
                            print(f"⚠️ [警告] 发现冲突工具: {name} (文件: {filename})。已强制隔离。")
                            self.system_warnings.append(f"工具库加载异常：发现冲突插件 '{name}'。")
                            continue
                            
                        # 确保最外层有 "type": "function" 标识
                        if "type" not in tool_manifest:
                            tool_manifest["type"] = "function"

                        self.tools.append(tool_manifest)
                        self.registered_names.add(name)
                        print(f"🔌 [VPM 挂载] 外部插件契约已就绪: {name}")

                except json.JSONDecodeError as e:
                    # 单独捕获 JSON 语法错误，方便排查格式问题
                    print(f"🚨 契约解析失败 {filename}: JSON 格式错误 - {e}")    
                except Exception as e:
                    print(f"🚨 契约损坏 {filename}: {e}")

    def get_tools(self):
        """直接将标准的 Tools 数组暴露给大模型接口"""
        # 如果没有任何工具，按 OpenAI 标准不能传空列表，必须返回 None
        return self.tools if self.tools else None