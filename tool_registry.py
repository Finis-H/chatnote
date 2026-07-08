import os
import json
from main import VAULT_ROOT
from plugin_security import normalize_manifest_security

class ToolRegistry:
    def __init__(self, tools_dir=None):
        self.tools_dir = tools_dir or os.path.join(VAULT_ROOT, "tools")
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
                    "description": "这是一个带多通道降级的全球网络搜索引擎，返回标题、摘要、URL、来源、日期和搜索时间等元数据；如果只能拿到无时间限制的结果，会明确标注“未验证时效性”。【最高指令】：1. 当检索全球前沿科技动态、AI大模型进展、外企新闻时，你必须将搜索词翻译为纯英文再传入！2. 当检索【天气、股市、新闻、比赛结果】等对时间极度敏感的实时信息时，你 **必须** 将系统的当前日期（年月日）直接强制拼接在搜索词中！例如：绝对不能传入 '今天上海天气'，必须传入 '上海天气 2026年5月23日'。3. 回答必须优先引用工具返回的 URL/日期/来源；如果工具报告失败、为空或未验证时效性，必须如实说明，不要使用训练数据补编最新事实。",
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
                    "description": "本地高维向量数据库（RAG）唯一检索入口！核心触发法则：只要 Boss 询问的内容不是客观世界的公共常识（如'地球有多大'），而是涉及他【个人系统内部的专属资产】——包括但不限于他自己写的笔记、代码、历史对话，以及【任何已安装的第三方 Agent（如影音、健康、财务、日程等插件）自动生成并投喂的领域数据与解析】，你必须且只能调用此工具在向量空间中执行模糊检索！绝对禁止调用任何外部子进程或全量文件扫描脚本！",
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
                    "description": "纯粹的 UI 控制器。当 Boss 明确要求“收起面板”、“关闭窗口”或“全屏放大面板”时调用此工具。⚠️警告：如果你已经调用了具体的业务插件（如 play_music_playlist 音乐播放），业务插件会自动弹出 UI，此时【绝对禁止】再调用本工具，否则会导致界面冲突！",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "target_panel": {
                                "type": "string",
                                "description": "要控制的目标面板名称，例如 'music_agent', 'invest_agent'"
                            },
                            "target_component": {
                                "type": "string",
                                "description": "目标面板的主 Vue 组件名，例如音乐插件固定填 'MusicAgentPanel'"
                            },
                            "state": {
                                "type": "string",
                                "enum": ["mini", "immersive", "closed"],
                                "description": "面板的目标形态：mini(侧边栏静默陪伴), immersive(全屏沉浸覆盖), closed(关闭)"
                            }
                        },
                        "required": ["target_panel", "target_component", "state"]
                    }
                }
            }
        ]
        self.registered_names.add("web_search")
        self.registered_names.add("search_local_knowledge")
        self.registered_names.add("control_ui_layout")
        # 2. 动态加载外部插件生态 (VPM 雏形)
        self._load_external_tools()

    def _load_external_tools(self):
        """物理扫描 tools 目录，加载第三方 MCP/Agent 契约并执行防撞校验"""
        os.makedirs(self.tools_dir, exist_ok=True)
        # 1. 扫描公共工具目录 (tools/*.json)
        self._scan_folder(self.tools_dir)
        # 2. 扫描插件私有工具目录 (plugins/*/tools/*.json)
        plugins_root = os.path.join(VAULT_ROOT, "plugins")
        if os.path.exists(plugins_root):
            for plugin_name in os.listdir(plugins_root):
                plugin_path = os.path.join(plugins_root, plugin_name)
                if not os.path.isdir(plugin_path): continue
                
                # 直接读取并加载插件的“身份证” manifest.json
                manifest_file = os.path.join(plugin_path, "manifest.json")
                if os.path.exists(manifest_file):
                    self._parse_and_register_tool(manifest_file)
                
                # 兼容性保留：扫描额外的 tools 目录 (以防后续有复杂的插件拆分多个 json)
                plugin_tool_dir = os.path.join(plugin_path, "tools")
                if os.path.exists(plugin_tool_dir):
                    self._scan_folder(plugin_tool_dir)
        
    def _scan_folder(self, folder_path):
        if not os.path.exists(folder_path):
            return
        for filename in os.listdir(folder_path):
            if not filename.endswith(".json"): continue
            filepath = os.path.join(folder_path, filename)
            self._parse_and_register_tool(filepath)
   
    def _parse_and_register_tool(self, filepath):
        """ 独立解析器：从任意 JSON 文件中提取符合大模型标准的 Tool"""
        with open(filepath, 'r', encoding='utf-8') as f:
            try:
                tool_manifest = json.load(f)
                
                # 容错：处理被包在数组里的 JSON
                if isinstance(tool_manifest, dict):
                    manifests = [tool_manifest]
                elif isinstance(tool_manifest, list):
                    manifests = tool_manifest
                else:
                    return
                    
                for manifest in manifests:
                    # 必须有 function 且包含 name，否则判定为普通配置文件（不喂给大模型）
                    if "function" not in manifest or "name" not in manifest["function"]:
                        continue       
                    
                    name = manifest["function"]["name"]
                    
                    if name in self.registered_names:
                        print(f"⚠️ [警告] 发现冲突工具: {name} (文件: {os.path.basename(filepath)})。已强制隔离。")
                        self.system_warnings.append(f"工具库加载异常：发现冲突插件 '{name}'。")
                        continue
                        
                    if "type" not in manifest:
                        manifest["type"] = "function"

                    plugin_id = self._plugin_id_from_path(filepath)
                    if plugin_id:
                        declared_plugin_id = manifest.get("plugin_id")
                        if declared_plugin_id and declared_plugin_id != plugin_id:
                            print(f"⚠️ [警告] 插件 {plugin_id} 的 manifest.plugin_id 不匹配: {declared_plugin_id}。已隔离。")
                            self.system_warnings.append(f"插件契约异常：'{plugin_id}' 的 plugin_id 与目录名不一致。")
                            continue
                        manifest["plugin_id"] = plugin_id
                    normalize_manifest_security(manifest, plugin_id)

                    self.tools.append(manifest)
                    self.registered_names.add(name)
                    print(f" [VPM 挂载] 外部插件契约已就绪: {name}")

            except Exception as e:
                # 忽略普通的 json 报错（比如解析到 system_config 这种纯数据文件）
                pass

    def _plugin_id_from_path(self, filepath):
        normalized = os.path.normpath(filepath)
        parts = normalized.split(os.sep)
        if "plugins" not in parts:
            return ""
        idx = parts.index("plugins")
        if idx + 1 >= len(parts):
            return ""
        return parts[idx + 1]

    def get_tools(self):
        """直接将标准的 Tools 数组暴露给大模型接口"""
        # 如果没有任何工具，按 OpenAI 标准不能传空列表，必须返回 None
        return self.tools if self.tools else None
