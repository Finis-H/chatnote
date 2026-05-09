<script setup>
import { ref, onMounted, onUnmounted, defineAsyncComponent } from 'vue';
import { getCurrentWindow } from '@tauri-apps/api/window';
import { register, unregister } from '@tauri-apps/plugin-global-shortcut';
import { activeView, pendingCount, userInput, systemToast, inputError, deleteModal, currentNote, useNeuroLink } from './composables/useNeuroLink';

import './assets/cyber-theme.css'; // 载入全局样式

// 懒加载视窗组件，极致优化初始启动速度
const TerminalView = defineAsyncComponent(() => import('./views/TerminalView.vue'));
const KnowledgeListView = defineAsyncComponent(() => import('./views/KnowledgeListView.vue'));
const NoteDetailView = defineAsyncComponent(() => import('./views/NoteDetailView.vue'));
const MemoryStaging = defineAsyncComponent(() => import('./views/MemoryStaging.vue'));
const SettingsView = defineAsyncComponent(() => import('./views/SettingsView.vue'));
const ProfileImportView = defineAsyncComponent(() => import('./views/ProfileImportView.vue'));

const { connectWebSocket, destroyLink, sendChatCommand, switchView, confirmDelete } = useNeuroLink();
const appWindow = getCurrentWindow();
const isSidebarCollapsed = ref(false);

function toggleSidebar() { isSidebarCollapsed.value = !isSidebarCollapsed.value; }
function cancelDelete() { deleteModal.value.show = false; }
function handleKeyDown(event) { if (event.key === 'Escape') appWindow.hide(); }

let isToggling = false;
async function toggleVaultOS() {
  if (isToggling) return;
  isToggling = true;
  try {
    const isVisible = await appWindow.isVisible();
    isVisible ? await appWindow.hide() : (await appWindow.unminimize(), await appWindow.show(), await appWindow.setFocus());
  } finally { setTimeout(() => { isToggling = false; }, 500); }
}

onMounted(async () => {
  connectWebSocket();
  window.addEventListener('keydown', handleKeyDown);
  try { await register('Alt+V', toggleVaultOS); } catch (e) {}
});

onUnmounted(async () => {
  destroyLink();
  window.removeEventListener('keydown', handleKeyDown);
  await unregister('Alt+V');
});
</script>

