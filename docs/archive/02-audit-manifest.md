# Vault OS 只读审计与清理候选清单

> 本清单完成 `03-audit-only` 的只读审查。它记录候选决定，不构成删除、移动、重命名、提交、打标签、推送、安装包运行、停服或配置修改的授权。

## 1. 审查范围与方法

| 项目 | 记录 |
| --- | --- |
| 审查日期 | 2026-07-17 00:09 +08:00 |
| 审查基线 | `vault-os-pre-archive-20260716` → `49b7b3e16a703abbb30ec0d753aad24a34b44ab1` |
| 审查开始时工作区 | 干净；`git status --short` 无输出，`git diff --check` 无输出。 |
| 基线后的既有差异 | 当前 `HEAD` 为 `a229dc8311fdebb16f0a78a7369721b6e0308707`；相对基线仅有 `docs/archive/PROJECT_CLOSURE_STATE.md` 的元数据更正。 |
| 静态检索范围 | 已跟踪后端、前端、Tauri、测试、插件源码、构建/发布脚本、依赖清单、忽略规则、文档、设计资产，以及 `build/`、`dist/`、`target/`、`bin/`、`discard/`、`temp/`、`.venv/`、`vault/`、`vault_seed/` 的路径、元数据和必要哈希。 |
| 已执行验证 | Git 基线与状态检查；静态导入/引用检索；本地相对 Markdown 链接检查（未发现断链）；安装包 SHA-256 对比。 |
| 未执行的动作 | 未读取运行时数据库、日志、真实对话或密钥；未运行 Build、测试、服务、Docker、Tauri、安装包或清理脚本；未检查外部账号、账单、Release 或 CI 执行环境。 |

### 1.1 证据摘要

- `main.py` 静态导入记忆、RAG、向量库、工具、Trace 与规则模块；`server.py` 导入数据库、异步任务和 Trace 模块。未发现可直接删除的当前后端模块。
- `App.vue` 异步加载所有现有视图；通用组件、`useNeuroLink`、`useScrollAffordance` 与 `vpmLoader` 都有静态引用。
- `server.py` 通过 `importlib` 挂载插件，前端 `vpmLoader` 运行时加载插件 UI。因此 `vault/`、`vault_seed/`、插件依赖和 sidecar 不能仅凭“无普通 import”删除。
- `tauri.conf.json` 的 `externalBin` 与 `resources` 分别要求 `chat-ui/src-tauri/bin/vault_engine-x86_64-pc-windows-msvc.exe` 和 `bin/_internal/`；二者是当前桌面候选构建的动态输入。
- 根 `Dockerfile` 仍复制根目录不存在、仅位于 `discard/` 的 `data_pipeline.py` 与 `llm_engine.py`，以当前工作树无法完成 Docker Build；是否废弃 Docker 路径尚未获得人工确认。
- `dist/Vault OS_0.1.0_x64-setup.exe` 与 `chat-ui/src-tauri/target/release/bundle/nsis/Vault OS_0.1.0_x64-setup.exe` 的 SHA-256 均为 `ACEEE0B63DEB9BBBE847E4DB548BEBE4EF3E6094A2930B1BAA987FC535E56162`，属于同一安装包副本。
- 已跟踪的五张截图、四张 Figma 静态导出、Eval 报告和设计输入均有 README、资产索引或快照证据；Figma 导出仅可表述为 synthetic、redacted、fixture-only 静态资产。

## 2. 完整候选清理清单

