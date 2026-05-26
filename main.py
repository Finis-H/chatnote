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
    from memory_system import MemoryGatekeeper
    from tool_registry import ToolRegistry
    from tool_executor import ToolExecutor
    from trace_system import copy_current_context, trace_emitter, traced_span
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
        self.gatekeeper = MemoryGatekeeper()
        self.registry = ToolRegistry()
        self.executor = ToolExecutor(self.registry, self.vector_db)
        # 4. 启动时的例行公事：确认 SQLite 画像内核已就绪。
        print("\n" + "="*50)
        self.gatekeeper.check_and_promote()
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

    def _build_memory_prefetch_context(self, user_input):
        """从 SQLite L2 统一选择当前输入命中的实体与关系上下文。"""
        try:
            context_text = self.gatekeeper.get_l2_context_text(user_input)
        except Exception as e:
            print(f" [记忆预读] L2 上下文读取异常: {e}")
            return ""
        if context_text:
            print(" [记忆预读] 已挂载 SQLite L2 实体/关系上下文。")
        return context_text

    def get_response(self, user_input: str, thread_id: str = "global", display_message: str = None) -> str:
        if not self.llm_config.get("api_key"):
            return " [系统提醒] 核心引擎尚未激活。请前往「引擎设置」配置您的 API Key。"
        if display_message is None:
            display_message = user_input
        try:
            print(f" [收到指令] 正在思考: {display_message} (线程: {thread_id})")   
            if display_message.lower() == '/audit':
                with self.gatekeeper.memory_lock:
                    self.gatekeeper.check_and_promote()
                return " [系统动作] SQLite 待审事件与 L2 快照已完成惰性结算。"
                
            print(" [记忆路由] 正在扫描用户输入中的长期记忆事件...")
            trace_emitter.begin_background_task()
            def _shadow_pipeline():
                try:
                    with traced_span("MEMORY_FLOW", "后台记忆流程") as flow_span:
                        current_history = self.threads.get(thread_id, []).copy()
                        caller_with_memory = lambda p, u: self._mock_llm_for_extractor(p, u, chat_history=current_history)
                        
                        with self.gatekeeper.memory_lock:
                            extract_span = trace_emitter.start_span("MEMORY_EXTRACT", "解析长期记忆候选")
                            candidates = self.extractor.analyze_input(display_message, caller_with_memory, chat_history=current_history)
                            candidate_count = len(candidates or [])
                            extract_span.finish(
                                "SUCCESS",
                                f"发现 {candidate_count} 条长期记忆" if candidate_count else "未发现需要长期保存的信息",
                                {"count": candidate_count}
                            )
                            self.gatekeeper.check_and_promote(
                                candidates,
                                llm_router=self._call_memory_router,
                                raw_reference=thread_id
                            )
                        flow_span.finish("SUCCESS", "后台记忆流程完成", {"count": candidate_count})
                except Exception as e:
                    print(f" [记忆路由] 后台记忆流程失败: {e}")
                finally:
                    trace_emitter.finish_background_task()
            shadow_context = copy_current_context()
            threading.Thread(target=shadow_context.run, args=(_shadow_pipeline,)).start()

            with traced_span("L2_QUERY", "预读记忆画像上下文"):
                prefetch_context = self._build_memory_prefetch_context(display_message)

            with traced_span("JIT_PARSE", "编译动态执行蓝图"):
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
                    with traced_span("DAG_STEP", f"执行 DAG 节点: {tool_name}", {"step": step_data}):
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
                                    step_context = copy_current_context()
                                    step_futures[step_id] = pool.submit(step_context.run, run_step, step)
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
                
            final_system_prompt = self.assembler.assemble(display_message, retrieved_context)
            print(" [核心算力] 正在生成最终回复...")
            with traced_span("LLM_FINAL", "生成最终回复"):
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
            trace_emitter.emit_event("AGENT_ERROR", "FAILED", "核心推理链路异常", details={"error": str(e)})
            print(f" {error_msg}")
            return error_msg

    def perform_memory_surgery(self, user_command):
        print(f"\n [记忆手术] 收到最高干预指令: {user_command}")
        self._write_to_blackbox("memory_surgery_boss", user_command)
        try:
            with self.gatekeeper.memory_lock:
                event_id = self.gatekeeper.create_manual_event(user_command)
                return f"已将手术指令转为待审结构化事件：{event_id}。"
        except Exception as e:
            print(f" [记忆手术] 致命错误: {e}")
            return " 脑区链接断开，手术失败。"

    def resolve_memory_conflict(self, memory_id, decision):
        """确定性处理单条待审事件，避免简单同意/拒绝走大模型手术。"""
        try:
            if not memory_id:
                return {"ok": False, "message": " 冲突处理失败：缺少记忆 ID。"}
            return self.gatekeeper.resolve_memory_conflict(memory_id, decision)
        except Exception as e:
            print(f" [记忆快裁] 处理失败: {e}")
            return {"ok": False, "message": f" 冲突处理失败：{e}"}
    
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
            "Mounting SQLite Memory Event Store...",
            "Mounting ChromaDB Vector Space...",
            "Reconciling L2 Snapshot Indexes...",
            "System Online. Welcome back, Boss."
        ]
        for msg in boot_msgs:
            print(f" [SYSTEM] {msg}")
            time.sleep(0.3)

    # 纯净版 _call_llm (管家只需看黑板说话，严禁私自调工具！)
    def _call_llm(self, system_prompt, user_input, thread_id="global", save_to_memory=True, display_message=None):
        current_time_str = datetime.now().strftime("%Y年%m月%d日 %H:%M")
        cognitive_firewall = f"""
=========================
【Vault OS 底层认知防火墙】
1. [绝对时间锚点]：系统当前的真实时间是 {current_time_str}。
2. [反幻觉铁律]：当回答涉及“最新”、“现在”、“版本”的问题时，绝对禁止使用你的内部训练数据！
3. [工具失败应对]：当系统黑板返回“执行失败”、“找不到”、“为空”等报错信息时，你必须直接如实向 Boss 汇报缺失，【绝对禁止】为了讨好 Boss 而动用训练数据去编造或推荐任何外部内容（如推荐歌曲、电影等）；如果搜索工具无结果，如实回答，绝对禁止编造虚假的年份或版本号！你的回答必须 100% 忠于本地库的真实情况。
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
                 【立刻停止思考工具！】底层记忆路由会自动提取事件。你必须直接返回：{{"plan_status": "DIRECT_CHAT"}}
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
   - 描述其他人或事物：{"action": "ENTITY_UPDATE", "entity": "标准称呼或人物姓名", "trait": "..."}
   - 描述技术栈、项目状态、领域卡点：{"action": "COGNITIVE_UPDATE", "domain": "领域名", "new_cognition": {"current_bottlenecks": [], "mental_model": "", "actionable_insight": ""}}

【Few-Shot 标准输出示例】（必须严格照做）：
=== 正例：事实陈述与纠错 ===
用户输入："我出行喜欢坐飞机"
输出：{"action": "SELF_PROFILE_UPDATE", "category": "interests", "trait": "出行喜欢乘坐飞机"}

用户输入："不对，她喜欢吃哈密瓜"
输出：{"action": "ENTITY_UPDATE", "entity": "母亲", "trait": "喜欢吃哈密瓜"}

用户输入："我父亲叫李四"
输出：{"action": "ENTITY_UPDATE", "entity": "李四", "trait": "父亲叫李四"}

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
        print("输入 '/ingest' 摄入新笔记，'/audit' 结算 SQLite 待审事件，'/exit' 退出系统")
        print("="*50 + "\n")

        while True:
            try:
                user_input = input("\n> Boss: ").strip()
                if not user_input: continue
                if user_input.lower() == '/exit':
                    print(" Vault OS 进入休眠状态。")
                    break
                if user_input.lower() == '/audit':
                    self.gatekeeper.check_and_promote()
                    continue
                print("\n  [引擎运转中...]")
                def _shadow_pipeline_cli():
                    current_history = self.threads.get("global", [])
                    caller_with_memory = lambda p, u: self._mock_llm_for_extractor(p, u, chat_history=current_history)
                    
                    with self.gatekeeper.memory_lock:
                        candidates = self.extractor.analyze_input(user_input, caller_with_memory, chat_history=current_history)
                        self.gatekeeper.check_and_promote(
                            candidates,
                            llm_router=self._call_memory_router,
                            raw_reference="global"
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

    def _call_memory_router(self, candidate):
        prompt = """
