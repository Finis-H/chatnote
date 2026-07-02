<template>
  <aside
    class="agent-dock"
    :class="[`mode-${dockMode}`, `state-${dockStatus}`, { 'is-open': hasPanel, 'is-dragging': isDragging }]"
    :style="dockStyle"
    aria-label="AgentDock"
  >
    <div
      v-if="hasPanel && dockMode !== 'mini'"
      class="dock-resizer"
      role="separator"
      aria-orientation="vertical"
      title="拖拽调整 AgentDock 宽度"
      @pointerdown="startResize"
    ></div>

    <div v-if="hasPanel && dockMode === 'mini'" class="mini-stack" aria-label="已最小化的 Agent">
      <button
        v-for="item in dockItems"
        :key="item.key"
        type="button"
        class="mini-rail"
        :title="`展开 ${titleFor(item)}`"
        :aria-label="`展开 ${titleFor(item)}`"
        @click="restoreDock(item.key)"
      >
        <span class="mini-icon">{{ iconFor(item) }}</span>
        <span class="mini-status" :class="`state-${statusFor(item)}`" aria-hidden="true"></span>
        <span v-if="item.unreadCount > 0" class="mini-count">{{ item.unreadCount }}</span>
      </button>
    </div>

    <div v-if="hasPanel" class="dock-shell" v-show="dockMode !== 'mini'">
      <header class="dock-header">
        <div class="dock-identity">
          <span class="plugin-mark">{{ activeIcon }}</span>
          <div class="title-stack">
            <div class="dock-title">{{ dockTitle }}</div>
            <div class="dock-source">{{ dockSource }}</div>
          </div>
        </div>

        <div class="dock-actions">
          <div class="dock-meta" :title="statusMeta.detail">
            <span class="state-dot" aria-hidden="true"></span>
            <span>{{ statusMeta.label }}</span>
            <span class="trust-pill">{{ trustLabel }}</span>
          </div>
          <button type="button" class="icon-button" title="最小化到右侧" aria-label="最小化到右侧" @click="setDockMode('mini')">
            <Minus aria-hidden="true" />
          </button>
          <button
            type="button"
            class="icon-button"
            :title="dockMode === 'focus' ? '恢复停靠宽度' : '聚焦面板'"
            :aria-label="dockMode === 'focus' ? '恢复停靠宽度' : '聚焦面板'"
            @click="toggleFocus"
          >
            <component :is="dockMode === 'focus' ? Fold : FullScreen" aria-hidden="true" />
          </button>
          <button type="button" class="icon-button close-button" title="关闭全部 Agent 面板" aria-label="关闭全部 Agent 面板" @click="closeAll">
            <Close aria-hidden="true" />
          </button>
        </div>
      </header>

      <section v-if="musicSummary" class="music-strip" aria-label="音乐任务状态">
        <div class="music-task">
          <span class="strip-label">任务</span>
          <strong>{{ musicSummary.taskName }}</strong>
        </div>
        <div class="music-now">
          <span class="strip-label">当前</span>
          <span>{{ musicSummary.currentSong }}</span>
        </div>
        <div class="music-state">
          <span class="strip-label">播放</span>
          <span>{{ musicSummary.playbackState }}</span>
        </div>
        <div class="music-controls">
          <button type="button" :class="{ active: musicView === 'player' }" :aria-pressed="musicView === 'player'" @click="setMusicView('player')">播放控制</button>
          <button type="button" :class="{ active: musicView === 'lyrics' }" :aria-pressed="musicView === 'lyrics'" @click="setMusicView('lyrics')">歌词</button>
        </div>
      </section>

      <main class="dock-list" aria-label="Agent 面板列表">
        <section
          v-for="item in dockItems"
          :key="item.key"
          class="dock-item"
          :class="{ collapsed: item.collapsed, active: item.key === activeKey }"
        >
          <header class="item-header">
            <button type="button" class="item-main" :aria-expanded="!item.collapsed" @click="toggleItem(item.key)">
              <span class="item-icon">{{ iconFor(item) }}</span>
              <span class="item-copy">
                <strong>{{ titleFor(item) }}</strong>
                <small>{{ sourceFor(item) }}</small>
              </span>
              <span class="item-status" :class="`state-${statusFor(item)}`" :title="statusLabelFor(item)"></span>
            </button>
            <div class="item-actions">
              <button type="button" class="icon-button compact" :title="item.collapsed ? '展开此 Agent' : '折叠此 Agent'" :aria-label="item.collapsed ? '展开此 Agent' : '折叠此 Agent'" @click="toggleItem(item.key)">
                <component :is="item.collapsed ? ArrowLeft : ArrowRight" aria-hidden="true" />
              </button>
              <button type="button" class="icon-button compact close-button" title="关闭此 Agent" aria-label="关闭此 Agent" @click="closeItem(item.key)">
                <Close aria-hidden="true" />
              </button>
            </div>
          </header>

          <div class="dock-content" :class="contentClassFor(item)" v-show="!item.collapsed">
            <component
              :is="item.component"
              :is-immersive="contentIsImmersive"
            />
          </div>
        </section>
      </main>
    </div>
  </aside>