| ID | 路径或模块 | 类别 | 原用途 | 当前引用证据 | 风险 | 候选决定 | 处理理由 | 删除/迁移后验证 | 用户审批 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CLN-001 | 根目录当前后端模块：`main.py`、`server.py`、`agent_runner.py`、`core_bus.py`、`db.py`、`memory_*`、`rag_assembler.py`、`chroma_engine.py`、`tool_*`、`plugin_security.py`、`trace_system.py`、`habit_extractor.py`、`init_vault.py` | 代码 | 当前本地 Agent、记忆、RAG、工具、Trace 与启动 | `main.py`、`server.py` 与模块间 import 链 | 高 | 保留 | 当前入口或运行时模块；本审计未发现已替代实现。 | 后续任何代码清理须 Build + 后端关键流程/测试。 | 不适用 |
| CLN-002 | `chat-ui/src/`、`chat-ui/src-tauri/src/main.rs`、前端视图/组件/composable | 代码 | 当前桌面 UI 与本地连接 | `App.vue` 动态加载各视图；组件和 composable 均有引用 | 高 | 保留 | 当前 UI 与 WebSocket/插件交互链路的一部分。 | 后续任何清理须前端 Build、桌面关键路径验证。 | 不适用 |
| CLN-003 | `tests/` | 测试 | 当前可复现验证材料 | `01-final-snapshot.md` 已记录 11 个测试文件与失败边界 | 中 | 保留 | 失败记录仍是归档事实和重构输入，不能因当前失败删除。 | 仅在后续重构后更新测试基线。 | 不适用 |
| CLN-004 | `vault/plugins/music_agent/`、`vault/plugins/README.md` | 动态插件 | 一方插件与协议 | 服务器枚举 `VAULT_ROOT/plugins` 并动态挂载；工具注册表扫描 manifest/tools | 高 | 保留 | 动态注册风险高；当前第一方插件仍是产品能力与权限边界证据。 | 若将来卸载，须走插件协议、权限与 RAG 数据路径审查。 | 不适用 |
| CLN-005 | `vault_seed/` | 打包输入/初始化数据 | 首次启动或空 vault 初始化 | `main.py` 将其作为回退来源；`vault_engine.spec` 将其打包为 datas | 高 | 保留 | 虽被 `.gitignore` 忽略，仍是当前 sidecar 的运行时输入。 | 清理前先验证干净安装/首次启动；不得读取或公开其中可能的配置值。 | 不适用 |
| CLN-006 | `docs/assets/`、`design-automation/`、`docs/EVAL_REPORT.md`、产品/架构/案例文档 | 文档/设计证据 | 作品集、架构和质量证据 | README、资产索引、设计 QA 与最终快照均定位这些资产 | 中 | 保留 | 已确认公开候选或私有证据链；不能按未被运行时代码引用处理。 | 公开前逐图/逐文档复核敏感信息与表述边界。 | 不适用 |
| CLN-007 | `docs/draft/eval_review.md` | 忽略草稿文档 | Eval 修改建议与人工复核笔记 | 未被跟踪；含失效的绝对本机路径链接；结论部分已被 `EVAL_REPORT.md` 吸收 | 中 | 移出主仓库 | 保留为私有审计笔记即可，不应继续作为仓库文档入口。 | 移出后重新检查工作区与文档链接；保留其去向记录。 | 待确认 |
| CLN-008 | `docs/ARCHITECTURE.md` 中 Eval 总计 `33 通过 / 1 部分通过 / 11 未通过` | 文档事实 | 架构与质量边界说明 | 与 `docs/EVAL_REPORT.md` 的 `33 通过 / 2 部分通过 / 10 未通过` 冲突 | 中 | 待人工确认 | 属于事实冲突，不能在审计阶段猜测应采用哪个计数。 | 确认来源后仅做文档一致性检查。 | 待确认 |
| CLN-009 | `Dockerfile` | 部署配置 | 旧容器化启动路径 | `COPY data_pipeline.py`、`COPY llm_engine.py`，两文件仅存在于 `discard/`；无 `.dockerignore` 或 Compose/CI 配置 | 高 | 待人工确认 | 当前 Docker Build 静态上不可复现；可能仍对应未审计的外部部署。 | 先确认是否有部署，再选择修复、保留为历史或删除；如删除须检查外部部署与文档。 | 待确认 |
| CLN-010 | `discard/data_pipeline.py`、`discard/llm_engine.py` | 旧代码 | Dockerfile 所指向的旧数据/LLM 路径 | 仅根 `Dockerfile` 静态引用 | 高 | 待人工确认 | 删除前必须先决定 Dockerfile 的归属；不能以破损配置反推旧代码无价值。 | 确认 Docker 决策后，检索 Docker/外部部署引用。 | 待确认 |
| CLN-011 | `discard/{actions.jsonl,api_test.http,Briefing_Today.md,chat_mode.py,ingestion_pipeline.py,session_draft.jsonl,vault_kernel.py,vault_tasks.json,web_ui.py,2}` | 旧代码/临时数据 | 忽略的旧实验、草稿与本地数据 | 除自身外未发现静态代码、配置、构建脚本或文档引用 | 中 | 删除 | 不是当前运行时、构建、设计或已确认的证据链；`actions.jsonl`/草稿仍须按私有数据处理。 | 用户批准后逐个明确路径删除；再次检索文件名并执行 Git/文件检查。 | 待确认 |
| CLN-012 | `.gitignore` 中 `discard/`、`docs/draft`、`temp/` 规则 | 配置 | 隐藏本地旧代码、草稿和临时产物 | `discard/`、草稿与 Windows staging 目录实际存在 | 中 | 待人工确认 | 清理决定后需判断规则是否仍应保护私人临时资料；当前不能改动忽略边界。 | 在批准清理后检查 `git status --ignored` 与保留目录策略。 | 待确认 |
| CLN-013 | `.gitignore` 中 `tests/`、`vault_seed/` 规则 | 配置 | 忽略本地测试与初始化数据 | 两者对当前归档和可重复构建均有价值；`vault_engine.spec` 打包 `vault_seed/` | 高 | 待人工确认 | 新测试与 seed 变更可能不出现在常规 Git 状态中；不能直接移除或保留而不先确认敏感数据边界。 | 确认哪些脱敏 seed/测试文件应版本化后再作 Git 规则审查。 | 待确认 |
| CLN-014 | `requirements.txt` 的 `feedparser`、`trafilatura` | Python 依赖 | 旧内容抓取能力候选 | 在当前受审代码与第一方插件中未发现 import；动态插件可共享 Python 环境 | 高 | 待人工确认 | 静态无引用不足以删除，动态插件或外部运行方式尚未审计。 | 在隔离环境确认全部插件/工具清单后，执行后端测试与最小启动。 | 待确认 |
| CLN-015 | `chat-ui/package.json` 的 `@tauri-apps/plugin-opener` | 前端依赖 | Tauri opener JS API 候选 | 当前 `chat-ui/src/` 无该包 import；Rust crate 仅由 `src/lib.rs` 使用 | 高 | 待人工确认 | 需先决定 `lib.rs` 是否为历史模板，不能单独删依赖。 | 清理后执行 `npm ci`、前端 Build 和 Tauri Build。 | 待确认 |
| CLN-016 | `chat-ui/src-tauri/src/lib.rs`、Cargo 的 `tauri-plugin-opener`、`serde`、`serde_json` 直接声明 | Rust 代码/依赖 | Tauri 模板库与 opener 示例 | 当前运行入口是 `main.rs`；`main.rs` 不调用 `chat_ui_lib::run`，`lib.rs` 含独立 greet/opener builder | 高 | 待人工确认 | 疑似残留模板，但 Cargo 的库目标、桌面/移动目标和打包影响未验证。 | 先确认目标平台；后续执行 Cargo/Tauri Build 与安装包验证。 | 待确认 |
| CLN-017 | `__pycache__/` | 解释器缓存 | Python 字节码缓存 | `.gitignore` 忽略；可由 Python 自动再生 | 低 | 删除 | 无源码、配置或文档引用，且可重复生成。 | A-1 已执行：用户手动删除 `__pycache__/` 与 `tests/__pycache__/`；随后仅确认两路径不存在，未运行 Python 导入/启动。 | 已批准并完成（A-1；2026-07-17） |
| CLN-018 | `.venv/`（30,402 文件，约 710.7 MB） | 本地依赖环境 | 本机构建/测试环境 | `.gitignore` 忽略；快照已记录 Python/pip 版本和 `requirements.txt` | 低 | 删除 | 可由清单重建，不是归档源码或证据链；保留清单与快照即可。 | 若后续还要本机验证，先重建环境并运行约定命令。 | 待确认 |
| CLN-019 | `build/vault_engine/` | PyInstaller 中间产物 | sidecar 打包缓存、xref 与警告文件 | `scripts/build-windows-release.ps1` 使用其自身临时 workpath；当前目录未被脚本引用 | 低 | 删除 | 当前构建可重生，且不是安装包/sidecar交付输入。 | A-1 已执行：用户手动删除 `build/vault_engine/`；随后仅确认该路径不存在，未运行重新打包。 | 已批准并完成（A-1；2026-07-17） |
| CLN-020 | `build/chroma_behavior_20260524221523/`、`build/legacy_chroma_20260524222107/`、`build/smoke_vault_*` | 测试运行时数据 | Chroma/SQLite、测试 vault、日志与插件副本 | `.gitignore` 忽略；不被当前入口或构建脚本引用 | 高 | 待人工确认 | 含 SQLite、聊天/记忆/配置线索；未读取内容，不能确认是否含个人数据或复盘价值。 | 先完成隐私与保留期限确认；若批准，逐目录、逐路径处理并检查无共享数据。 | 待确认 |
| CLN-021 | `temp/windows-release-build-20260716/`、`temp/windows-release-onedir-20260716/`（约 569.7 MB 的 `temp/`） | 临时发行 staging | 2026-07-16 Windows 打包中间/目录式 sidecar 候选 | 构建脚本每次新建带时间戳 staging 目录；现有目录未被配置引用 | 中 | 待人工确认 | 与未验证安装包/sidecar 的私有归档决策相关，且可能含重复二进制。 | 先核对其与保留候选的哈希和隐私边界，再决定删除。 | 待确认 |
| CLN-022 | `chat-ui/src-tauri/target/debug/`、`target/release/` 中非 `bundle/` 缓存（约 10.86 GB 的 `target/` 总量） | Rust/Tauri 编译缓存 | 本地 Cargo/Tauri 构建中间产物 | `src-tauri/.gitignore` 忽略；仅 Tauri 构建工具隐式使用 | 中 | 删除 | 可由 Cargo/Tauri 重建；安装包候选另列，不能连同 bundle 一并处理。 | 用户批准后保留/移出 bundle 候选，再删除明确缓存目录并重新 Build。 | 待确认 |
| CLN-023 | `chat-ui/src-tauri/target/release/bundle/nsis/Vault OS_0.1.0_x64-setup.exe` | Windows 安装包 | 2026-07-16 NSIS 私有候选，78,230,654 bytes | 构建脚本输出位置；SHA-256 已记录，且与 `dist/` 副本一致 | 高 | 移出主仓库 | OQ-CLOSE-003/OQ-CLOSE-007 要求安装包保持私有；尚未安装验证、签名验证或公开。 | B-1 已执行私有归档复制并核验资产引用 `VAULT-OS-PRIV-NSIS-001`：SHA-256 `ACEEE0B63DEB9BBBE847E4DB548BEBE4EF3E6094A2930B1BAA987FC535E56162` 一致；本批次按授权保留仓库源文件，未运行、安装、签名或公开。 | 已批准；B-1 私有归档已验证，仓库源文件保留 |
| CLN-024 | `dist/Vault OS_0.1.0_x64-setup.exe` | 重复安装包 | NSIS 候选副本 | 与 CLN-023 SHA-256 完全相同 | 中 | 删除 | 与保留的私有候选重复；无需保留两个工作树副本。 | B-1 在 CLN-023 私有归档校验成功后删除精确文件；删除后确认路径不存在。 | 已批准并完成（B-1；2026-07-17） |
| CLN-025 | `chat-ui/src-tauri/target/release/bundle/msi/Vault OS_0.1.0_x64_en-US.msi` | Windows 安装包 | 2026-05-20 MSI 候选，83,910,656 bytes | 当前 `tauri.conf.json` targets 仅为 `nsis`；未验证版本、来源或安装行为 | 高 | 删除 | 可能是较早的交付证据或过期产物，不能仅按当前 target 删除。 | B-1 删除前记录 SHA-256 `72E90D1774709C5FAD19BBBE5142859F4735CD9ED4E7CBB1ED481D2838B3FA60`、83,910,656 bytes、修改时间 `2026-05-20 18:02:17 +08:00`；未保留副本，删除后确认路径不存在。 | 已批准并完成（B-1；2026-07-17） |
| CLN-026 | `dist/vault_engine.exe` | 旧 Python sidecar | 2026-05-24 单文件私有候选，104,569,380 bytes | 当前 Tauri 配置使用 `bin/vault_engine` 目录式 sidecar；无路径引用该文件 | 高 | 删除 | 现有快照明确列为私有 sidecar 候选；未验证，不宜公开或直接丢弃。 | B-1 删除前复核 SHA-256 `6BB177B96079D1B4383F51600557628D9222052E5C246DB9CA9F77CD04F22024`；未保留副本，删除后确认路径不存在。 | 已批准并完成（B-1；2026-07-17） |
| CLN-027 | `chat-ui/src-tauri/bin/vault_engine-x86_64-pc-windows-msvc.exe` 与 `bin/_internal/`（约 241.0 MB） | 当前 sidecar 发行输入 | Tauri 外置 Python 后端及运行时 | `tauri.conf.json` 的 `externalBin`/`resources`；构建脚本将产物复制到这里 | 高 | 保留 | 是当前 Windows 候选打包的必要输入，不能按忽略构建产物处理。 | 如需移出，须先完成可替代重建和 Tauri 安装验证。 | 不适用 |
| CLN-028 | `vault/` 与 `dist/vault/` | 私有运行时数据 | 用户配置、聊天、Trace、数据库、插件运行数据 | `VAULT_ROOT` 默认指向 `vault/`；`dist/vault/` 未读取内容 | 高 | 保留 | 可能含用户数据，且动态插件/本地运行路径依赖；审计边界禁止读取或移动。 | 06-decommission 前由用户决定备份、隐私审查和保留期限。 | 不适用 |
| CLN-029 | `.github/`、CI/CD 与发布自动化 | 缺失配置/外部风险 | 自动化发布或验证线索 | 工作树无 `.github/`；仅发现本地 Windows 构建脚本，未发现工作流文件 | 高 | 待人工确认 | “未发现仓库工作流”不等于不存在外部自动化、Release 或账号配置。 | 06-decommission 前检查 GitHub Actions、Release、外部 runner、账单与密钥归属。 | 待确认 |

