# Vault OS 已批准清理执行记录

> 本记录只覆盖用户已批准的 A-1 与 B-1 批次。未列出的候选项均未获得对应批次授权，也未被处理。

## A-1 批次

| 字段 | 记录 |
| --- | --- |
| 执行日期 | 2026-07-17 |
| 审批 ID | CLN-017、CLN-019 |
| 执行方式 | 用户手动删除；Codex 仅执行删除后的非破坏性复核与归档记录。 |
| 实际处理路径 | `__pycache__/`、`tests/__pycache__/`、`build/vault_engine/` |
| 删除前清单 | 两个项目源码范围内的 Python 缓存目录共 33 个 `.pyc` 文件；`build/vault_engine/` 含 14 个 PyInstaller 中间文件和 1 个 `localpycs/` 子目录。 |
| 结果 | 通过：三个批准路径均已不存在。 |

## B-1 批次

| 字段 | 记录 |
| --- | --- |
| 执行日期 | 2026-07-17 |
| 审批 ID | CLN-023、CLN-024、CLN-025、CLN-026 |
| 私有归档资产 | `VAULT-OS-PRIV-NSIS-001`；SHA-256 `ACEEE0B63DEB9BBBE847E4DB548BEBE4EF3E6094A2930B1BAA987FC535E56162`。私有归档已验证；未记录私有归档绝对路径。 |
| CLN-023 源文件 | `chat-ui/src-tauri/target/release/bundle/nsis/Vault OS_0.1.0_x64-setup.exe` 保留在仓库中；本批次只执行复制与哈希核验，未运行、安装、签名或公开。 |
| 实际删除路径 | `dist/Vault OS_0.1.0_x64-setup.exe`、`chat-ui/src-tauri/target/release/bundle/msi/Vault OS_0.1.0_x64_en-US.msi`、`dist/vault_engine.exe` |
| MSI 删除前元数据 | SHA-256 `72E90D1774709C5FAD19BBBE5142859F4735CD9ED4E7CBB1ED481D2838B3FA60`；83,910,656 bytes；修改时间 `2026-05-20 18:02:17 +08:00`。 |
| 旧 sidecar 删除前校验 | SHA-256 `6BB177B96079D1B4383F51600557628D9222052E5C246DB9CA9F77CD04F22024`；未保留副本。 |
| 结果 | 通过：私有归档哈希匹配；NSIS 源文件保留；三项精确删除路径均不存在。 |

## 验证结果

| 检查 | 结果 | 说明 |
| --- | --- | --- |
| 批准路径存在性 | 通过 | `__pycache__/`、`tests/__pycache__/`、`build/vault_engine/` 均不存在。 |
| 排除范围 | 通过 | `.venv/`、`vault/`、`dist/`、`build/chroma_behavior_20260524221523/`、`build/legacy_chroma_20260524222107/`、`chat-ui/src-tauri/target/`、`temp/`、`vault_seed/` 均仍存在。 |
| Build、测试、服务、安装包 | 未执行 | 本批次按用户要求只做非破坏性验证，不运行任何可能写入运行时数据的命令。 |
| Git 静态检查 | 通过 | 文档写入后，`git status --short` 仅列出本批次的三份归档文档；`git diff --check` 以退出码 0 完成、未报告差异空白错误。Git 报告既有 `PROJECT_CLOSURE_STATE.md` 的 LF/CRLF 转换提示，不是差异检查失败。 |
| B-1 私有归档 | 通过 | `VAULT-OS-PRIV-NSIS-001` 的目标 SHA-256 与指定值完全一致；仓库不记录私有归档绝对路径。 |
| B-1 删除路径 | 通过 | `dist/Vault OS_0.1.0_x64-setup.exe`、MSI 与 `dist/vault_engine.exe` 均已不存在；NSIS 源文件仍存在。 |
| B-1 排除范围 | 通过 | `chat-ui/src-tauri/bin/vault_engine-x86_64-pc-windows-msvc.exe`、`bin/_internal/`、`vault/`、`dist/vault/`、已列出的 `build/*vault*`、`temp/`、`.venv/`、Dockerfile、依赖清单和 Tauri 配置均仍存在。 |
| B-1 Build、测试、服务、安装包 | 未执行 | 本批次未运行、安装、签名或公开安装包，也未运行 Build、测试或服务。 |
| B-1 Git 静态检查 | 通过 | 文档写入后，`git diff --check` 以退出码 0 完成，Git 状态仅列出本批次的三份归档文档；未发现私有归档绝对路径。 |

