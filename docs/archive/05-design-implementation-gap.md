# Vault OS 设计与实现差距基线

> 对比对象：已跟踪实际 UI 截图、当前前端/后端代码、四张 Figma 静态导出和版本化产品资料。图像在本阶段仅作为既有资产阅读，不是重新运行产品得到的证据。
>
> Figma 证据边界：design-automation/figma/export-manifest.json 明确将四张导出标为 static fixture-only，输入为 synthetic and redacted，未连接生产运行时；design-automation/qa/review-report.md 的 12 项通过只证明静态作品集资产 QA。不得据此宣称产品运行态或权限流程已验收。

## 1. 资产与可比性

| 资产组 | 已发现内容 | 可用于说明 | 不可用于说明 |
| --- | --- | --- | --- |
| 实际 UI 截图 | docs/assets/screenshots/01-home-command-console.png 至 05-eval-report-preview.png。 | 已存在的主控、Trace、记忆审核、插件卸载确认和 Eval 页面样式/信息结构。 | 2026-07-17 的实时运行状态、端到端成功率或桌面交付。 |
| Figma 静态导出 | KF01-control-terminal、KF02-agent-running、KF03-memory-permission、KF04-plugin-center，均为 1440×900。 | 目标信息架构、文案、状态表达和重构设计输入。 | 生产截图、实际 WebSocket 事件、真实插件执行、真实权限决定或真实用户数据。 |
| 当前代码 | App.vue、TerminalView.vue、MemoryStaging.vue、VpmCenterView.vue、useNeuroLink.js、server.py、plugin_security.py 等。 | 当前可定位的页面、WebSocket 类型、权限/记忆/Trace 数据链路。 | 未运行的 UI 路径或未测试的服务端行为。 |
| 产品资料 | docs/PRODUCT.md、docs/PRODUCT_CASE.md、docs/ARCHITECTURE.md、docs/EVAL_REPORT.md、docs/UI_TOKENS.md。 | 产品意图、质量边界和已有风险记录。 | 覆盖更高优先级代码/运行记录的最终事实。 |

仓库范围内检索未发现可定位的 Figma 原文件或 URL；这一事项为“未发现/待确认”，不是原文件不存在的证明。

## 2. 场景对照

| 场景 | 设计意图 | 实际实现/资产 | 一致性 | 差异影响 | 结论 |
| --- | --- | --- | --- | --- | --- |
| KF01 主控终端 | 以本地优先 AI 工作台呈现主会话、Trace 摘要、连接状态、记忆边界和风险状态。 | Figma KF01 是带固定“静态导出覆盖层”的目标画面；实际截图 01 为 VOS 样式主控终端，实际截图 02 在终端顶部展开了 Trace 步骤；App.vue 和 TerminalView.vue 存在主控与 Trace UI。 | 部分一致 | 当前实现把 Trace 作为终端视图的一部分；Figma 额外的工作台状态卡、风险文案和 Agent 入口不能由实际截图或运行记录证明。 | 保留当前终端/Trace 链路；将 Figma 信息层作为重构输入，不将其视为已交付页面。 |
| KF02 Agent 执行 | 以可读任务时间线呈现运行、降级、失败、等待权限和恢复语义。 | 实际截图 02 展示 MEMORY_FLOW、L2_QUERY、JIT_PARSE、DAG_STEP、TOOL_EXEC 等 Trace 行；trace_system.py 和 TerminalView.vue 有对应实现。Figma KF02 中 research_bridge_fixture、权限卡和恢复说明均带模拟/静态标识。 | 部分一致 | 实际 Trace 是当前可见路径，但没有本阶段端到端复验；设计稿中的细粒度治理面板和“可恢复”表达没有真实运行态证据。 | 以真实 Trace 事件契约为先，再设计 Agent 时间线；不得把 fixture 状态作为产品状态。 |
| KF03 记忆审核 | 呈现低置信度候选、待审/采纳、来源、倒计时和写入后的可追溯状态。 | 实际截图 03 及 MemoryStaging.vue 都展示待审/历史、倒计时、采纳/驳回和三天自动采纳；main.py 与 memory_system.py 有缓冲、路由和待审实现。 | 部分一致 | Figma 强调“待确认的长期事实”与来源；实际实现虽有审核 UI，但 Eval 记录敏感 PII、偏见过滤和失败可见性缺口，不能把审核界面等同于安全记忆保证。 | 保留“预览/确认/待审”方向；重构须补齐数据分级、来源可解释与失败状态。 |
| KF04 插件中心与设置 | 显示插件身份、敏感权限、脱敏参数预览和拒绝/仅本次/本会话决策。 | VpmCenterView.vue 实现插件卡、动态管理组件和不可撤销卸载确认；App.vue 与 plugin_security.py 实现权限确认、脱敏预览及三个决策选项；实际截图 04 是插件卸载确认而非完整权限面板。Figma KF04 自述为规划中/只读展示，并使用 research_bridge_fixture。 | 部分一致 | 后端/前端确有权限构件，但 Figma 完整治理台、fixture 插件与其模拟状态并非已证明的产品页面；历史 Eval 仍列服务端确认和敏感参数为 P0 风险。 | 以现有确认事件为实现事实；Figma 仅作为权限工作流的视觉/内容重构输入。 |

