<template>
  <div class="vpm-center">
    <div class="header-section">
      <h2 class="cyber-title">VPM 插件生态 <span>[Vault Package Manager]</span></h2>
      <button class="btn-scan">刷新本地库</button>
    </div>

    <div class="plugin-grid" v-if="pluginsList.length > 0">
      <div class="plugin-card" v-for="plugin in pluginsList" :key="plugin.plugin_id">
        <div class="card-header">
          <h3 class="p-name">{{ plugin.name }}</h3>
          <span class="p-version">v{{ plugin.version }}</span>
        </div>
        <p class="p-desc">{{ plugin.description }}</p>
        <div class="card-footer">
          <span class="p-author">Author: {{ plugin.author }}</span>
          <div class="p-actions">
            <button class="btn-setting" title="配置" @click="openManager(plugin.plugin_id)">⚙️ 管理</button>
            <button class="btn-uninstall" title="卸载" @click="confirmUninstall(plugin.plugin_id, plugin.name)">🗑️</button>
          </div>
        </div>
      </div>
    </div>

    <div class="empty-state" v-else>
      <div class="scan-line"></div>
      <p>未检测到已安装的合规 VPM 插件。</p>
    </div>
  </div>
  <transition name="fade">
      <component v-if="activeManager" :is="activeManager" @close="activeManager = null" />
    </transition>
  <DangerDialog
    :show="!!pendingUninstall"
    title="插件卸载确认"
    :object-name="pendingUninstall?.pluginName || '未命名插件'"
    impact="将删除该插件产生的本地专属资产，并清理该插件关联的 RAG 向量记录。"
    :irreversible="true"
    risk-tip="建议先进入该插件的配置或管理面板执行导出备份，再继续卸载。"
    confirm-text="确认卸载"
    @cancel="cancelUninstall"
    @confirm="uninstallPlugin"
  />
</template>

<script setup>
import { ref } from 'vue';
import { pluginsList, useNeuroLink } from '../composables/useNeuroLink.js'; 
import { loadVpmComponent } from '../utils/vpmLoader.js';
import DangerDialog from '../components/DangerDialog.vue';

const { sendWsCommand } = useNeuroLink();
const activeManager = ref(null);
const pendingUninstall = ref(null);
const openManager = (pluginId) => {
  activeManager.value = loadVpmComponent(pluginId, 'Manager');
};
const confirmUninstall = (pluginId, pluginName) => {
  pendingUninstall.value = { pluginId, pluginName };
};
const cancelUninstall = () => {
  pendingUninstall.value = null;
};
const uninstallPlugin = () => {
  if (!pendingUninstall.value) return;
  sendWsCommand({ type: "uninstall_plugin", plugin_id: pendingUninstall.value.pluginId });
  pendingUninstall.value = null;
};
</script>

<style scoped>
.vpm-center { padding: var(--space-3xl); height: 100%; overflow-y: auto; color: var(--text-primary);}
.header-section { display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--space-3xl); border-bottom: 1px solid var(--border-strong); padding-bottom: var(--space-lg);}
.cyber-title { font-size: 24px; margin: 0; color: var(--accent); display: flex; align-items: baseline; gap: var(--space-sm);}
.cyber-title span { font-size: 12px; color: var(--text-disabled); letter-spacing: 2px;}
.btn-scan { background: transparent; border: 1px solid var(--accent-border); color: var(--accent); padding: var(--space-xs) var(--space-lg); border-radius: var(--radius-xs); cursor: pointer; transition: background var(--duration-base) var(--ease-standard), box-shadow var(--duration-base) var(--ease-standard), color var(--duration-base) var(--ease-standard);}
.btn-scan:hover { background: var(--accent-soft); box-shadow: var(--shadow-glow-soft);}

.plugin-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: var(--space-xl); }
.plugin-card { background: var(--bg-panel); border: 1px solid var(--border-strong); border-radius: var(--radius-md); padding: var(--space-xl); display: flex; flex-direction: column; transition: transform var(--duration-base) var(--ease-standard), border-color var(--duration-base) var(--ease-standard), background var(--duration-base) var(--ease-standard), box-shadow var(--duration-base) var(--ease-standard);}
.plugin-card:hover { border-color: var(--accent-border); background: var(--bg-panel-raised); transform: translateY(-3px); box-shadow: var(--shadow-panel);}
.card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--space-lg);}
.p-name { margin: 0; font-size: 18px; color: var(--text-primary);}
.p-version { font-size: 12px; background: var(--bg-panel-raised); padding: 2px 6px; border-radius: var(--radius-xs); color: var(--text-muted);}
.p-desc { font-size: 13px; color: var(--text-secondary); line-height: 1.5; margin-bottom: var(--space-xl); flex: 1;}
.card-footer { display: flex; justify-content: space-between; align-items: center; border-top: 1px dashed var(--border-strong); padding-top: var(--space-lg);}
.p-author { font-size: 11px; color: var(--text-disabled); font-family: var(--font-mono);}
.p-actions button { background: none; border: none; cursor: pointer; opacity: 0.68; transition: opacity var(--duration-base) var(--ease-standard), color var(--duration-base) var(--ease-standard); font-size: 16px;}
.p-actions button:hover { opacity: 1; }
.btn-uninstall:hover { color: var(--danger) !important; }

.empty-state { text-align: center; margin-top: 100px; color: var(--text-disabled); font-family: var(--font-mono); position: relative;}
.fade-enter-active, .fade-leave-active { transition: opacity 0.3s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