你是 Vault OS 的 L1 云端语义路由器。请把候选记忆转成唯一标准 JSON。
输出字段必须固定为：
{
  "target_entity": "Boss 或具体实体名",
  "action_category": "PROFILE|ENTITY|RELATION|PLAN|LEARN|BUILD|DEBUG|ARCHIVE",
  "action_detail": "facts|interests|communication|coding_style 或领域名",
  "context": "极短事实句",
  "relation_type": "father|mother|partner|friend|colleague|project_member|uses_tech，可省略",
  "source_entity": "关系源实体，可省略，默认 Boss",
  "confidence": 0.0-1.0,
  "requires_review": true/false
}
规则：
1. Boss 本人事实用 PROFILE；他人普通事实用 ENTITY；“X 是我的父亲/朋友/项目成员/技术栈”等关系事实用 RELATION。
2. 技术规划/学习目标用 PLAN 或 LEARN；当前开发/排障卡点用 BUILD 或 DEBUG。
3. 姓名、血缘、身份等单值属性若不确定，requires_review 必须为 true。
4. 只输出 JSON，不要解释。
"""
        try:
            response = self.client.chat.completions.create(
                model=self.llm_config.get("model_mini", "qwen-turbo"),
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": json.dumps(candidate, ensure_ascii=False)}
                ],
                timeout=15
            )
            parsed = self._parse_json_robust(response.choices[0].message.content)
            return parsed if isinstance(parsed, dict) else {}
        except Exception as e:
            print(f" [L1 路由器] 云端路由失败: {e}")
            return {}

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
1. Boss 画像只保存用户本人事实；父亲、母亲、朋友、老板等身边人的事实必须输出 ENTITY_UPDATE。
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
                valid_traits = [trait for trait in raw_traits if isinstance(trait, dict)]
                self.gatekeeper.process_import_traits(valid_traits)
                return f"已成功从文档中提取出 {len(valid_traits)} 条记忆事件，并写入 SQLite 画像事件源。"
            return "未能从文档中识别出有效的习惯或事实。"
        except Exception as e:
            return f"画像提取过程中发生异常: {str(e)}"

if __name__ == "__main__":
    print(">>> 本地终端调试模式 <<<")
    terminal = VaultOS_Terminal()
    terminal.run_cli()
