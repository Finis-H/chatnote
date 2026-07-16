# Vault OS 功能状态基线

> 时间边界：清理前标签 vault-os-pre-archive-20260716 对应的源码版本。标签之后的提交只记录清理过程和归档状态，未改变源码；本文件以该标签为代码/功能基线。
>
> 证据口径：本阶段只读审查代码、配置、测试、既有文档、截图与设计资产；未重新运行 Build、测试、服务、安装包或桌面壳。下表的“验证”仅引用 docs/archive/01-final-snapshot.md 已记录的结果，不能外推为完整产品验收。

## 状态定义

- 已实现并验证：有当前源码，且有可复核的构建、启动、测试或其他运行记录；验证范围必须按证据限定。
- 已实现未验证：有当前源码或静态资产，但本轮没有对应的运行/测试证据。
- 部分实现：只覆盖有限路径，或已有明确的失败、缺口、未验证边界。
- 仅设计：只有产品/设计资产或计划，未找到对应实现证据。
- 已放弃：存在明确不再进入当前产品或重构 MVP 的决定。

## 功能矩阵

| 能力域 | 用户价值 | 当前状态 | 证据 | 已知限制 | 重构处置 |
| --- | --- | --- | --- | --- | --- |
| 本地 RAG 知识检索 | 以本地知识为依据回答，并显示来源。 | 部分实现 | main.py 的 VaultOS_Terminal.receive_knowledge_payload；tool_executor.py 的 action_search_local_knowledge；server.py 的 /api/rag/ingest 与插件 RAG 路由；docs/EVAL_REPORT.md 的 RAG-01 至 RAG-10。 | Eval 已记录冲突资料处理、RAG Prompt Injection 和输出级 PII 最小披露未通过；历史人工证据未完整留存。 | 重写：先建立不可信知识包装、冲突呈现与输出级隐私策略。 |
| 长期记忆与画像审核 | 将可长期保留的信息经缓冲、路由、待审/合并流程写入本地记忆；支持画像导入预览后提交。 | 部分实现 | main.py 的后台记忆流程、get_response、prepare_profile_import/commit_profile_import；memory_system.py 的 MemoryRepository、MemoryGatekeeper；chat-ui/src/views/MemoryStaging.vue；docs/assets/screenshots/03-memory-review-permission.png；tests/test_memory_buffer_pool.py、tests/test_memory_cognitive_snapshots.py、tests/test_profile_import_flow.py。 | Eval 记录敏感信息进入多处生命周期节点、负面泛化被长期化、失败状态 UI 不足；最近完整单进程测试未通过，画像导入独立测试在隔离环境中遇到 PermissionError。 | 重写：以显式数据分级、审核规则和可证明的失败状态取代当前隐式路径。 |
| Agent、JIT 与工具调用 | 对复杂请求形成步骤、调用已注册工具并把结果约束回最终答复。 | 部分实现 | main.py 的 classify_interaction_intent、JIT_PARSE、DAG_STEP、preflight_authorize_steps 与 ThreadPoolExecutor 路径；tool_registry.py、tool_executor.py；agent_runner.py；tests/test_jit_intent_gate.py、tests/test_execution_health_plan.py、tests/test_music_jit_fallback.py。 | Eval 记录工具连接失败未正确标记、动态意图变更无取消能力、敏感参数链路需复测；完整单进程测试存在跨模块 stub 污染。 | 拆分：把编排、工具契约、取消/超时和状态聚合拆为可独立测试的服务。 |
| Trace 可观测性 | 将任务、记忆、JIT、DAG 与工具步骤呈现为可追溯状态。 | 已实现未验证 | trace_system.py 的 TraceEmitter、SQLite trace_runs/trace_events 读取和树构造；server.py 的 /api/traces 路由与 WebSocket 事件消费；chat-ui/src/views/TerminalView.vue；docs/assets/screenshots/02-agent-running-trace.png。 | 当前基线只有代码和既有截图；本阶段未重新完成一条端到端 Trace。Eval 还记录工具失败状态的准确性缺口。 | 保留并重构：稳定事件契约、失败/取消语义和可回放测试。 |
| 插件管理与动态加载 | 枚举本地 VPM 插件、加载工具/UI，并支持高风险卸载确认。 | 部分实现 | server.py 的 PLUGINS_DIR 枚举、mount_vpm_plugins、uninstall_plugin；tool_registry.py 的 plugins 扫描；chat-ui/src/views/VpmCenterView.vue 与 utils/vpmLoader.js；docs/assets/screenshots/04-plugin-permission-danger-dialog.png；vault/plugins/README.md。 | 插件从 VAULT_ROOT/plugins 运行时加载，不能仅按静态 import 判断依赖；卸载涉及插件数据与 RAG 删除，未经隔离验证；动态依赖边界仍待确认。 | 拆分：将插件发现、生命周期、数据清理和 UI 加载的信任边界分开。 |
| 权限、安全与不可信输出 | 对第三方插件敏感权限进行声明校验、脱敏预览、会话级确认和输出隔离。 | 部分实现 | plugin_security.py 的敏感权限识别、预检、脱敏、wrap_untrusted_result；server.py 的 plugin_permission_response；chat-ui/src/App.vue 的权限确认界面；tests/test_plugin_security.py。 | docs/EVAL_REPORT.md 记录敏感参数脱敏与服务端确认令牌仍有 P0 风险；第一方 allowlist、动态参数和真实第三方插件仍需端到端复核。 | 重写：在重构前先建立可审计的权限决策与密钥/PII 全链路测试。 |
| 桌面 UI 与 Web 前端 | 提供主控终端、临时会话、知识、记忆、设置、插件和画像导入入口。 | 已实现并验证 | chat-ui/src/App.vue 异步加载七个视图；useNeuroLink.js 建立 WebSocket 连接；docs/assets/screenshots/01-home-command-console.png 至 05-eval-report-preview.png；docs/archive/01-final-snapshot.md 记录 Vite 前端 Build 通过（253 modules transformed）。 | 该验证仅覆盖前端生产 Build；没有验证桌面壳、真实用户流程或所有页面与后端的端到端联通。实际截图也不是本阶段重新运行所得。 | 保留：在新架构确定状态模型后重做信息架构与端到端验收。 |
| Windows 交付与 Tauri sidecar | 将 Vue 前端和 Python 后端组合为 Windows 桌面候选。 | 部分实现 | chat-ui/src-tauri/tauri.conf.json 的 externalBin/resources；chat-ui/src-tauri/src/main.rs 的 sidecar 启动、token/port 获取和退出清理；vault_engine.spec；scripts/build-windows-release.ps1；docs/WINDOWS_RELEASE.md。 | docs/archive/01-final-snapshot.md 明确：Tauri bundle、安装/卸载、签名和 Windows 交付均未验证。当前 sidecar 与 bin/_internal/ 是动态打包输入，必须保留。 | 延后：先在隔离 Windows 环境建立重建、签名、安装、升级和卸载验证矩阵。 |
| Eval 与自动化测试 | 为记忆、RAG、工具、插件和临时会话提供回归与质量边界。 | 部分实现 | tests/ 下 11 个 test_*.py；docs/EVAL_REPORT.md；docs/archive/01-final-snapshot.md 的隔离执行记录。 | 最近完整单进程发现为 38 通过、11 错误；Web 搜索独立重跑为 5 通过、2 失败；docs/EVAL_REPORT.md 的 33/2/10 与 docs/ARCHITECTURE.md 的 33/1/11 发生待人工确认的事实冲突。 | 重写：隔离模块状态、固定夹具、保存 Trace/截图证据，并在确认计数来源后统一汇总。 |
| Figma 中的治理控制台与研究桥接示例 | 展示 Agent 执行、记忆审核、插件权限的目标信息架构。 | 仅设计 | design-automation/figma/exports/KF01-control-terminal.png 至 KF04-plugin-center.png；design-automation/figma/export-manifest.json；design-automation/qa/review-report.md。 | 四张导出明确为 synthetic、redacted、fixture-only，不连接生产运行时；研究桥接 fixture、完整权限治理面板和其状态不能作为已交付功能。仓库未发现可定位的 Figma 原文件或 URL。 | 延后：把静态稿作为重构输入，先由真实权限/Trace 契约决定页面。 |

