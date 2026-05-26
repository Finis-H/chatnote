# 项目说明与协作指南

## 基本定位

这是一个名为 **Vault OS** 的本地 AI 助手/外脑系统。项目主体由 Python 后端、Vue 3 + Tauri 桌面前端、以及 `vault/plugins` VPM 插件生态组成。后端负责大模型对话、记忆/RAG、工具调用、异步智能体调度、Trace 观测和 WebSocket 网关；前端负责桌面 UI、聊天终端、知识列表、记忆审核、画像导入、设置页和插件面板展示。

本仓库当前是活跃开发工作区。开始修改前先检查 `git status`，不要回滚或覆盖用户已有改动；本次文档检查时已存在多处未提交变更与未跟踪文件。

## 目录概览

- `main.py`：核心引擎，定义 `VaultOS_Terminal`，负责配置加载、LLM 客户端、向量库、RAG 组装、SQLite 画像内核、JIT 任务规划、工具注册器与执行器。
- `server.py`：FastAPI 网关入口，启动动态端口，写入 `vault/.server_port` 和 `vault/.run_token`，提供 WebSocket、Trace API、插件 UI 文件、RAG 摄入和插件挂载/管理接口。
- `agent_runner.py`：异步智能体任务入口，把重型 AI 推理放入独立线程池执行，并通过事件总线向前端流式回传状态、Trace 和结果。
- `trace_system.py`：运行 Trace 系统，负责 trace/span 上下文、事件持久化、事件总线推送、超时看门狗和快照查询。
- `memory_system.py`：画像/记忆/认知底层内核，包含实体、关系、事件源、待审、L2 实体快照、L2 认知快照、路由和结算服务。
- `memory_rules.py`：瞬时交互识别规则，用于避免把提问、搜索、播放、删除等一次性动作误写入长期记忆。
- `db.py`：SQLModel 数据库入口，绑定 `vault/vault_core.db`，并确保记忆系统表被注册与初始化。
- `chroma_engine.py`：ChromaDB 向量库封装，持久化到 `vault/knowledge/vector_store`，embedding 配置来自系统配置。
- `rag_assembler.py`：从 SQLite L2 快照和检索上下文组装最终系统提示词。
- `tool_registry.py`：注册内置工具，并扫描 `vault/tools/*.json`、插件 `manifest.json` 和插件 `tools/*.json`。
- `tool_executor.py`：执行内置工具与 VPM 工具，支持 `web_search`、`search_local_knowledge`、`control_ui_layout`、HTTP 插件和 subprocess 插件。
- `chat-ui/`：Vue 3 + Vite + Tauri 前端。`src/App.vue` 是主框架，`src/composables/useNeuroLink.js` 是全局状态与 WebSocket 中心。
- `chat-ui/src-tauri/src/main.rs`：Tauri v2 桌面入口，提供 `get_run_token`、`get_server_port`，生产模式启动 `vault_engine` sidecar，退出时清理 sidecar 进程树。
- `vault/`：运行时数据根目录，包含配置、聊天历史、数据库、Trace、知识库、向量库和插件。代码中统一通过 `VAULT_ROOT` 定位。
- `vault_seed/`：首次启动或运行时 vault 为空时用于初始化的种子数据。
- `vault/plugins/`：VPM 插件目录。插件一般包含 `manifest.json`、可选 `api.py`、`ui/*.vue`、`tools/`、`knowledge/`、`assets/` 等。
- `vault/plugins/music_agent/`：现有示例/官方插件，提供音乐管理接口、Vue 面板、私有资产和 `play_music_playlist` 工具。
- `tests/`：测试目录。新增后端行为时优先在这里补充针对性测试。
- `dist/`、`build/`、`__pycache__/`：构建或缓存产物，通常不应手动改动。

## 技术栈与依赖

