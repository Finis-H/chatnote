import os
import json

import chromadb
import dashscope
from chromadb.api.types import Documents, EmbeddingFunction, Embeddings

from main import VAULT_ROOT


CONFIG_PATH = os.path.join(VAULT_ROOT, "system_config.json")
LEGACY_COLLECTION_NAME = "vault_core_v3"
COLLECTION_NAME = "vault_core_v3_dashscope"


def load_embed_config():
    """Read embedding settings saved by the GUI."""
    if not os.path.exists(CONFIG_PATH):
        print(f" [RAG] Config file does not exist yet: {CONFIG_PATH}")
        return None, None
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            settings = json.load(f)
        embed_api_key = settings.get("embed_api_key")
        embed_model = settings.get("embed_model", dashscope.TextEmbedding.Models.text_embedding_v4)
        return embed_api_key, embed_model
    except Exception as e:
        print(f" [RAG] Failed to read embedding config: {e}")
        return None, None


class AliyunEmbeddingFunction(EmbeddingFunction):
    """DashScope embedding adapter used by ChromaDB."""

    def __init__(self):
        embed_api_key, embed_model = load_embed_config()
        if not embed_api_key:
            raise ValueError(
                "MISSING_EMBED_API_KEY: Please configure Embedding API Key in Settings."
            )
        dashscope.api_key = embed_api_key
        self.model_name = embed_model

    def __call__(self, input: Documents) -> Embeddings:
        print(f" [RAG] Sending {len(input)} chunks to DashScope embedding model {self.model_name}...")
        resp = dashscope.TextEmbedding.call(model=self.model_name, input=input)
        if resp.status_code == 200:
            return [item["embedding"] for item in resp.output["embeddings"]]
        raise Exception(f"DashScope embedding call failed: {resp.status_code} - {resp.message}")


class VaultVectorDB:
    def __init__(self, db_path=None):
        self.db_path = db_path or os.path.join(VAULT_ROOT, "knowledge", "vector_store")
        os.makedirs(self.db_path, exist_ok=True)
        self.client = chromadb.PersistentClient(path=self.db_path)
        self.aliyun_ef = None
        self.embedding_ready = False
        self._load_embedding_function()
        self.collection = self._get_collection() if self.embedding_ready else None
        print(f" ChromaDB ready | path: {self.db_path}")

    def _load_embedding_function(self):
        try:
            self.aliyun_ef = AliyunEmbeddingFunction()
            self.embedding_ready = True
        except ValueError as e:
            if "MISSING_EMBED_API_KEY" not in str(e):
                raise
            self.aliyun_ef = None
            self.embedding_ready = False
            print(" [RAG] Embedding API Key is empty; vector features are disabled until Settings are saved.")

    def _get_collection(self):
        if not self.aliyun_ef:
            return None
        return self.client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=self.aliyun_ef,
        )

    def is_ready(self):
        return self.embedding_ready

    def update_config(self, _new_config=None):
        self._load_embedding_function()
        self.collection = self._get_collection() if self.embedding_ready else None
        if self.embedding_ready:
            print(" [RAG] Embedding configuration reloaded.")

    def delete_by_source(self, source_path):
        if not self.is_ready() or self.collection is None:
            print(" [RAG] Embedding API Key is empty; skip vector delete.")
            return 0
        try:
            existing_data = self.collection.get(where={"source": source_path})
            count = len(existing_data["ids"]) if existing_data and existing_data["ids"] else 0
            if count > 0:
                self.collection.delete(where={"source": source_path})
                print(f" [RAG] Deleted {count} chunks for source: {source_path}")
            return count
        except Exception as e:
            print(f" [RAG] Failed to delete old chunks: {e}")
            return 0

    def add_chunks(self, texts, metadatas, ids):
        if not texts:
            return
        if not self.is_ready():
            raise RuntimeError(
                "MISSING_EMBED_API_KEY: Please configure Embedding API Key in Settings before ingesting knowledge."
            )
        if self.collection is None:
            self.collection = self._get_collection()

        print(f" [RAG] Embedding and storing {len(texts)} chunks...")
        self.collection.upsert(documents=texts, metadatas=metadatas, ids=ids)
        print(" [RAG] Upsert complete.")

    def search(self, query, top_k=3, where=None):
        if not self.is_ready():
            raise RuntimeError(
                "MISSING_EMBED_API_KEY: Please configure Embedding API Key in Settings before searching local knowledge."
            )
        if self.collection is None:
            self.collection = self._get_collection()

        print(f" [RAG] Searching local knowledge for: {query}")
        query_args = {"query_texts": [query], "n_results": top_k}
        if where:
            query_args["where"] = where
        results = self.collection.query(**query_args)
        formatted_results = []
        if results["documents"] and results["documents"][0]:
            for i in range(len(results["documents"][0])):
                distance = results["distances"][0][i] if "distances" in results and results["distances"] else 1.0
                score = max(0, round(1.0 - distance, 2))
                metadata = results["metadatas"][0][i] if results.get("metadatas") and results["metadatas"][0] else {}
                formatted_results.append(
                    {
                        "score": score,
                        "content": results["documents"][0][i],
                        "source": metadata.get("source", ""),
                        "metadata": metadata,
                    }
                )
        return formatted_results


if __name__ == "__main__":
    db = VaultVectorDB()
