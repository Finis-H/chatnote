<template>
  <div class="music-panel" :class="{ 'immersive': isImmersive, 'mini': !isImmersive }">
    
    <audio ref="audioPlayer"  
           crossorigin="anonymous"
           :src="currentTrack?.url ? getFullUrl(currentTrack.url) : undefined" 
           @timeupdate="onTimeUpdate" 
           @ended="onTrackEnded"
           @playing="onPlaying"
           @error="onAudioError"></audio>

    <div v-if="!isImmersive" class="dock-icon-mode" title="点击展开音乐沉浸控制台" @click="isImmersive = true">
      <div class="album-art dock-art" :class="{ rotating: isPlaying }">
        <img :src="currentTrack?.cover_url ? getFullUrl(currentTrack.cover_url) : defaultCover" alt="Cover" />
      </div>
    </div>

    <div v-else class="immersive-mode-container">
      <div class="os-window-controls">
        <button class="win-btn shrink" @click="isImmersive = false" title="收起为迷你挂件">↘ 收起</button>
        <button class="win-btn close" @click="closePanel" title="彻底关闭">✖ 终止</button>
      </div>

      <div class="panel-body player-only">
        
        <div class="status-badge" v-if="sysMsg" :class="{'error': sysMsg.includes('🚨')}">{{ sysMsg }}</div>

        <div class="album-art-wrapper">
          <div class="album-art" :class="{ rotating: isPlaying }">
            <img :src="currentTrack?.cover_url ? getFullUrl(currentTrack.cover_url) : defaultCover" alt="Cover" />
          </div>
        </div>
        
        <div class="track-info">
          <h2 class="title">{{ currentTrack?.title || '等待指令介入' }}</h2>
          <p class="artist">{{ currentTrack?.artist || 'Vault OS Agent' }}</p>
          <div class="playlist-counter" v-if="playlist.length > 0">
            [ {{ currentIndex + 1 }} / {{ playlist.length }} ]
          </div>
        </div>
        
        <div class="controls-wrapper">
          <div class="controls">
            <button class="ctrl-btn sub-btn" @click="toggleLoopMode" :title="loopMode === 'list' ? '当前：列表循环' : '当前：单曲循环'">
              {{ loopMode === 'list' ? '🔁' : '🔂' }}
            </button>
            <button class="ctrl-btn sub-btn" @click="playPrev" :disabled="playlist.length <= 1">⏮</button>
            
            <button class="play-btn ctrl-btn" @click="togglePlay" :disabled="!currentTrack">{{ isPlaying ? '⏸' : '▶️' }}</button>
            
            <button class="ctrl-btn sub-btn" @click="playNext" :disabled="playlist.length <= 1">⏭</button>
            <button class="ctrl-btn sub-btn" style="opacity: 0; pointer-events: none;">🔁</button> </div>
          
          <div class="volume-control">
            <span>🔉</span>
            <input type="range" min="0" max="1" step="0.05" v-model="volume" @input="updateVolume" class="vol-slider" />
          </div>
        </div>

        <div class="progress-container">
          <div class="time">{{ formatTime(currentTime) }}</div>
          <div class="progress-bar" @click="seekAudio"><div class="fill" :style="{ width: progressPercent + '%' }"></div></div>
          <div class="time">{{ formatTime(duration) }}</div>
        </div>
      </div>

      <transition name="fade-slide">
        <div class="lyrics-area">
          <div class="lyric-scroll-container">
            <div class="lyric-content">
              <pre v-if="currentTrack?.lyrics" class="pure-lyrics">{{ currentTrack.lyrics }}</pre>
              <div v-else-if="currentTrack" class="lyric-line active">🎵 暂无歌词数据</div>
              <div v-else class="lyric-line active">等待 LLM 下发临时歌单...</div>
            </div>
          </div>
          <div v-if="currentTrack?.analysis" class="analysis-footer">
            💡 AI 意境解析：{{ currentTrack.analysis }}
          </div>
        </div>
      </transition>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue';
import { activeAgentComponent, isImmersive } from 'vault:useNeuroLink';
import { SystemConfig } from 'vault:useNeuroLink';

const props = defineProps({ isImmersive: Boolean });
const defaultCover = 'https://api.dicebear.com/7.x/shapes/svg?seed=vaultOS';

