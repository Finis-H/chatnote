# Vault OS 插件 (VPM) 接入与开发标准 v2.0

本文档面向第三方开发者，用于在 `vault/plugins/` 下开发 Vault OS 插件。VPM v2 的基本原则是：插件负责自己的领域逻辑、界面和数据切片；主系统负责工具调度、路由挂载、UI 加载、向量写入/更新/删除和卸载边界控制。

插件目录名就是系统识别用的 `plugin_id`。例如目录 `vault/plugins/music_agent/` 的 `plugin_id` 是 `music_agent`。

> 重要：运行中新增插件目录后，插件中心可以扫描到 `manifest.json`，但后端路由和工具注册通常需要重启或重新初始化后才会生效。不要把“放入目录”理解为所有能力立刻可调用。

## 一、插件目录结构

一个典型插件建议采用以下结构：

```text
vault/plugins/your_agent/
├── manifest.json          # 必需：插件展示信息、工具契约、执行配置
├── api.py                 # 可选：需要后端 API、生命周期钩子或管理接口时提供
├── tools/                 # 可选：额外工具契约 JSON，可为单个对象或数组
├── ui/                    # 可选：Vue 单文件组件
│   ├── Manager.vue        # 可选但推荐：插件中心“管理”按钮默认加载
│   └── MainPanel.vue      # 可选：业务面板，由 target_component 指定
├── knowledge/             # 可选：插件私有知识材料、来源文件、切片依据
├── assets/                # 可选：插件私有静态资源
├── audio/                 # 可选：插件私有音频资源
└── covers/                # 可选：插件私有图片资源
```

目录约束：

- `manifest.json` 是插件被插件中心识别、被工具注册器读取的核心文件。
- `api.py` 不是所有插件都必须有；只有插件需要 HTTP 路由、数据库初始化、管理接口、生命周期钩子时才需要。
- 插件产生的文件必须放在自己的插件目录下，避免写入全局 `vault/` 根目录。
- 插件私有表、私有文件、私有向量来源都必须能通过 `plugin_id` 精确归属。

## 二、`manifest.json` 契约

`manifest.json` 同时承担两个职责：

- 给插件中心展示插件信息。
- 给大模型和工具执行器声明可调用工具。

推荐格式：

```json
{
  "name": "your_agent",
  "version": "2.0.0",
  "author": "Developer Name",
  "description": "展示在 VPM 插件中心的简短说明",
  "tags": ["示例", "工具"],
  "type": "function",
  "function": {
    "name": "your_core_function_name",
    "description": "告诉模型何时调用该工具。请写清楚触发场景、能力边界和禁止事项。",
    "parameters": {
      "type": "object",
      "properties": {
        "arg1": {
          "type": "string",
          "description": "参数说明"
        }
      },
      "required": ["arg1"]
    }
  },
  "execution": {
    "type": "http",
    "endpoint": "/api/plugins/your_agent/execute",
    "method": "POST",
    "payload_format": {
      "func_name": "your_core_function_name",
      "args": "{args}"
    }
  }
}
```

字段说明：

- `name`：展示名称，建议与目录名保持一致。
- `version`：插件版本，建议使用语义化版本。
- `author`：作者名称。
- `description`：插件中心展示文案。
- `tags`：插件标签，供 UI 展示或后续筛选使用。
- `type`：通常为 `function`。
- `function.name`：工具调用名，必须全局唯一，不要与内置工具或其他插件冲突。
- `function.description`：模型选择工具的主要依据，应明确说明适用场景和边界。
- `function.parameters`：OpenAI Tool Calling 风格的 JSON Schema。
- `execution`：Vault OS 执行器使用的物理执行配置。

### HTTP 执行模式

HTTP 模式适合带有 `api.py` 后端路由的插件。

```json
{
  "execution": {
    "type": "http",
    "endpoint": "/api/plugins/your_agent/execute",
    "method": "POST",
    "headers": {
      "X-Plugin-Version": "2.0.0"
    },
    "payload_format": {
      "func_name": "your_core_function_name",
      "args": "{args}"
    }
  }
}
```

规则：

