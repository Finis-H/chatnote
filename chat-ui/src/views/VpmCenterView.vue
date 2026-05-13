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
            <button class="btn-setting" title="配置">⚙️</button>
            <button class="btn-uninstall" title="卸载">🗑️</button>
          </div>
        </div>
      </div>
    </div>

    <div class="empty-state" v-else>
      <div class="scan-line"></div>
      <p>雷达未扫描到已安装的合规 VPM 插件。</p>
    </div>
  </div>
</template>

<script setup>
import { pluginsList } from '../composables/useNeuroLink.js'; // 路径按你实际的调整
</script>

<style scoped>
.vpm-center { padding: 30px; height: 100%; overflow-y: auto; color: #fff;}
.header-section { display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; border-bottom: 1px solid #333; padding-bottom: 15px;}
.cyber-title { font-size: 24px; margin: 0; color: #00ffcc; display: flex; align-items: baseline; gap: 10px;}
.cyber-title span { font-size: 12px; color: #666; letter-spacing: 2px;}
.btn-scan { background: transparent; border: 1px solid #00ffcc; color: #00ffcc; padding: 5px 15px; border-radius: 4px; cursor: pointer; transition: all 0.2s;}
.btn-scan:hover { background: rgba(0,255,204,0.1); box-shadow: 0 0 10px rgba(0,255,204,0.3);}

.plugin-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; }
.plugin-card { background: rgba(20,20,22,0.8); border: 1px solid #333; border-radius: 8px; padding: 20px; display: flex; flex-direction: column; transition: transform 0.2s, border-color 0.2s;}
.plugin-card:hover { border-color: #00ffcc; transform: translateY(-3px);}
.card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;}
.p-name { margin: 0; font-size: 18px; color: #fff;}
.p-version { font-size: 12px; background: #222; padding: 2px 6px; border-radius: 4px; color: #888;}
.p-desc { font-size: 13px; color: #aaa; line-height: 1.5; margin-bottom: 20px; flex: 1;}
.card-footer { display: flex; justify-content: space-between; align-items: center; border-top: 1px dashed #333; padding-top: 15px;}
.p-author { font-size: 11px; color: #666; font-family: 'Consolas';}
.p-actions button { background: none; border: none; cursor: pointer; opacity: 0.6; transition: opacity 0.2s; font-size: 16px;}
.p-actions button:hover { opacity: 1; }
.btn-uninstall:hover { color: #ff4d4f !important; }

.empty-state { text-align: center; margin-top: 100px; color: #555; font-family: 'Consolas'; position: relative;}
</style>