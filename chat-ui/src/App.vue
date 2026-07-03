<script setup>
import { ref, onMounted, onUnmounted, defineAsyncComponent } from 'vue';
import { getCurrentWindow } from '@tauri-apps/api/window';
import { register, unregister } from '@tauri-apps/plugin-global-shortcut';
import { Box, Connection, Document, Expand, Fold, Monitor, Promotion, Setting, Star, Timer, Upload } from '@element-plus/icons-vue';
import { activeView, pendingCount, userInput, systemToast, inputError, deleteModal, pluginPermissionRequest, currentNote, connectionState, useNeuroLink } from './composables/useNeuroLink';
import { activeAgentComponent, activeAgentDock } from './composables/useNeuroLink';
import AgentDock from './components/AgentDock.vue';
import DangerDialog from './components/DangerDialog.vue';
import './assets/cyber-theme.css'; // 载入全局样式

// 懒加载视窗组件，极致优化初始启动速度
const TerminalView = defineAsyncComponent(() => import('./views/TerminalView.vue'));
const KnowledgeListView = defineAsyncComponent(() => import('./views/KnowledgeListView.vue'));
const NoteDetailView = defineAsyncComponent(() => import('./views/NoteDetailView.vue'));
const MemoryStaging = defineAsyncComponent(() => import('./views/MemoryStaging.vue'));
const SettingsView = defineAsyncComponent(() => import('./views/SettingsView.vue'));
const VpmCenterView = defineAsyncComponent(() => import('./views/VpmCenterView.vue'));
const ProfileImportView = defineAsyncComponent(() => import('./views/ProfileImportView.vue'));
const { connectWebSocket, destroyLink, sendChatCommand, switchView, confirmDelete, startTempSession, respondPluginPermission } = useNeuroLink();
const appWindow = getCurrentWindow();
const isSidebarHidden = ref(false);

