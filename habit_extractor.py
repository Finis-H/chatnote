from memory_rules import is_transient_interaction


class HabitExtractor:
    def __init__(self):
        # The v3.1 memory path buffers candidate observations and extracts them in batches.
        pass

    def should_buffer(self, user_input: str) -> bool:
        text = str(user_input or "").strip()
        if not text:
            return False
        return not is_transient_interaction(text)

    def analyze_input(self, user_input: str, llm_caller=None, chat_history=None):
        """Legacy call site guard: realtime extraction is intentionally disabled."""
        if not self.should_buffer(user_input):
            print("🛡️ [记忆预检] 瞬时交互已跳过，不进入长期记忆缓冲池。")
            return []
        return [{
            "target_entity": "Boss",
            "action_category": "PROFILE",
            "action_detail": "facts",
            "context": str(user_input or "").strip(),
            "confidence": 0.5,
            "requires_review": True,
        }]
