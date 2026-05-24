from openai import OpenAI
import os
import json
import threading
import sys
import platform
import shutil
import time
import glob
import frontmatter
import re
import concurrent.futures
from datetime import datetime

for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

def get_vault_root():
    # 工业级路径寻址：全系统唯一的“绝对真理”
    if getattr(sys, 'frozen', False):
        # 生产环境：以打包后的 vault_engine.exe 所在的物理目录为基准
        base_dir = os.path.dirname(sys.executable)
    else:
        # 开发环境：以当前 main.py 文件所在目录为基准
        base_dir = os.path.dirname(os.path.abspath(__file__))
        
    prod_vault_path = os.environ.get("VAULT_ROOT") or os.path.join(base_dir, "vault")
    seed_candidates = [
        os.path.join(base_dir, "vault_seed"),
        os.path.join(getattr(sys, "_MEIPASS", base_dir), "vault_seed"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "vault_seed"),
    ]

    if not os.path.exists(prod_vault_path) or not os.listdir(prod_vault_path):
        os.makedirs(prod_vault_path, exist_ok=True)
        for seed_path in seed_candidates:
            if os.path.isdir(seed_path):
                print(f" [Vault Seed] Initializing clean vault from: {seed_path}")
                for item_name in os.listdir(seed_path):
                    source = os.path.join(seed_path, item_name)
                    target = os.path.join(prod_vault_path, item_name)
                    if os.path.exists(target):
                        continue
                    if os.path.isdir(source):
                        shutil.copytree(source, target)
                    else:
                        shutil.copy2(source, target)
                break

    os.makedirs(prod_vault_path, exist_ok=True)
    return prod_vault_path

VAULT_ROOT = get_vault_root()
print(f" [外脑物理锚点] 核心资产底座: {VAULT_ROOT}")

#  运行时路径嗅探器 (Audit Hook)
def path_sniffer(event, args):
    # 只要 Python 底层触发了文件打开动作
    if event == "open":
        file_path = args[0]
        if isinstance(file_path, str):
            # 命中规则 1：出现俄罗斯套娃
            if "vault/vault" in file_path.replace("\\", "/"):
                print(f" [系统探针] 抓获套娃路径: {file_path}")
            # 命中规则 2：使用了相对路径的 vault/ (在生产环境绝对不允许)
            elif not os.path.isabs(file_path) and file_path.replace("\\", "/").startswith("vault/"):
                print(f" [系统探针] 抓获未包裹 VAULT_ROOT 的野狗路径: {file_path}")

# 激活底层的监听！
sys.addaudithook(path_sniffer)

try:
    from habit_extractor import HabitExtractor
    from rag_assembler import RAGAssembler
    from chroma_engine import VaultVectorDB
    from promotion_gatekeeper import PromotionGatekeeper
    from tool_registry import ToolRegistry
    from tool_executor import ToolExecutor
except ImportError as e:
    print(f" 引擎组件缺失: {e}")
    print("请确保所有组件脚本 (.py) 都在当前目录下！")
    sys.exit(1)

