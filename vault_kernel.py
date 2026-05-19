import json
import os
from main import VAULT_ROOT

class VaultKernel:
    def __init__(self):
        self.core_path = os.path.join(VAULT_ROOT, "core", "digital_twin.json")
        self.profile = self._load_profile()

    def _load_profile(self):
        with open(self.core_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def generate_system_prompt(self, current_task_context=""):
        """🧠 思维注入：将本地 JSON 法则转化为系统级约束"""
        mindset = self.profile['mindset']
        style = self.profile['communication_style']
        
        system_prompt = f"""
# ROLE
你不再是一个通用的AI，你是 Vault OS 的执行中枢，是老板思维的数字分身。

# CORE PRINCIPLES
{chr(10).join([f"- {p}" for p in mindset['core_principles']])}

# STYLE CONSTRAINTS
- 语气: {style['tone']}
- 禁忌语: {', '.join(style['prohibited_phrases'])}
- 格式: 严格遵守 Markdown 规范。

# CURRENT CONTEXT
{current_task_context}
"""
        return system_prompt.strip()

    def execute_task(self, user_input):
        # 1. 准备上下文（这里后续接入 Layer 1 和 RAG）
        system_msg = self.generate_system_prompt()
        
        # 2. 模拟调用 API (这里接入 Qwen 或 GPT)
        print("--- [DEBUG: 发送给模型的 System Prompt] ---")
        print(system_msg)
        print("--- [DEBUG: 用户输入] ---")
        print(user_input)
        
        # 实际代码中，这里会调用 LLM 客户端并返回结果
        return "管家已就绪，正在按您的准则处理..."

if __name__ == "__main__":
    kernel = VaultKernel()
    kernel.execute_task("帮我写一个数据抓取的 Python 脚本。")