<template>
  <div class="magic-box" data-tauri-drag-region>
    <div class="title-bar" data-tauri-drag-region>
      <div class="left-group">
        <button class="fold-btn" @click="toggleSidebar">≡</button>
        <span class="os-name" data-tauri-drag-region>Vault OS // Core</span>
      </div>
      <div class="status-badge" data-tauri-drag-region>ONLINE</div>
    </div>
    
    <div class="workspace-body">
      <aside class="sidebar" :class="{ 'collapsed': isSidebarCollapsed }">
        <div class="nav-group">
          <div class="nav-item" :class="{active: activeView==='chat'}" @click="switchView('chat')">
            <span class="icon">💬</span><span class="label">主控终端</span>
          </div>
          <div class="nav-item" :class="{active: activeView==='news'}" @click="switchView('news')">
            <span class="icon">📰</span><span class="label">新闻信息</span>
          </div>
          <div class="nav-item" :class="{active: activeView==='favorites'}" @click="switchView('favorites')">
            <span class="icon">⭐</span><span class="label">订阅收藏</span>
          </div>
          <div class="nav-item" :class="{active: activeView==='memory'}" @click="switchView('memory')">
            <span class="icon">🧠</span><span class="label">记忆同步</span>
            <span class="badge pulse-anim" v-if="pendingCount > 0">{{ pendingCount }}</span>
          </div>
          <div class="nav-item" :class="{active: activeView==='profile_import'}" @click="switchView('profile_import')">
            <span class="icon">🌱</span><span class="label">画像导入</span>
          </div>
          <div class="nav-item" :class="{active: activeView==='settings'}" @click="switchView('settings')">
            <span class="icon">⚙️</span><span class="label">引擎设置</span>
          </div>
        </div>
      </aside>

      <main class="center-viewport">
        <div class="view-content">
          <TerminalView v-show="activeView === 'chat'" />
          <KnowledgeListView v-if="activeView === 'news'" type="news" />
          <KnowledgeListView v-if="activeView === 'favorites'" type="favorites" />
          <NoteDetailView v-if="activeView === 'note_detail'" />
          <MemoryStaging v-if="activeView === 'memory'" />
          <SettingsView v-if="activeView === 'settings'" />
          <ProfileImportView v-if="activeView === 'profile_import'" />
        </div>

        <div class="fixed-console" :class="{ 'error-shake': inputError }">
          <div class="context-pill" v-if="activeView==='note_detail'">📍 讨论中: {{ currentNote.title }}</div>
          <span class="prompt-icon">❯</span>
          <input v-model="userInput" @keyup.enter="sendChatCommand" placeholder="下达指令..." autofocus />
        </div>
      </main>

      <aside class="sidebar side-right" :class="{ 'collapsed': isSidebarCollapsed }">
        <div class="nav-group">
          <div class="nav-item"><span class="icon">📓</span><span class="label">个人笔记</span></div>
        </div>
      </aside>
    </div>

    <div class="custom-modal-overlay" v-if="deleteModal.show" @click="cancelDelete">
      <div class="custom-modal" @click.stop>
        <div class="modal-icon">⚠️</div>
        <h3 class="modal-title">系统删除确认</h3>
        <p class="modal-desc">
          确定要彻底销毁档案 <span class="highlight-text">《{{ deleteModal.note?.title }}》</span> 吗？<br>
          <span class="warning-text">物理文件与神经对话记录将被永久抹除，不可逆转。</span>
        </p>
        <div class="modal-actions">
          <button class="btn-cancel" @click="cancelDelete">取消指令</button>
          <button class="btn-confirm" @click="confirmDelete">执行销毁</button>
        </div>
      </div>
    </div>

    <div class="cyber-toast" :class="{ 'toast-visible': systemToast.show }">
      <span class="toast-icon">🩺</span><span class="toast-text">{{ systemToast.message }}</span>
    </div>
  </div>
</template>

