# Vault OS 当前架构基线

> 时间边界：清理前标签 vault-os-pre-archive-20260716 对应的源码版本。本文件描述当前实现，不把产品愿景、Figma 静态稿或未验证 Windows 候选写成已验证架构。
>
> 证据：当前源码、配置、docs/archive/01-final-snapshot.md、docs/archive/02-audit-manifest.md、docs/archive/04-cleanup-execution-log.md。未重新运行服务、Build、测试、Docker、Tauri 或安装包。

## 1. 实际入口与边界

~~~mermaid
flowchart LR
  UI["Vue 3 / Vite 前端<br/>chat-ui/src"] <-->|"带 token 的 WebSocket"| API["FastAPI<br/>server.py"]
  UI <-->|"Tauri invoke<br/>port/token"| DESKTOP["Tauri 壳<br/>src-tauri/src/main.rs"]
  DESKTOP -->|"sidecar + VAULT_ROOT"| API
  API --> ENGINE["VaultOS_Terminal<br/>main.py"]
  API --> BUS["NeuroLinkBus<br/>core_bus.py"]
  ENGINE --> MEM["Memory / SQLite<br/>memory_system.py, db.py"]
  ENGINE --> RAG["Chroma 向量库<br/>chroma_engine.py"]
  ENGINE --> TOOLS["ToolRegistry / ToolExecutor"]
  TOOLS --> PLUGIN["VAULT_ROOT/plugins<br/>动态插件"]
  ENGINE --> TRACE["TraceEmitter / SQLite<br/>trace_system.py"]
  BUS --> API
  API --> UI
~~~

| 层级 | 当前实现 | 证据与边界 |
| --- | --- | --- |
| 后端进程入口 | server.py 创建 FastAPI、实例化 VaultOS_Terminal、动态选取端口并启动 uvicorn。 | server.py；docs/archive/01-final-snapshot.md 仅记录最小启动 8 秒存活。 |
| 前端入口 | chat-ui/src/App.vue 异步加载 Terminal、Knowledge、Note、Memory、Settings、VpmCenter、ProfileImport 等视图，并由 useNeuroLink.js 管理共享连接/状态。 | chat-ui/src/App.vue；chat-ui/src/composables/useNeuroLink.js。 |
| 桌面入口 | Tauri 在 release 模式创建本地 vault 路径、启动 vault_engine sidecar，并把 VAULT_ROOT 注入 sidecar；前端通过 invoke 取得 .run_token 与 .server_port。 | chat-ui/src-tauri/src/main.rs；chat-ui/src-tauri/tauri.conf.json。 |
| 当前验证边界 | 前端 Build 与临时 VAULT_ROOT 下的最小后端启动曾通过。 | docs/archive/01-final-snapshot.md。WebSocket、桌面壳、Tauri bundle、安装/卸载均未验证。 |

## 2. 前后端通信与会话状态

| 机制 | 当前实现 | 事实边界 |
| --- | --- | --- |
| WebSocket | 服务端唯一主通道是 /ws/{client_token}；令牌不匹配以 1008 关闭。连接后下发 history_all，并消费 NeuroLinkBus 事件。 | server.py 的 websocket_endpoint；该连接认证不是完整的外部身份/多用户认证结论。 |
| 状态与命令 | WebSocket 处理聊天、临时会话、记忆读取/决策、设置、画像导入、插件列表和卸载等 type 消息。 | server.py 的 websocket_endpoint；chat-ui/src/composables/useNeuroLink.js。接口实际兼容性未在本阶段重测。 |
| HTTP API | 已有 Trace snapshot/latest、RAG ingest、插件 RAG search 与插件 UI 文件路由；动态插件还可通过 include_router 挂载。 | server.py。插件路由是运行期导入，静态检索不能覆盖其全部行为。 |
| 事件总线 | NeuroLinkBus 使用 asyncio.Queue；后台 Agent/线程可通过 publish_sync 回到 WebSocket 消费者。 | core_bus.py；server.py。当前为进程内队列，不是跨进程消息系统。 |
| 临时会话 | TempVaultSession 建立独立 threads，移除 search_local_knowledge，禁用记忆/设置/删除/卸载等命令。 | main.py 的 TempVaultSession；server.py 的 temp command block。历史 Eval 记录临时会话 5 项通过，但本阶段未重测。 |

## 3. 主会话、记忆与 RAG

| 组件 | 当前实现 | 数据边界与风险 |
| --- | --- | --- |
| 主 Agent | VaultOS_Terminal 读取配置/聊天历史，初始化向量库、RAGAssembler、HabitExtractor、MemoryGatekeeper、ToolRegistry 和 ToolExecutor。对输入执行记忆预读、意图分类、可选 JIT 与最终 LLM 调用。 | main.py。聊天历史、blackbox_raw.jsonl、配置都位于 VAULT_ROOT；它们是运行时私有数据，本阶段未读取。 |
| 长期记忆 | MemoryRepository 定义实体、关系、事件、待审和快照模型；MemoryGatekeeper 进行路由、待审、合并和过期处理。 | memory_system.py；db.py。Eval 已记录 PII、偏见与失败可见性的风险，不能表述为完整安全记忆方案。 |
| 画像导入 | 先标准化并进入 READY 状态，用户确认后才调用记忆事件提取/提交；待审事件未完成时维持锁定。 | main.py 的 prepare_profile_import、commit_profile_import。该路径有源码和测试，但本基线记录独立测试在隔离环境未能执行。 |
| 向量/RAG | VaultVectorDB 由 VaultOS_Terminal 初始化；receive_knowledge_payload 按来源删除/写入 chunk；ToolExecutor 的 search_local_knowledge 返回带来源的结果。 | main.py；chroma_engine.py；tool_executor.py。RAG 内容没有独立的不可信包装，相关 Eval 风险列入 Backlog。 |
| Prompt 组装 | RAGAssembler 组合本地画像、认知快照和任务黑板；对第三方插件输出写有不可信数据约束。 | rag_assembler.py。该约束不能证明 RAG 文本同样被隔离。 |

