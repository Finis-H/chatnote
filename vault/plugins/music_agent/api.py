import requests
import random
import json
import os
import time
import shutil
import zipfile

from core_bus import event_bus
from openai import OpenAI
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks
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

router = APIRouter()
engine = None
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
VAULT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
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
    print("🎵 [Music Agent] V2 数据库与本地图床已就绪！")
# 暴露本地音频的串流路由
@router.get("/audio/{filename}")
async def get_audio(filename: str):
    file_path = os.path.join(AUDIO_DIR, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path)
    raise HTTPException(status_code=404, detail="Audio not found")
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
        
    # 生成绝对唯一的内部 API 访问路径，彻底终结主键冲突！
    generated_url = f"http://127.0.0.1:8000/api/plugins/music_agent/audio/{safe_audio_name}"

    # --- 2. 物理保存封面图片 ---
    cover_url_db = ""
    if cover_file and cover_file.filename:
        cover_ext = os.path.splitext(cover_file.filename)[1] or '.jpg'
        safe_cover_name = f"cover_{timestamp}{cover_ext}"
        cover_save_path = os.path.join(COVERS_DIR, safe_cover_name)
        with open(cover_save_path, "wb") as buffer:
            shutil.copyfileobj(cover_file.file, buffer)
        cover_url_db = f"http://127.0.0.1:8000/api/plugins/music_agent/covers/{safe_cover_name}"

    try:
        # --- 3. 写入 SQLite ---
        with Session(engine) as session:
            new_track = MusicTrack(
                url=generated_url, title=title, artist=artist, cover_url=cover_url_db,
                tags_raw=tags_raw, lyrics=lyrics, analysis=analysis
            )
            session.add(new_track)
            session.commit()

        # --- 4. 生成底层 Markdown 资产 ---
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
*(Vault OS - 情绪打碟机 V2)*

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
    """真正的物理抹除：SQLite + 本地音频 + 本地封面 + Markdown记忆 + RAG 向量擦除"""
    if not engine: raise HTTPException(status_code=500, detail="引擎未初始化")
    import requests # 确保发通知能用到
    
    with Session(engine) as session:
        track = session.exec(select(MusicTrack).where(MusicTrack.url == url)).first()
        if not track:
            raise HTTPException(status_code=404, detail="未找到该曲目")

        # --- 1. 碎纸机：销毁本地封面图 ---
        if track.cover_url:
            cover_filename = track.cover_url.split("/")[-1]
            cover_path = os.path.join(COVERS_DIR, cover_filename)
            if os.path.exists(cover_path):
                os.remove(cover_path)
                print(f"🗑️ [碎纸机] 封面已销毁: {cover_filename}")

        # --- 2. 碎纸机：销毁本地音频文件 ---
        if track.url and track.url.startswith("http"):
            audio_filename = track.url.split("/")[-1]
            audio_path = os.path.join(AUDIO_DIR, audio_filename)
            if os.path.exists(audio_path):
                os.remove(audio_path)
                print(f"🗑️ [碎纸机] 音轨已销毁: {audio_filename}")

        # --- 3. 记忆切除：销毁 Markdown 沙盒资产，并通知主脑遗忘 ---
        if os.path.exists(KNOWLEDGE_DIR):
            for filename in os.listdir(KNOWLEDGE_DIR):
                if filename.endswith(".md"):
                    filepath = os.path.join(KNOWLEDGE_DIR, filename)
                    with open(filepath, "r", encoding="utf-8") as f:
                        content = f.read()
                        
                    # 只要 Markdown 文件的 frontmatter 里包含这个唯一主键 URL，就是它！
                    if track.url in content:
                        os.remove(filepath)
                        print(f"🗑️ [记忆切除] 物理知识库资产已抹除: {filename}")
                        
                        #  核心新增：向主引擎 RAG 网关发送“遗忘指令”
                        try:
                            token_path = os.path.join(VAULT_ROOT, ".run_token")
                            security_token = ""
                            if os.path.exists(token_path):
                                with open(token_path, "r", encoding="utf-8") as tf:
                                    security_token = tf.read().strip()
                                    
                            # 【精妙设计】：通过发送一个空的 payload 数组，利用主引擎逻辑触发彻底注销
                            rag_payload = {
                                "command": "RAG_UPSERT",
                                "source_file": filepath,
                                "hash": "delete_hash", 
                                "payload": [] 
                            }
                            headers = {"Authorization": f"Bearer {security_token}"}
                            
                            resp = requests.post("http://127.0.0.1:8000/api/rag/ingest", json=rag_payload, headers=headers, timeout=5)
                            if resp.status_code == 200:
                                print("✅ [记忆切除] 已成功通知主系统 ChromaDB 擦除相关的多维向量！")
                            else:
                                print(f"⚠️ [记忆切除] 主系统拒绝擦除: {resp.text}")
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
                
        # 通过 HTTP 向主系统的 RAG 神经总线发起注射！
        headers = {"Authorization": f"Bearer {security_token}"}
        try:
            resp = requests.post("http://127.0.0.1:8000/api/rag/ingest", json=rag_payload, headers=headers, timeout=10)
            if resp.status_code == 200:
                print("✅ [Music Agent] 记忆碎片已成功上交系统 RAG 向量库！管家现在可以搜到它了！")
            else:
                print(f"⚠️ [Music Agent] 记忆上交被主系统拒收: {resp.text}")
        except Exception as e:
            print(f"🚨 [Music Agent] 无法连接主引擎 RAG 网关 (可能后端尚未重启): {e}")

    except Exception as e:
        print(f"🚨 [Music Agent] 后台解析大崩盘: {e}")

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
                track.cover_url = f"http://127.0.0.1:8000/api/plugins/music_agent/covers/{safe_name}"

            session.add(track)
            session.commit()
            
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.post("/execute")
async def music_plugin_executor(payload: dict):
    """
    [VPM 独立执行网关]
    主引擎 ToolExecutor 转发过来的指令将在这里进行最终分发。
    """
    func_name = payload.get("func_name")
    args = payload.get("args", {})

    if func_name == "play_music_playlist":
        keywords = args.get("keywords", "")
        # --- 原本在主引擎里的逻辑现在搬家到了这里 ---
        with Session(engine) as session:
            # 1. 查库
            all_tracks = session.exec(select(MusicTrack)).all()
            valid_tracks = [t for t in all_tracks if "【失效】" not in t.title]
            
            if not valid_tracks:
                return "本地曲库为空，请Boss先去管理后台录入资产。"

            # 2. 模糊匹配
            matched = []
            k = keywords.lower()
            for t in valid_tracks:
                corpus = f"{t.title} {t.artist} {t.tags_raw} {t.analysis} {t.lyrics}".lower()
                if k in corpus: matched.append(t)
            
            # 3. 随机抽取并发布事件
            selection = random.sample(matched or valid_tracks, min(len(matched or valid_tracks), 10))
            
            # 将曲目对象转为字典格式发送
            playlist_data = [t.model_dump() if hasattr(t, "model_dump") else t.dict() for t in selection]
            
            # 关键：插件直接利用总线向前端发号施令
            await event_bus.publish({
                "type": "play_playlist",
                "target_panel": "music_agent",
                "target_component": "MusicAgentPanel",
                "playlist": playlist_data
            })
            
            songs_str = ", ".join([f"《{t.title}》" for t in selection])
            return f"已为你生成临时歌单：{songs_str}，并在右侧面板开始打碟。"

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
    """插件专属的焦土政策：清理自己留在全局的垃圾"""
    from sqlmodel import text, Session
    import os
    import shutil
    
    print("🧹 [Music Agent] 正在执行自毁程序...")
    
    # 1. 销毁自己的物理表
    try:
        with Session(app_engine) as session:
            session.exec(text("DROP TABLE IF EXISTS vpm_plugin_music_tracks;"))
            session.commit()
            print("   - 专属数据库表已 Drop")
    except Exception as e:
        print(f"   - 数据库清理跳过: {e}")

