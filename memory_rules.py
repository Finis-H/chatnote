import re


TRANSIENT_INTERACTION_PATTERN = re.compile(
    r"(\?|？|什么|谁|哪|哪里|多少|为什么|怎么|如何|吗|呢|"
    r"推荐|建议|适合|送|礼物|买|购买|选|选择|吃饭|吃什么|去哪|旅行|旅游|安排|"
    r"帮我|查一下|搜索|打开|播放|删除|创建|生成)"
)


def is_transient_interaction(text):
    return bool(TRANSIENT_INTERACTION_PATTERN.search(str(text or "")))