- `endpoint` 以 `/` 开头时，系统会自动补成本次运行的本地后端地址，例如 `http://127.0.0.1:{server_port}/api/plugins/your_agent/execute`。
- `method` 支持 `POST` 和 `GET`，默认是 `POST`。
- `headers` 可选。
- `payload_format` 可选。没有它时，执行器会直接把模型生成的参数作为请求数据发送。
- `"{args}"` 表示完整参数对象；`"{arg1}"` 表示替换某个具体参数值。

推荐插件 `/execute` 接收以下结构，便于一个后端入口分发多个工具：

```json
{
  "func_name": "your_core_function_name",
  "args": {
    "arg1": "value"
  }
}
```

### Subprocess 执行模式

Subprocess 模式适合轻量脚本工具。命令中的 `{参数名}` 会被替换为模型生成的参数值。

```json
{
  "execution": {
    "type": "subprocess",
    "command": "python vault/plugins/your_agent/scripts/run.py --query {query}"
  }
}
```

注意：

- 命令会在当前工作目录下执行。
- 执行器有超时限制。
- 不要把用户输入拼接成危险命令；尽量把复杂逻辑放在脚本内部校验。
- Subprocess 插件仍必须遵守插件目录和数据隔离规则。

## 三、`api.py` 运行时契约

当插件提供 `api.py` 时，主系统会在启动阶段动态导入它，并自动挂载 `router`：

```python
from fastapi import APIRouter
from sqlmodel import SQLModel, Field

router = APIRouter()


class YourRecord(SQLModel, table=True):
    __tablename__ = "vpm_plugin_your_agent_records"

    id: str = Field(primary_key=True)
    title: str


def init_plugin(app_engine):
    SQLModel.metadata.create_all(app_engine)


def uninstall_hook(app_engine):
    # 只清理插件明确拥有的数据库表、明确路径的单个文件或其他私有资源。
    # 不要清理主系统核心表，不要越权处理其他插件的数据。
    pass


@router.post("/execute")
async def execute_task(payload: dict):
    func_name = payload.get("func_name")
    args = payload.get("args", {})

    if func_name == "your_core_function_name":
        return {"status": "success", "result": args}

    return {"status": "error", "message": f"Unsupported function: {func_name}"}
```

规则：

- `router` 会被挂载到 `/api/plugins/{plugin_id}`，所以 `@router.post("/execute")` 的完整路径是 `/api/plugins/{plugin_id}/execute`。
- `init_plugin(app_engine)` 可选；存在时会在插件挂载时调用。适合建表、创建插件私有目录、检查插件私有配置。
- `uninstall_hook(app_engine)` 可选；存在时会在插件卸载前调用。它只应清理插件明确拥有的数据。
- 数据库表名建议使用 `vpm_plugin_{plugin_id}_...` 前缀。
- 插件不要写死模型名称，应读取系统配置或由主系统传入策略。

## 四、前端 UI 协议

插件 UI 使用 Vue 单文件组件，放在插件目录的 `ui/` 下。

### 业务面板

当后端通过事件总线或 WebSocket 下发包含以下字段的消息时，前端会加载对应组件：

```json
{
  "type": "your_event_type",
  "target_panel": "your_agent",
  "target_component": "MainPanel",
  "state": "immersive",
  "data": {}
}
```

规则：

- `target_panel` 必须等于插件目录名，也就是 `plugin_id`。
- `target_component` 对应 `ui/{target_component}.vue`，不需要写 `.vue` 后缀。
- 组件加载地址为 `/plugins/{plugin_id}/ui/{Component}.vue`。
- `state` 可为 `immersive`、`mini` 或省略；省略时默认按沉浸态处理。
- 前端会把业务消息以 `CustomEvent` 形式广播到 `window`，事件名为 `vpm_ws_{target_panel}`。

组件内接收事件示例：

```vue
<script setup>
import { onMounted, onBeforeUnmount, ref } from "vue";
import { SystemConfig, activeAgentComponent, isImmersive } from "vault:useNeuroLink";

const latestPayload = ref(null);

function onPluginMessage(event) {
  latestPayload.value = event.detail;
}

onMounted(() => {
  window.addEventListener("vpm_ws_your_agent", onPluginMessage);
});

onBeforeUnmount(() => {
  window.removeEventListener("vpm_ws_your_agent", onPluginMessage);
});

function closePanel() {
  activeAgentComponent.value = null;
  isImmersive.value = false;
}
</script>
```

