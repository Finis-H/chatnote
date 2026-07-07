import requests
import random
import json
import sys
import os
import time
import shutil
import zipfile
import re

from core_bus import event_bus
from openai import OpenAI
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks, Request, Response
from fastapi.responses import FileResponse
from sqlmodel import SQLModel, Field, Session, select
from typing import Optional, List
from main import VAULT_ROOT

# 1. 纯净版物理表模型 (彻底移除 mood，扩容多模态字段)
class MusicTrack(SQLModel, table=True):
    __tablename__ = "vpm_plugin_music_tracks"
    url: str = Field(primary_key=True, max_length=250)
    title: str = Field(max_length=50)
    artist: str = Field(max_length=50)
    cover_url: str = Field(default="") 
    tags_raw: str = Field(default="", max_length=70) 
    lyrics: str = Field(default="", max_length=1000) 
    analysis: str = Field(default="", max_length=300) 

GENERIC_MUSIC_QUERY_PREFIXES = [
    "请帮我", "帮我", "给我", "我想", "想要", "想听", "我要", "来点", "来首",
    "播放一首", "播放首", "播放", "放一首", "放首", "放点", "放", "听一首", "听首", "听",
]
GENERIC_MUSIC_QUERY_SUFFIXES = [
    "类型的歌曲", "类型音乐", "类型的歌", "歌曲听", "音乐听", "的歌曲", "的音乐", "的歌",
    "歌曲", "音乐", "歌",
]
MUSIC_QUERY_SYNONYMS = {
    "情歌": ["爱情", "恋爱", "感情"],
    "爱情": ["情歌", "恋爱", "感情"],
    "伤感": ["难过", "失恋", "遗憾"],
    "快乐": ["开心", "欢快", "愉快"],
    "治愈": ["温柔", "安静", "放松"],
    "rap": ["说唱"],
    "说唱": ["rap"],
}


def _compact_music_query(value: str) -> str:
    return "".join(re.findall(r"[\u4e00-\u9fffA-Za-z0-9]+", str(value or "").lower()))


def _strip_generic_music_words(value: str) -> str:
    text = _compact_music_query(value)
    changed = True
    while changed and text:
        changed = False
        for prefix in GENERIC_MUSIC_QUERY_PREFIXES:
            if text.startswith(prefix):
                text = text[len(prefix):]
                changed = True
        for suffix in GENERIC_MUSIC_QUERY_SUFFIXES:
            if text.endswith(suffix) and len(text) > len(suffix):
                text = text[:-len(suffix)]
                changed = True
    return text


def _music_query_terms(query: str) -> list[str]:
    terms = []
    for term in (_compact_music_query(query), _strip_generic_music_words(query)):
        if term and term not in terms:
            terms.append(term)
        for synonym in MUSIC_QUERY_SYNONYMS.get(term, []):
            if synonym not in terms:
                terms.append(synonym)
    return terms


def _music_track_field(track, field_name: str) -> str:
    return str(getattr(track, field_name, "") or "").lower()


def _score_music_track(track, terms: list[str]) -> tuple[int, list[str]]:
    score = 0
    reasons = []
    weighted_fields = [
        ("title", 100, "歌名"),
        ("artist", 90, "歌手"),
        ("tags_raw", 70, "标签"),
        ("analysis", 45, "词意解析"),
        ("lyrics", 20, "歌词"),
    ]
    for term in terms:
        for field_name, weight, label in weighted_fields:
            field_value = _music_track_field(track, field_name)
            if term and term in field_value:
                score += weight
                if label not in reasons:
                    reasons.append(label)
    return score, reasons


def select_music_tracks(valid_tracks, query: str, limit: int = 10):
    terms = _music_query_terms(query)
    if not terms:
        selection = random.sample(valid_tracks, min(len(valid_tracks), limit))
        return selection, {"terms": [], "match_source": "random", "candidate_count": len(valid_tracks)}

    ranked = []
    for index, track in enumerate(valid_tracks):
        score, reasons = _score_music_track(track, terms)
        if score > 0:
            ranked.append((score, index, track, reasons))
    ranked.sort(key=lambda item: (-item[0], item[1]))
    selection = [item[2] for item in ranked[:limit]]
    reason_labels = []
    for _score, _index, _track, reasons in ranked:
        for reason in reasons:
            if reason not in reason_labels:
                reason_labels.append(reason)
    return selection, {
        "terms": terms,
        "match_source": "、".join(reason_labels) if reason_labels else "none",
        "candidate_count": len(ranked),
    }

