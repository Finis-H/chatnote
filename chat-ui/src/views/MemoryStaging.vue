<script setup>
import { computed } from 'vue';
import PageFrame from '../components/PageFrame.vue';
import SegmentedControl from '../components/SegmentedControl.vue';
import { pendingMemory, pendingCount, memoryFilter, resolveMemoryConflict } from '../composables/useNeuroLink';

const memoryFilterOptions = computed(() => [
  { label: '全局视野', value: 'all' },
  { label: `⚠️ 待审事件 (${pendingCount.value})`, value: 'pending' },
  { label: '✨ 历史档案', value: 'merged' }
]);

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
  return `用户 ${trait}`;
}
</script>

<template>
  <PageFrame
    title="🧠 记忆事件同步"
    subtitle="在此处理低置信度、关系变更、手动记忆更新和冲突候选。待审项未处理满 3 天后，将自动采纳并生效。"
  >
    <div class="search-console">
      <SegmentedControl v-model="memoryFilter" :options="memoryFilterOptions" />
    </div>
    <div v-if="pendingMemory.length === 0" class="empty-state">当前没有待审记忆事件。</div>
    <div class="memory-grid" v-else>
      <div v-for="mem in displayMemory" :key="mem.id" class="memory-card" :class="mem.status === 'PENDING' ? 'card-warning' : 'card-success'">
        <div class="card-header">
          <span class="mem-tag">{{ mem.category.toUpperCase() }}</span>
          <span class="mem-status" v-if="mem.status === 'MERGED'">✨ 已合并生效</span>
          <span class="mem-status" v-if="mem.status === 'REJECTED'">❌ 已驳回</span>
          <span class="mem-status" v-if="mem.status === 'AUTO_OVERWRITTEN'">⏰ 超时自动采纳</span>
          <span class="mem-status blink" v-if="mem.status === 'PENDING'">⚠️ 事件待审</span>
        </div>
        <div class="card-body">
          <div v-if="mem.type === 'CONFLICT'" class="conflict-zone">
            <div class="old-trait"><del>{{ mem.old_trait }}</del></div>
            <div class="arrow">↓ 更新为 ↓</div>
          </div>
          <div class="new-trait">{{ displayTrait(mem) }}</div>
        </div>
        <div class="card-footer" v-if="mem.status === 'PENDING'">
          <div>⏳ 倒计时: <span class="countdown">{{ formatExpireTime(mem.expires_at) }}</span></div>
          <div class="decision-actions">
            <button class="decision-btn accept" @click="resolveMemoryConflict(mem.id, 'accept')">采纳更新</button>
            <button class="decision-btn reject" @click="resolveMemoryConflict(mem.id, 'reject')">驳回更新</button>
          </div>
        </div> 
      </div>
    </div>
  </PageFrame>
</template>

<style scoped>
.search-console { display: flex; gap: var(--space-lg); margin-bottom: var(--space-lg); align-items: center; }
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
