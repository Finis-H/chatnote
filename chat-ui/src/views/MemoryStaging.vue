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

function displayTrait(mem) {
  const trait = String(mem?.new_trait || mem?.context || '').trim();
  const subject = String(mem?.target_entity || '').trim();
  if (!trait || !subject) return trait;
  if (trait.startsWith(subject)) return trait;
  if (subject !== 'Boss') return `${subject}${trait}`;
  return `Boss ${trait}`;
}
</script>

<template>
  <div class="scroll-container">
    <div class="memory-header">
      <h2 class="view-title">🧠 记忆事件同步</h2>
      <p class="memory-subtitle">在此处理低置信度、关系变更、手术指令和冲突候选。超时 3 天的待审项将自动同化。</p>
    </div>
    <div class="search-console">
      <div class="filter-capsules">
        <button :class="{ active: memoryFilter === 'all' }" @click="memoryFilter = 'all'">全局视野</button>
        <button :class="{ active: memoryFilter === 'pending'}" @click="memoryFilter = 'pending'">
          ⚠️ 待审事件 ({{ pendingCount }})
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
          <span class="mem-status blink" v-if="mem.status === 'PENDING'">⚠️ 事件待审</span>
        </div>
        <div class="card-body">
          <div v-if="mem.type === 'CONFLICT'" class="conflict-zone">
            <div class="old-trait"><del>{{ mem.old_trait }}</del></div>
            <div class="arrow">↓ 强行覆写为 ↓</div>
          </div>
          <div class="new-trait">{{ displayTrait(mem) }}</div>
        </div>
        <div class="card-footer" v-if="mem.status === 'PENDING'">
          <div>⏳ 倒计时: <span class="countdown">{{ formatExpireTime(mem.expires_at) }}</span></div>
          <div class="decision-actions">
            <button class="decision-btn accept" @click="resolveMemoryConflict(mem.id, 'accept')">是</button>
            <button class="decision-btn reject" @click="resolveMemoryConflict(mem.id, 'reject')">否</button>
          </div>
        </div> 
      </div>
    </div>
  </div>
</template>

<style scoped>
.scroll-container { padding: var(--space-3xl); display: flex; flex-direction: column; gap: var(--space-xl); height: 100%; overflow-y: auto; }
.scroll-container::-webkit-scrollbar { width: 6px; }
.scroll-container::-webkit-scrollbar-thumb { background: var(--border-strong); border-radius: var(--radius-xs); }
.view-title { color: var(--text-primary); font-size: 18px; font-weight: normal; margin-bottom: var(--space-sm); }
.memory-header { border-bottom: 1px solid var(--border-strong); padding-bottom: var(--space-lg); }
.memory-subtitle { color: var(--text-muted); font-size: 13px; margin-top: var(--space-xs); }
.search-console { display: flex; gap: var(--space-lg); margin-bottom: var(--space-lg); align-items: center; }
.filter-capsules { display: flex; background: var(--bg-hover); border-radius: var(--radius-pill); padding: var(--space-2xs); }
.filter-capsules button { background: transparent; border: none; color: var(--text-muted); padding: 6px 16px; border-radius: var(--radius-pill); cursor: pointer; font-size: 12px; transition: background var(--duration-base) var(--ease-standard), color var(--duration-base) var(--ease-standard); font-family: var(--font-mono); }
.filter-capsules button.active { background: var(--accent); color: var(--text-inverse); font-weight: bold; }
.empty-state { color: var(--text-disabled); font-family: var(--font-mono); margin-top: var(--space-xl); }
.memory-grid { display: flex; flex-direction: column; gap: var(--space-lg); }
.memory-card { background: var(--bg-panel); border: 1px solid var(--border-strong); border-radius: var(--radius-md); padding: var(--space-lg); position: relative; overflow: hidden; transition: background var(--duration-slow) var(--ease-standard), border-color var(--duration-slow) var(--ease-standard); }
.memory-card::before { content: ''; position: absolute; left: 0; top: 0; bottom: 0; width: 4px; }
.card-success { border-color: var(--accent-border); }
.card-success::before { background: var(--accent); }
.card-warning { border-color: var(--danger-border); }
.card-warning::before { background: var(--danger); }
.card-header { display: flex; justify-content: space-between; margin-bottom: var(--space-md); font-size: 12px; }
.mem-tag { background: var(--bg-panel-raised); padding: var(--space-2xs) var(--space-sm); border-radius: var(--radius-xs); color: var(--text-secondary); font-family: var(--font-mono); }
.mem-status { font-weight: bold; }
.card-success .mem-status { color: var(--accent); }
.card-warning .mem-status { color: var(--danger); }
.blink { animation: blinkText 2s infinite; }
@keyframes blinkText { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
.conflict-zone { background: var(--bg-danger-soft); padding: var(--space-sm); border-radius: var(--radius-xs); margin-bottom: var(--space-sm); border: 1px dashed var(--border-dashed); }
.old-trait { color: var(--text-muted); text-decoration: line-through; font-size: 13px; }
.arrow { color: var(--danger); font-size: 12px; text-align: center; margin: var(--space-xs) 0; font-family: var(--font-mono); }
.new-trait { color: var(--text-primary); font-size: 15px; line-height: 1.5; }
.card-footer { margin-top: var(--space-lg); padding-top: var(--space-sm); border-top: 1px solid var(--border-strong); font-size: 12px; color: var(--text-muted); }
.countdown { color: var(--danger); font-weight: bold; font-family: var(--font-mono); }
.decision-actions { display: flex; gap: var(--space-sm); margin-top: var(--space-sm); }
.decision-btn { border: 1px solid var(--border-strong); background: var(--bg-hover); color: var(--text-secondary); padding: var(--space-xs) 14px; border-radius: var(--radius-xs); cursor: pointer; font-size: 12px; transition: background var(--duration-base) var(--ease-standard), border-color var(--duration-base) var(--ease-standard), color var(--duration-base) var(--ease-standard); }
.decision-btn.accept { border-color: var(--accent-border); color: var(--accent); }
.decision-btn.reject { border-color: var(--danger-border); color: var(--danger); }
.decision-btn:hover { background: var(--bg-hover-strong); }
</style>
