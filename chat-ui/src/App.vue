<script setup>
import { ref,computed, onMounted, onUnmounted, nextTick} from 'vue';
import { getCurrentWindow } from '@tauri-apps/api/window';
import { register, unregister } from '@tauri-apps/plugin-global-shortcut';
import { invoke } from '@tauri-apps/api/core';

const appWindow = getCurrentWindow();
// 核心状态机与存储
const activeView = ref('chat');
const sysConfig = ref({ 
  api_key: '', 
  base_url: '', 
  model_max: '', 
  model_mini: '',
  embed_api_key: '', 
  embed_base_url: '', 
  embed_model: 'text-embedding-v4' //  默认锁死
});
const previousView = ref('news'); // 用来记住你从哪个列表点进来的
const isSidebarCollapsed = ref(false); 
const newsList = ref([]); 
const favoritesList = ref([]);
// 新增：自定义悬浮通知状态
const systemToast = ref({ show: false, message: '' });
let toastTimeout = null;
function showToast(msg) {
  systemToast.value = { show: true, message: msg };
  if (toastTimeout) clearTimeout(toastTimeout);
  toastTimeout = setTimeout(() => { systemToast.value.show = false; }, 4000); // 4秒后自动消失
}
// 组合检索系统
const searchQuery = ref('');
const searchMode = ref('all'); // 'all' | 'title' | 'keyword'
// 利用 Vue computed 实现毫秒级数据切片
const filteredNewsList = computed(() => {
  if (!searchQuery.value) return newsList.value;
  const q = searchQuery.value.toLowerCase();
  return newsList.value.filter(n => {
    const matchTitle = n.title?.toLowerCase().includes(q);
    const matchSummary = n.summary?.toLowerCase().includes(q); // 用摘要充当轻量级内容检索
    const matchKeyword = n.keywords && n.keywords.some(k => k.toLowerCase().includes(q));
    
    if (searchMode.value === 'title') return matchTitle;
    if (searchMode.value === 'keyword') return matchKeyword;
    return matchTitle || matchSummary || matchKeyword; // 全局模式
  });
});
const filteredFavoritesList = computed(() => {
  if (!searchQuery.value) return favoritesList.value;
  const q = searchQuery.value.toLowerCase();
  return favoritesList.value.filter(n => {
    const matchTitle = n.title?.toLowerCase().includes(q);
    const matchSummary = n.summary?.toLowerCase().includes(q);
    const matchKeyword = n.keywords && n.keywords.some(k => k.toLowerCase().includes(q));
    
    if (searchMode.value === 'title') return matchTitle;
    if (searchMode.value === 'keyword') return matchKeyword;
    return matchTitle || matchSummary || matchKeyword;
  });
});
const globalMessages = ref([]); // 全局主终端对话
const noteThreads = ref({});    // 按笔记ID独立存放的对话线程
const currentNote = ref({ id: null, title: '', content: '' });
const userInput = ref('');
const isThinking = ref(false);
const inputError = ref(false);
const viewportRef = ref(null);
const scrollViewport = () => {
  if (viewportRef.value) {
    viewportRef.value.scrollTop = viewportRef.value.scrollHeight;
  }
};
let ws = null;
// UI 交互与视图路由
const toggleSidebar = () => { isSidebarCollapsed.value = !isSidebarCollapsed.value; };
// --- 自定义删除弹窗状态机 ---
const deleteModal = ref({ show: false, note: null});

const pendingMemory = ref([]);
// 计算红点数量：只统计处于 PENDING（待处理）状态的冲突记忆
const pendingCount = computed(() => {
  return pendingMemory.value.filter(item => item.status === 'PENDING').length;
});
const importFile = ref(null);
const isImporting = ref(false);

// 记忆面板的胶囊滤镜状态
const memoryFilter = ref('all');
// 智能过滤与排序引擎
const displayMemory = computed(() => {
  let list = [...pendingMemory.value];
  // 72 小时视界线 (Event Horizon) 拦截
  const THREE_DAYS_MS = 3 * 24 * 60 * 60 * 1000;
  const now = Date.now();
  list = list.filter(m => {
    // 1. 如果是 PENDING (红灯待办)，永远展示！绝不能让未处理的冲突因为时间久了就消失。
    if (m.status === 'PENDING') return true;
    // 2. 如果是历史档案 (MERGED / REJECTED)，只展示最近 3 天的。
    // 注意：假设后端传了 created_at。如果你的卡片上只有 expires_at，我们可以用 expires_at 减去 3 天来倒推它的创建时间。
    const itemTime = m.created_at ? new Date(m.created_at).getTime() : 
                     (m.expires_at ? new Date(m.expires_at).getTime() - THREE_DAYS_MS : now);
    return (now - itemTime) <= THREE_DAYS_MS;
  });
  // 1. 根据胶囊选项过滤
  if (memoryFilter.value === 'pending') {
    list = list.filter(m => m.status === 'PENDING');
  } else if (memoryFilter.value === 'merged') {
    list = list.filter(m => m.status !== 'PENDING'); // 把 MERGED, REJECTED, AUTO_OVERWRITTEN 都算作已处理
  }
  // 2. 绝对优先级排序：永远把 PENDING (待决冲突) 顶到最前面！
  return list.sort((a, b) => {
    if (a.status === 'PENDING' && b.status !== 'PENDING') return -1;
    if (a.status !== 'PENDING' && b.status === 'PENDING') return 1;
    // 如果状态相同，按时间倒序（最新的在上面，假设你的后端有 created_at 字段。如果没有，就保持原样）
    const timeA = a.created_at ? new Date(a.created_at).getTime() : 0;
    const timeB = b.created_at ? new Date(b.created_at).getTime() : 0;
    return timeB - timeA;
  });
});

