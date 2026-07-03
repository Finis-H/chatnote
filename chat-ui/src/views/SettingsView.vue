<script setup>
import { sysConfig, useNeuroLink } from '../composables/useNeuroLink';
const { saveSystemConfig } = useNeuroLink();
</script>

<template>
  <div class="scroll-container">
    <header class="settings-header">
      <div>
        <p class="eyebrow">Vault OS Runtime</p>
        <h2 class="view-title">引擎设置（Engine Control）</h2>
        <p class="view-desc">配置对话模型、向量模型与兼容 OpenAI 的代理端点。</p>
      </div>
      <div class="status-chips" aria-label="配置状态">
        <span class="status-chip">本地配置</span>
        <span class="status-chip accent">保存后重载</span>
      </div>
    </header>

    <div class="settings-stack">
      <section class="settings-section" aria-labelledby="rag-core-title">
        <div class="section-head">
          <div>
            <p class="section-kicker">Knowledge Retrieval</p>
            <h3 id="rag-core-title">知识库向量引擎（RAG Core）</h3>
            <p>用于笔记摄入、语义检索和知识库召回。</p>
          </div>
          <span class="section-chip">可选增强</span>
        </div>

        <div class="setting-row">
          <div class="setting-copy">
            <div class="label-line">
              <label for="embed-model">向量计算模型（Embedding Model）</label>
              <span class="field-chip muted">系统字段</span>
            </div>
            <p>当前向量化服务使用的模型，由系统配置读取。</p>
          </div>
          <input id="embed-model" class="setting-input readonly-input" v-model="sysConfig.embed_model" disabled />
        </div>

        <div class="setting-row">
          <div class="setting-copy">
            <div class="label-line">
              <label for="embed-api-key">向量密钥（Embedding API Key）</label>
              <span class="field-chip">可选</span>
            </div>
            <p>用于将本地笔记转化为高维向量；未填写时摄入功能不可用。</p>
          </div>
          <input id="embed-api-key" class="setting-input" type="password" v-model="sysConfig.embed_api_key" placeholder="请输入千问向量密钥（Embedding API Key）" />
        </div>
      </section>

      <section class="settings-section" aria-labelledby="chat-core-title">
        <div class="section-head">
          <div>
            <p class="section-kicker">Conversation Runtime</p>
            <h3 id="chat-core-title">主对话核心模型（Chat Core）</h3>
            <p>用于主对话、任务规划和最终回复生成。</p>
          </div>
          <span class="section-chip accent">核心配置</span>
        </div>

        <div class="setting-row">
          <div class="setting-copy">
            <div class="label-line">
              <label for="base-url">代理端点（API Base URL）</label>
              <span class="field-chip required">必填</span>
            </div>
            <p>兼容 OpenAI 格式的第三方 API，或本地 Ollama 地址。</p>
          </div>
          <input id="base-url" class="setting-input" v-model="sysConfig.base_url" placeholder="例如：https://api.deepseek.com/v1" />
        </div>

        <div class="setting-row">
          <div class="setting-copy">
            <div class="label-line">
              <label for="api-key">密钥（API Key）</label>
              <span class="field-chip required">必填</span>
            </div>
            <p>用于访问主对话模型服务，请使用当前代理端点对应的密钥。</p>
          </div>
          <input id="api-key" class="setting-input" type="password" v-model="sysConfig.api_key" placeholder="sk-..." />
        </div>

        <div class="setting-row">
          <div class="setting-copy">
            <div class="label-line">
              <label for="model-max">主算力模型（Model Max）</label>
              <span class="field-chip required">必填</span>
            </div>
            <p>承担复杂推理、任务规划和最终回复生成。</p>
          </div>
          <input id="model-max" class="setting-input" v-model="sysConfig.model_max" placeholder="例如：deepseek-chat" />
        </div>

        <div class="setting-row">
          <div class="setting-copy">
            <div class="label-line">
              <label for="model-mini">轻量提纯模型（Model Mini）</label>
              <span class="field-chip">推荐</span>
            </div>
            <p>用于轻量摘要、提纯和低成本辅助任务。</p>
          </div>
          <input id="model-mini" class="setting-input" v-model="sysConfig.model_mini" placeholder="例如：gpt-3.5-turbo" />
        </div>
      </section>

      <footer class="settings-actions">
        <div>
          <p class="action-title">应用配置变更</p>
          <p class="action-desc">配置保存后会重新加载引擎运行参数。</p>
        </div>
        <button class="save-btn" @click="saveSystemConfig">保存并重载配置</button>
      </footer>
    </div>
  </div>
</template>

