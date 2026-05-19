# Vault OS 插件 (VPM) 接入与开发标准 v1.0

欢迎来到 Vault OS 开发者生态。Vault OS 采用**微内核 + 零信任沙盒**架构。任何第三方 Agent、Tool 或 MCP 想要接入，只需创建一个文件夹并放置到 `vault/plugins/` 目录下即可实现“热插拔”。
为了确保主系统的安全与性能，您的插件必须严格遵守以下“三层契约”与“数据隔离法则”。
## 📂 一、 插件标准目录拓扑

一个合格的 VPM 插件文件夹（例如 `your_agent`），必须包含以下物理结构：

Plaintext

```
vault/plugins/your_agent/
├── manifest.json       # [必填] AI 认知契约：告诉大模型你是什么，能干什么
├── api.py              # [必填] 后端引擎：提供独立 API 路由与生命周期钩子
├── tools/              # [可选] 工具库：存放额外的独立 JSON 契约文件
├── ui/                 # [可选] 界面沙盒：存放 .vue 格式的独立沉浸式面板
│   └── MainPanel.vue   
├── assets/             # [可选] 插件私有资产 (图片、音频、临时文件)
```

---

## 📜 二、 认知契约层 (`manifest.json`)

这是大模型（CEO）认识你的唯一途径。你必须提供严格符合 OpenAI Tool Calling 格式的描述，并增加 Vault OS 专属的 `execution` 路由配置。

JSON

```
{
  "name": "your_agent",
  "version": "1.0.0",
  "author": "Developer Name",
  "description": "这是展示在 VPM 插件中心的简介",
  "type": "function",
  "function": {
    "name": "your_core_function_name",
    "description": "【系统级提示】告诉 LLM 在什么场景下必须调用这个插件。越详细越好。",
    "parameters": {
      "type": "object",
      "properties": {
        "arg1": { "type": "string", "description": "参数说明" }
      },
      "required": ["arg1"]
    }
  },
  "execution": {
    "type": "http",
    "endpoint": "http://127.0.0.1:8000/api/plugins/your_agent/execute",
    "method": "POST"
  }
}
```

_💡 **架构师注**：不要让你的插件试图包揽一切，做好单一职责（SRP）。_

---

## ⚙️ 三、 运行时契约层 (`api.py`)

主系统不会干涉你的内部业务逻辑，但你必须向主系统暴露标准的 FastAPI Router，并提供安装与销毁的“生命周期钩子”。

Python

```
from fastapi import APIRouter
import os

# 1. 暴露标准路由 (主系统会自动加上 /api/plugins/your_agent 前缀)
router = APIRouter()

# 2. [必填钩子] 初始化：主引擎启动时调用，用于建表或创建私有目录
def init_plugin(app_engine):
    # 此处编写你的 SQLite 建表逻辑，或创建私有文件夹
    print("✅ [Your Agent] 已挂载并完成初始化")

# 3. [必填钩子] 焦土卸载：主系统物理删除你之前，会调用此函数让你自己打扫战场
def uninstall_hook(app_engine):
    # 🚨 必须在此处执行 DROP TABLE 删除你的私有数据库表
    # 🚨 必须在此处 shutil.rmtree 删除你在全局 vault/ 下写入的任何共享记忆
    pass

# 4. 业务逻辑入口：接收大模型分配的任务
@router.post("/execute")
async def execute_task(payload: dict):
    # 你的核心处理逻辑
    return {"status": "success", "result": "任务完成的数据"}
```

---

## 🎨 四、 UI 沙盒契约层 (`ui/*.vue`)

如果你的插件需要前端界面（如音乐播放器、K线图），请遵守“致盲原则”：**插件前端不允许直接操作主系统的全局状态。**

1. **入口命名**：默认约定入口组件名为与后端交互或业务强相关的名称（主系统会通过 `target_component` 动态拉起）。
    
2. **接收数据**：大模型生成的数据，主系统会通过事件总线以 `vpm_ws_<插件名>` 的 CustomEvent 广播，你的组件只需监听该事件。
    
3. **空间自适应**：必须接收主系统下发的 `isImmersive` (Boolean) 属性，并针对 `true` (沉浸式宽屏) 和 `false` (侧边栏迷你状态) 做两套 CSS 布局适配。
    
4. **生命周期缝合**：在组件销毁 (`onBeforeUnmount`) 时，必须彻底清理 `Audio`、`Video`、`WebSocket` 等底层句柄，严禁制造僵尸进程。
    

---

## 🛡️ 五、 零信任与数据隔离法则 (The Zero-Trust Law)

为防止多个智能体“神仙打架”导致系统崩溃，开发者必须遵守以下红线：

1. **命名空间隔离**：
    
    - 所有的 SQLite 表名必须以 `vpm_plugin_你的插件名_` 开头。
        
    - 写入主系统的知识库（如生成 Markdown 笔记），文件名必须以 `你的插件名_` 开头，以便卸载时精准切除。
        
2. **黑板沙盒法则**：
    
    - 插件**绝对禁止**直接读写系统的全局内存或 `blackboard`。
        
    - 如果你需要依赖前一个插件的数据，在 `manifest.json` 的参数声明中等待主引擎使用 `$$` 语法将数据安全注入给你。
        
3. **资源私有化**：
    
    - 插件自身的图片、配置、音频等静态资源，必须存储在 `vault/plugins/your_agent/` 内部，绝对禁止污染根目录。