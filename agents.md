# 项目说明与协作指南

## 基本定位

这是一个名为 **Vault OS** 的本地 AI 助手/外脑系统。项目主体由 Python 后端、Vue 3 + Tauri 桌面前端、以及 `vault/plugins` 插件生态组成。后端负责大模型对话、记忆/RAG、工具调用、插件调度和 WebSocket 网关；前端负责桌面 UI、聊天终端、知识列表、记忆暂存、设置页和插件面板展示。

## 目录概览

- `main.py`：核心引擎，定义 `VaultOS_Terminal`，负责加载配置、初始化 LLM、向量库、RAG 组装器、SQLite 画像内核、工具注册器与执行器。
- `server.py`：FastAPI 网关入口，启动动态端口，写入 `vault/.server_port` 和 `vault/.run_token`，提供 WebSocket、插件 UI 文件、RAG 摄入、插件管理等接口。
- `chat-ui/`：Tauri + Vue 3 前端。`src/App.vue` 是主框架，`src/composables/useNeuroLink.js` 维护全局状态、WebSocket 连接和视图切换。
- `chat-ui/src-tauri/`：Tauri/Rust 外壳。开发模式只启动前端；生产模式会启动 `vault_engine` sidecar，并在退出时清理 Python 进程树。
- `vault/`：运行时数据根目录，包含配置、记忆、知识库、向量库、插件等。代码中统一通过 `VAULT_ROOT` 定位。
- `vault/plugins/`：VPM 插件目录。插件一般包含 `manifest.json`、`api.py`、可选 `ui/*.vue`、`tools/`、`assets/`。
- `vault/plugins/music_agent/`：现有示例/官方插件，注册 `play_music_playlist` 工具并提供 Vue 面板。
- `dist/`、`build/`、`__pycache__/`：构建或缓存产物，通常不应手动改动。

## 技术栈与依赖

- 后端：Python、FastAPI、Uvicorn、OpenAI SDK、ChromaDB、DashScope、SQLModel、Requests、DDGS、feedparser、trafilatura、python-frontmatter 等。
- 前端：Vue 3、Vite、Element Plus、marked、DOMPurify、highlight.js、vue3-sfc-loader、Tauri v2。
- 桌面壳：Rust + Tauri v2，使用 shell、opener、global-shortcut 插件。
- 打包：`vault_engine.spec` 使用 PyInstaller 从 `server.py` 打包 Python sidecar；Tauri 配置把 `vault/` 作为资源并绑定 `bin/vault_engine`。

注意：根目录 `requirements.txt` 目前只列出少量依赖，不覆盖代码里实际 import 的全部后端依赖。新环境安装时要结合源码 import 和打包 spec 补齐。

## 常用运行方式

- 后端开发：通常运行 `python server.py`。启动后会自动选择 `8000-8999` 范围内空闲端口，并写入 `vault/.server_port`。
- 前端开发：进入 `chat-ui` 后运行 `npm run dev` 或通过 Tauri 开发命令启动。Tauri 配置的 devUrl 是 `http://localhost:1420`。
- 前后端通信：前端通过 Tauri command 读取 `.run_token` 和 `.server_port`，再连接 `ws://127.0.0.1:{port}/ws/{token}`。
- 前端构建：`chat-ui/package.json` 提供 `npm run build`、`npm run preview`、`npm run tauri`。

## 后端核心机制

- `VAULT_ROOT` 是运行时数据的唯一根。开发环境通常指向项目根下的 `vault`，打包环境则以可执行文件目录为基准。
- `VaultOS_Terminal` 初始化时会加载 `vault/system_config.json`。默认模型配置指向 DashScope 兼容 OpenAI 接口，包含 chat model 和 embedding model 配置。
- `chroma_engine.py` 使用 ChromaDB 持久化向量库，默认路径是 `vault/knowledge/vector_store`，collection 名为 `vault_core_v3`，embedding 走 DashScope。
- `memory_system.py` 是画像/记忆/认知底层内核，使用 SQLite 作为唯一事实源，包含 L3 事件源、审核表、L2 实体快照、L2 认知快照、L1 路由和结算服务。
- `rag_assembler.py` 从 SQLite L2 快照读取 Boss 画像与认知状态，并与检索上下文组装成系统提示词。
- `tool_registry.py` 注册内置工具，并扫描 `vault/tools/*.json` 与 `vault/plugins/*/manifest.json`、`tools/*.json` 加载外部工具。
- `tool_executor.py` 执行内置工具，包括 `web_search`、`search_local_knowledge`、`control_ui_layout`，也支持 VPM 插件的 `subprocess` 与 `http` 执行方式。

## 前端核心机制

- `useNeuroLink.js` 是前端状态中心，维护当前视图、消息、配置、插件列表、记忆队列、动态插件组件等。
- `connectWebSocket()` 建立连接后会请求配置、记忆和历史记录。
- 主视图包括聊天、新闻/收藏知识列表、笔记详情、记忆同步、画像导入、设置、插件中心。
- 插件 UI 通过 `loadVpmComponent(plugin_id, component)` 动态加载，后端通过 WebSocket 下发 `ui_command` 或带 `target_panel` 的插件消息来打开侧栏/沉浸面板。
- 快捷键：`Alt+V` 用于显示/隐藏 Tauri 窗口，`Escape` 隐藏窗口。

## VPM 插件约定

- 插件放在 `vault/plugins/{plugin_id}/` 下。
- `manifest.json` 使用 OpenAI Tool Calling 风格描述 `type/function/parameters`，并通过 `execution` 指定执行方式。
- HTTP 插件 endpoint 通常写成 `/api/plugins/{plugin_id}/execute`，运行时会被补成当前本地后端端口。
- 插件 UI Vue 文件由后端 `/plugins/{plugin_id}/ui/{file_name}` 提供，前端动态加载。
- 插件应隔离数据和命名空间。数据库表、生成文件、知识材料应带插件名前缀或位于插件目录下，便于卸载和审计。

## 数据与持久化

- `vault/system_config.json`：模型、API Key、embedding 配置。
- `vault/chat_history.json`：多线程/多上下文聊天历史。
- `vault/vault_core.db`：SQLModel/SQLite 数据库。画像系统的 `entities`、`memory_events`、`event_reviews`、`l2_entity_snapshots`、`l2_cognitive_snapshots`、`memory_meta` 等表都在这里。
- `vault/blackbox_raw.jsonl`：聊天输入输出审计日志。
- `vault/knowledge/vector_store/`：ChromaDB 向量库文件。

## 代码风格与注意事项

- 项目中文注释和文案很多，文件应按 UTF-8 处理；Windows 终端编码不对时可能显示乱码，不代表源码一定损坏。
- 不要绕过 `VAULT_ROOT` 直接写相对 `vault/...` 路径，已有 audit hook 会提示风险。
- 修改插件卸载、RAG 删除、文件清理逻辑时要格外谨慎，避免误删 `vault` 下共享数据。
- 不要写具体模型名称，使用相对名称，调用实际在`vault/system_config.json`配置的模型。
- 不要采用粗暴补丁式修改代码，从系统架构层面出发思考修改方式。

## 本仓库操作限制

禁止批量删除文件或目录。不要使用 `del /s`、`rd /s`、`rmdir /s`、`Remove-Item -Recurse`、`rm -rf`。需要删除文件时，只能一次删除一个明确路径的文件，例如 `Remove-Item "C:\path\to\file.txt"`。如果需要批量删除文件，应停止操作并询问用户，让用户手动删除。
