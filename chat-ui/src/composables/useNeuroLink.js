import { ref, computed, shallowRef } from 'vue';
import { invoke } from '@tauri-apps/api/core';
// 🚀 引入注册器，并且彻底删除了原来造成死循环的 import * as selfContext
import { loadVpmComponent, registerVpmContext } from '../utils/vpmLoader';

export const SystemConfig = {
    SERVER_PORT: 8000,
    API_BASE: "http://127.0.0.1:8000",
    WS_BASE: "ws://127.0.0.1:8000",
    TOKEN: ""
};

export async function initSystemEnv() {
    try {
        SystemConfig.TOKEN = await invoke('get_run_token');
        const port = await invoke('get_server_port');
        SystemConfig.SERVER_PORT = port;
        SystemConfig.API_BASE = `http://127.0.0.1:${port}`;
        SystemConfig.WS_BASE = `ws://127.0.0.1:${port}`;
        console.log("🟢 [系统环境寻址完成]:", {
          API_BASE: SystemConfig.API_BASE,
          WS_BASE: SystemConfig.WS_BASE
        });
    } catch (error) {
        console.error("🔴 [环境寻址失败，使用备用降级模式]:", error);
    }
}

// === 全局单例状态 (State) ===
export const activeView = ref('chat');
export const previousView = ref('news');
export const sysConfig = ref({ api_key: '', base_url: '', model_max: '', model_mini: '', embed_api_key: '', embed_base_url: '', embed_model: 'text-embedding-v4' });
export const newsList = ref([]);
export const favoritesList = ref([]);
export const pluginsList = ref([]);
export const globalMessages = ref([]);
export const tempMessages = ref([]);
export const noteThreads = ref({});
export const currentNote = ref({ id: null, title: '', content: '', file_path: '' });
export const pendingMemory = ref([]);
export const mainIsThinking = ref(false);
export const tempIsThinking = ref(false);
export const tempSessionId = ref('');
export const isTempSession = computed(() => activeView.value === 'temp_chat');
export const isThinking = computed({
  get: () => isTempSession.value ? tempIsThinking.value : mainIsThinking.value,
  set: value => {
    if (isTempSession.value) tempIsThinking.value = value;
    else mainIsThinking.value = value;
  }
});
export const userInput = ref('');
export const systemToast = ref({ show: false, message: '' });
export const inputError = ref(false);
export const isImmersive = ref(false);
export const activeAgentComponent = shallowRef(null);
export const deleteModal = ref({ show: false, note: null });
export const pluginPermissionRequest = ref(null);
export const isImporting = ref(false);
export const importFile = ref(null);
export const PROFILE_IMPORT_MAX_CHARS = 9000;
export const profileImportSessionId = ref('');
export const profileImportPreview = ref('');
export const profileImportStage = ref('idle');
export const profileImportLockReason = ref('');
export const profileImportPendingIds = ref([]);
export const profileImportOriginalLength = ref(0);
export const profileImportNormalizedLength = ref(0);
export const mainTraceEvents = ref([]);
export const tempTraceEvents = ref([]);
export const mainActiveTraceId = ref('');
export const tempActiveTraceId = ref('');
export const traceEvents = computed({
  get: () => isTempSession.value ? tempTraceEvents.value : mainTraceEvents.value,
  set: value => {
    if (isTempSession.value) tempTraceEvents.value = value;
    else mainTraceEvents.value = value;
  }
});
export const activeTraceId = computed({
  get: () => isTempSession.value ? tempActiveTraceId.value : mainActiveTraceId.value,
  set: value => {
    if (isTempSession.value) tempActiveTraceId.value = value;
    else mainActiveTraceId.value = value;
  }
});
export const isTracePanelOpen = ref(false);

export const searchQuery = ref('');
export const searchMode = ref('all');
export const memoryFilter = ref('all');