</template>

<script setup>
import { computed, onBeforeUnmount, onErrorCaptured, ref, watch } from 'vue';
import { ArrowLeft, ArrowRight, Close, Fold, FullScreen, Minus } from '@element-plus/icons-vue';
import {
  activeAgentComponent,
  activeAgentDock,
  activeAgentDockItems,
  isImmersive,
  pluginPermissionRequest,
  pluginsList
} from '../composables/useNeuroLink';

const MIN_DOCK_WIDTH = 340;
const MAX_DOCK_WIDTH = 680;
const MINI_WIDTH = 64;
const DEFAULT_DOCK_WIDTH = 420;

const isDragging = ref(false);
const musicView = ref('player');
const hasPanel = computed(() => dockItems.value.length > 0);
const dockMode = computed(() => hasPanel.value ? activeAgentDock.value.mode : 'closed');
const activeKey = computed(() => activeAgentDock.value.activeKey || dockItems.value[0]?.key || '');
const contentIsImmersive = computed(() => dockMode.value !== 'mini');

const dockItems = computed(() => {
  if (activeAgentDockItems.value.length > 0) return activeAgentDockItems.value;
  if (!activeAgentComponent.value || !activeAgentDock.value.pluginId) return [];
  return [{
    key: activeAgentDock.value.activeKey || `${activeAgentDock.value.pluginId}:${activeAgentDock.value.componentName}`,
    pluginId: activeAgentDock.value.pluginId,
    componentName: activeAgentDock.value.componentName,
    component: activeAgentComponent.value,
    status: activeAgentDock.value.status,
    unreadCount: activeAgentDock.value.unreadCount,
    collapsed: false,
    lastPayload: activeAgentDock.value.lastPayload,
    openedAt: activeAgentDock.value.openedAt,
    updatedAt: activeAgentDock.value.updatedAt
  }];
});

const activeItem = computed(() => {
  return dockItems.value.find(item => item.key === activeKey.value) || dockItems.value[0] || null;
});

const dockWidth = computed(() => {
  const raw = Number(activeAgentDock.value.width || DEFAULT_DOCK_WIDTH);
  return Math.max(MIN_DOCK_WIDTH, Math.min(MAX_DOCK_WIDTH, raw));
});

const dockStyle = computed(() => {
  if (!hasPanel.value) return {};
  if (dockMode.value === 'mini') return { '--dock-width': `${MINI_WIDTH}px` };
  if (dockMode.value === 'focus') return { '--dock-width': `clamp(420px, 46vw, ${MAX_DOCK_WIDTH}px)` };
  return { '--dock-width': `${dockWidth.value}px` };
});

const pluginInfo = computed(() => pluginInfoFor(activeItem.value));
const dockTitle = computed(() => activeItem.value ? titleFor(activeItem.value) : 'AgentDock');
const dockSource = computed(() => activeItem.value ? sourceFor(activeItem.value) : 'agent / Vault Plugin');
const trustLabel = computed(() => trustFor(pluginInfo.value));
const activeIcon = computed(() => activeItem.value ? iconFor(activeItem.value) : 'A');

const dockStatus = computed(() => {
  if (permissionRequestMatches(activeItem.value)) return 'need_permission';
  return activeItem.value?.status || activeAgentDock.value.status || 'idle';
});

const statusMeta = computed(() => statusMetaFor(dockStatus.value));

