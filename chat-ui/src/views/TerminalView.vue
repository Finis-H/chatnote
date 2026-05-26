<script setup>
import { ref, computed, watch, nextTick } from 'vue';
import {
  globalMessages,
  isThinking,
  activeView,
  traceEvents,
  activeTraceId,
  isTracePanelOpen,
  traceSummary,
  toggleTracePanel
} from '../composables/useNeuroLink';
import CyberMarkdown from '../components/CyberMarkdown.vue';

const viewportRef = ref(null);
const manuallyExpandedSpans = ref(new Set());
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
const traceChildCount = computed(() => {
  const counts = {};
  traceEvents.value.forEach(event => {
    if (event.parent_span_id) {
      counts[event.parent_span_id] = (counts[event.parent_span_id] || 0) + 1;
    }
  });
  return counts;
});
const latestTraceMap = computed(() => {
  const map = {};
  traceEvents.value.forEach(event => { map[event.span_id] = event; });
  return map;
});
const visibleTraceEvents = computed(() => {
  return traceEvents.value.filter(event => {
    let parentId = event.parent_span_id;
    while (parentId) {
      const parent = latestTraceMap.value[parentId];
      if (!parent) return true;
      if (parent.collapsed && !manuallyExpandedSpans.value.has(parent.span_id)) return false;
      parentId = parent.parent_span_id;
    }
    return true;
  });
});
const traceButtonLabel = computed(() => {
  if (traceSummary.value.runningCount > 0) return `观测 ${traceSummary.value.runningCount}`;
  if (traceSummary.value.failedCount > 0) return `观测 ${traceSummary.value.failedCount}`;
  return traceSummary.value.totalCount > 0 ? `观测 ${traceSummary.value.totalCount}` : '观测';
});
const terminalStatusText = computed(() => {
  if (!activeTraceId.value) return '等待指令';
  if (traceSummary.value.status === 'RUNNING') return '执行中';
  if (traceSummary.value.status === 'FAILED') return '需要查看';
  return '已就绪';
});
function traceLevel(event) {
  let level = 0;
  let parentId = event.parent_span_id;
  while (parentId && latestTraceMap.value[parentId]) {
    level += 1;
    parentId = latestTraceMap.value[parentId].parent_span_id;
  }
  return Math.min(level, 4);
}
function statusText(status) {
  const labels = {
    RUNNING: '运行中',
    SUCCESS: '完成',
    FAILED: '失败',
    TIMEOUT: '超时',
    ABORTED: '已中断',
    BLOCKED: '阻塞',
    IDLE: '空闲'
  };
  return labels[status] || status;
}
function toggleTraceNode(event) {
  if (!traceChildCount.value[event.span_id]) return;
  const next = new Set(manuallyExpandedSpans.value);
  if (next.has(event.span_id)) next.delete(event.span_id);
  else next.add(event.span_id);
  manuallyExpandedSpans.value = next;
}
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
  <div class="terminal-shell">
    <div class="terminal-toolbar">
      <div class="terminal-title">
        <span class="terminal-name">主控终端</span>
        <span class="terminal-state">{{ terminalStatusText }}</span>
      </div>
      <button
        class="trace-toggle"
        :class="['trace-' + traceSummary.status.toLowerCase(), { active: isTracePanelOpen }]"
        @click="toggleTracePanel"
        title="查看命令执行步骤"
      >
        <span class="trace-dot"></span>
        <span>{{ traceButtonLabel }}</span>
      </button>
    </div>

    <section v-if="isTracePanelOpen" class="trace-panel">
      <div class="trace-panel-head">
        <span>执行步骤</span>
        <span class="trace-id">{{ activeTraceId || 'NO TRACE' }}</span>
      </div>
      <div v-if="traceEvents.length === 0" class="trace-empty">暂无执行步骤</div>
      <div v-else class="trace-list">
        <button
          v-for="event in visibleTraceEvents"
          :key="event.span_id"
          class="trace-row"
          :class="['status-' + event.status.toLowerCase(), { muted: event.muted, summary: event.isSummaryError }]"
          :style="{ '--level': traceLevel(event) }"
          @click="toggleTraceNode(event)"
        >
          <span class="trace-status-mark"></span>
          <span class="trace-code">{{ event.step_code }}</span>
          <span class="trace-message">{{ event.message || statusText(event.status) }}</span>
          <span class="trace-meta">
            <span v-if="traceChildCount[event.span_id]" class="trace-fold">
              {{ event.collapsed && !manuallyExpandedSpans.has(event.span_id) ? '+' : '-' }}
            </span>
            <span>{{ statusText(event.status) }}</span>
            <span v-if="event.duration_ms !== null && event.duration_ms !== undefined">{{ event.duration_ms }}ms</span>
          </span>
        </button>
      </div>
    </section>

    <div class="scroll-container" ref="viewportRef" @scroll="handleScroll">
      
      <div v-if="displayLimit >= globalMessages.length && globalMessages.length > 0" class="history-end">
        —— 已追溯至记忆链路的尽头 ——
      </div>
      
      <div v-for="(m, i) in processedMessages" :key="'msg_'+i" :class="['bubble', m.role]">
        <CyberMarkdown v-if="m.displayContent" :text="m.displayContent" />
      </div>
      <div v-if="isThinking" class="thinking-cursor">大脑全速运转中...</div>
    </div>
  </div>
