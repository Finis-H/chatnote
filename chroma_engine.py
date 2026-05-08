import os
import json
import chromadb
import dashscope
from chromadb.api.types import Documents, EmbeddingFunction, Embeddings

CONFIG_PATH = "vault/system_config.json"

def load_embed_config():
    """从 Tauri 前端生成的配置文件中读取 Embedding 专用配置"""
    if not os.path.exists(CONFIG_PATH):
        print(f"⚠️ 尚未检测到前端配置文件 {CONFIG_PATH}，请在 GUI 设置中保存。")
        return None, None   
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            settings = json.load(f)
            # 精准读取 embed 专属的 key 和 model
            embed_api_key = settings.get("embed_api_key")
            embed_model = settings.get("embed_model", dashscope.TextEmbedding.Models.text_embedding_v4)
            return embed_api_key, embed_model
    except Exception as e:
        print(f"🚨 读取 GUI 配置崩溃: {e}")
        return None, None

# 初始化时动态读取配置
EMBED_API_KEY, EMBED_MODEL = load_embed_config()

class AliyunEmbeddingFunction(EmbeddingFunction):
    """自定义阿里云 Embedding 引擎，读取 GUI 配置"""
    def __init__(self):
        # 🛡️ 终极防线：如果 GUI 还没配，或者配置失效
        if not EMBED_API_KEY:
            raise ValueError("MISSING_EMBED_API_KEY: 无法启动向量引擎，请在前端配置并保存系统密钥！") 
        dashscope.api_key = EMBED_API_KEY
        self.model_name = EMBED_MODEL
    """自定义阿里云 Embedding 引擎，替换 ChromaDB 默认的本地模型"""
    def __call__(self, input: Documents) -> Embeddings:
        print(f"☁️  [云端算力卸载] 正在发送 {len(input)} 个文本块至阿里云({self.model_name})...")
        resp = dashscope.TextEmbedding.call(
            model=self.model_name,
            input=input
        )
        if resp.status_code == 200:
            return [item['embedding'] for item in resp.output['embeddings']]
        else:
            raise Exception(f"🚨 阿里云 API 调用失败: {resp.status_code} - {resp.message}")

class VaultVectorDB:
    def __init__(self, db_path="vault/knowledge/vector_store"):
        self.db_path = db_path
        os.makedirs(self.db_path, exist_ok=True)
        self.client = chromadb.PersistentClient(path=self.db_path)
        self.aliyun_ef = AliyunEmbeddingFunction() 
        # 2. 核心魔法：在获取或创建集合时，强行注入阿里云引擎
        self.collection = self.client.get_or_create_collection(
            name="vault_core_v3", # 建议改个名字，和之前纯本地的库区分开
            embedding_function=self.aliyun_ef
        )
        print(f"💽 ChromaDB 已就绪 | 物理路径: {self.db_path}")

    def delete_by_source(self, source_path):
        """精准爆破：根据文件路径抹除 ChromaDB 中的所有相关历史切片"""
        try:
            # 1. 先探测敌情，数一数有多少个旧切片
            existing_data = self.collection.get(where={"source": source_path})
            count = len(existing_data["ids"]) if existing_data and existing_data["ids"] else 0
            # 2. 如果存在，直接执行物理抹除
            if count > 0:
                self.collection.delete(where={"source": source_path})
                print(f"🗑️ [向量引擎] 肃清完毕：已物理抹除 {count} 个属于 {source_path} 的旧切片。")
            
            return count
        except Exception as e:
            print(f"🚨 [向量引擎] 抹除旧切片失败: {e}")
            return 0
        
    def add_chunks(self, texts, metadatas, ids):
        """标准弹药装填：直接接收已解耦的纯净数据，执行底层 Upsert"""
        if not texts: 
            return
            
        print(f"📦 [向量引擎] 正在调用阿里云算力，为 {len(texts)} 个切片生成高维坐标并落盘...")
        try:
            # ChromaDB 的 upsert 如果遇到相同的 ID 会覆盖，遇到新的会新增
            self.collection.upsert(
                documents=texts,
                metadatas=metadatas,
                ids=ids
            )
            print("✅ [向量引擎] 注入完成！数字资产已绝对锁定。")
        except Exception as e:
            print(f"🚨 [向量引擎] 注入高维空间失败: {e}")
            raise e

    def search(self, query, top_k=3):
        """检索代码也无需修改！Query 也会自动经过阿里云变身向量，再和本地库比对"""
        print(f"🔍 [混合检索] 正在高维空间中寻找: '{query}'")
        
        results = self.collection.query(
            query_texts=[query],
            n_results=top_k
        )
        formatted_results = []
        if results['documents'] and results['documents'][0]:
            for i in range(len(results['documents'][0])):
                distance = results['distances'][0][i] if 'distances' in results and results['distances'] else 1.0
                score = max(0, round(1.0 - distance, 2)) 
                
                formatted_results.append({
                    "score": score,
                    "content": results['documents'][0][i],
                    "source": results['metadatas'][0][i]['source']
                })
        return formatted_results

    # 测试环境chunks，后期可删除
    # def ingest_chunks(self, chunks):
    #     """代码无需任何修改！ChromaDB 会在底层自动调用 AliyunEmbeddingFunction"""
    #     if not chunks: return
        
    #     documents = [c['content'] for c in chunks]
    #     metadatas = [{"source": c['source']} for c in chunks]
    #     ids = [f"{c['source']}_chunk_{i}" for i, c in enumerate(chunks)]
        
    #     print(f"📦 正在向量化并写入 {len(chunks)} 个知识切片...")
    #     self.collection.upsert(
    #         documents=documents,
    #         metadatas=metadatas,
    #         ids=ids
    #     )
    #     print("✅ 注入完成！高维度数字资产已落盘。")
if __name__ == "__main__":
    db = VaultVectorDB()
