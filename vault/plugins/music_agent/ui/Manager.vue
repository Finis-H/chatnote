<template>
  <div class="floating-os-window" :style="windowStyle" @mousedown="bringToFront" :class="{ 'is-maximized': isMaximized }">
    <div class="pm-header" @mousedown="startDrag">
      <h2>音乐资产管理</h2>
      <div class="win-actions">
        <button class="pm-btn maximize-btn" @click.stop="toggleMaximize">
          {{ isMaximized ? '🗗' : '🗖' }}
        </button>
        <button class="pm-btn close-btn" @click.stop="$emit('close')">✖</button>
      </div>
    </div>

    <div class="pm-nav">
      <button :class="{ active: currentTab === 'list' }" @click="currentTab = 'list'">📋 资产库管理</button>
      <button :class="{ active: currentTab === 'add' }" @click="openAdd">📥 录入新资产</button>
      <button v-if="currentTab === 'edit'" class="active" style="color: #ffaa00;">✏️ 资产修改</button>
    </div>

    <div class="pm-body">
      <div v-if="currentTab === 'list'" class="list-view">
        <div class="table-container">
          <table class="cyber-table">
            <thead><tr><th>封面</th><th>曲目名称</th><th>艺术家</th><th>资产来源 (URL)</th><th style="min-width: 100px;">操作</th></tr></thead>
            <tbody>
              <tr v-for="track in trackList" :key="track.url">
                <td><img :src="track.cover_url ? getFullUrl(track.cover_url) : defaultCover" class="list-cover" /></td>
                <td :class="{'dead-link': track.title.includes('【失效】')}">{{ track.title }}</td>
                <td>{{ track.artist }}</td>
                <td class="url-cell" :title="track.url">{{ track.url }}</td>
                <td>
                  <template v-if="confirmingDelete === track.url">
                    <button class="action-btn text-red confirm-text" @click="deleteTrack(track.url)">确认删除</button>
                    <button class="action-btn text-gray" @click="confirmingDelete = null">取消</button>
                  </template>
                  <template v-else>
                    <button class="action-btn text-blue" @click="openEdit(track)" title="修改资产">✏️</button>
                    <button class="action-btn text-yellow" @click="markDead(track.url)" title="标记失效">⚠️</button>
                    <button class="action-btn text-red" @click="confirmingDelete = track.url" title="删除资产">🗑️</button>
                  </template>
                </td>
              </tr>
              <tr v-if="trackList.length === 0">
                <td colspan="5" style="text-align: center; color: #666; padding: 20px;">数字资产库为空，请先录入。</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div v-if="currentTab === 'add' || currentTab === 'edit'" class="add-view">
        <div class="form-grid">
          <div class="fg-left">
            <div class="form-group"><label>Track Name *</label><input v-model="formData.title" type="text" maxlength="50" /></div>
            <div class="form-group" v-if="currentTab === 'add'">
              <label>本地音频文件 (Audio File) *</label>
              <input type="file" @change="onAudioFileChange" accept="audio/mpeg, audio/wav, audio/flac, audio/aac" class="file-input audio-input" />
            </div>
            <div class="form-group" v-else>
              <label>Audio URL (主键锁定)</label>
              <input v-model="formData.url" type="text" disabled />
            </div>
            <div class="form-group">
              <label>本地封面图 (仅限一张)</label>
              
              <div v-if="currentTab === 'edit' && formData.cover_url && !coverFile" class="current-cover-preview">
                <img :src="formData.cover_url ? getFullUrl(formData.cover_url) : defaultCover" alt="Current Cover" />
                <span>当前存储的封面</span>
              </div>

              <input 
                type="file" 
                @change="onFileChange" 
                accept="image/png, image/jpeg, image/webp" 
                class="file-input" 
                title="点击上传新封面，将覆盖旧图片"
              />
            </div>
            <div class="form-group"><label>Artist</label><input v-model="formData.artist" type="text" maxlength="50" /></div>
            <div class="form-group"><label>Tags (逗号分隔)</label><input v-model="formData.tagsInput" type="text" maxlength="70" /></div>
          </div>
          <div class="fg-right">
            <div class="form-group" style="height: 50%;"><label>原曲歌词 (Lyrics)</label><textarea v-model="formData.lyrics" maxlength="1000"></textarea></div>
            <div class="form-group" style="height: 50%;"><label>歌曲解析 (Analysis)</label><textarea v-model="formData.analysis" maxlength="300"></textarea></div>
          </div>
        </div>
        <div class="form-actions">
          <span class="sys-msg" :class="{'error': sysMsg.includes('🚨')}">{{ sysMsg }}</span>
          <button class="cyber-submit-btn" @click="submitForm" :disabled="isSubmitting">{{ isSubmitting ? '保存中...' : (currentTab === 'edit' ? '提交修改' : '提交入库') }}</button>
        </div>
      </div>
    </div>
    
    <div v-show="!isMaximized" class="resize-handle" @mousedown="startResize"></div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import { SystemConfig } from 'vault:useNeuroLink';

