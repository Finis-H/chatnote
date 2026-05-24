import os
import glob
import json
import re
import threading
from main import VAULT_ROOT
import uuid
from datetime import datetime, timedelta

class PromotionGatekeeper:
    SELF_ENTITIES = {"我", "用户", "Boss", "BOSS", "boss", "Master", "主人", "本尊", "自己", "本人", "创造者"}
    ENTITY_ALIASES = {
        "父亲": ("父亲", "爸爸", "爸", "爹", "老爸", "father"),
        "母亲": ("母亲", "妈妈", "妈", "娘", "老妈", "mother"),
        "朋友": ("朋友", "好友", "同学", "同事"),
        "老板": ("老板", "上司", "领导"),
        "伴侣": ("妻子", "老婆", "丈夫", "老公", "女朋友", "男朋友", "伴侣"),
        "孩子": ("儿子", "女儿", "孩子", "小孩"),
    }
    ENTITY_GROUPS = {
        "父母": ("父亲", "母亲"),
        "双亲": ("父亲", "母亲"),
        "爸妈": ("父亲", "母亲"),
        "家人": ("父亲", "母亲", "伴侣", "孩子"),
        "亲人": ("父亲", "母亲", "伴侣", "孩子"),
    }
    NAME_PATTERNS = (
        re.compile(r"(?:用户的名字|用户名字|用户姓名|用户的姓名|用户真实姓名|真实姓名|姓名|名字)\s*(?:是|叫|为|:|：)?\s*([\u4e00-\u9fffA-Za-z][\u4e00-\u9fffA-Za-z·.\-]{0,30})"),
        re.compile(r"(?:我叫|我名叫|我名字叫|我的名字是|我的姓名是|我的真实姓名是)\s*([\u4e00-\u9fffA-Za-z][\u4e00-\u9fffA-Za-z·.\-]{0,30})"),
    )
    NAME_STOP_WORDS = {
        "用户", "名字", "姓名", "真实姓名", "父亲", "母亲", "爸爸", "妈妈", "朋友", "老板",
        "喜欢", "讨厌", "不是", "不知道", "什么", "多少", "谁", "吗", "呢",
    }

    def __init__(self):
        self.fragments_dir = os.path.join(VAULT_ROOT, "active_tasks")
        self.profile_path = os.path.join(VAULT_ROOT, "core_profile.json")
        self.pending_path = os.path.join(VAULT_ROOT, "pending_memory.json")
        self.blackbox_path = os.path.join(VAULT_ROOT, "memory_blackbox.jsonl") # 黑盒溯源
        self.cognitive_path = os.path.join(VAULT_ROOT, "cognitive_map.json") # 认知图谱的物理路径
        self.entity_dir = os.path.join(VAULT_ROOT, "knowledge", "entities")
        self.entity_index = {}
        self.memory_lock = threading.RLock()
        self._init_files()
        self.refresh_entity_index()

    def _init_files(self):
        os.makedirs(os.path.dirname(self.profile_path), exist_ok=True)
        # 初始化基岩
        if not os.path.exists(self.profile_path):
            with open(self.profile_path, 'w', encoding='utf-8') as f:
                json.dump({"coding_style": [], "communication": [], "interests": [], "facts": []}, f)
        # 初始化缓冲队列
        if not os.path.exists(self.pending_path):
            with open(self.pending_path, 'w', encoding='utf-8') as f:
                json.dump({"queue": []}, f)
        # 初始化认知图谱 (Type 2)
        if not os.path.exists(self.cognitive_path):
            with open(self.cognitive_path, 'w', encoding='utf-8') as f:
                json.dump({}, f) # 初始为空字典，等待大模型动态创建领域节点
        os.makedirs(self.entity_dir, exist_ok=True)
        if not hasattr(self, "entity_index"):
            self.entity_index = {}

    def refresh_entity_index(self):
        """非递归挂载实体档案索引，避免回答前反复扫描和无关泄漏。"""
        index = {}
        try:
            os.makedirs(self.entity_dir, exist_ok=True)
            for filename in os.listdir(self.entity_dir):
                if not filename.endswith(".md"):
                    continue
                entity_name = filename[:-3]
                safe_entity = self.sanitize_entity_name(entity_name)
                if not safe_entity or safe_entity == "Boss":
                    continue
                index[safe_entity] = {
                    "name": safe_entity,
                    "path": os.path.join(self.entity_dir, filename),
                    "aliases": tuple(self.ENTITY_ALIASES.get(safe_entity, (safe_entity,))),
                }
        except Exception as e:
            print(f"⚠️ [实体索引] 刷新失败: {e}")
        self.entity_index = index
        print(f" [实体索引] 已挂载 {len(index)} 个实体档案路由。")
        return index

    def get_entity_path(self, entity_name):
        safe_entity = self.sanitize_entity_name(entity_name)
        if not safe_entity or safe_entity == "Boss":
            return None
        indexed = self.entity_index.get(safe_entity)
        if indexed:
            return indexed.get("path")
        fallback = os.path.join(self.entity_dir, f"{safe_entity}.md")
        return fallback if os.path.exists(fallback) else None

    def resolve_entities(self, text):
        """根据明确实体名、别名和有限集合词，返回本轮回答可挂载的实体。"""
        text = str(text or "")
        matched = set()

        for group_word, group_entities in self.ENTITY_GROUPS.items():
            if group_word in text:
                if group_word in {"家人", "亲人"}:
                    matched.update(entity for entity in group_entities if entity in self.entity_index)
                else:
                    matched.update(group_entities)

        for canonical, aliases in self.ENTITY_ALIASES.items():
            if canonical in text or any(alias in text for alias in aliases):
                matched.add(canonical)

        for entity_name, info in self.entity_index.items():
            aliases = info.get("aliases", ())
            if entity_name in text or any(alias in text for alias in aliases):
                matched.add(entity_name)

        return sorted(
            entity for entity in matched
            if self.sanitize_entity_name(entity) and self.sanitize_entity_name(entity) != "Boss"
        )

    def _write_blackbox(self, event_type, details):
        """记录绝对不可篡改的黑盒日志"""
        log_entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "event": event_type,
            "details": details
        }
        with open(self.blackbox_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

    def _normalize_entity(self, entity):
        if not entity:
            return "Boss"
        entity_text = str(entity).strip()
        if entity_text in self.SELF_ENTITIES:
            return "Boss"
        for canonical, aliases in self.ENTITY_ALIASES.items():
            if entity_text == canonical or entity_text in aliases:
                return canonical
        return entity_text

    def sanitize_entity_name(self, entity):
        entity_name = self._normalize_entity(entity)
        if entity_name == "Boss":
            return "Boss"
        if not entity_name:
            return None
        if len(entity_name) > 40:
            return None
        if entity_name in {".", ".."} or ".." in entity_name:
            return None
        if any(ch in entity_name for ch in ('/', '\\', ':', '*', '?', '"', '<', '>', '|')):
            return None
        return entity_name

    def _extract_external_entity_from_text(self, text):
        if not text:
            return None
        text = str(text)
        for canonical, aliases in self.ENTITY_ALIASES.items():
            for alias in aliases:
                patterns = (
                    rf"(我|用户|主人|Boss|boss|BOSS)的?{re.escape(alias)}",
                    rf"(他|她|其)的?{re.escape(alias)}",
                    rf"{re.escape(alias)}",
                )
                if any(re.search(pattern, text) for pattern in patterns):
                    return canonical
        return None

    def _coerce_external_entity_result(self, item):
        """Keep other people's facts out of core_profile even if the model labels them as NEW."""
        if not isinstance(item, dict):
            return item

        raw_entity = item.get("entity")
        entity = self._normalize_entity(raw_entity)
        if raw_entity and entity != "Boss":
            item["type"] = "ENTITY_UPDATE"
            item["entity"] = entity
            if "new_trait" not in item and "trait" in item:
                item["new_trait"] = item.pop("trait")
            return item

        text = " ".join(str(item.get(key, "")) for key in ("new_trait", "trait", "old_trait", "evidence"))
        inferred_entity = self._extract_external_entity_from_text(text)
        if inferred_entity:
            item["type"] = "ENTITY_UPDATE"
            item["entity"] = inferred_entity
            if "new_trait" not in item:
                item["new_trait"] = item.get("trait") or item.get("evidence")
        return item

    def _extract_identity_name(self, text):
        if not text:
            return None
        text = str(text).strip()
        if self._extract_external_entity_from_text(text):
            return None
        for pattern in self.NAME_PATTERNS:
            match = pattern.search(text)
            if not match:
                continue
            name = match.group(1).strip(" ，,。.;；!！?？\"'“”‘’")
            name = re.split(r"[，,。.;；!！?？\s]", name, maxsplit=1)[0].strip()
            if name and name not in self.NAME_STOP_WORDS:
                return name
        return None

    def _find_existing_name_fact(self, current_profile):
        facts = current_profile.get("facts", []) if isinstance(current_profile, dict) else []
        if not isinstance(facts, list):
            return None, None
        for fact in facts:
            name = self._extract_identity_name(fact)
            if name:
                return fact, name
        return None, None

    def _coerce_single_value_profile_result(self, item, current_profile):
        if not isinstance(item, dict):
            return item
        if item.get("type") != "NEW" or item.get("category") != "facts":
            return item

        new_trait = item.get("new_trait") or item.get("trait")
        new_name = self._extract_identity_name(new_trait)
        if not new_name:
            return item

        old_trait, old_name = self._find_existing_name_fact(current_profile)
        if not old_name:
            item["new_trait"] = new_trait
            return item
        if old_name == new_name:
            item["type"] = "DUPLICATE"
            item["old_trait"] = old_trait
            item["new_trait"] = new_trait
            return item

        item["type"] = "CONFLICT"
        item["category"] = "facts"
        item["old_trait"] = old_trait
        item["new_trait"] = new_trait
        return item

    def _normalize_profile_trait(self, trait):
        if not trait:
            return ""
        text = str(trait).strip()
        text = re.sub(r"^(用户|Boss|我|本人|自己)的?", "", text)
        text = text.replace("最爱吃的水果是", "喜欢吃")
        text = text.replace("最喜欢吃的水果是", "喜欢吃")
        text = text.replace("最喜欢的水果是", "喜欢吃")
        text = text.replace("爱吃", "喜欢吃")
        text = re.sub(r"[，,。.!！?？\s]", "", text)
        return text

    def _is_duplicate_profile_trait(self, current_profile, category, new_trait):
        new_key = self._normalize_profile_trait(new_trait)
        if not new_key:
            return False
        for old_trait in current_profile.get(category, []):
            old_key = self._normalize_profile_trait(old_trait)
            if old_trait == new_trait or old_key == new_key:
                return True
        return False

    def _coerce_profile_result_before_write(self, result):
        text = " ".join(str(result.get(key, "")) for key in ("new_trait", "trait", "evidence"))
        inferred_entity = self._extract_external_entity_from_text(text)
        if inferred_entity:
            result["type"] = "ENTITY_UPDATE"
            result["entity"] = inferred_entity
            if "new_trait" not in result and "trait" in result:
                result["new_trait"] = result.pop("trait")
        return result

    def _looks_like_query_memory(self, result):
        text = " ".join(str(result.get(key, "")) for key in ("new_trait", "trait", "evidence"))
        return bool(re.search(r"(用户询问|喜欢什么|什么水果|什么动物|叫什么|名字是什么|是谁|\?|？)", text))

    def _llm_arbitrator(self, current_profile, current_cognitive, new_traits, llm_caller):
        """真正的 LLM 仲裁引擎"""
        if not llm_caller:
            return []
        prompt = f"""
        你是 Vault OS 的潜意识记忆仲裁专家。
        【Type 1 物理基岩（关于 Boss 自身）】：{json.dumps(current_profile, ensure_ascii=False)}
        【Type 2 认知图谱】：{json.dumps(current_cognitive, ensure_ascii=False)}

        【最新提取的记忆碎片】：
        {json.dumps(new_traits, ensure_ascii=False)}

        【身份公理与绝对裁决法则】：
        1. 【自我统一性】：创造者(Boss)、“我”、“用户”、以及在基岩中记录的创造者真实姓名（如张三），在物理层面上是绝对的【同一个人】！
        2. 【核心基岩区（Boss本人情报）】：如果碎片描述的是 Boss 本人（无论 entity 字段写的是 Boss、我、用户还是真名）：
           - 🚨 物理隔离红线：绝对禁止使用 ENTITY_UPDATE 为创造者建立他人档案！
           - 若是全新情报，输出：{{"type": "NEW", "category": "分类名(如 facts/interests)", "new_trait": "特征描述"}}
           - 若与基岩旧情报矛盾，输出：{{"type": "CONFLICT", "category": "分类名", "old_trait": "旧特征", "new_trait": "新特征描述"}}
        3. 【他人情报区（独立实体档案）】：只有当碎片明确描述的是【真正的外部其他人】（如母亲、朋友李四）：
           - 🚨 物理隔离红线：绝对禁止将其写入 Boss 的基岩！绝对禁止输出 NEW 或 CONFLICT！
           - 必须且只能输出：{{"type": "ENTITY_UPDATE", "entity": "他人标准称呼", "new_trait": "客观特征"}}
        """
        try:
            print("  [仲裁官] 正在呼叫大模型进行判决...")
            response_data = llm_caller(prompt)
            if isinstance(response_data, dict): response_data = [response_data]
            results = []
            for item in response_data:
                item = self._coerce_external_entity_result(item)
                item = self._coerce_single_value_profile_result(item, current_profile)
                t = item.get("type")
                is_valid = False
                
                # 全局字段清洗：抹平大模型对 new_trait 和 trait 的混用
                if "trait" in item and "new_trait" not in item:
                    item["new_trait"] = item.pop("trait")
                
                if t == "NEW" and "new_trait" in item and "category" in item: 
                    is_valid = True
                    
                elif t == "CONFLICT" and "new_trait" in item and "category" in item: 
                    if "old_trait" not in item:
                        # 顺手把模型自己发明的 evidence 接住，当作 old_trait 的参考
                        item["old_trait"] = item.pop("evidence", "未知(大模型未提取)")
                    is_valid = True
                    
                elif t == "ENTITY_UPDATE" and "entity" in item:
                    if item["entity"] in ["我", "用户", "Boss", "Master", "本尊", "自己"]:
                        continue # 物理兜底，防止把Boss当别人
                    if "new_trait" in item:
                        is_valid = True
                    elif "trait" in item:
                        item["new_trait"] = item.pop("trait") 
                        is_valid = True
                        
                elif t == "COGNITIVE_UPDATE" and "domain" in item and "new_cognition" in item: 
                    is_valid = True

                elif t == "DUPLICATE":
                    print(f"ℹ️ [重复记忆] 已忽略重复的单值身份事实: {item.get('new_trait')}")
                    continue
                    
                if is_valid:
                    item["id"] = f"mem_{uuid.uuid4().hex[:8]}"
                    results.append(item)
                else:
                    print(f"⚠️ [防线拦截] 丢弃格式不完整的大模型幻觉碎片: {item}")          
            return results
        except Exception as e:
            print(f" [仲裁官] 大模型判决异常: {e}")
            return []

    def check_and_promote(self, llm_caller=None, entity_callback=None):
        self.run_garbage_collection()
        print("\n [晋升海关] 开始审计潜意识与时间流逝...")
        now = datetime.now()
        # 阶段 1：处理时间流逝（引爆过了 3 天的 PENDING 炸弹）
        with open(self.pending_path, 'r', encoding='utf-8') as f:
            pending_data = json.load(f)
        pending_queue = pending_data.get("queue", []) if isinstance(pending_data, dict) else pending_data
        if not isinstance(pending_queue, list):
            pending_queue = []
        with open(self.profile_path, 'r', encoding='utf-8') as f:
            current_profile = json.load(f)
        if not isinstance(current_profile, dict):
            current_profile = {}
        for profile_key in ("coding_style", "communication", "interests", "facts"):
            if not isinstance(current_profile.get(profile_key), list):
                current_profile[profile_key] = []
        with open(self.cognitive_path, 'r', encoding='utf-8') as f:
            current_cognitive = json.load(f)
        if not isinstance(current_cognitive, dict) or "nodes" in current_cognitive:
            current_cognitive = {}
        active_queue = []
        for item in pending_queue:
            if item["status"] == "PENDING":
                if item.get("type") == "ENTITY_UPDATE" or "category" not in item:
                    active_queue.append(item)
                    continue
                expire_time = datetime.fromisoformat(item["expires_at"])
                if now >= expire_time:
                    # 超过3天无操作，直接强行覆盖！
                    cat = item["category"]
                    # 覆写操作：移除旧的，加入新的
                    if item.get("old_trait") in current_profile[cat]:
                        current_profile[cat].remove(item["old_trait"])
                    current_profile[cat].append(item["new_trait"])   
                    item["status"] = "AUTO_OVERWRITTEN"
                    print(f" [超时裁决] 记忆冲突超期未处理，已强行覆写: {item['new_trait']}") 
                    # 写入黑盒
                    self._write_blackbox("TIMEOUT_OVERWRITE", item) 
            active_queue.append(item)
        # 阶段 2：处理新产生的暗影碎片
        fragments_files = glob.glob(f"{self.fragments_dir}/*.json")
        if fragments_files:
            print(f" 发现 {len(fragments_files)} 个新记忆指针，正在进行确定性分流...")
            new_traits = []
            routed_entity_traits = []
            routed_cognitive_traits = []
            valid_files = []
            for file in fragments_files:
                try:
                    with open(file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        action = data.get("action")
                        if action == "IGNORE":
                            valid_files.append(file)
                            continue
                        if action == "ENTITY_UPDATE":
                            source_entity = self.sanitize_entity_name(data.get("entity"))
                            new_trait = data.get("trait") or data.get("new_trait")
                            if source_entity and source_entity != "Boss" and new_trait:
                                routed_entity_traits.append({
                                    "type": "ENTITY_UPDATE",
                                    "entity": source_entity,
                                    "new_trait": new_trait,
                                    "evidence": data.get("evidence")
                                })
                                valid_files.append(file)
                            continue
                        if action == "COGNITIVE_UPDATE":
                            if data.get("domain") and data.get("new_cognition") is not None:
                                routed_cognitive_traits.append({
                                    "type": "COGNITIVE_UPDATE",
                                    "domain": data.get("domain"),
                                    "new_cognition": data.get("new_cognition"),
                                    "evidence": data.get("evidence")
                                })
                                valid_files.append(file)
                            continue
                        if action == "SELF_PROFILE_UPDATE":
                            new_trait = data.get("trait") or data.get("new_trait")
                            if new_trait:
                                new_traits.append({
                                    "type": "NEW",
                                    "category": data.get("category", "facts"),
                                    "new_trait": new_trait,
                                    "evidence": data.get("evidence")
                                })
                                valid_files.append(file)
                            continue
                        if action == "EXTRACT":
                            source_entity = self._normalize_entity(data.get("entity"))
                            if source_entity != "Boss":
                                safe_entity = self.sanitize_entity_name(source_entity)
                                if safe_entity:
                                    routed_entity_traits.append({
                                        "type": "ENTITY_UPDATE",
                                        "entity": safe_entity,
                                        "new_trait": data.get("trait") or data.get("new_trait"),
                                        "evidence": data.get("evidence")
                                    })
                            else:
                                new_traits.append(data)
                            valid_files.append(file) # 兼容旧碎片
                except Exception as e: 
                    print(f"⚠️ 无法读取碎片文件 {file}: {e}")
            # 呼叫 LLM 仲裁官进行分类
            arbitration_results = routed_entity_traits + routed_cognitive_traits
            if new_traits:
                arbitration_results.extend(self._llm_arbitrator(current_profile, current_cognitive, new_traits, llm_caller))
            # 核心容灾逻辑：只有当大模型成功返回了仲裁结果（哪怕是空列表，只要没报 Exception），才执行物理销毁！
            if arbitration_results is not None:
                for result in arbitration_results:
                    result = self._coerce_profile_result_before_write(result)
                    result["created_at"] = now.isoformat()
                    # 拦截他人情报，走绿色通道静默落盘，不进 UI 红点！
                    if result["type"] == "ENTITY_UPDATE":
                        safe_entity = self.sanitize_entity_name(result.get("entity"))
                        if not safe_entity or safe_entity == "Boss":
                            print(f"⚠️ [实体防线] 丢弃非法实体目标: {result.get('entity')}")
                            continue
                        result["entity"] = safe_entity
                        print(f"👤 [实体静默同步] 正在后台更新 {safe_entity} 的专属档案...")
                        if entity_callback:
                            entity_callback(safe_entity, result.get("new_trait"))
                        self._write_blackbox("SILENT_ENTITY_UPDATE", result)
                        continue
                    # 认知图谱静默覆写 (Type 2)
                    if result["type"] == "COGNITIVE_UPDATE":
                        domain = result.get("domain", "Unknown_Domain")
                        print(f"🧠 [认知升级] 正在后台静默重塑对【{domain}】的心智模型...")
                        # 覆盖更新该领域的认知
                        current_cognitive[domain] = result.get("new_cognition")
                        self._write_blackbox("SILENT_COGNITIVE_UPDATE", result)
                        continue # 直接放行，不进 UI 审批红点
                    # 规则 A：新增内容...
                    if result["type"] == "NEW":
                        if result.get("category") not in current_profile:
                            result["category"] = "facts"
                        if self._looks_like_query_memory(result):
                            result["status"] = "QUERY_IGNORED"
                            active_queue.append(result)
                            print(f"ℹ️ [查询污染] 已忽略疑似问句产生的画像条目: {result.get('new_trait')}")
                            self._write_blackbox("QUERY_MEMORY_IGNORED", result)
                            continue
                        if self._is_duplicate_profile_trait(current_profile, result["category"], result.get("new_trait")):
                            result["status"] = "DUPLICATE_IGNORED"
                            active_queue.append(result)
                            print(f"ℹ️ [重复画像] 已忽略重复画像条目: {result.get('new_trait')}")
                            self._write_blackbox("DUPLICATE_PROFILE_IGNORED", result)
                            continue
                        current_profile[result["category"]].append(result["new_trait"])
                        result["status"] = "MERGED"
                        active_queue.append(result)
                        print(f"✨ [秒速同化] 全新特质已直接写入基岩: {result['new_trait']}")
                        self._write_blackbox("INSTANT_MERGE", result)
                    # 规则 B：冲突内容...
                    elif result["type"] == "CONFLICT":
                        if result.get("category") not in current_profile:
                            result["category"] = "facts"
                        result["status"] = "PENDING"
                        result["expires_at"] = (now + timedelta(days=3)).isoformat()
                        active_queue.append(result)
                        print(f"⚠️ [记忆冲突] 发现冲突，已挂起并设定 3 天倒计时: {result['new_trait']}")
                        self._write_blackbox("CONFLICT_DETECTED", result)
                # 确认消费完毕，此时安全销毁物理文件！
                for file in valid_files:
                    try:
                        os.remove(file)
                    except: pass
            else:
                print(" 仲裁网络中断！为了保护记忆碎片，本次不销毁物理文件，等待下次重启重试。")
        # 阶段 3：统一落盘保存
        with open(self.profile_path, 'w', encoding='utf-8') as f:
            json.dump(current_profile, f, ensure_ascii=False, indent=2)
        with open(self.pending_path, 'w', encoding='utf-8') as f:
            json.dump({"queue": active_queue}, f, ensure_ascii=False, indent=2)
        with open(self.cognitive_path, 'w', encoding='utf-8') as f:
            json.dump(current_cognitive, f, ensure_ascii=False, indent=2)
        print(" [晋升海关] 审计与时空流转结算完毕。\n")

    def run_garbage_collection(self):
        """ 抹除超过 7 天的已归档记忆（绝不触碰黑盒）"""
        if not os.path.exists(self.pending_path):
            return
        try:
            with open(self.pending_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            queue = data.get("queue", []) if isinstance(data, dict) else data
            if not isinstance(queue, list):
                queue = []
            if not queue:
                return
            # 划定 7 天前的死亡警戒线
            seven_days_ago = datetime.now() - timedelta(days=7)
            new_queue = []
            deleted_count = 0
            for item in queue:
                # 🚨 绝对底线：永远保留 PENDING 状态的待办项（就算系统宕机错过强行同化，也不能乱删未决冲突）
                if item.get("status") == "PENDING":
                    new_queue.append(item)
                    continue
                # 尝试提取时间 (兼容 created_at 或 expires_at)
                item_time_str = item.get("created_at") or item.get("expires_at")
                if not item_time_str:
                    new_queue.append(item) # 没有时间戳的脏数据，保守保留
                    continue
                try:
                    # 将 ISO 格式字符串转化为 Python 时间对象 (处理末尾的 Z)
                    item_time = datetime.fromisoformat(item_time_str.replace("Z", "+00:00").split(".")[0])
                    # 如果只有 expires_at，说明这是条冲突记录，它的创建时间 = 强行同化时间 - 3天
                    if item.get("expires_at") and not item.get("created_at"):
                        item_time = item_time - timedelta(days=3)
                    # ⚡️ 判决：如果在 7 天内，保留；如果在 7 天外，直接无视（也就是物理删除）
                    if item_time > seven_days_ago:
                        new_queue.append(item)
                    else:
                        deleted_count += 1
                except Exception as e:
                    new_queue.append(item)
            # 只有当确实产生了垃圾清理时，才重新写入硬盘
            if deleted_count > 0:
                with open(self.pending_path, 'w', encoding='utf-8') as f:
                    json.dump({"queue": new_queue}, f, ensure_ascii=False, indent=2)
                print(f"🧹 [物理清理] 清道夫已彻底抹除 {deleted_count} 条远古记忆碎片。")
        except Exception as e:
            print(f"🚨 [物理清理异常] 清道夫发生故障: {e}")

    def inject_pending_memories(self, traits):
        """🌱 种子注入：将批量提取的初始记忆碎片打入缓冲队列"""
        try:
            with open(self.pending_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            queue = data.get("queue", []) if isinstance(data, dict) else data
            if not isinstance(queue, list):
                queue = []
            for t in traits:
                # 强制规范化：所有通过文档导入的记忆，初始状态均为 PENDING
                t["id"] = f"seed_{uuid.uuid4().hex[:8]}"
                t["status"] = "PENDING"
                t["created_at"] = datetime.now().isoformat()
                t["expires_at"] = (datetime.now() + timedelta(days=7)).isoformat()
                queue.append(t)
            with open(self.pending_path, 'w', encoding='utf-8') as f:
                json.dump({"queue": queue}, f, ensure_ascii=False, indent=2)   
            print(f"✅ [种子注入] 成功将 {len(traits)} 条初始记忆植入缓冲区。")
            return True
        except Exception as e:
            print(f"🚨 [注入失败] 写入缓冲队列时发生错误: {e}")
            return False

if __name__ == "__main__":
    gatekeeper = PromotionGatekeeper()
    gatekeeper.check_and_promote()