function switchView(viewName) {
  activeView.value = viewName;
  // 切换频道时，清空检索词，保持干净
  searchQuery.value = '';
  searchMode.value = 'all';
  if (viewName === 'memory') memoryFilter.value = 'all';
  if (viewName === 'chat') nextTick(scrollViewport);
  if (ws && ws.readyState === WebSocket.OPEN) {
    // 根据不同的视图，向后端要不同的数据
    if (viewName === 'news') ws.send(JSON.stringify({ type: "fetch_news" }));
    if (viewName === 'favorites') ws.send(JSON.stringify({ type: "fetch_favorites" }));
    if (viewName === 'settings') ws.send(JSON.stringify({ type: "get_config" }));
    if (viewName === 'memory') { memoryFilter.value = 'all'; ws.send(JSON.stringify({ type: "fetch_memory" }))};
  }
}
function openNote(note) {
  previousView.value = activeView.value;
  // 1. 先挂载基本信息，正文设为加载状态
  currentNote.value = { 
    id: note.id, 
    title: note.title, 
    content: "📡 正在从本地 Vault 提取深度情报...",
    file_path: note.file_path // 确保路径已存入
  };
  // 2. 切换到详情视图
  activeView.value = 'note_detail';
  // 3. 初始化对话线程
  if (!noteThreads.value[note.id]) noteThreads.value[note.id] = [];
  // 4. 核心：向 Python 发出正文抓取指令
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ 
      type: "fetch_note_detail", 
      path: note.file_path 
    }));
  }
  // 5. 阅读笔记通常从头开始，将视口滚回顶部
  nextTick(() => {
    if (viewportRef.value) viewportRef.value.scrollTop = 0;
  });
}
// 神经链路 (WebSocket 通信与自愈)
async function connectWebSocket() {
  try {
    const autoToken = await invoke('get_run_token');
    ws = new WebSocket(`ws://127.0.0.1:8000/ws/${autoToken}`);
    ws.onopen = () => {
      console.log("🟢 [Vault OS] 神经链路已接通！");
      inputError.value = false;
      ws.send(JSON.stringify({ type: "get_config" }));
      ws.send(JSON.stringify({ type: "fetch_memory" }));
    };
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'history_all') {
        globalMessages.value = data.content.global || [];
        Object.keys(data.content).forEach(key => {
          if (key !== 'global') noteThreads.value[key] = data.content[key];
        });
        if (activeView.value === 'chat') {
          nextTick(scrollViewport);
        }
      }
      else if (data.type === 'config_data') {
        sysConfig.value = data.content;
        if (!sysConfig.value.api_key && activeView.value !== 'settings') {
            console.warn("⚠️ 检测到引擎未配置，强制进入初始化流程");
            activeView.value = 'settings';
        }
      }
      // 补充丢失的管道：接收新闻列表、收藏列表、笔记正文
      else if (data.type === 'news_list') {
        newsList.value = data.content;
      }
      else if (data.type === 'favorites_list') {
        favoritesList.value = data.content;
      }
      else if (data.type === 'note_content') {
        currentNote.value.content = data.content;
      }
      else if (data.type === 'delete_success') {
        // 1. 从前端数组中直接剔除，实现无感刷新
        newsList.value = newsList.value.filter(n => n.id !== data.id);
        favoritesList.value = favoritesList.value.filter(n => n.id !== data.id);
        // 2. 如果用户恰好在看这篇笔记的详情，强制将其踢回列表页
        if (activeView.value === 'note_detail' && currentNote.value.id === data.id) {
          activeView.value = previousView.value;
        }
        console.log(`✅ 笔记 ${data.id} 已从物理层和 UI 层抹除`);
      }
      // 补充丢失的管道：处理 AI 思考状态，并创建空白气泡用于流式注入
      else if (data.type === 'status' && data.content === 'thinking') {
        isThinking.value = true;
        if (activeView.value === 'note_detail') {
          noteThreads.value[currentNote.value.id].push({ role: 'ai', content: '' });
        } else {
          globalMessages.value.push({ role: 'ai', content: '' });
        }
        nextTick(scrollViewport);
      }
      else if (data.type === 'status' && data.content === 'done') {
        isThinking.value = false;
      }
      // 流式打字机
      else if (data.type === 'stream') {
        const targetId = data.thread_id;
        const targetList = targetId === 'global' ? globalMessages.value : noteThreads.value[targetId];
        if (targetList && targetList.length > 0) {
          const lastIndex = targetList.length - 1;
          const lastMsg = targetList[lastIndex];
          if (lastMsg.role === 'ai') {
            lastMsg.content += data.content;
          } 
          else {
            // 如果因为网络原因没收到 thinking 状态，主动补一个 AI 气泡
            targetList.push({ role: 'ai', content: data.content });
          }
        } 
        else if (targetList) {
          // 极端情况：列表为空时收到流
          targetList.push({ role: 'ai', content: data.content });
        }
        nextTick(scrollViewport);
      }
      else if (data.type === 'memory_data') {
        pendingMemory.value = data.content;
      }
      // 接收后端记忆手术完毕的极客汇报
      else if (data.type === 'system_toast') {
        showToast("🩺 [管家汇报] " + data.content);
      }
    };
    ws.onclose = () => {
      console.warn("🔴 [Vault OS] 链路断开，3秒后自愈重连...");
      ws = null;
      setTimeout(connectWebSocket, 3000);
    };
    ws.onerror = (err) => { console.error("🚨 WebSocket 异常:", err); };
  } catch (error) {
    console.error("无法获取系统 Token，可能是后端未启动。3秒后重试...");
    setTimeout(connectWebSocket, 3000);
  }
}
// 核心指令发射器 (含防呆拦截)
function sendCommand() {
  // 1. 空白指令拦截
  if (!userInput.value || !userInput.value.trim()) {
    triggerErrorShake();
    return;
  }
  // 2. 离线阻断与 UI 报警穿透
  if (!ws || ws.readyState !== WebSocket.OPEN) {
    triggerErrorShake();
    const errorMsg = { role: 'ai', content: '🚨 [系统报错] 无法连接到 Python 大脑，请检查后端的 server.py 是否已点火！' };
    if (activeView.value === 'note_detail') {
      noteThreads.value[currentNote.value.id].push(errorMsg);
    } else {
      globalMessages.value.push(errorMsg);
    }
    nextTick(scrollViewport);
    return;
  }
  if (!sysConfig.value.api_key) {
    triggerErrorShake();
    alert("请先在「引擎设置」中填入 API Key，否则管家无法连接到大脑。");
    activeView.value = 'settings';
    return;
  }

  const msg = userInput.value;
  // 🚨 核心修复：记忆同步面板的专属指令拦截
  if (activeView.value === 'memory') {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: "memory_surgery", content: msg }));
    }
    userInput.value = ''; // 清空输入框
    return; // 🛑 极其关键：直接 return，绝不将其记入主控终端的聊天记录！
  }
  // 3. 正常发送管线 (主控终端 & 笔记详情)
  const thread_id = activeView.value === 'note_detail' ? currentNote.value.id : 'global';
  let finalPayload = msg; 

  if (activeView.value === 'note_detail') {
    // 视觉上只展示纯指令
    noteThreads.value[currentNote.value.id].push({ role: 'user', content: msg });
    // 后台拼装隐形上下文
    finalPayload= `[系统最高指令：用户正在阅读以下文章，请结合文章内容回答问题。]\n文章标题：《${currentNote.value.title}》\n文章内容：${currentNote.value.content}\n\nBOSS的最新指令：${msg}`;
  } else {
    // 正常主控终端聊天
    globalMessages.value.push({ role: 'user', content: msg });
  }
  
  nextTick(scrollViewport); // 触发自动滚动

  ws.send(JSON.stringify({ 
    message: finalPayload,
    display_message: msg,
    thread_id: thread_id
  }));
  
  userInput.value = '';
}
function saveSystemConfig() {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: "save_config", content: sysConfig.value }));
    showToast("✅ 核心引擎配置已下发并热重载！");
    switchView('chat');
  }
}
// 点击垃圾桶，唤起弹窗
function requestDelete(event, note) {
  event.stopPropagation(); 
  deleteModal.value = { show: true, note: note };
}
// 确认删除：发射指令并关闭弹窗
function confirmDelete() {
  const note = deleteModal.value.note;
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ 
      type: "delete_note", 
      path: note.file_path, 
      id: note.id 
    }));
  }
  deleteModal.value.show = false;
}
// 取消删除
function cancelDelete() {
  deleteModal.value.show = false;
}
let shakeTimeout = null;
function triggerErrorShake() {
  inputError.value = true;
  if (shakeTimeout) clearTimeout(shakeTimeout); // 清除上一次的定时器
  shakeTimeout = setTimeout(() => { inputError.value = false; }, 500);
}
// 窗口与生命周期管理
let isToggling = false;
async function toggleVaultOS() {
  if (isToggling) return;
  isToggling = true;
  try {
    const isVisible = await appWindow.isVisible();
    isVisible ? await appWindow.hide() : (await appWindow.unminimize(), await appWindow.show(), await appWindow.setFocus());
  } finally { setTimeout(() => { isToggling = false; }, 500); }
}
function handleKeyDown(event) { if (event.key === 'Escape') appWindow.hide(); }
// 美化时间
function formatExpireTime(isoString) { return new Date(isoString).toLocaleString(); }
// 处理文件选择
function handleFileChange(e) {
  const file = e.target.files[0];
  if (file && (file.name.endsWith('.md') || file.name.endsWith('.txt'))) {
    importFile.value = file;
  } else {
    showToast("⚠️ 仅支持导入 .md 或 .txt 格式的文档");
    e.target.value = ''; // 重置
  }
}
// 提交导入
function confirmImport() {
  if (!importFile.value) return;
  isImporting.value = true;
  const reader = new FileReader();
  reader.onload = (e) => {
    const content = e.target.result;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ 
        type: "import_profile", 
        content: content 
      }));
      showToast("📡 文档已上传，管家正在后台静默提纯...");
      activeView.value = 'chat'; // 立即返回主界面，不影响操作
    }
    isImporting.value = false;
    importFile.value = null;
  };
  reader.readAsText(importFile.value);
}
onMounted(async () => {
  connectWebSocket();
  window.addEventListener('keydown', handleKeyDown);
  try { await register('Alt+V', toggleVaultOS); } catch (e) {}
});
onUnmounted(async () => {
  if (ws) ws.close();
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
        <div class="view-content" ref="viewportRef">
          <div v-if="activeView === 'chat'" class="scroll-container">
            <div v-for="(m, i) in globalMessages" :key="i" :class="['bubble', m.role]">{{ m.content }}</div>
            <div v-if="isThinking && activeView==='chat'" class="thinking-cursor">🧠 大脑全速运转中...</div>
          </div>
          <div v-if="activeView === 'news'" class="scroll-container card-grid">
            <h2 class="view-title">最新摄入消息</h2>
            <div class="search-console">
              <div class="filter-capsules">
                <button :class="{ active: searchMode === 'all' }" @click="searchMode = 'all'">全局</button>
                <button :class="{ active: searchMode === 'title' }" @click="searchMode = 'title'">标题</button>
                <button :class="{ active: searchMode === 'keyword' }" @click="searchMode = 'keyword'">标签</button>
              </div>
              <input class="search-input" v-model="searchQuery" placeholder="输入关键字进行毫秒级过滤..." />
            </div>
            <div class="news-card" v-for="n in filteredNewsList" :key="n.id" @click="openNote(n)">
              <div class="card-header">
                <span class="card-id">#{{ n.id }}</span>
                <span class="card-time">{{ n.time_str }}</span>
                <button class="delete-btn" @click="requestDelete($event, n)" title="彻底删除">🗑️</button>
              </div>
              <h3 class="card-title">{{ n.title }}</h3>
              <p class="card-summary">{{ n.summary }}</p>
              <div class="card-tags" v-if="n.keywords && n.keywords.length">
                <span class="tag" v-for="k in n.keywords" :key="k">{{ k }}</span>
              </div>
              <div class="card-footer">点击阅读并讨论 →</div>
            </div>
          </div>
          <div v-if="activeView === 'favorites'" class="scroll-container card-grid">
            <h2 class="view-title">⭐ 订阅与收藏</h2>
            <div class="search-console">
              <div class="filter-capsules">
                <button :class="{ active: searchMode === 'all' }" @click="searchMode = 'all'">全局</button>
                <button :class="{ active: searchMode === 'title' }" @click="searchMode = 'title'">标题</button>
                <button :class="{ active: searchMode === 'keyword' }" @click="searchMode = 'keyword'">标签</button>
              </div>
              <input class="search-input" v-model="searchQuery" placeholder="输入关键字进行毫秒级过滤..." />
            </div>
            <div class="news-card" v-for="n in filteredFavoritesList" :key="n.id" @click="openNote(n)">
              <div class="card-header">
                <span class="card-id">#{{ n.id }}</span>
                <span class="card-time">{{ n.time_str }}</span>
                <button class="delete-btn" @click="requestDelete($event, n)" title="彻底删除">🗑️</button>
              </div>
              <h3 class="card-title">{{ n.title }}</h3>
              <p class="card-summary">{{ n.summary }}</p>
              <div class="card-tags" v-if="n.keywords && n.keywords.length">
                <span class="tag" v-for="k in n.keywords" :key="k">{{ k }}</span>
              </div>
              <div class="card-footer">点击阅读并讨论 →</div>
            </div>
          </div>
          <div v-if="activeView === 'note_detail'" class="scroll-container note-view">
            <div class="note-body">
              <button class="back-link" @click="switchView(previousView)">← 返回列表</button>
              <h1>{{ currentNote.title }}</h1>
              <div class="article">{{ currentNote.content }}</div>
            </div>
            <div class="thread-separator">讨论线程 (CONTEXT_THREAD)</div>
            <div class="thread-chat">
              <div v-for="(m, i) in noteThreads[currentNote.id]" :key="i" :class="['bubble', m.role]">
                <span class="role-tag" v-if="m.role==='user'">BOSS</span>
                <span class="role-tag" v-else>AI</span>
                {{ m.content }}
              </div>
              <div v-if="isThinking && activeView==='note_detail'" class="thinking-cursor">🧠 大脑全速运转中...</div>
            </div>
          </div>
          <div v-if="activeView === 'profile_import'" class="scroll-container">
            <h2 class="view-title">🌱 个性偏好初始化</h2>
            <div class="settings-panel">
              <p class="memory-subtitle">上传一份包含你个人偏好、编程习惯或自我介绍的文档，管家将通过深度扫描快速学习并重塑你的画像。</p>
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
          <div v-if="activeView === 'settings'" class="scroll-container">
            <h2 class="view-title">⚙️ LLM 引擎中枢配置</h2>
            <div class="settings-panel">
              <div class="settings-divider">知识库向量引擎 (RAG Core)</div>
              <div class="setting-item">
                <label>向量计算模型 (Embedding Model)</label>
                <input class="setting-input readonly-input" v-model="sysConfig.embed_model" disabled />
              </div>
              <div class="setting-item">
                <label>Embedding API Key</label>
                <input class="setting-input" type="password" v-model="sysConfig.embed_api_key" placeholder="请输入千问 Embedding 专用 API Key" />
                <span class="setting-tip">用于将本地笔记转化为高维向量。若不填写，摄入功能将不可用。</span>
              </div>
              <div class="setting-item">
                <label>API Base URL (代理端点)</label>
                <input class="setting-input" v-model="sysConfig.base_url" placeholder="例如: https://api.deepseek.com/v1" />
                <span class="setting-tip">兼容 OpenAI 格式的任何第三方 API 或本地 Ollama 地址。</span>
              </div>
              <div class="setting-item">
                <label>API Key (密钥)</label>
                <input class="setting-input" type="password" v-model="sysConfig.api_key" placeholder="sk-..." />
              </div>
              <div class="setting-item">
                <label>主算力模型 (Model Max)</label>
                <input class="setting-input" v-model="sysConfig.model_max" placeholder="例如: deepseek-chat 或 gpt-4o" />
                <span class="setting-tip">用于深度对话和高复杂度逻辑推理。</span>
              </div>
              <div class="setting-item">
                <label>轻量提纯模型 (Model Mini)</label>
                <input class="setting-input" v-model="sysConfig.model_mini" placeholder="例如: gpt-3.5-turbo" />
                <span class="setting-tip">用于后台极速提取用户画像、打标签等脏活累活。</span>
              </div>
              <button class="save-btn" @click="saveSystemConfig">⚡ 烧录并热重载引擎</button>
            </div>
          </div>
          <div v-if="activeView === 'memory'" class="scroll-container">
            <div class="memory-header">
              <h2 class="view-title">🧠 记忆神经同步 (Staging Area)</h2>
              <p class="memory-subtitle">在此界面向管家发送指令，可对记忆进行二次覆写或驳回。超时 3 天的警告项将被强行同化。</p>
            </div>
            <div class="search-console">
              <div class="filter-capsules">
                <button :class="{ active: memoryFilter === 'all' }" @click="memoryFilter = 'all'">全局视野</button>
                <button :class="{ active: memoryFilter === 'pending'}" @click="memoryFilter = 'pending'">
                  ⚠️ 待决冲突 ({{ pendingCount }})
                </button>
                <button :class="{ active: memoryFilter === 'merged' }" @click="memoryFilter = 'merged'">✨ 历史档案</button>
              </div>
            </div>
            <div v-if="pendingMemory.length === 0" class="empty-state">
              当前神经链路纯净，无待决记忆碎片。
            </div>
            <div class="memory-grid" v-else>
              <div v-for="mem in displayMemory" :key="mem.id" 
                   class="memory-card" 
                   :class="mem.status === 'PENDING' ? 'card-warning' : 'card-success'">
                <div class="card-header">
                  <span class="mem-tag">{{ mem.category.toUpperCase() }}</span>
                  <span class="mem-status" v-if="mem.status === 'MERGED'">✨ 已同化生效</span>
                  <span class="mem-status" v-if="mem.status === 'REJECTED'">❌ 已驳回抹除</span>
                  <span class="mem-status" v-if="mem.status === 'AUTO_OVERWRITTEN'">⏰ 超时强行同化</span>
                  <span class="mem-status blink" v-if="mem.status === 'PENDING'">⚠️ 记忆冲突待决</span>
                </div>
                <div class="card-body">
                  <div v-if="mem.type === 'CONFLICT'" class="conflict-zone">
                    <div class="old-trait"><del>{{ mem.old_trait }}</del></div>
                    <div class="arrow">↓ 强行覆写为 ↓</div>
                  </div>
                  <div class="new-trait">{{ mem.new_trait }}</div>
                </div>
                <div class="card-footer" v-if="mem.status === 'PENDING'">
                  ⏳ 倒计时: 距离强制同化还有 <span class="countdown">{{ formatExpireTime(mem.expires_at) }}</span>
                </div> 
              </div>
            </div>
          </div>
        </div>
        <div class="fixed-console" :class="{ 'error-shake': inputError }">
          <div class="context-pill" v-if="activeView==='note_detail'">
            📍 讨论中: {{ currentNote.title }}
          </div>
          <span class="prompt-icon">❯</span>
          <input v-model="userInput" @keyup.enter="sendCommand" placeholder="下达指令..." autofocus />
        </div>
      </main>
      <aside class="sidebar side-right">
        <div class="nav-group">
          <div class="nav-item">
            <span class="icon">📓</span><span class="label">个人笔记</span>
          </div>
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
      <span class="toast-icon">🩺</span>
      <span class="toast-text">{{ systemToast.message }}</span>
    </div>
  </div>
</template>

<style scoped>
/* ====== 基础重置 ====== */
.magic-box { width: 100vw; height: 100vh; display: flex; flex-direction: column; background: #0a0a0c; color: #d1d1d1; font-family: 'Consolas', monospace; overflow: hidden; }
.title-bar { height: 40px; display: flex; align-items: center; justify-content: space-between; padding: 0 15px; background: #000; border-bottom: 1px solid #222; user-select: none; }
.left-group { display: flex; align-items: center; }
.os-name { font-size: 12px; color: #666; letter-spacing: 2px; }
.status-badge { font-size: 10px; color: #00ffcc; font-weight: bold; }
.workspace-body { display: flex; flex: 1; overflow: hidden; }

/* ====== 侧边栏与折叠 ====== */
.sidebar {
  width: 200px; background: rgba(0,0,0,0.4); border-right: 1px solid #1a1a1a;
  transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden; display: flex; flex-direction: column; white-space: nowrap;
}
.sidebar.collapsed { width: 60px; }
.sidebar.collapsed .label { opacity: 0; pointer-events: none; }
.side-right { border-right: none; border-left: 1px solid #1a1a1a; }
.fold-btn { background: none; border: none; color: #fff; font-size: 20px; cursor: pointer; margin-right: 15px; }

.nav-group { padding: 15px 0; }
.nav-item { padding: 12px 20px; cursor: pointer; display: flex; align-items: center; gap: 15px; color: #888; transition: all 0.2s; }
.nav-item:hover, .nav-item.active { background: rgba(0, 255, 204, 0.05); color: #00ffcc; border-left: 2px solid #00ffcc; }
.nav-item .icon { font-size: 18px; }

/* ====== 中控视窗 ====== */
.center-viewport { flex: 1; display: flex; flex-direction: column; background: #0d0d0f; min-width: 400px; }
.view-content { flex: 1; overflow-y: auto; }
.view-content::-webkit-scrollbar { width: 6px; }
.view-content::-webkit-scrollbar-thumb { background: #333; border-radius: 3px; }
.scroll-container { padding: 30px; display: flex; flex-direction: column; gap: 20px; }

/* 聊天气泡 */
.bubble { padding: 12px 16px; border-radius: 6px; font-size: 14px; max-width: 85%; line-height: 1.6; white-space: pre-wrap; }
.user { background: #1a1a1c; align-self: flex-end; border-right: 2px solid #555; color: #eee; }
.ai { background: rgba(0,255,204,0.03); align-self: flex-start; border-left: 2px solid #00ffcc; color: #ccc; }
.role-tag { font-size: 10px; opacity: 0.4; display: block; margin-bottom: 5px; }

/* 新闻卡片 */
.view-title { color: #fff; font-size: 18px; font-weight: normal; margin-bottom: 10px; }
.news-card {
  background: rgba(255, 255, 255, 0.02); border: 1px solid #222; border-radius: 10px;
  padding: 20px; cursor: pointer; transition: all 0.2s;
}
.news-card:hover { transform: translateY(-2px); border-color: #00ffcc; background: rgba(0, 255, 204, 0.02); box-shadow: 0 10px 20px rgba(0,0,0,0.3); }
.card-header { display: flex; justify-content: space-between; align-items: center; font-size: 10px; color: #555; margin-bottom: 12px; }
.card-title { font-size: 16px; color: #00ffcc; margin-bottom: 8px; }
.card-summary { font-size: 13px; color: #888; line-height: 1.6; }
.card-footer { margin-top: 15px; font-size: 11px; color: #555; }

/* 笔记阅读器 */
.note-body { border-bottom: 1px solid #222; padding-bottom: 40px; margin-bottom: 20px; }
.note-body h1 { color: #fff; margin-bottom: 20px; font-size: 22px; }
.article { line-height: 1.8; color: #bbb; font-size: 15px; white-space: pre-wrap; }
.thread-separator { text-align: center; color: #444; font-size: 11px; letter-spacing: 3px; margin: 30px 0; }
.back-link { background: transparent; border: 1px solid #444; color: #888; padding: 5px 12px; border-radius: 4px; cursor: pointer; margin-bottom: 20px; font-family: 'Consolas'; }
.back-link:hover { color: #fff; border-color: #fff; }

/* ====== 检索控制台 ====== */
.search-console { display: flex; gap: 15px; margin-bottom: 25px; align-items: center; }
.filter-capsules { display: flex; background: rgba(255,255,255,0.05); border-radius: 20px; padding: 3px; }
.filter-capsules button { 
  background: transparent; border: none; color: #888; padding: 6px 16px; 
  border-radius: 18px; cursor: pointer; font-size: 12px; transition: all 0.2s; font-family: 'Consolas';
}
.filter-capsules button.warning-tab.active { 
  background: #ff4d4f; 
  color: #fff; 
  box-shadow: 0 0 10px rgba(255, 77, 79, 0.4);
}
.filter-capsules button:hover { color: #fff; }
.filter-capsules button.active { background: #00ffcc; color: #000; font-weight: bold; }
.search-input { 
  flex: 1; background: rgba(0,0,0,0.3); border: 1px solid #333; color: #fff; 
  padding: 10px 15px; border-radius: 6px; font-size: 14px; outline: none; transition: border 0.2s;
}
.search-input:focus { border-color: #00ffcc; box-shadow: 0 0 10px rgba(0,255,204,0.1); }

/* 卡片标签 */
.card-tags { display: flex; gap: 8px; margin-top: 12px; flex-wrap: wrap; }
.tag { background: rgba(0, 255, 204, 0.1); border: 1px solid rgba(0,255,204,0.3); color: #00ffcc; font-size: 10px; padding: 2px 8px; border-radius: 4px; }

.delete-btn {
  background: transparent; border: none; color: #555; 
  cursor: pointer; padding: 4px 8px; border-radius: 4px;
  font-size: 14px; transition: all 0.2s;
  z-index: 10; /* 确保在卡片最上层 */
}
.delete-btn:hover { 
  color: #ff4d4f; 
  background: rgba(255, 77, 79, 0.1); 
  transform: scale(1.1);
}

/* ====== 设置面板 ====== */
.settings-panel { background: rgba(255, 255, 255, 0.02); border: 1px solid #222; border-radius: 10px; padding: 30px; }
.setting-item { display: flex; flex-direction: column; margin-bottom: 25px; }
.setting-item label { color: #00ffcc; font-size: 14px; margin-bottom: 8px; font-weight: bold; }
.setting-input { 
  background: rgba(0,0,0,0.5); border: 1px solid #444; color: #fff; padding: 12px; 
  border-radius: 6px; font-family: 'Consolas'; font-size: 14px; outline: none; transition: all 0.2s;
}
.setting-input:focus { border-color: #00ffcc; box-shadow: 0 0 10px rgba(0,255,204,0.1); }
.setting-tip { color: #666; font-size: 12px; margin-top: 6px; }
.save-btn { 
  background: rgba(0, 255, 204, 0.1); border: 1px solid #00ffcc; color: #00ffcc;
  padding: 12px 20px; border-radius: 6px; cursor: pointer; font-family: 'Consolas';
  font-size: 15px; font-weight: bold; transition: all 0.2s; width: 100%; margin-top: 10px;
}
.save-btn:hover { background: #00ffcc; color: #000; box-shadow: 0 0 20px rgba(0,255,204,0.4); }
.settings-divider {
  margin: 30px 0 20px;
  border-bottom: 1px solid #222;
  color: #444;
  font-size: 11px;
  letter-spacing: 2px;
  text-transform: uppercase;
}
.readonly-input {
  background: rgba(255, 255, 255, 0.02) !important;
  border-color: #222 !important;
  color: #555 !important;
  cursor: not-allowed;
}
/* ====== 底部常驻终端 ====== */
.fixed-console {
  height: 65px; min-height: 65px; background: #050505; border-top: 1px solid #222;
  display: flex; align-items: center; padding: 0 25px; gap: 15px; position: relative;
}
.context-pill {
  position: absolute; top: -25px; left: 25px; background: #00ffcc; color: #000;
  font-size: 10px; font-weight: bold; padding: 3px 8px; border-radius: 4px;
}
.prompt-icon { color: #00ffcc; font-weight: bold; }
input { flex: 1; background: transparent; border: none; outline: none; color: #fff; font-size: 15px; font-family: 'Consolas'; }

/* ====== 动效 ====== */
.error-shake { animation: shake 0.4s; background: rgba(255,0,0,0.1) !important; }
@keyframes shake { 0%,100%{transform:translateX(0)} 25%{transform:translateX(-5px)} 75%{transform:translateX(5px)} }
.thinking-cursor { color: #00ffcc; font-size: 12px; animation: pulse-opacity 1.5s infinite; padding: 10px; }
@keyframes pulse { 0%, 100% { opacity: 0.5; } 50% { opacity: 1; } }

/* ====== 潜意识同步面板 ====== */
.memory-header { margin-bottom: 25px; border-bottom: 1px solid #333; padding-bottom: 15px; }
.memory-subtitle { color: #888; font-size: 13px; margin-top: 5px; }
.badge {
  background: #ff4d4f; color: #fff; font-size: 11px; font-weight: bold;
  padding: 2px 6px; border-radius: 10px; margin-left: auto;
}
.pulse-anim { animation: pulse 1.5s infinite; box-shadow: 0 0 0 0 rgba(255, 77, 79, 0.7); }
@keyframes pulse-glow {
  0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(255, 77, 79, 0.7); }
  70% { transform: scale(1); box-shadow: 0 0 0 6px rgba(255, 77, 79, 0); }
  100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(255, 77, 79, 0); }
}
.memory-grid { display: flex; flex-direction: column; gap: 15px; }
.memory-card {
  background: rgba(0,0,0,0.6); border: 1px solid #333; border-radius: 8px; padding: 15px;
  position: relative; overflow: hidden; transition: all 0.3s;
}
/* 卡片左侧的霓虹边带 */
.memory-card::before {
  content: ''; position: absolute; left: 0; top: 0; bottom: 0; width: 4px;
}
.card-success { border-color: rgba(0, 255, 204, 0.3); }
.card-success::before { background: #00ffcc; box-shadow: 0 0 10px #00ffcc; }
.card-warning { border-color: rgba(255, 77, 79, 0.4); }
.card-warning::before { background: #ff4d4f; box-shadow: 0 0 10px #ff4d4f; }

.card-header { display: flex; justify-content: space-between; margin-bottom: 12px; font-size: 12px; }
.mem-tag { background: #222; padding: 3px 8px; border-radius: 4px; color: #aaa; font-family: 'Consolas'; }
.mem-status { font-weight: bold; }
.card-success .mem-status { color: #00ffcc; }
.card-warning .mem-status { color: #ff4d4f; }
.blink { animation: blinkText 2s infinite; }
@keyframes blinkText { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }

.conflict-zone { background: rgba(255, 77, 79, 0.05); padding: 10px; border-radius: 4px; margin-bottom: 10px; border: 1px dashed #555; }
.old-trait { color: #888; text-decoration: line-through; font-size: 13px; }
.arrow { color: #ff4d4f; font-size: 12px; text-align: center; margin: 5px 0; font-family: 'Consolas'; }
.new-trait { color: #fff; font-size: 15px; line-height: 1.5; }

.card-footer { margin-top: 15px; padding-top: 10px; border-top: 1px solid #333; font-size: 12px; color: #888; }
.countdown { color: #ff4d4f; font-weight: bold; font-family: 'Consolas'; }
/* ===画像导入设置==== */
.upload-label {
  display: block; width: 100%; padding: 40px; border: 2px dashed #333;
  border-radius: 8px; text-align: center; color: #888; cursor: pointer;
  transition: all 0.2s; margin: 20px 0;
}
.upload-label:hover { border-color: #00ffcc; color: #00ffcc; background: rgba(0,255,204,0.02); }
/* ====== 全局悬浮通知 (Cyber Toast) ====== */
.cyber-toast {
  position: fixed; top: 20px; left: 50%; transform: translateX(-50%) translateY(-100px);
  background: rgba(0, 0, 0, 0.85); border: 1px solid #00ffcc; border-radius: 8px;
  padding: 12px 25px; display: flex; align-items: center; gap: 10px;
  box-shadow: 0 0 20px rgba(0, 255, 204, 0.2);
  z-index: 10000; transition: transform 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275), opacity 0.4s;
  pointer-events: none; opacity: 0;
}
.cyber-toast.toast-visible {
  transform: translateX(-50%) translateY(0); opacity: 1;
}
.toast-icon { font-size: 18px; }
.toast-text { color: #00ffcc; font-size: 14px; font-family: 'Consolas'; letter-spacing: 0.5px; }
/* ====== 自定义赛博弹窗 ====== */
.custom-modal-overlay {
  position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
  background: rgba(0, 0, 0, 0.7); backdrop-filter: blur(5px);
  display: flex; justify-content: center; align-items: center; z-index: 9999;
  animation: fadeIn 0.2s ease-out;
}
.custom-modal {
  background: #0d0d0f; border: 1px solid #333; border-top: 2px solid #ff4d4f;
  padding: 30px; border-radius: 8px; width: 400px; text-align: center;
  box-shadow: 0 20px 50px rgba(0,0,0,0.8);
  animation: slideUp 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
}
.modal-icon { font-size: 32px; margin-bottom: 15px; }
.modal-title { color: #fff; font-size: 18px; margin-bottom: 10px; font-weight: normal; letter-spacing: 1px; }
.modal-desc { color: #888; font-size: 13px; line-height: 1.6; margin-bottom: 25px; }
.highlight-text { color: #00ffcc; }
.warning-text { color: #ff4d4f; font-size: 12px; display: block; margin-top: 8px; }
.modal-actions { display: flex; gap: 15px; justify-content: center; }
.modal-actions button {
  padding: 8px 25px; border: none; border-radius: 4px; font-family: 'Consolas';
  font-size: 13px; cursor: pointer; transition: all 0.2s;
}
.btn-cancel { background: rgba(255,255,255,0.05); color: #ccc; border: 1px solid #444; }
.btn-cancel:hover { background: rgba(255,255,255,0.1); color: #fff; }
.btn-confirm { background: rgba(255, 77, 79, 0.1); color: #ff4d4f; border: 1px solid rgba(255, 77, 79, 0.4); }
.btn-confirm:hover { background: #ff4d4f; color: #000; box-shadow: 0 0 15px rgba(255, 77, 79, 0.4); }

@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
@keyframes slideUp { from { transform: translateY(20px) scale(0.95); opacity: 0; } to { transform: translateY(0) scale(1); opacity: 1; } }
</style>
<style>
/* 🚨 绝对暴力重置：消灭一切原生边距和外层滚动条 */
html, body, #app {
  margin: 0 !important;
  padding: 0 !important;
  width: 100vw;
  height: 100vh;
  overflow: hidden; /* 锁死根节点的滚动，滚动只在内部容器发生 */
}
/* 强制所有元素的边框和内边距计算在宽度内，防止撑爆容器 */
* {
  box-sizing: border-box;
}
/* 隐藏部分浏览器默认的聚焦外框，提升极客质感 */
*:focus {
  outline: none;
}
</style>