export const pendingCount = computed(() => pendingMemory.value.filter(m => m.status === 'PENDING').length);
export const profileImportPendingCount = computed(() => profileImportPendingIds.value.length);
export const traceSummary = computed(() => {
  const events = traceEvents.value || [];
  const runningCount = events.filter(event => event.status === 'RUNNING').length;
  const failedCount = events.filter(event => ['FAILED', 'TIMEOUT'].includes(event.status)).length;
  const degradedCount = events.filter(event => event.status === 'DEGRADED').length;
  const abortedCount = events.filter(event => event.status === 'ABORTED').length;
  const hasSuccessfulResponse = events.some(event => event.step_code === 'RESPONSE_DONE' && event.status === 'SUCCESS');
  const hasRecoveredDegradation = hasSuccessfulResponse && degradedCount > 0 && failedCount === 0 && runningCount === 0;
  let status = 'IDLE';
  if (failedCount > 0) status = 'FAILED';
  else if (runningCount > 0) status = 'RUNNING';
  else if (degradedCount > 0 && !hasRecoveredDegradation) status = 'DEGRADED';
  else if (events.length > 0) status = 'SUCCESS';
  return {
    status,
    totalCount: events.length,
    runningCount,
    failedCount,
    degradedCount,
    abortedCount,
    hasRecoveredDegradation
  };
});

export function toggleTracePanel() {
  isTracePanelOpen.value = !isTracePanelOpen.value;
}

let ws = null;
let isAppDestroyed = false;
let toastTimeout = null;
let shakeTimeout = null;
let traceWatchdogTimer = null;
const TRACE_TERMINAL_STATUSES = ['SUCCESS', 'DEGRADED', 'FAILED', 'TIMEOUT', 'ABORTED', 'BLOCKED'];
const TRACE_QUEUE_LIMIT = 50;

export function resolveMemoryConflict(id, decision) {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: "resolve_memory_conflict", id, decision }));
  }
}

