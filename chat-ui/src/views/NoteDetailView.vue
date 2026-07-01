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
.scroll-container { padding: var(--space-3xl); display: flex; flex-direction: column; height: 100%; overflow-y: auto; }
.scroll-container::-webkit-scrollbar { width: 6px; }
.scroll-container::-webkit-scrollbar-thumb { background: var(--border-strong); border-radius: var(--radius-xs); }
.note-body { border-bottom: 1px solid var(--border-subtle); padding-bottom: var(--space-4xl); margin-bottom: var(--space-xl); }
.note-body h1 { color: var(--text-primary); margin-bottom: var(--space-xl); font-size: 22px; }
.back-link { background: transparent; border: 1px solid var(--border-strong); color: var(--text-muted); padding: var(--space-xs) var(--space-md); border-radius: var(--radius-xs); cursor: pointer; margin-bottom: var(--space-xl); font-family: var(--font-mono); }
.back-link:hover { color: var(--text-primary); border-color: var(--text-secondary); }
.thread-separator { text-align: center; color: var(--text-disabled); font-size: 11px; letter-spacing: 3px; margin: var(--space-3xl) 0; }
.thread-chat { display: flex; flex-direction: column; gap: var(--space-xl); }
.bubble { padding: var(--space-md) 16px; border-radius: var(--radius-sm); font-size: 14px; max-width: 85%; line-height: 1.6; }
.user { background: var(--bg-panel-raised); align-self: flex-end; border-right: 2px solid var(--border-strong); color: var(--text-primary); }
.ai, .assistant { background: var(--accent-soft); align-self: flex-start; border-left: 2px solid var(--accent-border); color: var(--text-secondary); }
.role-tag { font-size: 10px; opacity: 0.4; display: block; margin-bottom: 5px; }
.thinking-cursor { color: var(--accent); font-size: 12px; animation: pulse 1.5s infinite; padding: var(--space-sm); }
@keyframes pulse { 0%, 100% { opacity: 0.5; } 50% { opacity: 1; } }
</style>
