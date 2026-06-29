import re


TRANSIENT_INTERACTION_PATTERN = re.compile(
    r"(\?|？|什么|谁|哪|哪里|多少|为什么|怎么|如何|吗|呢|"
    r"推荐|建议|适合|送|礼物|买|购买|选|选择|吃饭|吃什么|去哪|旅行|旅游|安排|"
    r"帮我|查一下|搜索|打开|播放|删除|创建|生成|放歌|听歌|打碟|放首|播首|来点音乐)"
)


def is_transient_interaction(text):
    return bool(TRANSIENT_INTERACTION_PATTERN.search(str(text or "")))


TOOL_INTENT_PATTERN = re.compile(
    r"(打开|播放|删除|下载|上传|导出|安装|卸载|运行|执行|扫描|刷新插件|控制|切换|调用|"
    r"放歌|听歌|打碟|放首|播首|来点.*(歌|歌曲|音乐)|放.*(歌|歌曲|音乐)|听.*(歌|歌曲|音乐))"
)

REALTIME_INTENT_PATTERN = re.compile(
    r"(查|查询|搜索|联网|网上|网页|新闻|最新|今年|今天|明天|附近|哪里买|在哪买|价格|多少钱|对比|京东|淘宝|地图)"
)

PROFILE_ENTITY_PATTERN = re.compile(
    r"(父亲|爸爸|爸|母亲|妈妈|妈|朋友|好友|同事|同学|老板|上司|领导|伴侣|妻子|老婆|丈夫|老公|孩子|儿子|女儿)"
)

PROFILE_ADVICE_PATTERN = re.compile(
    r"(应该|适合|推荐|建议|送|礼物|喜欢什么|爱吃什么|吃什么|去哪|怎么选)"
)

SELF_PROFILE_QUERY_PATTERN = re.compile(
    r"(我是谁|我叫什么|我的名字|我喜欢什么|我最喜欢什么|我不喜欢什么|我爱吃什么|我的偏好)"
)

DIRECT_STATEMENT_PATTERN = re.compile(
    r"^我(最)?(喜欢|不喜欢|讨厌|爱吃|叫|是|正在|平时|通常)"
)

CASUAL_CHAT_PATTERN = re.compile(
    r"^(你好|哈喽|嗨|谢谢|感谢|早安|晚安|好的|好|嗯|OK|ok|收到)[。！!？?]*$"
)

COMPLEX_INTENT_PATTERN = re.compile(
    r"(分析|设计|规划|方案|计划|排查|检查|诊断|实现|开发|优化|重构|总结|整理|对比|评估|审查|生成|创建|写)"
)


def classify_interaction_intent(text):
    text = str(text or "")
    if TOOL_INTENT_PATTERN.search(text):
        return "TOOL_TASK"
    if REALTIME_INTENT_PATTERN.search(text):
        return "TOOL_TASK"
    if SELF_PROFILE_QUERY_PATTERN.search(text):
        return "LOCAL_PROFILE_CHAT"
    if PROFILE_ENTITY_PATTERN.search(text) and PROFILE_ADVICE_PATTERN.search(text):
        return "LOCAL_PROFILE_CHAT"
    if COMPLEX_INTENT_PATTERN.search(text) or len(text) >= 80:
        return "UNCERTAIN"
    if DIRECT_STATEMENT_PATTERN.search(text) or CASUAL_CHAT_PATTERN.search(text):
        return "DIRECT_CHAT"
    return "UNCERTAIN"


def should_use_jit(text):
    return classify_interaction_intent(text) not in {"DIRECT_CHAT", "LOCAL_PROFILE_CHAT"}
