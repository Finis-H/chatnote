# Vault OS 外部资源、安全与运行环境处置清单

> 本文完成 `06-decommission` 的检查部分。所有结论只基于 2026-07-17 的仓库静态审查、Git 配置、既有归档记录和 GitHub 公开 API；未关闭、删除、暂停、撤销、轮换或修改任何外部资源。本文不记录密钥、Token、连接字符串、个人数据或私有归档绝对路径。

## 1. 审查边界与证据

- 已审查：受版本控制的源码、配置、忽略规则、`Dockerfile`、Windows 交付脚本、Tauri 配置、既有归档文档、Git 远端，以及 GitHub 的公开仓库元数据。
- 未读取：`vault/`、`dist/vault/`、数据库、日志、真实对话、Trace、实际 `system_config.json`、密钥文件、浏览器或桌面应用持久化 Token。
- 未运行：安装包、Docker、Tauri Build、服务、测试、部署或清理命令。
- GitHub 公开查询以本地 `origin` 的历史地址为线索；GitHub 查询结果解析为 `Finis-H/chatnote`。本地远端仍为 `Finis-H/chatnotev`，是否改名或重定向不在本阶段修改。

## 2. 外部资源与安全处置清单

| ID | 资源类别 | 资源名称/位置 | 用途 | 当前状态 | 推荐动作 | 风险 | 是否可能与其他项目共用 | 用户确认 | 执行结果 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| EXT-001 | GitHub 仓库 | `origin` 历史地址 `Finis-H/chatnotev`；公开查询解析为 `Finis-H/chatnote` | 源码托管与作品集入口 | 公开、未归档、默认分支为 `main`。 | 检查后保留 | 中 | GitHub 账号及其权限可能服务其它仓库；仓库本身待确认。 | OQ-CLOSE-002 已确认“暂时保持公开”；其余仓库/账号归属待线下确认。 | 只读确认；未改可见性、Archive、分支或权限。 |
| EXT-002 | GitHub Release | `Finis-H/chatnote` 的公开 Release | 对外二进制或版本交付 | 公开 API 返回 0 个 Release。 | 检查后保留 | 低 | 不适用；未来若创建 Release，可能关联共用发布凭据。 | 无需处理当前空清单；未来发布策略待用户决定。 | 只读确认；未创建、删除或修改 Release。 |
| EXT-003 | GitHub Actions / CI | 仓库公开 Actions 工作流与工作树 `.github/` | 自动验证、发布或定时自动化 | 公开 API 返回 0 个工作流；工作树不存在 `.github/`；仅发现本地 Windows 构建脚本。 | 无法确认，需用户检查 | 高 | 外部 runner、组织级自动化或其它项目的凭据可能共用。 | 待确认是否存在仓库外工作流、scheduled job、self-hosted runner、Preview 或组织级自动化。 | 未运行或停用任何自动化。 |
| EXT-004 | GitHub Issues / Discussions | `Finis-H/chatnote` | 对外协作与公开讨论 | Issues 已启用；公开 Issues 接口第一页返回 1 个开放 Issue、0 个已关闭 Issue；Discussions 未启用。 | 检查后保留 | 低 | 不适用。 | 是否关闭、整理或保留现有 Issue 待用户决定。 | 只读确认；未编辑、关闭或删除 Issue。 |
| EXT-005 | GitHub Webhook / 外部 Runner | 仓库设置、组织设置及第三方自动化账户 | 外部事件投递与自动执行 | 公开仓库元数据和工作树无法证明 Webhook、外部 runner 或第三方自动化不存在。 | 无法确认，需用户检查 | 高 | 是，常由共享 GitHub App、CI 账号或组织 runner 提供。 | 用户需在 GitHub 仓库/组织 Settings 和关联自动化平台核对。 | 未读取设置页敏感信息，未变更任何配置。 |
| EXT-006 | 对话模型 API | `VAULT_ROOT/system_config.json` 中的 `api_key`、`base_url`、模型字段；设置页与 OpenAI 兼容客户端 | 对话模型调用 | 源码默认面向 DashScope 兼容接口；设置页允许 OpenAI 兼容服务或本地 Ollama。实际配置值与账号均未读取。 | 无法确认，需用户检查 | 高 | 是，API Key 可能被其它项目、个人工具或团队共用。 | 用户需确认 Provider、Key 归属、是否仍有效、是否需要撤销或轮换。 | 仅记录字段位置与 Provider 线索；未读取或输出实际值。 |
| EXT-007 | Embedding API | 同一运行时配置中的 `embed_api_key`、`embed_base_url`、`embed_model`；`chroma_engine.py` 的 DashScope 适配器 | RAG 向量化 | 源码含 DashScope Embedding 调用线索；实际 Key、模型配置、额度和账单均未读取。 | 无法确认，需用户检查 | 高 | 是，Embedding Key 可能与对话模型或其它项目共用。 | 用户需确认 Key 归属、账单和轮换方案。 | 未发起模型调用或健康检查。 |
| EXT-008 | 本地/插件 Token | `vault/` 下运行 Token 文件、插件内部/界面 Token 逻辑 | 本地服务、WebSocket 与插件权限边界 | 代码会在运行时写入本地 Token；实际文件和内容按边界未读取。 | 无法确认，需用户检查 | 高 | 不明；通常为本地运行时凭据，但不能据此断言。 | 用户需在决定保留或销毁运行时数据时一并确认凭据处置。 | 未读取、复制、撤销或输出 Token。 |
| EXT-009 | Docker / 容器交付 | 根 `Dockerfile`；基础镜像经 `m.daocloud.io` 引用 Docker Hub Python 镜像 | 历史容器化启动入口 | 无 Compose、托管平台配置或 CI 容器工作流线索；`Dockerfile` 静态引用根目录不存在、仅在 `discard/` 中存在的旧模块，当前不可作为已验证部署入口。 | 无法确认，需用户检查 | 高 | 可能；镜像仓库、容器账号或云项目可能与其它项目共用。 | 用户需确认是否仍有 Docker 镜像、Container、Registry、云服务、监控或账单。 | 未运行 Docker、拉取镜像或变更 Registry。 |
| EXT-010 | 域名、DNS、TLS 与 Pages | 可识别的部署配置、GitHub Pages 公开端点 | 对外访问与费用 | 未发现用户自有域名、DNS、证书或托管配置；GitHub Pages 公开端点返回 404。代码中的模型 Provider 地址和本地开发地址不是用户自有域名证据。 | 无法确认，需用户检查 | 高 | 是，域名和证书常与其它项目共用。 | 用户需在线下检查域名注册商、DNS、SSL/CDN、静态托管和付款账户。 | 未修改 Pages、DNS、证书或托管。 |
| EXT-011 | 数据库、对象存储与监控 | SQLite/Chroma 的 `VAULT_ROOT` 路径；受审源码与常见部署配置 | 本地记忆、RAG、Trace 与可能的运维集成 | 源码指向本地 SQLite 和 Chroma；未发现受版本控制的对象存储、托管数据库或监控配置线索。未发现不等于外部账号不存在。 | 无法确认，需用户检查 | 高 | 可能；云数据库、对象存储、监控和账单可能共用。 | 用户需检查云控制台、对象存储、错误追踪、日志和账单。 | 未读取运行时数据或任何云账号。 |
| EXT-012 | 运行时数据 | `vault/`、`dist/vault/`、`build/*vault*` | 用户配置、记忆、聊天、Trace、数据库、插件与测试运行数据 | 可能含个人数据和敏感配置；本阶段未读取目录或内容。默认策略为私有保留。 | 检查后保留 | 高 | 不明；可能含来自其它项目或第三方插件的资料。 | 用户需决定备份副本、加密/访问控制、保留期限、复原方式和销毁条件。 | 未读取、复制、移动或删除。 |
| EXT-013 | Figma / 作品集分享 | Figma 原文件和原型分享权限 | 设计源资产与作品集展示 | 仓库中无可定位的原文件 URL 或公开只读链接；既有静态导出仅为 synthetic、redacted、fixture-only。 | 无法确认，需用户检查 | 中 | 是，Figma 团队、文件权限和付费席位可能共用。 | 用户需确认原文件所有权、分享权限、脱敏范围和席位费用。 | 未访问或变更 Figma 权限。 |
| EXT-014 | 账单、订阅与告警 | 模型 Provider、域名、云服务、GitHub/CI、Figma 及其它第三方账户 | 成本与自动续费控制 | 仓库和公开 API 无法提供账单、试用额度、订阅、信用卡或告警状态。 | 无法确认，需用户检查 | 高 | 是，账户和付款方式可能跨项目共用。 | 用户需逐账户检查计费、自动续费、预算告警和所有者；任何停用或取消须单独批准。 | 未访问账单或修改费用设置。 |