class VaultOS_Terminal:
    def __init__(self):
        print(" 正在初始化 AI 算力...")
        self._boot_sequence() 
        # 1. 定义物理存储路径
        self.chat_history_path = os.path.join(VAULT_ROOT, "chat_history.json") 
        self.blackbox_path = os.path.join(VAULT_ROOT, "blackbox_raw.jsonl")
        self.config_path = os.path.join(VAULT_ROOT, "system_config.json")
        os.makedirs(VAULT_ROOT, exist_ok=True)
        # 加载大模型配置并初始化万能客户端
        self.llm_config = self._load_config()
        self._init_llm_client()
        # 2. 加载多线程记忆字典
        self.threads = self._load_threads_from_disk()
        # 3. 实例化各个核心引擎
        self.vector_db = VaultVectorDB()
        self.assembler = RAGAssembler(max_tokens=6000)
        self.extractor = HabitExtractor()
        self.gatekeeper = PromotionGatekeeper()
        self.registry = ToolRegistry()
        self.executor = ToolExecutor(self.registry, self.vector_db)
        # 4. 启动时的例行公事：晋升核准自检
        print("\n" + "="*50)
        self.gatekeeper.check_and_promote(
            llm_caller=self._call_llm_json, 
            entity_callback=self._update_entity_file
        )
        print("="*50 + "\n")

    def receive_knowledge_payload(self, payload_data):
        """提供给外部仓管 Agent 调用的接口，彻底解耦切片与入库逻辑"""
        command = payload_data.get("command")
        source_file = payload_data.get("source_file")
        new_hash = payload_data.get("hash", "unknown_hash")
        chunks = payload_data.get("payload", [])

        if command != "RAG_UPSERT" or not source_file:
            print(" [RAG 网关] 拦截到非法或不完整的载荷指令！丢弃。")
            return False
        try:
            print(f"\n [RAG 网关] 收到来自外挂仓管的更新请求: {source_file}")
            if hasattr(self.vector_db, 'delete_by_source'):
                deleted_count = self.vector_db.delete_by_source(source_file)
            else:
                deleted_count = 0
            if not chunks:
                print(f" [RAG 网关] 载荷为空，已完成该文件的彻底注销。")
                return True
            texts = []
            metadatas = []
            ids = []
            for i, chunk in enumerate(chunks):
                text_content = chunk.get("chunk_text")
                if not text_content: continue
                texts.append(text_content)
                
                meta = chunk.get("metadata", {})
                meta["source"] = source_file
                meta["file_hash"] = new_hash
                meta["ingested_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
                metadatas.append(meta)
                
                ids.append(f"rag_{new_hash}_{i}")
            if hasattr(self.vector_db, 'add_chunks'):
                self.vector_db.add_chunks(texts, metadatas, ids)
                print(f"[RAG 网关] 成功同化 {len(texts)} 块高纯度记忆碎片！\n")
                return True
            return False
        except Exception as e:
            print(f" [RAG 网关] 数据引流发生雪崩，执行中断: {e}")
            return False

    def _load_config(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    if "embed_model" not in config:
                        config["embed_model"] = "text-embedding-v4"
                        config["embed_api_key"] = ""
                        config["embed_base_url"] = "https://dashscope.aliyuncs.com/compatible-mode/v1"
                    return config
            except: pass
        default_config = {
            "api_key": "",
            "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "model_max": "qwen-max",
            "model_mini": "qwen-turbo",
            "embed_api_key": "", 
            "embed_base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "embed_model": "text-embedding-v4" 
        }
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, ensure_ascii=False, indent=2)
            print(f" [系统] 已自动生成初始配置文件: {self.config_path}")
        except Exception as e:
            print(f" [系统] 自动生成配置文件失败: {e}")  
        return default_config

    def save_config(self, new_config):
        self.llm_config = new_config
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self.llm_config, f, ensure_ascii=False, indent=2)
        print("  [系统核心] 大模型配置已更新，正在热重载引擎...")
        self._init_llm_client()

    def _init_llm_client(self):
        raw_key = self.llm_config.get("api_key", "")
        safe_key = raw_key if raw_key.strip() else "sk-placeholder"
        self.client = OpenAI(
            api_key=safe_key,
            base_url=self.llm_config.get("base_url", "https://dashscope.aliyuncs.com/compatible-mode/v1")
        )
        if hasattr(self, 'vector_db') and hasattr(self.vector_db, 'update_config'):
            self.vector_db.update_config(self.llm_config)

    def _load_threads_from_disk(self):
        if os.path.exists(self.chat_history_path):
            with open(self.chat_history_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {"global": []}
        return {"global": []}

    def _save_to_disk(self):
        with open(self.chat_history_path, 'w', encoding='utf-8') as f:
            json.dump(self.threads, f, ensure_ascii=False, indent=2)
    
    def _write_to_blackbox(self, role, content):
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        log_entry = {"timestamp": timestamp, "role": role, "content": content}
        with open(self.blackbox_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

    def _extract_profile_value(self, traits, patterns):
        for trait in traits:
            trait_text = str(trait)
            for pattern in patterns:
                match = re.search(pattern, trait_text, flags=re.IGNORECASE)
                if match:
                    return match.group(1)
        return None

    def _read_entity_profile_text(self, entity_name):
        entity_path = None
        if hasattr(self, "gatekeeper") and hasattr(self.gatekeeper, "get_entity_path"):
            entity_path = self.gatekeeper.get_entity_path(entity_name)
        if not entity_path:
            entity_path = os.path.join(VAULT_ROOT, "knowledge", "entities", f"{entity_name}.md")
        if not os.path.exists(entity_path):
            return ""
        try:
            with open(entity_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            return ""

    def _looks_like_recommendation_request(self, text):
        text = str(text or "")
        return bool(re.search(r"(推荐|建议|适合|送|礼物|买|购买|选|选择|吃饭|吃什么|去哪|旅行|旅游|安排)", text))

    def _build_memory_prefetch_context(self, user_input):
        """回答前按需读取本地画像与相关实体，避免全量实体泄漏。"""
        context_parts = []
        loaded_entities = []
        is_recommendation = self._looks_like_recommendation_request(user_input)

        if is_recommendation:
            try:
                with open(self.gatekeeper.profile_path, "r", encoding="utf-8") as f:
                    profile_data = json.load(f)
                if profile_data:
                    context_parts.append(
                        "【回答前本地画像预读 - Boss】\n"
                        "以下画像只用于理解 Boss 的预算倾向、表达偏好和决策风格；"
                        "如果问题对象是他人，禁止把 Boss 的个人偏好套用给该实体。\n"
                        f"{json.dumps(profile_data, ensure_ascii=False)}"
                    )
            except Exception as e:
                print(f" [记忆预读] Boss 画像读取异常: {e}")

        try:
            if hasattr(self.gatekeeper, "resolve_entities"):
                matched_entities = self.gatekeeper.resolve_entities(user_input)
            else:
                matched_entities = []
            for entity_name in matched_entities:
                content = self._read_entity_profile_text(entity_name)
                if content:
                    context_parts.append(
                        f"【实体专属事实源 - {entity_name}】\n"
                        f"以下内容是回答“{entity_name}”相关问题的最高优先级事实源。"
                        "如果用户询问该实体，只能依据本档案回答；档案没有记录时，必须说本地实体档案暂无记录，禁止套用 Boss 自己的画像或模型常识。\n"
                        f"{content}"
                    )
                else:
                    context_parts.append(
                        f"【实体专属事实源 - {entity_name}】\n"
                        "本地实体档案暂无记录。回答该实体问题时，禁止套用 Boss 自己的画像或模型常识。"
                    )
                loaded_entities.append(entity_name)
        except Exception as e:
            print(f" [记忆预读] 实体档案读取异常: {e}")

        if loaded_entities:
            print(f" [记忆预读] 已挂载相关实体档案: {', '.join(loaded_entities)}")
        elif is_recommendation:
            print(" [记忆预读] 已挂载 Boss 画像用于建议类问题。")

        return "\n\n".join(context_parts)

    def _detect_local_profile_query(self, user_input):
        text = str(user_input or "")
        if not re.search(r"(\?|？|什么|谁|哪|哪里|多少|为什么|怎么|如何|吗|呢)", text):
            return None

        target = "Boss"
        if hasattr(self, "gatekeeper"):
            for canonical, aliases in self.gatekeeper.ENTITY_ALIASES.items():
                if canonical in text or any(alias in text for alias in aliases):
                    target = canonical
                    break

        if re.search(r"(名字|姓名|叫什么|叫啥|我是谁)", text):
            return {"target": target, "slot": "name"}
        if "水果" in text or "吃什么" in text:
            return {"target": target, "slot": "fruit"}
        if "动物" in text:
            return {"target": target, "slot": "animal"}
        if "编程语言" in text:
            return {"target": target, "slot": "programming_language"}
        if "交通方式" in text or "出行" in text:
            return {"target": target, "slot": "transport"}
        return None

    def _answer_local_profile_query(self, query):
        target = query.get("target")
        slot = query.get("slot")
        if target != "Boss":
            content = self._read_entity_profile_text(target)
            if not content:
                return f"本地实体档案暂无记录：{target}。"
            patterns = {
                "fruit": [r"(?:喜欢吃|爱吃)([\u4e00-\u9fffA-Za-z0-9、和]+)"],
                "name": [r"(?:名字|姓名|叫)(?:是|为)?([\u4e00-\u9fffA-Za-z0-9·.\-]+)"],
            }.get(slot, [])
            value = self._extract_profile_value([content], patterns)
            if not value:
                return f"本地实体档案暂无记录：{target}。"
            if slot == "fruit":
                return f"您的{target}喜欢吃{value}。"
            if slot == "name":
                return f"{target}的名字是{value}。"
            return f"本地实体档案暂无记录：{target}。"

        try:
            with open(self.gatekeeper.profile_path, "r", encoding="utf-8") as f:
                profile = json.load(f)
        except Exception:
            profile = {}
        interests = profile.get("interests", []) if isinstance(profile, dict) else []
        facts = profile.get("facts", []) if isinstance(profile, dict) else []
        coding_style = profile.get("coding_style", []) if isinstance(profile, dict) else []

        if slot == "fruit":
            value = self._extract_profile_value(interests, [
                r"最爱吃的水果是([\u4e00-\u9fffA-Za-z0-9、和]+)",
                r"最喜欢吃的水果是([\u4e00-\u9fffA-Za-z0-9、和]+)",
                r"最喜欢的水果是([\u4e00-\u9fffA-Za-z0-9、和]+)",
                r"喜欢吃([\u4e00-\u9fffA-Za-z0-9、和]+)",
            ])
            return f"您最喜欢吃的水果是{value}。" if value else "本地画像暂无记录：喜欢吃什么水果。"
        if slot == "name":
            value = self._extract_profile_value(facts, [
                r"(?:用户的名字是|真实姓名是|名字叫|姓名是)([\u4e00-\u9fffA-Za-z0-9·.\-]+)",
            ])
            return f"您的名字是{value}。" if value else "本地画像暂无记录：名字。"
        if slot == "animal":
            value = self._extract_profile_value(interests, [
                r"最喜欢的动物是([\u4e00-\u9fffA-Za-z0-9、和]+)",
            ])
            return f"您最喜欢的动物是{value}。" if value else "本地画像暂无记录：喜欢什么动物。"
        if slot == "programming_language":
            value = self._extract_profile_value(coding_style + interests, [
                r"喜欢使用([\u4e00-\u9fffA-Za-z0-9#+.、和]+)",
                r"喜欢([\u4e00-\u9fffA-Za-z0-9#+.、和]+)",
            ])
            return f"您喜欢的编程语言是{value}。" if value else "本地画像暂无记录：喜欢什么编程语言。"
        if slot == "transport":
            value = self._extract_profile_value(interests, [
                r"(?:出行喜欢|喜欢)(乘坐[\u4e00-\u9fffA-Za-z0-9、和]+出行|乘坐[\u4e00-\u9fffA-Za-z0-9、和]+)",
            ])
            return f"您出行喜欢{value}。" if value else "本地画像暂无记录：喜欢什么交通方式。"
        return None

    def get_response(self, user_input: str, thread_id: str = "global", display_message: str = None) -> str:
        if not self.llm_config.get("api_key"):
            return " [系统提醒] 核心引擎尚未激活。请前往「引擎设置」配置您的 API Key。"
        if display_message is None:
            display_message = user_input
        try:
            print(f" [收到指令] 正在思考: {display_message} (线程: {thread_id})")   
            if display_message.lower() == '/audit':
                with self.gatekeeper.memory_lock:
                    self.gatekeeper.check_and_promote(
                        llm_caller=self._call_llm_json,
                        entity_callback=self._update_entity_file
                    )
                return " [系统动作] 审计完毕：暗影碎片已完成提纯与画像晋升。"

            local_profile_query = self._detect_local_profile_query(display_message)
            if local_profile_query:
                answer = self._answer_local_profile_query(local_profile_query)
                if answer:
                    print(" [本地画像查询] 已由 Python 确定性读取返回，跳过记忆写入与主模型推理。")
                    self.threads.setdefault(thread_id, [])
                    self.threads[thread_id].append({'role': 'user', 'content': display_message})
                    self.threads[thread_id].append({'role': 'assistant', 'content': answer})
                    self._save_to_disk()
                    self._write_to_blackbox(f"{thread_id}_boss", display_message)
                    self._write_to_blackbox(f"{thread_id}_butler", answer)
                    return answer
                
            print(" [暗影守护者] 正在扫描用户输入提取习惯...")
            def _shadow_pipeline():
                current_history = self.threads.get(thread_id, []).copy()
                caller_with_memory = lambda p, u: self._mock_llm_for_extractor(p, u, chat_history=current_history)
                
                with self.gatekeeper.memory_lock:
                    self.extractor.analyze_input(display_message, caller_with_memory, chat_history=current_history)
                    self.gatekeeper.check_and_promote(
                        llm_caller=self._call_llm_json,
                        entity_callback=self._update_entity_file
                    )
            threading.Thread(target=_shadow_pipeline).start()

            prefetch_context = self._build_memory_prefetch_context(display_message)

            blueprint = self._compile_jit_task(display_message, prefetch_context=prefetch_context)
            status = blueprint.get("plan_status", "DIRECT_CHAT")
            print(f" [编译决断]: {status} | 理由: {blueprint.get('reasoning')}")
            
            retrieved_context = prefetch_context
            if status == "NEEDS_NEW_TOOLS":
                suggestion = blueprint.get("suggestion_msg", "Boss，我缺少完成此任务的工具。")
                missing = ", ".join(blueprint.get("missing_capabilities", []))
                print(f" [能力探针] 发现缺失能力: {missing}")
                answer = f" [Vault OS 架构建议]:\n{suggestion}\n\n(系统检测到缺失核心组件：{missing}。您可以前往 VPM 插件中心挂载相关能力后，再次下达该指令。)"
                self._save_to_disk()
                return answer
                
            elif status == "READY":
                print(" [DAG 引擎] 图纸审核通过，正在初始化系统黑板...")
                steps = blueprint.get("steps", [])
                blackboard = {key: None for key in blueprint.get("blackboard_keys", [])}
                bb_lock = threading.Lock()
                step_futures = {}
                
                def run_step(step_data):
                    tool_name = step_data.get("tool_name")
                    raw_args = step_data.get("args", {})
                    output_key = step_data.get("output_to_blackboard")
                    # 核心防线：动态参数解析 (主引擎负责把黑板数据喂给插件)
                    resolved_args = {}
                    with bb_lock:
                        for k, v in raw_args.items():
                            # 如果参数值是以 $$ 开头的字符串，说明需要去黑板取值
                            if isinstance(v, str) and v.startswith("$$"):
                                bb_key = v[2:]
                                resolved_args[k] = blackboard.get(bb_key, v) # 取不到就保留原值
                            else:
                                resolved_args[k] = v
                    
                    print(f"   -> [并发激活] 委派任务至: {tool_name} ...")
                    class MockToolCall:
                        class MockFunction:
                            def __init__(self, name, arguments):
                                self.name = name
                                self.arguments = arguments
                        def __init__(self, name, arguments):
                            self.function = self.MockFunction(name, arguments)
                    step_result = self.executor.execute(MockToolCall(tool_name, json.dumps(resolved_args)))
                    if output_key:
                        with bb_lock:
                            blackboard[output_key] = step_result
                        print(f"   -> [黑板更新] 已写入共享变量: {output_key}")
                        
                with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
                    pending_steps = steps.copy()
                    completed_step_ids = set()
                    submitted_step_ids = set()
                    
                    while pending_steps:
                        progress_made = False
                        for step in pending_steps[:]:
                            step_id = step.get("step_id")
                            depends_on = step.get("depends_on", [])
                            if isinstance(depends_on, str): depends_on = [depends_on]
                            if all(dep in completed_step_ids for dep in depends_on):
                                if step_id not in submitted_step_ids:
                                    step_futures[step_id] = pool.submit(run_step, step)
                                    submitted_step_ids.add(step_id)
                                    pending_steps.remove(step)
                                    progress_made = True
                        if step_futures:
                            not_done = [f for sid, f in step_futures.items() if sid not in completed_step_ids]
                            if not_done:
                                concurrent.futures.wait(not_done, return_when=concurrent.futures.FIRST_COMPLETED)
                                for sid, f in step_futures.items():
                                    if f.done() and sid not in completed_step_ids:
                                        completed_step_ids.add(sid)
                        if not progress_made and not [f for sid, f in step_futures.items() if not f.done()]:
                            print(" [DAG 引擎] 警告：发现无法满足的依赖逻辑环，强制中止剩余蓝图！")
                            break 
                if any(step.get("tool_name") == "control_ui_layout" for step in steps):
                    answer = "已为您开启。"
                    self.threads[thread_id].append({'role': 'user', 'content': display_message})
                    self.threads[thread_id].append({'role': 'assistant', 'content': answer})
                    self._save_to_disk()
                    return answer
                # 新增：Token 防爆墙，对黑板中的超大文本进行静默截断
                safe_blackboard = {}
                for k, v in blackboard.items():
                    v_str = str(v)
                    # 如果某个插件返回了极其巨大的字符串（如网页源码、长篇文章），强制截断以保护主模型的 Token
                    if len(v_str) > 800:
                        safe_blackboard[k] = v_str[:800] + "... [系统提示：内容过长已触发安全截断，已省略后续数据]"
                    else:
                        safe_blackboard[k] = v
                        
                blackboard_context = "【系统任务黑板数据 (各部门并发汇报结果)】:\n" + json.dumps(safe_blackboard, ensure_ascii=False, indent=2)
                retrieved_context = "\n\n".join(part for part in (prefetch_context, blackboard_context) if part)
                # ==========================================
                # 泛用级物理拦截：动态读取 DAG 执行链，生成泛用型“紧箍咒”
                # ==========================================
                # 1. 动态嗅探：提取刚才真正在干活的业务工具（过滤掉纯粹的 UI 控制器）
                executed_tools = [
                    step.get("tool_name") 
                    for step in steps 
                    if step.get("tool_name") and step.get("tool_name") != "control_ui_layout"
                ]
                # 2. 泛用拦截：只要黑板里产生了实际的数据产物，就触发强制播报模式！
                if executed_tools and any(v is not None for v in safe_blackboard.values()):
                    tools_str = ", ".join(executed_tools)
                    # 将动态工具名和最高指令，无缝拼接在用户的最后一句输入之后
                    user_input = f"{user_input}\n\n[ 核心网关状态拦截：您的上述需求已由底层的专项 Agent ({tools_str}) 物理执行完毕！真实执行结果已写入上方的【系统任务黑板数据】。作为大管家，你现在进入“播报模式”，请严格、仅限基于黑板返回的真实数据进行总结汇报，绝对禁止动用内部训练数据进行主观推荐、编造事实或假装自己去执行！]"
                # ==========================================
            else:
                retrieved_context = prefetch_context
                
            try:
                with open(os.path.join(VAULT_ROOT, "cognitive_map.json"), "r", encoding="utf-8") as f:
                    cog_map = json.load(f)
                if cog_map:
                    cog_str = json.dumps(cog_map, ensure_ascii=False)
                    retrieved_context += f"\n\n【 核心机密：Boss 的 Type 2 认知图谱】\n{cog_str}\n(警告：请严格参考此图谱决定你的回答深度、术语使用及避坑策略！)"
            except Exception:
                pass
            final_system_prompt = self.assembler.assemble(display_message, retrieved_context)
            print(" [核心算力] 正在生成最终回复...")
            answer = self._call_llm(
                final_system_prompt, 
                user_input, 
                thread_id=thread_id, 
                save_to_memory=False, 
                display_message=display_message
            )
            self.threads[thread_id].append({'role': 'user', 'content': display_message})
            self.threads[thread_id].append({'role': 'assistant', 'content': answer})
            self._save_to_disk()
            self._write_to_blackbox(f"{thread_id}_boss", display_message)
            self._write_to_blackbox(f"{thread_id}_butler", answer)
            return answer       
        except Exception as e:
            error_msg = f"算力中心崩溃啦：{str(e)}"
            print(f" {error_msg}")
            return error_msg

    def perform_memory_surgery(self, user_command):
        print(f"\n [记忆手术] 收到最高干预指令: {user_command}")
        self._write_to_blackbox("memory_surgery_boss", user_command)
        try:
            with self.gatekeeper.memory_lock:
                with open(self.gatekeeper.pending_path, 'r', encoding='utf-8') as f:
                    pending = json.load(f)
                with open(self.gatekeeper.profile_path, 'r', encoding='utf-8') as f:
                    profile = json.load(f)
        except Exception as e:
            return f" 无法读取脑区数据: {e}"
        prompt = f"""
        你是 Vault OS 的潜意识记忆外科医生。
        【当前等待裁决的冲突队列】：{json.dumps(pending.get('queue', []), ensure_ascii=False)}
        【当前的基岩画像】：{json.dumps(profile, ensure_ascii=False)}

        创造者（Boss）发出了最高手术指令："{user_command}"
        
        【核心防线】：
        对于已经处理/缝合的冲突条目，绝不能从队列中删除！你必须将它们的 "status" 字段严格修改为 "MERGED" (同化生效) 或 "REJECTED" (驳回)，以保留为历史档案。只有需要等待 Boss 决断的才标记为 PENDING。

        【要求】：修改上述 JSON。输出格式必须为：
        {{
            "updated_queue": [...],
            "updated_profile": {{...}},
            "reply": "汇报手术结果（50字内）"
        }}
        """
        try:
            response = self.client.chat.completions.create(
                model=self.llm_config.get("model_max", "qwen-max"), 
                messages=[{'role': 'system', 'content': prompt}]
            )
            content = response.choices[0].message.content
            result_json = self._parse_json_robust(content)
            
            if result_json and "updated_queue" in result_json:
                with self.gatekeeper.memory_lock:
                    with open(self.gatekeeper.pending_path, 'w', encoding='utf-8') as f:
                        json.dump({"queue": result_json["updated_queue"]}, f, ensure_ascii=False, indent=2)
                    with open(self.gatekeeper.profile_path, 'w', encoding='utf-8') as f:
                        json.dump(result_json["updated_profile"], f, ensure_ascii=False, indent=2)
                print(f" [记忆手术] 成功: {result_json.get('reply')}")
                return result_json.get("reply", "神经链路重塑完毕。")
            else:
                return " 手术中止：大模型未能按标准格式完成缝合。"        
        except Exception as e:
            print(f" [记忆手术] 致命错误: {e}")
            return " 脑区链接断开，手术失败。"

    def resolve_memory_conflict(self, memory_id, decision):
        """确定性处理单条待决冲突，避免简单同意/拒绝走大模型手术。"""
        if decision not in {"accept", "reject"}:
            return {"ok": False, "message": " 冲突处理失败：未知裁决动作。"}
        if not memory_id:
            return {"ok": False, "message": " 冲突处理失败：缺少记忆 ID。"}

        try:
            with self.gatekeeper.memory_lock:
                with open(self.gatekeeper.pending_path, 'r', encoding='utf-8') as f:
                    pending_data = json.load(f)
                queue = pending_data.get("queue", []) if isinstance(pending_data, dict) else pending_data
                if not isinstance(queue, list):
                    queue = []

                target = next((item for item in queue if item.get("id") == memory_id), None)
                if not target:
                    return {"ok": False, "message": " 冲突处理失败：找不到对应记忆。"}
                if target.get("status") != "PENDING" or target.get("type") != "CONFLICT":
                    return {"ok": False, "message": " 冲突处理失败：该记忆不是待决冲突。"}

                if decision == "accept":
                    category = target.get("category")
                    old_trait = target.get("old_trait")
                    new_trait = target.get("new_trait")
                    with open(self.gatekeeper.profile_path, 'r', encoding='utf-8') as f:
                        profile = json.load(f)
                    if not isinstance(profile, dict) or not isinstance(profile.get(category), list):
                        return {"ok": False, "message": " 冲突处理失败：画像分类不存在或格式异常。"}
                    if old_trait in profile[category]:
                        profile[category].remove(old_trait)
                    if new_trait and new_trait not in profile[category]:
                        profile[category].append(new_trait)
                    target["status"] = "MERGED"
                    with open(self.gatekeeper.profile_path, 'w', encoding='utf-8') as f:
                        json.dump(profile, f, ensure_ascii=False, indent=2)
                    event_type = "FAST_CONFLICT_ACCEPTED"
                    message = " 已同意修改：新记忆已写入。"
                else:
                    target["status"] = "REJECTED"
                    event_type = "FAST_CONFLICT_REJECTED"
                    message = " 已拒绝修改：旧记忆已保留。"

                with open(self.gatekeeper.pending_path, 'w', encoding='utf-8') as f:
                    json.dump({"queue": queue}, f, ensure_ascii=False, indent=2)
                self.gatekeeper._write_blackbox(event_type, target)
                return {"ok": True, "message": message, "queue": queue}
        except Exception as e:
            print(f" [记忆快裁] 处理失败: {e}")
            return {"ok": False, "message": f" 冲突处理失败：{e}"}
    
    def _update_entity_file(self, entity_name, new_trait):
        if not new_trait:
            return
        if hasattr(self, "gatekeeper") and hasattr(self.gatekeeper, "sanitize_entity_name"):
            entity_name = self.gatekeeper.sanitize_entity_name(entity_name)
        if not entity_name or entity_name == "Boss":
            print(f" [实体防线] 已拦截非法实体档案目标: {entity_name}")
            return
        entity_dir = os.path.join(VAULT_ROOT, "knowledge", "entities")
        os.makedirs(entity_dir, exist_ok=True)
        file_path = os.path.join(entity_dir, f"{entity_name}.md")
        lock = getattr(getattr(self, "gatekeeper", None), "memory_lock", threading.RLock())
        
        with lock:
            if not os.path.exists(file_path):
                final_content = f"---\ntitle: {entity_name} 的核心画像\ncategory: EntityProfile\n---\n\n## 基础情报\n- {new_trait}\n"
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(final_content)
                if hasattr(self.gatekeeper, "refresh_entity_index"):
                    self.gatekeeper.refresh_entity_index()
                print(f" [实体档案] 已为 {entity_name} 建立初始卷宗。")
            else:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        old_content = f.read()

                    # 【架构升级】：引入高强度语义排他性检测的合并器 Prompt
                    prompt = f"""
                    你是 Vault OS 的专属档案整理专家。
                    你需要将新收集到的碎片情报，无缝且合乎逻辑地融入该实体的现有 Markdown 档案中。

                    【实体名称】：{entity_name}
                    【现有档案内容】：
                    {old_content}

                    【需要合入的新情报】："{new_trait}"

                    【最高修改法则】：
                    1. 语义排他性检测（冲突覆盖）：仔细对比新情报与现有情报。如果新情报与旧情报属于“互斥”或“同类属性更替”（例如：原本喜欢苹果，现在说喜欢哈密瓜；或者原本住北京，现在住上海），你必须【物理抹除】旧的属性记录，只保留新情报！绝对禁止出现“既喜欢苹果又喜欢哈密瓜”的自相矛盾罗列。
                    2. 知识增量（补充追加）：只有当新情报是一个完全不相关的全新维度（比如原来只记录了职业，新情报是爱好）时，才作为新的一行无序列表追加。
                    3. 格式洁癖：必须完整保留文件头部的 --- frontmatter --- 和所有 Markdown 标题结构，只精确修改正文的内容。

                    请直接输出修改完毕的完整 Markdown 文本，绝不允许包含任何解释性文字或 ```markdown 标记。
                    """

                    # 算力升级：从 model_mini 切换到 model_max，确保合并逻辑严密
                    response = self.client.chat.completions.create(
                        model=self.llm_config.get("model_max", "qwen-max"),
                        messages=[{"role": "user", "content": prompt}]
                    )

                    new_content = response.choices[0].message.content
                    # 增强型正则表达式：暴力剔除任何可能带有语言标识的代码块包装
                    new_content = re.sub(r'^```[a-zA-Z]*\n|```$', '', new_content.strip(), flags=re.MULTILINE)
                    if not new_content:
                        print(f" [实体档案] 模型返回空内容，已保护 {entity_name} 原档案不被覆盖。")
                        return
                    if not new_content.lstrip().startswith("---") or new_content.count("---") < 2:
                        print(f" [实体档案] 模型输出缺少 frontmatter，已保护 {entity_name} 原档案不被覆盖。")
                        return

                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    if hasattr(self.gatekeeper, "refresh_entity_index"):
                        self.gatekeeper.refresh_entity_index()
                    print(f" [实体档案] {entity_name} 的卷宗已完成深度清洗与覆写。")
                except Exception as e:
                    print(f" 实体档案覆写失败: {e}")

    def _scan_md_folder(self, folder_pattern):
        items = []
        files = glob.glob(folder_pattern)
        for file_path in files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    post = frontmatter.load(f)
                    file_stat = os.stat(file_path)
                    stored_time = file_stat.st_mtime 
                    items.append({
                        "id": post.get('id', os.path.basename(file_path)),
                        "title": post.get('title', '无标题笔记'),
                        "summary": post.get('summary', '暂无内容摘要...'),
                        "author": post.get('author', 'System'),
                        "time_str": time.strftime("%Y-%m-%d %H:%M", time.localtime(stored_time)),
                        "timestamp": stored_time,
                        "source_url": post.get('source_url', ''),
                        "file_path": file_path,
                        "keywords": post.get('keywords', post.get('tags', []))
                    })
            except:pass
        items.sort(key=lambda x: x['timestamp'], reverse=True)
        return items

    def get_local_news_list(self):
        inbox_dir = os.path.join(VAULT_ROOT, "knowledge", "inbox")
        os.makedirs(inbox_dir, exist_ok=True)
        return self._scan_md_folder(os.path.join(inbox_dir, "*.md"))

    def get_favorite_list(self):
        fav_dir = os.path.join(VAULT_ROOT, "knowledge", "favorites")
        os.makedirs(fav_dir, exist_ok=True)
        return self._scan_md_folder(os.path.join(fav_dir, "*.md"))
    
    def get_note_content(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                post = frontmatter.load(f)
                return post.content
        except Exception as e:
            return f"读取内容失败: {str(e)}"

    def _boot_sequence(self):
        os.system('cls' if os.name == 'nt' else 'clear')
        boot_msgs = [
            "Initializing Vault OS Kernel...",
            "Loading Layer 3 Core Profile...",
            "Mounting ChromaDB Vector Space...",
            "Waking up Shadow Observer Daemon...",
            "System Online. Welcome back, Boss."
        ]
        for msg in boot_msgs:
            print(f" [SYSTEM] {msg}")
            time.sleep(0.3)

    # 纯净版 _call_llm (管家只需看黑板说话，严禁私自调工具！)
    def _call_llm(self, system_prompt, user_input, thread_id="global", save_to_memory=True, display_message=None):
        current_time_str = datetime.now().strftime("%Y年%m月%d日 %H:%M")
        core_profile = ""
        try:
            with open(self.gatekeeper.profile_path, 'r', encoding='utf-8') as f:
                profile_data = json.load(f)
                if profile_data and len(str(profile_data)) > 15:
                    core_profile = json.dumps(profile_data, ensure_ascii=False)
        except Exception:
            pass

        if core_profile:
            profile_strategy = f"""
【 最高权重：基岩画像驱动】
以下是 Boss 的核心基岩画像与偏好设置：
{core_profile}
        
**指令执行优先级**：
你不是普通的聊天助手，你是基于上述【基岩画像】运行的专属管家。
- 你在决定语气、代码风格、建议策略时，必须 100% 遵从基岩画像。
- 如果短期对话的内容与基岩画像发生冲突，永远、绝对以【基岩画像】为准！
- 但当系统提示中出现【实体专属事实源】且用户正在询问该实体时，实体档案是该实体问题的最高事实源；禁止把 Boss 自己的偏好迁移给该实体。
"""
        else:
            profile_strategy = """
【🌱 当前状态：基岩画像收集中】
Boss 的专属基岩画像尚未完全建立。请暂时以一个高度专业、灵活的通用 AI 管家身份运行。
"""
        
        cognitive_firewall = f"""
=========================
【Vault OS 底层认知防火墙】
1. [绝对时间锚点]：系统当前的真实时间是 {current_time_str}。
2. [反幻觉铁律]：当回答涉及“最新”、“现在”、“版本”的问题时，绝对禁止使用你的内部训练数据！
3. [工具失败应对]：当系统黑板返回“执行失败”、“找不到”、“为空”等报错信息时，你必须直接如实向 Boss 汇报缺失，【绝对禁止】为了讨好 Boss 而动用训练数据去编造或推荐任何外部内容（如推荐歌曲、电影等）；如果搜索工具无结果，如实回答，绝对禁止编造虚假的年份或版本号！你的回答必须 100% 忠于本地库的真实情况。
{profile_strategy}
=========================
"""
        enhanced_system_prompt = system_prompt + cognitive_firewall

        if display_message is None: display_message = user_input
        messages = [{'role': 'system', 'content': enhanced_system_prompt}]
        if thread_id not in self.threads: self.threads[thread_id] = []
        messages.extend(self.threads[thread_id][-6:])
        messages.append({'role': 'user', 'content': user_input})

        try:
            #  彻底移除了 tools 和 tool_choice 参数！管家现在是个纯粹的语言生成器！
            api_params = {
                "model": self.llm_config.get("model_max", "qwen-max"), 
                "messages": messages
            }
                
            response = self.client.chat.completions.create(**api_params, timeout=30)
            raw_content = response.choices[0].message.content
            answer = raw_content if raw_content else "【系统提示：管家思考完毕，但未返回任何实质内容。】"

            if save_to_memory:
                self.threads[thread_id].append({'role': 'user', 'content': display_message})
                self.threads[thread_id].append({'role': 'assistant', 'content': answer})
                self._save_to_disk()
                self._write_to_blackbox(f"{thread_id}_boss", display_message)
                self._write_to_blackbox(f"{thread_id}_butler", answer)
            return answer
        except Exception as e:
            error_msg = f" API 调用异常或超时，请检查配置: {str(e)}"
            print(error_msg)
            return error_msg

    def _parse_json_robust(self, text):
        if not text: return None
        text = text.strip()
        try:
            # 1. 优先尝试直接解析
            return json.loads(text)
        except Exception:
            pass
        try:
            match = re.search(r'```json\s*(\{.*?\}|\[.*?\])\s*```', text, re.DOTALL)
            if match:
                return json.loads(match.group(1).strip())
        except Exception:
            pass
        try:
            # 3. 物理切片：寻找最外层的 {} 或 []，彻底免疫大模型的前言后语
            start_dict = text.find('{')
            end_dict = text.rfind('}')
            start_list = text.find('[')
            end_list = text.rfind(']')
            
            if start_dict != -1 and end_dict != -1 and (start_list == -1 or start_dict < start_list):
                return json.loads(text[start_dict:end_dict+1])
            elif start_list != -1 and end_list != -1:
                return json.loads(text[start_list:end_list+1])
        except Exception as e:
            print(f" [底层JSON脱壳异常]: {e}")
            return None

    def _compile_jit_task(self, user_input: str, prefetch_context: str = "") -> dict:
        print(" [JIT 编译器] 正在为复杂任务绘制动态执行蓝图...")
        # 让 CEO (JIT编译器) 也拥有时间观念
        current_time_str = datetime.now().strftime("%Y年%m月%d日")
        current_tools = self.registry.get_tools()
        if current_tools:
            tool_specs = [
                {
                    "name": t['function']['name'],
                    "description": t['function']['description'],
                    "parameters": t['function'].get('parameters', {})
                }
                for t in current_tools
            ]
        else:
            tool_specs = ["无可用工具"]
        
        prompt = f"""
        你是 Vault OS 的 JIT 任务编译器 (CEO)。今天的时间是 {current_time_str}。
        主人的当前任务是: "{user_input}"

        【回答前本地记忆预读】:
        {prefetch_context if prefetch_context else "本轮没有命中需要预读的实体档案或建议类画像。"}
        
        【你当前可用的工具 (手下的总监) 及其参数说明】: 
        {json.dumps(tool_specs, ensure_ascii=False)}
        
        【你的任务】：评估任务所需的能力。
        第一步：判断主人的指令意图。
               - 如果主人只是在闲聊、分享个人生活、陈述事实或表达喜好（例如：“我父亲喜欢吃西瓜”、“今天天气好”、“我平时爱看书”）：
                 【立刻停止思考工具！】底层暗影进程会自动提取记忆。你必须直接返回：{{"plan_status": "DIRECT_CHAT"}}
        第二步：如果主人明确下达了需要操作的指令（如播放音乐、查询网络、操控系统），才去匹配上方工具。
               - 如果有工具可以满足需求 -> 返回 "READY" 并规划 steps。
               - 如果没有任何工具能做到 -> 返回 "NEEDS_NEW_TOOLS"。
               - 如果是推荐、送礼、购买、旅行、吃饭等建议类问题，且需要最新趋势、价格、新闻或时效信息，可以调用 web_search；但搜索只能补充候选，不能覆盖上方本地记忆预读。

        【强制输出 JSON 格式】：
        必须严格输出以下格式的 JSON，不要包含任何多余文字：
        {{
            "plan_status": "READY" | "NEEDS_NEW_TOOLS" | "DIRECT_CHAT",
            "missing_capabilities": ["缺失的能力描述"],
            "suggestion_msg": "向 Boss 汇报的一句话建议",
            "blackboard_keys": ["需要记录在黑板上的变量名"],
            "steps": [
                {{
                    "step_id": "s1",
                    "tool_name": "对应工具的准确 name",
                    "args": {{"参数名": "参数值"}}, 
                    "output_to_blackboard": "必须起一个英文字段名，绝对不能为 null！"
                }},
                {{
                    "step_id": "s2",
                    "depends_on": ["s1"],
                    "tool_name": "另一个工具",
                    "args": {{"file_data": "$$s1的输出变量名"}}, 
                    "output_to_blackboard": "必须起一个英文字段名，绝对不能为 null！"
                }}
            ],
            "reasoning": "一句话解释你的规划逻辑"
        }}
        """
        try:
            response = self.client.chat.completions.create(
                model=self.llm_config.get("model_max", "qwen-max"),
                messages=[{"role": "system", "content": prompt}],
                timeout=10
            )
            content = response.choices[0].message.content
            parsed = self._parse_json_robust(content)
            if parsed and "plan_status" in parsed:
                return parsed
            return {"plan_status": "DIRECT_CHAT"}
        except Exception as e:
            print(f" [JIT 编译器] 脑区故障，降级为直连: {e}")
            return {"plan_status": "DIRECT_CHAT"}

    def _mock_llm_for_extractor(self, prompt, user_input, chat_history=None):
        strict_prompt = prompt + """\n\n【系统最高防线】：
1. 必须输出合法的纯 JSON 格式！绝不允许包含前言后语。
2. 【行为与事实的物理隔离】：提问、查询、下达指令等瞬时交互，绝对没有记忆价值！必须强制输出 {"action": "IGNORE"}。只有陈述客观事实、喜好、纠错才允许提取。
3. 【强制 Schema】action 必须是 IGNORE、SELF_PROFILE_UPDATE、ENTITY_UPDATE、COGNITIVE_UPDATE 之一。
   - 描述创造者本人：{"action": "SELF_PROFILE_UPDATE", "category": "facts|interests|communication|coding_style", "trait": "..."}
   - 描述其他人或事物：{"action": "ENTITY_UPDATE", "entity": "标准称呼", "trait": "..."}
   - 描述技术栈、项目状态、领域卡点：{"action": "COGNITIVE_UPDATE", "domain": "领域名", "new_cognition": {"current_bottlenecks": [], "mental_model": "", "actionable_insight": ""}}

【Few-Shot 标准输出示例】（必须严格照做）：
=== 正例：事实陈述与纠错 ===
用户输入："我出行喜欢做飞机"
输出：{"action": "SELF_PROFILE_UPDATE", "category": "interests", "trait": "出行喜欢乘坐飞机"}

用户输入："不对，她喜欢吃哈密瓜"
输出：{"action": "ENTITY_UPDATE", "entity": "母亲", "trait": "喜欢吃哈密瓜"}

用户输入："Tauri 的 UI 真难写，我卡在窗口通信上"
输出：{"action": "COGNITIVE_UPDATE", "domain": "Tauri", "new_cognition": {"current_bottlenecks": ["窗口通信"], "mental_model": "Boss 正在处理 Tauri UI 与窗口通信问题", "actionable_insight": "回答时优先给出 Tauri v2 桌面端可落地方案"}}

=== 反例：提问与瞬时交互（极度重要，绝不允许提取！） ===
用户输入："我父亲喜欢什么水果？"
输出：{"action": "IGNORE"}

用户输入："帮我查一下北京的天气"
输出：{"action": "IGNORE"}
"""
        
        strict_prompt += """

【实体画像隔离补充规则】
1. “我父亲喜欢吃西瓜”必须输出 {"action": "ENTITY_UPDATE", "entity": "父亲", "trait": "喜欢吃西瓜"}，绝不能写成 Boss/用户事实。
2. “我喜欢吃西瓜”才允许输出 {"action": "SELF_PROFILE_UPDATE", "category": "interests", "trait": "喜欢吃西瓜"}。
3. 如果一句话同时包含 Boss 和他人事实，输出 JSON 数组，分别给 Boss 与对应实体。
4. “真实姓名/名字/我叫”属于 Boss 的高优先级单值身份事实；如果与历史姓名不同，后端会强制转为冲突等待确认。
5. 只能从最后一条用户输入提取新事实；历史对话只用于理解“她/他/这个”等代词，绝不能把历史或 assistant 回复内容当作新记忆。
"""

        messages = [{'role': 'system', 'content': strict_prompt}]
        messages.append({'role': 'user', 'content': user_input})
        
        try:
            response = self.client.chat.completions.create(
                model=self.llm_config.get("model_mini", "qwen-turbo"),
                messages=messages
            )
            content = response.choices[0].message.content
            print(f" [提取器原始输出]: {content.strip()}")
            parsed = self._parse_json_robust(content) 
            if not parsed: return {"action": "IGNORE"} 
            if isinstance(parsed, list):
                return parsed if parsed else {"action": "IGNORE"}
            return parsed
        except Exception as e:
            return {"action": "IGNORE"}

    def delete_note(self, file_path, note_id):
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"  [物理删除] 文件已移除: {file_path}")
            if note_id in self.threads:
                del self.threads[note_id]
                self._save_to_disk()
                print(f" [内存清理] 关联对话线程已移除: {note_id}")
            return True
        except Exception as e:
            print(f" [删除失败] 错误原因: {e}")
            return False

    def run_cli(self):
        print("\n" + "="*50)
        print(" Vault OS 主控终端已接管 ")
        print("输入 '/ingest' 摄入新笔记，'/audit' 手动核准习惯，'/exit' 退出系统")
        print("="*50 + "\n")

        while True:
            try:
                user_input = input("\n> Boss: ").strip()
                if not user_input: continue
                if user_input.lower() == '/exit':
                    print(" Vault OS 进入休眠状态。")
                    break
                if user_input.lower() == '/audit':
                    self.gatekeeper.check_and_promote(
                        llm_caller=self._call_llm_json, 
                        entity_callback=self._update_entity_file
                    )
                    continue
                print("\n  [引擎运转中...]")
                def _shadow_pipeline_cli():
                    current_history = self.threads.get("global", [])
                    caller_with_memory = lambda p, u: self._mock_llm_for_extractor(p, u, chat_history=current_history)
                    
                    with self.gatekeeper.memory_lock:
                        self.extractor.analyze_input(user_input, caller_with_memory, chat_history=current_history)
                        self.gatekeeper.check_and_promote(
                            llm_caller=self._call_llm_json,
                            entity_callback=self._update_entity_file
                        )
                threading.Thread(target=_shadow_pipeline_cli).start()
                retrieved_context = ""
                final_system_prompt = self.assembler.assemble(user_input, retrieved_context)
                print(" [LLM 推理中...]")
                answer = self._call_llm(final_system_prompt, user_input)
                print(f"\n[Vault OS]:\n{answer}")
            except KeyboardInterrupt:
                print("\n 检测到强制中断，Vault OS 进入休眠。")
                break
            except Exception as e:
                print(f"\n 系统崩溃: {str(e)}")

    def _call_llm_json(self, prompt, user_input="执行记忆仲裁"):
        strict_prompt = prompt + "\n\n【系统最高指令】：\n1. 你必须且只能输出合法的纯 JSON 格式！\n2. 绝对不允许包含任何解释性文字、前言后语。\n3. 不要使用 ```json 标记，直接输出以 { 或 [ 开头的纯文本！"
        messages = [{'role': 'system', 'content': strict_prompt}, {'role': 'user', 'content': user_input}]
        try:
            response = self.client.chat.completions.create(
                model=self.llm_config.get("model_mini", "qwen-turbo"),
                messages=messages
            )
            content = response.choices[0].message.content
            print(f" [仲裁官原始输出]: \n{content.strip()}\n" + "-"*30) 
            parsed = self._parse_json_robust(content)
            if isinstance(parsed, dict):
                parsed = [parsed]
            return parsed if parsed else []
        except Exception as e:
            print(f" 后台 JSON 解析异常: {e}")
            return []

    def process_profile_import(self, file_content):
        print(" [画像导入] 正在深度扫描文档内容...")
        seed_prompt = """
        你现在是 Vault OS 的初始化专家。请阅读用户提供的个人资料文档，
        从中提炼出关于用户的：coding_style(编程习惯), communication(交流风格), 
        interests(兴趣), facts(基本事实)。

        【提取法则】：
        1. 寻找明确的偏好，如“我喜欢...”、“我倾向于...”、“我常用...”。
        2. 识别客观事实，如“我在用 Python”、“我住在广州”。
        
        【输出要求】：必须输出 JSON 数组格式，每一项包含 type(固定为NEW), category, new_trait。
        例如：[{"type": "NEW", "category": "facts", "new_trait": "用户正在开发 AI Agent"}]
        """
        seed_prompt += """

【实体画像隔离规则】
1. core_profile.json 只保存用户本人事实；父亲、母亲、朋友、老板等身边人的事实必须输出 ENTITY_UPDATE。
2. “我父亲喜欢吃西瓜”输出 {"type": "ENTITY_UPDATE", "entity": "父亲", "new_trait": "喜欢吃西瓜"}。
3. “我喜欢吃西瓜”输出 {"type": "NEW", "category": "interests", "new_trait": "喜欢吃西瓜"}。
4. 如果文档同时包含用户本人和他人事实，输出数组，分别列出 NEW 与 ENTITY_UPDATE。
5. “真实姓名/名字/我叫”属于用户本人高优先级单值身份事实；与已有姓名不同必须作为冲突处理，不能普通新增。
"""
        try:
            response = self.client.chat.completions.create(
                model=self.llm_config.get("model_mini", "qwen-turbo"),
                messages=[{"role": "system", "content": seed_prompt}, {"role": "user", "content": file_content}],
                timeout = 15
            )
            content = response.choices[0].message.content
            print(f" [画像提取器返回]: {content.strip()}")
            raw_traits = self._parse_json_robust(content)
            if raw_traits:
                if isinstance(raw_traits, dict):
                    raw_traits = [raw_traits]
                profile_traits = []
                entity_count = 0
                for trait in raw_traits:
                    if not isinstance(trait, dict):
                        continue
                    if trait.get("type") == "ENTITY_UPDATE":
                        entity_name = trait.get("entity")
                        new_trait = trait.get("new_trait") or trait.get("trait")
                        if entity_name and new_trait:
                            self._update_entity_file(entity_name, new_trait)
                            entity_count += 1
                    else:
                        profile_traits.append(trait)
                success = self.gatekeeper.inject_pending_memories(profile_traits) if profile_traits else True
                if success:
                    return f"已成功从文档中提取出 {len(profile_traits)} 条用户记忆碎片，并同步 {entity_count} 条实体画像。请前往「记忆同步」进行最后核准。"
            return "未能从文档中识别出有效的习惯或事实。"
        except Exception as e:
            return f"画像提取过程中发生异常: {str(e)}"

if __name__ == "__main__":
    print(">>> 本地终端调试模式 <<<")
    terminal = VaultOS_Terminal()
    terminal.run_cli()
