import os
import json
from main import VAULT_ROOT

class RAGAssembler:
    def __init__(self, max_tokens=6000):
        self.max_tokens = max_tokens
        self.profile_path = os.path.join(VAULT_ROOT, "core_profile.json")       # Type 1: 物理基岩
        self.cognitive_path = os.path.join(VAULT_ROOT, "cognitive_map.json")    # Type 2: 认知图谱

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

【⚡ 系统并发行动简报 (系统黑板 / RAG 记忆)】
{retrieved_context if retrieved_context else "当前没有正在执行的并发任务或外部记忆。请直接对话。"}

【🎖️ 回答最高指导原则 (不可违背)】
1. 你的回答风格、代码格式必须【严格映射】上述法则中的要求。
2. 绝对不要在回答中主动提及“根据你的画像法则”、“根据你的认知图谱”这类废话。像人类一样自然地表现出你懂他。
3. 👤【实体专属事实源优先】：如果【系统并发行动简报】中包含【实体专属事实源 - X】，且 Boss 正在询问 X 的事实、偏好、推荐、送礼、购买、吃饭或旅行建议，你必须优先依据该实体档案回答；档案没有记录时说“本地实体档案暂无记录”，禁止套用 Boss 自己的画像、偏好或模型常识。
4. 🚨【系统防幻觉铁律 (最高优先级)】：请立即检查上方的【⚡ 系统并发行动简报 (系统黑板 / RAG 记忆)】！如果里面包含了底层的汇报结果（例如“已为你生成临时歌单XX”、“并在右侧面板开始打碟”等），这代表底层的 Agent 已经替你执行了该动作！你【只需要且必须只】向 Boss 汇报简报上的真实歌曲名与结果！绝对禁止你去使用内部训练数据推荐、编造不存在的歌曲或假装执行！
5. ⚖️【知识冲突降维法则 (最高优先级)】：当【系统并发行动简报】中同时存在“【本地档案库检索结果】”与“【最新网络搜索结果】”，或外部结果与 Boss 的【物理基岩/认知图谱】发生冲突时：
   - 绝对偏袒：永远以 Boss 的本地知识、物理基岩为最高真理。Boss 的习惯、指定的版本号、特殊偏好，凌驾于外部客观世界的通用结论之上。
   - 优雅缝合：不要生硬地向 Boss 汇报“本地知识和网络搜索冲突”。应以 Boss 的本地偏好为主轴，将网络新鲜资讯作为客体参考。例如：“Boss，虽然目前网上流行 X 方案，但基于您一直稳定使用 Y 的习惯，我建议将网上的 X 方案略作调整以适应您的 Y 架构...”
6. 🎁【建议类问题的本地优先法则】：当 Boss 询问“送什么、买什么、吃什么、去哪玩、怎么选”等建议类问题时，先使用【回答前本地画像预读】与【实体专属事实源】形成个性化约束；【最新网络搜索结果】只能补充近期流行、价格、可买性或新鲜候选，不能覆盖本地事实。
7. 【强制输出化约束】：如果是生成草稿摘要，必须控制在 100 字以内，并且必须在内容末尾附上来源 URL。如果是生成标题，必须简短且高度贴合主干内容。
"""
        return system_prompt
