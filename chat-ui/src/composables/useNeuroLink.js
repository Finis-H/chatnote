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
        console.log("🟢 [系统环境寻址完成]:", SystemConfig);
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
export const noteThreads = ref({});
export const currentNote = ref({ id: null, title: '', content: '', file_path: '' });
export const pendingMemory = ref([]);
export const isThinking = ref(false);
export const userInput = ref('');
export const systemToast = ref({ show: false, message: '' });
export const inputError = ref(false);
export const isImmersive = ref(false);
export const activeAgentComponent = shallowRef(null);
export const deleteModal = ref({ show: false, note: null });
export const isImporting = ref(false);
export const importFile = ref(null);

export const searchQuery = ref('');
export const searchMode = ref('all');
export const memoryFilter = ref('all');

export const pendingCount = computed(() => pendingMemory.value.filter(m => m.status === 'PENDING').length);

let ws = null;
let isAppDestroyed = false;
let toastTimeout = null;
let shakeTimeout = null;

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

  // 🚀 核心架构解法：在系统主流程中，单向注入所有依赖环境！
  // 完美提供了真正的函数 (showToast) 和所需配置，不再造成 TypeError 和 undefined
  registerVpmContext({
    SystemConfig, sysConfig, activeView, previousView, newsList, favoritesList,
    pluginsList, globalMessages, noteThreads, currentNote, pendingMemory,
    isThinking, userInput, systemToast, inputError, isImmersive,
    activeAgentComponent, deleteModal, isImporting, importFile,
    searchQuery, searchMode, memoryFilter, pendingCount,
    showToast, sendWsCommand, switchView, openNote, confirmDelete, saveSystemConfig, confirmImport
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
        ws.send(JSON.stringify({ type: "fetch_memory" }));
        ws.send(JSON.stringify({ type: "fetch_history", thread_id: "global" }));
      };
      
      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
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
          isThinking.value = true;
          if (activeView.value === 'note_detail') {
            if(!noteThreads.value[currentNote.value.id]) noteThreads.value[currentNote.value.id] = [];
            noteThreads.value[currentNote.value.id].push({ role: 'ai', content: '' });
          } else {
            globalMessages.value.push({ role: 'ai', content: '' });
          }
        }
        else if (data.type === 'status' && data.content === 'done') {
          isThinking.value = false;
        }
        else if (data.type === 'stream' || data.type === 'chat_stream') {
          const targetId = data.thread_id || 'global';
          const targetList = targetId === 'global' ? globalMessages.value : noteThreads.value[targetId];
          if (targetList && targetList.length > 0) {
            const lastMsg = targetList[targetList.length - 1];
            if (lastMsg.role === 'ai'|| lastMsg.role === 'assistant') lastMsg.content += data.content;
            else targetList.push({ role: 'ai', content: data.content });
          } else if (targetList) {
            targetList.push({ role: 'ai', content: data.content });
          }
        }
        else if (data.type === 'memory_data') pendingMemory.value = data.content;
        else if (data.type === 'system_toast') showToast("🩺 [管家汇报] " + data.content);
        
        else if (data.type === 'ui_command') {
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

  function sendChatCommand() {
    if (!userInput.value || !userInput.value.trim()) return triggerErrorShake();
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      triggerErrorShake();
      const errorMsg = { role: 'ai', content: '🚨 [系统报错] 无法连接到 Python 大脑！' };
      activeView.value === 'note_detail' ? noteThreads.value[currentNote.value.id].push(errorMsg) : globalMessages.value.push(errorMsg);
      return;
    }
    if (!sysConfig.value.api_key) {
      triggerErrorShake();
      alert("请先配置 API Key。");
      activeView.value = 'settings';
      return;
    }

    const msg = userInput.value;
    if (activeView.value === 'memory') {
      sendWsCommand({ type: "memory_surgery", content: msg });
      userInput.value = '';
      return;
    }

    const thread_id = activeView.value === 'note_detail' ? currentNote.value.id : 'global';
    let finalPayload = msg;

    if (activeView.value === 'note_detail') {
      noteThreads.value[currentNote.value.id].push({ role: 'user', content: msg });
      finalPayload= `[当前操作界面：笔记阅读模式]\n参考文章：《${currentNote.value.title}》\n部分内容：${currentNote.value.content.substring(0, 1500)}\n\n【系统提示】：如果BOSS的问题与文章相关，请优先基于文章回答；如果问题是通用询问或查询最新资讯，请直接忽略文章，务必调用 web_search 工具获取最新信息。\n\nBOSS的指令：${msg}`;
    } else {
      globalMessages.value.push({ role: 'user', content: msg });
    }

    sendWsCommand({ message: finalPayload, display_message: msg, thread_id: thread_id });
    userInput.value = '';
  }

  function switchView(viewName) {
    activeView.value = viewName;
    searchQuery.value = ''; searchMode.value = 'all';
    if (viewName === 'memory') memoryFilter.value = 'all';
    if (viewName === 'news') sendWsCommand({ type: "fetch_news" });
    if (viewName === 'favorites') sendWsCommand({ type: "fetch_favorites" });
    if (viewName === 'settings') sendWsCommand({ type: "get_config" });
    if (viewName === 'vpm_center') sendWsCommand({ type: "fetch_plugins" });
    if (viewName === 'memory') sendWsCommand({ type: "fetch_memory" });
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
    showToast("✅ 核心引擎配置已热重载！");
    switchView('chat');
  }

  function confirmImport() {
    if (!importFile.value) return;
    isImporting.value = true;
    const reader = new FileReader();
    reader.onload = (e) => {
      sendWsCommand({ type: "import_profile", content: e.target.result });
      showToast("📡 文档已上传，管家后台静默提纯中...");
      activeView.value = 'chat';
      isImporting.value = false;
      importFile.value = null;
    };
    reader.readAsText(importFile.value);
  }

  return { 
    connectWebSocket, destroyLink, sendChatCommand, switchView, openNote, 
    confirmDelete, saveSystemConfig, confirmImport, showToast, sendWsCommand, resolveMemoryConflict
  };
}
