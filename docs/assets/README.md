# Vault OS Assets

本目录用于存放 Vault OS 文档中的作品集展示类视觉资产。

## Screenshot Checklist

截图已存放在 `docs/assets/screenshots/`，可用于 README 和产品文档中的作品集展示。

| File | Scene | Purpose | Status |
|---|---|---|---|
| `01-home-command-console.png` | 首页工作台，显示 Command Console | 展示本地 AI 工作台的主入口和 command-first 工作流。 | 已收录 |
| `02-agent-running-trace.png` | Agent 任务运行中，显示 Trace | 展示可观测的 tool/action 执行过程和运行时状态。 | 已收录 |
| `03-memory-review-permission.png` | 记忆审查或权限确认流程 | 展示谨慎的 memory 写入和审查语义。 | 已收录 |
| `04-plugin-permission-danger-dialog.png` | 使用 DangerDialog 的插件权限流程 | 展示插件边界、敏感权限预览和高风险确认文案。 | 已收录 |
| `05-eval-report-preview.png` | Eval Report 文档或预览状态 | 展示 AI 产品质量意识和 eval 思考。 | 已收录 |

## Capture Guidance

当前清单中的截图均已就位。后续补充或重新截取时，可按以下轻量流程操作；仓库已有后端单元测试和前端构建脚本，但没有 Playwright、Cypress 或 Puppeteer 等专门的截图自动化工具。

建议使用轻量流程：

1. 如果页面状态依赖实时 API 数据，先启动后端：

   ```powershell
   python server.py
   ```

2. 在另一个终端启动前端：

   ```powershell
   cd chat-ui
   npm run dev
   ```

3. 打开 Vite URL，准备每个目标状态，然后用浏览器或操作系统截图工具手动截图。

4. 按清单中的精确文件名保存图片到 `docs/assets/screenshots/`。

如果需要更接近桌面端打包效果的界面，可以使用现有 Tauri dev 命令，不必为了截图额外新增依赖：

```powershell
cd chat-ui
npm run tauri -- dev
```

新增截图时，请在本清单中补充文件名、场景、用途和状态；未实际保存的图片仍应标记为 `TODO`，不要将其视为已完成的作品集资产。
