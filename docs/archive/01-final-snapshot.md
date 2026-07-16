# Vault OS 清理前最终快照

> 本快照在任何清理动作前建立，只记录可核验的仓库、命令和资产线索。不得将其中的候选安装包、静态 Figma 导出或历史 Eval 结论扩大表述为已发布、已安装验证或完整生产验证。

## 1. 快照标识

| 字段 | 内容 |
| --- | --- |
| 快照日期 | 2026-07-16 23:09:03 +08:00 |
| 执行人 | Codex / 用户 |
| 仓库远端 | `origin`：`https://github.com/Finis-H/chatnotev.git`（历史远端名称为 `chatnotev`，对外产品名称为 Vault OS） |
| 分支 | `main` |
| 快照基准 HEAD | `e9b3ae16100b43b2f532ea32fcbfc2f9c3434c72`（本快照文档写入前的 HEAD） |
| 已建立的前序提交 1 | `a4a41a7140023af1d18a794517a8fa6d35cf2bc7` — `docs: add Vault OS archive closure workflow` |
| 已建立的前序提交 2 | `e9b3ae16100b43b2f532ea32fcbfc2f9c3434c72` — `build(windows): preserve unverified release candidate` |
| 清理前标签 | `vault-os-pre-archive-20260716`；按已确认命名，指向承载本快照的第三次本地提交 |
| 现有标签（写入时） | 无 |
| 工作区状态 | 在前两次提交后检查为干净；本快照及状态更新将以单独第三次提交承载。 |

## 2. 最小运行与依赖说明

| 项目 | 实际内容 | 本阶段验证状态 |
| --- | --- | --- |
| 验证主机 | Windows PowerShell 环境。 | 已验证环境类型；未做干净 Windows 11 安装验证。 |
| Python | 本地 `.venv\\Scripts\\python.exe`：Python `3.12.10`，pip `26.1`。 | 已验证。 |
| Python 依赖 | `requirements.txt`，以 `pip install -r requirements.txt` 管理；Windows 候选构建脚本另要求本地 `.venv` 和 PyInstaller。 | 清单已读取；本阶段未重新安装依赖。 |
| 前端依赖 | `chat-ui/package.json` 与 `chat-ui/package-lock.json`，以 npm 管理。验证环境为 Node `v24.15.0`、npm `11.12.1`。 | 已验证清单与工具版本。 |
| 桌面依赖 | `chat-ui/src-tauri/Cargo.toml` 与 `Cargo.lock`；Tauri 打包还依赖 Rust 工具链。 | 清单存在；未运行 Tauri/Cargo 打包。 |
| 后端测试命令 | `python -m unittest discover tests`（开发文档声明的标准命令）。本阶段为避免写入项目运行时数据，使用临时工作目录和临时 `VAULT_ROOT` 执行等价发现。 | 有限制，详见第 3 节。 |
| 前端 Build 命令 | 在 `chat-ui/` 执行 `npm run build -- --outDir <临时目录>`。 | 通过，253 modules transformed；有 chunk 体积警告。 |
| 后端最小启动 | 在临时 `VAULT_ROOT` 下以 `server.py` 启动，8 秒后确认进程仍存活并主动停止。 | 通过；未发送 API 请求，未读取或写入项目 `vault/`。 |
| Windows 交付候选 | `scripts/build-windows-release.ps1` 可作为候选构建入口。 | 未运行；未执行安装包、Tauri bundle 或安装/卸载流程。 |

开发文档中的常规安装与启动入口为：`python -m venv .venv`、`pip install -r requirements.txt`、`python server.py`、在 `chat-ui/` 下执行 `npm install`、`npm run dev`。这些命令仅作为复现入口记录；本快照未重新安装依赖，也未运行会修改被忽略发行产物的 Windows 打包流程。

## 3. 验证记录

