<script setup>
import { ref, onMounted, onUnmounted, defineAsyncComponent } from 'vue';
import { getCurrentWindow } from '@tauri-apps/api/window';
import { register, unregister } from '@tauri-apps/plugin-global-shortcut';
import { activeView, pendingCount, userInput, systemToast, inputError, deleteModal, pluginPermissionRequest, currentNote, useNeuroLink } from './composables/useNeuroLink';
import { activeAgentComponent, isImmersive } from './composables/useNeuroLink';
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
          <div class="nav-item" :class="{active: activeView==='vpm_center'}" @click="switchView('vpm_center')">
            <span class="icon">📦</span><span class="label">插件中心</span>
          </div>
          <div class="nav-item" :class="{active: activeView==='temp_chat'}" @click="startTempSession">
            <span class="icon">⏱</span><span class="label">临时会话</span>
          </div>
        </div>
      </aside>

      <main class="center-viewport" :class="{ 'squeezed': activeAgentComponent && isImmersive }">
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

        <div class="fixed-console" :class="{ 'error-shake': inputError }">
          <div class="context-pill" v-if="activeView==='note_detail'">📍 讨论中: {{ currentNote.title }}</div>
          <span class="prompt-icon">❯</span>
          <input v-model="userInput" @keyup.enter="sendChatCommand" placeholder="下达指令..." autofocus />
        </div>
      </main>

      <aside class="dynamic-sidebar" :class="{ 'sidebar-open': activeAgentComponent !== null, 'sidebar-immersive': isImmersive }">
        <div class="sidebar-content" v-if="activeAgentComponent">
          <component 
            :is="activeAgentComponent" 
            :is-immersive="isImmersive" 
          />
        </div>
      </aside>

    </div> <div class="custom-modal-overlay" v-if="deleteModal.show" @click="cancelDelete">
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
.fold-btn { background: none; border: none; color: var(--text-primary); font-size: 20px; cursor: pointer; margin-right: var(--space-lg); border-radius: var(--radius-xs); }
.os-name { font-size: 12px; color: var(--text-disabled); letter-spacing: 2px; }
.status-badge { font-size: 10px; color: var(--accent); font-weight: bold; }

.workspace-body { display: flex; flex: 1; overflow: hidden; }
.sidebar { width: 200px; background: var(--bg-shell); border-right: 1px solid var(--border-muted); transition: width var(--duration-slow) var(--ease-standard); overflow: hidden; display: flex; flex-direction: column; white-space: nowrap; }
.sidebar.collapsed { width: 60px; }
.sidebar.collapsed .label { opacity: 0; pointer-events: none; }
.side-right { border-right: none; border-left: 1px solid var(--border-muted); }
.nav-group { padding: var(--space-lg) 0; }
.nav-item { padding: var(--space-md) var(--space-xl); cursor: pointer; display: flex; align-items: center; gap: var(--space-lg); color: var(--text-muted); transition: background var(--duration-base) var(--ease-standard), color var(--duration-base) var(--ease-standard), border-color var(--duration-base) var(--ease-standard); border-left: 2px solid transparent; box-sizing: border-box; }
.nav-item:hover, .nav-item.active { background: var(--bg-selected); color: var(--accent-strong); border-left-color: var(--accent); }
.nav-item .icon { width: 20px; flex: 0 0 20px; text-align: center; font-size: 18px; line-height: 1; }
.badge { background: var(--danger); color: var(--text-primary); font-size: 11px; font-weight: bold; padding: 2px 6px; border-radius: var(--radius-pill); margin-left: auto; }
.pulse-anim { animation: pulse-glow 1.5s infinite; }

.center-viewport { 
  flex: 1; 
  display: flex; 
  flex-direction: column; 
  background: var(--bg-shell); 
  min-width: 400px; 
  overflow: hidden;
  transition: opacity var(--duration-slow) var(--ease-standard), transform var(--duration-slow) var(--ease-standard); 
}
/* 沉浸态下的主视图被挤压变暗 */
.center-viewport.squeezed {
  opacity: 0.3;
  transform: scale(0.98); 
  pointer-events: none; /* 沉浸时防止误触主界面的按钮 */
}
.dynamic-sidebar {
  width: 0; /* 默认隐藏 */
  background: var(--bg-app);
  border-left: 1px solid var(--border-muted);
  transition: width var(--duration-slow) var(--ease-standard);
  display: flex;
  flex-direction: column;
  overflow: hidden; /* 收缩时切断内部溢出 */
  z-index: 50;
}
/* 形态 1：侧边栏唤醒（静默陪伴模式） */
.dynamic-sidebar.sidebar-open {
  width: 65px; 
}
/* 形态 2：沉浸覆盖模式（掌控模式） */
.dynamic-sidebar.sidebar-immersive {
  width: 70vw; /* 占据屏幕 70% 的宽度 */
  box-shadow: var(--shadow-popover);
  z-index: 100;
}
.sidebar-content {
  width: 100%;
  height: 100%;
  min-width: 65px; /* 保证内部组件在缩放时不会变形乱折行 */
}
.view-content { flex: 1; overflow: hidden; display: flex; flex-direction: column;}

.fixed-console { height: 65px; min-height: 65px; background: var(--bg-console); border-top: 1px solid var(--border-subtle); display: flex; align-items: center; padding: 0 var(--space-2xl); gap: var(--space-lg); position: relative; }
.context-pill { position: absolute; top: -25px; left: var(--space-2xl); background: var(--accent); color: var(--text-inverse); font-size: 10px; font-weight: bold; padding: var(--space-2xs) var(--space-sm); border-radius: var(--radius-xs); }
.prompt-icon { color: var(--accent); font-weight: bold; }
.fixed-console input { flex: 1; background: transparent; border: none; color: var(--text-primary); font-size: 15px; font-family: var(--font-mono); }

.error-shake { animation: shake 0.4s; background: var(--bg-danger-soft) !important; }
@keyframes shake { 0%,100%{transform:translateX(0)} 25%{transform:translateX(-5px)} 75%{transform:translateX(5px)} }
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
