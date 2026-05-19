import os
import re
from main import VAULT_ROOT
# 暂时保留,等后续直接在主流程调用(做独立笔记管理agent或脚本用)
class MarkdownSemanticSplitter:
    def __init__(self, inbox_dir=None, archive_dir=None):
        self.inbox_dir = inbox_dir or os.path.join(VAULT_ROOT, "knowledge", "inbox")
        self.archive_dir = archive_dir or os.path.join(VAULT_ROOT, "knowledge", "archives")
        
    def split_document(self, text, filename):
        """核心算法：护盾与手术刀"""
        # 1. 启动护盾：隔离所有代码块
        code_blocks = []
        def code_replacer(match):
            code_blocks.append(match.group(0))
            return f"\n<VAULT_CODE_SHIELD_{len(code_blocks)-1}>\n"
        
        # 使用正则捕获 ``` 包裹的任意内容 (含换行)
        text_without_code = re.sub(r'```.*?```', code_replacer, text, flags=re.DOTALL)
        
        # 2. 手术刀切割：顺着 Markdown 标题 (##, ###) 切分
        raw_chunks = re.split(r'(?=\n#{2,3} )', text_without_code)
        
        final_chunks = []
        for chunk in raw_chunks:
            chunk = chunk.strip()
            if not chunk: continue
            
            # 3. 撤销护盾：精准还原代码块
            for i in range(len(code_blocks)):
                shield_tag = f"<VAULT_CODE_SHIELD_{i}>"
                if shield_tag in chunk:
                    chunk = chunk.replace(shield_tag, code_blocks[i])
            
            final_chunks.append({
                "source": filename,
                "content": chunk,
                "token_estimate": len(chunk) # 粗略估计
            })
            
        return final_chunks

    def process_inbox(self):
        """扫描 Inbox，切片并准备送入向量库"""
        print(f"🚜 启动摄入流水线，扫描 {self.inbox_dir} ...\n")
        
        all_chunks = []
        for filename in os.listdir(self.inbox_dir):
            if not filename.endswith(".md"): continue
                
            filepath = os.path.join(self.inbox_dir, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                
            print(f"⏳ 正在解剖文件: {filename}")
            chunks = self.split_document(content, filename)
            all_chunks.extend(chunks)
            
            print(f"   -> 成功切分为 {len(chunks)} 个完美语义块。")

        print(f"\n✅ 摄入完成！共产出 {len(all_chunks)} 个知识切片，等待向量化。")
        return all_chunks

if __name__ == "__main__":
    # 测试桩：在 inbox 造一个测试文件
    os.makedirs(os.path.join(VAULT_ROOT, "knowledge", "inbox"), exist_ok=True)
    
    # 巧妙利用 chr(96) 动态生成 Markdown 的三个反引号，彻底避开前端渲染器的截断 Bug
    bq = chr(96) * 3
    
    test_md = f"""
## 数据库连接模块
这是一个负责连接本地 SQLite 的基础模块。
必须处理好连接池，防止并发报错。

{bq}python
import sqlite3
def get_db_connection():
    conn = sqlite3.connect('vault.db')
    conn.row_factory = sqlite3.Row
    return conn
{bq}

## 注意事项
密码严禁硬编码。
"""
    
    # 1. 写入测试文件
    test_file_path = os.path.join(VAULT_ROOT, "knowledge", "inbox", "test_db.md")
    with open(test_file_path, "w", encoding="utf-8") as f:
        f.write(test_md.strip())

    # 2. 运行摄入流水线
    pipeline = MarkdownSemanticSplitter()
    chunks = pipeline.process_inbox()
    
    # 3. 打印验证结果：看看代码块有没有被暴力切碎
    print("\n--- 🔪 抽查第 1 个 Chunk (预期包含完整代码块) ---")
    if len(chunks) > 0:
        print(chunks[0]['content'])
    
    print("\n--- 🔪 抽查第 2 个 Chunk (预期为纯文本注意事项) ---")
    if len(chunks) > 1:
        print(chunks[1]['content'])