const musicSummary = computed(() => {
  const musicItem = dockItems.value.find(item => item.pluginId === 'music_agent');
  if (!musicItem) return null;
  const playlist = musicItem.lastPayload?.playlist || [];
  const current = playlist[0] || {};
  return {
    taskName: playlist.length > 0 ? `临时歌单 ${playlist.length} 首` : '音乐 Agent 待命',
    currentSong: current.title ? `${current.title}${current.artist ? ` / ${current.artist}` : ''}` : '等待歌曲',
    playbackState: statusMetaFor(statusFor(musicItem)).label
  };
});

function pluginInfoFor(item) {
  if (!item) return {};
  return (pluginsList.value || []).find(entry => entry.plugin_id === item.pluginId) || {};
}

function titleFor(item) {
  const info = pluginInfoFor(item);
  return info.name || item?.componentName || item?.pluginId || 'Agent';
}

function sourceFor(item) {
  const info = pluginInfoFor(item);
  return `${item?.pluginId || 'agent'} / ${info.author || 'Vault Plugin'}`;
}

function trustFor(info) {
  const trust = info?.security?.trust || 'third_party';
  return trust === 'first_party' ? 'first-party' : 'third-party';
}

function iconFor(item) {
  if (item?.pluginId === 'music_agent') return 'M';
  return (titleFor(item) || 'A').slice(0, 1).toUpperCase();
}

function permissionRequestMatches(item) {
  const request = pluginPermissionRequest.value;
  if (!request || !item?.pluginId) return false;
  const items = request.items || [request];
  return items.some(entry => entry.plugin_id === item.pluginId || entry.plugin_name === titleFor(item));
}

function statusFor(item) {
  if (permissionRequestMatches(item)) return 'need_permission';
  return item?.status || 'idle';
}

function statusMetaFor(status) {
  const labels = {
    idle: ['空闲', 'AgentDock 空闲'],
    running: ['执行中', '插件正在处理任务'],
    success: ['已就绪', '最近一次插件任务已完成'],
    error: ['异常', '插件面板加载或运行异常'],
    need_permission: ['待授权', '插件请求敏感权限确认']
  };
  const [label, detail] = labels[status] || labels.idle;
  return { label, detail };
}

function statusLabelFor(item) {
  return statusMetaFor(statusFor(item)).label;
}

function setMusicView(view) {
  musicView.value = view;
}

function contentClassFor(item) {
  if (item?.pluginId !== 'music_agent') return '';
  return `music-view-${musicView.value}`;
}

function updateDock(patch) {
  activeAgentDock.value = {
    ...activeAgentDock.value,
    ...patch,
    updatedAt: Date.now()
  };
}

function updateItems(updater) {
  activeAgentDockItems.value = updater(activeAgentDockItems.value).map(item => ({ ...item }));
}

function syncActiveComponent(nextKey = activeKey.value) {
  const next = activeAgentDockItems.value.find(item => item.key === nextKey) || activeAgentDockItems.value[0] || null;
  activeAgentComponent.value = next?.component || null;
  updateDock({
    activeKey: next?.key || '',
    pluginId: next?.pluginId || '',
    componentName: next?.componentName || '',
    status: next?.status || 'idle',
    unreadCount: next?.unreadCount || 0,
    lastPayload: next?.lastPayload || null
  });
}

function setDockMode(mode) {
  updateDock({
    mode,
    lastExpandedMode: mode === 'mini' ? activeAgentDock.value.lastExpandedMode : mode,
    unreadCount: mode === 'mini' ? activeAgentDock.value.unreadCount : 0
  });
  isImmersive.value = mode !== 'mini';
}

function restoreDock(key) {
  updateItems(items => items.map(item => (
    item.key === key ? { ...item, collapsed: false, unreadCount: 0 } : item
  )));
  syncActiveComponent(key);
  setDockMode(activeAgentDock.value.lastExpandedMode || 'dock');
}

function toggleFocus() {
  setDockMode(dockMode.value === 'focus' ? 'dock' : 'focus');
}

function toggleItem(key) {
  updateItems(items => items.map(item => (
    item.key === key ? { ...item, collapsed: !item.collapsed, unreadCount: 0 } : item
  )));
  syncActiveComponent(key);
}

function closeItem(key) {
  updateItems(items => items.filter(item => item.key !== key));
  if (activeAgentDockItems.value.length === 0) {
    closeAll();
    return;
  }
  syncActiveComponent(activeKey.value === key ? activeAgentDockItems.value[0].key : activeKey.value);
}

