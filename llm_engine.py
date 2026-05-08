import os
from openai import OpenAI
from datetime import datetime

# 🌟 核心修改点：将网关指向阿里云 DashScope 的兼容接口
client = OpenAI(
    # 强烈建议将 API Key 存入环境变量，这里为了快速测试可以先写死
    api_key=os.environ.get("DASHSCOPE_API_KEY", "sk-test"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1" 
)

def generate_daily_briefing(clean_data_list, output_filename="Briefing_Today.md"):
    """
    极简 LLM 提炼引擎 (Qwen-max 驱动)
    """
    print("🧠 管家(Qwen-max)正在思考并提炼今日情报...")
    
    system_prompt = """
    你是一个顶级的技术管家。请阅读用户提供的多篇文章，提炼出最核心的价值点。
    你必须严格按照以下格式输出，不要有任何多余的废话：
    
    ---
    id: brf_{当前日期}
    date: {当前日期}
    tags: [根据内容自动提取3个标签]
    ---
    
    # ☕ 早安，老板！这是今天的核心简报：
    
    ## [文章1标题]
    - 💡 **核心洞察**：(一句话总结文章最核心的观点或技术突破)
    - 🔗 **溯源锚点**：(附上原文链接)
    
    ## [文章2标题]
    ...
    """

    user_content = "今天是：" + datetime.now().strftime("%Y-%m-%d") + "\n\n"
    for idx, item in enumerate(clean_data_list):
        user_content += f"【第{idx+1}篇】\n标题：{item['title']}\n链接：{item['link']}\n正文内容：{item['content']}\n\n"

    try:
        # 🌟 核心修改点：指定模型为 qwen-max
        response = client.chat.completions.create(
            model="qwen-max", 
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            temperature=0.3 # 保持管家语气的克制
        )
        
        final_markdown = response.choices[0].message.content
        
        with open(output_filename, "w", encoding="utf-8") as f:
            f.write(final_markdown)
            
        print(f"✅ 搞定！简报已保存至: {output_filename}")
        return output_filename
        
    except Exception as e:
        print(f"❌ 管家脑子宕机了: {e}")
        return None

# --- 联调测试 ---
# 你可以在这里把 data_pipeline 抓取的数据传进来测试
from data_pipeline import fetch_and_clean_articles
real_rss_url = "https://hnrss.org/frontpage"
results = fetch_and_clean_articles(real_rss_url, max_items=2)

if results:
    generate_daily_briefing(results)
else:
    print("抓取失败，看看是不是网络问题，或者换个 RSS 链接试试。")