- 后端：Python、FastAPI、Uvicorn、OpenAI SDK、ChromaDB、DashScope、SQLModel、Requests、DDGS、feedparser、trafilatura、python-frontmatter、python-multipart 等。
- 前端：Vue 3、Vite、Element Plus、marked、DOMPurify、highlight.js、vue3-sfc-loader、Tauri v2。
- 桌面壳：Rust + Tauri v2，使用 shell、opener、global-shortcut 插件。
- 打包：`vault_engine.spec` 使用 PyInstaller 从 `server.py` 打包 Python sidecar，并把 `vault_seed/` 作为数据资源；Tauri 配置绑定 `bin/vault_engine`。

注意：根目录没有 `package.json`，前端依赖与脚本在 `chat-ui/package.json`。根目录 `requirements.txt` 已覆盖当前主要后端运行依赖，但新环境、打包环境和平台相关依赖仍需结合源码 import 与 `vault_engine.spec` 检查。

## 常用运行方式

- 后端开发：通常运行 `python server.py`。启动后会自动选择 `8000-8999` 范围内空闲端口，并写入 `vault/.server_port` 和 `vault/.run_token`。
- 前端开发：进入 `chat-ui` 后运行 `npm run dev`，或通过 Tauri 开发命令启动。Tauri 配置的 devUrl 是 `http://localhost:1420`。
- 前后端通信：前端通过 Tauri command 读取 `.run_token` 和 `.server_port`，再连接 `ws://127.0.0.1:{port}/ws/{token}`。
- 前端构建：`chat-ui/package.json` 提供 `npm run build`、`npm run preview`、`npm run tauri`。
- 桌面生产模式：Tauri 启动 `vault_engine` sidecar，并通过环境变量把真实 `VAULT_ROOT` 传给后端。

## 后端核心机制

- `VAULT_ROOT` 是运行时数据的唯一根。开发环境通常指向项目根下的 `vault`，打包环境以可执行文件目录或环境变量为准。不要绕过它直接写相对 `vault/...` 路径。
- `VaultOS_Terminal` 初始化时加载 `vault/system_config.json`，配置里保存 chat model、embedding model、API Key 和 base URL。业务代码不要写死具体模型名称，应读取配置键。
- 启动时会初始化向量库、RAG 组装器、记忆门控器、工具注册器和工具执行器，并执行一次记忆待审结算。
- `agent_runner.py` 使用独立线程池运行 `vault_os.get_response()`，避免长时间模型调用阻塞 WebSocket 主循环。任务开始、结束、超时和异常都应通过事件总线回传。
- `main.py` 的 JIT 编译器会根据用户指令和可用工具生成执行蓝图。简单闲聊直接进入语言模型；复杂任务可调度工具步骤并把结果写入黑板，再由最终回复总结。
- `trace_system.py` 把 trace run 和 span event 持久化到 `vault/vault_trace.db`，通过 `trace_event` 推送给前端，并提供 `/api/traces/{trace_id}/snapshot` 和 `/api/traces/thread/{thread_id}/latest` 用于快照补偿。
- `memory_system.py` 使用 SQLite 作为唯一事实源，当前包含 L3 事件源、`event_reviews` 待审、实体关系、L2 实体快照、L2 认知快照和 3 天待审自动结算。
- `memory_rules.py` 会过滤瞬时交互，防止“帮我查一下”“播放”“删除”“推荐”等请求被误当作长期事实。
- `rag_assembler.py` 从 SQLite L2 快照读取 Boss 画像、实体关系和认知状态，并与向量检索上下文组装系统提示词。
- `tool_registry.py` 负责工具发现；`tool_executor.py` 负责工具执行、HTTP 端点补全、subprocess 调用、内置搜索、UI 控制和 Trace 埋点。

## 前端核心机制

- `chat-ui/src/composables/useNeuroLink.js` 是前端状态中心，维护当前视图、消息、配置、插件列表、记忆队列、Trace 队列、动态插件组件和 WebSocket 连接。
- `connectWebSocket()` 建立连接后请求配置、记忆和历史记录；断线后会自愈重连。
- Trace 前端状态包含 `traceEvents` 和 `activeTraceId`。前端会接收 `trace_event`，在终态或看门狗触发时拉取 Trace 快照进行补偿。
- `App.vue` 管理主视图、侧边栏、输入框、插件动态侧栏/沉浸面板、删除确认弹窗、全局 Toast 和快捷键。
- 主视图包括聊天、新闻/收藏知识列表、笔记详情、记忆同步、画像导入、设置、插件中心。
- 插件 UI 通过 `loadVpmComponent(plugin_id, component)` 动态加载。后端可通过 WebSocket 下发 `ui_command` 或带 `target_panel`、`target_component` 的插件消息打开侧栏/沉浸面板。
- 快捷键：`Alt+V` 用于显示/隐藏 Tauri 窗口，`Escape` 隐藏窗口。