function closeAll() {
  activeAgentComponent.value = null;
  isImmersive.value = false;
  activeAgentDockItems.value = [];
  activeAgentDock.value = {
    activeKey: '',
    pluginId: '',
    componentName: '',
    mode: 'mini',
    width: activeAgentDock.value.width || DEFAULT_DOCK_WIDTH,
    lastExpandedMode: 'dock',
    status: 'idle',
    unreadCount: 0,
    lastPayload: null,
    openedAt: null,
    updatedAt: Date.now()
  };
}

function startResize(event) {
  if (dockMode.value === 'mini') return;
  isDragging.value = true;
  event.currentTarget.setPointerCapture?.(event.pointerId);
  window.addEventListener('pointermove', resizeDock);
  window.addEventListener('pointerup', stopResize, { once: true });
}

function resizeDock(event) {
  if (!isDragging.value) return;
  const width = Math.max(MIN_DOCK_WIDTH, Math.min(MAX_DOCK_WIDTH, window.innerWidth - event.clientX));
  updateDock({ width, mode: dockMode.value === 'focus' ? 'focus' : 'dock' });
}

function stopResize() {
  isDragging.value = false;
  window.removeEventListener('pointermove', resizeDock);
}

watch(isImmersive, value => {
  if (!hasPanel.value) return;
  if (!value && dockMode.value !== 'mini') setDockMode('mini');
}, { flush: 'post' });

onBeforeUnmount(() => {
  window.removeEventListener('pointermove', resizeDock);
});

onErrorCaptured(error => {
  console.error('[AgentDock] 插件内容渲染失败:', error);
  updateDock({ status: 'error' });
  updateItems(items => items.map(item => (
    item.key === activeKey.value ? { ...item, status: 'error' } : item
  )));
  return false;
});
</script>

<style scoped>
.agent-dock {
  --dock-width: 0px;
  width: 0;
  flex: 0 0 0;
  height: 100%;
  position: relative;
  background: var(--bg-app);
  border-left: 1px solid transparent;
  overflow: hidden;
  transition: width var(--duration-slow) var(--ease-standard), flex-basis var(--duration-slow) var(--ease-standard), border-color var(--duration-slow) var(--ease-standard), box-shadow var(--duration-slow) var(--ease-standard);
  z-index: 60;
}

.agent-dock.is-open {
  width: var(--dock-width);
  flex-basis: var(--dock-width);
  border-left-color: var(--border-muted);
}

.agent-dock.mode-focus {
  box-shadow: var(--shadow-popover);
  z-index: 100;
}

.agent-dock.is-dragging {
  transition: none;
}

.dock-resizer {
  position: absolute;
  top: 0;
  left: 0;
  width: 8px;
  height: 100%;
  cursor: col-resize;
  z-index: 5;
}

.dock-resizer::after {
  content: '';
  position: absolute;
  top: 0;
  left: 3px;
  width: 1px;
  height: 100%;
  background: transparent;
  transition: background var(--duration-base) var(--ease-standard);
}

.dock-resizer:hover::after,
.is-dragging .dock-resizer::after {
  background: var(--accent-border);
}

.mini-stack {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-sm);
  padding: var(--space-md) 0;
  background: var(--bg-console);
  overflow-y: auto;
}

.mini-rail {
  width: 48px;
  min-height: 58px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-xs);
  background: transparent;
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  cursor: pointer;
}

.mini-rail:hover {
  border-color: var(--border-strong);
  background: var(--bg-hover);
}

.mini-icon,
.plugin-mark,
.item-icon {
  width: 34px;
  height: 34px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--accent-border);
  border-radius: var(--radius-sm);
  background: var(--accent-soft);
  color: var(--accent-strong);
  font-weight: 700;
}

.mini-status,
.state-dot,
.item-status {
  width: 8px;
  height: 8px;
  flex: 0 0 8px;
  border-radius: 50%;
  background: var(--text-disabled);
}

.mini-count {
  min-width: 20px;
  height: 18px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0 var(--space-xs);
  border-radius: var(--radius-pill);
  background: var(--danger);
  color: var(--text-primary);
  font-size: 11px;
  font-weight: 700;
}

.dock-shell {
  height: 100%;
  min-width: 0;
  display: flex;
  flex-direction: column;
  background: var(--bg-shell);
}

.dock-header {
  min-height: 58px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-md);
  padding: var(--space-sm) var(--space-md) var(--space-sm) var(--space-lg);
  border-bottom: 1px solid var(--border-subtle);
  background: var(--bg-console);
  overflow: hidden;
}

