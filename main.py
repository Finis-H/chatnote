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

# 模块接入 (导入我们之前手搓的引擎部件),确保以下文件在同级目录，且类名一致
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
        # 1. 定义物理存储路径 (绝不能删，且必须放在最前面！)
        self.chat_history_path = "vault/chat_history.json" # [加载 L0 硬盘记忆]
        self.blackbox_path = "vault/blackbox_raw.jsonl"
        self.config_path = "vault/system_config.json"
        os.makedirs("vault", exist_ok=True)
        # 加载大模型配置并初始化万能客户端
        self.llm_config = self._load_config()
        self._init_llm_client()
        # 2. 加载多线程记忆字典 (它会依赖上面的 chat_history_path)
        self.threads = self._load_threads_from_disk()
        # 3. 实例化各个核心引擎
        self.vector_db = VaultVectorDB()
        self.assembler = RAGAssembler(max_tokens=6000) # 给 LLM 留足思考空间
        self.extractor = HabitExtractor()
        self.gatekeeper = PromotionGatekeeper()
        # 新增：实例化工具注册表和执行引擎
        self.registry = ToolRegistry()
        self.executor = ToolExecutor(self.registry, self.vector_db)
        # 4. 启动时的例行公事：晋升核准自检
        print("\n" + "="*50)
        self.gatekeeper.check_and_promote(
            llm_caller=self._call_llm_json, 
            entity_callback=self._update_entity_file
        )
        print("="*50 + "\n")
    # 新增核心模块：RAG 独立数据接收网关
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
            # 1. 精准爆破：安全销毁旧切片
            if hasattr(self.vector_db, 'delete_by_source'):
                deleted_count = self.vector_db.delete_by_source(source_file)
            else:
                deleted_count = 0
            # 2. 空载荷即物理删除
            if not chunks:
                print(f"🗑️ [RAG 网关] 载荷为空，已完成该文件的彻底注销。")
                return True
            # 3. 组装新切片并装填
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
    # 配置读取方法
    def _load_config(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    # 读取已有的配置
                    config = json.load(f)
                    # 关键补丁：如果旧的 JSON 里没有 embed 字段，在此处强制补齐
                    if "embed_model" not in config:
                        config["embed_model"] = "text-embedding-v4"
                        config["embed_api_key"] = ""
                        config["embed_base_url"] = "https://dashscope.aliyuncs.com/compatible-mode/v1"
                    return config
            except: pass
        # 2. 如果文件不存在，定义一套标准的初始配置
        default_config = {
            "api_key": "",
            "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "model_max": "qwen-max",
            "model_mini": "qwen-turbo",
            "embed_api_key": "", 
            "embed_base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "embed_model": "text-embedding-v4" 
        }
        # 物理写入硬盘，实现“自动再生”
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, ensure_ascii=False, indent=2)
            print(f"📦 [系统] 已自动生成初始配置文件: {self.config_path}")
        except Exception as e:
            print(f"🚨 [系统] 自动生成配置文件失败: {e}")  
        return default_config
    # 新增配置保存与热重载方法
    def save_config(self, new_config):
        self.llm_config = new_config
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self.llm_config, f, ensure_ascii=False, indent=2)
        print("⚙️  [系统核心] 大模型配置已更新，正在热重载引擎...")
        self._init_llm_client()
    # 初始化万能客户端
    def _init_llm_client(self):
        # 核心防御：如果 JSON 里是空字符串，强行塞一个假 Key 防止 OpenAI 库崩溃
        raw_key = self.llm_config.get("api_key", "")
        safe_key = raw_key if raw_key.strip() else "sk-placeholder"
        self.client = OpenAI(
            api_key=safe_key,
            base_url=self.llm_config.get("base_url", "https://dashscope.aliyuncs.com/compatible-mode/v1")
        )
        # 注意：向量数据库实例化时也需要这份配置
        if hasattr(self, 'vector_db'):
            self.vector_db.update_config(self.llm_config)

    def _load_threads_from_disk(self):
        if os.path.exists(self.chat_history_path):
            with open(self.chat_history_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {"global": []}
        return {"global": []}

    def _save_to_disk(self):
        """将 L0 记忆写入硬盘，防止重启丢失"""
        with open(self.chat_history_path, 'w', encoding='utf-8') as f:
            json.dump(self.threads, f, ensure_ascii=False, indent=2)
    
    def _write_to_blackbox(self, role, content):
        """🚨 物理落地：黑盒子全量日志 (Append 模式)"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        # 1. 把数据组装成一个标准的字典
        log_entry = {"timestamp": timestamp, "role": role, "content": content}
        # json.dumps 把字典转成单行字符串
        # ensure_ascii=False 是为了保证中文正常显示，不变成 \uXXXX
        with open(self.blackbox_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
    # 专门给 server.py (WebSocket) 调用的专属方法
    def get_response(self, user_input: str, thread_id: str = "global", display_message: str = None) -> str:
        if not self.llm_config.get("api_key"):
            return "⚠️ [系统提醒] 核心引擎尚未激活。请前往「引擎设置」配置您的 API Key。"
        if display_message is None:
            display_message = user_input
        # 网关专用接口：这里接收指令，返回字符串
        try:
            print(f"🧠 [收到指令] 正在思考: {display_message} (线程: {thread_id})")   
            if display_message.lower() == '/audit':
                self.gatekeeper.check_and_promote(
                    llm_caller=self._call_llm_json, 
                    entity_callback=self._update_entity_file
                )
                return "✅ [系统动作] 审计完毕：暗影碎片已完成提纯与画像晋升。"
            # 步骤 1：后台静默提取习惯 (Shadow Daemon)
            print("🕵️  [暗影守护者] 正在扫描用户输入提取习惯...")
            def _shadow_pipeline():
                # 1. 抓取碎发
                current_history = self.threads.get(thread_id, [])
                self.extractor.analyze_input(display_message, self._mock_llm_for_extractor, chat_history=current_history)
                # 2. 立刻调用海关进行提纯、判定冲突和落盘
                self.gatekeeper.check_and_promote(
                    llm_caller=self._call_llm_json, 
                    entity_callback=self._update_entity_file
                )
            threading.Thread(target=_shadow_pipeline).start()
            # 步骤 2：组装附带 RAG 和画像的核心 Prompt (RAG Assembler),新增JIT 即时编译与黑板执行流 (The DAG Engine)
            blueprint = self._compile_jit_task(display_message)
            status = blueprint.get("plan_status", "DIRECT_CHAT")
            print(f"🔀 [编译决断]: {status} | 理由: {blueprint.get('reasoning')}")
            
            retrieved_context = ""
            # 场景 A：能力缺失！主动建议下载插件
            if status == "NEEDS_NEW_TOOLS":
                suggestion = blueprint.get("suggestion_msg", "Boss，我缺少完成此任务的工具。")
                missing = ", ".join(blueprint.get("missing_capabilities", []))
                print(f"⚠️ [能力探针] 发现缺失能力: {missing}")
                # 骗过下面的最终总结，直接在此处短路返回给 Boss
                answer = f"🤖 [Vault OS 架构建议]:\n{suggestion}\n\n(系统检测到缺失核心组件：{missing}。您可以前往 VPM 插件中心挂载相关能力后，再次下达该指令。)"
                self._save_to_disk()
                return answer
            # 场景 B：能力齐备！启动黑板流转机制 (DAG Execution)
            elif status == "READY":
                print("📋 [DAG 引擎] 图纸审核通过，正在初始化系统黑板...")
                # 1. 开辟内存黑板
                steps = blueprint.get("steps", [])
                blackboard = {key: None for key in blueprint.get("blackboard_keys", [])}
                # 黑板必须加锁，防止多线程并发写入时发生数据雪崩
                bb_lock = threading.Lock()
                step_futures = {}
                # 定义单步执行函数（给线程池用）
                def run_step(step_data):
                    tool_name = step_data.get("tool_name")
                    args = step_data.get("args", {})
                    output_key = step_data.get("output_to_blackboard")
                    
                    print(f"   -> 🚀 [并发激活] 委派任务至: {tool_name} ...")
                    class MockToolCall:
                        class MockFunction:
                            def __init__(self, name, arguments):
                                self.name = name
                                self.arguments = arguments
                        def __init__(self, name, arguments):
                            self.function = self.MockFunction(name, arguments)
                    step_result = self.executor.execute(MockToolCall(tool_name, json.dumps(args)))
                    if output_key:
                        with bb_lock:
                            blackboard[output_key] = step_result
                        print(f"   -> 📝 [黑板更新] 已写入共享变量: {output_key}")
                # 启动 5 个并发工位的车间
                with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
                    pending_steps = steps.copy()
                    completed_step_ids = set()
                    submitted_step_ids = set()
                    
                    # 只要还有任务没提交，就一直扫图纸
                    while pending_steps:
                        progress_made = False
                        for step in pending_steps[:]:
                            step_id = step.get("step_id")
                            depends_on = step.get("depends_on", [])
                            if isinstance(depends_on, str): depends_on = [depends_on]
                            # 拓扑解锁核心：只有依赖项全部完成，才将此任务扔进并发池
                            if all(dep in completed_step_ids for dep in depends_on):
                                if step_id not in submitted_step_ids:
                                    step_futures[step_id] = pool.submit(run_step, step)
                                    submitted_step_ids.add(step_id)
                                    pending_steps.remove(step)
                                    progress_made = True
                        # 收割已完成的线程
                        if step_futures:
                            not_done = [f for sid, f in step_futures.items() if sid not in completed_step_ids]
                            if not_done:
                                # 阻塞等待，直到至少有一个 Agent 干完活回来
                                concurrent.futures.wait(not_done, return_when=concurrent.futures.FIRST_COMPLETED)
                                for sid, f in step_futures.items():
                                    if f.done() and sid not in completed_step_ids:
                                        completed_step_ids.add(sid)
                        # 防死锁核武：如果图纸逻辑有环，立刻强行阻断
                        if not progress_made and not [f for sid, f in step_futures.items() if not f.done()]:
                            print("⚠️ [DAG 引擎] 警告：发现无法满足的依赖逻辑环，强制中止剩余蓝图！")
                            break 
                # 3. 将写满数据的黑板压缩为上下文，供 CEO 最终缝合            
                retrieved_context = "【系统任务黑板数据 (各部门并发汇报结果)】:\n" + json.dumps(blackboard, ensure_ascii=False, indent=2)
            # 场景 C：纯聊天 (DIRECT_CHAT)
            else:
                retrieved_context = ""
            # 挂载 Type 2 认知图谱 (透视眼镜) [保留你原有的逻辑]
            try:
                with open("vault/cognitive_map.json", "r", encoding="utf-8") as f:
                    cog_map = json.load(f)
                if cog_map:
                    cog_str = json.dumps(cog_map, ensure_ascii=False)
                    retrieved_context += f"\n\n【🎯 核心机密：Boss 的 Type 2 认知图谱】\n{cog_str}\n(警告：请严格参考此图谱决定你的回答深度、术语使用及避坑策略！)"
            except Exception:
                pass
            
            # 步骤 3：终极思维装配与输出
            final_system_prompt = self.assembler.assemble(display_message, retrieved_context)
            
            print("🔥 [核心算力] 正在生成最终回复...")
            # 如果是 READY (复杂编排)，黑板上已经有数据了，强制卸载底层工具，防止二次返工浪费算力。
            # 如果是 DIRECT_CHAT (极简直连)，保留底层工具，让管家利用原生 Tool Calling 去查天气或笔记。
            should_disable_tools = True if status == "READY" else False
            answer = self._call_llm(
                final_system_prompt, 
                user_input, 
                thread_id=thread_id, 
                save_to_memory=False, 
                display_message=display_message,
                disable_tools=should_disable_tools  # 传入开关
            )
            # 收尾固化记忆
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
        """🩺 专属视窗：潜意识记忆外科手术"""
        print(f"\n🔪 [记忆手术] 收到最高干预指令: {user_command}")
        self._write_to_blackbox("memory_surgery_boss", user_command)
        # 1. 读取当前患者的状态
        try:
            with open(self.gatekeeper.pending_path, 'r', encoding='utf-8') as f:
                pending = json.load(f)
            with open(self.gatekeeper.profile_path, 'r', encoding='utf-8') as f:
                profile = json.load(f)
        except Exception as e:
            return f"🚨 无法读取脑区数据: {e}"
        # 2. 组装手术要求
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
            # 🚨 脑科手术极其精密，必须调用最聪明的大模型
            response = self.client.chat.completions.create(
                model=self.llm_config.get("model_max", "qwen-max"), 
                messages=[{'role': 'system', 'content': prompt}]
            )
            content = response.choices[0].message.content
            # 使用咱们刚写的正则装甲剥离 JSON
            result_json = self._parse_json_robust(content)
            
            if result_json and "updated_queue" in result_json:
                # 3. 手术成功，物理落盘缝合
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
        """📂 物理级同步：静默创建或智能覆写实体档案"""
        entity_dir = "vault/knowledge/entities"
        os.makedirs(entity_dir, exist_ok=True)
        file_path = os.path.join(entity_dir, f"{entity_name}.md")
        # 1. 全新人物：直接创建档案
        if not os.path.exists(file_path):
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(f"---\ntitle: {entity_name} 的核心画像\ncategory: EntityProfile\n---\n\n")
                f.write(f"## 🧬 基础情报\n- {new_trait}\n")
            print(f"🆕 [实体档案] 已为 {entity_name} 建立初始卷宗。")
        # 2. 已有的人物：调用小模型进行“智能覆写”
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
                # 剔除大模型可能手贱加上的 markdown 语法块
                new_content = re.sub(r'^```markdown\s*|```$', '', new_content.strip(), flags=re.DOTALL)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print(f"📝 [实体档案] {entity_name} 的卷宗已静默覆写完成。")
            except Exception as e:
                print(f"🚨 实体档案覆写失败: {e}")
        # 不要忘了触发 RAG 向量库静默更新
        # def _silent_ingest():
        #     try:
        #         # 适配降级环境下的单体静默摄入
        #         chunks = self.ingester.process_inbox() 
        #         if chunks:
        #             texts = [c['content'] for c in chunks]
        #             metas = [{"source": c['source']} for c in chunks]
        #             ids = [f"{c['source']}_chunk_{i}" for i, c in enumerate(chunks)]
        #             self.vector_db.add_chunks(texts, metas, ids)
        #             print("📚 [知识引擎] 实体情报已静默沉淀至向量空间。")
        #     except Exception as e: 
        #         pass
        # threading.Thread(target=_silent_ingest).start()

    # --- 提取出来的通用 Markdown 扫描引擎 ---
    def _scan_md_folder(self, folder_pattern):
        """通用底层：扫描指定目录下的所有 MD 文件并提取元数据"""
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
    # --- 两个具体的业务接口 ---
    def get_local_news_list(self):
        """业务A：拉取新闻收件箱"""
        os.makedirs("vault/knowledge/inbox", exist_ok=True)
        return self._scan_md_folder("vault/knowledge/inbox/*.md")

    def get_favorite_list(self):
        """业务B：拉取收藏夹"""
        # 确保文件夹存在
        os.makedirs("vault/knowledge/favorites", exist_ok=True)
        return self._scan_md_folder("vault/knowledge/favorites/*.md")
    
    def get_note_content(self, file_path):
        """根据路径读取完整的 Markdown 正文"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                post = frontmatter.load(f)
                return post.content
        except Exception as e:
            return f"读取内容失败: {str(e)}"

    def _boot_sequence(self):
        """极客风的开机动画"""
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

    def _call_llm(self, system_prompt, user_input, thread_id="global", save_to_memory=True, display_message=None, disable_tools=False):
        """统一的大模型调用网关"""
        if display_message is None: display_message = user_input
        messages = [{'role': 'system', 'content': system_prompt}]
        if thread_id not in self.threads: self.threads[thread_id] = []
        messages.extend(self.threads[thread_id][-6:])
        messages.append({'role': 'user', 'content': user_input})

        try:
            # 动态构建请求参数，防止 tools 为 None 导致 SDK 崩溃
            api_params = {
                "model": self.llm_config.get("model_max", "qwen-max"), 
                "messages": messages
            }
            available_tools = self.registry.get_tools()
            # 核心逻辑：如果工具库有工具，且系统没有要求强行卸载，才挂载给大模型
            if available_tools and not disable_tools:
                api_params["tools"] = available_tools
                api_params["tool_choice"] = "auto"
                
            response = self.client.chat.completions.create(**api_params, timeout=30)
            response_message = response.choices[0].message
            # 判断：大模型是否决定动用工具？
            if getattr(response_message, 'tool_calls', None):
                # 1. 把它想调用工具的记录塞进对话历史
                messages.append(response_message)
                # 2. 遍历执行所有它想调用的工具 (支持并行调用)
                for tool_call in response_message.tool_calls:
                    print(f"🛠️  [中枢指令] 管家大脑请求调用工具: {tool_call.function.name}")
                    # 真正执行物理动作！
                    tool_result = self.executor.execute(tool_call)
                    # 将执行结果包装好，塞回给大模型
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": str(tool_result)
                    })
                # 3. 第二轮召唤：大模型拿到了工具数据，进行最终缝合并说话
                print("🧠 [认知融合] 已获取外部工具数据，正在生成最终汇报...")
                second_response = self.client.chat.completions.create(
                    model=self.llm_config.get("model_max", "qwen-max"),
                    messages=messages,
                    timeout=30
                )
                # 防止大模型偶尔抽风返回 None 导致 server.py 打字机崩溃
                raw_content = second_response.choices[0].message.content
                answer = raw_content if raw_content else "【系统提示：管家已经拿到数据，但未能成功生成自然语言总结。】"
            else:
                # 如果没调用工具，说明是直接聊天的内容
                raw_content = response_message.content
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
    # --- 路由中枢的占位接口 ---
    # def _intent_router(self, user_input: str) -> dict:
    #     """🚦 意图路由中枢：决定工具调用的十字路口"""
    #     prompt = """
    #     你是 Vault OS 的中枢路由引擎 (Intent Router)。
    #     你的唯一任务是根据主人的输入，判断应该调用哪个底层工具来获取信息。

    #     【可用工具库】：
    #     1. LOCAL_RAG：用于查询主人自身的事务，包括：个人笔记、记忆、日程、过往记录、人际关系（如妈妈的喜好）、代码习惯等。
    #     2. WEB_SEARCH：用于查询外部世界的信息，包括：最新的新闻、天气、股价、技术文档、不属于主人私域的百科知识。
    #     3. DIRECT_CHAT：普通的闲聊、翻译、代码编写、无需查资料的纯逻辑推理。

    #     【强制输出 JSON 格式】：
    #     {
    #         "action": "LOCAL_RAG" | "WEB_SEARCH" | "DIRECT_CHAT",
    #         "search_query": "提取出的核心搜索词（如果是 DIRECT_CHAT 则留空）",
    #         "reason": "路由选择的理由（简短一句话）"
    #     }
    #     """
    #     try:
    #         # 🚨 路由判断必须极速！强行使用 model_mini 且设置超时
    #         response = self.client.chat.completions.create(
    #             model=self.llm_config.get("model_mini", "qwen-turbo"),
    #             messages=[{"role": "system", "content": prompt}, {"role": "user", "content": user_input}],
    #             timeout=5
    #         )
    #         content = response.choices[0].message.content
    #         parsed = self._parse_json_robust(content)
            
    #         if parsed and "action" in parsed:
    #             return parsed
    #         return {"action": "DIRECT_CHAT", "search_query": ""}
    #     except Exception as e:
    #         print(f"🚨 [路由中枢] 引擎故障，降级为直连聊天: {e}")
    #         return {"action": "DIRECT_CHAT", "search_query": ""}

    def _compile_jit_task(self, user_input: str) -> dict:
        """ JIT 即时任务编译器：生成动态 DAG 剧本与能力探针"""
        print("💡 [JIT 编译器] 正在为复杂任务绘制动态执行蓝图...")
        
        # 1. 获取当前兵力 (挂载的所有工具)
        current_tools = self.registry.get_tools()
        tool_names = [t['function']['name'] for t in current_tools] if current_tools else ["无可用工具"]
        
        prompt = f"""
        你是 Vault OS 的 JIT 任务编译器 (CEO)。
        主人的当前任务是: "{user_input}"
        
        【你当前可用的工具 (手下的总监)】: 
        {json.dumps(tool_names, ensure_ascii=False)}
        
        【你的任务】：评估任务所需的能力。
        1. 如果现有工具足以完成任务，请规划一条清晰的执行步骤 (DAG)，并设定黑板需要记录的数据。
        2. 如果现有工具【不足以】完美完成任务（例如需要查外部特定的旅游、法律、股票数据，但你没有对应的 API 工具），请中止规划，并主动向主人提出插件下载建议。

        【强制输出 JSON 格式】：
        必须严格输出以下格式的 JSON，不要包含任何多余文字：
        {{
            "plan_status": "READY" | "NEEDS_NEW_TOOLS" | "DIRECT_CHAT",
            
            // 如果状态是 NEEDS_NEW_TOOLS，填写以下建议：
            "missing_capabilities": ["缺失的能力描述，如：日本新干线实时票务", "日本当地精准气象预报"],
            "suggestion_msg": "向 Boss 汇报的一句话建议，如：Boss，要完美规划日本游，建议您去 VPM 商店安装 [携程旅游 Agent] 和 [日本气象 MCP]。",
            
            // 如果状态是 READY，填写以下 DAG 执行蓝图：
            "blackboard_keys": ["需要记录在黑板上的变量名，如: 'weather_result', 'file_content'"],
            "steps": [
                {{
                    "step_id": "s1",
                    "tool_name": "web_search",
                    "args": {{"query": "东京天气"}},
                    "output_to_blackboard": "weather_result"
                }},
                {{
                    "step_id": "s2",
                    "depends_on": ["s1"], // 教会模型：如果有严格的先后顺序，必须加上依赖项数组
                    "tool_name": "search_local_knowledge",
                    "args": {{"query": "我的航班号"}},
                    "output_to_blackboard": "flight_info"
                }}
            ],
            // 无论何种状态，写下你的思考依据
            "reasoning": "一句话解释你的规划逻辑"
        }}
        """
        
        try:
            # 规划阶段需要高智商，调用 model_max
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
        """专门给习惯提取器用的小模型调用（省钱、快速）"""
        messages = [{'role': 'system', 'content': prompt}, {'role': 'user', 'content': user_input}]
        try:
            response = self.client.chat.completions.create(
                model=self.llm_config.get("model_mini", "qwen-turbo"),
                messages=messages
            )
            content = response.choices[0].message.content
            # 🚨 雷达 1 号：打印提取器到底看了啥
            print(f"🕵️ [提取器原始输出]: {content.strip()}")
            parsed = self._parse_json_robust(content) 
            if not parsed: return {"action": "IGNORE"} 
            # 核心防御：打平 List
            if isinstance(parsed, list):
                parsed = parsed[0] if parsed else {"action": "IGNORE"}
            return parsed
        except Exception as e:
            return {"action": "IGNORE"}

    def delete_note(self, file_path, note_id):
        """物理删除文件并同步清理内存中的对话线程"""
        try:
            # 1. 物理删除磁盘文件
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"🗑️  [物理删除] 文件已移除: {file_path}")
            # 2. 清理内存中的对话线程
            if note_id in self.threads:
                del self.threads[note_id]
                # 同步到硬盘 chat_history.json
                self._save_to_disk()
                print(f"🧠 [内存清理] 关联对话线程已移除: {note_id}")
            return True
        except Exception as e:
            print(f"🚨 [删除失败] 错误原因: {e}")
            return False

    def run_cli(self):
        """主控事件循环 (REPL)"""
        print("\n" + "="*50)
        print("⚡ Vault OS 主控终端已接管 ⚡")
        print("输入 '/ingest' 摄入新笔记，'/audit' 手动核准习惯，'/exit' 退出系统")
        print("="*50 + "\n")

        while True:
            try:
                user_input = input("\n> Boss: ").strip()
                if not user_input: continue
                # 🛑 内置系统指令
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
                # 步骤 1：后台静默提取习惯 (Shadow Daemon)
                # 在终端模式下，也必须使用完整的“提取+仲裁”双重静默流水线
                def _shadow_pipeline_cli():
                    self.extractor.analyze_input(user_input, self._mock_llm_for_extractor, chat_history=self.threads.get("global", []))
                    self.gatekeeper.check_and_promote(
                        llm_caller=self._call_llm_json, 
                        entity_callback=self._update_entity_file
                    )
                threading.Thread(target=_shadow_pipeline_cli).start()
                # 步骤 2：组装附带 RAG 和画像的核心 Prompt (RAG Assembler)
                retrieved_context = ""
                final_system_prompt = self.assembler.assemble(user_input, retrieved_context)
                # 步骤 3：调用大模型生成最终回复
                print("🧠 [LLM 推理中...]")
                answer = self._call_llm(final_system_prompt, user_input)
                # 打印结果
                print(f"\n🤖 [Vault OS]:\n{answer}")
            except KeyboardInterrupt:
                print("\n💤 检测到强制中断，Vault OS 进入休眠。")
                break
            except Exception as e:
                print(f"\n🚨 系统崩溃: {str(e)}")

    def _call_llm_json(self, prompt, user_input="执行记忆仲裁"):
        """通用 JSON 输出大模型调用网关"""
        messages = [{'role': 'system', 'content': prompt}, {'role': 'user', 'content': user_input}]
        try:
            response = self.client.chat.completions.create(
                model=self.llm_config.get("model_mini", "qwen-turbo"),
                messages=messages
            )
            content = response.choices[0].message.content
            # 🚨 雷达 2 号：打印仲裁官的判决废话
            print(f"⚖️ [仲裁官原始输出]: \n{content.strip()}\n" + "-"*30) 
            parsed = self._parse_json_robust(content)
            return parsed if parsed else []
        except Exception as e:
            print(f"🚨 后台 JSON 解析异常: {e}")
            return []

    def process_profile_import(self, file_content):
        """ 异步手术：从文档中提纯画像碎片"""
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
            # 调用最强模型进行全量扫描
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
    # 只要运行这句话，终端就会接管。如果你要跑 UI 测试，不要在终端乱敲回车
    terminal.run_cli()