## 3. 分批建议

| 批次 | 范围 | 风险 | 前置审批 | 验证命令或流程 | 建议 |
| --- | --- | --- | --- | --- | --- |
| A | CLN-017、CLN-019；CLN-024 仅在 CLN-023 已完成私有归档后 | 低/中 | 用户逐项确认 | 文件路径与 SHA-256 复核；Python 最小导入或后续 Build 检查 | 可先处理，但必须逐个明确路径，不做递归或批量删除。 |
| B | CLN-007、CLN-011、CLN-018、CLN-021、CLN-022、CLN-026 | 中 | 用户逐项确认，并先确定私有归档位置 | 静态检索、文档链接检查、必要的隔离 Build | 先保留证据和私有数据边界，再清理重复/可重建内容。 |
| C | CLN-008 至 CLN-016、CLN-020、CLN-023、CLN-025、CLN-027 至 CLN-029 | 高 | 用户逐项确认；涉及安装包、动态插件、依赖、Docker、外部资源时需额外授权 | Tauri/Windows 安装验证、后端测试、动态插件审查、外部资源清单 | 不在归档关闭的清理阶段自动处理。 |

## 4. 未决项与默认行为

| 项目 | 缺少的证据/决策 | 应由谁决定 | 若不处理的代价 | 建议默认行为 |
| --- | --- | --- | --- | --- |
| Docker 与旧管线 | 是否仍有容器部署、为何 Dockerfile 指向 `discard/` 旧模块 | 用户 | 保留一个静态上不可构建的部署入口，或误删仍在用的外部路径 | 保留并标为不可验证，直到用户确认。 |
| Windows 候选 | NSIS/MSI/sidecar 的实际版本、签名、安装/卸载和私有存储位置 | 用户 | 可能丢失唯一交付证据，或误把未验证产物公开 | 私有保留，不运行、不公开、不删除。 |
| 运行时与测试数据 | `vault/`、`dist/vault/`、`build/*vault*` 是否含个人数据及保留期限 | 用户 | 误删用户数据或保留不必要的敏感副本 | 不读取、不移动；仅完成目录级候选记录。 |
| 动态插件与依赖 | 外部插件是否依赖 `feedparser`/`trafilatura`，`vault_seed/` 哪些内容可版本化 | 用户 | 依赖删除或 Git 规则调整可能破坏动态功能/首次启动 | 保留依赖与忽略规则，等待隔离插件审查。 |
| Tauri 模板残留 | `src/lib.rs`、opener/serde 依赖是否为移动端或历史模板 | 用户 | 误删后影响 Cargo/Tauri 目标或未来平台支持 | 保留，待确认平台范围后再做受控 Build 验证。 |
| Eval 文档冲突 | 两组汇总数中哪一组是最终事实 | 用户 | 架构与 Eval 对外口径不一致 | 不修改任一结论，先确认原始评测口径。 |
| 外部资源 | GitHub Release/Actions、域名、模型 API、存储和账单是否存在 | 用户 | 未关闭的费用、安全或公开资产风险 | 留待 06-decommission 逐项确认。 |

## 5. 审计结论

本阶段未执行任何清理。可立即进入人工审批的低风险候选仅限可再生缓存和已确认重复安装包副本；所有运行时数据、动态插件、sidecar、Windows 候选、Docker、依赖、Git 忽略规则和外部资源均保守地保留或标记为待人工确认。

下一阶段只能在用户明确批准具体候选 ID 或批次，以及排除范围后启动 `04-approved-cleanup`。
