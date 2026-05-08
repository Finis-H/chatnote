import os
import json

class RAGAssembler:
    def __init__(self, max_tokens=6000):
        self.max_tokens = max_tokens
        self.profile_path = "vault/core_profile.json"       # Type 1: 物理基岩
        self.cognitive_path = "vault/cognitive_map.json"    # Type 2: 认知图谱

    def _load_json(self, path):
        """通用 JSON 读取器"""
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"🚨 读取 {path} 失败: {e}")
        return {}

    def _format_profile(self, profile):
        """将 Type 1 物理基岩翻译成强约束指令"""
        if not profile:
            return "暂无特别设定的客观事实与习惯。"
        
        lines = []
        for category, traits in profile.items():
            if traits:
                cat_name = {
                    "coding_style": "💻 代码与技术法则",
                    "communication": "🗣️ 沟通与表达风格",
                    "interests": "🎯 关注点与兴趣",
                    "facts": "📌 核心事实记忆"
                }.get(category, category.upper())
                
                lines.append(f"[{cat_name}]:")
                for t in traits:
                    lines.append(f"  - {t}")
        return "\n".join(lines) if lines else "暂无特别设定的客观事实与习惯。"

    def _format_cognitive(self, cog_map):
        """🧠 将 Type 2 认知图谱翻译成大模型的'透视眼镜'"""
        if not cog_map:
            return "暂无特定领域的认知与技能记录。"
            
        lines = []
        for domain, data in cog_map.items():
            lines.append(f"[{domain} 领域当前认知]:")
            if data.get("current_bottlenecks"):
                lines.append(f"  - ⚠️ 当前卡点: {', '.join(data['current_bottlenecks'])}")
            if data.get("mental_model"):
                lines.append(f"  - 🧩 心智模型: {data['mental_model']}")
            if data.get("actionable_insight"):
                lines.append(f"  - 💡 对接策略: {data['actionable_insight']}")
        return "\n".join(lines)

    def assemble(self, user_input, retrieved_context=""):
        """
        组装终极 System Prompt
        :param user_input: 用户的原始问题
        :param retrieved_context: 从 ChromaDB 里查到的 Markdown 碎片文本 (Type 3)
        """
        # 1. 获取两层潜意识
        profile_text = self._format_profile(self._load_json(self.profile_path))
        cognitive_text = self._format_cognitive(self._load_json(self.cognitive_path))

        # 2. 注入灵魂：缝合潜意识、认知状态、外脑记忆与绝对格式约束
        system_prompt = f"""
你是 Vault OS 的极客大管家。你正在与你的创造者/Boss 进行对话。
你必须绝对忠诚，并将以下信息作为你的“底层思维网格”：

========================================
【🧱 Type 1 物理基岩 (客观事实与习惯)】
{profile_text}

【🧠 Type 2 认知图谱 (Boss当前的技能状态与痛点)】
{cognitive_text}
(警告：请严格参考上述认知图谱来决定你的回答深度、是否需要类比，以及避坑策略！)
========================================

【📚 Type 3 检索到的外脑物理记忆】
{retrieved_context if retrieved_context else "当前未命中任何外部知识。请直接使用你的内部算力和法则进行回答。"}

【🎖️ 回答最高指导原则 (不可违背)】
1. 你的回答风格、代码格式必须【严格映射】上述法则中的要求。
2. 绝对不要在回答中主动提及“根据你的画像法则”、“根据你的认知图谱”这类废话。像人类一样自然地表现出你懂他。
3. 如果外部知识中有答案，优先提炼外部知识；如果没有，大胆使用本体知识，但绝不编造。
4. 【强制输出化约束】：如果是生成草稿摘要，必须控制在 100 字以内，并且必须在内容末尾附上来源 URL。如果是生成标题，必须简短且高度贴合主干内容。
"""
        return system_prompt