## VPM 插件约定

VPM 当前按 `vault/plugins/README.md` 的 v2 规则维护。该文件是插件开发的详细标准，修改插件协议前应同步更新它和本文件。

- 插件放在 `vault/plugins/{plugin_id}/` 下，目录名就是系统识别用的 `plugin_id`。
- `manifest.json` 同时用于插件中心展示和工具注册，使用 OpenAI Tool Calling 风格描述 `type/function/parameters`，并通过 `execution` 指定执行方式。
- HTTP 插件 endpoint 通常写成 `/api/plugins/{plugin_id}/execute`，运行时会被补成本次后端端口。
- `api.py` 是可选的。提供时可声明 `router`、`init_plugin(app_engine)` 和 `uninstall_hook(app_engine)`，用于后端路由、建表和生命周期处理。
- 插件 UI Vue 文件由后端 `/plugins/{plugin_id}/ui/{file_name}` 提供，前端动态加载。插件中心“管理”按钮默认尝试加载 `ui/Manager.vue`。
- 插件应隔离数据和命名空间。数据库表、生成文件、知识材料、静态资产应带插件名前缀或位于插件目录下，便于审计和卸载。
- 插件负责自己的领域逻辑、材料整理和切片；主系统负责向量写入、更新、删除和卸载边界控制。插件不要直接操作底层向量库。
- 运行中新增插件目录后，插件中心可以扫描到 `manifest.json`，但后端路由和工具注册通常需要重启或重新初始化后才会生效。

## 数据与持久化

- `vault/system_config.json`：模型、API Key、embedding 和 base URL 配置。
- `vault/chat_history.json`：多线程/多上下文聊天历史。
- `vault/vault_core.db`：SQLModel/SQLite 主数据库。画像系统的实体、关系、事件源、待审、L2 快照和元信息都在这里。
- `vault/vault_trace.db`：Trace 运行记录和 span 事件数据库。
- `vault/blackbox_raw.jsonl`：聊天输入输出审计日志。
- `vault/knowledge/vector_store/`：ChromaDB 向量库文件。
- `vault/plugins/{plugin_id}/`：插件私有代码、配置、知识材料和资产。

## 代码风格与注意事项

- 项目中文注释和文案很多，文件应按 UTF-8 处理；Windows 终端编码不对时可能显示乱码，不代表源码一定损坏。
- 修改前先读相关模块，优先延续现有架构和命名，不要采用粗暴补丁式修改。
- 不要绕过 `VAULT_ROOT` 直接写相对 `vault/...` 路径，已有 audit hook 会提示风险。
- 不要写具体模型名称，使用配置中的相对键或当前 `vault/system_config.json` 配置。
- 修改插件卸载、RAG 删除、笔记删除、资产导出清理逻辑时要逐路径审查，避免误删 `vault` 下共享数据。
- 当前 `server.py` 的插件卸载路径仍存在递归删除插件目录的实现，后续应优先改造为更安全、可审计、逐项确认的卸载策略；在改造完成前，不要扩大这类逻辑的适用范围。
- 运行测试或构建前注意现有工作区可能包含用户未提交改动；不要格式化或重写无关文件。

## 本仓库操作限制

禁止批量删除文件或目录。不要使用 `del /s`、`rd /s`、`rmdir /s`、`Remove-Item -Recurse`、`rm -rf`。需要删除文件时，只能一次删除一个明确路径的文件，例如 `Remove-Item "C:\path\to\file.txt"`。如果需要批量删除文件，应停止操作并询问用户，让用户手动删除。