| 时间 | 命令或检查 | 结果 | 限制、影响与复现条件 |
| --- | --- | --- | --- |
| 2026-07-16 23:04 +08:00 | `git diff --check`、`git diff --cached --check` | 通过；两次检查均无输出。 | 仅静态检查，不代表运行行为。 |
| 2026-07-16 23:05 +08:00 | 隔离目录内执行 `python -m unittest discover -s <repo>\\tests -t <repo> -v` | 未进入测试：`ImportError: Start directory is not importable`。 | 该调用方式与非包化 `tests/` 目录不兼容；不涉及产品源码失败。后续使用不带 `-t` 的发现命令。 |
| 2026-07-16 23:06 +08:00 | 临时工作目录、临时 `VAULT_ROOT` 下执行 `python -m unittest discover -s <repo>\\tests -v` | 49 项中 38 通过、11 错误。 | 单进程按发现顺序运行时，多个测试模块写入且未恢复 `sys.modules` stub，后续模块因此导入替身：`test_music_jit_fallback`、`test_profile_import_flow`、`test_relationship_graph`、`test_single_value_name_conflict` 与 7 个 `test_web_search_tool` 用例受影响。未修复；按该命令可复现。 |
| 2026-07-16 23:07 +08:00 | 受影响模块在独立 Python 进程、临时工作目录和临时 `VAULT_ROOT` 下重跑 | `test_music_jit_fallback.py`：10 通过；`test_relationship_graph.py`：7 通过；`test_single_value_name_conflict.py`：8 通过。 | 这说明上述三组在独立进程条件下通过；不抵消整套单进程测试失败。 |
| 2026-07-16 23:07 +08:00 | `test_profile_import_flow.py` 独立重跑 | 导入 `main` 时失败：测试自身以 `tempfile.mkdtemp()` 创建的 `VAULT_ROOT` 在 `os.listdir()` 处报 `PermissionError: [WinError 5]`。 | 尚未执行该模块的用例；复现条件为本快照的隔离 PowerShell/临时目录环境。未更改源码。 |
| 2026-07-16 23:07 +08:00 | `test_web_search_tool.py` 独立重跑 | 7 项中 5 通过、2 失败。 | `test_empty_results_return_antihallucination_message` 与 `test_missing_ddgs_import_reports_dependency_failure` 期望的中文防编造文案与实际返回文案不一致；未修复。 |
| 2026-07-16 23:08 +08:00 | 受限沙箱内执行 `npm run build -- --outDir <临时目录>` | 失败：Vite 加载配置时 esbuild 子进程 `spawn EPERM`。 | 影响为受限沙箱无法启动 esbuild；同一命令在获准隔离执行环境中成功，故不归因于前端源码。 |
| 2026-07-16 23:08 +08:00 | 获准隔离执行环境中执行相同前端 Build 命令 | 通过：Vite `6.4.2`，253 modules transformed，3.56 秒完成。 | 输出写入临时目录，未写入仓库 `chat-ui/dist/`。Vite 报告 `CyberMarkdown`（1,037.38 kB）与 `index`（2,047.13 kB）压缩后超过 500 kB 的优化警告。 |
| 2026-07-16 23:08 +08:00 | 临时 `VAULT_ROOT` 下以隐藏后台进程运行 `.venv\\Scripts\\python.exe server.py` | 8 秒后进程存活；随后主动停止并确认已退出。 | 只验证最小启动与受控退出；未访问服务、未验证 WebSocket、模型调用、桌面壳或用户流程。 |

结论：前端生产构建与隔离最小后端启动已实际通过；完整后端单进程测试套件当前未通过，且两个独立模块仍有可复现失败。禁止据此快照宣称完整回归通过或产品功能已全部验证。

## 4. 最终资产索引

### 4.1 已跟踪 UI 截图

