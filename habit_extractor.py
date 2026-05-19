import os
import json
from main import VAULT_ROOT
import time

class HabitExtractor:    
    def __init__(self):
        # 定义碎片存放目录，不再维护旧版的 habits.json
        self.fragments_dir = os.path.join(VAULT_ROOT, "active_tasks")
        os.makedirs(self.fragments_dir, exist_ok=True)

    def analyze_input(self, user_input: str, llm_caller, chat_history=None):
        """静默扫描并生成 JSON 碎片"""
        # 1. 提取近期上下文（防代词指代丢失）
        context_str = "暂无近期对话上下文"
        if chat_history and isinstance(chat_history, list):
            # 取最后 4 条（即最近的两轮对话）
            recent_msgs = chat_history[-4:]
            context_str = "\n".join([f"[{m.get('role', 'UNKNOWN').upper()}]: {m.get('content', '')}" for m in recent_msgs])
        # 极客风：给大模型下达不容置疑的 JSON 指令
        system_prompt = f"""
        你是 Vault OS 的前哨潜意识捕捉器 (Scout)。
        你的唯一任务是判断用户的输入中，是否包含需要被长期记忆的【高价值情报】。

        【当前对话上下文（非常重要！用于推断代词如"她"、"这"的意思）】：
        {context_str}

        【高价值情报必须包含以下三类之一】：
        1. 物理事实与习惯 (Type 1)：主人的客观事实、生活偏好（如喜欢吃什么、住在哪里）。
        2. 实体情报 (Type 1)：主人社交圈/身边实体的喜好与事实（如家人、老板、朋友）。
        3. 认知与状态 (Type 2) 🚨最高优先级：主人当前正在使用的【技术栈】、涉及的【业务领域】、遇到的【技术卡点】、技能【熟练度】或【项目进度】（例如：“我在用 Tauri 设计前端”、“我遇到一个跨域报错”、“我对这个不太熟”）。

        【裁决逻辑】：
        - 只要包含上述任何一类信息（即使是一句抱怨中带了技术栈，如“Tauri 的 UI 真难写”），都必须输出 EXTRACT 指令！
        - 只有当输入是纯粹的寒暄、毫无信息量的纯提问（如“你好”、“这怎么办”），且结合上下文也提炼不出任何用户状态时，才输出：{{"action": "IGNORE"}}

        【EXTRACT 输出格式】（必须是纯 JSON，注意双花括号转义）：
        {{
            "action": "EXTRACT",
            "category": "facts",
            "new_trait": "提取出的完整陈述（必须消除代词并补全上下文！例如把'我在用它'还原为'用户正在使用 Tauri 设计前端，并感觉 UI 不够漂亮'）",
            "evidence": "用户的原话"
        }}
        """
        try:
            # 统一参数名，调用外部传入的大模型执行器
            result_json = llm_caller(system_prompt, user_input)
            
            # 如果成功抓取到特质，物理落地
            if result_json and result_json.get("action") == "EXTRACT":
                self._save_fragment(result_json)
        except Exception as e:
            print(f"🕵️ [暗影守护者] 分析异常: {e}")

    def _save_fragment(self, data):
        """将提取到的 JSON 碎片落地到硬盘，等待审计"""
        timestamp = int(time.time() * 1000)
        file_path = os.path.join(self.fragments_dir, f"trait_{timestamp}.json")
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"🕵️ [暗影守护者] 碎片落地失败: {e}")
