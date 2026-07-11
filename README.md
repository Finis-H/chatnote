# Vault OS

> 一个本地优先的长期记忆 AI Agent 工作台，面向 AI 重度用户、知识工作者和开发者。

Vault OS 希望把私人知识、长期记忆、Tool Use、可追踪的 Agent 执行过程和插件工作流，连接成一个用户可掌控的桌面 AI 助手。

## 从这里开始

| 目标 | 推荐入口 |
|---|---|
| 项目案例 | [Product Case](./docs/PRODUCT_CASE.md) |
| 项目定义 | [Product Spec](./docs/PRODUCT.md) |
| 开发指南 | [Developer Guide](./docs/DEVELOPER_GUIDE.md) |
| 项目测评 | [Eval Report](./docs/EVAL_REPORT.md) |
| 开发路线 | [Roadmap](./docs/ROADMAP.md) |
| 架构设计 | [Architecture](./docs/ARCHITECTURE.md) |

## 前端界面示例

截图资产说明见：[docs/assets/README.md](./docs/assets/README.md)

| 截图 | 说明 | 状态 |
|---|---|---|
| [01-home-command-console.png](./docs/assets/screenshots/01-home-command-console.png) | 首页工作台与 Command Console | 完成 |
| [02-agent-running-trace.png](./docs/assets/screenshots/02-agent-running-trace.png) | Agent 运行中与 Trace 可观测过程 | 完成 |
| [03-memory-review-permission.png](./docs/assets/screenshots/03-memory-review-permission.png) | 记忆审查或权限确认流程 | 完成 |
| [04-plugin-permission-danger-dialog.png](./docs/assets/screenshots/04-plugin-permission-danger-dialog.png) | 插件权限与高风险确认弹窗 | 完成 |
| [05-eval-report-preview.png](./docs/assets/screenshots/05-eval-report-preview.png) | Eval Report 预览或测评说明 | 完成 |

## 为什么做 Vault OS

普通 AI 聊天工具在长期使用中存在：

- 上下文容易丢失
- 个人知识难接入
- 长期记忆不可控
- 工具调用过程不透明
- 插件权限边界不清晰

Vault OS 探索的是：AI 助手如何从“聊天框”变成一个可管理、可观察、可长期协作的本地工作台。

## 核心场景

1. 长期个人记忆和偏好管理
2. 本地知识问答和上下文增强
3. 可追踪执行过程的 Agent Tool Use
4. 临时会话隔离和插件权限控制

## 核心能力

| 能力 | 说明 |
|---|---|
| Long-term Memory | 管理用户偏好、事实、关系和项目上下文。 |
| RAG / Local Knowledge | 把本地私人知识作为 AI 回复的上下文。 |
| Tool Use | 让 Agent 通过受控接口调用本地或外部工具。 |
| Trace / Observability | 展示 Agent 做了什么、调用了哪些工具、结果如何。 |
| Plugin Permission | 管理插件权限、敏感操作和安全边界。 |
| Local-first Desktop | 尽量让个人数据和工作流留在用户自己的环境里。 |

## 项目案例

关于产品思考、问题定义、方案设计和指标设计，见：

[docs/PRODUCT_CASE.md](./docs/PRODUCT_CASE.md)

## 项目说明

关于产品定位、当前能力、产品边界和 Roadmap，见：

[docs/PRODUCT.md](./docs/PRODUCT.md)

## 测评

评估设计将覆盖：

- RAG 回答质量
- Memory 写入准确性
- Tool 选择和执行成功率
- 插件权限和 Prompt Injection 安全
- 临时会话隔离

详情见：

[docs/EVAL_REPORT.md](./docs/EVAL_REPORT.md)

## 开发指南

安装、本地开发、构建命令、项目结构和排障说明，见：

[docs/DEVELOPER_GUIDE.md](./docs/DEVELOPER_GUIDE.md)

## 路线图

后续产品演进计划见：

[docs/ROADMAP.md](./docs/ROADMAP.md)

## 架构

Vault OS 的架构围绕“本地优先”的 Agent 工作台循环构建：

用户输入 → 上下文 → 记忆 / RAG → 智能体运行时 → 工具调用 → 追踪（Trace） → 响应 → 评估

查看完整架构文档：

[docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md)