# Vault OS 前端修改守则

## 适用范围

本文件适用于 `chat-ui/` 下的前端工作。

根目录 `AGENTS.md` 是全仓规则来源，包含安全约束、删除规则、超时要求和完成定义。本文件只补充 Vault OS 前端局部修改规则。

## 产品边界

Vault OS 前端产品化改版主要是表达层、轻量组件复用和文案收敛。

默认不要修改：

- WebSocket 行为。
- 后端 API。
- Trace 数据结构。
- 记忆流程。
- 插件权限协议。

除非任务明确要求并已审查影响范围，否则不要把前端表达优化扩展成后端协议变更。

## 当前前端状态

### 已完成

- 基础组件文件存在。
- `cyber-theme.css` tokens 存在。
- Command Console 已进入主控体验。
- Trace 基础观测面板已进入主控体验。
- AgentDock 已进入主控体验。

### 阶段性完成

- 组件覆盖已试点，但未全站统一。
- 高风险确认已试点，但未全站统一。
- 业务页一致性仍在推进。

### 下一阶段

- 统一权限/危险确认。
- 扩展 `PageFrame` / `SegmentedControl` / `VaultCard` / `DangerDialog` 覆盖。
- 提升 Trace 可读性。
- 收敛设置、画像导入、插件中心等业务页文案。

## UI 风格规则

- 使用暗色、克制、专业、轻赛博风格。
- 少用强霓虹。
- 高风险流程不要戏剧化。
- 保留可见 `focus-visible`。
- 不要重新引入大量硬编码颜色。
- 优先使用 `src/assets/cyber-theme.css` 中的 tokens。

## 组件复用规则

优先复用：

- `DangerDialog`
- `PageFrame`
- `SegmentedControl`
- `VaultCard`
- `AgentDock`
- `CyberMarkdown`

不要为同类页面重复造：

- frame 布局
- filter 控件
- card
- danger confirmation

## 状态表达规则

AI/tool/action 至少要表达以下状态或项目内等价状态：

- `idle`
- `running`
- `success`
- `failed`
- `needs_permission`

Trace、AgentDock、配置保存、导入、删除、权限确认都要表达：

- 正在做什么
- 结果是什么
- 是否需要用户介入

## 高风险文案规则

删除、卸载、配置重载、记忆待审、画像导入、插件权限必须说明：

- 操作对象
- 影响范围
- 是否可撤销
- 风险

文案要冷静、明确、可审计。

不要在高风险操作中使用夸张赛博文案或 emoji。

## 工作流规则

- 修改前先看 `git status`。
- 不得批量删除文件。
- 不回滚用户改动。
- 长时间命令必须有超时或非交互模式。
- 不新增依赖，除非明确说明理由并获得确认。
- 前端文档修改不要顺手改业务代码。

## 验证

前端改动后在 `chat-ui/` 下运行：

```powershell
npm run build
```

如果本次只改 Markdown，可以说明 build 是否必要。

当前 `package.json` 未声明 lint 脚本，因此除非项目新增或确认 lint 脚本，否则不能运行 lint。

## 完成定义

完成前端工作时必须输出：

- 修改文件
- 验证命令
- 未运行的检查及原因
- 风险点
- 是否仍需人工确认
