# Vault OS UI Tokens

本文档记录 Vault OS Phase 1 前端设计系统 token。当前唯一实现源为：

`chat-ui/src/assets/cyber-theme.css`

后续新增或修改 UI 样式时，应优先使用这些 CSS variables，避免在 scoped CSS 中继续散落硬编码颜色、阴影、圆角、间距和动效值。

## 设计方向

Vault OS 保留暗色、终端感、轻赛博识别度，但降低大面积霓虹和强发光效果。

核心原则：

- 大面积背景保持低亮度、低饱和。
- `--accent` 主要用于小面积强调、选中态、边框、状态点和关键文字。
- 危险、警告、成功、信息状态必须使用语义 token。
- 所有可键盘聚焦的交互元素必须保留可见 `focus-visible`。
- 组件样式优先复用 token，不新增一次性视觉值。

## Token 分类

### 字体

- `--font-ui`：普通 UI 与 Markdown 正文字体。
- `--font-mono`：终端、输入框、状态、代码、编号等固定宽度场景。

### 背景与层级

- `--bg-app`：应用最底层背景。
- `--bg-shell`：主工作区、侧栏等基础壳层。
- `--bg-panel`：卡片、弹窗、配置面板等普通面。
- `--bg-panel-raised`：悬浮或强调卡片面。
- `--bg-console`：底部命令栏、Trace 面板、代码块等深层面。
- `--bg-overlay`：Modal 遮罩。
- `--bg-hover` / `--bg-hover-strong`：普通 hover 面。
- `--bg-selected`：导航与分段控件选中背景。

### 文本

- `--text-primary`：主标题、重要内容。
- `--text-secondary`：正文、普通信息。
- `--text-muted`：辅助说明。
- `--text-disabled`：禁用、空状态、弱提示。
- `--text-inverse`：亮色背景上的反色文字。

### 强调与状态

- `--accent`：主强调色，克制使用。
- `--accent-strong`：更高亮的强调文本或 focus 轮廓。
- `--accent-soft`：低强度强调背景。
- `--accent-border`：强调边框。
- `--danger` / `--danger-strong` / `--danger-border`：危险、删除、失败。
- `--warning` / `--warning-strong`：警告、降级。
- `--success`：成功、已完成。
- `--info`：信息提示。

### 边框

- `--border-subtle`：弱边界。
- `--border-strong`：普通可见边界。
- `--border-muted`：低层级结构边界。
- `--border-dashed`：冲突、提示、上传等虚线边界。

### 圆角

- `--radius-xs`：小按钮、标签。
- `--radius-sm`：输入框、消息气泡、Trace 行。
- `--radius-md`：弹窗、普通面板。
- `--radius-lg`：卡片、大面板。
- `--radius-pill`：徽标、胶囊筛选控件。

### 间距

- `--space-2xs`：极小内边距。
- `--space-xs`：小按钮、紧凑控件。
- `--space-sm`：控件内部间距。
- `--space-md`：普通控件间距。
- `--space-lg`：行内元素和小区块间距。
- `--space-xl`：卡片、表单区块间距。
- `--space-2xl`：命令栏、弹窗按钮间距。
- `--space-3xl`：页面级 padding。
- `--space-4xl`：大块内容 padding。

### 阴影

- `--shadow-panel`：卡片 hover、轻浮层。
- `--shadow-popover`：Modal、沉浸侧栏。
- `--shadow-glow-soft`：克制的强调光晕。
- `--shadow-danger-soft`：危险操作 hover 光晕。

### Focus 与动效

- `--focus-ring`：键盘 focus ring。
- `--focus-ring-offset`：focus 外扩距离。
- `--duration-fast`：快速反馈。
- `--duration-base`：普通 hover/active。
- `--duration-slow`：侧栏、弹窗、面板过渡。
- `--ease-standard`：默认缓动曲线。

## 使用约定

1. 新增样式优先使用 `var(--token-name)`。
2. 不在组件 scoped CSS 中直接写新的品牌色、状态色或阴影值。
3. 只有 token 源文件可以新增原始色值。
4. 交互态必须包含 hover、active/selected、disabled、focus-visible 中适用的状态。
5. 危险操作必须使用 `danger` 语义 token，不复用 accent。
6. 大面积背景不使用 `--accent` 实色填充。
7. Markdown 样式继续维护在 `cyber-theme.css`，不要拆散到各视图组件。
8. 业务逻辑、WebSocket、数据结构和插件安全语义不得通过样式 token 变更。

## 当前覆盖范围

Phase 1 已覆盖：

- App Shell
- Sidebar
- Bottom Command Console
- Modal / Toast
- Terminal / Trace
- Chat bubbles
- Knowledge list cards
- Memory staging cards
- Note detail
- Profile import
- Settings
- VPM center
- Markdown 基础样式

## 后续维护

当 UI 需要新增视觉语义时，先判断是否属于现有 token 分类。

可以新增 token 的情况：

- 出现新的稳定语义，例如 trust、plugin、sandbox、readonly。
- 多个组件重复出现同一种视觉值。
- 当前 token 无法表达清晰的层级或状态。

不应新增 token 的情况：

- 只服务单个一次性装饰。
- 为绕过现有设计约束而新增近似颜色。
- 为某个页面单独创建不通用的间距、圆角或阴影。