// OS 视窗交互：拖拽、缩放与最大化
const winPos = ref({ x: window.innerWidth/2 - 400, y: window.innerHeight/2 - 300 });
const winSize = ref({ w: 800, h: 600 });
const zIndex = ref(9999);
const isMaximized = ref(false);

const windowStyle = computed(() => {
  if (isMaximized.value) {
    return { left: '20px', top: '20px', width: 'calc(100vw - 40px)', height: 'calc(100vh - 40px)', zIndex: zIndex.value };
  }
  return { left: `${winPos.value.x}px`, top: `${winPos.value.y}px`, width: `${winSize.value.w}px`, height: `${winSize.value.h}px`, zIndex: zIndex.value };
});
const getFullUrl = (url) => {
  if (!url) return '';
  if (url.startsWith('http')) return url;
  return SystemConfig.API_BASE + url;
};
const toggleMaximize = () => { isMaximized.value = !isMaximized.value; };
const bringToFront = () => { zIndex.value = 10000; };

// 拖拽逻辑 (最大化时禁用)
let isDragging = false, startX, startY, initX, initY;
const startDrag = (e) => {
  if(e.target.tagName === 'BUTTON' || isMaximized.value) return;
  isDragging = true; startX = e.clientX; startY = e.clientY;
  initX = winPos.value.x; initY = winPos.value.y;
  document.addEventListener('mousemove', onDrag);
  document.addEventListener('mouseup', stopDrag);
};
const onDrag = (e) => {
  if(!isDragging) return;
  winPos.value.x = initX + (e.clientX - startX);
  winPos.value.y = initY + (e.clientY - startY);
};
const stopDrag = () => { isDragging = false; document.removeEventListener('mousemove', onDrag); document.removeEventListener('mouseup', stopDrag); };

// 缩放逻辑
let isResizing = false, initW, initH;
const startResize = (e) => {
  isResizing = true; startX = e.clientX; startY = e.clientY;
  initW = winSize.value.w; initH = winSize.value.h;
  document.addEventListener('mousemove', onResize);
  document.addEventListener('mouseup', stopResize);
  e.preventDefault();
};
const onResize = (e) => {
  if(!isResizing) return;
  winSize.value.w = Math.max(600, initW + (e.clientX - startX));
  winSize.value.h = Math.max(400, initH + (e.clientY - startY));
};
const stopResize = () => { isResizing = false; document.removeEventListener('mousemove', onResize); document.removeEventListener('mouseup', stopResize); };

// === 业务逻辑 ===
const currentTab = ref('list');
const defaultCover = 'https://api.dicebear.com/7.x/shapes/svg?seed=vaultOS';
const trackList = ref([]);
const confirmingDelete = ref(null); // 删除确认状态机
const formData = ref({ title: '', url: '', artist: '', tagsInput: '', lyrics: '', analysis: '' });
const coverFile = ref(null);
const audioFile = ref(null);
const onAudioFileChange = (e) => { 
  if (e.target.files.length > 0) audioFile.value = e.target.files[0]; 
};
const isSubmitting = ref(false);
const sysMsg = ref('');

