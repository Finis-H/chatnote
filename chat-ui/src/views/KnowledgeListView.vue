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
.scroll-container { padding: 30px; display: flex; flex-direction: column; gap: 20px; height: 100%; overflow-y: auto; }
.scroll-container::-webkit-scrollbar { width: 6px; }
.scroll-container::-webkit-scrollbar-thumb { background: #333; border-radius: 3px; }
.view-title { color: #fff; font-size: 18px; font-weight: normal; margin-bottom: 10px; }
.search-console { display: flex; gap: 15px; margin-bottom: 25px; align-items: center; }
.filter-capsules { display: flex; background: rgba(255,255,255,0.05); border-radius: 20px; padding: 3px; }
.filter-capsules button { background: transparent; border: none; color: #888; padding: 6px 16px; border-radius: 18px; cursor: pointer; font-size: 12px; transition: all 0.2s; font-family: 'Consolas'; }
.filter-capsules button.active { background: #00ffcc; color: #000; font-weight: bold; }
.search-input { flex: 1; background: rgba(0,0,0,0.3); border: 1px solid #333; color: #fff; padding: 10px 15px; border-radius: 6px; font-size: 14px; outline: none; }
.search-input:focus { border-color: #00ffcc; box-shadow: 0 0 10px rgba(0,255,204,0.1); }
.news-card { background: rgba(255, 255, 255, 0.02); border: 1px solid #222; border-radius: 10px; padding: 20px; cursor: pointer; transition: all 0.2s; }
.news-card:hover { transform: translateY(-2px); border-color: #00ffcc; background: rgba(0, 255, 204, 0.02); box-shadow: 0 10px 20px rgba(0,0,0,0.3); }
.news-card:hover .card-title { color: #00ffcc; }
.card-header { display: flex; justify-content: space-between; align-items: center; font-size: 10px; color: #555; margin-bottom: 12px; }
.card-title { font-size: 16px; color: rgba(0, 255, 204, 0.736); margin-bottom: 8px; }
.card-summary { font-size: 13px; color: #888; line-height: 1.6; }
.card-tags { display: flex; gap: 8px; margin-top: 12px; flex-wrap: wrap; }
.tag { background: rgba(0, 255, 204, 0.1); border: 1px solid rgba(0,255,204,0.3); color: #00ffcc; font-size: 10px; padding: 2px 8px; border-radius: 4px; }
.delete-btn { background: transparent; border: none; color: #555; cursor: pointer; padding: 4px 8px; font-size: 14px; z-index: 10; transition: all 0.2s;}
.delete-btn:hover { color: #ff4d4f; transform: scale(1.1); }
.card-footer { margin-top: 15px; font-size: 11px; color: #555; }
</style>