</template>

<style scoped>
.terminal-shell { height: 100%; min-height: 0; display: flex; flex-direction: column; background: #0d0d0f; }
.terminal-toolbar { height: 44px; flex: 0 0 44px; display: flex; align-items: center; justify-content: space-between; padding: 0 18px 0 24px; border-bottom: 1px solid #202024; background: #09090b; }
.terminal-title { display: flex; align-items: center; gap: 10px; min-width: 0; }
.terminal-name { color: #f0f0f0; font-size: 13px; font-weight: bold; }
.terminal-state { color: #777; font-size: 11px; }
.trace-toggle { height: 28px; display: inline-flex; align-items: center; gap: 7px; padding: 0 11px; border: 1px solid #33383c; border-radius: 6px; background: #111114; color: #aaa; font-family: 'Consolas'; font-size: 12px; cursor: pointer; transition: all 0.2s; }
.trace-toggle:hover, .trace-toggle.active { color: #00ffcc; border-color: rgba(0, 255, 204, 0.55); background: rgba(0, 255, 204, 0.06); }
.trace-dot { width: 7px; height: 7px; border-radius: 50%; background: #666; flex: 0 0 7px; }
.trace-running .trace-dot { background: #00ffcc; animation: pulse 1.2s infinite; }
.trace-failed .trace-dot { background: #ff4d4f; }
.trace-success .trace-dot { background: #55d17a; }
.trace-panel { flex: 0 0 auto; max-height: 34vh; display: flex; flex-direction: column; border-bottom: 1px solid #222; background: #08080a; box-shadow: 0 12px 30px rgba(0,0,0,0.2); }
.trace-panel-head { height: 34px; display: flex; align-items: center; justify-content: space-between; padding: 0 24px; color: #b8b8b8; font-size: 12px; border-bottom: 1px solid #1b1b1f; }
.trace-id { color: #555; font-size: 10px; max-width: 45%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.trace-empty { padding: 18px 24px; color: #555; font-size: 12px; }
.trace-list { overflow-y: auto; padding: 8px 12px 10px; display: flex; flex-direction: column; gap: 4px; }
.trace-list::-webkit-scrollbar { width: 6px; }
.trace-list::-webkit-scrollbar-thumb { background: #333; border-radius: 3px; }
.trace-row { width: 100%; min-height: 32px; display: grid; grid-template-columns: 14px minmax(90px, 140px) minmax(0, 1fr) auto; align-items: center; gap: 10px; padding: 5px 10px 5px calc(10px + var(--level) * 18px); border: 1px solid transparent; border-radius: 6px; background: transparent; color: #bdbdbd; font-family: 'Consolas'; font-size: 11px; text-align: left; cursor: default; }
.trace-row:hover { background: rgba(255,255,255,0.03); border-color: #24242a; }
.trace-row.summary { border-color: rgba(255, 77, 79, 0.28); background: rgba(255, 77, 79, 0.06); }
.trace-status-mark { width: 8px; height: 8px; border-radius: 50%; background: #666; }
.status-running .trace-status-mark { background: #00ffcc; animation: pulse 1.2s infinite; }
.status-success .trace-status-mark { background: #55d17a; }
.status-failed .trace-status-mark, .status-timeout .trace-status-mark { background: #ff4d4f; }
.status-aborted .trace-status-mark, .trace-row.muted .trace-status-mark { background: #555; }
.trace-code { color: #d7d7d7; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.trace-message { color: #aaa; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.trace-meta { display: inline-flex; align-items: center; gap: 8px; color: #666; white-space: nowrap; }
.trace-fold { color: #00ffcc; font-weight: bold; }
.status-failed .trace-message, .status-timeout .trace-message { color: #ff8f91; }
.trace-row.muted { color: #666; }
.trace-row.muted .trace-message, .trace-row.muted .trace-code { color: #666; }
.scroll-container { padding: 30px; display: flex; flex-direction: column; gap: 20px; flex: 1; min-height: 0; overflow-y: auto; scroll-behavior: smooth; }
.scroll-container::-webkit-scrollbar { width: 6px; }
.scroll-container::-webkit-scrollbar-thumb { background: #333; border-radius: 3px; }
.history-end { text-align: center; color: #444; font-size: 11px; letter-spacing: 2px; margin-bottom: 10px; }
.bubble { padding: 12px 16px; border-radius: 6px; font-size: 14px; max-width: 85%; line-height: 1.6; }
.user { background: #1a1a1c; align-self: flex-end; border-right: 2px solid #555; color: #eee; }
.ai, .assistant { background: rgba(0,255,204,0.03); align-self: flex-start; border-left: 2px solid #00ffcc; color: #ccc; }
.thinking-cursor { color: #00ffcc; font-size: 12px; animation: pulse 1.5s infinite; padding: 10px; }
@keyframes pulse { 0%, 100% { opacity: 0.5; } 50% { opacity: 1; } }
</style>
