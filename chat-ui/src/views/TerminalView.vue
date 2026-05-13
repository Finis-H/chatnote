<script setup>
import { ref, computed, watch, nextTick } from 'vue';
import { globalMessages, isThinking, activeView } from '../composables/useNeuroLink';
import CyberMarkdown from '../components/CyberMarkdown.vue';

const viewportRef = ref(null);
// 视觉切片状态：1 轮对话 = 1个User + 1个AI，6轮就是 12 条消息
const PAGE_SIZE = 12; 
const displayLimit = ref(PAGE_SIZE);
let isFetchingMore = false; // 防抖锁

// ✨ 2. 消息解析引擎：分离纯文本与交互卡片
const processedMessages = computed(() => {
  let baseMessages = globalMessages.value;
  if (baseMessages.length > displayLimit.value) {
    baseMessages = baseMessages.slice(-displayLimit.value);
  }

  return baseMessages.map(m => {
    return {
      ...m,
      displayContent: m.content 
    };
  });
});
const scrollViewport = () => { if (viewportRef.value) viewportRef.value.scrollTop = viewportRef.value.scrollHeight; };
// 监听正常对话的新消息触底
watch([globalMessages, isThinking], () => {
  // 如果当前正在往上翻看历史，不要强行把用户拽到底部
  if (!isFetchingMore) {
    nextTick(scrollViewport);
  }
}, { deep: true });
// 监听视图切换时的置底
watch(activeView, (newVal) => {
  if (newVal === 'chat') {
    nextTick(scrollViewport);
  }
});
// 上滑加载更多逻辑
const handleScroll = async (e) => {
  const container = e.target;
  // 触发条件：滚动到顶部，且还有未展示的历史数据
  if (container.scrollTop === 0 && displayLimit.value < globalMessages.value.length) {
    isFetchingMore = true;
    // 1. 记录加载前的历史总高度
    const previousHeight = container.scrollHeight;
    // 2. 扩大展示窗口
    displayLimit.value += PAGE_SIZE;
    // 3. 等待 Vue 完成新一轮的 DOM 插入和 Markdown 渲染
    await nextTick();
    // 4. 高度补偿：把滚动条推回到用户刚才看的位置，实现无缝加载
    const newHeight = container.scrollHeight;
    container.scrollTop = newHeight - previousHeight;
    // 稍微延迟释放防抖锁，防止连续触发
    setTimeout(() => { isFetchingMore = false; }, 100);
  }
};
</script>

<template>
  <div class="scroll-container" ref="viewportRef" @scroll="handleScroll">
    
    <div v-if="displayLimit >= globalMessages.length && globalMessages.length > 0" class="history-end">
      —— 已追溯至记忆链路的尽头 ——
    </div>
    
    <div v-for="(m, i) in processedMessages" :key="'msg_'+i" :class="['bubble', m.role]">
      <CyberMarkdown v-if="m.displayContent" :text="m.displayContent" />
    </div>
    <div v-if="isThinking" class="thinking-cursor">🧠 大脑全速运转中...</div>
  </div>
</template>

<style scoped>
.scroll-container { padding: 30px; display: flex; flex-direction: column; gap: 20px; height: 100%; overflow-y: auto; scroll-behavior: smooth; }
.scroll-container::-webkit-scrollbar { width: 6px; }
.scroll-container::-webkit-scrollbar-thumb { background: #333; border-radius: 3px; }
.history-end { text-align: center; color: #444; font-size: 11px; letter-spacing: 2px; margin-bottom: 10px; }
.bubble { padding: 12px 16px; border-radius: 6px; font-size: 14px; max-width: 85%; line-height: 1.6; }
.user { background: #1a1a1c; align-self: flex-end; border-right: 2px solid #555; color: #eee; }
.ai, .assistant { background: rgba(0,255,204,0.03); align-self: flex-start; border-left: 2px solid #00ffcc; color: #ccc; }
.thinking-cursor { color: #00ffcc; font-size: 12px; animation: pulse 1.5s infinite; padding: 10px; }
@keyframes pulse { 0%, 100% { opacity: 0.5; } 50% { opacity: 1; } }
</style>