<script setup>
import { ref, watch, nextTick } from 'vue';
import { currentNote, noteThreads, isThinking, previousView, useNeuroLink } from '../composables/useNeuroLink';
import CyberMarkdown from '../components/CyberMarkdown.vue';

const { switchView } = useNeuroLink();
const viewportRef = ref(null);
const scrollViewport = () => { if (viewportRef.value) viewportRef.value.scrollTop = viewportRef.value.scrollHeight; };
watch([noteThreads, isThinking], () => nextTick(scrollViewport), { deep: true });

</script>

<template>
  <div class="scroll-container note-view" ref="viewportRef">
    <div class="note-body">
      <button class="back-link" @click="switchView(previousView)">← 返回列表</button>
      <h1>{{ currentNote.title }}</h1>
      <CyberMarkdown :text="currentNote.content" />
    </div>
    <div class="thread-separator">讨论线程 (CONTEXT_THREAD)</div>
    <div class="thread-chat">
      <div v-for="(m, i) in noteThreads[currentNote.id]" :key="i" :class="['bubble', m.role]">
        <span class="role-tag">{{ m.role === 'user' ? 'BOSS' : 'AI' }}</span>
        <CyberMarkdown :text="m.content" />
      </div>
      <div v-if="isThinking" class="thinking-cursor">🧠 大脑全速运转中...</div>
    </div>
  </div>
</template>

<style scoped>
.scroll-container { padding: 30px; display: flex; flex-direction: column; height: 100%; overflow-y: auto; }
.scroll-container::-webkit-scrollbar { width: 6px; }
.scroll-container::-webkit-scrollbar-thumb { background: #333; border-radius: 3px; }
.note-body { border-bottom: 1px solid #222; padding-bottom: 40px; margin-bottom: 20px; }
.note-body h1 { color: #fff; margin-bottom: 20px; font-size: 22px; }
.back-link { background: transparent; border: 1px solid #444; color: #888; padding: 5px 12px; border-radius: 4px; cursor: pointer; margin-bottom: 20px; font-family: 'Consolas'; }
.back-link:hover { color: #fff; border-color: #fff; }
.thread-separator { text-align: center; color: #444; font-size: 11px; letter-spacing: 3px; margin: 30px 0; }
.thread-chat { display: flex; flex-direction: column; gap: 20px; }
.bubble { padding: 12px 16px; border-radius: 6px; font-size: 14px; max-width: 85%; line-height: 1.6; }
.user { background: #1a1a1c; align-self: flex-end; border-right: 2px solid #555; color: #eee; }
.ai, .assistant { background: rgba(0,255,204,0.03); align-self: flex-start; border-left: 2px solid #00ffcc; color: #ccc; }
.role-tag { font-size: 10px; opacity: 0.4; display: block; margin-bottom: 5px; }
.thinking-cursor { color: #00ffcc; font-size: 12px; animation: pulse 1.5s infinite; padding: 10px; }
@keyframes pulse { 0%, 100% { opacity: 0.5; } 50% { opacity: 1; } }
</style>