.dock-identity {
  flex: 1 1 auto;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  overflow: hidden;
}

.title-stack {
  flex: 1 1 auto;
  min-width: 0;
}

.dock-title {
  color: var(--text-primary);
  font-size: 13px;
  font-weight: 700;
  line-height: 1.3;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.dock-source {
  color: var(--text-disabled);
  font-size: 10px;
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.dock-actions {
  flex: 0 0 auto;
  margin-left: auto;
  display: inline-flex;
  align-items: center;
  gap: var(--space-xs);
  position: relative;
  z-index: 2;
}

.dock-meta {
  max-width: 118px;
  display: none;
  align-items: center;
  gap: var(--space-xs);
  color: var(--text-muted);
  font-size: 11px;
  white-space: nowrap;
}

.trust-pill {
  height: 20px;
  display: inline-flex;
  align-items: center;
  padding: 0 var(--space-xs);
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-xs);
  color: var(--text-disabled);
}

.icon-button {
  width: 28px;
  height: 28px;
  flex: 0 0 28px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid transparent;
  border-radius: var(--radius-xs);
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  transition: background var(--duration-base) var(--ease-standard), border-color var(--duration-base) var(--ease-standard), color var(--duration-base) var(--ease-standard);
}

.mode-focus .dock-meta {
  display: inline-flex;
}

.icon-button.compact {
  width: 26px;
  height: 26px;
  flex-basis: 26px;
}

.icon-button:hover {
  border-color: var(--border-strong);
  background: var(--bg-hover);
  color: var(--accent-strong);
}

.close-button:hover {
  color: var(--danger);
  border-color: var(--danger-border);
}

.icon-button svg {
  width: 15px;
  height: 15px;
}

.music-strip {
  display: grid;
  grid-template-columns: minmax(92px, auto) minmax(0, 1fr) minmax(64px, auto) auto;
  gap: var(--space-md);
  align-items: center;
  padding: var(--space-sm) var(--space-md) var(--space-sm) var(--space-lg);
  border-bottom: 1px solid var(--border-muted);
  background: var(--bg-panel);
}

.music-task,
.music-now,
.music-state {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-2xs);
  color: var(--text-secondary);
  font-size: 12px;
}

.music-task strong,
.music-now span:last-child,
.music-state span:last-child {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.strip-label {
  color: var(--text-disabled);
  font-size: 10px;
}

.music-controls {
  display: inline-flex;
  align-items: center;
  gap: var(--space-xs);
}

.music-controls button {
  height: 26px;
  padding: 0 var(--space-sm);
  border: 1px solid var(--accent-border);
  border-radius: var(--radius-xs);
  background: var(--accent-soft);
  color: var(--accent-strong);
  font: inherit;
  font-size: 11px;
  cursor: pointer;
}

.music-controls button.active {
  background: var(--accent);
  color: var(--text-inverse);
  border-color: var(--accent);
}

.dock-list {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
  padding: var(--space-sm);
}

.dock-item {
  min-height: 0;
  display: flex;
  flex-direction: column;
  border: 1px solid var(--border-muted);
  border-radius: var(--radius-md);
  background: var(--bg-panel);
  overflow: hidden;
}

.dock-item.active {
  border-color: var(--border-strong);
}

.dock-item.collapsed {
  flex: 0 0 auto;
}

.item-header {
  min-height: 44px;
  display: flex;
  align-items: center;
  gap: var(--space-xs);
  padding: var(--space-xs);
  border-bottom: 1px solid var(--border-muted);
  background: var(--bg-console);
}

.dock-item.collapsed .item-header {
  border-bottom: 0;
}

.item-main {
  min-width: 0;
  flex: 1;
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  border: 0;
  background: transparent;
  color: var(--text-secondary);
  font: inherit;
  text-align: left;
  cursor: pointer;
}

.item-copy {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-2xs);
}