| 资产 | 用途 | 位置与 SHA-256 | 敏感信息检查状态 | 保留决定 |
| --- | --- | --- | --- | --- |
| Command Console 截图 | 作品集/实际 UI 场景索引 | `docs/assets/screenshots/01-home-command-console.png` — `75B34EB689B70CC10E1F71CDA57013EF706B8C26B5AF97D9E64FE6747243DC1B` | `docs/assets/README.md` 已列为已收录截图；本阶段未重新打开图像，公开前仍应逐图人工复核。 | 按 OQ-CLOSE-003/OQ-CLOSE-007 保留为经审查的公开候选。 |
| Agent/Trace 截图 | 作品集/可观测性场景索引 | `docs/assets/screenshots/02-agent-running-trace.png` — `ACCA719E679606B16D731BC943E9FF5FC00A6EDA91DD4B88B1AA92B4EB23D11E` | 同上。 | 同上。 |
| 记忆审核截图 | 作品集/记忆与权限场景索引 | `docs/assets/screenshots/03-memory-review-permission.png` — `ECAD3050A5FD431CB6C223F2ACD22AAD09B5ED4E8E5352FA20ECBCDDDB104B04` | 同上。 | 同上。 |
| 插件权限截图 | 作品集/权限场景索引 | `docs/assets/screenshots/04-plugin-permission-danger-dialog.png` — `B47B98C0B94AE3B5A6BDD52806B5E6129C4694D2AAB8F0866FFD396634FD41E4` | 同上。 | 同上。 |
| Eval 预览截图 | 作品集/质量意识场景索引 | `docs/assets/screenshots/05-eval-report-preview.png` — `62900E40C1701132C933CD1ABAE792398514255D83FC7EB1DB560F95921FB439` | 同上。 | 同上。 |

### 4.2 Figma 静态导出

`design-automation/figma/export-manifest.json` 标注这些 1440×900 图像为 static fixture-only exports，输入为 synthetic and redacted，未连接生产运行时。`design-automation/qa/review-report.md` 于 2026-07-15 记录 12 项通过、0 项部分通过、0 项失败；该 QA 仅证明作品集静态资产，不证明生产运行态。

| 资产 | 用途 | 位置与 SHA-256 | 敏感信息检查状态 | 保留决定 |
| --- | --- | --- | --- | --- |
| KF01 Control Terminal Home | Figma 关键帧 | `design-automation/figma/exports/KF01-control-terminal.png` — `1DD134CD9079A11B46CC029CE83183DC8D595BA1EB34930843BBA340FB722DF8` | 既有 manifest/QA 记录为合成、脱敏、fixture-only。 | 保留；不表述为生产截图。 |
| KF02 Agent Running | Figma 关键帧 | `design-automation/figma/exports/KF02-agent-running.png` — `1B633C5FA302B4B34739CA9676D0F94570CC096C0D02BAD84E8A3D586CF57B84` | 同上。 | 同上。 |
| KF03 Memory Review + Permission Gate | Figma 关键帧 | `design-automation/figma/exports/KF03-memory-permission.png` — `91F4304FB49162F6A7CEC216C1ACC7F1F082886EB0F24B824B8BFA7079E490EE` | 同上。 | 同上。 |
| KF04 Plugin Center + Settings | Figma 关键帧 | `design-automation/figma/exports/KF04-plugin-center.png` — `18066ED24D59285B492688B461DB58AE8B1024FF86FBCD6AE03CAF0E01397A72` | 同上。 | 同上。 |

仓库中未发现可定位的 Figma 原文件 URL 或可公开只读链接；按 OQ-CLOSE-003/OQ-CLOSE-007 保留原文件，是否分享链接仍待资产审查后由用户确认。

### 4.3 Eval、测试与发行候选

