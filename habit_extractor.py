import re

class HabitExtractor:    
    def __init__(self):
        # v2 memory core no longer uses JSON fragment files.
        pass

    def analyze_input(self, user_input: str, llm_caller, chat_history=None):
        """静默路由用户输入，返回候选记忆事件。"""
        question_pattern = r"(\?|？|什么|谁|哪|哪里|多少|为什么|怎么|如何|吗|呢|推荐|建议|送.*礼物|买什么|购买|选择|选什么|去哪|吃什么)"
        if re.search(question_pattern, user_input or ""):
            print("🕵️ [记忆 Router] 检测到查询语句，跳过画像写入。")
            return []
        # 1. 提取近期上下文（防代词指代丢失）
        context_str = "暂无近期对话上下文"
        if chat_history and isinstance(chat_history, list):
            # 取最后 4 条（即最近的两轮对话）
            recent_msgs = chat_history[-4:]
            context_str = "\n".join([f"[{m.get('role', 'UNKNOWN').upper()}]: {m.get('content', '')}" for m in recent_msgs])
        system_prompt = f"""
        你是 Vault OS 的记忆 Router。
        你的唯一任务是阅读用户当前输入，判断它是否包含需要写入本地长期记忆的事实。
        你只做语义路由，不决定文件路径，不读取任何本地文件。
        只能从【当前用户输入】提取新记忆；下方历史上下文只允许用于代词消解，绝不能把历史消息或 assistant 回复当作新事实写入。

        【当前对话上下文（非常重要！用于推断代词如"她"、"这"的意思）】：
        {context_str}

        【合法 action】：
        1. IGNORE：寒暄、提问、查询、命令、瞬时交互，没有长期记忆价值。
        2. SELF_PROFILE_UPDATE：Boss 自身的客观事实、偏好、沟通方式、编程习惯。
        3. ENTITY_UPDATE：Boss 身边其他人或实体的事实与偏好。
        4. COGNITIVE_UPDATE：Boss 当前技术栈、项目状态、领域理解、卡点、熟练度或洞察。

        【输出 Schema】：
        - 无记忆价值：{{"action": "IGNORE"}}
        - Boss 自身画像：{{"action": "SELF_PROFILE_UPDATE", "trait": "完整事实", "category": "facts|interests|communication|coding_style"}}
        - 他人实体画像：{{"action": "ENTITY_UPDATE", "entity": "标准称呼", "trait": "完整事实"}}
        - 认知图谱：{{"action": "COGNITIVE_UPDATE", "domain": "领域名", "new_cognition": {{"current_bottlenecks": [], "mental_model": "", "actionable_insight": ""}}}}

        【强制规则】：
        - 必须输出合法纯 JSON，禁止解释文字。
        - “我父亲喜欢吃西瓜”是 ENTITY_UPDATE，entity 是“父亲”。
        - “我喜欢吃西瓜”是 SELF_PROFILE_UPDATE。
        - “帮我查天气”“我父亲喜欢什么水果？”必须 IGNORE。
        - “Tauri 的 UI 真难写，我卡在窗口通信上”是 COGNITIVE_UPDATE。
        - 一句话包含多条事实时，输出 JSON 数组。
        """
        try:
            # 统一参数名，调用外部传入的大模型执行器
            result_json = llm_caller(system_prompt, user_input)
            if isinstance(result_json, list):
                return [item for item in result_json if isinstance(item, dict) and item.get("action") != "IGNORE"]
            if isinstance(result_json, dict) and result_json.get("action") != "IGNORE":
                return [result_json]
            return []
        except Exception as e:
            print(f"🕵️ [暗影守护者] 分析异常: {e}")
            return []
