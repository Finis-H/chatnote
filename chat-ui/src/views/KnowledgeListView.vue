<script setup>
import { computed } from 'vue';
import PageFrame from '../components/PageFrame.vue';
import SegmentedControl from '../components/SegmentedControl.vue';
import VaultCard from '../components/VaultCard.vue';
import { newsList, favoritesList, searchQuery, searchMode, deleteModal, useNeuroLink } from '../composables/useNeuroLink';

const props = defineProps({ type: String }); // 'news' or 'favorites'
const { openNote } = useNeuroLink();

const title = computed(() => props.type === 'news' ? '最新摄入消息' : '⭐ 订阅与收藏');
const searchModeOptions = [
  { label: '全局', value: 'all' },
  { label: '标题', value: 'title' },
  { label: '标签', value: 'keyword' }
];

const currentList = computed(() => {
  const baseList = props.type === 'news' ? newsList.value : favoritesList.value;
  if (!searchQuery.value) return baseList;
  const q = searchQuery.value.toLowerCase();
  return baseList.filter(n => {
    const matchTitle = n.title?.toLowerCase().includes(q);
    const matchSummary = n.summary?.toLowerCase().includes(q);
    const matchKeyword = n.keywords && n.keywords.some(k => k.toLowerCase().includes(q));
    if (searchMode.value === 'title') return matchTitle;
    if (searchMode.value === 'keyword') return matchKeyword;
    return matchTitle || matchSummary || matchKeyword;
  });
});

function requestDelete(event, note) {
  event.stopPropagation();
  deleteModal.value = { show: true, note: note };
}
</script>

<template>
  <PageFrame :title="title">
    <div class="search-console">
      <SegmentedControl v-model="searchMode" :options="searchModeOptions" />
      <input class="search-input" v-model="searchQuery" placeholder="输入关键字进行毫秒级过滤..." />
    </div>
    <VaultCard
      v-for="n in currentList"
      :key="n.id"
      class="news-card"
      :title="n.title"
      :meta="`#${n.id} · ${n.time_str}`"
      interactive
      @click="openNote(n)"
    >
      <template #status>
        <button class="delete-btn" @click="requestDelete($event, n)" title="删除档案">🗑️</button>
      </template>
      <p class="card-summary">{{ n.summary }}</p>
      <div class="card-tags" v-if="n.keywords && n.keywords.length">
        <span class="tag" v-for="k in n.keywords" :key="k">{{ k }}</span>
      </div>
      <div class="card-footer">点击阅读并讨论 →</div>
    </VaultCard>
  </PageFrame>
</template>

<style scoped>
.search-console { display: flex; gap: var(--space-lg); margin-top: var(--space-sm); margin-bottom: var(--space-2xl); align-items: center; }
.search-input { flex: 1; background: var(--bg-console); border: 1px solid var(--border-strong); color: var(--text-primary); padding: 10px var(--space-lg); border-radius: var(--radius-sm); font-size: 14px; }
.search-input:focus { border-color: var(--accent-border); box-shadow: var(--shadow-glow-soft); }
.news-card { border-radius: var(--radius-lg); }
.card-summary { font-size: 13px; color: var(--text-muted); line-height: 1.6; }
.card-tags { display: flex; gap: var(--space-sm); margin-top: var(--space-md); flex-wrap: wrap; }
.tag { background: var(--accent-soft); border: 1px solid var(--accent-border); color: var(--accent); font-size: 10px; padding: 2px var(--space-sm); border-radius: var(--radius-xs); }
.delete-btn { background: transparent; border: none; color: var(--text-disabled); cursor: pointer; padding: var(--space-xs) var(--space-sm); font-size: 14px; z-index: 10; transition: color var(--duration-base) var(--ease-standard), transform var(--duration-base) var(--ease-standard);}
.delete-btn:hover { color: var(--danger); transform: scale(1.1); }
.card-footer { margin-top: var(--space-lg); font-size: 11px; color: var(--text-disabled); }
</style>