CURRENT_DIR = os.path.join(VAULT_ROOT, "plugins", "music_agent")
router = APIRouter()
engine = None
COVERS_DIR = os.path.join(CURRENT_DIR, "covers")
AUDIO_DIR = os.path.join(CURRENT_DIR, "audio")
KNOWLEDGE_DIR = os.path.join(CURRENT_DIR, "knowledge")

def init_plugin(app_engine):
    global engine
    engine = app_engine
    SQLModel.metadata.create_all(engine)
    # 自动创建本地封面图床目录
    os.makedirs(COVERS_DIR, exist_ok=True)
    os.makedirs(AUDIO_DIR, exist_ok=True)
    os.makedirs(KNOWLEDGE_DIR, exist_ok=True)
    print(" [Music Agent] V2 数据库与本地图床已就绪！")
# 暴露本地音频的串流路由
@router.get("/audio/{filename}")
async def get_audio(request: Request, filename: str):
    file_path = os.path.join(AUDIO_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Audio not found")

    file_size = os.path.getsize(file_path)
    range_header = request.headers.get("Range")

    # 如果 Chromium 带着切片请求头来，我们必须按规矩返回 206 切片！
    if range_header:
        byte_range = range_header.replace("bytes=", "").split("-")
        start = int(byte_range[0])
        end = int(byte_range[1]) if byte_range[1] else file_size - 1
        chunk_size = end - start + 1
        
        with open(file_path, "rb") as f:
            f.seek(start)
            data = f.read(chunk_size)
            
        headers = {
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(chunk_size),
            "Content-Type": "audio/mpeg",
        }
        return Response(content=data, status_code=206, headers=headers)
    else:
        # 如果是普通请求，正常返回
        return FileResponse(file_path, media_type="audio/mpeg")
# 插件自带图床路由！
# 把图片存进插件目录，并通过这个接口暴露给前端，完美继承 server.py 的 CORS 跨域放行机制！
@router.get("/covers/{filename}")
async def get_cover(filename: str):
    file_path = os.path.join(COVERS_DIR, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path)
    raise HTTPException(status_code=404, detail="Cover not found")
# 接收 FormData 表单（支持图片+文本混合上传）
@router.post("/add")
async def add_music_track(
    background_tasks: BackgroundTasks,
    title: str = Form(...),
    artist: str = Form("未知"),
    tagsInput: str = Form(""),
    lyrics: str = Form(""),
    analysis: str = Form(""),
    cover_file: UploadFile = File(None),
    audio_file: UploadFile = File(...) 
):
    if not engine: raise HTTPException(status_code=500, detail="引擎未初始化")

    title = title.replace('"', "'")[:50]
    artist = artist.replace('"', "'")[:50]
    lyrics = lyrics[:1000]
    analysis = analysis[:300]
    tags_list = [t.strip() for t in tagsInput.split(',') if t.strip()]
    tags_raw = ",".join(tags_list)[:70]

    timestamp = int(time.time())

    # --- 1. 物理保存音频文件并生成主键 URL ---
    if not audio_file or not audio_file.filename:
        raise HTTPException(status_code=400, detail="必须上传音频文件")
    
    audio_ext = os.path.splitext(audio_file.filename)[1] or '.mp3'
    safe_audio_name = f"track_{timestamp}{audio_ext}"
    audio_save_path = os.path.join(AUDIO_DIR, safe_audio_name)
    
    with open(audio_save_path, "wb") as buffer:
        shutil.copyfileobj(audio_file.file, buffer)
        
    generated_url = f"/api/plugins/music_agent/audio/{safe_audio_name}"
    # --- 2. 物理保存封面图片 ---
    cover_url_db = ""
    if cover_file and cover_file.filename:
        cover_ext = os.path.splitext(cover_file.filename)[1] or '.jpg'
        safe_cover_name = f"cover_{timestamp}{cover_ext}"
        cover_save_path = os.path.join(COVERS_DIR, safe_cover_name)
        with open(cover_save_path, "wb") as buffer:
            shutil.copyfileobj(cover_file.file, buffer)
        cover_url_db = f"/api/plugins/music_agent/covers/{safe_cover_name}"

    try:
        # --- 3. 写入 SQLite ---
        with Session(engine) as session:
            new_track = MusicTrack(
                url=generated_url, title=title, artist=artist, cover_url=cover_url_db,
                tags_raw=tags_raw, lyrics=lyrics, analysis=analysis
            )
            session.add(new_track)
            session.commit()

        # --- 4. 生成 Markdown 资产 ---
        safe_title = "".join(c for c in title if c.isalnum() or c in " -_")
        file_name = f"music_{timestamp}_{safe_title}.md"
        file_path = os.path.join(KNOWLEDGE_DIR, file_name)

        md_content = f"""---
title: "{title}"
artist: "{artist}"
tags: {tags_list}
url: "{generated_url}"
cover_url: "{cover_url_db}"
created_at: {timestamp}
---
# {title}
*(Vault OS - Music Agent V2)*

## 原曲歌词 (Lyrics)
{lyrics if lyrics else '暂无歌词'}

## 歌曲解析 (Analysis)
{analysis if analysis else '暂无解析'}
"""
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(md_content)
            
        # 触发后台 Agent 解析任务
        if len(analysis) < 20 and len(lyrics) >= 20:
            background_tasks.add_task(agent_analyze_lyrics, generated_url, lyrics, file_path)

        return {"status": "success", "id": generated_url, "file": file_name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.get("/list")
async def get_music_list():
    """拉取全部音乐资产"""
    if not engine: raise HTTPException(status_code=500, detail="引擎未初始化")
    with Session(engine) as session:
        tracks = session.exec(select(MusicTrack)).all()
        return {"status": "success", "data": tracks}

@router.delete("/delete")
async def delete_music_track(url: str):
    """删除曲目资产：SQLite + 本地音频 + 本地封面 + Markdown 记录 + RAG 向量记录"""
    if not engine: raise HTTPException(status_code=500, detail="引擎未初始化")
    import requests # 确保发通知能用到
    
    with Session(engine) as session:
        track = session.exec(select(MusicTrack).where(MusicTrack.url == url)).first()
        if not track:
            raise HTTPException(status_code=404, detail="未找到该曲目")

        # --- 1. 删除本地封面图 ---
        if track.cover_url:
            cover_filename = track.cover_url.split("/")[-1]
            cover_path = os.path.join(COVERS_DIR, cover_filename)
            if os.path.exists(cover_path):
                os.remove(cover_path)
                print(f" [Music Agent] 封面已删除: {cover_filename}")

        # --- 2. 删除本地音频文件 ---
        if track.url:
            audio_filename = track.url.split("/")[-1]
            audio_path = os.path.join(AUDIO_DIR, audio_filename)
            if os.path.exists(audio_path):
                os.remove(audio_path)
                print(f" [Music Agent] 音轨已删除: {audio_filename}")

        # --- 3. 删除 Markdown 资产，并通知主系统清理向量记录 ---
        if os.path.exists(KNOWLEDGE_DIR):
            for filename in os.listdir(KNOWLEDGE_DIR):
                if filename.endswith(".md"):
                    filepath = os.path.join(KNOWLEDGE_DIR, filename)
                    with open(filepath, "r", encoding="utf-8") as f:
                        content = f.read()
                        
                    # 只要 Markdown 文件的 frontmatter 里包含这个唯一主键 URL，就是它。
                    if track.url in content:
                        os.remove(filepath)
                        print(f" [Music Agent] 知识库资产已删除: {filename}")
                        
                        # 向主系统 RAG 网关请求删除该来源的向量记录。
                        try:
                            token_path = os.path.join(VAULT_ROOT, ".run_token")
                            security_token = ""
                            if os.path.exists(token_path):
                                with open(token_path, "r", encoding="utf-8") as tf:
                                    security_token = tf.read().strip()
                            actual_port = "8000"
                            port_path = os.path.join(VAULT_ROOT, ".server_port")
                            if os.path.exists(port_path):
                                with open(port_path, "r", encoding="utf-8") as pf:
                                    actual_port = pf.read().strip()
                            rag_url = f"http://127.0.0.1:{actual_port}/api/rag/ingest"
                                    
                            # 【精妙设计】：通过发送一个空的 payload 数组，利用主引擎逻辑触发彻底注销
                            rag_payload = {
                                "command": "RAG_UPSERT",
                                "source_file": filepath,
                                "hash": "delete_hash", 
                                "payload": [] 
                            }
                            headers = {"Authorization": f"Bearer {security_token}"}
 
                            def _notify_rag():
                                try:
                                    resp = requests.post(rag_url, json=rag_payload, headers=headers, timeout=10)
                                    if resp.status_code == 200:
                                        print("✅ [记忆切除] 已成功通知主系统 ChromaDB 擦除相关的多维向量！")
                                except Exception as rag_e:
                                    print(f"🚨 [记忆切除] 向量擦除通知发送失败: {rag_e}")
                            
                            import threading
                            threading.Thread(target=_notify_rag).start()
                            print("✅ [记忆切除] 已向主系统发送后台擦除指令，前端物理秒删！")
                            
                            break
                        except Exception as rag_e:
                            print(f"🚨 [记忆切除] 向量擦除通知发送失败: {rag_e}")
                            
                        break # 找到了就跳出循环

        # --- 4. 数据库抹除 ---
        session.delete(track)
        session.commit()
        return {"status": "success"}
    
@router.post("/mark_dead")
async def mark_music_dead(payload: dict):
    """标记 URL 失效"""
    url = payload.get("url")
    if not engine: raise HTTPException(status_code=500, detail="引擎未初始化")
    with Session(engine) as session:
        track = session.exec(select(MusicTrack).where(MusicTrack.url == url)).first()
        if not track:
            raise HTTPException(status_code=404, detail="未找到该曲目")
        
        # 在标题前追加失效标识
        if "【失效】" not in track.title:
            track.title = f"【失效】{track.title}"
            session.add(track)
            session.commit()
        return {"status": "success", "new_title": track.title}

def agent_analyze_lyrics(url: str, lyrics: str, md_file_path: str):
    """独立的微型 Agent：后台调用 LLM 解析歌词、双写更新、并自主投喂 RAG 向量库"""
    try:
        # 1. 微服务级解耦：自己去读取系统的 config
        config_path = os.path.join(VAULT_ROOT, "system_config.json")
        if not os.path.exists(config_path):
            print("🚨 [Music Agent] 找不到系统配置，取消后台解析。")
            return
            
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
            
        api_key = config.get("api_key")
        if not api_key:
            print("🚨 [Music Agent] API Key 未配置，取消后台解析。")
            return

        base_url = config.get("base_url")
        client_kwargs = {"api_key": api_key}
        if base_url and base_url.strip():
            client_kwargs["base_url"] = base_url.strip()

        client = OpenAI(**client_kwargs)

        prompt = f"""
        你是一个拥有极高音乐审美和共情能力的 Vault OS 专属音乐解析 Agent。
        请对以下歌词进行赏析：
        1. 如果歌词不是中文，请先简要翻译其核心段落。
        2. 从适配心情、歌词的意象角度进行深度解析。
        3. 必须精简克制，严格限制在 300 字以内。不要输出任何 Markdown 格式，直接输出纯文本。
        
        【歌词内容】：
        {lyrics}
        """
        
        print(f"🧠 [Music Agent] 正在后台解析歌曲意境: {url} ...")
        response = client.chat.completions.create(
            model=config.get("model_mini", "qwen-turbo"),
            messages=[{"role": "user", "content": prompt}],
            timeout=20
        )
        
        analysis_result = response.choices[0].message.content.strip()
        print(f"✅ [Music Agent] 解析完成！生成了 {len(analysis_result)} 字的意境摘要。")

        # ==================== 数据落盘与 RAG 投喂 ====================
        track_title = "未知"
        track_artist = "未知"
        track_tags = ""
        # 2. 更新 SQLite 数据库，并提取元数据用于组装 RAG 切片
        with Session(engine) as session:
            track = session.exec(select(MusicTrack).where(MusicTrack.url == url)).first()
            if track:
                track.analysis = analysis_result
                track_title = track.title
                track_artist = track.artist
                track_tags = track.tags_raw
                session.add(track)
                session.commit()

        # 3. 物理覆写 Markdown 文件
        if os.path.exists(md_file_path):
            with open(md_file_path, "r", encoding="utf-8") as f:
                content = f.read()
            new_content = content.replace("暂无解析", analysis_result)
            with open(md_file_path, "w", encoding="utf-8") as f:
                f.write(new_content)

        # 4. 🚀 [核心机制] 插件自主 RAG 封装与向主引擎投喂
        print("🚚 [Music Agent] 正在根据音乐领域特性封装记忆切片...")
        
        # 音乐 Agent 专属切片策略：高度浓缩的情感胶囊
        combined_text = f"【曲目】{track_title} (艺术家: {track_artist})\n【标签】{track_tags}\n【意境解析】{analysis_result}\n【部分歌词】{lyrics[:500]}..."
        timestamp = int(time.time())
        
        rag_payload = {
            "command": "RAG_UPSERT",
            "source_file": md_file_path,
            "hash": f"music_{timestamp}", 
            "payload": [
                {
                    "chunk_text": combined_text,
                    "metadata": {
                        "domain": "music",
                        "artist": track_artist,
                        "url": url
                    }
                }
            ]
        }
        # 获取主系统的安全通行证
        token_path = os.path.join(VAULT_ROOT, ".run_token")
        security_token = ""
        if os.path.exists(token_path):
            with open(token_path, "r", encoding="utf-8") as tf:
                security_token = tf.read().strip()
        actual_port = "8000"
        port_path = os.path.join(VAULT_ROOT, ".server_port")
        if os.path.exists(port_path):
            with open(port_path, "r", encoding="utf-8") as pf:
                actual_port = pf.read().strip()
                
        rag_url = f"http://127.0.0.1:{actual_port}/api/rag/ingest"
                
        # 通过 HTTP 向主系统的 RAG 网关提交更新。
        headers = {"Authorization": f"Bearer {security_token}"}
        try:
            resp = requests.post(rag_url, json=rag_payload, headers=headers, timeout=10)
            if resp.status_code == 200:
                print(" [Music Agent] 知识切片已写入系统 RAG 向量库。")
            else:
                print(f" [Music Agent] RAG 更新被主系统拒绝: {resp.text}")
        except Exception as e:
            print(f" [Music Agent] 无法连接主系统 RAG 网关 (可能后端尚未重启): {e}")

    except Exception as e:
        print(f" [Music Agent] 后台解析失败: {e}")

@router.post("/update")
async def update_music_track(
    title: str = Form(...),
    url: str = Form(...), # URL 依然传过来作为主键去寻找，但不允许改
    artist: str = Form("未知"),
    tagsInput: str = Form(""),
    lyrics: str = Form(""),
    analysis: str = Form(""),
    cover_file: UploadFile = File(None)
):
    if not engine: raise HTTPException(status_code=500, detail="引擎未初始化")
    
    tags_list = [t.strip() for t in tagsInput.split(',') if t.strip()]
    tags_raw = ",".join(tags_list)

    try:
        with Session(engine) as session:
            # 根据唯一主键 URL 找到原记录
            track = session.exec(select(MusicTrack).where(MusicTrack.url == url)).first()
            if not track:
                raise HTTPException(status_code=404, detail="未找到该曲目资产")

            # 更新数据
            track.title = title[:50]
            track.artist = artist[:50]
            track.tags_raw = tags_raw[:70]
            track.lyrics = lyrics[:1000]
            track.analysis = analysis[:300]

            # 如果上传了新封面，则覆盖
            if cover_file and cover_file.filename:
                ext = os.path.splitext(cover_file.filename)[1] or '.jpg'
                safe_name = f"cover_{int(time.time())}{ext}"
                save_path = os.path.join(COVERS_DIR, safe_name)
                with open(save_path, "wb") as buffer:
                    import shutil
                    shutil.copyfileobj(cover_file.file, buffer)
                track.cover_url = f"/api/plugins/music_agent/covers/{safe_name}"

            session.add(track)
            session.commit()
            
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.post("/execute")
async def music_plugin_executor(payload: dict):
    func_name = payload.get("func_name")
    args = payload.get("args", {})

    if func_name == "play_music_playlist":
        keywords = args.get("raw_query") or args.get("keywords", "")
        limit = args.get("limit", 10)
        try:
            limit = max(1, min(int(limit), 20))
        except (TypeError, ValueError):
            limit = 10
        with Session(engine) as session:
            all_tracks = session.exec(select(MusicTrack)).all()
            valid_tracks = [t for t in all_tracks if "【失效】" not in t.title]
            
            if not valid_tracks:
                return "本地曲库为空，请先去管理后台录入资产。"
            
            selection, match_meta = select_music_tracks(valid_tracks, keywords, limit=limit)
            if keywords and keywords.strip() and not selection:
                normalized = "、".join(match_meta.get("terms") or []) or keywords
                return f"【本地曲库检索结果】：未找到与 '{keywords}' 相关的曲目。已尝试关键词：{normalized}。请向用户说明本地缺失此类型歌曲，不要编造歌曲名或推荐互联网上的曲目。"
            
            # --- 下面发布事件的代码保持不变 ---
            playlist_data = [t.model_dump() if hasattr(t, "model_dump") else t.dict() for t in selection]
            
            await event_bus.publish({
                "type": "play_playlist",
                "target_panel": "music_agent",
                "target_component": "MusicAgentPanel",
                "playlist": playlist_data
            })
            
            songs_str = ", ".join([f"《{t.title}》" for t in selection])
            match_source = match_meta.get("match_source")
            if match_source and match_source != "random":
                return f"已根据{match_source}匹配为你生成临时歌单：{songs_str}，并在右侧面板开始播放。"
            return f"已为你生成临时歌单：{songs_str}，并在右侧面板开始播放。"

    return f"Music Agent 暂不支持指令: {func_name}"
@router.get("/export")
async def export_music_assets():
    """
    [数字资产归还]
    将混淆命名的本地文件还原为人类可读格式并打包 ZIP
    """
    if not engine: raise HTTPException(status_code=500, detail="引擎未初始化")
    
    timestamp = int(time.time())
    zip_name = f"vault_music_backup_{timestamp}.zip"
    zip_path = os.path.join(CURRENT_DIR, zip_name)
    
    with Session(engine) as session:
        tracks = session.exec(select(MusicTrack)).all()
        
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for track in tracks:
                # 1. 处理音频文件
                audio_filename = track.url.split("/")[-1]
                audio_path = os.path.join(AUDIO_DIR, audio_filename)
                if os.path.exists(audio_path):
                    # 🚀 关键：在 ZIP 中重命名为：歌曲名 - 歌手.mp3
                    ext = os.path.splitext(audio_filename)[1]
                    readable_name = f"Music/{track.title} - {track.artist}{ext}"
                    zipf.write(audio_path, readable_name)
                
                # 2. 处理封面图
                if track.cover_url:
                    cover_filename = track.cover_url.split("/")[-1]
                    cover_path = os.path.join(COVERS_DIR, cover_filename)
                    if os.path.exists(cover_path):
                        ext = os.path.splitext(cover_filename)[1]
                        zipf.write(cover_path, f"Covers/{track.title}{ext}")
            
            # 3. 附带一份 Metadata 说明文档
            metadata = "\n\n".join([f"曲目: {t.title}\n艺术家: {t.artist}\n解析: {t.analysis}" for t in tracks])
            zipf.writestr("资产清单.txt", metadata)

    return FileResponse(zip_path, filename=zip_name, background=BackgroundTasks().add_task(os.remove, zip_path))

# VPM 生命周期钩子：当主引擎准备卸载本插件时，会自动调用此函数
def uninstall_hook(app_engine):
    """插件卸载钩子：清理自己拥有的数据库对象"""
    from sqlmodel import text, Session
    import os
    import shutil
    
    print(" [Music Agent] 正在执行卸载清理...")
    
    # 1. 清理自己的数据库表
    try:
        with Session(app_engine) as session:
            session.exec(text("DROP TABLE IF EXISTS vpm_plugin_music_tracks;"))
            session.commit()
            print("   - 专属数据库表已 Drop")
    except Exception as e:
        print(f"   - 数据库清理跳过: {e}")

