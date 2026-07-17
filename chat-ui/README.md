# Vault OS Frontend

## 前端定位

`chat-ui/` 是 Vault OS 的前端子项目，基于 Vue 3、Vite 和 Tauri v2 构建，用于承载本地桌面工作台前端。

它负责主控终端、Command Console、Trace 基础观测面板、AgentDock、知识/记忆视图、设置和插件中心等界面。后端负责会话推理、记忆/RAG、工具执行、Trace 记录和插件安全边界，前端负责把这些能力组织成可操作、可观察、可判断状态的桌面工作流。

## 当前状态

### 已完成

- Tauri/Vite 基础工程。
- WebSocket 连接。
- 读取 `.server_port` / `.run_token`。
- 主界面路由/视图骨架。
- 基础组件文件存在。

### 阶段性完成

- 主控体验 v1 产品化骨架。
- 分组导航。
- Command Console。
- Trace 基础观测面板。
- AgentDock。
- `cyber-theme.css` design tokens。
- 部分页面接入 `PageFrame` / `SegmentedControl` / `VaultCard` / `DangerDialog`。

### 下一阶段

- 业务页一致性。
- 高风险确认体系化。
- 插件权限弹窗统一。
- Trace 摘要、错误解释、恢复建议。
- 更多组件覆盖。

## 前端目录说明

- `src/App.vue`：应用 shell，包含主导航、视图挂载、Command Console、AgentDock、全局确认/权限弹窗等入口。
- `src/composables/useNeuroLink.js`：前端核心状态与 WebSocket 通信层，维护连接状态、消息流、临时会话、Trace、插件面板、记忆待审和插件权限请求等状态。
- `src/views/*`：业务视图目录，包含主控终端、知识列表、笔记详情、记忆同步、画像导入、设置和插件中心等页面。
- `src/components/*`：通用组件目录，包含 `AgentDock`、`CyberMarkdown`、`DangerDialog`、`PageFrame`、`SegmentedControl`、`VaultCard` 等组件。
- `src/assets/cyber-theme.css`：全局设计 token 与基础样式，覆盖颜色、背景层级、边框、圆角、间距、阴影、focus 和 Markdown 基础表现。
- `src-tauri/*`：Tauri v2 桌面壳相关配置与 Rust 代码，包含窗口、能力声明、命令注册、运行时端口/token 读取和桌面构建配置。

## 常用命令

以下命令必须在 `chat-ui/` 目录下执行。

```powershell
npm run dev
```

启动 Vite 前端开发服务。

```powershell
npm run build
```

构建前端资源。

```powershell
npm run preview
```

预览已构建的前端资源。

```powershell
npm run tauri -- dev
```

启动 Tauri 桌面开发模式。

当前 `package.json` 未声明 lint 脚本。

## 后端依赖

前端开发通常需要先在仓库根目录启动后端：

```powershell
python server.py
```

后端启动后会写入运行时端口和 token，前端通过 `.server_port` / `.run_token` 建立连接。桌面生产模式由 sidecar 处理，具体行为以当前 Tauri 配置为准。

## 文档导航

- [../README.md](../README.md)：项目入口、启动方式、核心能力和当前状态。
- [../docs/PRODUCT.md](../docs/PRODUCT.md)：产品定位、产品化改版边界、当前能力和 Roadmap。
- [../AGENTS.md](../AGENTS.md)：全仓协作规则、修改约束和 Done Definition。
- [./AGENTS.md](./AGENTS.md)：前端局部修改守则，包含 UI 风格、组件复用、高风险文案和验证要求。

根目录文档是产品定位和全仓规则来源；`chat-ui/AGENTS.md` 是前端范围内的补充约束。