<style scoped>
/* 仅保留骨架布局级别的 CSS */
.magic-box { display: flex; flex-direction: column; width: 100vw; height: 100vh; overflow: hidden; background: #0a0a0c; font-family: 'Consolas', monospace; color: #d1d1d1; }
.title-bar { height: 40px; display: flex; align-items: center; justify-content: space-between; padding: 0 15px; background: #000; border-bottom: 1px solid #222; user-select: none; }
.left-group { display: flex; align-items: center; }
.fold-btn { background: none; border: none; color: #fff; font-size: 20px; cursor: pointer; margin-right: 15px; }
.os-name { font-size: 12px; color: #666; letter-spacing: 2px; }
.status-badge { font-size: 10px; color: #00ffcc; font-weight: bold; }

.workspace-body { display: flex; flex: 1; overflow: hidden; }
.sidebar { width: 200px; background: rgba(0,0,0,0.4); border-right: 1px solid #1a1a1a; transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1); overflow: hidden; display: flex; flex-direction: column; white-space: nowrap; }
.sidebar.collapsed { width: 60px; }
.sidebar.collapsed .label { opacity: 0; pointer-events: none; }
.side-right { border-right: none; border-left: 1px solid #1a1a1a; }
.nav-group { padding: 15px 0; }
.nav-item { padding: 12px 20px; cursor: pointer; display: flex; align-items: center; gap: 15px; color: #888; transition: all 0.2s; }
.nav-item:hover, .nav-item.active { background: rgba(0, 255, 204, 0.05); color: #00ffcc; border-left: 2px solid #00ffcc; }
.nav-item .icon { font-size: 18px; }
.badge { background: #ff4d4f; color: #fff; font-size: 11px; font-weight: bold; padding: 2px 6px; border-radius: 10px; margin-left: auto; }
.pulse-anim { animation: pulse-glow 1.5s infinite; }

.center-viewport { flex: 1; display: flex; flex-direction: column; background: #0d0d0f; min-width: 400px; overflow: hidden;}
.view-content { flex: 1; overflow: hidden; display: flex; flex-direction: column;}

.fixed-console { height: 65px; min-height: 65px; background: #050505; border-top: 1px solid #222; display: flex; align-items: center; padding: 0 25px; gap: 15px; position: relative; }
.context-pill { position: absolute; top: -25px; left: 25px; background: #00ffcc; color: #000; font-size: 10px; font-weight: bold; padding: 3px 8px; border-radius: 4px; }
.prompt-icon { color: #00ffcc; font-weight: bold; }
.fixed-console input { flex: 1; background: transparent; border: none; outline: none; color: #fff; font-size: 15px; font-family: 'Consolas'; }

.error-shake { animation: shake 0.4s; background: rgba(255,0,0,0.1) !important; }
@keyframes shake { 0%,100%{transform:translateX(0)} 25%{transform:translateX(-5px)} 75%{transform:translateX(5px)} }
@keyframes pulse-glow { 0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(255, 77, 79, 0.7); } 70% { transform: scale(1); box-shadow: 0 0 0 6px rgba(255, 77, 79, 0); } 100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(255, 77, 79, 0); } }

/* 弹窗与 Toast 动画 */
.cyber-toast { position: fixed; top: 20px; left: 50%; transform: translateX(-50%) translateY(-100px); background: rgba(0, 0, 0, 0.85); border: 1px solid #00ffcc; border-radius: 8px; padding: 12px 25px; display: flex; align-items: center; gap: 10px; box-shadow: 0 0 20px rgba(0, 255, 204, 0.2); z-index: 10000; transition: transform 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275), opacity 0.4s; pointer-events: none; opacity: 0; }
.cyber-toast.toast-visible { transform: translateX(-50%) translateY(0); opacity: 1; }
.toast-icon { font-size: 18px; }
.toast-text { color: #00ffcc; font-size: 14px; letter-spacing: 0.5px; }

.custom-modal-overlay { position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background: rgba(0, 0, 0, 0.7); backdrop-filter: blur(5px); display: flex; justify-content: center; align-items: center; z-index: 9999; animation: fadeIn 0.2s ease-out; }
.custom-modal { background: #0d0d0f; border: 1px solid #333; border-top: 2px solid #ff4d4f; padding: 30px; border-radius: 8px; width: 400px; text-align: center; box-shadow: 0 20px 50px rgba(0,0,0,0.8); animation: slideUp 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275); }
.modal-icon { font-size: 32px; margin-bottom: 15px; }
.modal-title { color: #ffffff; font-size: 18px; margin-bottom: 10px; font-weight: normal; letter-spacing: 1px; }
.modal-desc { color: #888; font-size: 13px; line-height: 1.6; margin-bottom: 25px; }
.highlight-text { color: #00ffcc; }
.warning-text { color: #ff4d4f; font-size: 12px; display: block; margin-top: 8px; }
.modal-actions { display: flex; gap: 15px; justify-content: center; }
.modal-actions button { padding: 8px 25px; border: none; border-radius: 4px; font-family: 'Consolas'; font-size: 13px; cursor: pointer; transition: all 0.2s; }
.btn-cancel { background: rgba(255,255,255,0.05); color: #ccc; border: 1px solid #444; }
.btn-cancel:hover { background: rgba(255,255,255,0.1); color: #fff; }
.btn-confirm { background: rgba(255, 77, 79, 0.1); color: #ff4d4f; border: 1px solid rgba(255, 77, 79, 0.4); }
.btn-confirm:hover { background: #ff4d4f; color: #000; box-shadow: 0 0 15px rgba(255, 77, 79, 0.4); }

@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
@keyframes slideUp { from { transform: translateY(20px) scale(0.95); opacity: 0; } to { transform: translateY(0) scale(1); opacity: 1; } }
</style>