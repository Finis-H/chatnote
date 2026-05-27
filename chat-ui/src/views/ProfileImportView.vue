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
      <p class="memory-subtitle">上传一份包含你个人偏好、编程习惯或自我介绍的文档，管家会先整理成可确认版本，再进入记忆流程。</p>

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
          <button class="save-btn" @click="commitProfileImport">确认写入记忆</button>
        </div>
      </div>

      <div v-else class="import-zone">
        <div class="limit-tip">当前上限：{{ PROFILE_IMPORT_MAX_CHARS }} 字符</div>
        <input type="file" id="profile-upload" @change="handleFileChange" accept=".md,.txt" :disabled="profileImportStage !== 'idle'" hidden />
        <label for="profile-upload" class="upload-label">
          {{ importFile ? '📄 ' + importFile.name : '点击选择初始化文档 (.md / .txt)' }}
        </label>
        <button class="save-btn" :disabled="!importFile || isImporting || profileImportStage !== 'idle'" @click="confirmImport">
          {{ profileImportStage === 'preparing' ? '⚡ 正在标准化整理...' : profileImportStage === 'committing' ? '⚡ 正在写入记忆...' : '开始标准化预览' }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.scroll-container { padding: 30px; display: flex; flex-direction: column; gap: 20px; height: 100%; overflow-y: auto; }
.scroll-container::-webkit-scrollbar { width: 6px; }
.scroll-container::-webkit-scrollbar-thumb { background: #333; border-radius: 3px; }
.view-title { color: #fff; font-size: 18px; font-weight: normal; margin-bottom: 10px; }
.settings-panel { background: rgba(255, 255, 255, 0.02); border: 1px solid #222; border-radius: 10px; padding: 30px; }
.memory-subtitle { color: #888; font-size: 13px; margin-top: 5px; }
.limit-tip { color: #666; font-size: 12px; font-family: 'Consolas'; }
.upload-label { display: block; width: 100%; padding: 40px; border: 2px dashed #333; border-radius: 8px; text-align: center; color: #888; cursor: pointer; transition: all 0.2s; margin: 20px 0; }
.upload-label:hover { border-color: #00ffcc; color: #00ffcc; background: rgba(0,255,204,0.02); }
.save-btn { background: rgba(0, 255, 204, 0.1); border: 1px solid #00ffcc; color: #00ffcc; padding: 12px 20px; border-radius: 6px; cursor: pointer; font-family: 'Consolas'; font-size: 15px; font-weight: bold; transition: all 0.2s; width: 100%; margin-top: 10px; }
.save-btn:hover:not(:disabled) { background: #00ffcc; color: #000; box-shadow: 0 0 20px rgba(0,255,204,0.4); }
.save-btn:disabled { border-color: #444; color: #666; cursor: not-allowed; background: transparent; }
.panel-title { color: #fff; font-size: 15px; margin: 20px 0 10px; }
.preview-panel, .locked-panel { margin-top: 20px; }
.import-stats { display: flex; gap: 15px; color: #777; font-size: 12px; margin-bottom: 10px; }
.preview-text { width: 100%; min-height: 360px; resize: vertical; box-sizing: border-box; background: rgba(0,0,0,0.45); border: 1px solid #333; border-radius: 8px; color: #ddd; padding: 15px; line-height: 1.6; font-family: 'Consolas', monospace; font-size: 13px; }
.action-row { display: flex; gap: 12px; margin-top: 12px; }
.action-row .save-btn { margin-top: 0; }
.ghost-btn { width: 40%; background: transparent; border: 1px solid #444; color: #aaa; padding: 12px 20px; border-radius: 6px; cursor: pointer; font-family: 'Consolas'; font-size: 14px; transition: all 0.2s; }
.ghost-btn:hover { border-color: #888; color: #fff; }
.locked-panel { border: 1px solid rgba(255, 77, 79, 0.35); border-radius: 8px; padding: 18px; background: rgba(255, 77, 79, 0.05); }
.locked-panel p { color: #aaa; line-height: 1.6; }
</style>