function toggleSidebar() { isSidebarHidden.value = !isSidebarHidden.value; }
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
        <button
          type="button"
          class="sidebar-toggle"
          :aria-expanded="!isSidebarHidden"
          aria-controls="primary-sidebar"
          :title="isSidebarHidden ? '显示左侧导航' : '隐藏左侧导航'"
          @click="toggleSidebar"
        >
          <component :is="isSidebarHidden ? Expand : Fold" aria-hidden="true" />
        </button>
        <span class="os-name" data-tauri-drag-region>VOS</span>
      </div>
      <div
        class="system-status"
        :class="`status-${connectionState.status}`"
        :title="connectionState.detail"
        :aria-label="connectionState.detail"
        role="status"
        data-tauri-drag-region
      >
        <span class="status-dot" aria-hidden="true"></span>
        <span>{{ connectionState.label }}</span>
      </div>
    </div>
    
    <div class="workspace-body">
      
      <aside id="primary-sidebar" class="sidebar" :class="{ 'sidebar-hidden': isSidebarHidden }" aria-label="Vault OS 主导航">
        <div class="nav-group">
          <section class="nav-section" aria-labelledby="nav-execution-title">
            <div id="nav-execution-title" class="nav-section-title">执行</div>
            <button type="button" class="nav-item" :class="{active: activeView==='chat'}" @click="switchView('chat')">
              <span class="icon"><Monitor aria-hidden="true" /></span><span class="label">主控终端</span>
            </button>
            <button type="button" class="nav-item" :class="{active: activeView==='temp_chat'}" @click="startTempSession">
              <span class="icon"><Timer aria-hidden="true" /></span><span class="label">临时会话</span>
            </button>
          </section>

          <section class="nav-section" aria-labelledby="nav-knowledge-title">
            <div id="nav-knowledge-title" class="nav-section-title">知识</div>
            <button type="button" class="nav-item" :class="{active: activeView==='news'}" @click="switchView('news')">
              <span class="icon"><Document aria-hidden="true" /></span><span class="label">新闻信息</span>
            </button>
            <button type="button" class="nav-item" :class="{active: activeView==='favorites'}" @click="switchView('favorites')">
              <span class="icon"><Star aria-hidden="true" /></span><span class="label">订阅收藏</span>
            </button>
            <button type="button" class="nav-item" :class="{active: activeView==='memory'}" @click="switchView('memory')">
              <span class="icon"><Connection aria-hidden="true" /></span><span class="label">记忆同步</span>
              <span class="badge pulse-anim" v-if="pendingCount > 0">{{ pendingCount }}</span>
            </button>
            <button type="button" class="nav-item" :class="{active: activeView==='profile_import'}" @click="switchView('profile_import')">
              <span class="icon"><Upload aria-hidden="true" /></span><span class="label">画像导入</span>
            </button>
          </section>

          <section class="nav-section" aria-labelledby="nav-system-title">
            <div id="nav-system-title" class="nav-section-title">系统</div>
            <button type="button" class="nav-item" :class="{active: activeView==='settings'}" @click="switchView('settings')">
              <span class="icon"><Setting aria-hidden="true" /></span><span class="label">引擎设置</span>
            </button>
            <button type="button" class="nav-item badge-ready" :class="{active: activeView==='vpm_center'}" @click="switchView('vpm_center')">
              <span class="icon"><Box aria-hidden="true" /></span><span class="label">插件中心</span>
            </button>
          </section>
        </div>
      </aside>

      <main class="center-viewport" :class="{ 'squeezed': activeAgentComponent && activeAgentDock.mode === 'focus' }">
        <div class="view-content">
          <TerminalView v-show="activeView === 'chat' || activeView === 'temp_chat'" />
          <KnowledgeListView v-if="activeView === 'news'" type="news" />
          <KnowledgeListView v-if="activeView === 'favorites'" type="favorites" />
          <NoteDetailView v-if="activeView === 'note_detail'" />
          <MemoryStaging v-if="activeView === 'memory'" />
          <SettingsView v-if="activeView === 'settings'" />
          <ProfileImportView v-if="activeView === 'profile_import'" />
          <VpmCenterView v-if="activeView === 'vpm_center'" />
        </div>

        <div
          v-if="!['settings', 'profile_import', 'vpm_center'].includes(activeView)"
          class="fixed-console"
          :class="{ 'error-shake': inputError }"
        >
          <div class="context-pill" v-if="activeView==='note_detail'">📍 讨论中: {{ currentNote.title }}</div>
          <div class="command-rail">
            <span class="prompt-icon" aria-hidden="true">❯</span>
            <input
              v-model="userInput"
              @keyup.enter="sendChatCommand"
              placeholder="下达指令..."
              aria-label="命令输入"
              autofocus
            />
            <div class="console-actions">
              <span class="shortcut-hint" aria-hidden="true">Enter</span>
              <button type="button" class="send-button" title="发送指令" aria-label="发送指令" @click="sendChatCommand">
                <Promotion aria-hidden="true" />
              </button>
            </div>
          </div>
        </div>
      </main>

      <AgentDock />

    </div>
    <DangerDialog
      :show="deleteModal.show"
      title="系统删除确认"
      :object-name="deleteModal.note?.title || '未命名档案'"
      impact="将删除相关本地文件与对话记录。"
      :irreversible="true"
      risk-tip="删除前请确认该档案不再需要；此操作完成后无法在应用内恢复。"
      confirm-text="确认删除"
      @cancel="cancelDelete"
      @confirm="confirmDelete"
    />

    <div class="custom-modal-overlay" v-if="pluginPermissionRequest" @click.stop>
      <div class="custom-modal permission-modal" @click.stop>
        <div class="modal-icon">!</div>
        <h3 class="modal-title">本轮任务需要插件权限确认</h3>
        <div
          class="permission-item"
          v-for="item in (pluginPermissionRequest.items || [pluginPermissionRequest])"
          :key="`${item.plugin_id || item.plugin_name}-${item.tool_name || 'tool'}`"
        >
          <p class="modal-desc">
            插件 <span class="highlight-text">{{ item.plugin_name || item.plugin_id }}</span>
            <span v-if="item.tool_name"> / {{ item.tool_name }}</span>
            请求敏感权限：<span class="warning-text">{{ item.permissions?.join(', ') }}</span>
          </p>
          <p class="modal-desc">{{ item.reason }}</p>
          <pre class="permission-preview">{{ JSON.stringify(item.preview || {}, null, 2) }}</pre>
        </div>
        <div class="modal-actions">
          <button class="btn-cancel" @click="respondPluginPermission('deny')">拒绝</button>
          <button class="btn-cancel" @click="respondPluginPermission('allow_once')">允许一次</button>
          <button class="btn-confirm" @click="respondPluginPermission('allow_session')">本次会话允许</button>
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
.magic-box { display: flex; flex-direction: column; width: 100vw; height: 100vh; overflow: hidden; background: var(--bg-app); font-family: var(--font-mono); color: var(--text-secondary); }
.title-bar { height: 40px; display: flex; align-items: center; justify-content: space-between; padding: 0 var(--space-lg); background: var(--bg-console); border-bottom: 1px solid var(--border-subtle); user-select: none; }
.left-group { display: flex; align-items: center; }
.sidebar-toggle { width: 26px; height: 26px; margin-right: var(--space-md); border: 1px solid transparent; border-radius: var(--radius-xs); display: inline-flex; align-items: center; justify-content: center; color: var(--text-muted); background: transparent; cursor: pointer; transition: background var(--duration-base) var(--ease-standard), border-color var(--duration-base) var(--ease-standard), color var(--duration-base) var(--ease-standard), box-shadow var(--duration-base) var(--ease-standard); }
.sidebar-toggle:hover { border-color: var(--border-strong); background: var(--bg-hover); color: var(--accent-strong); }
.sidebar-toggle svg { width: 15px; height: 15px; }
.os-name { font-size: 12px; color: var(--text-disabled); letter-spacing: 2px; }
.system-status { height: 24px; display: inline-flex; align-items: center; gap: var(--space-xs); padding: 0 var(--space-sm); border: 1px solid var(--border-strong); border-radius: var(--radius-sm); background: var(--bg-panel); color: var(--text-muted); font-size: 11px; font-weight: bold; line-height: 1; }
.status-dot { width: 7px; height: 7px; flex: 0 0 7px; border-radius: 50%; background: var(--text-disabled); }
.status-connected { color: var(--success); border-color: rgba(121, 214, 143, 0.36); }
.status-connected .status-dot { background: var(--success); }
.status-connecting { color: var(--accent); border-color: var(--accent-border); }
.status-connecting .status-dot { background: var(--accent); animation: status-pulse 1.2s infinite; }
.status-reconnecting { color: var(--warning); border-color: rgba(242, 189, 92, 0.42); }
.status-reconnecting .status-dot { background: var(--warning); animation: status-pulse 1.2s infinite; }
.status-offline { color: var(--danger); border-color: var(--danger-border); }
.status-offline .status-dot { background: var(--danger); }

