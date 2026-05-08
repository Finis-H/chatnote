import os
import glob
import json
import uuid
from datetime import datetime, timedelta

class PromotionGatekeeper:
    def __init__(self):
        self.fragments_dir = "vault/active_tasks"
        self.profile_path = "vault/core_profile.json"
        self.pending_path = "vault/pending_memory.json"
        self.blackbox_path = "vault/memory_blackbox.jsonl" # 黑盒溯源
        self.cognitive_path = "vault/cognitive_map.json" # 认知图谱的物理路径
        self._init_files()

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

    def _write_blackbox(self, event_type, details):
        """记录绝对不可篡改的黑盒日志"""
        log_entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "event": event_type,
            "details": details
        }
        with open(self.blackbox_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

    def _llm_arbitrator(self, current_profile, current_cognitive, new_traits, llm_caller):
        """真正的 LLM 仲裁引擎"""
        if not llm_caller:
            return []
        prompt = f"""
        你是 Vault OS 的潜意识记忆仲裁专家。
        【Type 1 物理基岩】：{json.dumps(current_profile, ensure_ascii=False)}
        【Type 2 认知图谱】：{json.dumps(current_cognitive, ensure_ascii=False)}

        【最新提取的记忆碎片（含用户原话证据）】：
        {json.dumps(new_traits, ensure_ascii=False)}

        【绝对裁决法则】（仔细阅读）：
        1. 识别实体（他人）：主语是用户以外的人，必须输出 {{"type": "ENTITY_UPDATE", ...}}
        2. 物理界碑（Type 1）：关于用户的客观事实、生活偏好（例如“住在广州”、“讨厌香菜”），输出 NEW 或 CONFLICT。
        3. 认知流形（Type 2）：如果碎片反映了用户在某项【技术、知识、业务】上的【掌握程度、痛点、里程碑】（例如“今天搞懂了Tauri”、“看不懂财报”）。必须输出 COGNITIVE_UPDATE！

        【COGNITIVE_UPDATE 强制输出格式】：
        {{
            "type": "COGNITIVE_UPDATE",
            "domain": "提取出的领域名（如：Tauri, Python, 股票投资）",
            "new_cognition": {{
                "exposure_time": "如果基岩里没有该领域，写今天的日期；如果有，保持原样",
                "milestones_achieved": ["他已经做成了什么（结合旧图谱合并）"],
                "current_bottlenecks": ["他现在的痛点和卡点"],
                "mental_model": "他的理解视角（如：把 Rust 当黑盒）",
                "actionable_insight": "给大模型的建议（如：必须多用前端概念解释）"
            }}
        }}
        """
        try:
            print("⚖️  [仲裁官] 正在呼叫大模型进行时空与认知判决...")
            response_data = llm_caller(prompt)
            if isinstance(response_data, dict): response_data = [response_data]
            results = []
            for item in response_data:
                t = item.get("type")
                # 根据不同的类型，严格校验它该有的器官是否完整
                is_valid = False
                if t == "NEW" and "new_trait" in item and "category" in item: 
                    is_valid = True
                elif t == "CONFLICT" and "new_trait" in item and "old_trait" in item and "category" in item: 
                    is_valid = True
                elif t == "ENTITY_UPDATE" and "entity" in item and "new_trait" in item: 
                    is_valid = True
                elif t == "COGNITIVE_UPDATE" and "domain" in item and "new_cognition" in item: 
                    is_valid = True
                if is_valid:
                    item["id"] = f"mem_{uuid.uuid4().hex[:8]}"
                    results.append(item)
                else:
                    # 记录脏数据，坚决不让它弄脏下游的主控引擎
                    print(f"⚠️ [防线拦截] 丢弃格式不完整的大模型幻觉碎片: {item}")          
            return results
        except Exception as e:
            print(f"🚨 [仲裁官] 大模型判决异常: {e}")
            return []

    def check_and_promote(self, llm_caller=None, entity_callback=None):
        self.run_garbage_collection()
        print("\n🛂 [晋升海关] 开始审计潜意识与时间流逝...")
        now = datetime.now()
        # 阶段 1：处理时间流逝（引爆过了 3 天的 PENDING 炸弹）
        with open(self.pending_path, 'r', encoding='utf-8') as f:
            pending_data = json.load(f)
        with open(self.profile_path, 'r', encoding='utf-8') as f:
            current_profile = json.load(f)
        with open(self.cognitive_path, 'r', encoding='utf-8') as f:
            current_cognitive = json.load(f)
        active_queue = []
        for item in pending_data.get("queue", []):
            if item["status"] == "PENDING":
                expire_time = datetime.fromisoformat(item["expires_at"])
                if now >= expire_time:
                    # 🚨 触发你的强制规则：超过3天无操作，直接强行覆盖！
                    cat = item["category"]
                    # 覆写操作：移除旧的，加入新的
                    if item.get("old_trait") in current_profile[cat]:
                        current_profile[cat].remove(item["old_trait"])
                    current_profile[cat].append(item["new_trait"])   
                    item["status"] = "AUTO_OVERWRITTEN"
                    print(f"⏰ [超时裁决] 记忆冲突超期未处理，已强行覆写: {item['new_trait']}") 
                    # 写入黑盒
                    self._write_blackbox("TIMEOUT_OVERWRITE", item) 
            active_queue.append(item)
        # 阶段 2：处理新产生的暗影碎片
        fragments_files = glob.glob(f"{self.fragments_dir}/*.json")
        if fragments_files:
            print(f"🔍 发现 {len(fragments_files)} 个新暗影碎片，正在进行 LLM 仲裁...")
            new_traits = []
            valid_files = []
            for file in fragments_files:
                try:
                    with open(file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if data.get("action") == "EXTRACT": 
                            new_traits.append(data)
                            valid_files.append(file) # 记录下来，先不删！
                except Exception as e: 
                    print(f"⚠️ 无法读取碎片文件 {file}: {e}")
            # 呼叫 LLM 仲裁官进行分类
            arbitration_results = self._llm_arbitrator(current_profile, current_cognitive, new_traits, llm_caller)
            # 核心容灾逻辑：只有当大模型成功返回了仲裁结果（哪怕是空列表，只要没报 Exception），才执行物理销毁！
            if arbitration_results is not None:
                for result in arbitration_results:
                    result["created_at"] = now.isoformat()
                    # 拦截他人情报，走绿色通道静默落盘，不进 UI 红点！
                    if result["type"] == "ENTITY_UPDATE":
                        print(f"👤 [实体静默同步] 正在后台更新 {result.get('entity')} 的专属档案...")
                        if entity_callback:
                            entity_callback(result.get("entity"), result.get("new_trait"))
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
                        current_profile[result["category"]].append(result["new_trait"])
                        result["status"] = "MERGED"
                        active_queue.append(result)
                        print(f"✨ [秒速同化] 全新特质已直接写入基岩: {result['new_trait']}")
                        self._write_blackbox("INSTANT_MERGE", result)
                    # 规则 B：冲突内容...
                    elif result["type"] == "CONFLICT":
                        result["status"] = "PENDING"
                        result["expires_at"] = (now + timedelta(days=3)).isoformat()
                        active_queue.append(result)
                        print(f"⚠️ [记忆冲突] 发现冲突，已挂起并设定 3 天倒计时: {result['new_trait']}")
                        self._write_blackbox("CONFLICT_DETECTED", result)
                # 🔪 确认消费完毕，此时安全销毁物理文件！
                for file in valid_files:
                    try:
                        os.remove(file)
                    except: pass
            else:
                print("🚨 仲裁网络中断！为了保护记忆碎片，本次不销毁物理文件，等待下次重启重试。")
        # 阶段 3：统一落盘保存
        with open(self.profile_path, 'w', encoding='utf-8') as f:
            json.dump(current_profile, f, ensure_ascii=False, indent=2)
        with open(self.pending_path, 'w', encoding='utf-8') as f:
            json.dump({"queue": active_queue}, f, ensure_ascii=False, indent=2)
        with open(self.cognitive_path, 'w', encoding='utf-8') as f:
            json.dump(current_cognitive, f, ensure_ascii=False, indent=2)
        print("✅ [晋升海关] 审计与时空流转结算完毕。\n")

    def run_garbage_collection(self):
        """ 抹除超过 7 天的已归档记忆（绝不触碰黑盒）"""
        if not os.path.exists(self.pending_path):
            return
        try:
            with open(self.pending_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            queue = data.get("queue", [])
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
            queue = data.get("queue", [])
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