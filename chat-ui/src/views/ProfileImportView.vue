<script setup>
import { importFile, isImporting, useNeuroLink } from '../composables/useNeuroLink';
const { confirmImport, showToast } = useNeuroLink();

function handleFileChange(e) {
  const file = e.target.files[0];
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
      <p class="memory-subtitle">上传一份包含你个人偏好、编程习惯或自我介绍的文档，管家将通过深度扫描重塑你的画像。</p>
      <div class="import-zone">
        <input type="file" id="profile-upload" @change="handleFileChange" accept=".md,.txt" hidden />
        <label for="profile-upload" class="upload-label">
          {{ importFile ? '📄 ' + importFile.name : '点击选择初始化文档 (.md / .txt)' }}
        </label>
      </div>
      <button class="save-btn" :disabled="!importFile || isImporting" @click="confirmImport">
        {{ isImporting ? '⚡ 正在解析神经元...' : '开始执行提取指令' }}
      </button>
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
.upload-label { display: block; width: 100%; padding: 40px; border: 2px dashed #333; border-radius: 8px; text-align: center; color: #888; cursor: pointer; transition: all 0.2s; margin: 20px 0; }
.upload-label:hover { border-color: #00ffcc; color: #00ffcc; background: rgba(0,255,204,0.02); }
.save-btn { background: rgba(0, 255, 204, 0.1); border: 1px solid #00ffcc; color: #00ffcc; padding: 12px 20px; border-radius: 6px; cursor: pointer; font-family: 'Consolas'; font-size: 15px; font-weight: bold; transition: all 0.2s; width: 100%; margin-top: 10px; }
.save-btn:hover:not(:disabled) { background: #00ffcc; color: #000; box-shadow: 0 0 20px rgba(0,255,204,0.4); }
.save-btn:disabled { border-color: #444; color: #666; cursor: not-allowed; background: transparent; }
</style>