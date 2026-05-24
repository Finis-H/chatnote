import os
import json
from main import VAULT_ROOT

def init_vault():
    # 1. 定义物理目录结构
    directories = [
        os.path.join(VAULT_ROOT, "core"),           # Layer 3: 核心基岩 (digital_twin.json)
        os.path.join(VAULT_ROOT, "knowledge", "entities"), # Layer 3: 外部实体画像
        os.path.join(VAULT_ROOT, "shadow"),         # Layer 2: 观察沙盒
        os.path.join(VAULT_ROOT, "knowledge/inbox"),# Layer 1: 原始输入/抓取
        os.path.join(VAULT_ROOT, "knowledge/archives"), # 经过融合的知识
        os.path.join(VAULT_ROOT, "active_tasks"),   # 任务断点快照
        os.path.join(VAULT_ROOT, "cache")           # Layer 1: 对话缓存 (TTL)
    ]

    for folder in directories:
        os.makedirs(folder, exist_ok=True)
        print(f"✅ 已就绪: {folder}")

    # 2. 初始化核心画像标准 (digital_twin.json)
    digital_twin_path = os.path.join(VAULT_ROOT, "core", "digital_twin.json")
    if not os.path.exists(digital_twin_path):
        initial_profile = {
            "version": "1.0",
            "owner": "Boss",
            "mindset": {
                "core_principles": [
                    "数据架构先于代码实现",
                    "极简主义，拒绝过度封装",
                    "沟通先说结论，超过100字必加Markdown"
                ],
                "tech_preference": ["Python", "Markdown", "Docker", "Jina"]
            },
            "communication_style": {
                "tone": "Architect/Geek",
                "prohibited_phrases": ["作为一个AI助手...", "我建议...", "可能..."]
            }
        }
        with open(digital_twin_path, 'w', encoding='utf-8') as f:
            json.dump(initial_profile, f, indent=4, ensure_ascii=False)
        print(f"✨ 核心画像已生成: {digital_twin_path}")

if __name__ == "__main__":
    init_vault()
