# Vault OS

Vault OS 是一个本地 AI 助手与外脑系统。它把大模型对话、长期记忆、RAG 知识检索、工具调用、异步智能体执行、Trace 观测和桌面 UI 组合在一起，用于构建可扩展、可审计、可插件化的个人智能工作台。

如果你想先了解 Vault OS 的产品定位、使用场景和核心体验，请阅读 [产品介绍](PRODUCT.md)。

项目主体由 Python 后端、Vue 3 + Tauri 桌面前端，以及 `vault/plugins` 下的 VPM 插件生态组成。后端负责会话推理、记忆系统、向量库、工具调度、插件安全和 WebSocket 网关；前端负责聊天终端、临时会话、执行观测、知识与记忆管理、画像导入、设置页和插件面板。

## 核心能力

- **AI 对话终端**：支持多线程聊天历史、模型配置读取、黑盒输入输出审计和 WebSocket 流式回传。
- **长期记忆与画像**：基于 SQLite/SQLModel 维护实体、关系、事件源、待审项、L2 实体快照和认知快照。
- **RAG 知识检索**：使用 ChromaDB 持久化向量库，并把检索上下文与画像快照组装进系统提示词。
- **JIT 工具规划**：根据用户意图和可用工具生成执行蓝图，简单闲聊与本地画像问答会尽量绕过工具规划。
- **Trace 执行观测**：记录 trace/span、任务状态、工具调用和快照补偿，前端可展示执行过程。
- **临时会话隔离**：临时会话不读取主记忆、不写入持久状态，结束后会丢弃迟到结果。
- **VPM 插件生态**：支持插件 manifest、工具注册、动态 Vue 面板、权限声明、敏感权限确认和第三方输出隔离。
- **桌面应用壳**：通过 Tauri v2 提供桌面窗口、sidecar 启动、快捷键和本地运行体验。

## 技术栈

- 后端：Python、FastAPI、Uvicorn、OpenAI SDK、SQLModel、SQLite、ChromaDB、DashScope、Requests、DDGS、feedparser、trafilatura、python-frontmatter、python-multipart。
- 前端：Vue 3、Vite、Element Plus、marked、DOMPurify、highlight.js、vue3-sfc-loader。
- 桌面壳：Rust、Tauri v2、Tauri shell/opener/global-shortcut 插件。
- 插件：VPM manifest、可选 FastAPI router、Vue 单文件组件、HTTP 或 subprocess 工具执行。
- 打包：PyInstaller `vault_engine.spec` + Tauri external sidecar。

## 目录导览

```text
.
├── main.py                 # 核心引擎：配置、LLM、RAG、记忆、JIT、画像导入、工具执行入口
├── server.py               # FastAPI 网关：动态端口、WebSocket、Trace API、插件路由和权限交互
├── agent_runner.py         # 异步智能体任务入口，在线程池中执行重型推理
├── core_bus.py             # 事件总线，隔离主会话、临时会话和插件 UI 消息
├── trace_system.py         # Trace/span 记录、事件推送、超时看门狗和快照查询
├── memory_system.py        # 画像、记忆、实体关系、待审和 L2 快照内核
├── memory_rules.py         # 瞬时交互识别与 JIT 意图门控规则
├── plugin_security.py      # 插件安全、权限确认、脱敏和不可信输出包裹
├── tool_registry.py        # 内置工具、外部工具和插件工具发现
├── tool_executor.py        # 工具执行器：搜索、知识检索、UI 指令、HTTP/subprocess 插件
├── rag_assembler.py        # 组装画像、认知快照和向量检索上下文
├── chroma_engine.py        # ChromaDB 向量库封装
├── db.py                   # SQLModel 数据库入口
├── chat-ui/                # Vue 3 + Vite + Tauri 前端
├── tests/                  # 单元测试：记忆、插件安全、JIT 门控、画像导入、搜索等
├── vault/                  # 运行时数据根目录：配置、数据库、Trace、知识库、插件
├── vault_seed/             # 首次启动或空 vault 初始化数据
├── requirements.txt        # 后端 Python 依赖
└── vault_engine.spec       # PyInstaller sidecar 打包配置
```

## 快速开始

### 1. 安装后端依赖

建议使用虚拟环境：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

后端配置保存在 `vault/system_config.json`。请在本地配置模型、API Key、base URL 和 embedding 参数，不要把真实密钥提交到版本库。

