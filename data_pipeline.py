import feedparser
import trafilatura

def fetch_and_clean_articles(rss_url, max_items=3):
    """
    极简数据输入管道 (纯函数)
    作用：抓取 RSS 源，并对提取到的链接进行正文脱水。
    """
    print(f"📡 正在探测数据源: {rss_url}")
    feed = feedparser.parse(rss_url)
    
    clean_data_list = []
    
    # 限制抓取数量，防止把大模型的 Token 撑爆
    for entry in feed.entries[:max_items]:
        print(f"  -> 正在抓取并脱水: {entry.title}")
        
        # 1. 抓取网页原始 HTML
        downloaded = trafilatura.fetch_url(entry.link)
        
        if downloaded:
            # 2. 核心脱水逻辑：只保留干净的正文文本
            clean_text = trafilatura.extract(downloaded)
            
            if clean_text:
                # 3. 封装成标准化的字典格式，准备交接给 LLM
                clean_data_list.append({
                    "title": entry.title,
                    "link": entry.link,
                    # MVP 阶段：截取前 1500 个字符，防止长文直接超载
                    "content": clean_text[:1500] 
                })
        else:
            print(f"  [X] 抓取失败: {entry.link}")
            
    return clean_data_list

# --- 本地测试入口 ---
if __name__ == "__main__":
    # 找一个高质量的 RSS 源测试，比如阮一峰的网络日志或者某个技术社区
    test_rss_url = "http://www.ruanyifeng.com/blog/atom.xml" 
    
    results = fetch_and_clean_articles(test_rss_url, max_items=2)
    
    for idx, item in enumerate(results):
        print(f"\n--- 抓取成功 {idx+1} ---")
        print(f"标题: {item['title']}")
        print(f"脱水正文片段: {item['content'][:100]}...") # 只打印开头看效果