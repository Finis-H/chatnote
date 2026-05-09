<script setup>
import { ref, watch, nextTick } from 'vue';
import { globalMessages, isThinking } from '../composables/useNeuroLink';
import CyberMarkdown from '../components/CyberMarkdown.vue';

const viewportRef = ref(null);
const scrollViewport = () => { if (viewportRef.value) viewportRef.value.scrollTop = viewportRef.value.scrollHeight; };
watch([globalMessages, isThinking], () => nextTick(scrollViewport), { deep: true });

</script>

<template>
  <div class="scroll-container" ref="viewportRef">
    <div v-for="(m, i) in globalMessages" :key="i" :class="['bubble', m.role]">
      <CyberMarkdown :text="m.content" />
    </div>
    <div v-if="isThinking" class="thinking-cursor">🧠 大脑全速运转中...</div>
  </div>
</template>

<style scoped>
.scroll-container { padding: 30px; display: flex; flex-direction: column; gap: 20px; height: 100%; overflow-y: auto; }
.scroll-container::-webkit-scrollbar { width: 6px; }
.scroll-container::-webkit-scrollbar-thumb { background: #333; border-radius: 3px; }
.bubble { padding: 12px 16px; border-radius: 6px; font-size: 14px; max-width: 85%; line-height: 1.6; }
.user { background: #1a1a1c; align-self: flex-end; border-right: 2px solid #555; color: #eee; }
.ai, .assistant { background: rgba(0,255,204,0.03); align-self: flex-start; border-left: 2px solid #00ffcc; color: #ccc; }
.thinking-cursor { color: #00ffcc; font-size: 12px; animation: pulse 1.5s infinite; padding: 10px; }
@keyframes pulse { 0%, 100% { opacity: 0.5; } 50% { opacity: 1; } }
</style>