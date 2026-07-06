# Vault OS

> 文档定位：本文保留原根目录 README 的开发者安装、运行、构建、项目结构和协作说明。项目入口页见 [../README.md](../README.md)，产品说明见 [PRODUCT.md](PRODUCT.md)，产品案例见 [PRODUCT_CASE.md](PRODUCT_CASE.md)。

Vault OS 是一个本地 AI 工作台，聚焦长期记忆、知识检索、插件执行与 Trace 可观测协作。

它不是普通聊天框，而是一个正在产品化的本地桌面 AI 系统：后端负责会话推理、记忆/RAG、工具调度、Trace 和插件安全；前端负责主控终端、Command Console、AgentDock、知识/记忆视图、设置和插件中心。

## 当前状态

Vault OS 目前处于活跃开发和产品化打磨阶段。主控体验 v1 的产品化骨架已阶段性完成，包含分组导航、Command Console、Trace 基础观测面板、AgentDock 和统一设计 token。

仍需继续推进的部分包括：全站业务页一致性、高风险确认体系化、更多基础组件覆盖、更完整的 Trace 复盘和作品集材料归档。不要把当前状态理解为“全站改版完成”或“开箱即用商业产品”。

## 核心亮点

- **Local-first AI workbench**：运行时数据围绕本地 `vault/` 组织，便于掌控、迁移和审计。
- **Long-term memory**：基于 SQLite/SQLModel 维护画像、实体关系、事件源、待审项和 L2 快照。
- **RAG / knowledge workspace**：使用 ChromaDB 持久化向量库，并把检索上下文与画像快照组装进系统提示词。
- **Plugin / tool execution**：通过工具注册器、执行器和 VPM 插件接入搜索、知识检索、UI 指令、HTTP/subprocess 插件能力。
- **Trace observability**：记录 trace/span、任务状态、耗时和快照补偿，前端可查看执行步骤。
- **Command Console**：底部主控命令入口，保留命令提示符、发送按钮、回车提示和焦点状态。
- **AgentDock**：插件/Agent 任务面板宿主，支持 dock、mini、focus 形态和任务状态表达。
- **Tauri desktop UI**：Vue 3 + Vite + Tauri v2 桌面前端，生产模式通过 sidecar 启动后端。

## 产品化改版亮点

- 建立 `chat-ui/src/assets/cyber-theme.css` 设计 token，覆盖颜色、背景层级、边框、圆角、间距、阴影、focus 和动效。
- 左侧导航从扁平列表收敛为执行、知识、系统分组。
- 顶部展示连接状态，帮助判断 WebSocket / 后端状态。
- 底部输入区收敛为 Command Console，保留轻量、直接的主控入口。
- 主控终端内置 Trace 基础观测面板，可查看执行步骤、层级、状态和耗时。
- AgentDock 将插件 UI 从临时侧栏推进为可管理的任务面板。
- 恢复并统一 `focus-visible`，避免桌面工具丢失键盘可用性。

## 快速开始

### 1. 安装后端依赖

建议使用虚拟环境：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

后端配置保存在 `vault/system_config.json`。请在本地配置模型、API Key、base URL 和 embedding 参数，不要提交真实密钥、token 或个人隐私数据。

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

## 项目结构

