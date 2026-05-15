from openai import OpenAI
import os
import json
import threading
import sys
import time
import glob
import frontmatter
import re
import concurrent.futures
from datetime import datetime

# 模块接入 (导入我们之前手搓的引擎部件)
try:
    from habit_extractor import HabitExtractor
    from rag_assembler import RAGAssembler
    from chroma_engine import VaultVectorDB
    from promotion_gatekeeper import PromotionGatekeeper
    from tool_registry import ToolRegistry
    from tool_executor import ToolExecutor
except ImportError as e:
    print(f"🚨 引擎组件缺失: {e}")
    print("请确保所有组件脚本 (.py) 都在当前目录下！")
    sys.exit(1)

class VaultOS_Terminal:
    def __init__(self):
        print("⚙️  正在初始化 AI 算力...")
        self._boot_sequence() 
        # 1. 定义物理存储路径
        self.chat_history_path = "vault/chat_history.json" 
        self.blackbox_path = "vault/blackbox_raw.jsonl"
        self.config_path = "vault/system_config.json"
        os.makedirs("vault", exist_ok=True)
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
            print("🚨 [RAG 网关] 拦截到非法或不完整的载荷指令！丢弃。")
            return False
        try:
            print(f"\n📥 [RAG 网关] 收到来自外挂仓管的更新请求: {source_file}")
            if hasattr(self.vector_db, 'delete_by_source'):
                deleted_count = self.vector_db.delete_by_source(source_file)
            else:
                deleted_count = 0
            if not chunks:
                print(f"🗑️ [RAG 网关] 载荷为空，已完成该文件的彻底注销。")
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
                print(f"✅ [RAG 网关] 成功同化 {len(texts)} 块高纯度记忆碎片！\n")
                return True
            return False
        except Exception as e:
            print(f"💥 [RAG 网关] 数据引流发生雪崩，执行中断: {e}")
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
            print(f"📦 [系统] 已自动生成初始配置文件: {self.config_path}")
        except Exception as e:
            print(f"🚨 [系统] 自动生成配置文件失败: {e}")  
        return default_config

    def save_config(self, new_config):
        self.llm_config = new_config
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self.llm_config, f, ensure_ascii=False, indent=2)
        print("⚙️  [系统核心] 大模型配置已更新，正在热重载引擎...")
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

    def get_response(self, user_input: str, thread_id: str = "global", display_message: str = None) -> str:
        if not self.llm_config.get("api_key"):
            return "⚠️ [系统提醒] 核心引擎尚未激活。请前往「引擎设置」配置您的 API Key。"
        if display_message is None:
            display_message = user_input
        try:
            print(f"🧠 [收到指令] 正在思考: {display_message} (线程: {thread_id})")   
            if display_message.lower() == '/audit':
                self.gatekeeper.check_and_promote(
                    llm_caller=self._call_llm_json, 
                    entity_callback=self._update_entity_file
                )
                return "✅ [系统动作] 审计完毕：暗影碎片已完成提纯与画像晋升。"
                
            print("🕵️  [暗影守护者] 正在扫描用户输入提取习惯...")
            def _shadow_pipeline():
                current_history = self.threads.get(thread_id, [])
                self.extractor.analyze_input(display_message, self._mock_llm_for_extractor, chat_history=current_history)
                self.gatekeeper.check_and_promote(
                    llm_caller=self._call_llm_json, 
                    entity_callback=self._update_entity_file
                )
            threading.Thread(target=_shadow_pipeline).start()

            blueprint = self._compile_jit_task(display_message)
            status = blueprint.get("plan_status", "DIRECT_CHAT")
            print(f"🔀 [编译决断]: {status} | 理由: {blueprint.get('reasoning')}")
            
            retrieved_context = ""
            if status == "NEEDS_NEW_TOOLS":
                suggestion = blueprint.get("suggestion_msg", "Boss，我缺少完成此任务的工具。")
                missing = ", ".join(blueprint.get("missing_capabilities", []))
                print(f"⚠️ [能力探针] 发现缺失能力: {missing}")
                answer = f"🤖 [Vault OS 架构建议]:\n{suggestion}\n\n(系统检测到缺失核心组件：{missing}。您可以前往 VPM 插件中心挂载相关能力后，再次下达该指令。)"
                self._save_to_disk()
                return answer
                
            elif status == "READY":
                print("📋 [DAG 引擎] 图纸审核通过，正在初始化系统黑板...")
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
                    
                    print(f"   -> 🚀 [并发激活] 委派任务至: {tool_name} ...")
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
                        print(f"   -> 📝 [黑板更新] 已写入共享变量: {output_key}")
                        
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
                            print("⚠️ [DAG 引擎] 警告：发现无法满足的依赖逻辑环，强制中止剩余蓝图！")
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
                        
                retrieved_context = "【系统任务黑板数据 (各部门并发汇报结果)】:\n" + json.dumps(safe_blackboard, ensure_ascii=False, indent=2)
            else:
                retrieved_context = ""
                
            try:
                with open("vault/cognitive_map.json", "r", encoding="utf-8") as f:
                    cog_map = json.load(f)
                if cog_map:
                    cog_str = json.dumps(cog_map, ensure_ascii=False)
                    retrieved_context += f"\n\n【🎯 核心机密：Boss 的 Type 2 认知图谱】\n{cog_str}\n(警告：请严格参考此图谱决定你的回答深度、术语使用及避坑策略！)"
            except Exception:
                pass
            
            final_system_prompt = self.assembler.assemble(display_message, retrieved_context)
            print("🔥 [核心算力] 正在生成最终回复...")
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
            print(f"🚨 {error_msg}")
            return error_msg

    def perform_memory_surgery(self, user_command):
        print(f"\n🔪 [记忆手术] 收到最高干预指令: {user_command}")
        self._write_to_blackbox("memory_surgery_boss", user_command)
        try:
            with open(self.gatekeeper.pending_path, 'r', encoding='utf-8') as f:
                pending = json.load(f)
            with open(self.gatekeeper.profile_path, 'r', encoding='utf-8') as f:
                profile = json.load(f)
        except Exception as e:
            return f"🚨 无法读取脑区数据: {e}"
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
                with open(self.gatekeeper.pending_path, 'w', encoding='utf-8') as f:
                    json.dump({"queue": result_json["updated_queue"]}, f, ensure_ascii=False, indent=2)
                with open(self.gatekeeper.profile_path, 'w', encoding='utf-8') as f:
                    json.dump(result_json["updated_profile"], f, ensure_ascii=False, indent=2)   
                print(f"✅ [记忆手术] 成功: {result_json.get('reply')}")
                return result_json.get("reply", "神经链路重塑完毕。")
            else:
                return "⚠️ 手术中止：大模型未能按标准格式完成缝合。"        
        except Exception as e:
            print(f"🚨 [记忆手术] 致命错误: {e}")
            return "⚠️ 脑区链接断开，手术失败。"
    
    def _update_entity_file(self, entity_name, new_trait):
        entity_dir = "vault/knowledge/entities"
        os.makedirs(entity_dir, exist_ok=True)
        file_path = os.path.join(entity_dir, f"{entity_name}.md")
        if not os.path.exists(file_path):
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(f"---\ntitle: {entity_name} 的核心画像\ncategory: EntityProfile\n---\n\n")
                f.write(f"## 🧬 基础情报\n- {new_trait}\n")
            print(f"🆕 [实体档案] 已为 {entity_name} 建立初始卷宗。")
        else:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    old_content = f.read()
                prompt = f"""
                档案整理员，【{entity_name}】现有内容：\n{old_content}\n新情报："{new_trait}"
                合并规则：冲突则覆盖，补充则追加。直接输出 Markdown。
                """
                response = self.client.chat.completions.create(
                    model=self.llm_config.get("model_mini", "qwen-turbo"),
                    messages=[{"role": "user", "content": prompt}]
                )
                new_content = response.choices[0].message.content
                new_content = re.sub(r'^```markdown\s*|```$', '', new_content.strip(), flags=re.DOTALL)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print(f"📝 [实体档案] {entity_name} 的卷宗已静默覆写完成。")
            except Exception as e:
                print(f"🚨 实体档案覆写失败: {e}")

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
        os.makedirs("vault/knowledge/inbox", exist_ok=True)
        return self._scan_md_folder("vault/knowledge/inbox/*.md")

    def get_favorite_list(self):
        os.makedirs("vault/knowledge/favorites", exist_ok=True)
        return self._scan_md_folder("vault/knowledge/favorites/*.md")
    
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
            print(f"🟢 [SYSTEM] {msg}")
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
【⚠️ 最高权重：基岩画像驱动】
以下是 Boss 的核心基岩画像与偏好设置：
{core_profile}
        