const audioPlayer = ref(null);
const isPlaying = ref(false);
const currentTime = ref(0);
const duration = ref(0);
const volume = ref(0.7);
const sysMsg = ref('');
const getFullUrl = (url) => {
  if (!url) return undefined;
  if (url.startsWith('http')) return url;
  return SystemConfig.API_BASE + url;
};
// 核心调度变量
const playlist = ref([]);
const currentIndex = ref(0);
const currentTrack = ref(null);
const loopMode = ref('list'); // 'list' 列表循环 | 'single' 单曲循环
let watchdogTimer = null; // 15秒探测狗

// ================= 核心播放逻辑 =================
const toggleLoopMode = () => { loopMode.value = loopMode.value === 'list' ? 'single' : 'list'; };

const attemptPlay = async () => {
  if (!audioPlayer.value || !currentTrack.value) return;
  
  await nextTick(); 
  audioPlayer.value.load();
  sysMsg.value = '缓冲中...';
  
  clearTimeout(watchdogTimer);
  watchdogTimer = setTimeout(() => {
    sysMsg.value = `🚨 [${currentTrack.value.title}] 链接失效，正在执行自动跳过与标记...`;
    markTrackDead(currentTrack.value.url);
    playNext(true); 
  }, 15000);

  audioPlayer.value.play().catch(e => {
    console.warn("🔊 音频播放指令异常:", e);
    // 核心保命机制：如果是浏览器拦截了自动播放 (NotAllowedError)，立刻取消 15 秒死刑判决！
    if (e.name === 'NotAllowedError') {
      clearTimeout(watchdogTimer); // 勒死探测狗！
      sysMsg.value = "⏸️ 浏览器拦截了自动播放，请手动点击播放按钮";
      isPlaying.value = false;
    }
  });
};

// 音频真正开始播放的回调
const onPlaying = () => {
  clearTimeout(watchdogTimer); // 缓冲成功，勒死探测狗
  isPlaying.value = true;
  sysMsg.value = '';
};

// 探测狗触发：向后端 API 提交失效标记
const markTrackDead = async (deadUrl) => {
  try {
    await fetch(`${SystemConfig.API_BASE}/api/plugins/music_agent/mark_dead`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: deadUrl })
    });
  } catch (e) { console.error("标记失效异常", e); }
};

// 切歌逻辑 (isForceSkip: 是否因为失效导致的强制切歌)
const playNext = (isForceSkip = false) => {
  if (playlist.value.length === 0) return;
  
  // 如果是正常播完且单曲循环，且不是因为失效强制跳过
  if (loopMode.value === 'single' && !isForceSkip) {
    audioPlayer.value.currentTime = 0;
    attemptPlay();
    return;
  }

  // 列表循环 / 强制切歌 / 手动下一首
  if (currentIndex.value < playlist.value.length - 1) {
    currentIndex.value++;
    currentTrack.value = playlist.value[currentIndex.value];
    attemptPlay();
  } else {
    // 到了歌单末尾
    if (isForceSkip) {
      // 如果最后一首也失效了，直接停止
      isPlaying.value = false;
      sysMsg.value = '临时歌单已耗尽，全部失效。';
    } else {
      // 列表循环回到第一首
      currentIndex.value = 0;
      currentTrack.value = playlist.value[0];
      attemptPlay();
    }
  }
};

const playPrev = () => {
  if (playlist.value.length === 0) return;
  if (audioPlayer.value && audioPlayer.value.currentTime > 3) {
    audioPlayer.value.currentTime = 0; // 如果播放超过3秒，点击上一首其实是重头播
    return;
  }
  currentIndex.value = currentIndex.value > 0 ? currentIndex.value - 1 : playlist.value.length - 1;
  currentTrack.value = playlist.value[currentIndex.value];
  attemptPlay();
};

const onTrackEnded = () => { playNext(false); };

const onAudioError = () => {
  // 如果当前没歌，或者根本没有加载 src，直接无视
  if (!currentTrack.value || !audioPlayer.value?.src || audioPlayer.value.src.endsWith('undefined')) {
    return;
  }

  // 核心修复 2：读取原生 DOM 的 MediaError 对象
  const err = audioPlayer.value.error;
  if (err && err.code === 1) {
    return; 
  }

  if (isPlaying.value || currentTrack.value) {
    clearTimeout(watchdogTimer);
    sysMsg.value = `🚨 资源加载失败 (Code: ${err ? err.code : '未知'})，自动跳过...`;
    markTrackDead(currentTrack.value.url);
    playNext(true);
  }
};
let lastPlaylistStr = "";
// ================= 事件接收与生命周期 =================
onMounted(() => {
  // 监听来自主程序的 "隔空投送" 歌单指令
  window.addEventListener('vpm_ws_music_agent', (e) => {
    const payload = e.detail;
    if (payload.type === 'play_playlist') {
      const currentStr = JSON.stringify(payload.playlist);
      if (currentStr === lastPlaylistStr) return; 
      lastPlaylistStr = currentStr;
      setTimeout(() => { lastPlaylistStr = ""; }, 4000);

      const newPlaylist = payload.playlist;
      if (newPlaylist && newPlaylist.length > 0) {
        playlist.value = newPlaylist;
        currentIndex.value = 0;
        currentTrack.value = playlist.value[0];
        sysMsg.value = `已接收系统下发的 ${newPlaylist.length} 首临时资产...`;
        
        setTimeout(attemptPlay, 100);
      }
    }
  });
});