export function useNeuroLink() {

  function showToast(msg) {
    systemToast.value = { show: true, message: msg };
    if (toastTimeout) clearTimeout(toastTimeout);
    toastTimeout = setTimeout(() => { systemToast.value.show = false; }, 4000);
  }

  function triggerErrorShake() {
    inputError.value = true;
    if (shakeTimeout) clearTimeout(shakeTimeout);
    shakeTimeout = setTimeout(() => { inputError.value = false; }, 500);
  }

  function sendWsCommand(payload) {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(payload));
    }
  }

  function respondPluginPermission(decision) {
    const current = pluginPermissionRequest.value;
    if (!current) return;
    sendWsCommand({
      type: "plugin_permission_response",
      request_id: current.request_id,
      decision
    });
    pluginPermissionRequest.value = null;
  }

  function applyProfileImportState(state = {}) {
    profileImportSessionId.value = state.session_id || '';
    profileImportPreview.value = state.preview || '';
    profileImportStage.value = state.stage || 'idle';
    profileImportLockReason.value = state.lock_reason || '';
    profileImportPendingIds.value = state.pending_ids || [];
    profileImportOriginalLength.value = state.original_length || 0;
    profileImportNormalizedLength.value = state.normalized_length || 0;
    isImporting.value = ['preparing', 'committing'].includes(profileImportStage.value);
    if (profileImportStage.value === 'idle') importFile.value = null;
  }

  function clearTraceWatchdog() {
    if (traceWatchdogTimer) clearTimeout(traceWatchdogTimer);
    traceWatchdogTimer = null;
  }

  function traceStoreFor(sessionId = 'main') {
    return sessionId && sessionId === tempSessionId.value ? tempTraceEvents : mainTraceEvents;
  }

  function activeTraceRefFor(sessionId = 'main') {
    return sessionId && sessionId === tempSessionId.value ? tempActiveTraceId : mainActiveTraceId;
  }

  function trimTraceQueue(sessionId = 'main') {
    const store = traceStoreFor(sessionId);
    if (store.value.length > TRACE_QUEUE_LIMIT) {
      store.value = store.value.slice(-TRACE_QUEUE_LIMIT);
    }
  }

  function upsertTraceEvent(event) {
    if (!event || !event.span_id) return;
    const sessionId = event.session_id || 'main';
    const store = traceStoreFor(sessionId);
    const activeRef = activeTraceRefFor(sessionId);
    if (event.trace_id) activeRef.value = event.trace_id;
    const normalized = {
      ...event,
      timestamp: event.timestamp || Date.now(),
      collapsed: event.collapsed || event.step_code === 'MEMORY_FLOW',
      muted: event.status === 'ABORTED'
    };
    const index = store.value.findIndex(item => item.span_id === normalized.span_id);
    if (index >= 0) {
      const existing = store.value[index];
      if ((normalized.timestamp || 0) >= (existing.timestamp || 0)) {
        store.value.splice(index, 1, { ...existing, ...normalized });
      }
    } else {
      store.value.push(normalized);
    }
    trimTraceQueue(sessionId);
  }

  async function fetchTraceSnapshot(traceId, threadId) {
    const primaryUrl = traceId
      ? `${SystemConfig.API_BASE}/api/traces/${encodeURIComponent(traceId)}/snapshot`
      : `${SystemConfig.API_BASE}/api/traces/thread/${encodeURIComponent(threadId || 'global')}/latest`;
    const resp = await fetch(primaryUrl);
    if (!resp.ok) throw new Error(`Trace snapshot failed: ${resp.status}`);
    return await resp.json();
  }

  function applyTraceSnapshot(snapshot) {
    if (!snapshot || !snapshot.run) return;
    const sessionId = snapshot.run.session_id || 'main';
    const store = traceStoreFor(sessionId);
    const activeRef = activeTraceRefFor(sessionId);
    const runStatus = snapshot.run.status;
    activeRef.value = snapshot.run.trace_id || activeRef.value;

    (snapshot.events || []).forEach(event => upsertTraceEvent(event));

    if (runStatus === 'SUCCESS' || runStatus === 'DEGRADED') {
      const parentIdsToCollapse = new Set();
      store.value = store.value.map(event => {
        if (event.status === 'RUNNING') {
          if (event.parent_span_id) parentIdsToCollapse.add(event.parent_span_id);
          return { ...event, status: runStatus, muted: false };
        }
        return event;
      });
      store.value = store.value.map(event => (
        parentIdsToCollapse.has(event.span_id) ? { ...event, collapsed: true } : event
      ));
      clearTraceWatchdog();
    } else if (runStatus === 'FAILED' || runStatus === 'TIMEOUT') {
      store.value = store.value.map(event => (
        event.status === 'RUNNING' ? { ...event, status: 'ABORTED', muted: true } : event
      ));
      const hasSummaryError = store.value.some(event => event.isSummaryError && event.trace_id === snapshot.run.trace_id);
      if (!hasSummaryError) {
        store.value.push({
          trace_id: snapshot.run.trace_id,
          thread_id: snapshot.run.thread_id,
          span_id: `trace_error_${Date.now()}`,
          parent_span_id: snapshot.run.root_span_id || null,
          step_code: 'TRACE_SUMMARY',
          status: 'FAILED',
          message: snapshot.run.error_message || '任务执行失败，已保护现场并中止未完成节点。',
          timestamp: Date.now(),
          details: {},
          metrics: {},
          isSummaryError: true
        });
      }
      trimTraceQueue(sessionId);
      clearTraceWatchdog();
    }
  }

  function startTraceWatchdog(traceId, threadId) {
    clearTraceWatchdog();
    traceWatchdogTimer = setTimeout(async () => {
      try {
        const snapshot = await fetchTraceSnapshot(traceId || activeTraceId.value, threadId);
        applyTraceSnapshot(snapshot);
      } catch (error) {
        console.warn('[Trace Watchdog] 快照补偿失败:', error);
      }
    }, 15000);
  }

  // 🚀 核心架构解法：在系统主流程中，单向注入所有依赖环境！
  // 完美提供了真正的函数 (showToast) 和所需配置，不再造成 TypeError 和 undefined
  registerVpmContext({
    SystemConfig, sysConfig, activeView, previousView, newsList, favoritesList,
    pluginsList, globalMessages, noteThreads, currentNote, pendingMemory,
    isThinking, userInput, systemToast, inputError, isImmersive,
    activeAgentComponent, deleteModal, pluginPermissionRequest, respondPluginPermission, isImporting, importFile,
    PROFILE_IMPORT_MAX_CHARS, profileImportSessionId, profileImportPreview,
    profileImportStage, profileImportLockReason, profileImportPendingIds,
    profileImportOriginalLength, profileImportNormalizedLength, profileImportPendingCount,
    tempMessages, isTempSession, tempSessionId, tempIsThinking,
    searchQuery, searchMode, memoryFilter, pendingCount, traceEvents, activeTraceId,
    isTracePanelOpen, traceSummary, toggleTracePanel,
    showToast, sendWsCommand, switchView, openNote, confirmDelete, saveSystemConfig,
    confirmImport, commitProfileImport, cancelProfileImport, startTempSession, endTempSession
  });

  async function connectWebSocket() {
    try {
      const port = await invoke('get_server_port');
      SystemConfig.API_BASE = `http://127.0.0.1:${port}`;
      SystemConfig.WS_BASE = `ws://127.0.0.1:${port}`;
      const autoToken = await invoke('get_run_token');
      ws = new WebSocket(`${SystemConfig.WS_BASE}/ws/${SystemConfig.TOKEN}`);
      
      ws.onopen = () => {
        console.log("🟢 [Vault OS] 神经链路已接通！");
        inputError.value = false;
        ws.send(JSON.stringify({ type: "get_config" }));
        ws.send(JSON.stringify({ type: "fetch_plugins" }));
        ws.send(JSON.stringify({ type: "fetch_memory" }));
        ws.send(JSON.stringify({ type: "fetch_history", thread_id: "global" }));
      };
      
      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        const incomingSessionId = data.session_id || 'main';
        if (data.type === 'history_all') {
          globalMessages.value = data.content.global || [];
          const newThreads = { ...noteThreads.value };
          Object.keys(data.content).forEach(key => {
            if (key !== 'global') newThreads[key] = data.content[key];
          });
          noteThreads.value = newThreads;
        }
        else if (data.type === 'config_data') {
          sysConfig.value = data.content;
          if (!sysConfig.value.api_key && activeView.value !== 'settings') {
            activeView.value = 'settings';
          }
        }
        else if (data.type === 'news_list') newsList.value = data.content;
        else if (data.type === 'favorites_list') favoritesList.value = data.content;
        else if (data.type === 'plugins_list') pluginsList.value = data.content;
        else if (data.type === 'plugin_uninstalled_success') {
          pluginsList.value = pluginsList.value.filter(p => p.plugin_id !== data.plugin_id);
        }
        else if (data.type === 'plugin_permission_request') {
          pluginPermissionRequest.value = data;
        }
        else if (data.type === 'temp_session_started') {
          tempSessionId.value = data.session_id;
          tempMessages.value = [];
          tempTraceEvents.value = [];
          tempActiveTraceId.value = '';
          tempIsThinking.value = false;
          activeView.value = 'temp_chat';
          activeAgentComponent.value = null;
          isImmersive.value = false;
          showToast("临时会话已开启。");
        }
        else if (data.type === 'temp_session_ended') {
          if (data.session_id === tempSessionId.value) {
            tempSessionId.value = '';
            tempMessages.value = [];
            tempTraceEvents.value = [];
            tempActiveTraceId.value = '';
            tempIsThinking.value = false;
            activeAgentComponent.value = null;
            isImmersive.value = false;
            if (activeView.value === 'temp_chat') activeView.value = 'chat';
          }
          showToast("临时会话已结束。");
        }
        else if (data.type === 'note_content') currentNote.value.content = data.content;
        else if (data.type === 'delete_success') {
          newsList.value = newsList.value.filter(n => n.id !== data.id);
          favoritesList.value = favoritesList.value.filter(n => n.id !== data.id);
          if (noteThreads.value[data.id]) delete noteThreads.value[data.id];
          if (activeView.value === 'note_detail' && currentNote.value.id === data.id) {
            activeView.value = previousView.value;
          }
        }
        else if (data.type === 'status' && data.content === 'thinking') {
          const isTempEvent = incomingSessionId === tempSessionId.value && incomingSessionId !== 'main';
          if (isTempEvent) tempIsThinking.value = true;
          else mainIsThinking.value = true;
          if (data.trace_id) {
            activeTraceRefFor(incomingSessionId).value = data.trace_id;
            startTraceWatchdog(data.trace_id, data.thread_id || 'global');
          }
          if (isTempEvent) {
            tempMessages.value.push({ role: 'ai', content: '' });
          } else if (activeView.value === 'note_detail') {
            if(!noteThreads.value[currentNote.value.id]) noteThreads.value[currentNote.value.id] = [];
            noteThreads.value[currentNote.value.id].push({ role: 'ai', content: '' });
          } else {
            globalMessages.value.push({ role: 'ai', content: '' });
          }
        }
        else if (data.type === 'status' && data.content === 'done') {
          if (incomingSessionId === tempSessionId.value && incomingSessionId !== 'main') tempIsThinking.value = false;
          else mainIsThinking.value = false;
        }
        else if (data.type === 'trace_event') {
          upsertTraceEvent(data);
          if (data.step_code === 'ROOT' && TRACE_TERMINAL_STATUSES.includes(data.status)) {
            fetchTraceSnapshot(data.trace_id, data.thread_id)
              .then(applyTraceSnapshot)
              .catch(error => console.warn('[Trace] 终态快照拉取失败:', error));
          }
        }
        else if (data.type === 'stream' || data.type === 'chat_stream') {
          const targetId = data.thread_id || 'global';
          const isTempEvent = incomingSessionId === tempSessionId.value && incomingSessionId !== 'main';
          const targetList = isTempEvent ? tempMessages.value : (targetId === 'global' ? globalMessages.value : noteThreads.value[targetId]);
          if (targetList && targetList.length > 0) {
            const lastMsg = targetList[targetList.length - 1];
            if (lastMsg.role === 'ai'|| lastMsg.role === 'assistant') lastMsg.content += data.content;
            else targetList.push({ role: 'ai', content: data.content });
          } else if (targetList) {
            targetList.push({ role: 'ai', content: data.content });
          }
        }
        else if (data.type === 'memory_data') pendingMemory.value = data.content;
        else if (data.type === 'SYSTEM_STATE_CHANGED') {
          sendWsCommand({ type: "fetch_memory" });
        }
        else if (data.type === 'config_save_result') {
          const result = data.content || {};
          if (result.active_config) sysConfig.value = result.active_config;
          const failedChecks = (result.checks || []).filter(item => !item.ok).map(item => item.name).join(', ');
          const failedSuffix = failedChecks ? ` 失败项: ${failedChecks}` : '';
          showToast(result.ok ? `✅ ${result.message || '系统核心已热重载！'}` : `⚠️ ${result.message || '配置体检未通过，已保留当前配置。'}${failedSuffix}`);
          if (result.ok) switchView('chat');
        }
        else if (data.type === 'system_toast') showToast("🩺 [管家汇报] " + data.content);
        else if (data.type === 'profile_import_state') {
          applyProfileImportState(data.content || {});
        }
        else if (data.type === 'profile_import_preview') {
          applyProfileImportState(data.content?.state || {});
          activeView.value = 'profile_import';
        }
        else if (data.type === 'profile_import_done') {
          applyProfileImportState(data.content?.state || {});
        }
        else if (data.type === 'profile_import_error') {
          applyProfileImportState(data.content?.state || {});
          showToast("⚠️ " + (data.content?.message || "画像导入失败"));
        }
        
        else if (data.type === 'ui_command') {
          if (incomingSessionId !== 'main' && incomingSessionId !== tempSessionId.value) return;
          if (incomingSessionId === 'main' && isTempSession.value) return;
          if (incomingSessionId !== 'main' && !isTempSession.value) return;
          console.log(`🪄 收到中枢 UI 指令：${data.target_panel} -> ${data.state}`);
          if (data.state === 'closed') {
            activeAgentComponent.value = null;
            return;
          }
          if (!data.target_component) {
              console.error(` [VPM 协议错误] 缺少 target_component，无法加载 UI`);
              return;
          }
          // 🚀 恢复经典调用：仅需 2 个参数，URL组装和上下文全部由底层代理
          activeAgentComponent.value = loadVpmComponent(data.target_panel, data.target_component);
          isImmersive.value = (data.state === 'immersive' || data.state === undefined);
        }
        
        else if (data.target_panel) {
            if (incomingSessionId !== 'main' && incomingSessionId !== tempSessionId.value) return;
            if (incomingSessionId === 'main' && isTempSession.value) return;
            if (incomingSessionId !== 'main' && !isTempSession.value) return;
            if (!data.target_component) {
                console.error(` [VPM 协议错误] 插件数据包缺少 target_component，无法渲染 UI`);
                return;
            }
            
            // 🚀 恢复经典调用
            activeAgentComponent.value = loadVpmComponent(data.target_panel, data.target_component);
            isImmersive.value = (data.state === 'immersive' || data.state === undefined);
            
            const eventName = `vpm_ws_${data.target_panel}`;
            [300, 800, 1500, 3000].forEach(delay => {
              setTimeout(() => {
                window.dispatchEvent(new CustomEvent(eventName, { detail: data }));
              }, delay);
            });
            return;
        }
      };
      
      ws.onclose = () => {
        if (isAppDestroyed) return;
        console.warn("🔴 [Vault OS] 链路断开，3秒后自愈重连...");
        ws = null;
        setTimeout(connectWebSocket, 3000);
      };
    } catch (error) {
      setTimeout(connectWebSocket, 3000);
    }
  }

  function destroyLink() {
    isAppDestroyed = true;
    if (ws) ws.close();
  }

  function startTempSession() {
    if (!ws || ws.readyState !== WebSocket.OPEN) return triggerErrorShake();
    if (tempSessionId.value) {
      activeView.value = 'temp_chat';
      return;
    }
    sendWsCommand({ type: "start_temp_session" });
  }

  function endTempSession() {
    if (!tempSessionId.value) return;
    sendWsCommand({ type: "end_temp_session", session_id: tempSessionId.value });
  }

  function sendChatCommand() {
    if (!userInput.value || !userInput.value.trim()) return triggerErrorShake();
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      triggerErrorShake();
      const errorMsg = { role: 'ai', content: '🚨 [系统报错] 无法连接到 Python 大脑！' };
      isTempSession.value ? tempMessages.value.push(errorMsg) : (activeView.value === 'note_detail' ? noteThreads.value[currentNote.value.id].push(errorMsg) : globalMessages.value.push(errorMsg));
      return;
    }
    if (!sysConfig.value.api_key) {
      triggerErrorShake();
      alert("请先配置 API Key。");
      activeView.value = 'settings';
      return;
    }

    if (isTempSession.value && !tempSessionId.value) {
      triggerErrorShake();
      showToast("临时会话尚未初始化。");
      return;
    }

    const msg = userInput.value;
    if (!isTempSession.value && activeView.value === 'memory') {
      sendWsCommand({ type: "memory_surgery", content: msg });
      userInput.value = '';
      return;
    }

    const thread_id = isTempSession.value ? tempSessionId.value : (activeView.value === 'note_detail' ? currentNote.value.id : 'global');
    let finalPayload = msg;
    traceEvents.value = [];
    activeTraceId.value = '';
    clearTraceWatchdog();

    if (isTempSession.value) {
      tempMessages.value.push({ role: 'user', content: msg });
    } else if (activeView.value === 'note_detail') {
      noteThreads.value[currentNote.value.id].push({ role: 'user', content: msg });
      finalPayload= `[当前操作界面：笔记阅读模式]\n参考文章：《${currentNote.value.title}》\n部分内容：${currentNote.value.content.substring(0, 1500)}\n\n【系统提示】：如果BOSS的问题与文章相关，请优先基于文章回答；如果问题是通用询问或查询最新资讯，请直接忽略文章，务必调用 web_search 工具获取最新信息。\n\nBOSS的指令：${msg}`;
    } else {
      globalMessages.value.push({ role: 'user', content: msg });
    }

    sendWsCommand({
      message: finalPayload,
      display_message: msg,
      thread_id: thread_id,
      session_mode: isTempSession.value ? "temp" : "main",
      session_id: isTempSession.value ? tempSessionId.value : "main"
    });
    userInput.value = '';
  }

  function switchView(viewName) {
    activeView.value = viewName;
    searchQuery.value = ''; searchMode.value = 'all';
    if (viewName === 'memory') memoryFilter.value = 'all';
    if (viewName === 'temp_chat') {
      startTempSession();
      return;
    }
    if (viewName === 'news') sendWsCommand({ type: "fetch_news" });
    if (viewName === 'favorites') sendWsCommand({ type: "fetch_favorites" });
    if (viewName === 'settings') sendWsCommand({ type: "get_config" });
    if (viewName === 'vpm_center') sendWsCommand({ type: "fetch_plugins" });
    if (viewName === 'memory') sendWsCommand({ type: "fetch_memory" });
    if (viewName === 'profile_import') sendWsCommand({ type: "fetch_profile_import_state" });
  }

  function openNote(note) {
    previousView.value = activeView.value;
    currentNote.value = { id: note.id, title: note.title, content: "📡 正在提取情报...", file_path: note.file_path };
    activeView.value = 'note_detail';
    if (!noteThreads.value[note.id]) noteThreads.value[note.id] = [];
    sendWsCommand({ type: "fetch_note_detail", path: note.file_path });
  }

  function confirmDelete() {
    const note = deleteModal.value.note;
    sendWsCommand({ type: "delete_note", path: note.file_path, id: note.id });
    deleteModal.value.show = false;
  }

  function saveSystemConfig() {
    sendWsCommand({ type: "save_config", content: sysConfig.value });
    showToast("🩺 正在进行配置体检...");
  }

  function confirmImport() {
    if (!importFile.value) return;
    if (!['idle'].includes(profileImportStage.value)) {
      showToast("⚠️ 上一份画像导入尚未完成。");
      return;
    }
    isImporting.value = true;
    profileImportStage.value = 'preparing';
    const reader = new FileReader();
    reader.onload = (e) => {
      const content = e.target.result || '';
      if (!content.trim()) {
        showToast("⚠️ 文档内容为空。");
        applyProfileImportState({ stage: 'idle' });
        return;
      }
      if (content.trim().length > PROFILE_IMPORT_MAX_CHARS) {
        showToast(`⚠️ 文档超过 ${PROFILE_IMPORT_MAX_CHARS} 字符上限。`);
        applyProfileImportState({ stage: 'idle' });
        return;
      }
      sendWsCommand({ type: "prepare_profile_import", content });
      showToast("📡 文档已上传，正在标准化整理...");
    };
    reader.readAsText(importFile.value);
  }

  function commitProfileImport() {
    if (!profileImportSessionId.value || profileImportStage.value !== 'preview') return;
    profileImportStage.value = 'committing';
    isImporting.value = true;
    sendWsCommand({ type: "commit_profile_import", session_id: profileImportSessionId.value });
  }

  function cancelProfileImport() {
    if (!profileImportSessionId.value || profileImportStage.value !== 'preview') return;
    sendWsCommand({ type: "cancel_profile_import", session_id: profileImportSessionId.value });
  }

  return { 
    connectWebSocket, destroyLink, sendChatCommand, switchView, openNote, 
    confirmDelete, saveSystemConfig, confirmImport, commitProfileImport,
    cancelProfileImport, showToast, sendWsCommand, respondPluginPermission, resolveMemoryConflict,
    startTempSession, endTempSession
  };
}