.workspace-body { display: flex; flex: 1; overflow: hidden; }
.sidebar { width: 188px; flex: 0 0 188px; background: var(--bg-shell); border-right: 1px solid var(--border-muted); overflow: hidden; display: flex; flex-direction: column; white-space: nowrap; transition: width var(--duration-slow) var(--ease-standard), flex-basis var(--duration-slow) var(--ease-standard), border-color var(--duration-slow) var(--ease-standard); }
.sidebar.sidebar-hidden { width: 0; flex-basis: 0; border-right-color: transparent; }
.side-right { border-right: none; border-left: 1px solid var(--border-muted); }
.nav-group { padding: var(--space-sm) 0; display: flex; flex-direction: column; gap: var(--space-xs); }
.nav-section { padding: var(--space-2xs) 0 var(--space-xs); }
.nav-section:last-child { border-bottom: none; }
.nav-section-title { padding: var(--space-xs) var(--space-lg); color: var(--text-disabled); font-size: 10px; font-weight: bold; letter-spacing: 0.8px; }
.nav-item { width: 100%; min-height: 35px; padding: var(--space-xs) var(--space-md) var(--space-xs) var(--space-lg); cursor: pointer; display: flex; align-items: center; gap: var(--space-sm); color: var(--text-muted); background: transparent; border: 0; border-left: 2px solid transparent; border-radius: 0; box-sizing: border-box; font: inherit; text-align: left; transition: background var(--duration-base) var(--ease-standard), color var(--duration-base) var(--ease-standard), border-color var(--duration-base) var(--ease-standard), box-shadow var(--duration-base) var(--ease-standard); }
.nav-item:hover { background: var(--bg-hover); color: var(--text-primary); border-left-color: var(--border-strong); }
.nav-item.active { background: var(--accent-soft); color: var(--accent-strong); border-left-color: var(--accent); box-shadow: none; }
.nav-item:focus-visible { position: relative; z-index: 1; background: var(--bg-hover-strong); color: var(--accent-strong); }
.nav-item .icon { width: 18px; height: 18px; flex: 0 0 18px; display: inline-flex; align-items: center; justify-content: center; color: var(--text-disabled); line-height: 1; }
.nav-item .icon svg { width: 15px; height: 15px; }
.nav-item:hover .icon, .nav-item.active .icon { color: var(--accent-strong); }
.nav-item .label { overflow: hidden; text-overflow: ellipsis; }
.nav-item.badge-ready::after { content: ''; min-width: 20px; height: 18px; margin-left: auto; visibility: hidden; }
.badge { min-width: 20px; height: 18px; display: inline-flex; align-items: center; justify-content: center; background: var(--danger); color: var(--text-primary); font-size: 11px; font-weight: bold; padding: 0 var(--space-xs); border-radius: var(--radius-pill); margin-left: auto; }
.pulse-anim { animation: pulse-glow 1.5s infinite; }