**指令执行优先级**：
你不是普通的聊天助手，你是基于上述【基岩画像】运行的专属管家。
- 你在决定语气、代码风格、建议策略时，必须 100% 遵从基岩画像。
- 如果短期对话的内容与基岩画像发生冲突，永远、绝对以【基岩画像】为准！
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
3. [工具失败应对]：如果搜索工具无结果，如实回答，绝对禁止编造虚假的年份或版本号！
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
            # 🚀 彻底移除了 tools 和 tool_choice 参数！管家现在是个纯粹的语言生成器！
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
            error_msg = f"🚨 API 调用异常或超时，请检查配置: {str(e)}"
            print(error_msg)
            return error_msg

    def _parse_json_robust(self, text):
        try:
            match = re.search(r'```json\s*(\{.*?\}|\[.*?\])\s*```', text, re.DOTALL)
            if match:
                return json.loads(match.group(1).strip())
            match = re.search(r'(\{.*\}|\[.*\])', text, re.DOTALL)
            if match:
                return json.loads(match.group(1).strip())
            return json.loads(text)
        except Exception:
            return None

    def _compile_jit_task(self, user_input: str) -> dict:
        print("💡 [JIT 编译器] 正在为复杂任务绘制动态执行蓝图...")
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
        
        【你当前可用的工具 (手下的总监) 及其参数说明】: 
        {json.dumps(tool_specs, ensure_ascii=False)}
        
        【你的任务】：评估任务所需的能力。
        1. 如果现有工具足以完成任务，请规划一条清晰的执行步骤 (DAG)，并设定黑板需要记录的数据。
        2. 如果现有工具【不足以】完美完成任务，请中止规划，并主动向主人提出插件下载建议。

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
                    "args": {{"参数名": "参数值"}}, // 必须严格遵守上方工具说明中的 parameters 结构！
                    "output_to_blackboard": "输出变量名"
                }}
                {{
                    "step_id": "s2",
                    "depends_on": ["s1"],
                    "tool_name": "另一个工具",
                    "args": {{"file_data": "$$s1的输出变量名"}}, // 🚀 重点：使用 $$前缀 引用黑板上的数据传递给下个工具！
                    "output_to_blackboard": null
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
            print(f"🚨 [JIT 编译器] 脑区故障，降级为直连: {e}")
            return {"plan_status": "DIRECT_CHAT"}

    def _mock_llm_for_extractor(self, prompt, user_input):
        messages = [{'role': 'system', 'content': prompt}, {'role': 'user', 'content': user_input}]
        try:
            response = self.client.chat.completions.create(
                model=self.llm_config.get("model_mini", "qwen-turbo"),
                messages=messages
            )
            content = response.choices[0].message.content
            print(f"🕵️ [提取器原始输出]: {content.strip()}")
            parsed = self._parse_json_robust(content) 
            if not parsed: return {"action": "IGNORE"} 
            if isinstance(parsed, list):
                parsed = parsed[0] if parsed else {"action": "IGNORE"}
            return parsed
        except Exception as e:
            return {"action": "IGNORE"}

    def delete_note(self, file_path, note_id):
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"🗑️  [物理删除] 文件已移除: {file_path}")
            if note_id in self.threads:
                del self.threads[note_id]
                self._save_to_disk()
                print(f"🧠 [内存清理] 关联对话线程已移除: {note_id}")
            return True
        except Exception as e:
            print(f"🚨 [删除失败] 错误原因: {e}")
            return False

    def run_cli(self):
        print("\n" + "="*50)
        print("⚡ Vault OS 主控终端已接管 ⚡")
        print("输入 '/ingest' 摄入新笔记，'/audit' 手动核准习惯，'/exit' 退出系统")
        print("="*50 + "\n")

        while True:
            try:
                user_input = input("\n> Boss: ").strip()
                if not user_input: continue
                if user_input.lower() == '/exit':
                    print("💤 Vault OS 进入休眠状态。")
                    break
                if user_input.lower() == '/audit':
                    self.gatekeeper.check_and_promote(
                        llm_caller=self._call_llm_json, 
                        entity_callback=self._update_entity_file
                    )
                    continue
                print("\n⚙️  [引擎运转中...]")
                def _shadow_pipeline_cli():
                    self.extractor.analyze_input(user_input, self._mock_llm_for_extractor, chat_history=self.threads.get("global", []))
                    self.gatekeeper.check_and_promote(
                        llm_caller=self._call_llm_json, 
                        entity_callback=self._update_entity_file
                    )
                threading.Thread(target=_shadow_pipeline_cli).start()
                retrieved_context = ""
                final_system_prompt = self.assembler.assemble(user_input, retrieved_context)
                print("🧠 [LLM 推理中...]")
                answer = self._call_llm(final_system_prompt, user_input)
                print(f"\n🤖 [Vault OS]:\n{answer}")
            except KeyboardInterrupt:
                print("\n💤 检测到强制中断，Vault OS 进入休眠。")
                break
            except Exception as e:
                print(f"\n🚨 系统崩溃: {str(e)}")

    def _call_llm_json(self, prompt, user_input="执行记忆仲裁"):
        messages = [{'role': 'system', 'content': prompt}, {'role': 'user', 'content': user_input}]
        try:
            response = self.client.chat.completions.create(
                model=self.llm_config.get("model_mini", "qwen-turbo"),
                messages=messages
            )
            content = response.choices[0].message.content
            print(f"⚖️ [仲裁官原始输出]: \n{content.strip()}\n" + "-"*30) 
            parsed = self._parse_json_robust(content)
            return parsed if parsed else []
        except Exception as e:
            print(f"🚨 后台 JSON 解析异常: {e}")
            return []

    def process_profile_import(self, file_content):
        print("📡 [画像导入] 正在深度扫描文档内容...")
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
        try:
            response = self.client.chat.completions.create(
                model=self.llm_config.get("model_mini", "qwen-turbo"),
                messages=[{"role": "system", "content": seed_prompt}, {"role": "user", "content": file_content}],
                timeout = 15
            )
            content = response.choices[0].message.content
            print(f"🕵️ [画像提取器返回]: {content.strip()}")
            raw_traits = self._parse_json_robust(content)
            if raw_traits:
                success = self.gatekeeper.inject_pending_memories(raw_traits)
                if success:
                    return f"已成功从文档中提取出 {len(raw_traits)} 条记忆碎片。请前往「记忆同步」进行最后核准。"
            return "未能从文档中识别出有效的习惯或事实。"
        except Exception as e:
            return f"画像提取过程中发生异常: {str(e)}"

if __name__ == "__main__":
    print(">>> 本地终端调试模式 <<<")
    terminal = VaultOS_Terminal()
    terminal.run_cli()