const fetchList = async () => {
  try {
    const res = await fetch(`${SystemConfig.API_BASE}/api/plugins/music_agent/list`);
    const data = await res.json();
    if (res.ok) trackList.value = data.data;
  } catch (e) { console.error("拉取列表失败", e); }
};

const openAdd = () => {
  formData.value = { title: '', url: '', artist: '', tagsInput: '', lyrics: '', analysis: '' };
  coverFile.value = null; 
  audioFile.value = null; // 重置
  sysMsg.value = ''; 
  currentTab.value = 'add';
};

const openEdit = (track) => {
  formData.value = { ...track, tagsInput: track.tags_raw };
  coverFile.value = null; sysMsg.value = ''; currentTab.value = 'edit';
};

const onFileChange = (e) => { if (e.target.files.length > 0) coverFile.value = e.target.files[0]; };

const submitForm = async () => {
  if (!formData.value.title) { sysMsg.value = "🚨 缺少曲目名称"; return; }
  if (currentTab.value === 'add' && !audioFile.value) { sysMsg.value = "🚨 必须上传本地音频文件"; return; }
  isSubmitting.value = true;
  
  const fd = new FormData();
  fd.append('title', formData.value.title); 
  fd.append('artist', formData.value.artist); 
  fd.append('tagsInput', formData.value.tagsInput);
  fd.append('lyrics', formData.value.lyrics); 
  fd.append('analysis', formData.value.analysis);
  if (coverFile.value) fd.append('cover_file', coverFile.value);
  if (currentTab.value === 'add') {
    fd.append('audio_file', audioFile.value);
  } else {
    fd.append('url', formData.value.url);
  }

  const endpoint = currentTab.value === 'edit' ? '/update' : '/add';
  
  try {
    const res = await fetch(`${SystemConfig.API_BASE}/api/plugins/music_agent${endpoint}`, { method: 'POST', body: fd });
    if (!res.ok) throw new Error((await res.json()).detail || "API 拒绝");
    sysMsg.value = currentTab.value === 'edit' ? "✅ 修改已保存！" : "✅ 资产已入库！";
    fetchList();
    setTimeout(() => { currentTab.value = 'list'; sysMsg.value = '';}, 1000);
  } catch (e) { sysMsg.value = "🚨 " + e.message; }
  finally { isSubmitting.value = false; }
};

const deleteTrack = async (url) => {
  try {
    await fetch(`${SystemConfig.API_BASE}/api/plugins/music_agent/delete?url=${encodeURIComponent(url)}`, { method: 'DELETE' });
    confirmingDelete.value = null;
    fetchList();
  } catch (e) { alert("删除失败"); }
};

const markDead = async (url) => {
  try {
    await fetch(`${SystemConfig.API_BASE}/api/plugins/music_agent/mark_dead`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ url }) });
    fetchList();
  } catch (e) { alert("标记失败"); }
};

onMounted(() => { fetchList(); });
</script>