.center-viewport { 
  flex: 1; 
  display: flex; 
  flex-direction: column; 
  background: var(--bg-shell); 
  min-width: 320px; 
  overflow: hidden;
  transition: opacity var(--duration-slow) var(--ease-standard), transform var(--duration-slow) var(--ease-standard); 
}
/* 沉浸态下的主视图被挤压变暗 */
.center-viewport.squeezed {
  opacity: 0.3;
  transform: scale(0.98); 
  pointer-events: none; /* 沉浸时防止误触主界面的按钮 */
}
.view-content { flex: 1; min-height: 0; overflow: hidden; display: flex; flex-direction: column;}

.fixed-console { min-height: 78px; flex: 0 0 auto; background: linear-gradient(180deg, rgba(6, 7, 10, 0.96), var(--bg-console)); border-top: 1px solid var(--border-subtle); display: flex; align-items: center; padding: var(--space-md) var(--space-2xl); position: relative; box-shadow: 0 -12px 26px rgba(0, 0, 0, 0.22); }
.context-pill { position: absolute; top: -25px; left: var(--space-2xl); background: var(--accent); color: var(--text-inverse); font-size: 10px; font-weight: bold; padding: var(--space-2xs) var(--space-sm); border-radius: var(--radius-xs); }
.command-rail { width: 100%; min-height: 52px; display: flex; align-items: center; gap: var(--space-md); padding: 0 var(--space-sm) 0 var(--space-lg); border: 1px solid var(--border-strong); border-radius: var(--radius-md); background: rgba(255, 255, 255, 0.025); box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.04); transition: border-color var(--duration-base) var(--ease-standard), box-shadow var(--duration-base) var(--ease-standard), background var(--duration-base) var(--ease-standard); }
.command-rail:focus-within { border-color: var(--accent-border); background: rgba(69, 224, 200, 0.045); box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.06), 0 0 0 3px rgba(69, 224, 200, 0.08), var(--shadow-glow-soft); }
.prompt-icon { flex: 0 0 auto; color: var(--accent); font-size: 20px; font-weight: bold; line-height: 1; text-shadow: 0 0 12px rgba(69, 224, 200, 0.32); }
.fixed-console input { flex: 1; min-width: 0; height: 100%; background: transparent; border: none; color: var(--text-primary); font-size: 15px; font-family: var(--font-mono); outline: none; }
.fixed-console input::placeholder { color: var(--text-disabled); }
.fixed-console input:focus-visible { outline: none; box-shadow: none; }
.console-actions { flex: 0 0 auto; display: flex; align-items: center; gap: var(--space-sm); }
.shortcut-hint { height: 26px; display: inline-flex; align-items: center; padding: 0 var(--space-sm); border: 1px solid var(--border-subtle); border-radius: var(--radius-xs); background: var(--bg-hover); color: var(--text-muted); font-size: 11px; line-height: 1; }
.send-button { width: 34px; height: 34px; display: inline-flex; align-items: center; justify-content: center; border: 1px solid var(--accent-border); border-radius: var(--radius-sm); background: var(--accent-soft); color: var(--accent-strong); cursor: pointer; transition: background var(--duration-base) var(--ease-standard), border-color var(--duration-base) var(--ease-standard), color var(--duration-base) var(--ease-standard), box-shadow var(--duration-base) var(--ease-standard), transform var(--duration-fast) var(--ease-standard); }
.send-button:hover { background: rgba(69, 224, 200, 0.16); border-color: var(--accent); box-shadow: var(--shadow-glow-soft); }
.send-button:active { transform: translateY(1px); }
.send-button svg { width: 17px; height: 17px; }

@media (max-width: 720px) {
  .fixed-console { min-height: 72px; padding: var(--space-sm) var(--space-md); }
  .command-rail { min-height: 48px; gap: var(--space-sm); padding-left: var(--space-md); }
  .shortcut-hint { display: none; }
}