## 3. 信息架构与文案差异

| 维度 | 实际 UI/代码 | 静态设计与产品资料 | 基线判断 |
| --- | --- | --- | --- |
| Trace 布局 | 实际截图和 TerminalView.vue 将 Trace 置于主控终端内并可展开；服务器另提供 snapshot/latest API。 | KF01/KF02 将 Trace 摘要和时间线提升为工作台核心视觉层。 | 方向相近，布局和信息密度不一致；重构前应先定义 Trace 状态/失败/取消契约。 |
| 插件权限 | 现有 App.vue 弹层显示插件、权限、风险、脱敏预览和三种决策；VpmCenter 侧重列表/管理/卸载。 | KF04 同屏展示声明权限、治理检查点、参数预览与决策模型。 | 实现已覆盖部分确认机制，完整治理台仅设计。 |
| 记忆审核 | MemoryStaging 提供待审、合并、拒绝、自动采纳和倒计时；实际截图呈现同类信息。 | KF03 把低置信度、人工审查、来源、写入影响表达得更明确。 | 交互骨架已实现，安全/隐私/可解释的语义仍有实现缺口。 |
| 中英文文案 | 实际 UI 以中文为主，含 VPM、Trace、WebSocket、Enter、Agent 等中英混合术语；代码亦保留技术命名。 | Figma 同样混用中文产品文案和英文状态/注释，且有“NOT PRODUCT UI”“STATIC EXPORT OVERLAY”等资产注解。 | 静态稿的注释不是用户界面文案。重构应建立术语表，并区分开发注释和用户可见文本。 |
| 已实现与仅设计 | App.vue 已加载七个视图，后端也有实际 WebSocket/权限/Trace/记忆代码。 | 四张 Figma 图是合成、脱敏、fixture-only 导出，不连接运行时。 | 图中展示的精细风险态、研究桥接 fixture 与完整治理台不得计为已实现功能。 |

## 4. 对产品资料的回读

1. 产品资料将 Vault OS 定位为本地优先、长期记忆、RAG、工具/插件、Trace 和权限治理工作台；当前代码可定位到这些模块，但 docs/EVAL_REPORT.md 已保留多项安全与可靠性缺口。
2. 实际截图支持“存在 UI 原型与若干状态页面”，不支持“当前版本完整可用”或“Windows 可交付”。
3. 四张 Figma 静态导出适合作为作品集交接和重构讨论材料；它们不替代真实运行截图、Trace、测试夹具或权限审计证据。
4. 设计资产中的 synthetic、redacted、fixture-only 声明必须在任何复用、公开或重构说明中保留。
