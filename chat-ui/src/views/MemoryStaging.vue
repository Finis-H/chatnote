<script setup>
import { computed } from 'vue';
import { pendingMemory, pendingCount, memoryFilter, resolveMemoryConflict } from '../composables/useNeuroLink';

const displayMemory = computed(() => {
  let list = [...pendingMemory.value];
  const THREE_DAYS_MS = 3 * 24 * 60 * 60 * 1000;
  const now = Date.now();
  list = list.filter(m => {
    if (m.status === 'PENDING') return true;
    const itemTime = m.created_at ? new Date(m.created_at).getTime() : (m.expires_at ? new Date(m.expires_at).getTime() - THREE_DAYS_MS : now);
    return (now - itemTime) <= THREE_DAYS_MS;
  });
  if (memoryFilter.value === 'pending') list = list.filter(m => m.status === 'PENDING');
  else if (memoryFilter.value === 'merged') list = list.filter(m => m.status !== 'PENDING');
  return list.sort((a, b) => {
    if (a.status === 'PENDING' && b.status !== 'PENDING') return -1;
    if (a.status !== 'PENDING' && b.status === 'PENDING') return 1;
    const timeA = a.created_at ? new Date(a.created_at).getTime() : 0;
    const timeB = b.created_at ? new Date(b.created_at).getTime() : 0;
    return timeB - timeA;
  });
});

function formatExpireTime(isoString) { return new Date(isoString).toLocaleString(); }
</script>

<template>
  <div class="scroll-container">
    <div class="memory-header">
      <h2 class="view-title">🧠 记忆神经同步 (Staging Area)</h2>
      <p class="memory-subtitle">在此界面向管家发送指令，可对记忆进行二次覆写或驳回。超时 3 天的警告项将被强行同化。</p>
    </div>
    <div class="search-console">
      <div class="filter-capsules">
        <button :class="{ active: memoryFilter === 'all' }" @click="memoryFilter = 'all'">全局视野</button>
        <button :class="{ active: memoryFilter === 'pending'}" @click="memoryFilter = 'pending'">
          ⚠️ 待决冲突 ({{ pendingCount }})
        </button>
        <button :class="{ active: memoryFilter === 'merged' }" @click="memoryFilter = 'merged'">✨ 历史档案</button>
      </div>
    </div>
    <div v-if="pendingMemory.length === 0" class="empty-state">当前神经链路纯净，无待决记忆碎片。</div>
    <div class="memory-grid" v-else>
      <div v-for="mem in displayMemory" :key="mem.id" class="memory-card" :class="mem.status === 'PENDING' ? 'card-warning' : 'card-success'">
        <div class="card-header">
          <span class="mem-tag">{{ mem.category.toUpperCase() }}</span>
          <span class="mem-status" v-if="mem.status === 'MERGED'">✨ 已同化生效</span>
          <span class="mem-status" v-if="mem.status === 'REJECTED'">❌ 已驳回抹除</span>
          <span class="mem-status" v-if="mem.status === 'AUTO_OVERWRITTEN'">⏰ 超时强行同化</span>
          <span class="mem-status blink" v-if="mem.status === 'PENDING'">⚠️ 记忆冲突待决</span>
        </div>
        <div class="card-body">
          <div v-if="mem.type === 'CONFLICT'" class="conflict-zone">
            <div class="old-trait"><del>{{ mem.old_trait }}</del></div>
            <div class="arrow">↓ 强行覆写为 ↓</div>
          </div>
          <div class="new-trait">{{ mem.new_trait }}</div>
        </div>
        <div class="card-footer" v-if="mem.status === 'PENDING'">
          <div>⏳ 倒计时: <span class="countdown">{{ formatExpireTime(mem.expires_at) }}</span></div>
          <div class="decision-actions" v-if="mem.type === 'CONFLICT'">
            <button class="decision-btn accept" @click="resolveMemoryConflict(mem.id, 'accept')">是</button>
            <button class="decision-btn reject" @click="resolveMemoryConflict(mem.id, 'reject')">否</button>
          </div>
        </div> 
      </div>
    </div>
  </div>
</template>

<style scoped>
.scroll-container { padding: 30px; display: flex; flex-direction: column; gap: 20px; height: 100%; overflow-y: auto; }
.scroll-container::-webkit-scrollbar { width: 6px; }
.scroll-container::-webkit-scrollbar-thumb { background: #333; border-radius: 3px; }
.view-title { color: #fff; font-size: 18px; font-weight: normal; margin-bottom: 10px; }
.memory-header { border-bottom: 1px solid #333; padding-bottom: 15px; }
.memory-subtitle { color: #888; font-size: 13px; margin-top: 5px; }
.search-console { display: flex; gap: 15px; margin-bottom: 15px; align-items: center; }
.filter-capsules { display: flex; background: rgba(255,255,255,0.05); border-radius: 20px; padding: 3px; }
.filter-capsules button { background: transparent; border: none; color: #888; padding: 6px 16px; border-radius: 18px; cursor: pointer; font-size: 12px; transition: all 0.2s; font-family: 'Consolas'; }
.filter-capsules button.active { background: #00ffcc; color: #000; font-weight: bold; }
.empty-state { color: #666; font-family: 'Consolas'; margin-top: 20px; }
.memory-grid { display: flex; flex-direction: column; gap: 15px; }
.memory-card { background: rgba(0,0,0,0.6); border: 1px solid #333; border-radius: 8px; padding: 15px; position: relative; overflow: hidden; transition: all 0.3s; }
.memory-card::before { content: ''; position: absolute; left: 0; top: 0; bottom: 0; width: 4px; }
.card-success { border-color: rgba(0, 255, 204, 0.3); }
.card-success::before { background: #00ffcc; box-shadow: 0 0 10px #00ffcc; }
.card-warning { border-color: rgba(255, 77, 79, 0.4); }
.card-warning::before { background: #ff4d4f; box-shadow: 0 0 10px #ff4d4f; }
.card-header { display: flex; justify-content: space-between; margin-bottom: 12px; font-size: 12px; }
.mem-tag { background: #222; padding: 3px 8px; border-radius: 4px; color: #aaa; font-family: 'Consolas'; }
.mem-status { font-weight: bold; }
.card-success .mem-status { color: #00ffcc; }
.card-warning .mem-status { color: #ff4d4f; }
.blink { animation: blinkText 2s infinite; }
@keyframes blinkText { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
.conflict-zone { background: rgba(255, 77, 79, 0.05); padding: 10px; border-radius: 4px; margin-bottom: 10px; border: 1px dashed #555; }
.old-trait { color: #888; text-decoration: line-through; font-size: 13px; }
.arrow { color: #ff4d4f; font-size: 12px; text-align: center; margin: 5px 0; font-family: 'Consolas'; }
.new-trait { color: #fff; font-size: 15px; line-height: 1.5; }
.card-footer { margin-top: 15px; padding-top: 10px; border-top: 1px solid #333; font-size: 12px; color: #888; }
.countdown { color: #ff4d4f; font-weight: bold; font-family: 'Consolas'; }
.decision-actions { display: flex; gap: 8px; margin-top: 10px; }
.decision-btn { border: 1px solid #444; background: rgba(255,255,255,0.05); color: #ddd; padding: 5px 14px; border-radius: 4px; cursor: pointer; font-size: 12px; transition: all 0.2s; }
.decision-btn.accept { border-color: rgba(0, 255, 204, 0.45); color: #00ffcc; }
.decision-btn.reject { border-color: rgba(255, 77, 79, 0.45); color: #ff4d4f; }
.decision-btn:hover { background: rgba(255,255,255,0.12); }
</style>