## 3. 私有 Windows 发布资产

| 资产/路径 | 当前归档状态 | SHA-256 / 处理结果 | 后续边界 |
| --- | --- | --- | --- |
| `VAULT-OS-PRIV-NSIS-001` | B-1 已完成私有归档校验；本文不记录私有归档绝对路径。 | `ACEEE0B63DEB9BBBE847E4DB548BEBE4EF3E6094A2930B1BAA987FC535E56162`。本次只读复核确认仓库内 NSIS 源候选仍存在，大小为 78,230,654 bytes，哈希一致。 | 私有保留；未运行、安装、签名或公开。 |
| `chat-ui/src-tauri/target/release/bundle/nsis/Vault OS_0.1.0_x64-setup.exe` | 当前仓库内的 NSIS 源候选保留。 | 与 `VAULT-OS-PRIV-NSIS-001` 哈希一致。 | 仅是未验证的最终源码/交付候选，不得描述为已发布或可支持安装包。 |
| `dist/Vault OS_0.1.0_x64-setup.exe`、历史 MSI、`dist/vault_engine.exe` | 已在 B-1 按已批准的精确路径处理。 | 重复 NSIS 副本、MSI 和旧单文件 sidecar 均已删除并记录在 `04-cleanup-execution-log.md`。 | 本阶段不重复处理、不恢复、不公开。 |
| 当前 sidecar | `chat-ui/src-tauri/bin/vault_engine-x86_64-pc-windows-msvc.exe` 与 `bin/_internal/` 仍保留。 | 既有 B-1 复核确认其属于当前 Tauri 候选的发行输入。 | 不读取、不运行、不删除；待未来隔离 Windows 安装/卸载验证和用户决策。 |