.error-shake { animation: shake 0.4s; background: var(--bg-danger-soft) !important; }
@keyframes shake { 0%,100%{transform:translateX(0)} 25%{transform:translateX(-5px)} 75%{transform:translateX(5px)} }
@keyframes status-pulse { 0%, 100% { opacity: 0.45; } 50% { opacity: 1; } }
@keyframes pulse-glow { 0% { transform: scale(0.95); box-shadow: 0 0 0 0 var(--danger-border); } 70% { transform: scale(1); box-shadow: 0 0 0 6px transparent; } 100% { transform: scale(0.95); box-shadow: 0 0 0 0 transparent; } }

/* 弹窗与 Toast 动画 */
.cyber-toast { position: fixed; top: var(--space-xl); left: 50%; transform: translateX(-50%) translateY(-100px); background: var(--bg-panel-raised); border: 1px solid var(--accent-border); border-radius: var(--radius-md); padding: var(--space-md) var(--space-2xl); display: flex; align-items: center; gap: var(--space-sm); box-shadow: var(--shadow-panel); z-index: 10000; transition: transform var(--duration-slow) cubic-bezier(0.175, 0.885, 0.32, 1.275), opacity var(--duration-slow) var(--ease-standard); pointer-events: none; opacity: 0; }
.cyber-toast.toast-visible { transform: translateX(-50%) translateY(0); opacity: 1; }
.toast-icon { font-size: 18px; }
.toast-text { color: var(--accent); font-size: 14px; letter-spacing: 0.5px; }

.custom-modal-overlay { position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background: var(--bg-overlay); backdrop-filter: blur(5px); display: flex; justify-content: center; align-items: center; z-index: 9999; animation: fadeIn var(--duration-base) ease-out; }
.custom-modal { background: var(--bg-panel); border: 1px solid var(--border-strong); border-top: 2px solid var(--danger); padding: var(--space-3xl); border-radius: var(--radius-md); width: 400px; text-align: center; box-shadow: var(--shadow-popover); animation: slideUp var(--duration-slow) cubic-bezier(0.175, 0.885, 0.32, 1.275); }
.modal-icon { font-size: 32px; margin-bottom: var(--space-lg); }
.modal-title { color: var(--text-primary); font-size: 18px; margin-bottom: var(--space-sm); font-weight: normal; letter-spacing: 1px; }
.modal-desc { color: var(--text-muted); font-size: 13px; line-height: 1.6; margin-bottom: var(--space-2xl); }
.highlight-text { color: var(--accent); }
.warning-text { color: var(--danger); font-size: 12px; display: block; margin-top: var(--space-sm); }
.modal-actions { display: flex; gap: var(--space-lg); justify-content: center; }
.modal-actions button { padding: var(--space-sm) var(--space-2xl); border: 1px solid transparent; border-radius: var(--radius-xs); font-family: var(--font-mono); font-size: 13px; cursor: pointer; transition: background var(--duration-base) var(--ease-standard), color var(--duration-base) var(--ease-standard), border-color var(--duration-base) var(--ease-standard), box-shadow var(--duration-base) var(--ease-standard); }
.btn-cancel { background: var(--bg-hover); color: var(--text-secondary); border-color: var(--border-strong); }
.btn-cancel:hover { background: var(--bg-hover-strong); color: var(--text-primary); }
.btn-confirm { background: var(--bg-danger-soft); color: var(--danger); border-color: var(--danger-border); }
.btn-confirm:hover { background: var(--danger); color: var(--text-inverse); box-shadow: var(--shadow-danger-soft); }
.permission-modal { width: 520px; text-align: left; }
.permission-item { border-top: 1px solid var(--border-subtle); padding-top: var(--space-md); margin-top: var(--space-md); }
.permission-item:first-of-type { border-top: none; padding-top: 0; margin-top: 0; }
.permission-preview { max-height: 160px; overflow: auto; background: var(--bg-hover); border: 1px solid var(--border-strong); padding: var(--space-md); color: var(--text-secondary); white-space: pre-wrap; font-size: 12px; border-radius: var(--radius-xs); }

/* 滑动动画 */
.slide-up-enter-active, .slide-up-leave-active { transition: all var(--duration-slow) ease; }
.slide-up-enter-from, .slide-up-leave-to { transform: translateY(100%); opacity: 0; }

@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
@keyframes slideUp { from { transform: translateY(20px) scale(0.95); opacity: 0; } to { transform: translateY(0) scale(1); opacity: 1; } }
</style>