### 2. 启动后端

```powershell
python server.py
```

后端会在 `8000-8999` 范围内选择可用端口，并写入：

- `vault/.server_port`：当前后端端口。
- `vault/.run_token`：当前运行会话 token，前端连接 WebSocket 时使用。

### 3. 启动前端开发服务

```powershell
cd chat-ui
npm install
npm run dev
```

Vite 开发服务默认由 Tauri 配置使用 `http://localhost:1420`。

### 4. 启动桌面开发模式

```powershell
cd chat-ui
npm run tauri -- dev
```

桌面开发模式会使用 Tauri v2 启动窗口。生产模式下，Tauri 会启动 `vault_engine` sidecar，并通过运行环境定位真实的 `VAULT_ROOT`。

## 配置与运行时数据

`VAULT_ROOT` 是运行时数据的唯一根目录。开发环境通常是项目根目录下的 `vault/`，打包环境可能由环境变量或可执行文件位置决定。业务代码应通过 `VAULT_ROOT` 定位运行时文件，不要硬编码相对 `vault/...` 路径。

常见运行时文件：

- `vault/system_config.json`：模型、API Key、embedding 和 base URL 配置。
- `vault/chat_history.json`：聊天历史。
- `vault/vault_core.db`：主数据库，包含记忆、画像、实体关系和待审项。
- `vault/vault_trace.db`：Trace 运行记录和 span 事件。
- `vault/plugin_permissions.json`：第三方插件敏感权限授权记录。
- `vault/blackbox_raw.jsonl`：聊天输入输出审计日志。
- `vault/knowledge/vector_store/`：ChromaDB 向量库。
- `vault/plugins/`：VPM 插件目录。

这些文件大多属于本地运行态数据，通常不应提交真实内容、密钥、token 或个人隐私数据。

## 测试

当前测试以 Python `unittest` 为主：

```powershell
python -m unittest discover tests
```

测试覆盖 JIT 意图门控、记忆缓冲池、认知快照、插件安全、画像导入、实体隔离、关系图、姓名冲突和网络搜索工具等关键路径。

## VPM 插件开发

插件位于 `vault/plugins/{plugin_id}/`，目录名就是系统识别使用的 `plugin_id`。插件通常包含：

- `manifest.json`：插件中心展示信息、工具契约、执行方式和安全声明。
- `api.py`：可选后端 API、生命周期钩子或数据初始化逻辑。
- `ui/*.vue`：可选 Vue 面板，由前端动态加载。
- `tools/*.json`：可选额外工具描述。
- `knowledge/`、`assets/`、`audio/` 等插件私有资源目录。

插件必须声明 `security.trust`、`security.permissions` 和 `security.sensitive_reason`。运行时会重新归一化安全字段，第三方插件不能仅靠 manifest 自称 first-party 来获得信任。

更完整的插件协议、manifest 示例和安全规则见 `vault/plugins/README.md`。

## 打包说明

后端 sidecar 使用 PyInstaller 配置：

```powershell
pyinstaller vault_engine.spec
```

Tauri 配置位于 `chat-ui/src-tauri/tauri.conf.json`，其中 `externalBin` 指向 `bin/vault_engine`。完整桌面打包需要准备 Python sidecar、Node/Vite 前端依赖、Rust/Tauri 工具链和平台相关打包环境。

## 协作注意事项

- 修改前先查看 `git status`，不要回滚或覆盖他人已有改动。
- 不要绕过 `VAULT_ROOT` 直接读写运行时数据路径。
- 修改临时会话逻辑时，必须保持“不读主记忆、不写持久状态、结束后丢弃迟到结果”的隔离语义。
- 修改画像导入时，必须保持“预览后提交”的两阶段流程。
- 修改第三方插件权限、UI token、内部 token、脱敏规则或不可信输出包裹时，需要同步更新插件文档并补充测试。
- 修改插件安全、插件卸载、RAG 删除、笔记删除、资产导出清理逻辑时，应逐路径审查，避免误删共享数据或放宽第三方插件边界。
- 禁止批量删除文件或目录。不要使用 `del /s`、`rd /s`、`rmdir /s`、`Remove-Item -Recurse`、`rm -rf`。如需删除多个文件，应先停止并让用户手动确认处理。