## 4. Agent、工具、Trace 与安全

| 组件 | 当前实现 | 已知边界 |
| --- | --- | --- |
| JIT/DAG | 主会话按意图选择 DIRECT_CHAT 或 JIT 蓝图；READY 蓝图以依赖关系提交线程池执行，并先做插件权限预检。 | main.py。取消、部分失败与运行状态一致性仍有 Eval 缺口。 |
| 工具 | ToolRegistry 注册 web_search、本地 RAG，并扫描 VAULT_ROOT/plugins 下 manifest.json 和 tools/*.json；ToolExecutor 支持内置、subprocess 与 HTTP 插件。 | tool_registry.py；tool_executor.py。插件是动态依赖；未证明静态清单等同实际可执行工具集合。 |
| Trace | TraceEmitter 保存 trace_runs 和 trace_events，构建 tree，并暴露 snapshot/latest thread 查询；主链路使用 traced_span。 | trace_system.py；server.py。当前端到端 Trace 没有在本阶段重新验证。 |
| 插件权限 | PluginSecurityManager 区分第一方 allowlist 与第三方，检测敏感权限和参数，生成脱敏预览，请求 deny/allow_once/allow_session 决策，并包装第三方输出为不可信数据。 | plugin_security.py；chat-ui/src/App.vue；tests/test_plugin_security.py。历史 Eval 指出敏感参数脱敏和服务端令牌风险；不能声称第三方插件边界已完整验证。 |
| 插件卸载 | 服务端可清理插件知识向量、执行插件卸载钩子并删除插件目录；UI 显示不可撤销影响。 | server.py；chat-ui/src/views/VpmCenterView.vue；docs/assets/screenshots/04-plugin-permission-danger-dialog.png。该高风险路径未在本阶段执行或重测。 |

## 5. 配置、打包与运行时数据

| 范围 | 当前事实 | 动态/运行时依赖风险 |
| --- | --- | --- |
| VAULT_ROOT | main.py 优先使用环境变量，否则使用源码/sidecar 相邻的 vault；空 vault 时从 vault_seed 复制初始化内容。 | vault/ 是用户配置、聊天、Trace、数据库、插件等私有运行时数据根。本阶段不得读取、移动或清理。 |
| vault_seed | 被 main.py 作为空 vault 初始化来源，且 vault_engine.spec 将其作为 PyInstaller datas。 | 虽受 Git 忽略，仍可能是首次启动/sidecar 运行输入；不得当作无引用文件删除。 |
| 插件目录 | PLUGINS_DIR 指向 VAULT_ROOT/plugins；服务器、注册表和前端 VPM loader 都在运行时按插件目录加载内容。 | 动态插件与其依赖不能由普通 Python/JS import 检索完全证明；需单独审查。 |
| Tauri sidecar | bundle.externalBin 指向 bin/vault_engine，resources 指向 bin/_internal/；release main.rs 启动 sidecar。 | chat-ui/src-tauri/bin/vault_engine-x86_64-pc-windows-msvc.exe 与 bin/_internal/ 是当前打包候选的必要动态输入，按清理记录保留。 |
| 应用配置 | system_config.json、.run_token、.server_port、聊天历史和 blackbox 日志写入 VAULT_ROOT。 | 配置与运行产物可能含密钥或个人数据；仅记录路径，不在归档文档写入内容。 |
| 容器化 | 根 Dockerfile COPY 根目录 data_pipeline.py、llm_engine.py，但文件只在 discard/；静态上无法以当前工作树完成 Docker Build。 | Dockerfile 不是当前可验证部署方案。是否仍有外部容器部署待 06-decommission 人工确认。 |

## 6. 已知技术风险与待确认项

1. 完整后端单进程测试在最近隔离记录中为 38 通过、11 错误；多个模块互相污染 sys.modules stub，两个 Web 搜索断言仍失败。
2. Windows candidate 源码、sidecar 与 NSIS 候选均未经过 Tauri bundle、签名、安装、卸载或升级验证。
3. docs/EVAL_REPORT.md 与 docs/ARCHITECTURE.md 的 Eval 汇总分别为 33/2/10 和 33/1/11；这是待人工确认的事实冲突，不在本阶段改写原文。
4. 仓库未发现可定位的 Figma 原文件或 URL；四张导出只能作为 synthetic、redacted、fixture-only 设计输入。
5. GitHub Release/Actions、域名、模型 API、存储、账单和外部自动化的存在及状态未由仓库证实，留待 06-decommission。