## 已知验证基线

| 检查 | 已记录结果 | 本文件的使用方式 |
| --- | --- | --- |
| 前端 Build | 2026-07-16 的隔离执行记录为通过，Vite 6.4.2 转换 253 个 modules；存在 bundle 体积警告。 | 仅支撑“前端 Build 已通过”，不支撑桌面交付或端到端可用。 |
| 后端最小启动 | 2026-07-16 在临时 VAULT_ROOT 启动 server.py 8 秒后仍存活，并受控停止。 | 仅支撑最小启动；未请求 API、未验证 WebSocket、模型调用或 UI。 |
| 后端完整单进程测试 | 2026-07-16 隔离执行为 38 通过、11 错误；多个模块受 sys.modules stub 污染。 | 作为未通过的重构输入，不能宣称完整回归通过。 |
| 独立失败 | 画像导入测试在隔离环境中因 WinError 5 未执行；Web 搜索测试为 5 通过、2 失败，均为防编造错误文案断言。 | 保留可复现条件和失败，不在本阶段修复。 |
| Windows 安装包/Tauri | 未运行 bundle、安装、卸载或签名验证。 | 一律标记为未验证，不作为 Release 或公开交付。 |

## 统计与结论

- 已实现能力：2 项（其中 1 项已实现并验证、1 项已实现未验证）。
- 部分实现能力：7 项。
- 仅设计能力：1 项；已放弃：0 项。
- “已实现并验证”不等于产品整体可交付：本基线唯一的当前构建级验证是前端 Build 与最小后端启动；完整后端单进程测试未通过，Windows 交付未验证。

## 待人工确认的事实

1. Eval 汇总数字存在冲突：docs/EVAL_REPORT.md 为 33 通过、2 部分通过、10 未通过；docs/ARCHITECTURE.md 为 33 通过、1 部分通过、11 未通过。两份原文均不改写。
2. 动态插件、vault_seed、当前 sidecar、bin/_internal/、vault/ 与 dist/vault/ 的实际运行依赖、私有数据和保留期限仍待确认。
3. GitHub Release/Actions、域名、模型 API、账单、存储和任何外部自动化是否存在，尚未在仓库内得到证实，留待 06-decommission 逐项确认。