## 范围与后续

- B-1 未处理当前 sidecar `chat-ui/src-tauri/bin/vault_engine-x86_64-pc-windows-msvc.exe`、`bin/_internal/`、`vault/`、`dist/vault/`、其它 `build/*vault*`、`temp/`、`.venv/`、Dockerfile、依赖、业务代码、测试、Git 忽略规则、Tauri 配置或外部服务。
- 除已完成的 CLN-017、CLN-019、CLN-024、CLN-025、CLN-026，以及 CLN-023 的已验证私有归档副本外，其余候选仍未获批准；后续批次必须由用户另行指定候选 ID、排除范围与验证方式。
- 如需回退本批次，清理前内容可从清理前标签 `vault-os-pre-archive-20260716` 或对应构建流程重新取得；本次未创建、移动或修改任何 Git 标签。

## C-1 容量清理批次（已停止）

| 字段 | 记录 |
| --- | --- |
| 执行日期 | 2026-07-17 |
| 审批范围 | CLN-018、CLN-021、CLN-022；`.venv/`、两个指定 Windows staging 目录和 `chat-ui/src-tauri/target/`。 |
| 删除前重建快照 | 已创建 `docs/archive/REBUILD_ENVIRONMENT.md`，记录 Python/pip/Node/npm/Rust/cargo 版本、三个锁/清单 SHA-256、脱敏 `pip freeze`、sidecar 状态和重建前提。 |
| 私有 NSIS 预检 | 仓库内 NSIS 源候选存在，SHA-256 为 `ACEEE0B63DEB9BBBE847E4DB548BEBE4EF3E6094A2930B1BAA987FC535E56162`；与 `VAULT-OS-PRIV-NSIS-001` 的既有记录一致。私有归档位置未写入仓库，不能仅凭标识独立重新访问确认，因此不删除 `target/`。 |
| sidecar 预检 | `chat-ui/src-tauri/bin/vault_engine-x86_64-pc-windows-msvc.exe` 与 `chat-ui/src-tauri/bin/_internal/` 均存在，未读取、运行或删除。 |
| 两个 `temp/` 目录预检 | 仅文件名级检查即发现 `python-smoke-vault`/`smoke-vault`、`system_config.json`、`chat_history.json`、`vault_trace.db`/WAL/SHM 和多份日志。未读取内容；按任务停止条件，不处理这两个目录。 |
| 实际删除路径 | 无。仓库规则禁止 Codex 对目录执行递归/批量删除；同时两个 `temp/` 目录不满足本批次的运行时数据安全门槛，`target/` 不满足私有归档复核门槛。 |
| 实际释放空间 | `0 bytes`。删除前四个路径的逻辑文件大小合计为 12,054,817,896 bytes；这只是容量估算，不是已释放空间。 |
| Build、测试、服务、安装包 | 未执行。 |
| 结果 | 已停止，未造成文件或运行时数据变更。 |

### C-1 排除范围复核

`vault/`、`dist/vault/`、`build/chroma_behavior_20260524221523/`、`build/legacy_chroma_20260524222107/`、全部 `build/smoke_vault_*`、`vault_seed/`、当前 sidecar、`bin/_internal/`、`chat-ui/node_modules/`、Dockerfile、依赖清单、业务代码、测试、`discard/`、Git 忽略规则和 README 均仍存在。未读取这些受保护范围的内容。

继续 C-1 前，需要用户决定两个 staging 目录中检测到的运行时数据的保留策略，提供可访问但不写入仓库的私有 NSIS 归档核验方式，并由用户手动处理任何仍获准删除的明确目录。之后仅进行存在性、实际释放空间与 Git 静态检查；不会补跑 Build、测试、服务、Docker、Tauri 或安装包。
