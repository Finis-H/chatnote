import re


TRANSIENT_INTERACTION_PATTERN = re.compile(
    r"(\?|？|什么|谁|哪|哪里|多少|为什么|怎么|如何|吗|呢|"
    r"推荐|建议|适合|送|礼物|买|购买|选|选择|吃饭|吃什么|去哪|旅行|旅游|安排|"
    r"帮我|查一下|搜索|打开|播放|删除|创建|生成)"
)


def is_transient_interaction(text):
    return bool(TRANSIENT_INTERACTION_PATTERN.search(str(text or "")))


TOOL_INTENT_PATTERN = re.compile(
    r"(打开|播放|删除|下载|上传|导出|安装|卸载|运行|执行|扫描|刷新插件|控制|切换|调用)"
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


def classify_interaction_intent(text):
    text = str(text or "")
    if TOOL_INTENT_PATTERN.search(text):
        return "TOOL_TASK"
    if REALTIME_INTENT_PATTERN.search(text):
        return "TOOL_TASK"
    if PROFILE_ENTITY_PATTERN.search(text) and PROFILE_ADVICE_PATTERN.search(text):
        return "LOCAL_PROFILE_CHAT"
    return "DIRECT_CHAT"


def should_use_jit(text):
    return classify_interaction_intent(text) == "TOOL_TASK"
