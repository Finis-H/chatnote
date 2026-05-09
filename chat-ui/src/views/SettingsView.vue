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
      <button class="save-btn" @click="saveSystemConfig">⚡ 烧录并热重载引擎</button>
    </div>
  </div>
</template>

<style scoped>
.scroll-container { padding: 30px; display: flex; flex-direction: column; gap: 20px; height: 100%; overflow-y: auto; }
.scroll-container::-webkit-scrollbar { width: 6px; }
.scroll-container::-webkit-scrollbar-thumb { background: #333; border-radius: 3px; }
.view-title { color: #fff; font-size: 18px; font-weight: normal; margin-bottom: 10px; }
.settings-panel { background: rgba(255, 255, 255, 0.02); border: 1px solid #222; border-radius: 10px; padding: 30px; }
.setting-item { display: flex; flex-direction: column; margin-bottom: 25px; }
.setting-item label { color: #00ffcc; font-size: 14px; margin-bottom: 8px; font-weight: bold; }
.setting-input { background: rgba(0,0,0,0.5); border: 1px solid #444; color: #fff; padding: 12px; border-radius: 6px; font-family: 'Consolas'; font-size: 14px; outline: none; transition: all 0.2s; }
.setting-input:focus { border-color: #00ffcc; box-shadow: 0 0 10px rgba(0,255,204,0.1); }
.setting-tip { color: #666; font-size: 12px; margin-top: 6px; }
.save-btn { background: rgba(0, 255, 204, 0.1); border: 1px solid #00ffcc; color: #00ffcc; padding: 12px 20px; border-radius: 6px; cursor: pointer; font-family: 'Consolas'; font-size: 15px; font-weight: bold; transition: all 0.2s; width: 100%; margin-top: 10px; }
.save-btn:hover { background: #00ffcc; color: #000; box-shadow: 0 0 20px rgba(0,255,204,0.4); }
.settings-divider { margin: 30px 0 20px; border-bottom: 1px solid #222; color: #444; font-size: 11px; letter-spacing: 2px; text-transform: uppercase; }
.readonly-input { background: rgba(255, 255, 255, 0.02) !important; border-color: #222 !important; color: #555 !important; cursor: not-allowed; }
</style>