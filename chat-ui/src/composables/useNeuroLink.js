import { ref, computed, shallowRef } from 'vue';
import { invoke } from '@tauri-apps/api/core';
import { loadVpmComponent } from '../utils/vpmLoader';

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

// === 组合式检索与过滤状态 ===
export const searchQuery = ref('');
export const searchMode = ref('all');
export const memoryFilter = ref('all');

export const pendingCount = computed(() => pendingMemory.value.filter(m => m.status === 'PENDING').length);

let ws = null;
let isAppDestroyed = false;
let toastTimeout = null;
let shakeTimeout = null;

// === 核心通信业务 ===
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

  async function connectWebSocket() {
    try {
      const autoToken = await invoke('get_run_token');
      ws = new WebSocket(`ws://127.0.0.1:8000/ws/${autoToken}`);
      
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
          // 直接根据后端传来的 ID 动态去加载组件！
          // 假设 data.target_panel 传的是 "music_agent"
          // 约定 UI 的入口文件固定叫 "MainPanel" 或者跟插件同名
          activeAgentComponent.value = loadVpmComponent(data.target_panel, 'MusicAgentPanel');
          // 控制空间形态
          isImmersive.value = (data.state === 'immersive');
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

  function sendWsCommand(payload) {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(payload));
    }
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
    confirmDelete, saveSystemConfig, confirmImport, showToast, sendWsCommand
  };
}

// --- 🎧 情绪打碟机：全局播放状态 ---
export const playerState = ref({
  isActive: false,      // 底部播放条是否显示
  isPlaying: false,     // 是否正在播放
  currentSong: null,    // 当前播放的歌曲对象 { title, artist, url }
  progress: 0,          // 播放进度 0-100
});

export function playSong(song) {
  playerState.value.isActive = true;
  playerState.value.currentSong = song;
  playerState.value.isPlaying = true;
  // TODO: 实际的音乐播放逻辑 (如操作隐藏的 iframe 或 Audio 实例)
}

export function togglePlay() {
  if (!playerState.value.currentSong) return;
  playerState.value.isPlaying = !playerState.value.isPlaying;
  // TODO: 实际的暂停/恢复逻辑
}