onBeforeUnmount(() => {
  clearTimeout(watchdogTimer);
  if (audioPlayer.value) {
    audioPlayer.value.pause();
    // 组件卸载时释放音频资源，避免后台占用。
    audioPlayer.value.removeAttribute('src');
    audioPlayer.value.load();
  }
});

// ================= 基础UI交互 =================
const progressPercent = computed(() => duration.value ? (currentTime.value / duration.value) * 100 : 0);
const togglePlay = () => {
  if (!audioPlayer.value) return;
  if (isPlaying.value) { audioPlayer.value.pause(); isPlaying.value = false; } 
  else { attemptPlay(); }
};
const onTimeUpdate = () => {
  if (audioPlayer.value) {
    currentTime.value = audioPlayer.value.currentTime;
    duration.value = audioPlayer.value.duration || 0;
  }
};
const seekAudio = (e) => {
  if (!audioPlayer.value || !duration.value) return;
  const rect = e.currentTarget.getBoundingClientRect();
  audioPlayer.value.currentTime = (e.clientX - rect.left) / rect.width * duration.value;
};
const updateVolume = () => { if (audioPlayer.value) audioPlayer.value.volume = volume.value; };
const formatTime = (t) => {
  if (!t || isNaN(t)) return "00:00";
  return `${Math.floor(t / 60).toString().padStart(2, '0')}:${Math.floor(t % 60).toString().padStart(2, '0')}`;
};
const closePanel = () => {
  if (audioPlayer.value) {
    audioPlayer.value.pause();
    // 核心拔管操作：清空数据源并强制重载，彻底释放后端的 HTTP Socket
    audioPlayer.value.removeAttribute('src'); 
    audioPlayer.value.load(); 
  }
  activeAgentComponent.value = null;
  isImmersive.value = false; 
};
</script>