```text
.
├── main.py                 # 核心引擎：配置、LLM、RAG、记忆、JIT、画像导入、工具执行入口
├── server.py               # FastAPI 网关：动态端口、WebSocket、Trace API、插件路由和权限交互
├── agent_runner.py         # 异步智能体任务入口，在线程池中执行重型推理
├── core_bus.py             # 事件总线，隔离主会话、临时会话和插件 UI 消息
├── trace_system.py         # Trace/span 记录、事件推送、看门狗和快照查询
├── memory_system.py        # 画像、记忆、实体关系、待审和 L2 快照内核
├── memory_rules.py         # 瞬时交互识别与 JIT 意图门控规则
├── plugin_security.py      # 插件安全、权限确认、脱敏和不可信输出包裹
├── tool_registry.py        # 内置工具、外部工具和插件工具发现
├── tool_executor.py        # 工具执行器：搜索、知识检索、UI 指令、HTTP/subprocess 插件
├── rag_assembler.py        # 组装画像、认知快照和向量检索上下文
├── chroma_engine.py        # ChromaDB 向量库封装
├── db.py                   # SQLModel 数据库入口
├── chat-ui/                # Vue 3 + Vite + Tauri 前端
├── tests/                  # Python 单元测试
├── vault/                  # 运行时数据根目录：配置、数据库、Trace、知识库、插件
├── vault_seed/             # 首次启动或空 vault 初始化数据
├── requirements.txt        # 后端 Python 依赖
└── vault_engine.spec       # PyInstaller sidecar 打包配置
```

前端主界面相关文件：

- `chat-ui/src/App.vue`：应用 shell、分组导航、Command Console、权限弹窗、全局 Toast。
- `chat-ui/src/views/TerminalView.vue`：主控终端、临时会话和 Trace 基础观测面板。
- `chat-ui/src/components/AgentDock.vue`：插件/Agent 任务面板宿主。
- `chat-ui/src/assets/cyber-theme.css`：全局设计 token 和 Markdown 基础样式。

## 开发与验证

后端测试：

```powershell
python -m unittest discover tests
```

前端构建：

```powershell
cd chat-ui
npm run build
```

前端预览：

```powershell
cd chat-ui
npm run preview
```

当前 `chat-ui/package.json` 未声明 lint 脚本；如需 lint，请先根据项目实际脚本补充或确认。

## 文档导航

- [../README.md](../README.md)：项目门面和读者导航。
- [PRODUCT.md](PRODUCT.md)：产品定位、当前能力、产品化改版边界和 Roadmap。
- [PRODUCT_CASE.md](PRODUCT_CASE.md)：面向 AI 产品经理面试的作品集案例。
- [EVAL_REPORT.md](EVAL_REPORT.md)：AI 产品质量评估占位文档。
- [ROADMAP.md](ROADMAP.md)：产品演进路线占位文档。
- [ARCHITECTURE.md](ARCHITECTURE.md)：系统架构占位文档。
- [../vault/plugins/README.md](../vault/plugins/README.md)：VPM 插件协议、manifest 示例和安全规则。

## Roadmap

Now:

- 稳定主控体验 v1 的产品化骨架。
- 同步 README 与 PRODUCT 的公开说明口径。
- 保持当前改版边界，不混入业务协议变更。

Next:

- 统一危险确认和权限相关交互。
- 扩大 `PageFrame`、`SegmentedControl`、`VaultCard` 等基础组件覆盖范围。
- 提升设置、画像导入、插件中心和记忆相关业务页一致性。
- 增强 Trace 的阶段摘要、错误解释和恢复建议。

Later:

- 更完整的 Trace 归档和任务复盘。
- 插件中心可信体系和插件市场方向探索。
- 更成熟的记忆审核体验。
- 作品集展示页或案例材料归档。

## 协作注意事项

- 修改前先查看 `git status`，不要回滚或覆盖他人已有改动。
- 不要绕过 `VAULT_ROOT` 直接读写运行时数据路径。
- 修改临时会话逻辑时，必须保持“不读主记忆、不写持久状态、结束后丢弃迟到结果”的隔离语义。
- 修改画像导入时，必须保持“预览后提交”的两阶段流程。
- 修改第三方插件权限、UI token、内部 token、脱敏规则或不可信输出包裹时，需要同步更新插件文档并补充测试。
- 修改插件安全、插件卸载、RAG 删除、笔记删除、资产导出清理逻辑时，应逐路径审查，避免误删共享数据或放宽第三方插件边界。
- 禁止批量删除文件或目录。不要使用 `del /s`、`rd /s`、`rmdir /s`、`Remove-Item -Recurse`、`rm -rf`。如需删除多个文件，应先停止并让用户手动确认处理。
