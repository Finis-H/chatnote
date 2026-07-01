<script setup>
import { computed } from 'vue';
import { newsList, favoritesList, searchQuery, searchMode, deleteModal, useNeuroLink } from '../composables/useNeuroLink';

const props = defineProps({ type: String }); // 'news' or 'favorites'
const { openNote } = useNeuroLink();

const title = computed(() => props.type === 'news' ? '最新摄入消息' : '⭐ 订阅与收藏');

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
  <div class="scroll-container card-grid">
    <h2 class="view-title">{{ title }}</h2>
    <div class="search-console">
      <div class="filter-capsules">
        <button :class="{ active: searchMode === 'all' }" @click="searchMode = 'all'">全局</button>
        <button :class="{ active: searchMode === 'title' }" @click="searchMode = 'title'">标题</button>
        <button :class="{ active: searchMode === 'keyword' }" @click="searchMode = 'keyword'">标签</button>
      </div>
      <input class="search-input" v-model="searchQuery" placeholder="输入关键字进行毫秒级过滤..." />
    </div>
    <div class="news-card" v-for="n in currentList" :key="n.id" @click="openNote(n)">
      <div class="card-header">
        <span class="card-id">#{{ n.id }}</span><span class="card-time">{{ n.time_str }}</span>
        <button class="delete-btn" @click="requestDelete($event, n)" title="彻底删除">🗑️</button>
      </div>
      <h3 class="card-title">{{ n.title }}</h3>
      <p class="card-summary">{{ n.summary }}</p>
      <div class="card-tags" v-if="n.keywords && n.keywords.length">
        <span class="tag" v-for="k in n.keywords" :key="k">{{ k }}</span>
      </div>
      <div class="card-footer">点击阅读并讨论 →</div>
    </div>
  </div>
</template>

<style scoped>
.scroll-container { padding: var(--space-3xl); display: flex; flex-direction: column; gap: var(--space-xl); height: 100%; overflow-y: auto; }
.scroll-container::-webkit-scrollbar { width: 6px; }
.scroll-container::-webkit-scrollbar-thumb { background: var(--border-strong); border-radius: var(--radius-xs); }
.view-title { color: var(--text-primary); font-size: 18px; font-weight: normal; margin-bottom: var(--space-sm); }
.search-console { display: flex; gap: var(--space-lg); margin-bottom: var(--space-2xl); align-items: center; }
.filter-capsules { display: flex; background: var(--bg-hover); border-radius: var(--radius-pill); padding: var(--space-2xs); }
.filter-capsules button { background: transparent; border: none; color: var(--text-muted); padding: 6px 16px; border-radius: var(--radius-pill); cursor: pointer; font-size: 12px; transition: background var(--duration-base) var(--ease-standard), color var(--duration-base) var(--ease-standard); font-family: var(--font-mono); }
.filter-capsules button.active { background: var(--accent); color: var(--text-inverse); font-weight: bold; }
.search-input { flex: 1; background: var(--bg-console); border: 1px solid var(--border-strong); color: var(--text-primary); padding: 10px var(--space-lg); border-radius: var(--radius-sm); font-size: 14px; }
.search-input:focus { border-color: var(--accent-border); box-shadow: var(--shadow-glow-soft); }
.news-card { background: var(--bg-panel); border: 1px solid var(--border-subtle); border-radius: var(--radius-lg); padding: var(--space-xl); cursor: pointer; transition: transform var(--duration-base) var(--ease-standard), border-color var(--duration-base) var(--ease-standard), background var(--duration-base) var(--ease-standard), box-shadow var(--duration-base) var(--ease-standard); }
.news-card:hover { transform: translateY(-2px); border-color: var(--accent-border); background: var(--bg-panel-raised); box-shadow: var(--shadow-panel); }
.news-card:hover .card-title { color: var(--accent-strong); }
.card-header { display: flex; justify-content: space-between; align-items: center; font-size: 10px; color: var(--text-disabled); margin-bottom: var(--space-md); }
.card-title { font-size: 16px; color: var(--accent); margin-bottom: var(--space-sm); }
.card-summary { font-size: 13px; color: var(--text-muted); line-height: 1.6; }
.card-tags { display: flex; gap: var(--space-sm); margin-top: var(--space-md); flex-wrap: wrap; }
.tag { background: var(--accent-soft); border: 1px solid var(--accent-border); color: var(--accent); font-size: 10px; padding: 2px var(--space-sm); border-radius: var(--radius-xs); }
.delete-btn { background: transparent; border: none; color: var(--text-disabled); cursor: pointer; padding: var(--space-xs) var(--space-sm); font-size: 14px; z-index: 10; transition: color var(--duration-base) var(--ease-standard), transform var(--duration-base) var(--ease-standard);}
.delete-btn:hover { color: var(--danger); transform: scale(1.1); }
.card-footer { margin-top: var(--space-lg); font-size: 11px; color: var(--text-disabled); }
</style>
