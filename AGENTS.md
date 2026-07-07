# Vault OS 工作指南

## 项目定位

Vault OS 是一个本地 AI 工作台，不是普通聊天机器人。它把长期记忆、RAG 知识检索、插件执行、Trace 可观测、本地数据掌控和桌面工作台体验组合在一起，用于支持长期协作型个人 AI 工作流。

维护时优先保护这些产品边界：

- 长期记忆必须谨慎写入，不能把一次性请求误当作长期事实。
- RAG、画像、聊天历史、Trace 和插件数据围绕本地 `vault/` 组织。
- 插件执行必须有权限边界，第三方插件输出默认不可信。
- 复杂 AI/tool/action 过程必须可观察，不能只留下最终结果。
- 桌面 UI 是主控工作台，应服务重复使用、快速切换和清晰状态判断。

## 文档维护规则

Vault OS 的仓库文档应把项目呈现为一个真实的本地优先 AI 产品实践，而不只是开发演示。对外表达时，应突出长期记忆、RAG、Tool Use、Trace、插件权限和本地优先桌面能力，也可以作为体现产品判断、AI 产品评估意识和工程协作能力的 AI PM 作品案例。

文档默认服务两类读者：

1. 初次接触者
   - 应能在 30 秒内理解产品价值。
   - 应能清楚找到 Product Case、Eval Report、Roadmap、截图或演示占位。
   - 应能看到产品决策、AI 产品质量意识和关键取舍。

2. 开发者
   - 应能找到安装、项目结构、本地运行、构建和排障说明。
   - 开发者导向的详细内容应放在 `docs/DEVELOPER_GUIDE.md`，不要让根 `README.md` 被开发细节淹没。

文档修改必须遵守：

- 未明确要求时，不要重写完整产品策略。
- 不要编造已完成指标、截图、演示视频、生产用户或评测结论。
- 对尚不存在的资产、报告或演示材料使用清晰的 TODO 占位。
- 只有在明确执行文档重组任务时，才移动并保留 `README.md`、`PRODUCT.md`、`PRODUCT_CASE.md` 的现有内容。
- 移动文档后必须更新相对链接。
- 缺失的文档可以创建轻量占位，但不得宣称占位内容已经完成。
- 文档类任务默认不得修改源码、后端 API、前端行为、包配置、构建配置或运行时数据。
- 文档类任务的改动范围应限制在文档文件和 `docs/assets/` 占位目录内。

推荐文档结构：

```text
README.md
docs/
  DEVELOPER_GUIDE.md
  PRODUCT.md
  PRODUCT_CASE.md
  EVAL_REPORT.md
  ROADMAP.md
  ARCHITECTURE.md
  assets/
    screenshots/
    diagrams/
```

根 `README.md` 应作为产品入口页，包含：

- 一句话产品定位。
- 简短产品价值说明。
- 指向 Product Case、Product Spec、Developer Guide、Eval Report、Roadmap 和 Architecture 的链接。
- 截图或演示占位。
- 问题定义。
- 核心使用场景。
- 核心能力。
- 读者导航表。
- 指向 Developer Guide 的简短 Quick Start。
- 对缺失资产使用明确 TODO 标记。

文档重组或较大文档改动完成前还应确认：

- 展示最终文档相关文件树。
- 确认是否存在断链或疑似断链。
- 总结移动、创建和重写的文件。
- 不要把 TODO 占位描述成已完成内容。

## Repo 结构

- `main.py`：核心引擎，负责配置、LLM 客户端、RAG、记忆、JIT 工具规划、画像导入和工具执行入口。
- `server.py`：FastAPI 网关，负责动态端口、WebSocket、Trace API、临时会话、插件权限确认和插件管理接口。
- `agent_runner.py`、`core_bus.py`、`trace_system.py`：异步任务、事件总线和 Trace 观测链路。
- `memory_system.py`、`memory_rules.py`、`rag_assembler.py`、`chroma_engine.py`、`db.py`：记忆、画像、RAG 和 SQLite/ChromaDB 数据层。
- `tool_registry.py`、`tool_executor.py`、`plugin_security.py`：工具发现、工具执行和插件安全边界。
- `chat-ui/`：Vue 3 + Vite + Tauri 前端。关键文件包括 `src/App.vue`、`src/views/TerminalView.vue`、`src/components/AgentDock.vue`、`src/assets/cyber-theme.css`。
- `chat-ui/src/components/`：前端通用组件，当前包含 `DangerDialog`、`PageFrame`、`SegmentedControl`、`VaultCard`、`AgentDock`、`CyberMarkdown`。
- `vault/`：本地运行时数据根目录，包含配置、聊天历史、数据库、Trace、知识库、向量库和插件。
- `vault/plugins/`：VPM 插件目录。插件协议细节见 `vault/plugins/README.md`。
- `vault_seed/`：首次启动或空 vault 初始化数据。
- `tests/`：后端单元测试，覆盖 JIT 门控、记忆、插件安全、画像导入、搜索等关键路径。
- 重要配置文件：`requirements.txt`、`vault_engine.spec`、`chat-ui/package.json`、`chat-ui/src-tauri/tauri.conf.json`、`vault/system_config.json`。