<style scoped>
/* 容器基础样式 */
.music-panel { display: flex; flex-direction: column; height: 100%; color: #fff; position: relative;}
.music-panel.immersive { 
  padding: 40px; 
  background: linear-gradient(135deg, #0d0d12 0%, #16213e 100%); 
  min-height: 500px; /* 强制保底高度，防止非最大化时坍塌 */
  height: 100%;
}
.music-panel.mini { padding: 0; background: transparent; height: 65px; flex: none; }

.dock-icon-mode { display: flex; justify-content: center; align-items: center; width: 100%; height: 100%; cursor: pointer; }
.dock-icon-mode .album-art { width: 45px !important; height: 45px !important; border-width: 2px !important; flex-shrink: 0; transition: all 0.2s;}
.dock-icon-mode:hover .album-art { transform: scale(1.15); box-shadow: 0 0 15px rgba(0, 255, 204, 0.8); }

.immersive-mode-container { 
  display: grid; 
  grid-template-columns: 1fr 1.2fr; 
  gap: 40px; /* 缩小间距以适配较小窗口 */
  align-items: start; /* 改为顶部对齐，防止垂直居中在小窗口失效 */
  height: 100%; 
  padding-top: 40px;
}
.os-window-controls { position: absolute; top: 20px; right: 20px; display: flex; gap: 10px; z-index: 10; }
.win-btn { background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2); color: #ccc; border-radius: 4px; padding: 6px 15px; font-size: 13px; cursor: pointer; transition: all 0.2s; }
.win-btn:hover { background: rgba(255,255,255,0.2); color: #fff; }
.win-btn.close:hover { background: rgba(255, 74, 74, 0.3); border-color: #ff4a4a; color: #ff4a4a; }

.panel-body.player-only { 
  display: flex; 
  flex-direction: column; 
  align-items: center; 
  justify-content: flex-start; /*  取消 center 居中，防止内容在小窗口下被两头裁切 */
  position: relative;
  height: 100%;
}
.status-badge { position: absolute; top: -20px; background: rgba(0,255,204,0.1); color: #00ffcc; padding: 5px 15px; border-radius: 20px; font-size: 12px; border: 1px solid #00ffcc; z-index: 5;}
.status-badge.error { background: rgba(255,74,74,0.1); color: #ff4a4a; border-color: #ff4a4a; }

.album-art-wrapper { display: flex; justify-content: center; margin-bottom: 15px; margin-top: 10px; }
.album-art { width: 190px; height: 190px; border-radius: 50%; border: 8px solid #222; overflow: hidden; box-shadow: 0 10px 40px rgba(0,0,0,0.6); }
.album-art img { width: 100%; height: 100%; object-fit: cover; }
.rotating { animation: rotate 15s linear infinite; }
@keyframes rotate { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }

.track-info { text-align: center; margin-bottom: 15px; }
.title { margin: 0; font-size: 1.4rem; color: #fff; text-shadow: 0 0 15px rgba(0,255,204,0.4); letter-spacing: 1px;}
.artist { margin: 8px 0 0; color: #00ffcc; font-size: 0.9rem; opacity: 0.8;}
.playlist-counter { font-size: 12px; color: #555; margin-top: 10px; font-family: 'Consolas';}

.controls-wrapper { display: flex; flex-direction: column; align-items: center; gap: 15px; margin-bottom: 15px; width: 100%; }
.controls { display: flex; justify-content: center; align-items: center; gap: 20px;}
.ctrl-btn { background: none; border: none; cursor: pointer; display: flex; align-items: center; justify-content: center; transition: all 0.2s; }
.sub-btn { font-size: 20px; color: #888; padding: 10px;}
.sub-btn:hover:not(:disabled) { color: #00ffcc; transform: scale(1.1);}
.sub-btn:disabled { opacity: 0.3; cursor: not-allowed;}
.play-btn { width: 65px; height: 65px; border-radius: 50%; background: #00ffcc; color: #000; font-size: 28px; transition: transform 0.1s, box-shadow 0.2s; }
.play-btn:hover:not(:disabled) { box-shadow: 0 0 20px rgba(0,255,204,0.5); }
.play-btn:active:not(:disabled) { transform: scale(0.9); }
.play-btn:disabled { background: #333; color: #555;}

.volume-control { display: flex; align-items: center; gap: 10px; width: 60%; color: #888; font-size: 14px;}
.vol-slider { flex: 1; -webkit-appearance: none; appearance: none; height: 4px; background: #333; border-radius: 2px; outline: none; }
.vol-slider::-webkit-slider-thumb { -webkit-appearance: none; appearance: none; width: 12px; height: 12px; border-radius: 50%; background: #00ffcc; cursor: pointer; box-shadow: 0 0 10px rgba(0,255,204,0.5);}

.progress-container { 
  display: flex; 
  align-items: center; 
  gap: 15px; 
  font-size: 13px; 
  color: #888; 
  width: 90%; 
  margin-top: auto; 
  padding-bottom: 10px;
}
.progress-bar { flex: 1; height: 6px; background: #333; border-radius: 3px; cursor: pointer; overflow: hidden; position: relative; }
.progress-bar .fill { height: 100%; background: #00ffcc; transition: width 0.1s linear; }

.lyrics-area { 
  height: 100%; 
  display: flex; 
  flex-direction: column; 
  overflow: hidden; 
}
.lyric-scroll-container { 
  flex: 1; 
  overflow-y: auto; 
  padding-right: 15px;
  mask-image: linear-gradient(to bottom, transparent, black 10%, black 90%, transparent);
}
.pure-lyrics {
  font-size: 1.1rem;
  line-height: 1.8;
  color: #ccc;
  white-space: pre-wrap;
  font-family: inherit;
  text-align: left;
}
.analysis-footer {
  margin-top: 20px;
  font-size: 13px;
  color: #00ffcc;
  opacity: 0.7;
  padding: 15px;
  background: rgba(0,255,204,0.05);
  border-radius: 4px;
}
.lyric-scroll-container::-webkit-scrollbar { width: 4px; }
.lyric-scroll-container::-webkit-scrollbar-thumb { background: #333; border-radius: 10px; }
.lyric-line { font-size: 1.2rem; opacity: 0.4; transition: all 0.3s; line-height: 1.6;}
.lyric-line.active { font-size: 1.6rem; opacity: 1; color: #00ffcc; font-weight: normal; text-shadow: 0 0 20px rgba(0,255,204,0.2); }
</style>