| 资产 | 用途 | 位置或标识 | 敏感信息检查状态 | 保留决定 |
| --- | --- | --- | --- | --- |
| Eval 基线 | 质量风险与证据缺口记录 | `docs/EVAL_REPORT.md`：既有记录为 33 通过、2 部分通过、10 未通过；原始 Trace/截图/夹具并未完整留存。 | 只引用已版本化报告；不读取、复制或公开原始 Trace、日志或数据库。 | 保留报告；敏感评测原件作为私有归档。 |
| 自动化测试 | 当前可复现验证材料 | `tests/` 中 11 个 `test_*.py` 文件及本快照第 3 节命令结果。 | 使用临时 `VAULT_ROOT`；不写项目运行时数据。 | 保留；整套单进程失败与独立失败均需后续基线记录。 |
| Windows 安装包候选 | 私有交付线索 | 被 Git 忽略的 `dist/Vault OS_0.1.0_x64-setup.exe`；78,230,654 bytes；修改时间 `2026-07-16 15:34:29 +08:00`；SHA-256 `ACEEE0B63DEB9BBBE847E4DB548BEBE4EF3E6094A2930B1BAA987FC535E56162`。 | 仅检查路径、大小、时间和哈希；未运行、未安装、未公开。 | 私有候选，留待 03 审计。 |
| Python sidecar 候选 | 私有构建线索 | 被 Git 忽略的 `dist/vault_engine.exe`；104,569,380 bytes；修改时间 `2026-05-24 22:16:43 +08:00`；SHA-256 `6BB177B96079D1B4383F51600557628D9222052E5C246DB9CA9F77CD04F22024`。 | 同上。 | 私有候选，留待 03 审计。 |
| Windows 构建源码候选 | 可回溯构建入口 | 提交 `e9b3ae16100b43b2f532ea32fcbfc2f9c3434c72` 中的 `scripts/build-windows-release.ps1`、Tauri 配置、sidecar spec 与发行说明；版本号 `0.1.0`。 | 发行说明已明确标注“未验证的最终源码候选”。 | 保留；不得表述为已发布、已安装验证或公开作品集交付。 |

## 5. 敏感信息线索检查

本节只记录位置、检查范围和处置建议；不记录任何密钥、Token、个人数据、真实对话、`vault/` 内容、数据库正文或日志正文。

| 范围 | 检查结果 | 建议处置 |
| --- | --- | --- |
| Git 忽略规则 | `.gitignore` 排除 `.env*`、`system_config.json`、日志、SQLite/Chroma 数据、`vault/`、发行与构建目录等。 | 继续保持规则；归档和公开前不得把被忽略运行时资产加入版本控制。 |
| 当前仓库文件名 | 在排除 `vault/`、`dist/`、`build/`、`target/`、`bin/` 后，未发现 `.env*`、数据库或日志命名文件；命中项仅为设计 token 与 UI token 文档名称。 | 文件名扫描不等同于内容审计；未来对外发布前仍需人工审批。 |
| Git 历史文件名 | 仅以文件名扫描历史，未发现 `.env*`、数据库或日志命名线索；未读取历史文件内容。 | 不把此结果表述为“历史中不存在密钥”。 |
| `vault/`、数据库、日志和用户配置 | 按任务边界未读取、未输出、未移动；最小启动仅使用临时 `VAULT_ROOT`。 | 作为私有本地数据保留；06-decommission 前先由用户确认保留、备份和审查方式。 |
| 已跟踪截图 | 依据既有截图清单和 OQ-CLOSE 决策记录为公开候选；本阶段未重新展开图像内容。 | 对任何新的公开渠道逐图人工复核，确认无账号、对话、Trace、主机、端口或密钥信息。 |
| Figma 静态导出 | manifest 与 QA 明确记录为 synthetic、redacted、fixture-only。 | 可按已确认范围保留；仍不得把它们描述为真实生产运行态。 |
| 安装包与构建产物 | 仅列出位置、元数据和 SHA-256，未运行。 | 继续私有保留；03 审计后再决定验证、保留或清理。 |

## 6. 快照结论与下一阶段确认门

1. 当前清理前状态可由本快照、前两次本地提交以及 `vault-os-pre-archive-20260716` 标签共同定位；标签建立后不得推送。
2. 前端生产 Build 与隔离最小后端启动已实际通过，但完整后端单进程测试、画像导入独立测试和两项 Web 搜索文案断言存在未修复失败。Windows 安装包、Tauri bundle、安装/卸载和完整用户路径均未验证。
3. Windows 发行相关源码仍且只能被标识为“未验证的最终源码候选”；现有 `dist/` 资产是私有候选线索，不是 Release，也不进入公开作品集。
4. 本阶段未上传、公开、移动或删除资产，未推送提交或标签，未读取项目 `vault/`、真实对话、数据库或日志正文。
5. 进入 `03-audit-only` 前，需要用户确认：可以以此快照为基础开始只读审计；该确认不授权任何删除、移动、发布、停服、撤销密钥或修改 README。