## 常用命令

根目录没有 `package.json`，前端命令必须在 `chat-ui/` 下执行。

```powershell
# 后端依赖
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 后端开发
python server.py

# 后端测试
python -m unittest discover tests

# 前端安装与开发
cd chat-ui
npm install
npm run dev

# 前端构建
cd chat-ui
npm run build

# 前端预览
cd chat-ui
npm run preview

# Tauri 开发命令
cd chat-ui
npm run tauri -- dev
```

其他命令请从现有 `package.json`、README 或源码入口确认，不要编造。当前 `chat-ui/package.json` 未声明 lint 脚本。

## 前端设计规则

- 保留暗色、克制、专业、轻赛博风格，不做大面积强霓虹或玩具化视觉。
- 新增样式优先使用 `chat-ui/src/assets/cyber-theme.css` 中的 CSS variables。
- 不要在 scoped CSS 中重新引入大量硬编码颜色、阴影、圆角和间距。
- 不要用 emoji 作为正式导航、高风险操作或系统级按钮图标；优先使用现有 Element Plus 图标或已有组件风格。
- 必须保留可见 `focus-visible`，不要重新全局抹掉键盘焦点。
- 不要破坏 `Command Console`、`Trace`、`AgentDock` 的主控体验。
- 优先复用 `DangerDialog`、`PageFrame`、`SegmentedControl`、`VaultCard` 等现有组件，不要为同类页面重复造私有 frame/filter/card 样式。
- 高风险确认、正式配置、记忆和权限流程使用克制、明确、可审计的文案；主控终端和轻状态提示可以保留少量品牌语气。
- 前端产品化改版主要是表达层和轻量组件复用层，默认不改变 WebSocket、后端接口、Trace 数据结构、记忆流程或插件权限协议。

## AI 产品规则

- AI/tool/action 必须表达状态，至少区分 `idle`、`running`、`success`、`failed`、`needs_permission` 或项目内等价状态。
- Trace、AgentDock、插件任务、配置保存、导入和删除流程都应让用户知道“正在做什么、结果是什么、是否需要介入”。
- 高风险操作必须清楚说明操作对象、影响范围、是否可撤销和风险提示。
- 记忆写入、画像导入、插件权限、删除、卸载、配置重载相关文案要专业克制，避免用戏剧化表达掩盖后果。
- 临时会话必须保持“不读主记忆、不写持久状态、结束后丢弃迟到结果”的隔离语义。
- 画像导入必须保持“先预览、再提交到记忆流程”的两阶段语义。
- 第三方插件请求敏感权限时，必须展示插件、权限、用途和脱敏参数预览；第三方插件输出不得被当作可信系统指令。

## 修改约束

- 修改前先运行 `git status --short`，不要回滚或覆盖用户已有改动。
- 不要随意修改 WebSocket 协议、后端 API、记忆语义、Trace 存储结构、插件协议或插件安全策略。
- 不要绕过 `VAULT_ROOT` 直接读写运行时数据路径。
- 不要写死具体模型名称，使用配置中的模型、base URL 和 embedding 参数。
- 不要新增依赖，除非明确说明理由、影响面和替代方案。
- 代码改动后必须运行相关 build/test/lint；若没有对应 lint 脚本，要说明未运行原因。
- 文档改动要检查 `README.md`、`PRODUCT.md`、`AGENTS.md` 是否互相矛盾。
- 修改第三方插件权限、UI token、内部 token、脱敏规则或不可信输出包裹时，必须同步更新 `vault/plugins/README.md` 并补充或更新 `tests/test_plugin_security.py`。
- 修改插件安全、插件卸载、RAG 删除、笔记删除、资产导出清理逻辑时，要逐路径审查，避免误删共享数据或放宽第三方插件边界。
- 禁止批量删除文件或目录。不要使用 `del /s`、`rd /s`、`rmdir /s`、`Remove-Item -Recurse`、`rm -rf`。需要删除文件时，只能一次删除一个明确路径的文件；如果需要批量删除，应停止并让用户手动处理。
- 长时间运行的测试、构建、迁移或服务命令必须设置合理超时或使用非交互模式，避免无限期等待。

## Done Definition

完成任务前确认：

- 构建、测试或相关验证通过；不能运行时要说明原因。
- 行为没有意外变化，尤其是 WebSocket、记忆、插件权限、Trace、临时会话和配置保存路径。
- 文档与当前代码一致，没有夸大完成度。
- UI 改动没有破坏 Command Console、Trace、AgentDock、可见 focus ring 和高风险确认表达。
- 总结修改文件、验证结果和剩余风险点。