<style scoped>
.floating-os-window { position: fixed; background: rgba(15, 15, 18, 0.95); backdrop-filter: blur(10px); border: 1px solid #333; border-radius: 8px; box-shadow: 0 20px 50px rgba(0,0,0,0.8); display: flex; flex-direction: column; overflow: hidden; font-family: system-ui, sans-serif; transition: width 0.3s cubic-bezier(0.25, 1, 0.5, 1), height 0.3s cubic-bezier(0.25, 1, 0.5, 1), top 0.3s, left 0.3s;}
.floating-os-window.is-maximized { border-radius: 0; box-shadow: none; border: 1px solid #00ffcc; }
.resize-handle { position: absolute; right: 0; bottom: 0; width: 15px; height: 15px; cursor: nwse-resize; background: linear-gradient(135deg, transparent 50%, #555 50%); }

.pm-header { display: flex; justify-content: space-between; align-items: center; padding: 15px 20px; border-bottom: 1px solid #222; cursor: grab; background: rgba(0,0,0,0.4); user-select: none;}
.pm-header:active { cursor: grabbing; }
.pm-header h2 { margin: 0; font-size: 1.1rem; color: #00ffcc; pointer-events: none;}
.win-actions { display: flex; gap: 8px;}
.pm-btn { background: none; border: none; color: #aaa; font-size: 16px; cursor: pointer; transition: color 0.2s;}
.pm-btn.close-btn:hover { color: #ff4a4a; }
.pm-btn.maximize-btn:hover { color: #00ffcc; }

.pm-nav { display: flex; gap: 20px; padding: 0 30px; border-bottom: 1px solid #222; background: #0a0a0c;}
.pm-nav button { background: none; border: none; color: #666; padding: 12px 5px; cursor: pointer; font-size: 14px; position: relative;}
.pm-nav button.active { color: #00ffcc; font-weight: bold; }
.pm-nav button.active::after { content: ''; position: absolute; bottom: -1px; left: 0; width: 100%; height: 2px; background: currentColor; }

.pm-body { flex: 1; overflow-y: auto; padding: 25px; }

/* 列表样式 */
.table-container { background: #16161a; border: 1px solid #222; border-radius: 8px; overflow: hidden; }
.cyber-table { width: 100%; border-collapse: collapse; text-align: left; font-size: 13px;}
.cyber-table th { background: #0f0f12; color: #888; padding: 12px 15px; border-bottom: 1px solid #222; font-weight: normal;}
.cyber-table td { padding: 10px 15px; border-bottom: 1px solid #222; vertical-align: middle;}
.cyber-table tr:hover { background: rgba(0, 255, 204, 0.05); }
.list-cover { width: 40px; height: 40px; border-radius: 4px; object-fit: cover; border: 1px solid #333;}
.url-cell { max-width: 150px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: #555; }
.dead-link { color: #ff4a4a; text-decoration: line-through; }

/* 动作按钮 */
.action-btn { background: none; border: none; cursor: pointer; font-size: 15px; opacity: 0.6; padding: 5px;}
.action-btn:hover { opacity: 1; transform: scale(1.1); }
.confirm-text { font-size: 12px; border: 1px solid #ff4a4a; padding: 3px 6px; border-radius: 4px; background: rgba(255,74,74,0.1); font-family: 'Consolas';}
.text-gray { font-size: 12px; color: #aaa; }

/* 表单样式 */
.add-view { height: 100%; display: flex; flex-direction: column; }
.form-grid { display: flex; gap: 30px; flex: 1; }
.fg-left, .fg-right { flex: 1; display: flex; flex-direction: column; gap: 15px; }
.form-group { display: flex; flex-direction: column; gap: 8px; }
.form-group label { font-size: 12px; color: #888; }
.form-group input[type="text"], .form-group textarea { background: #16161a; border: 1px solid #333; color: #fff; padding: 10px; border-radius: 4px; outline: none; }
.form-group input:focus, .form-group textarea:focus { border-color: #00ffcc; }
.form-group input:disabled { opacity: 0.5; cursor: not-allowed; }
.form-group textarea { flex: 1; resize: none; font-family: inherit;}
.file-input { background: #16161a; border: 1px dashed #444; padding: 15px; text-align: center; border-radius: 4px; color: #aaa; cursor: pointer;}

.form-actions { margin-top: 20px; display: flex; justify-content: space-between; align-items: center; padding-top: 20px; border-top: 1px solid #222;}
.sys-msg { font-size: 13px; color: #00ffcc; }
.sys-msg.error { color: #ff4a4a; }
.cyber-submit-btn { background: #00ffcc; color: #000; font-weight: bold; padding: 10px 30px; border: none; border-radius: 4px; cursor: pointer;}
.cyber-submit-btn:active { transform: scale(0.95); }
.cyber-submit-btn:disabled { background: #555; color: #888; cursor: not-allowed;}

.current-cover-preview {
  display: flex;
  align-items: center;
  gap: 15px;
  background: #1a1a1e;
  padding: 10px;
  border-radius: 4px;
  margin-bottom: 10px;
}
.current-cover-preview img {
  width: 60px;
  height: 60px;
  border-radius: 4px;
  object-fit: cover;
  border: 1px solid #333;
}
.current-cover-preview span {
  font-size: 12px;
  color: #888;
}
</style>
