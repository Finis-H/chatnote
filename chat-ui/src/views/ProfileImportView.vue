<script setup>
import {
  PROFILE_IMPORT_MAX_CHARS,
  importFile,
  isImporting,
  profileImportLockReason,
  profileImportNormalizedLength,
  profileImportOriginalLength,
  profileImportPendingCount,
  profileImportPreview,
  profileImportStage,
  useNeuroLink
} from '../composables/useNeuroLink';

const { confirmImport, commitProfileImport, cancelProfileImport, switchView, showToast } = useNeuroLink();

function handleFileChange(e) {
  const file = e.target.files[0];
  if (profileImportStage.value !== 'idle') {
    showToast("⚠️ 上一份画像导入尚未完成。");
    e.target.value = '';
    return;
  }
  if (file && (file.name.endsWith('.md') || file.name.endsWith('.txt'))) {
    importFile.value = file;
  } else {
    showToast("⚠️ 仅支持导入 .md 或 .txt 格式的文档");
    e.target.value = '';
  }
}
</script>

<template>
  <div class="scroll-container">
    <h2 class="view-title">🌱 个性偏好初始化</h2>
    <div class="settings-panel">
      <p class="memory-subtitle">上传一份包含你个人偏好、编程习惯或自我介绍的文档，系统会先整理成可确认版本，再进入记忆流程。</p>

      <div v-if="profileImportStage === 'locked'" class="locked-panel">
        <div class="panel-title">上一份导入仍在等待记忆结算</div>
        <p>{{ profileImportLockReason || `还有 ${profileImportPendingCount} 条待审记忆未完成。` }}</p>
        <button class="save-btn" @click="switchView('memory')">前往记忆同步</button>
      </div>

      <div v-else-if="profileImportStage === 'preview'" class="preview-panel">
        <div class="panel-title">标准化预览</div>
        <div class="import-stats">
          <span>原文 {{ profileImportOriginalLength }} 字符</span>
          <span>整理后 {{ profileImportNormalizedLength }} 字符</span>
        </div>
        <textarea class="preview-text" :value="profileImportPreview" readonly></textarea>
        <div class="action-row">
          <button class="ghost-btn" @click="cancelProfileImport">取消导入</button>
          <button class="save-btn" @click="commitProfileImport">确认提交到记忆待审</button>
        </div>
      </div>

      <div v-else class="import-zone">
        <div class="limit-tip">当前上限：{{ PROFILE_IMPORT_MAX_CHARS }} 字符</div>
        <input type="file" id="profile-upload" @change="handleFileChange" accept=".md,.txt" :disabled="profileImportStage !== 'idle'" hidden />
        <label for="profile-upload" class="upload-label">
          {{ importFile ? '📄 ' + importFile.name : '点击选择初始化文档 (.md / .txt)' }}
        </label>
        <button class="save-btn" :disabled="!importFile || isImporting || profileImportStage !== 'idle'" @click="confirmImport">
          {{ profileImportStage === 'preparing' ? '正在标准化整理...' : profileImportStage === 'committing' ? '正在提交到记忆流程...' : '开始标准化预览' }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.scroll-container { padding: var(--space-3xl); display: flex; flex-direction: column; gap: var(--space-xl); height: 100%; overflow-y: auto; }
.scroll-container::-webkit-scrollbar { width: 6px; }
.scroll-container::-webkit-scrollbar-thumb { background: var(--border-strong); border-radius: var(--radius-xs); }
.view-title { color: var(--text-primary); font-size: 18px; font-weight: normal; margin-bottom: var(--space-sm); }
.settings-panel { background: var(--bg-panel); border: 1px solid var(--border-subtle); border-radius: var(--radius-lg); padding: var(--space-3xl); }
.memory-subtitle { color: var(--text-muted); font-size: 13px; margin-top: var(--space-xs); }
.limit-tip { color: var(--text-disabled); font-size: 12px; font-family: var(--font-mono); }
.upload-label { display: block; width: 100%; padding: var(--space-4xl); border: 2px dashed var(--border-strong); border-radius: var(--radius-md); text-align: center; color: var(--text-muted); cursor: pointer; transition: border-color var(--duration-base) var(--ease-standard), color var(--duration-base) var(--ease-standard), background var(--duration-base) var(--ease-standard); margin: var(--space-xl) 0; }
.upload-label:hover { border-color: var(--accent-border); color: var(--accent); background: var(--accent-soft); }
.save-btn { background: var(--accent-soft); border: 1px solid var(--accent-border); color: var(--accent); padding: var(--space-md) var(--space-xl); border-radius: var(--radius-sm); cursor: pointer; font-family: var(--font-mono); font-size: 15px; font-weight: bold; transition: background var(--duration-base) var(--ease-standard), color var(--duration-base) var(--ease-standard), box-shadow var(--duration-base) var(--ease-standard), border-color var(--duration-base) var(--ease-standard); width: 100%; margin-top: var(--space-sm); }
.save-btn:hover:not(:disabled) { background: var(--accent); color: var(--text-inverse); box-shadow: var(--shadow-glow-soft); }
.save-btn:disabled { border-color: var(--border-strong); color: var(--text-disabled); cursor: not-allowed; background: transparent; }
.panel-title { color: var(--text-primary); font-size: 15px; margin: var(--space-xl) 0 var(--space-sm); }
.preview-panel, .locked-panel { margin-top: var(--space-xl); }
.import-stats { display: flex; gap: var(--space-lg); color: var(--text-muted); font-size: 12px; margin-bottom: var(--space-sm); }
.preview-text { width: 100%; min-height: 360px; resize: vertical; box-sizing: border-box; background: var(--bg-console); border: 1px solid var(--border-strong); border-radius: var(--radius-md); color: var(--text-secondary); padding: var(--space-lg); line-height: 1.6; font-family: var(--font-mono); font-size: 13px; }
.action-row { display: flex; gap: var(--space-md); margin-top: var(--space-md); }
.action-row .save-btn { margin-top: 0; }
.ghost-btn { width: 40%; background: transparent; border: 1px solid var(--border-strong); color: var(--text-muted); padding: var(--space-md) var(--space-xl); border-radius: var(--radius-sm); cursor: pointer; font-family: var(--font-mono); font-size: 14px; transition: border-color var(--duration-base) var(--ease-standard), color var(--duration-base) var(--ease-standard), background var(--duration-base) var(--ease-standard); }
.ghost-btn:hover { border-color: var(--text-muted); color: var(--text-primary); background: var(--bg-hover); }
.locked-panel { border: 1px solid var(--danger-border); border-radius: var(--radius-md); padding: 18px; background: var(--bg-danger-soft); }
.locked-panel p { color: var(--text-secondary); line-height: 1.6; }
</style>