## 4. 待用户线下确认的最小清单

1. 各对话/Embedding Provider 的账号、Key 归属、是否与其它项目共用，以及保留、撤销或轮换决定。
2. 是否存在仓库外的 GitHub Webhook、GitHub App、Actions/外部 Runner、定时任务、Preview、Docker/Container、Registry 或云服务。
3. 域名、DNS、证书、静态托管、对象存储、托管数据库、监控、日志和费用账户的实际存在性与所有者。
4. `vault/`、`dist/vault/`、`build/*vault*` 的备份位置、加密/访问控制、保留期限、恢复流程和销毁触发条件。
5. Figma 原文件和作品集入口的分享权限、脱敏复核与席位/订阅费用。
6. GitHub 保持公开、现有 Issue 的处置和未来 Release 策略；当前没有授权改变这些状态。

## 5. 执行记录与结论

| 时间 | 检查 | 结果 | 不可逆影响 |
| --- | --- | --- | --- |
| 2026-07-17 15:29 +08:00 | Git、受版本控制的配置、忽略规则、Docker、Windows 交付脚本和 Tauri 配置 | 识别到 GitHub、模型 API 字段、Docker 历史入口、本地 SQLite/Chroma 与 Windows 私有候选线索。 | 无。 |
| 2026-07-17 15:29 +08:00 | GitHub 公开 API | `Finis-H/chatnote` 为公开、未归档仓库；0 Release、0 Actions 工作流、Issues 已启用、Discussions 未启用、Pages 端点为 404。 | 无。 |
| 2026-07-17 15:29 +08:00 | 私有 NSIS 资产引用与仓库内源候选哈希 | `VAULT-OS-PRIV-NSIS-001` 的既有归档哈希与保留源候选一致。 | 无。 |

本工作包的检查目标已完成。已能安全确认的外部结论只有公开 GitHub 状态、仓库内配置线索和私有安装包引用状态；所有账号、密钥、账单、域名、外部自动化、云资源和运行时数据策略仍须由用户线下确认。在收到逐项授权前，它们均按“私有保留、不得变更”处理。