`vault:useNeuroLink` 是主系统注入给插件组件的上下文，常用对象包括：

- `SystemConfig.API_BASE`：当前后端 HTTP 地址。
- `SystemConfig.WS_BASE`：当前 WebSocket 地址。
- `activeAgentComponent`：当前业务插件面板。
- `isImmersive`：当前插件面板是否为沉浸态。
- `showToast`：主系统 Toast。
- `sendWsCommand`：向主系统 WebSocket 发送命令。

插件 UI 必须在 `onBeforeUnmount` 中释放自己创建的 `Audio`、`Video`、定时器、事件监听器和网络连接。

### 管理面板

插件中心的“管理”按钮会尝试加载：

```text
vault/plugins/{plugin_id}/ui/Manager.vue
```

如果插件有配置、导入、导出、资产管理等后台能力，建议提供 `Manager.vue`。管理面板可以通过 `SystemConfig.API_BASE` 调用自己的后端接口，例如：

```js
await fetch(`${SystemConfig.API_BASE}/api/plugins/your_agent/list`);
```

## 五、RAG：插件切片，管家托管向量

VPM v2 的 RAG 边界如下：

- 插件负责自己的领域理解、材料整理和切片策略。
- 插件提交给管家的内容应当已经切好，每个切片包含 `chunk_text` 和 `metadata`。
- 管家只负责向量层面的写入、更新、删除，不替插件设计切片方式。
- 插件不得绕过管家改动本地向量存储。
- 管家只接受归属于该插件的来源，并且只影响该插件名下、该插件来源路径下的向量内容。

建议插件把可追踪来源文件放在：

```text
vault/plugins/{plugin_id}/knowledge/
```

向管家提交的逻辑载荷建议保持以下形状：

```json
{
  "command": "RAG_UPSERT",
  "source_file": "{VAULT_ROOT}/plugins/your_agent/knowledge/item_001.md",
  "hash": "your_agent_item_001_v1",
  "payload": [
    {
      "chunk_text": "插件自行切好的领域内容。",
      "metadata": {
        "plugin_id": "your_agent",
        "domain": "your_domain",
        "source_type": "plugin_knowledge"
      }
    }
  ]
}
```

约束：

- `source_file` 或来源标识必须位于或指向当前插件私有目录。
- `metadata.plugin_id` 应等于插件目录名。
- `hash` 应能表达本次内容版本，便于更新时覆盖旧向量。
- 空 `payload` 表示请求管家删除该来源对应的向量记录。
- 插件卸载时，向量注销由管家按 `plugin_id` 和插件私有来源路径执行。

## 六、卸载与安全边界

插件卸载必须遵守以下规则：

- 插件只能清理自己明确拥有的数据库表、配置和单个明确路径的私有文件。
- 需要删除文件时，只处理一个明确路径的文件。
- 不允许批量删除目录。
- 不允许删除或改写其他插件目录。
- 不允许操作主系统核心表、聊天历史、画像记忆、全局配置和其他共享运行时文件。
- 插件产生的 RAG 向量由管家根据插件归属清理，插件不要自行处理底层向量存储。

推荐命名规则：

- SQLite 表：`vpm_plugin_{plugin_id}_records`
- 知识材料：`vault/plugins/{plugin_id}/knowledge/{plugin_id}_xxx.md`
- 静态资产：`vault/plugins/{plugin_id}/assets/{plugin_id}_xxx.ext`
- 后端路由：`/api/plugins/{plugin_id}/...`
- 前端事件：`vpm_ws_{plugin_id}`

## 七、开发检查清单

发布插件前，请至少检查：

- `manifest.json` 是合法 JSON。
- `function.name` 全局唯一。
- `execution.endpoint` 与 `api.py` 路由一致。
- 如果使用 `payload_format`，后端能正确接收包装后的结构。
- 如果提供管理面板，文件名是 `ui/Manager.vue`。
- 如果提供业务面板，后端消息包含正确的 `target_panel` 和 `target_component`。
- 所有插件资源都位于 `vault/plugins/{plugin_id}/` 内。
- 数据库表名带有 `vpm_plugin_{plugin_id}_` 前缀。
- RAG 内容由插件自行切片，但向量写入、更新、删除交给管家。
- 卸载钩子不越权、不处理其他插件或主系统数据。