<style scoped>
.scroll-container { padding: var(--space-3xl); display: flex; flex-direction: column; gap: var(--space-2xl); height: 100%; overflow-y: auto; }
.scroll-container::-webkit-scrollbar { width: 6px; }
.scroll-container::-webkit-scrollbar-thumb { background: var(--border-strong); border-radius: var(--radius-xs); }
.settings-header { display: flex; justify-content: space-between; align-items: flex-start; gap: var(--space-xl); padding-bottom: var(--space-lg); border-bottom: 1px solid var(--border-strong); }
.eyebrow { margin: 0 0 var(--space-xs); color: var(--accent); font-family: var(--font-mono); font-size: 11px; letter-spacing: 1.4px; text-transform: uppercase; }
.view-title { color: var(--text-primary); font-size: 24px; line-height: 1.2; font-weight: 600; margin: 0; }
.view-desc { color: var(--text-muted); font-size: 13px; line-height: 1.6; margin: var(--space-sm) 0 0; }
.status-chips { display: flex; flex-wrap: wrap; justify-content: flex-end; gap: var(--space-sm); }
.status-chip, .section-chip, .field-chip { display: inline-flex; align-items: center; min-height: 22px; padding: 0 var(--space-sm); border: 1px solid var(--border-strong); border-radius: var(--radius-pill); background: var(--bg-panel); color: var(--text-muted); font-family: var(--font-mono); font-size: 11px; white-space: nowrap; }
.status-chip.accent, .section-chip.accent { border-color: var(--accent-border); background: var(--accent-soft); color: var(--accent-strong); }
.settings-stack { display: flex; flex-direction: column; gap: var(--space-xl); max-width: 1040px; }
.settings-section { background: var(--bg-panel); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); overflow: hidden; }
.section-head { display: flex; justify-content: space-between; align-items: flex-start; gap: var(--space-xl); padding: var(--space-xl) var(--space-2xl); background: var(--bg-panel-raised); border-bottom: 1px solid var(--border-subtle); }
.section-kicker { margin: 0 0 var(--space-xs); color: var(--text-disabled); font-family: var(--font-mono); font-size: 11px; letter-spacing: 1.2px; text-transform: uppercase; }
.section-head h3 { margin: 0; color: var(--text-primary); font-size: 16px; line-height: 1.3; font-weight: 600; }
.section-head p:not(.section-kicker) { margin: var(--space-xs) 0 0; color: var(--text-muted); font-size: 13px; line-height: 1.6; }
.section-chip { flex: 0 0 auto; margin-top: var(--space-xs); }
.setting-row { display: grid; grid-template-columns: minmax(220px, 0.85fr) minmax(260px, 1fr); gap: var(--space-2xl); align-items: center; padding: var(--space-xl) var(--space-2xl); border-top: 1px solid var(--border-muted); }
.section-head + .setting-row { border-top: 0; }
.setting-copy { min-width: 0; }
.label-line { display: flex; align-items: center; flex-wrap: wrap; gap: var(--space-sm); }
.label-line label { color: var(--accent-strong); font-size: 14px; line-height: 1.4; font-weight: 600; }
.setting-copy p { margin: var(--space-xs) 0 0; color: var(--text-muted); font-size: 12px; line-height: 1.6; }
.field-chip { min-height: 20px; padding: 0 var(--space-xs); border-color: var(--border-subtle); background: var(--bg-field-muted); color: var(--text-disabled); font-size: 10px; }
.field-chip.required { border-color: var(--accent-border); background: var(--accent-soft); color: var(--accent-strong); }
.field-chip.muted { color: var(--text-disabled); }
.setting-input { width: 100%; min-width: 0; background: var(--bg-console); border: 1px solid var(--border-strong); color: var(--text-primary); padding: var(--space-md); border-radius: var(--radius-sm); font-family: var(--font-mono); font-size: 14px; transition: border-color var(--duration-base) var(--ease-standard), box-shadow var(--duration-base) var(--ease-standard), background var(--duration-base) var(--ease-standard); }
.setting-input:focus { border-color: var(--accent-border); background: rgba(69, 224, 200, 0.045); box-shadow: var(--shadow-glow-soft); }
.setting-input::placeholder { color: var(--text-disabled); }
.readonly-input { background: var(--bg-field-muted) !important; border-color: var(--border-subtle) !important; color: var(--text-disabled) !important; cursor: not-allowed; }
.settings-actions { display: flex; align-items: center; justify-content: space-between; gap: var(--space-xl); padding: var(--space-xl) var(--space-2xl); border: 1px solid var(--border-strong); border-radius: var(--radius-md); background: var(--bg-panel); }
.action-title { margin: 0; color: var(--text-primary); font-size: 14px; font-weight: 600; }
.action-desc { margin: var(--space-xs) 0 0; color: var(--text-muted); font-size: 12px; line-height: 1.5; }
.save-btn { flex: 0 0 auto; background: var(--accent-soft); border: 1px solid var(--accent-border); color: var(--accent); padding: var(--space-md) var(--space-xl); border-radius: var(--radius-sm); cursor: pointer; font-family: var(--font-mono); font-size: 14px; font-weight: bold; transition: background var(--duration-base) var(--ease-standard), color var(--duration-base) var(--ease-standard), box-shadow var(--duration-base) var(--ease-standard), transform var(--duration-fast) var(--ease-standard); }
.save-btn:hover { background: var(--accent); color: var(--text-inverse); box-shadow: var(--shadow-glow-soft); }
.save-btn:active { transform: translateY(1px); }

@media(max-width: 760px) {
  .scroll-container { padding: var(--space-xl); }
  .settings-header, .section-head, .settings-actions { flex-direction: column; align-items: stretch; }
  .status-chips { justify-content: flex-start; }
  .setting-row { grid-template-columns: 1fr; gap: var(--space-md); padding: var(--space-lg); }
  .section-head, .settings-actions { padding: var(--space-lg); }
  .save-btn { width: 100%; }
}
</style>
