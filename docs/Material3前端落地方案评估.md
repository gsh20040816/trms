# Material 3 React 落地方案评估

更新时间：2026-04-29

本文记录 TRMS Web 前端 Material 3 重写的库选型，作为 P5 任务批次的前置依据。本轮不实际安装任何依赖，不改动业务代码。

## 1. 决策

采用 **MUI v7（@mui/material）** 作为 Material 3 React 落地库。

## 2. 候选方案对照

| 方案 | 版本 / 状态 | 优点 | 风险 | 结论 |
|---|---|---|---|---|
| **MUI v7** | 稳定，2026-04 主流 | 生态最成熟；文档完备；TS 类型一流；含 DataGrid、Pickers、Snackbar、Dialog；M3 token 已对齐；社区可搜性强 | bundle 较大；M3 迁移仍在进行中（v6 起），部分组件仍在过渡 | 采用 |
| sixui | v5.1.0（2025-11） | 纯 M3、react-aria、110+ 组件、SSR 友好 | 社区小、生态弱；文档较薄；中文资料几乎没有 | 备选 |
| Actify | 偏小 | M3 + Tailwind，react-aria | 组件数量少，部分仍在补完 | 拒绝 |
| material-web (Lit) + 自封装 | Google 官方 | 与规范距离最近 | Web Component 和 React 19 表单/事件桥接成本高，受控组件不友好 | 拒绝 |
| 不引库，手写 M3 token + 组件 | — | 零依赖 | 工作量极大；需要自造 ripple/elevation/state layer/动画；与"专注业务"原则冲突 | 拒绝 |

选择 MUI v7 的核心理由：

1. 项目是**内部系统**，bundle 大小不是关键约束；可视化与可维护性优先。
2. MUI v7 的 `createTheme` 已经直接支持 Material 3 token（color schemes、`palette.tonalOffset`、Roboto Flex），与 M3 设计意图一致。
3. 自带成熟的 **DataGrid、DatePicker、Snackbar、Dialog、Autocomplete、Stepper、Tabs**，可以直接替换当前自造的 `dashboard.tsx` 中所有组件，并显著减少 `styles.css`（当前 1700+ 行）的体积。
4. TypeScript 类型完备，与现有 React 19 + Vite + Vitest 生态无冲突。
5. AI/Cursor 辅助代码生成能力对 MUI 支持最好。

## 3. 引入新依赖说明

按 `AGENTS.md` "确需新增依赖时，必须说明原因和影响范围" 要求，列出本批次将引入的依赖：

| 依赖 | 版本 | 用途 | 影响 |
|---|---|---|---|
| `@mui/material` | ^7.x | 核心组件库 | 主 bundle 增加约 80~120 kB（gzipped） |
| `@emotion/react` | ^11.x | MUI 默认样式引擎 | 必需 peerDep |
| `@emotion/styled` | ^11.x | MUI 默认样式引擎 | 必需 peerDep |
| `@mui/icons-material` | ^7.x | M3 风格图标 | 按需 tree-shake |
| `@fontsource/roboto-flex` | ^5.x | M3 标准字体 Roboto Flex | 自托管，避免对 Google Fonts 的运行时依赖（生产 CSP 友好） |
| `notistack` 或 MUI 自带 Snackbar | — | 全局消息中心 | 可选；首选 MUI 自带 + 自写 Provider，避免再加新 dep |

不引入：

- 不引入 `notistack`，使用 MUI 自带 `Snackbar` + 自写最小 `SnackbarProvider`。
- 不引入 `@mui/x-data-grid` 商业版；若需高级表格能力，使用社区版 `@mui/x-data-grid`（MIT），并在引入轮次单独说明。
- 不引入 `react-hook-form`；继续使用现有受控表单写法，避免一次引入多种范式。

## 4. 测试改动面预估

当前 `web/src/` 测试约 30+ 个 `.test.tsx`，多数以 `screen.getByRole` / `screen.getByText` 查询，少量依赖具体 className（如 `.route-link`、`.status-badge-warning`、`.task-status-open` 等）。

预计测试改动：

- **不需要改的**：使用 `getByRole('button', { name: ... })`、`getByText(...)` 的断言（占多数），MUI 组件保留语义角色，不受影响。
- **需要改的**：
  - 任何 `container.querySelector(".some-class")` 或 `expect(element).toHaveClass("xxx")` 形式的断言（少量）。
  - 直接对 DOM 结构做硬编码层级查询的断言（少量）。
- **可能需要补 polyfill**：MUI v7 的 Popper / Modal 在 jsdom 中可能需要 `ResizeObserver` / `matchMedia` polyfill；统一在 `src/test/setup.ts` 中补齐。

每轮重写都将同步更新该轮涉及的测试，不通过删除或弱化断言制造通过。

## 5. 不在本批次范围内的事项

- 不重写后端 API 契约。
- 不调整路由路径定义（除将旧成员二级路由改为重定向到工作台 tab 之外，由对应 round 单独处理）。
- 不引入 SSR / Next.js。
- 不引入 i18n 框架（当前文案仍为简体中文硬编码）。
- 不替换现有 `vitest` / `@testing-library/react` 测试工具链。

## 6. 后续轮次顺序

详见 `TASKS.md` 中 P5 章节，按顺序：

1. 评估并确认 Material 3 React 落地方案（本文档）
2. 引入 Material 3 主题与基线依赖
3. 重构应用骨架：Top App Bar + Navigation Rail + Snackbar
4. 重写登录/注册页交互
5. 重写首页：任务驱动总览
6. 重写成员端任务列表与单任务工作台
7. 重写管理员任务详情：列表+详情联动
8. 重写表单与上传组件
9. 引入 ConfirmDialog 守护破坏性操作
10. 移除遗留 `styles.css` 与冲突类
