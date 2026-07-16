# Vault OS 技术债与重构 Backlog

> 本 Backlog 是截至清理前标签 vault-os-pre-archive-20260716 的重构处置清单，不是继续在旧架构上实施功能的授权。优先级只表示未来重构的前置关系，不代表本阶段应修改源码、测试、依赖、Docker、Tauri 配置或运行时数据。

## 优先级规则

- P0：开始重构或承诺处理敏感数据/第三方能力前必须处理的边界。
- P1：MVP 前应处理，影响可验证性、可靠性或交付判断。
- P2：在重构范围和目标平台确定后再处理的遗留项或体验改进。

| ID | 问题/机会 | 证据 | 用户/技术影响 | 重构处置 | 优先级 | 前置条件 |
| --- | --- | --- | --- | --- | --- | --- |
| REB-001 | 后端测试隔离失败：完整单进程发现受到跨模块 sys.modules stub 污染，不能形成可信回归基线。 | docs/archive/01-final-snapshot.md：38 通过、11 错误；tests/ 下 11 个模块。 | 失败可能被测试顺序掩盖，任何重构缺少可靠回归护栏。 | 重写 | P0 | 为每个模块重置 stub/导入状态，使用临时 VAULT_ROOT 与固定夹具，再保存可复现日志。 |
| REB-002 | RAG 缺少独立的不可信内容包装、冲突呈现和输出级 PII 最小披露。 | docs/EVAL_REPORT.md：RAG-04、RAG-05、RAG-06 未通过；rag_assembler.py 仅对第三方插件输出写入不可信约束。 | 检索内容可能被当作指令、被单一化解释或过度披露。 | 重写 | P0 | 明确数据分类、检索引用模型、冲突 UI 和脱敏策略；用隔离夹具与 Trace 验收。 |
| REB-003 | 记忆写入缺少敏感信息与偏见过滤的可证明边界，失败状态对用户不充分可见。 | docs/EVAL_REPORT.md：MEM-03、MEM-06 未通过，MEM-10 部分通过；main.py、memory_system.py。 | 长期记忆可能扩大隐私、偏见或错误状态影响。 | 重写 | P0 | 定义可写入数据等级、拒绝/待审规则、保留期与审计字段；不得读取既有 vault 数据作为先决条件。 |
| REB-004 | 动态插件的权限、依赖、生命周期和数据清理边界尚未完成隔离验证。 | plugin_security.py；tool_registry.py；server.py；docs/archive/02-audit-manifest.md 的 CLN-004、CLN-014、CLN-027、CLN-028。 | 第三方代码/输出、动态依赖和卸载时的 RAG/数据副作用难以通过静态检索保证。 | 拆分 | P0 | 明确插件信任级别、沙箱/进程边界、manifest 契约、一次性夹具和卸载回滚/备份策略。 |
| REB-005 | 运行时数据与隐私保留策略尚未确定。 | main.py 的 VAULT_ROOT 路径；docs/archive/01-final-snapshot.md 第 5 节；docs/archive/02-audit-manifest.md 的 CLN-020、CLN-028。 | vault、数据库、Trace、聊天、配置和插件数据可能含个人信息或密钥，错误迁移/清理会造成泄露或丢失。 | 保留 | P0 | 用户确认数据所有者、私有归档位置、加密/访问、保留期、导出和删除流程；06-decommission 不得越权。 |
| REB-006 | Web 搜索防编造文案断言与实际返回不一致。 | docs/archive/01-final-snapshot.md：test_web_search_tool.py 独立运行 5 通过、2 失败；tool_executor.py 的 action_web_search。 | 出错/空结果时用户可见承诺与测试基线不一致，削弱“如实说明”的产品边界。 | 保留 | P1 | 先确认期望文案与错误对象，再以测试夹具覆盖空结果、依赖缺失和全通道失败。 |
| REB-007 | Agent/Trace 的取消、失败与部分成功语义不完整。 | docs/EVAL_REPORT.md：TOOL-05、TOOL-08 未通过；main.py 的 ThreadPoolExecutor DAG；trace_system.py。 | 后台任务可能产生迟到结果，失败状态可能误导用户。 | 拆分 | P1 | 定义任务 ID、取消协议、终态枚举、父子 span 规则和前端状态机，并做端到端回归。 |
| REB-008 | Windows 交付没有可重复验证的构建、签名、安装、卸载和升级证据。 | docs/archive/01-final-snapshot.md；scripts/build-windows-release.ps1；chat-ui/src-tauri/tauri.conf.json；docs/WINDOWS_RELEASE.md。 | 安装包和 sidecar 只是私有候选，不能作为可支持交付。 | 延后 | P1 | 隔离 Windows 环境、明确证书/签名归属、固定依赖和 sidecar 重建来源；先验证安装/卸载再决定发布。 |
| REB-009 | Eval 汇总存在待人工确认的事实冲突。 | docs/EVAL_REPORT.md：33 通过 / 2 部分通过 / 10 未通过；docs/ARCHITECTURE.md：33 通过 / 1 部分通过 / 11 未通过。 | 对外质量叙事和重构优先级可能依据错误分母。 | 保留 | P1 | 用户确认原始评测口径或原始记录；在确认前保留两份原文和冲突标记。 |
| REB-010 | Docker 是静态上不可构建的旧路径，归属未确认。 | Dockerfile COPY 根目录 data_pipeline.py、llm_engine.py；文件仅在 discard/；docs/archive/02-audit-manifest.md 的 CLN-009、CLN-010。 | 误以为容器化仍可用会导致错误部署判断；直接删除又可能损坏未审计的外部路径。 | 放弃 | P2 | 先由用户确认是否存在容器部署；若不存在，单独审查/移除旧 Docker 路径并更新文档。 |
| REB-011 | Tauri 模板残留和 opener/serde 依赖归属未知。 | docs/archive/02-audit-manifest.md 的 CLN-015、CLN-016；chat-ui/src-tauri/src/lib.rs、Cargo.toml、src/main.rs。 | 清理或保留都可能影响未来桌面/移动目标，当前无 Build 证据可判定。 | 延后 | P2 | 明确支持平台与入口，再在隔离环境运行 Cargo/Tauri Build。 |
| REB-012 | 设计资产与运行实现之间没有可执行映射或验收标准。 | docs/archive/05-design-implementation-gap.md；design-automation/figma/export-manifest.json；docs/assets/screenshots/。 | 静态 fixture 容易被误当作生产能力，UI 重构会脱离真实事件/权限状态。 | 保留 | P2 | 建立页面—状态—事件—验收映射；保留 synthetic/redacted/fixture-only 注记，且不以 Figma 替代运行测试。 |

## 人工确认与外部依赖清单

以下事项不是技术债条目自动可处理的范围，必须由用户在 06-decommission 或重构立项时逐项确认：

1. GitHub Release/Actions、外部 runner、域名、模型 API、对象存储、账单和自动化是否存在，以及其所有者和关闭/保留方案。
2. vault/、dist/vault/、build 中历史测试数据、vault_seed、当前 sidecar、bin/_internal/ 的隐私分类、运行依赖和保留期限。
3. Eval 汇总两种数字的原始口径。
4. Figma 原文件、访问 URL 和公开范围；仓库当前未发现可定位的原文件或 URL。

## 重构启动顺序

1. 先完成 REB-005、REB-001 至 REB-004 的数据、测试和信任边界，形成可安全验证的最小内核。
2. 再处理 REB-006、REB-007、REB-009，建立可观察的 Agent/工具质量基线。
3. 目标平台确认后，处理 REB-008、REB-010 至 REB-012；Windows 与 Docker 不应阻塞尚未定义的核心重构 MVP。