.item-copy strong,
.item-copy small {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.item-copy strong {
  color: var(--text-primary);
  font-size: 12px;
}

.item-copy small {
  color: var(--text-disabled);
  font-size: 10px;
}

.item-actions {
  flex: 0 0 auto;
  display: inline-flex;
  align-items: center;
  gap: var(--space-xs);
}

.dock-content {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.state-idle .state-dot,
.mini-status.state-idle,
.item-status.state-idle {
  background: var(--text-disabled);
}

.state-running .state-dot,
.mini-status.state-running,
.item-status.state-running {
  background: var(--accent);
  animation: dock-pulse 1.2s infinite;
}

.state-success .state-dot,
.mini-status.state-success,
.item-status.state-success {
  background: var(--success);
}

.state-error .state-dot,
.mini-status.state-error,
.item-status.state-error {
  background: var(--danger);
}

.state-need_permission .state-dot,
.mini-status.state-need_permission,
.item-status.state-need_permission {
  background: var(--warning);
  animation: dock-pulse 1.2s infinite;
}

.state-error .dock-meta {
  color: var(--danger-strong);
}

.state-need_permission .dock-meta {
  color: var(--warning-strong);
}

.agent-dock :deep(.music-panel.immersive) {
  height: 100%;
  max-height: 100%;
  max-width: 100%;
  min-height: 0;
  padding: var(--space-lg);
  overflow-x: hidden;
  overflow-y: auto;
}

.agent-dock :deep(.immersive-mode-container) {
  width: 100%;
  max-width: 100%;
  height: auto;
  min-height: 0;
  display: flex !important;
  flex-direction: column;
  align-items: stretch;
  gap: var(--space-lg);
  padding-top: 0;
  overflow: visible;
}

.agent-dock :deep(.os-window-controls) {
  display: none;
}

.agent-dock :deep(.panel-body.player-only) {
  width: 100%;
  height: auto;
  min-height: 0;
  flex: 0 0 auto;
  justify-content: flex-start;
}

.agent-dock :deep(.album-art-wrapper) {
  margin-top: 0;
  margin-bottom: var(--space-sm);
}

.agent-dock :deep(.album-art) {
  width: clamp(104px, 18vw, 168px);
  height: clamp(104px, 18vw, 168px);
}

.agent-dock :deep(.track-info) {
  margin-bottom: var(--space-sm);
}

.agent-dock :deep(.controls-wrapper) {
  flex: 0 0 auto;
  gap: var(--space-sm);
  margin-bottom: var(--space-sm);
}

.agent-dock :deep(.controls) {
  gap: var(--space-md);
}

.agent-dock :deep(.play-btn) {
  width: 56px;
  height: 56px;
  flex: 0 0 56px;
}

.agent-dock :deep(.progress-container) {
  flex: 0 0 auto;
  width: 100%;
  margin-top: 0;
  padding-bottom: 0;
}

.agent-dock :deep(.lyrics-area) {
  width: 100%;
  height: auto;
  min-height: 120px;
  max-height: 280px;
  flex: 0 0 auto;
  overflow: hidden;
}

.agent-dock :deep(.lyric-scroll-container) {
  max-height: 210px;
  min-height: 0;
}

.agent-dock :deep(.pure-lyrics) {
  font-size: 0.96rem;
  line-height: 1.65;
}

.music-view-player :deep(.lyrics-area) {
  display: none;
}

.music-view-lyrics :deep(.album-art-wrapper),
.music-view-lyrics :deep(.controls-wrapper),
.music-view-lyrics :deep(.volume-control) {
  display: none;
}

.music-view-lyrics :deep(.panel-body.player-only) {
  padding-bottom: var(--space-sm);
}

.music-view-lyrics :deep(.progress-container) {
  margin-top: var(--space-xs);
}

.music-view-lyrics :deep(.lyrics-area) {
  display: flex;
  min-height: 240px;
  max-height: none;
}

.music-view-lyrics :deep(.lyric-scroll-container) {
  max-height: 320px;
}

.agent-dock.mode-focus :deep(.dock-content) {
  min-height: 0;
}

.agent-dock.mode-focus :deep(.music-panel.immersive) {
  padding: var(--space-xl);
}

.agent-dock.mode-focus :deep(.lyrics-area) {
  max-height: 340px;
}

@media (max-width: 1100px) {
  .dock-meta {
    display: none;
  }

  .music-strip {
    grid-template-columns: minmax(0, 1fr);
  }

  .music-controls {
    justify-content: flex-start;
  }
}

@media (max-width: 760px) {
  .agent-dock.mode-dock,
  .agent-dock.mode-focus {
    --dock-width: min(460px, 62vw) !important;
  }

  .dock-header {
    padding-left: var(--space-md);
  }

  .plugin-mark {
    width: 30px;
    height: 30px;
  }
}

@keyframes dock-pulse {
  0%, 100% { opacity: 0.45; }
  50% { opacity: 1; }
}
</style>
