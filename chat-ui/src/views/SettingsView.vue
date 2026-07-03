<script setup>
import { sysConfig, useNeuroLink } from '../composables/useNeuroLink';
const { saveSystemConfig } = useNeuroLink();
</script>

<template>
  <div class="scroll-container">
    <h2 class="view-title">⚙️ LLM 引擎中枢配置</h2>
    <div class="settings-panel">
      <div class="settings-divider">知识库向量引擎 (RAG Core)</div>
      <div class="setting-item">
        <label>向量计算模型 (Embedding Model)</label>
        <input class="setting-input readonly-input" v-model="sysConfig.embed_model" disabled />
      </div>
      <div class="setting-item">
        <label>Embedding API Key</label>
        <input class="setting-input" type="password" v-model="sysConfig.embed_api_key" placeholder="请输入千问 Embedding 专用 API Key" />
        <span class="setting-tip">用于将本地笔记转化为高维向量。若不填写，摄入功能将不可用。</span>
      </div>
      <div class="settings-divider">主对话核心模型 (Chat Core)</div>
      <div class="setting-item">
        <label>API Base URL (代理端点)</label>
        <input class="setting-input" v-model="sysConfig.base_url" placeholder="例如: https://api.deepseek.com/v1" />
        <span class="setting-tip">兼容 OpenAI 格式的任何第三方 API 或本地 Ollama 地址。</span>
      </div>
      <div class="setting-item">
        <label>API Key (密钥)</label>
        <input class="setting-input" type="password" v-model="sysConfig.api_key" placeholder="sk-..." />
      </div>
      <div class="setting-item">
        <label>主算力模型 (Model Max)</label>
        <input class="setting-input" v-model="sysConfig.model_max" placeholder="例如: deepseek-chat" />
      </div>
      <div class="setting-item">
        <label>轻量提纯模型 (Model Mini)</label>
        <input class="setting-input" v-model="sysConfig.model_mini" placeholder="例如: gpt-3.5-turbo" />
      </div>
      <button class="save-btn" @click="saveSystemConfig">保存并重载配置</button>
    </div>
  </div>
</template>

<style scoped>
.scroll-container { padding: var(--space-3xl); display: flex; flex-direction: column; gap: var(--space-xl); height: 100%; overflow-y: auto; }
.scroll-container::-webkit-scrollbar { width: 6px; }
.scroll-container::-webkit-scrollbar-thumb { background: var(--border-strong); border-radius: var(--radius-xs); }
.view-title { color: var(--text-primary); font-size: 18px; font-weight: normal; margin-bottom: var(--space-sm); }
.settings-panel { background: var(--bg-panel); border: 1px solid var(--border-subtle); border-radius: var(--radius-lg); padding: var(--space-3xl); }
.setting-item { display: flex; flex-direction: column; margin-bottom: var(--space-2xl); }
.setting-item label { color: var(--accent); font-size: 14px; margin-bottom: var(--space-sm); font-weight: bold; }
.setting-input { background: var(--bg-console); border: 1px solid var(--border-strong); color: var(--text-primary); padding: var(--space-md); border-radius: var(--radius-sm); font-family: var(--font-mono); font-size: 14px; transition: border-color var(--duration-base) var(--ease-standard), box-shadow var(--duration-base) var(--ease-standard); }
.setting-input:focus { border-color: var(--accent-border); box-shadow: var(--shadow-glow-soft); }
.setting-tip { color: var(--text-disabled); font-size: 12px; margin-top: 6px; }
.save-btn { background: var(--accent-soft); border: 1px solid var(--accent-border); color: var(--accent); padding: var(--space-md) var(--space-xl); border-radius: var(--radius-sm); cursor: pointer; font-family: var(--font-mono); font-size: 15px; font-weight: bold; transition: background var(--duration-base) var(--ease-standard), color var(--duration-base) var(--ease-standard), box-shadow var(--duration-base) var(--ease-standard); width: 100%; margin-top: var(--space-sm); }
.save-btn:hover { background: var(--accent); color: var(--text-inverse); box-shadow: var(--shadow-glow-soft); }
.settings-divider { margin: var(--space-3xl) 0 var(--space-xl); border-bottom: 1px solid var(--border-subtle); color: var(--text-disabled); font-size: 11px; letter-spacing: 2px; text-transform: uppercase; }
.readonly-input { background: var(--bg-field-muted) !important; border-color: var(--border-subtle) !important; color: var(--text-disabled) !important; cursor: not-allowed; }
</style>
