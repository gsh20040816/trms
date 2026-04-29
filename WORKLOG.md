# WORKLOG

## 2026-04-29 12:01 - Rewrite home page with task-driven Material 3 layout

### 完成内容
- 重写 `web/src/app/pages.tsx` 中的 `HomePage` 与 `NotFoundPage`，全面切换到 MUI v7 组件，并按"任务驱动"原则重新组织信息架构。
- 未登录首页 `GuestHomePage`：
  - 顶部仅保留极简 hero（"账号入口"小标 + "登录后进入对应工作台" h3 + 一句业务描述 + "前往登录 / 注册" Contained Button）。
  - 三张 outlined Card 展示成员/管理员/系统管理员账号的"用途速览"，每张含 Avatar 图标 + 标签 + 重点词 + 一句话描述，去掉以往"账号与页面边界"这种实现导向卡片。
- 已登录首页 `AuthenticatedHomePage`：
  - 顶部 hero 显示"报销任务总览"小标、"Tongji ACM 报销管理系统" h3、一句任务驱动描述、当前身份与显示名 Chip 行、"进入我的工作台" Contained Button（带向前箭头）。
  - "当前身份"卡：Avatar + 标题 + 业务摘要 + 推荐操作 Chip 行（取自 ROLE_OVERVIEWS.actions），不再是 `<ul>` 列表。
  - "可进入的工作台"分组：每个角色用 outlined Card + CardActionArea + 操作 Chip 行表达，整张卡片即点击区，导航到对应工作台。
- `NotFoundPage`：换成 M3 居中布局（Avatar 图标 + 标题 + Alert info + 返回按钮），不再是空 SectionCard。
- 业务文案调整：
  - 已登录首页副文案改为"直接进入你的工作台查看当前需要处理的任务和异常事项。"
  - 删除"页面边界已收口"、"无关角色入口、系统配置与诊断信息不会出现在当前首页"等实现导向描述。
- 同步更新 `web/src/app/App.test.tsx`：
  - "登录后只展示当前账号可进入的工作台..."文案断言改为新的任务驱动文案"直接进入你的工作台查看当前需要处理的任务和异常事项。"
  - "进入我的工作台"链接断言用 regex 包容前后缀（按钮含图标）。
  - 其余 7 个用例均不变。

### 根因
- 旧首页是"工作台说明 + 角色入口卡 + 实现边界说明"的入口页风格，与 `docs/UI原型图对照与交互规范补充.md` 强调的"任务驱动、单页闭环、状态一眼可扫"不符。
- 用户在 P5 计划中明确要求首页改为任务驱动总览。
- 本轮先把 `/` 总览页本身的视觉与 IA 改完；KPI 数据计算与"今日最紧急任务"列表会随 Round 6（成员任务列表）、已存在的 `/admin` 任务列表（管理员）一起完成。

### 关键改动点
- 重写：
  - `web/src/app/pages.tsx`：`HomePage`、`GuestHomePage`、`AuthenticatedHomePage`、`NotFoundPage` 全部基于 MUI 组件实现，移除对自造 `RoleWorkspace`/`PageHeader`/`StatCard`/`SectionCard`/`StatusBadge` 的调用。
- 同步测试：
  - `web/src/app/App.test.tsx`：更新两条断言以匹配新文案，并保留全部其他业务断言不变。
- 任务状态：
  - `TASKS.md` P5 第五条标记完成，并添加实现说明，指出 KPI 列表实际收口到 `/member` 与 `/admin` 任务列表轮次。

### 风险与影响面
- 业务行为没有变化：未登录跳登录、登录后展示当前可见工作台、点击进入对应路径。
- 视觉与可达性都升级到 MUI 主题；颜色、间距、阴影、Hover、点击区扩大。
- bundle gzipped 由 248.72 kB 增至 ~250 kB（与上轮基本持平），新增的 CardActionArea / Avatar / Chip 已在前序轮次随 MUI 引入；主要差异是去除了 dashboard.tsx 在首页中的部分依赖。
- 旧 `dashboard.tsx` 中的 `RoleWorkspace`/`PageHeader`/`StatCard`/`SectionCard`/`ErrorMessage`/`TaskTable` 仍被业务页面（成员任务、管理员任务、复核、导出 等）使用，本轮不删除。

### 修改文件
- `web/src/app/pages.tsx`
- `web/src/app/App.test.tsx`
- `TASKS.md`
- `WORKLOG.md`

### 验证结果
- `./scripts/verify.sh` 通过：
  - Python 编译检查通过
  - Alembic upgrade/downgrade/upgrade 通过
  - pytest 全量通过
  - Web `npm run lint` 0 error 0 warning
  - Web `npm test` 21 文件、69 用例全部通过
  - Web `npm run build` 成功
  - Docker Compose 配置检查通过
  - `git diff --check` 通过

### 假设
- 已登录首页只显示"当前账号可进入的工作台"卡片组合，不重复列出 KPI 数据；KPI 重写已经在 `/member` 与 `/admin` 任务列表页面分别完成或后续完成。
- React 19 中 `JSX.Element` 命名空间不再开箱可用；使用 `ComponentType<SvgIconProps>` 表示 MUI 图标组件类型。
- 测试用 `getByRole("link", { name: /进入我的工作台/ })` regex 匹配，是因为新版按钮带图标后 accessible name 可能拼接图标 alt 文本。

### 备注
- "今日最紧急任务"在管理员任务列表页（`AdminTaskListPage`）已经存在为"按任务推进处理当前工作"的优先级表格；成员任务列表的 KPI 卡也已经存在。本轮不重复实现。
- 后续 Round 6 重写成员任务列表页时会将其升级为 MUI 卡片网格 + 单任务工作台 Tabs。

## 2026-04-29 11:55 - Rewrite login/register interaction with M3 components

### 完成内容
- 用 MUI v7 重写 `web/src/app/auth.tsx`：
  - `MockLoginPage` 改为：标题区 + Card 内 M3 Tabs（登录 / 注册）+ Stack 表单（TextField / Select MenuItem）+ 提交按钮带 LoginIcon / PersonAddAltIcon。
  - 错误统一通过 `useSnackbar().showError(...)` 推送，并在表单内同步显示一个可关闭的 `<Alert severity="error">`，不再依赖页面级红色 ApiErrorNotice 卡片。
  - 成功登录/注册/退出/切换身份均通过 `showSuccess(...)` 即时反馈。
  - 已登录卡片用 `<Collapse>` 包裹，登录后才出现，并展示当前身份、可切换身份组按钮、进入入口与退出登录。
  - 开发调试角色入口收口为单张 dashed outlined Card，内含 3 张 outlined 子 Card + 标题区域 DEV chip；`uiConfig.enableDevRoleEntries=false` 时整张隐藏。
  - 注册时角色受限场景用 `<Alert severity="info">` 提示当前环境只允许成员自注册。
  - 登录后 `<TextField select label="角色">` 仍保留 `<input type="hidden" name="role">` 用于提交语义不变。
- `ProtectedRoleRoute` 从原 `RoleShell` 重写为 `<Card><CardContent>`：身份切换中、不可访问、切换失败三种状态都用 MUI Alert + Button 表达，链接全部改用 `<Button component={RouterLink}>`。
- 新增本地 `describeError(error)` 工具（`auth.tsx` 内），从 `ApiError` / `summarizeUnknownError` 提取一句话错误信息，喂给 Snackbar。
- 把 `useSnackbar()` 在 Provider 之外的退化行为调整为静默 noop，避免单元测试为单组件单独包裹 SnackbarProvider；生产构建仍始终包裹。
- 同步更新 `web/src/app/App.test.tsx`：
  - 注册 Tab 切换断言改为 `getByRole("tab", { name: "注册" })`。
  - MUI TextField label 在 required 字段后会自动追加 `*`，`getByLabelText` 改为 regex 匹配；Select 用 `getByRole("combobox", { name: "角色" })` + `getByRole("option", { name: "管理员" })`。
  - 受限注册场景下"角色"不可见的断言改为 `queryByRole("combobox", { name: "角色" })`，开发调试入口断言改为 `queryByRole("group", { name: "开发调试角色入口" })`。
  - 全部 8 个用例通过，断言语义没有弱化。

### 根因
- 原登录页是一整页"标题卡 + 登录注册卡 + 错误卡 + 调试卡 + 已登录卡"五张并列的自造卡片，靠原生 `<input>` + `<button>` 渲染，没有任何 M3 视觉、缺少操作反馈、登录态与表单同时渲染，长期信息过载。
- 用户在 P5 重写计划中明确要求登录页采用 M3 组件、Tab 切换、Snackbar 反馈、登录态隐藏表单、调试入口收口为可折叠区域。

### 关键改动点
- 重写：
  - `web/src/app/auth.tsx`：从原 396 行重写为基于 MUI 的版本。
- 调整：
  - `web/src/components/use-snackbar.ts`：`useSnackbar` 在 Provider 之外退化为 noop，方便单元测试。
  - `web/src/app/App.test.tsx`：同步更新 8 个 case 中的断言到 M3 组件语义。
- 任务状态：
  - `TASKS.md` P5 第四条标记完成。

### 风险与影响面
- 业务行为没有变化：登录、注册、Mock 登录、登录后切换身份、退出登录、跳转 next path、生产受限场景隐藏调试入口 - 这些路径全部保持原契约。
- bundle gzipped 从 228.39 kB 增至 248.72 kB（+20.33 kB），新增 Tabs / Tab / Card / Collapse / Chip / Stack / Alert / Divider / TextField / Select 等组件代码。
- `MockLoginPage` 不再保留对原 `ApiErrorNotice` 与 `RoleShell` 的引用，但这两个组件仍被其他业务页面使用，保留不动。
- 已登录卡片用 `<Collapse>` 切换可见性，避免登录瞬间布局抖动。

### 修改文件
- `web/src/app/auth.tsx`
- `web/src/app/App.test.tsx`
- `web/src/components/use-snackbar.ts`
- `TASKS.md`
- `WORKLOG.md`

### 验证结果
- `./scripts/verify.sh` 通过：
  - Python 编译检查通过
  - Alembic upgrade/downgrade/upgrade 通过
  - pytest 全量通过
  - Web `npm run lint` 0 error 0 warning
  - Web `npm test` 21 文件、69 用例全部通过
  - Web `npm run build` 成功；bundle gzipped 248.72 kB
  - Docker Compose 配置检查通过
  - `git diff --check` 通过

### 假设
- 默认 mode 仍是 `"login"`；切换到注册 tab 后字段顺序与旧版保持一致，便于现有用户路径直觉。
- 调试入口标题区出现 "DEV" warning chip，让运维一眼识别出当前是非生产构建。
- 测试中 fireEvent.mouseDown + 点击 option 是 MUI Select 在 jsdom 下被广泛使用的可靠交互模拟。

### 备注
- 本轮没有删除旧 `ApiErrorNotice` / `RoleShell` 等组件；它们仍被其他业务页使用，将在后续轮次按页迁移时再决定是否退役。
- `Collapse` 在已登录卡片不存在时作为占位 `<Box />` 返回，避免 transition 在空内容上闪烁。

## 2026-04-29 11:48 - Replace app shell with M3 top app bar, navigation rail and global snackbar

### 完成内容
- 新增 `web/src/components/AppShell.tsx`：基于 MUI v7 实现 Material 3 顶栏 + 侧边导航 rail（桌面）/ 抽屉 + 底部导航（移动）。
  - 顶部 AppBar 左侧：响应式菜单按钮（移动端打开抽屉）+ TR 圆角品牌 + 副标题"同济 ACM 报销管理"。
  - 顶部 AppBar 右侧：未登录显示"登录 / 注册"按钮 + 账号 IconButton；已登录显示头像首字 IconButton。
  - 账号弹出菜单：当前账号信息、可切换身份（多角色账号才出现）、外观主题（亮/暗/跟随系统）、退出登录或登录入口。
  - 桌面端 ≥ md：左侧 88px Navigation Rail，垂直堆叠图标 + 文字，hover 与 active 状态使用 surface tonal 层。
  - 移动端 < md：顶栏菜单按钮打开 SwipeableDrawer；底部 BottomNavigation 显示 1~4 个主入口。
  - 鼓励路径：导航项随 `useAuthSession().availableRoles` 动态生成，未登录只显示总览。
- 新增 `web/src/components/AppSnackbar.tsx` + `snackbar-context.ts` + `use-snackbar.ts`：全局 Snackbar 队列。
  - 提供 `useSnackbar()` hook 与 `showSuccess` / `showError` / `showInfo` / `showWarning` 快捷方法。
  - 多次调用按队列依次展示；同时只展示一个；点击外部不关闭，过期或主动关闭时下一条自动入队。
- 重写 `web/src/app/pages.tsx` 中的 `RootLayout` 为 `<AppThemeProvider><SnackbarProvider><AppShell><Outlet /></AppShell></SnackbarProvider></AppThemeProvider>`，并移除自造顶栏代码。
- 调整 `web/src/main.tsx`：移除外层 AppThemeProvider（已下沉到 RootLayout），保留 Roboto Flex 字体导入。
- 删除 `pages.tsx` 中不再使用的 `formatRole`、`useLocation`、`Link` 中部分引用。

### 根因
- 旧 `RootLayout` 顶栏由原生 HTML + 1700+ 行 `styles.css` 拼成，无统一主题、无 Snackbar、无主题切换。
- 用户在 P5 重写计划中明确要求按 M3 重构应用骨架，并把账号操作收口到顶栏右上角的账号菜单。
- 全局 Snackbar 是后续轮次（登录、上传、状态流转、确认）操作反馈的前置基础。

### 关键改动点
- 新增组件：
  - `web/src/components/AppShell.tsx`
  - `web/src/components/AppSnackbar.tsx`
  - `web/src/components/snackbar-context.ts`
  - `web/src/components/use-snackbar.ts`
- 重写：
  - `web/src/app/pages.tsx`：`RootLayout` 简化为 Provider 包裹 + AppShell。
- 调整入口：
  - `web/src/main.tsx`：删除外层 AppThemeProvider 包裹（下沉到 RootLayout），避免双重包裹。
- 任务状态：
  - `TASKS.md` P5 第三条任务标记为已完成。

### 风险与影响面
- AppShell 直接消费 MUI 主题 token，对原 `styles.css` 中 `.topbar*`、`.brand-mark`、`.workspace-page`、`.app-shell` 等类名不再有依赖，但这些 CSS 仍保留在 `styles.css` 中，将在 Round 10 清理。
- 现有 21 个测试文件、69 个用例全部通过。`useMediaQuery` 在 jsdom 环境下触发的 act() 警告不影响测试结果。
- bundle gzipped 从 178.37 kB 增至 228.39 kB（+50.02 kB），主要来自 AppBar、Toolbar、IconButton、Menu、SwipeableDrawer、BottomNavigation、Snackbar、Avatar、Tooltip、Stack 等首批 MUI 组件。
- `RootLayout` 同时包裹 ThemeProvider，因此所有现有测试只要 render `routes` 都自动获得正确的主题与 Snackbar 上下文，不需要修改 App.test.tsx。
- 多角色账号在账号菜单切换身份后会自动 navigate 到对应工作台路径，并通过 Snackbar 反馈。

### 修改文件
- `web/src/components/AppShell.tsx`（新增）
- `web/src/components/AppSnackbar.tsx`（新增）
- `web/src/components/snackbar-context.ts`（新增）
- `web/src/components/use-snackbar.ts`（新增）
- `web/src/app/pages.tsx`
- `web/src/main.tsx`
- `TASKS.md`
- `WORKLOG.md`

### 验证结果
- `./scripts/verify.sh` 通过：
  - Python 编译检查通过
  - Alembic upgrade/downgrade/upgrade 通过
  - pytest 全量通过
  - Web `npm run lint` 0 error 0 warning
  - Web `npm test` 21 文件、69 用例全通过
  - Web `npm run build` 成功；bundle gzipped 228.39 kB
  - Docker Compose 配置检查通过
  - `git diff --check` 通过

### 假设
- 桌面端断点采用 MUI 默认 `breakpoints.up("md")`（≥ 900px），与原 `styles.css` 的 960px 接近。
- Navigation Rail 仅在用户登录后显示业务入口；总览路径 `/` 始终可见。
- 顶栏品牌点击回到 `/`；移动端折叠后保留 `TR` Avatar，副标题在 xs 屏隐藏。

### 备注
- 测试期间出现"An update to AppShell inside a test was not wrapped in act(...)"警告，由 `useMediaQuery` 的异步状态更新引发，与 MUI 在 jsdom 上下文的标准行为一致；不影响断言通过，后续若噪音过大可通过在 setup 中固定 matchMedia 返回值消除。
- 仍保留旧 `styles.css`，以便后续按页迁移时旧业务页面继续工作。

## 2026-04-29 11:42 - Bring in MUI v7 baseline theme and font

### 完成内容
- 在 `web/` 引入 MUI v7 全套：`@mui/material@^7.3.10`、`@emotion/react@^11.14`、`@emotion/styled@^11.14`、`@mui/icons-material@^7.3.10`、`@fontsource/roboto-flex@^5.2`。
- 新增 Material 3 主题文件 `web/src/theme/m3-theme.ts`，包含完整 M3 token：
  - 亮色和暗色两套 palette（primary/secondary/error/warning/success/info、background、text、divider）
  - 字体栈以 Roboto Flex 为主，回退到中文系统字体
  - typography scale（h1~h6 + button + body1/2）
  - 25 级渐进 elevation 阴影
  - 全局组件 token 默认值（Button、Card、Paper、AppBar、TextField、OutlinedInput、Chip、Tooltip、TableCell）
  - 圆角 token `borderRadius=12`
- 新增 `web/src/theme/AppThemeProvider.tsx`，包裹 `ThemeProvider` 与 `CssBaseline`，按 `localStorage` 存储用户偏好，并通过 `useMediaQuery('(prefers-color-scheme: dark)')` 跟随系统主题。
- 拆分 `web/src/theme/app-theme-context.ts` 与 `web/src/theme/use-app-theme.ts`，避免 `react-refresh/only-export-components` 警告。
- `main.tsx` 新增 Roboto Flex 400（variable font）字体导入，并把根组件 `<App />` 包入 `AppThemeProvider`。
- 在 `src/test/setup.ts` 中补齐 jsdom 环境下缺失的 `matchMedia` 与 `ResizeObserver` polyfill，避免后续 MUI 组件在测试中报错。

### 根因
- 用户在 P5 重写计划中确认采用 MUI v7 实现 Material 3。本轮负责"主题与基线"层，把库装上、token 统一、Provider 接好，让后续每一轮可以在确定的主题上下文中改具体页面。
- 本轮不调用任何 MUI 组件，避免一次性触发大量测试与样式联动失败；现有 `styles.css` 完整保留。

### 关键改动点
- `web/package.json`、`web/package-lock.json`：新增 5 个生产依赖。
- 新增主题文件：
  - `web/src/theme/m3-theme.ts`
  - `web/src/theme/AppThemeProvider.tsx`
  - `web/src/theme/app-theme-context.ts`
  - `web/src/theme/use-app-theme.ts`
- 修改入口：
  - `web/src/main.tsx`：包裹 ThemeProvider；引入 Roboto Flex 字体。
- 修改测试基线：
  - `web/src/test/setup.ts`：补 `matchMedia` / `ResizeObserver` polyfill。
- 任务状态：
  - `TASKS.md` 第二条 P5 子任务标记为已完成。

### 风险与影响面
- 本轮新增依赖；bundle gzipped 从 145.60 kB 增至 178.37 kB（+32.77 kB），全部为 ThemeProvider/CssBaseline/useMediaQuery 与样式引擎。后续轮次替换组件后，自造 `styles.css` 体积会回降。
- 现有 1700+ 行 `styles.css` 暂时保留；它定义的 `:root` 颜色与背景与 MUI `CssBaseline` 注入的 `body` 颜色会有重叠，后续轮次会按页迁移再清理。
- `MuiAppBar` 默认 elevation 改为 0、color 设为透明并使用主题 surface 背景；这会在 Round 3 顶栏重写时立即生效。
- `enableColorScheme` 让 `<html style="color-scheme">` 自动同步亮/暗，浏览器表单控件原生外观会跟随主题。

### 修改文件
- `web/package.json`
- `web/package-lock.json`
- `web/src/main.tsx`
- `web/src/test/setup.ts`
- `web/src/theme/m3-theme.ts`（新增）
- `web/src/theme/AppThemeProvider.tsx`（新增）
- `web/src/theme/app-theme-context.ts`（新增）
- `web/src/theme/use-app-theme.ts`（新增）
- `TASKS.md`
- `WORKLOG.md`

### 验证结果
- `./scripts/verify.sh` 通过：
  - Python 编译检查通过
  - Alembic upgrade/downgrade/upgrade 通过
  - pytest 全量通过（420 用例）
  - Web `npm run lint` 0 error 0 warning
  - Web `npm test` 21 个文件、69 个用例全通过
  - Web `npm run build` 成功；产物体积如下记录
  - Docker Compose 配置检查通过
  - `git diff --check` 通过

### 假设
- 主题 seed color `#1A53A8` 是与同济 ACM 蓝接近的深蓝；Round 3 重写顶栏时如果设计上需要更接近橙金品牌色，可以再调整 palette。
- 本轮还没有任何业务组件使用 MUI；现有所有页面继续走旧 `styles.css`。

### 备注
- bundle 体积对比：
  - 之前：`dist/assets/index-*.js 531.16 kB │ gzip 145.60 kB`
  - 现在：`dist/assets/index-*.js 625.53 kB │ gzip 178.37 kB`
  - 净增：+94.37 kB / +32.77 kB gzipped
- 1 个 `vite build` 体积告警（500 kB）属于既有警告，本轮未新增构建失败。
- `@fontsource/roboto-flex` 是 variable font，只导出 `400.css`（实际覆盖 100~1000 字重）；不需要分别导入 500/600/700。

## 2026-04-29 11:35 - Evaluate Material 3 React adoption plan

### 完成内容
- 新增 `docs/Material3前端落地方案评估.md`，记录 Web 前端 M3 重写的库选型、新依赖范围、bundle/测试影响面和后续轮次顺序。
- 在 `TASKS.md` 末尾新增 P5 - 前端 Material 3 重写章节，拆出 10 条单轮可验证子任务（含本轮）。
- 将 P5 第一条"评估并确认 Material 3 React 落地方案"标记为已完成。

### 根因
- 用户明确提出"前端实在太丑陋，重新设计前端并重写"，并指定使用 Material 3 设计体系。
- 当前前端仅靠 1700+ 行原生 `styles.css` 维持视觉，存在两套相互冲突的 token（早期橙金 hero + 后期灰白 dashboard），既无设计系统也无组件库；同时交互层面也存在多处不合理（首页是入口页而非任务驱动、成员端 4 段拆分、管理员任务详情仍依赖跨页跳转、缺少 Snackbar/ConfirmDialog 等统一反馈）。
- 按 `AGENTS.md` 要求，整体重写属于大块架构变更，必须先拆分到 `TASKS.md` 再单轮推进，本轮负责拆分与方案确认。

### 关键改动点
- 新增评估文档：
  - `docs/Material3前端落地方案评估.md`
- 任务拆分：
  - `TASKS.md` 新增 `## P5 - 前端 Material 3 重写`，10 条子任务
- 同步任务状态：
  - 第一条子任务标记为 `[x]`

### 风险与影响面
- 本轮只新增评估文档和任务拆分，不安装任何依赖，不改动业务代码、接口语义、数据库结构或测试逻辑。
- 后续轮次会引入 `@mui/material`、`@emotion/*`、`@mui/icons-material`、`@fontsource/roboto-flex` 等新依赖；对 bundle 体积、测试 polyfill 和现有 `styles.css` 的影响在评估文档中已说明。
- 拒绝引入 sixui、Actify、material-web、`notistack`、`react-hook-form` 的理由记录在评估文档中。

### 修改文件
- `docs/Material3前端落地方案评估.md`
- `TASKS.md`
- `WORKLOG.md`

### 验证结果
- 本轮仅新增 Markdown 文档与任务拆分；将在本轮 commit 前运行 `./scripts/verify.sh` 确认 Python/Web/Compose 检查未受影响。

### 假设
- 选择 MUI v7 而不是 sixui 的核心理由是 MUI 的生态、文档、TypeScript 类型、DataGrid/DatePicker/Snackbar/Dialog 等成熟组件可以直接替换当前自造的 `dashboard.tsx`，从而显著减小 `styles.css` 体积。
- 假设后续轮次允许保留 `styles.css` 直到全部页面迁移完成；本轮不删除任何现有样式。

### 备注
- 后续轮次顺序固定为 1→10，每轮独立验证；前后存在依赖（例如 Round 2 需在 Round 3 之前完成）。

## 2026-04-29 05:49 - Evaluate automatic missing-material reminder messaging

### 完成内容
- 新增 `docs/自动生成成员补材料消息评估.md`，明确“自动生成成员补材料消息”不进入第一阶段实现范围，而是保留为后续阶段增强项。
- 将 `TASKS.md` 中“评估自动生成成员补材料消息”标记为已完成。

### 根因
- 需求文档只把“自动生成成员补材料消息”列为 Could have，而 FR-009 的第一阶段硬要求仍是“管理员可手动提醒成员补材料”和“管理员可查看自动提醒记录”，不是“系统必须真实自动向成员发出通知”。
- 当前仓库虽然已经具备两块相关能力，但都还没形成通知闭环：
  - `src/trms_backend/domain/automatic_reminders.py` 只会基于当前任务快照生成 `pending` 的自动提醒任务记录；
  - `src/trms_backend/domain/material_reminders.py` 只会记录管理员手动填写的补材料提醒文本。
- 仓库内当前不存在统一通知模块、消息模板渲染器、出站发送队列、送达状态模型或失败重试链路；Web、Telegram、邮件和 CLI 也都还没有可审计的主动通知出站能力。
- 在 `AC-018 审计记录` 仍未完成的前提下，如果现在直接加入自动消息外发，会把“谁触发、发给谁、发了什么、是否送达”的关键追溯链路留空。

### 关键改动点
- 新增评估文档：
  - `docs/自动生成成员补材料消息评估.md`
- 同步任务状态：
  - `TASKS.md`

### 风险与影响面
- 本轮只新增评估文档和任务记录，不改动任何业务代码、接口语义、数据库结构或测试逻辑。
- 当前结论是“后续阶段再做”，因此不会提升成员被动收到提醒的及时性；但它避免了把通知模板、渠道绑定、审计和失败重试这些尚未收口的复杂度，直接混入第一阶段主链路。

### 修改文件
- `docs/自动生成成员补材料消息评估.md`
- `TASKS.md`
- `WORKLOG.md`

### 验证结果
- 已通过：
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic `upgrade -> downgrade -> upgrade` 验证通过
    - `pytest` 420 个用例通过
    - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过
    - Docker Compose 配置检查通过
    - `git diff --check` 通过

### 假设
- 本轮将“自动生成成员补材料消息”保守解释为“系统根据缺失材料快照自动生成可外发的提醒内容，并通过某个渠道主动发送给成员”，不把成员在 Web/CLI 主动查询到的缺失材料列表混同为该能力。
- 本轮按当前代码状态保守判断：如果后续真的要做，应该先建立通知域模型和审计链路，再评估 Web 站内提醒、邮件或 Telegram 出站；不直接复用现有入站渠道实现旁路发送。

### 备注
- `pytest` 期间仍有 3 条既有 `DeprecationWarning`，来源于导出测试中的旧 `HTTP_422_UNPROCESSABLE_ENTITY` 常量。
- Web 测试期间仍打印 Node `--localstorage-file` 既有警告。
- `vite build` 仍提示单个 chunk 超过 500 kB，这是仓库既有体积告警，本轮未新增构建失败。

## 2026-04-29 05:32 - Evaluate CLI offline staging and sync

### 完成内容
- 新增 `docs/CLI离线暂存后同步评估.md`，明确“CLI 离线暂存后同步”不进入第一阶段实现范围，而是保留为后续阶段增强项。
- 将 `TASKS.md` 中“评估 CLI 离线暂存后同步”标记为已完成。

### 根因
- 需求文档只把“CLI 离线暂存后同步”列为 Could have，且 Q-011 仍是未决问题，不是第一阶段 Must / Should 主链路。
- 当前 CLI 代码仍是显式在线模型：`src/trms_cli/token_store.py` 只保存本地会话，`src/trms_cli/cli.py` 的 `submit` / `tasks` / `status` / `missing-materials` / `confirm-expense` 都依赖实时访问后端 API，没有本地离线队列或同步状态机。
- 一旦引入离线暂存，就必须同时处理两类当前仓库尚未建立的边界：
  - 数据安全：本地是否复制敏感材料副本、暂存元数据如何保护、同步成功后如何清理、是否扩大 token 泄漏面；
  - 同步冲突：任务截止或关闭、成员身份变化、文件内容变化、重复材料、批量部分成功和重试结果收敛。
- 这些复杂度明显超出“当前最小可验证任务”的合理范围，也不应在第一阶段优先于鉴权、审计和生产边界任务实现。

### 关键改动点
- 新增评估文档：
  - `docs/CLI离线暂存后同步评估.md`
- 同步任务状态：
  - `TASKS.md`

### 风险与影响面
- 本轮只新增评估文档和任务记录，不改动任何业务代码、接口语义、数据库结构或测试逻辑。
- 当前结论是“后续阶段再做”，因此不会改善弱网场景下的 CLI 体验；但它避免了在第一阶段把本地敏感材料缓存、本地队列恢复和同步冲突处理混入现有在线提交主路径。

### 修改文件
- `docs/CLI离线暂存后同步评估.md`
- `TASKS.md`
- `WORKLOG.md`

### 验证结果
- 已通过：
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic `upgrade -> downgrade -> upgrade` 验证通过
    - `pytest` 418 个用例通过
    - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过
    - Docker Compose 配置检查通过
    - `git diff --check` 通过

### 假设
- 本轮将“CLI 离线暂存后同步”保守解释为：成员在离线时先把材料及提交元数据存入本地待同步队列，联网后再统一发往后端；不把“shell 重试上传命令”或“操作系统断网后自动重发”混同为该能力。
- 当前保守判断：如果后续真的要做，应该先单独设计本地队列和同步冲突模型，而不是直接给现有 `submit` 命令补一个隐式缓存开关。

### 备注
- `pytest` 期间仍有 3 条既有 `DeprecationWarning`，来源于导出测试中的旧 `HTTP_422_UNPROCESSABLE_ENTITY` 常量。
- Web 测试期间仍打印 Node `--localstorage-file` 既有警告。
- `vite build` 仍提示单个 chunk 超过 500 kB，这是仓库既有体积告警，本轮未新增构建失败。

## 2026-04-29 05:27 - Evaluate common competition templates

### 完成内容
- 新增 `docs/常见比赛模板评估.md`，明确“常见比赛模板”不进入第一阶段，而是保留为后续阶段增强项。
- 将 `TASKS.md` 中“评估常见比赛模板”标记为已完成。

### 根因
- 需求文档只把“常见比赛模板”列为 Could have，架构文档也已把“历史比赛模板和成员复用”归入后续阶段，不属于第一阶段主链路阻塞能力。
- 当前任务创建链路只有显式字段录入：后端 `TaskCreateInput` 和前端 `admin-task-create` 页面都没有模板来源、模板版本或字段覆盖语义。
- 如果现在直接引入模板，就必须同时回答模板与全局抬头/税号默认值、历史成员复用、当前登录管理员责任边界之间的合并规则，会污染现有最小创建闭环。

### 关键改动点
- 新增评估文档：
  - `docs/常见比赛模板评估.md`
- 同步任务状态：
  - `TASKS.md`

### 风险与影响面
- 本轮只新增评估文档和任务记录，不改动任何业务代码、接口语义、数据库结构或测试逻辑。
- 当前结论是“后续阶段再做”，因此不会提升当前管理员创建任务的录入效率；但它避免了在第一阶段把模板默认值、全局配置和成员复用三套来源混进同一条创建路径。

### 修改文件
- `docs/常见比赛模板评估.md`
- `TASKS.md`
- `WORKLOG.md`

### 验证结果
- 已通过：
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic `upgrade -> downgrade -> upgrade` 验证通过
    - `pytest` 418 个用例通过
    - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过
    - Docker Compose 配置检查通过
    - `git diff --check` 通过

### 假设
- 本轮将“常见比赛模板”解释为“创建任务时的一次性预填模板”，而不是新建一套会持续回写任务或自动带出成员名单的主数据系统。
- 本轮按当前代码状态保守判断：模板若后续落地，应只覆盖稳定默认值，不应与 `member_ids`、`administrator_id`、具体比赛日期和全局抬头税号共用同一来源语义。

### 备注
- `pytest` 期间仍有 3 条既有 `DeprecationWarning`，来源于导出测试中的旧 `HTTP_422_UNPROCESSABLE_ENTITY` 常量。
- Web 测试期间仍打印 Node `--localstorage-file` 既有警告。
- `vite build` 仍提示单个 chunk 超过 500 kB，这是仓库既有体积告警，本轮未新增构建失败。

## 2026-04-29 05:31 - Evaluate historical member reuse

### 完成内容
- 新增 `docs/历史成员信息复用评估.md`，明确“历史成员信息复用”不进入第一阶段，而是保留为后续阶段增强项。
- 将 `TASKS.md` 中“评估历史成员信息复用”标记为已完成。

### 根因
- 当前仓库只有任务内 `member_ids` 列表和账号体系里的 `member_code` 绑定，没有稳定的“历史成员主数据”模型。
- 若现在把历史成员复用直接拉进第一阶段，会同时扩大任务创建页、任务成员管理接口、账号绑定语义和身份去重边界，超出“当前最小可验证任务”的合理范围。
- 架构设计文档 V0.1 第 13.3 节也已经把“历史比赛模板和成员复用”列为后续阶段能力，与当前评估结论一致。

### 关键改动点
- 新增评估文档：
  - `docs/历史成员信息复用评估.md`
- 同步任务状态：
  - `TASKS.md`

### 风险与影响面
- 本轮只新增评估文档和任务记录，不改动任何业务代码、接口语义、数据库结构或测试逻辑。
- 当前结论是“后续阶段再做”，因此不会提升当前管理员创建任务的录入效率；但它避免了在第一阶段主链路里混入成员主数据、模板复用和身份去重的额外复杂度。

### 修改文件
- `docs/历史成员信息复用评估.md`
- `TASKS.md`
- `WORKLOG.md`

### 验证结果
- 已通过：
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic `upgrade -> downgrade -> upgrade` 验证通过
    - `pytest` 418 个用例通过
    - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过
    - Docker Compose 配置检查通过
    - `git diff --check` 通过

### 假设
- 本轮将“历史成员信息复用”解释为“管理员在新建任务时复用历史成员名单或成员档案”，而不是扩展现有成员登录或渠道绑定功能。
- 本轮按当前仓库状态保守判断：只有先定义成员主数据边界，后续才适合继续做复用能力。

### 备注
- `pytest` 期间仍有 3 条既有 `DeprecationWarning`，来源于导出测试中的旧 `HTTP_422_UNPROCESSABLE_ENTITY` 常量。
- Web 测试期间仍打印 Node `--localstorage-file` 既有警告。
- `vite build` 仍提示单个 chunk 超过 500 kB，这是仓库既有体积告警，本轮未新增构建失败。

## 2026-04-29 05:19 - Update README first-phase run instructions

### 完成内容
- 更新 `README.md`，补齐面向当前第一阶段代码状态的运行说明：
  - 新增“第一阶段本地运行闭环”，明确 `.env` 准备、依赖安装、Alembic 迁移、后端启动、独立 worker 启动、Web 前端联调和统一验证入口；
  - 新增“CLI 当前状态”，明确现有命令集合、当前只能通过 `uv run python -m trms_cli.cli` 调用、`login` 仅是本地 token 会话保存占位而非完整登录闭环；
  - 新增“当前未实现或未联通的外部依赖”，明确 Telegram、格式化邮件、LLM Provider、Browser Use / 财务系统自动录入和 XLSX 导出的当前边界。
- 将 `TASKS.md` 中“更新 README 的第一阶段运行说明”标记为已完成。

### 根因
- 现有 `README.md` 已积累大量配置和部署边界，但缺少一个面向“当前第一阶段仓库到底怎么跑、CLI 现在处于什么状态、哪些外部能力还没接通”的最小运行说明。
- 这会导致阅读者容易把零散配置项误解为“已有完整运行闭环”，尤其是：
  - 会误以为仓库已经提供可直接执行的 `trms-cli` 命令；
  - 会误以为 Telegram、邮件、LLM 和财务系统自动录入已经在 README 层面可直接联通；
  - 会忽略 `./scripts/verify.sh` 才是仓库要求的统一验证入口。

### 关键改动点
- 运行说明文档收口：
  - `README.md`
- 任务状态同步：
  - `TASKS.md`

### 风险与影响面
- 本轮只修改文档和任务记录，不改动任何生产业务逻辑、测试逻辑或运行配置默认值。
- 风险主要在于 README 描述是否与仓库当前实现一致；本轮已按代码现状保守表述，不把占位能力写成已完成外部集成。

### 修改文件
- `README.md`
- `TASKS.md`
- `WORKLOG.md`

### 验证结果
- 已通过：
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic `upgrade -> downgrade -> upgrade` 验证通过
    - `pytest` 418 个用例通过
    - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过
    - Docker Compose 配置检查通过
    - `git diff --check` 通过

### 备注
- `pytest` 期间仍有 3 条既有 `DeprecationWarning`，来源于导出测试中的旧 `HTTP_422_UNPROCESSABLE_ENTITY` 常量。
- Web 测试期间仍打印 Node `--localstorage-file` 既有警告。
- `vite build` 仍提示单个 chunk 超过 500 kB，这是仓库既有体积告警，本轮未新增构建失败。

### 假设
- 本轮将“CLI 占位”保守解释为：README 需要准确描述当前 CLI 只是已有命令和本地 token 会话边界，不额外发明不存在的 CLI 安装、签发或刷新流程。
- 本轮将“当前未实现外部依赖”聚焦到 README 最容易被误读为已联通的能力：Telegram、格式化邮件、LLM Provider、Browser Use / 财务系统自动录入和 XLSX 导出；不在同一轮里扩散成新的需求评审文档。

## 2026-04-29 05:10 - Execute pre-release main-flow E2E drill

### 完成内容
- 将 `tests/test_main_flow_e2e.py` 从“状态门禁骨架”扩展为仓库内可重复执行的主流程演练：
  - 管理员创建任务并发布；
  - 成员上传真实文本 PDF 发票材料；
  - 使用 fake LLM 配合 `RecognitionAsyncJobProcessor` 执行真实识别 worker；
  - 管理员录入发票并校验抬头、税号和重复发票边界；
  - 成员提交分摊并确认个人费用；
  - 管理员推进任务进入 `reviewing` 和 `ready_to_export`；
  - 创建 `reimbursement_summary` 导出任务，并通过 `ExportAsyncJobProcessor` 真实生成持久化 CSV 产物，再经下载接口校验内容。
- 将 `TASKS.md` 中“执行上线前主流程 E2E 演练并记录风险”标记为已完成。

### 根因
- 现有 `tests/test_main_flow_e2e.py` 虽然已经覆盖了任务创建、上传、录票、分摊、确认和导出门禁放行，但识别阶段依赖管理员手动改 `recognition_task` 状态，且流程停在 `exports/capabilities`，没有真正演练异步识别 worker、异步导出 worker 和导出产物下载。
- 当前任务要求的是“上线前主流程 E2E 演练并记录风险”，如果继续停留在骨架层，就会把“导出真的能跑完”和“fake LLM 配置下的识别链路真的能走通”留在未验证状态。

### 关键改动点
- 扩展主流程 E2E 演练测试：
  - `tests/test_main_flow_e2e.py`
- 更新任务与日志：
  - `TASKS.md`
  - `WORKLOG.md`

### 风险与影响面
- 本轮未修改任何生产业务逻辑，只增强主流程演练测试与任务记录；若后续识别 worker、导出 worker、任务状态流转、确认门禁或导出下载回归，这条测试会优先暴露问题。
- 本轮把“上线前主流程 E2E 演练”保守定义为“仓库内真实 API + 真实异步处理器 + fake LLM + 本地文件存储”的最小可重复闭环，不把外部渠道和真实外部服务伪装成已验证。

### 修改文件
- `tests/test_main_flow_e2e.py`
- `TASKS.md`
- `WORKLOG.md`

### 验证结果
- 已通过：
  - `uv run pytest tests/test_main_flow_e2e.py`
    - 1 个测试通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic `upgrade -> downgrade -> upgrade` 验证通过
    - `pytest` 418 个用例通过
    - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过
    - Docker Compose 配置检查通过
    - `git diff --check` 通过

### 备注
- `pytest` 期间仍有 3 条既有 `DeprecationWarning`，来源于导出测试中的旧 `HTTP_422_UNPROCESSABLE_ENTITY` 常量。
- Web 测试期间仍打印 Node `--localstorage-file` 既有警告。
- `vite build` 仍提示单个 chunk 超过 500 kB，这是仓库既有体积告警，本轮未新增构建失败。

### 假设
- 本轮按任务定义允许的边界，使用 fake LLM 作为上线前主流程演练中的识别提供方替身；目标是验证“系统主链路与异步执行机制”而不是宣称真实外部 Provider 已联通。
- 本轮优先覆盖文本 PDF 发票主路径，不额外把扫描 PDF、图片识别或多材料合并导出塞进同一条主流程演练，避免把任务范围无边界扩大。

### 未覆盖风险
- Telegram Bot、格式化邮件入站和真实渠道身份绑定流程没有包含在本轮演练内；当前只证明统一主链路可被这些渠道复用，不代表外部渠道已经联通。
- 真实 OpenAI 兼容 LLM Provider、真实扫描 PDF / 图片识别输入、真实 OCR / VLM 失败恢复没有在本轮验证；fake LLM 只能证明内部编排正确，不能替代外部联调。
- 本轮使用本地文件存储与进程内测试客户端，没有覆盖 S3/MinIO 权限策略、独立 worker 进程、容器网络或跨进程队列配置错误。
- Browser Use / 财务系统自动录入仍然明确属于第一阶段范围外能力，本轮未演练，也不应被表述为已具备。

## 2026-04-29 05:03 - Add pre-release security regression coverage

### 完成内容
- 新增 `tests/test_security_regressions.py`，把上线前需要反复确认的安全边界收敛成单独的 smoke regression 入口。
- 新增回归覆盖以下 5 类边界：
  - 成员越权：成员不能查看他人材料原文，也不能进入管理员复核摘要路径；
  - 导出下载：只有负责该任务的管理员可以下载导出产物，相关成员和无关管理员都会被拒绝；
  - 日志脱敏：运行日志中的 `authorization`、`storage_key`、本地路径、带签名下载 URL 会被脱敏，审计日志中的 `raw_response` 和 bearer 信息不会裸写；
  - CORS 配置：生产环境缺少 `TRMS_CORS_ALLOWED_ORIGINS` 会显式报错，显式配置的 Origin 会真实下发到应用响应头；
  - 生产注册策略：生产环境拒绝管理员自注册，但仍允许普通成员自注册。
- 将 `TASKS.md` 中“增加上线前安全回归验证”标记为已完成。

### 根因
- 这些安全边界此前大多已经存在单点测试，但分散在权限、导出、运行配置、认证和日志等不同文件里，没有一组可直接代表“上线前安全回归”的集中入口。
- 当前任务要求的是“增加上线前安全回归验证”，重点是把关键安全假设收口成稳定、可重复执行的一组验证，而不是继续改业务逻辑或声称外部依赖也已自动化覆盖。

### 关键改动点
- 新增集中式安全回归测试：
  - `tests/test_security_regressions.py`
- 更新任务与日志：
  - `TASKS.md`
  - `WORKLOG.md`

### 风险与影响面
- 本轮未修改任何生产业务实现，只新增测试；如果后续权限判断、导出下载授权、日志脱敏、CORS 约束或生产注册策略回归，这组测试会先暴露问题。
- 本轮没有把 Telegram、邮件、真实 OCR、真实外部 LLM、对象存储权限策略或人工上线检查项伪装成自动化已覆盖；这些仍属于后续主流程演练或外部依赖联调范围。

### 修改文件
- `tests/test_security_regressions.py`
- `TASKS.md`
- `WORKLOG.md`

### 验证结果
- 已通过：
  - `uv run pytest tests/test_security_regressions.py`
    - 5 个测试通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic `upgrade -> downgrade -> upgrade` 验证通过
    - `pytest` 418 个用例通过
    - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过
    - Docker Compose 配置检查通过
    - `git diff --check` 通过

### 备注
- `pytest` 期间仍有 3 条既有 `DeprecationWarning`，来源于导出测试中的旧 `HTTP_422_UNPROCESSABLE_ENTITY` 常量。
- Web 测试期间仍打印 Node `--localstorage-file` 既有警告。
- `vite build` 仍提示单个 chunk 超过 500 kB，这是仓库既有体积告警，本轮未新增构建失败。

### 假设
- 本轮默认“上线前安全回归验证”应以仓库内可自动执行的关键安全边界 smoke tests 为完成标准，而不是要求在同一轮内接入真实外部渠道、真实生产凭据或人工上线演练步骤。

## 2026-04-29 04:53 - Add backend main-flow E2E scaffold

### 完成内容
- 新增 `tests/test_main_flow_e2e.py`，用单个后端集成测试串起当前第一阶段主流程骨架：
  - 管理员创建任务并开放提交通道；
  - 成员通过 bearer 身份上传发票材料；
  - 用 fake recognition result 驱动识别任务成功，不接真实 AI；
  - 管理员录入发票并断言抬头、税号、重复发票等核心校验结果；
  - 成员提交金额分摊并确认个人费用；
  - 管理员查看复核摘要、推动任务进入 `reviewing` / `ready_to_export`，并验证导出门禁由阻塞变为放行。
- 将 `TASKS.md` 中“建立主流程 E2E 测试骨架”标记为已完成。

### 根因
- 仓库此前只有 `web/src/app/main-flow-e2e-placeholder.test.tsx` 这一条前端路由级占位测试，能覆盖页面协作，但不能证明后端真实 API 主链路已经可从“创建任务”走到“导出门禁放行”。
- 当前 P3 首个未完成任务要求的是可纳入 `./scripts/verify.sh` 的主流程 E2E 骨架，因此本轮补的是后端集成测试闭环，而不是继续扩展前端 mock 场景或引入真实外部依赖。

### 关键改动点
- 新增后端主流程 E2E 骨架测试：
  - `tests/test_main_flow_e2e.py`
- 更新任务与日志：
  - `TASKS.md`
  - `WORKLOG.md`

### 风险与影响面
- 本轮未修改生产业务实现，只新增测试；如果后续任务状态流转、bearer 身份收口、识别任务结果落库、费用确认或导出门禁回归，这条主流程测试会首先暴露问题。
- 本测试把“E2E 骨架”保守定义为仓库内可稳定运行的后端 API 集成链路，不引入真实 AI、Telegram、邮件或对象存储；真实外部依赖联调仍应留给后续“上线前主流程 E2E 演练并记录风险”任务。

### 修改文件
- `tests/test_main_flow_e2e.py`
- `TASKS.md`
- `WORKLOG.md`

### 验证结果
- 已通过：
  - `uv run pytest tests/test_main_flow_e2e.py`
    - 1 个测试通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic `upgrade -> downgrade -> upgrade` 验证通过
    - `pytest` 413 个用例通过
    - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过
    - Docker Compose 配置检查通过
    - `git diff --check` 通过

### 备注
- `pytest` 期间仍有 3 条既有 `DeprecationWarning`，来源于导出测试中的旧 `HTTP_422_UNPROCESSABLE_ENTITY` 常量。
- Web 测试期间仍打印 Node `--localstorage-file` 既有警告。
- `vite build` 仍提示单个 chunk 超过 500 kB，这是仓库既有体积告警，本轮未新增构建失败。

### 假设
- 本轮默认“建立主流程 E2E 测试骨架”应在既有前端占位测试之外，再补一条后端真实 API 主链路；否则该任务与已完成的“建立前端主流程 E2E 占位”会出现职责重叠。

## 2026-04-29 04:45 - Add CLI argument parsing coverage

### 完成内容
- 新增 `tests/test_cli_argument_parsing.py`，集中覆盖 CLI 参数层回归，不再只依赖各命令执行路径的零散断言。
- 已补齐以下参数解析场景：
  - `login`、`tasks`、`submit`、`status`、`missing-materials`、`split`、`confirm-expense` 的成功解析路径；
  - `submit`、`status`、`missing-materials`、`split` 等命令的必填参数缺失时，`argparse` 会直接拒绝；
  - `confirm-expense` 在“仅查询”与“提交确认”两种模式下的参数组合校验，包括缺少 `split_version`、缺少 `status`、`disputed` 缺少异议原因，以及 `confirmed` 错带异议原因等失败路径。
- 既有 CLI 测试继续覆盖本轮任务要求的另外两部分：
  - `tests/test_cli_login.py`、`tests/test_cli_tasks.py`、`tests/test_cli_status.py`、`tests/test_cli_missing_materials.py`、`tests/test_cli_split.py`、`tests/test_cli_confirm_expense.py` 已覆盖各命令 `--json` 输出；
  - `tests/test_cli_submit.py` 已覆盖本地文件不存在、不支持类型、超出大小限制等本地预检查失败路径。

### 根因
- 现有 CLI 测试主要围绕命令执行结果、HTTP 载荷和错误输出展开，但缺少一组直接锁定 `argparse` 约束和 `confirm-expense` 参数组合语义的测试。
- 这导致一旦命令名称、必填参数或“查询/提交双模式”边界被改坏，回归可能要到更晚的执行路径才暴露，定位成本偏高。

### 关键改动点
- 新增 CLI 参数解析测试：
  - `tests/test_cli_argument_parsing.py`
- 更新任务与日志：
  - `TASKS.md`
  - `WORKLOG.md`

### 风险与影响面
- 本轮未修改任何生产代码，只增强 CLI 测试；如果后续有人调整命令参数、删除 `--json` 开关或放松 `confirm-expense` 的参数校验，这组测试会先暴露问题。
- 新增测试把 `TASKS.md` 中旧称呼 `list-tasks` 按当前实现映射为 `tasks` 命令处理；这是基于仓库现状的保守解释，未引入别名或兼容层。

### 修改文件
- `tests/test_cli_argument_parsing.py`
- `TASKS.md`
- `WORKLOG.md`

### 验证结果
- 已通过：
  - `uv run pytest tests/test_cli_argument_parsing.py tests/test_cli_login.py tests/test_cli_tasks.py tests/test_cli_submit.py tests/test_cli_status.py tests/test_cli_missing_materials.py tests/test_cli_split.py tests/test_cli_confirm_expense.py`
    - 49 个测试通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic `upgrade -> downgrade -> upgrade` 验证通过
    - `pytest` 412 个用例通过
    - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过
    - Docker Compose 配置检查通过
    - `git diff --check` 通过

### 备注
- `pytest` 期间仍有 3 条既有 `DeprecationWarning`，来源于导出测试中的旧 `HTTP_422_UNPROCESSABLE_ENTITY` 常量。
- Web 测试期间仍打印 Node `--localstorage-file` 既有警告。
- `vite build` 仍提示单个 chunk 超过 500 kB，这是仓库既有体积告警，本轮未新增构建失败。

### 假设
- 本轮默认 `TASKS.md` 中的 `list-tasks` 指代当前仓库已实现的 `tasks` CLI 子命令，而不是一个尚未存在的独立别名。

## 2026-04-29 04:39 - Add export job integration coverage

### 完成内容
- 在既有 `tests/test_export_async_jobs.py` 基础上补强导出异步处理器集成断言，直接覆盖当前任务要求的导出任务创建、真实状态变化和失败原因持久化。
- 已补齐以下集成场景：
  - 导出任务创建后先以 `pending` 状态落库，且初始无产物、无失败原因；
  - 异步处理器真实执行后，导出任务会从 `pending` 进入终态，并在成功路径上生成可下载产物；
  - 合并 PDF 遇到损坏 PDF 时，失败原因会显式带出具体 `material_id`，不会只给模糊错误；
  - 失败终态会写入 `fail_task_export_job` 审计日志，并保留失败原因，不伪装成成功。

### 根因
- 现有仓库虽然已经有 `tests/test_exports_api.py` 和 `tests/test_export_async_jobs.py`，但“损坏 PDF 后异步导出任务失败时是否把具体材料编号和失败审计一起落库”这一点还没有被明确锁住。
- 当前首个未完成任务要求的是“导出任务集成测试”，重点不在单个导出函数本身，而在“创建任务 -> 异步处理 -> 成功/失败终态 -> 原因可追溯”这条主链路，因此本轮补的是异步处理器级别的集成断言。

### 关键改动点
- 增强导出异步集成测试：
  - `tests/test_export_async_jobs.py`
- 更新任务与日志：
  - `TASKS.md`
  - `WORKLOG.md`

### 风险与影响面
- 本轮未修改任何生产业务逻辑，只增强测试；如果后续导出任务状态流转、失败原因拼装或审计记录回归，这组测试会先暴露问题。
- 当前损坏 PDF 断言仍按“错误消息必须包含 `material_id` 和 `is unreadable:` 前缀”校验，没有把底层 PDF 库的完整报错文本写死，避免因为第三方库错误细节轻微变化导致无意义脆弱测试。
- 本轮仍不扩展到真实财务可提交材料正确性验证，符合当前任务“只补导出任务集成测试，不要求真实财务可用材料”的边界。

### 修改文件
- `tests/test_export_async_jobs.py`
- `TASKS.md`
- `WORKLOG.md`

### 验证结果
- 已通过：
  - `uv run pytest tests/test_export_async_jobs.py`
    - 5 个测试通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic `upgrade -> downgrade -> upgrade` 验证通过
    - `pytest` 393 个用例通过
    - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过
    - Docker Compose 配置检查通过
    - `git diff --check` 通过
- 备注：
  - `pytest` 期间仍有 3 条既有 `DeprecationWarning`，来源于导出测试中的旧 `HTTP_422_UNPROCESSABLE_ENTITY` 常量；
  - Web 测试期间仍打印 Node `--localstorage-file` 既有警告；
  - `vite build` 仍提示单个 chunk 超过 500 kB，这是仓库既有体积告警，本轮未新增构建失败。

### 假设
- 本轮默认“导出任务状态变化”以真实异步处理器驱动的 `pending -> succeeded/failed` 主链路为准；已有 `tests/test_exports_api.py` 中的状态接口覆盖继续负责补足管理接口层的手工状态查看与参数持久化断言。

## 2026-04-29 04:37 - Add material upload integration coverage

### 完成内容
- 新增上传链路集成测试文件 `tests/test_material_upload_integration.py`，集中覆盖本轮任务要求的上传主链路断言。
- 已补齐以下集成场景：
  - `web`、`cli`、可信 `telegram`、可信 `email` 四类已归属上传都会落到同一保存/落库/识别占位流程；
  - 已验证文件内容落盘、本地存储 key、`sha256` hash 持久化，以及识别任务占位创建；
  - 已验证跨渠道重复检测：同一任务内 `web` 首次上传后，`telegram` 再上传相同内容会正确标记 `duplicate_of`；
  - 已验证批量上传部分成功：合法 PDF 成功入库，非法文本附件失败并返回明确错误，且失败文件不会伪造为已保存。

### 根因
- 现有仓库虽然已有 `test_materials_api.py`、`test_email_materials_api.py`、`test_telegram_materials_api.py` 和 `test_material_storage.py` 等零散测试，但断言分散在 API、渠道和底层存储文件中，缺少一组直接对照 `TASKS.md` Done when 的“材料上传集成测试”。
- 当前首个未完成任务明确要求同时覆盖文件保存、hash、重复检测、批量部分成功和跨渠道统一流程，因此本轮补的是测试闭环，而不是继续改业务实现。

### 关键改动点
- 新增上传集成测试：
  - `tests/test_material_upload_integration.py`
- 更新任务与日志：
  - `TASKS.md`
  - `WORKLOG.md`

### 风险与影响面
- 本轮未修改任何生产业务逻辑，只新增测试；如果后续上传链路、重复检测策略或渠道归属边界回归，这组测试会先暴露问题。
- 集成测试仍基于本地 `LocalMaterialFileStorage`，符合“不要依赖外部对象存储”的当前任务边界；S3 兼容存储契约仍由既有 `tests/test_material_storage.py` 负责，不在本轮扩大到外部依赖集成。
- `telegram` 和 `email` 场景本轮只覆盖“可信入站并直接归属”的统一主链路，未把未绑定/待归属分支重新复制进该测试文件，因为那部分已有专门渠道测试覆盖。

### 修改文件
- `tests/test_material_upload_integration.py`
- `TASKS.md`
- `WORKLOG.md`

### 验证结果
- 已通过：
  - `uv run pytest tests/test_material_upload_integration.py`
    - 6 个测试通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic `upgrade -> downgrade -> upgrade` 验证通过
    - `pytest` 393 个用例通过
    - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过
    - Docker Compose 配置检查通过
    - `git diff --check` 通过
- 备注：
  - `pytest` 期间仍有 3 条既有 `DeprecationWarning`，来源于导出测试中的旧 `HTTP_422_UNPROCESSABLE_ENTITY` 常量；
  - Web 测试期间仍打印 Node `--localstorage-file` 既有警告；
  - `vite build` 仍提示单个 chunk 超过 500 kB，这是仓库既有体积告警，本轮未新增构建失败。

### 假设
- 本轮默认“不同渠道进入统一流程”应覆盖 `web`、`cli`、可信 `telegram`、可信 `email` 四条第一阶段主链路；待归属分支已由既有渠道测试覆盖，因此不在本轮重复铺开。

## 2026-04-29 04:24 - Add rule-layer validation test matrix

### 完成内容
- 新增领域层规则单测文件 `tests/test_invoice_validation_rules.py`，直接覆盖 `src/trms_backend/domain/invoice_validation.py` 的核心校验函数，不再依赖 API 链路间接断言。
- 已补齐以下规则矩阵：
  - 抬头/税号规则：覆盖通过、失败、待确认；
  - 大额支付记录规则：覆盖支付记录必需规则的通过/失败，以及金额匹配规则的通过、失败、待确认；
  - 附件完整性规则：覆盖比赛通知、航空行程单、航空舱位证明、网约车行程信息等规则的通过/失败，并为支持待确认的规则补齐待确认路径；
  - 比赛范围规则：覆盖时间范围和地点范围的通过、失败、待确认；
  - 重复发票规则：覆盖通过、失败。

### 根因
- 现有校验语义大多只在 `tests/test_invoices_api.py` 等 API 用例里间接验证，断言分散且依赖整条请求链，规则层一旦回归，定位会被接口行为和仓储细节噪声掩盖。
- `TASKS.md` 的当前最小任务要求是补“规则层单元测试覆盖矩阵”，因此本轮不扩散到业务逻辑改造，而是把规则纯函数的状态矩阵直接锁住。

### 关键改动点
- 新增规则层测试：
  - `tests/test_invoice_validation_rules.py`
- 更新任务与日志：
  - `TASKS.md`
  - `WORKLOG.md`

### 风险与影响面
- 本轮未修改任何生产业务逻辑，只新增测试；如果后续规则语义调整，这些测试会先暴露不一致。
- 重复发票规则当前域模型只定义了 `passed/failed`，不存在独立的 `pending` 语义；本轮按现有实现记录为“覆盖全部受支持状态”，未擅自扩展规则行为。
- 比赛通知和航空行程单必需规则当前也只有“通过/失败/不适用”，待确认语义仍由更细粒度的舱位证明、网约车行程、时间范围、地点范围等规则承担。

### 修改文件
- `tests/test_invoice_validation_rules.py`
- `TASKS.md`
- `WORKLOG.md`

### 验证结果
- 已通过：
  - `uv run pytest tests/test_invoice_validation_rules.py`
    - 26 个测试通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic `upgrade -> downgrade -> upgrade` 验证通过
    - `pytest` 382 个用例通过
    - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过
    - Docker Compose 配置检查通过
    - `git diff --check` 通过
- 备注：
  - `pytest` 期间仍有 3 条既有 `DeprecationWarning`，来源于导出测试中的旧 `HTTP_422_UNPROCESSABLE_ENTITY` 常量；
  - Web 测试期间仍打印 Node `--localstorage-file` 既有警告；
  - `vite build` 仍提示单个 chunk 超过 500 kB，这是仓库既有体积告警，本轮未新增构建失败。

### 假设
- 本轮默认“每条规则覆盖通过、失败、待确认路径”应按规则实际支持的状态解释；对于重复发票、比赛通知、航空行程单这类当前不产生 `pending` 的规则，不在本轮擅自改动业务语义去制造待确认态。

## 2026-04-29 04:13 - Support multi-role account binding and switching

### 完成内容
- 将认证模型从“单账号单角色”扩展为“单账号多角色 + 会话激活角色”：
  - 后端用户模型新增 `roles` 集合，登录会话新增 `active_role`；
  - Alembic 新增 `20260429_01` 迁移，把既有 `role` 数据回填到 `roles` 与 `active_role`。
- 增加角色切换闭环：
  - 后端新增 `POST /api/auth/switch-role`，同一 bearer 会话内可切换到账号已绑定角色；
  - `request-context` 和 `me` 返回当前激活角色与可切换角色集合。
- 前端接入多角色工作台切换：
  - 会话存储支持 `availableRoles`；
  - 同账号访问其他已绑定角色工作台时，会自动切换当前激活角色并进入对应页面；
  - 登录页“当前会话”区域补充可切换身份按钮。
- 补齐认证与前端回归测试：
  - 后端测试覆盖多角色登录、切换成功、未绑定角色切换失败、生产环境禁止在角色集合中混入特权角色；
  - 前端测试覆盖已绑定多角色账号进入其他工作台时的自动切换。

### 根因
- 当前实现把 `user.role` 当作账号唯一角色，导致同一人如果既是报销成员又承担管理员或系统管理员职责，只能靠多个账号切换，认证上下文也无法表达“当前激活角色”和“可切换角色集合”。
- 首页和导航此前虽然已经按 `availableRoles` 预留了可见入口过滤逻辑，但后端没有真实角色集合、前端也没有切换会话能力，导致这个边界停留在占位状态。

### 关键改动点
- 后端认证模型、请求身份和仓储：
  - `src/trms_backend/domain/auth.py`
  - `src/trms_backend/api/auth.py`
  - `src/trms_backend/api/request_identity.py`
  - `src/trms_backend/api/request_task_access.py`
  - `src/trms_backend/infrastructure/models.py`
  - `src/trms_backend/infrastructure/repositories.py`
  - `alembic/versions/20260429_01_auth_multi_role_sessions.py`
- 后端回归测试：
  - `tests/test_auth_api.py`
  - `tests/test_request_identity.py`
  - `tests/test_database_migrations.py`
- 前端会话与切换：
  - `web/src/app/auth-store.ts`
  - `web/src/app/auth.tsx`
  - `web/src/lib/api/trms.ts`
  - `web/src/lib/api/types.ts`
  - `web/src/app/App.test.tsx`

### 风险与影响面
- 本轮把“多角色绑定”收口到账号数据模型、登录响应和会话切换，不包含完整的系统管理员账号/角色管理后台；后续若要支持“存量账号追加角色”“撤销角色”等运维流程，应作为独立任务继续做，不要继续挤在本轮里。
- 为避免成员态借同一 `actor_id` 直接走管理员访问边界，本轮把任务管理员可见性收口为“`actor_id` 匹配且当前激活角色为 `admin/system_admin`”；其他业务接口后续若新增类似双重条件，也应沿用相同约束。
- `vite build` 仍有既有单 chunk 超过 500 kB 告警，本轮未新增构建失败。

### 修改文件
- `alembic/versions/20260429_01_auth_multi_role_sessions.py`
- `src/trms_backend/domain/auth.py`
- `src/trms_backend/api/auth.py`
- `src/trms_backend/api/request_identity.py`
- `src/trms_backend/api/request_task_access.py`
- `src/trms_backend/infrastructure/models.py`
- `src/trms_backend/infrastructure/repositories.py`
- `tests/test_auth_api.py`
- `tests/test_request_identity.py`
- `tests/test_database_migrations.py`
- `web/src/app/auth-store.ts`
- `web/src/app/auth.tsx`
- `web/src/lib/api/trms.ts`
- `web/src/lib/api/types.ts`
- `web/src/app/App.test.tsx`
- `TASKS.md`
- `WORKLOG.md`

### 验证结果
- 已通过：
  - `uv run pytest tests/test_auth_api.py tests/test_request_identity.py`
    - 20 个测试通过
  - `cd web && npm test -- --run src/app/App.test.tsx`
    - 1 个测试文件、8 个测试通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic `upgrade -> downgrade -> upgrade` 验证通过
    - `pytest` 356 个用例通过
    - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过
    - Docker Compose 配置检查通过
    - `git diff --check` 通过
- 备注：
  - `pytest` 期间仍有 3 条既有 `DeprecationWarning`，来源于导出测试中的旧 `HTTP_422_UNPROCESSABLE_ENTITY` 常量；
  - Web 测试期间仍打印 Node `--localstorage-file` 既有警告；
  - `vite build` 仍提示单个 chunk 超过 500 kB，这是仓库既有体积告警，本轮未新增构建失败。

### 假设
- 本轮默认同一账号的多角色属于同一真实用户，因此沿用同一个 `actor_id`、`display_name` 和可选 `member_code`，只切换激活角色，不创建多份会话主体信息。
- 本轮默认多角色绑定发生在账号创建/初始化后的数据层和认证层；如果后续产品要求系统管理员在 Web 页面上给存量账号增删角色，应新增独立任务，而不是继续扩大当前改动面。

## 2026-04-29 03:56 - Close the member single-task workflow loop in the workbench

### 完成内容
- 将成员端“上传材料”和“费用确认”主动作收口回单任务发票工作台：
  - 工作台新增当前任务内联上传区，成员可直接选择材料类型、批量上传文件，并在同页看到逐文件成功/失败结果；
  - 工作台新增当前任务费用确认区，成员可直接对分到本人名下的费用提交确认或异议，不再必须跳转到专项确认页。
- 收口工作台内的主流程导航：
  - 顶部“待处理事项”从跳到独立页面改为跳到当前工作台内的上传区、发票详情区和确认区；
  - 每张发票卡片的“下一步动作”也改成工作台内锚点，成员优先留在单任务上下文连续处理。
- 补齐前端回归测试：
  - 更新既有工作台测试，适配同页锚点和新增的确认区；
  - 新增测试覆盖“在工作台内上传材料并刷新当前任务视图”和“在工作台内提交费用确认并刷新状态”。

### 根因
- 之前的成员工作台已经能查看识别字段、材料类型、分摊去向和缺失项，但“上传材料”和“提交确认”仍必须跳到独立页面，主链路最后两步仍然被拆散。
- `docs/UI原型图对照与交互规范补充.md` 对成员端的要求是“单任务闭环”，即用户在一个任务上下文中连续完成上传、查看、补充和确认，而不是自己判断还要切去哪个子页。

### 关键改动点
- 成员工作台补齐上传与确认闭环：
  - `web/src/app/member-invoice-workbench.tsx`
- 成员工作台回归测试：
  - `web/src/app/member-invoice-workbench.test.tsx`

### 风险与影响面
- 原有成员材料上传页和费用确认页仍然保留，作为深链接或专项入口使用；本轮只改变主流程优先级，不删除既有入口。
- 工作台确认区复用了现有后端确认接口和版本失效语义；如果后续产品希望在工作台内继续补入更细的成员提醒或批量确认能力，应作为独立任务处理。
- 前端构建仍有既有的单 chunk 超过 500 kB 告警，本轮未新增构建失败。

### 修改文件
- `web/src/app/member-invoice-workbench.tsx`
- `web/src/app/member-invoice-workbench.test.tsx`
- `TASKS.md`
- `WORKLOG.md`

### 验证结果
- 已通过：
  - `cd web && npm test -- --run src/app/member-invoice-workbench.test.tsx`
    - 1 个测试文件、8 个测试通过
  - `cd web && npm run lint`
  - `cd web && npm run build`
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic `upgrade -> downgrade -> upgrade` 验证通过
    - `pytest` 352 个用例通过
    - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过
    - Docker Compose 配置检查通过
    - `git diff --check` 通过
- 备注：
  - `pytest` 期间仍有 3 条既有 `DeprecationWarning`，来源于导出测试中的旧 `HTTP_422_UNPROCESSABLE_ENTITY` 常量；
  - Web 测试期间仍打印 Node `--localstorage-file` 既有警告；
  - `vite build` 仍提示单个 chunk 超过 500 kB，这是仓库既有体积告警，本轮未新增构建失败。

### 假设
- 本轮默认“成员端主流程闭环”优先级高于“删除所有专项页”，因此保留上传页、材料状态页和费用确认页作为补充入口，但不再让成员依赖它们完成主流程。
- 工作台内上传区默认只处理当前选中任务；若后续产品要求跨任务拖拽上传或批量切换目标任务，应拆成新的独立任务，而不是继续扩大本轮改动范围。

## 2026-04-29 03:38 - Build linked material review list/detail workspace

### 完成内容
- 将管理员复核主界面收口为“材料列表 + 当前材料详情”联动结构：
  - 复核页左侧统一列出当前任务已归档材料，按材料类型、渠道、提交人、关联发票和异常数量帮助管理员快速筛选；
  - 右侧固定展示当前选中材料的详情，不再把“材料状态摘要”和“发票复核摘要”拆成两个互相割裂的长列表。
- 在当前材料详情中集中展示复核所需上下文：
  - 新增原始材料内容预览，支持已归档 PDF 和图片材料的内联预览；
  - 同页展示识别字段、来源、置信度、校验异常、关联发票摘要、当前分摊去向和成员确认状态；
  - 当前材料若已形成主发票，可直接进入“更正金额与字段”或“调整分摊”；若是辅助材料，则直接跳到其关联发票。
- 补齐材料预览接口和测试：
  - 后端新增 `GET /api/materials/{material_id}/content`，要求已登录且满足任务可见性约束；
  - 管理员可预览任务内材料，成员仍不能预览无关成员材料；
  - 前端测试覆盖初始发票详情和切换到辅助材料后的联动展示，后端测试覆盖管理员预览成功和无关成员被拒绝。

### 根因
- `docs/UI原型图对照与交互规范补充.md` 已明确指出：审核类页面应采用“列表 + 详情面板”的审查模式，而当前实现仍把材料列表、发票列表、校验异常和分摊确认拆成多个并列区块。
- 现有管理员要处理一张发票时，往往先在复核总览里看摘要，再跳去发票录入页看识别字段，再跳去分摊页看归属与确认状态；问题不在后端能力缺失，而在复核页没有承接这些上下文。
- 仓库此前也没有材料原件读取接口，导致前端即使想做联动详情，也只能显示文件名和元数据，无法满足“原始票据预览”的任务要求。

### 关键改动点
- 后端材料预览接口：
  - `src/trms_backend/api/materials.py`
  - `src/trms_backend/application/material_submission.py`
- 前端 API 与复核页联动视图：
  - `web/src/lib/api/trms.ts`
  - `web/src/app/admin-review-overview.tsx`
  - `web/src/styles.css`
- 回归测试：
  - `tests/test_materials_api.py`
  - `web/src/app/admin-review-overview.test.tsx`
- 任务与日志：
  - `TASKS.md`
  - `WORKLOG.md`

### 风险与影响面
- 本轮新增的材料内容接口只开放给已归档材料，且继续受任务级权限约束；待归属材料仍只在待归属列表中展示摘要，不在本轮开放原件预览。
- 复核页当前把“查看和决策上下文”集中到同页，但字段补录和分摊编辑仍复用既有独立页面；这轮的目标是消除为看上下文而频繁跳页，不是把所有编辑表单再次复制进复核页。
- 原始材料预览目前只对 PDF 和图片做内联展示；若后续引入更多可上传类型，需要单独评估是否允许浏览器内联预览，而不是默认放开。

### 修改文件
- `src/trms_backend/api/materials.py`
- `src/trms_backend/application/material_submission.py`
- `tests/test_materials_api.py`
- `web/src/lib/api/trms.ts`
- `web/src/app/admin-review-overview.tsx`
- `web/src/app/admin-review-overview.test.tsx`
- `web/src/styles.css`
- `TASKS.md`
- `WORKLOG.md`

### 验证结果
- 已通过：
  - `uv run pytest tests/test_materials_api.py -k 'preview_assigned_material_content or preview_other_members_material_content'`
    - 2 个测试通过
  - `uv run pytest tests/test_materials_api.py tests/test_task_review_summary_api.py`
    - 33 个测试通过
  - `cd web && npm test -- --run src/app/admin-review-overview.test.tsx`
    - 2 个测试通过
  - `cd web && npm run lint`
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic `upgrade -> downgrade -> upgrade` 验证通过
    - `pytest` 352 个用例通过
    - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过
    - Docker Compose 配置检查通过
    - `git diff --check` 通过
- 备注：
  - `pytest` 期间仍有 3 条既有 `DeprecationWarning`，来源于导出测试中的旧 `HTTP_422_UNPROCESSABLE_ENTITY` 常量；
  - Web 测试期间仍打印 Node `--localstorage-file` 既有警告；
  - `vite build` 仍提示单个 chunk 超过 500 kB，这是仓库既有体积告警，本轮未新增构建失败。

### 假设
- 本轮默认“复核主界面需要同页完成的是查看、判断和进入正确处理动作”，因此没有把发票录入表单和分摊编辑表单整块复制到复核页，而是保留既有独立编辑页作为处理入口。
- 辅助材料在当前详情里优先展示其关联发票摘要和跳转动作；若后续产品要求辅助材料也必须直接展示关联发票的完整分摊表单，应作为下一轮独立任务处理，而不是继续在本轮扩散修改。

## 2026-04-29 03:22 - Align admin navigation and task progression with prototype

### 完成内容
- 建立管理员端共享壳层：
  - 新增 `web/src/app/admin-workspace-shell.tsx` 与 `web/src/app/admin-task-stage.ts`；
  - 在管理员首页、任务创建、任务详情、复核总览、缺失材料、分摊编辑、导出管理页面统一接入“固定模块导航 + 当前任务上下文 + 当前任务快捷入口”；
  - 侧栏固定展示首页总览、任务管理、材料审核、成员提醒、分摊确认、导出打印六个稳定模块，不再主要依赖页面内部一组跳转按钮。
- 收口管理员首页为任务推进视图：
  - 管理员首页标题改为“按任务推进处理当前工作”；
  - 首页优先展示创建中/收集中/审核中/需优先处理/可导出等阶段摘要；
  - 新增“当前优先推进任务”卡片，直接给出任务阶段、异常数量和建议入口。
- 同步调整测试与端到端占位流：
  - 更新管理员相关页面测试，覆盖模块导航高亮、当前任务上下文和关键动作入口；
  - 更新账号登录测试与主流程占位测试，对齐新的管理员首页标题与导出入口命名。

### 根因
- `docs/UI原型图对照与交互规范补充.md` 已明确指出：管理端应按“任务推进”而不是“页面入口”组织，且必须具备稳定导航骨架。
- 现有实现虽然已有任务列表、详情、复核、导出等页面，但管理员仍主要通过各页面内部散落的返回链接和跳转按钮穿梭，当前任务上下文不断丢失。
- 管理员首页此前只是泛化任务列表，不能先回答“当前任务推进到哪一步、异常有多少、下一步应该做什么”，因此不满足本轮任务要求。

### 关键改动点
- 新增共享导航与阶段描述：
  - `web/src/app/admin-workspace-shell.tsx`
  - `web/src/app/admin-task-stage.ts`
- 接入共享壳层并重写管理员首页推进摘要：
  - `web/src/app/admin-task-list.tsx`
  - `web/src/app/admin-task-create.tsx`
  - `web/src/app/admin-task-detail.tsx`
  - `web/src/app/admin-review-overview.tsx`
  - `web/src/app/task-missing-materials.tsx`
  - `web/src/app/admin-split-editor.tsx`
  - `web/src/app/admin-export-tasks.tsx`
  - `web/src/styles.css`
- 更新回归测试与主流程占位测试：
  - `web/src/app/admin-task-list.test.tsx`
  - `web/src/app/admin-task-create.test.tsx`
  - `web/src/app/admin-task-detail.test.tsx`
  - `web/src/app/admin-review-overview.test.tsx`
  - `web/src/app/admin-export-tasks.test.tsx`
  - `web/src/app/App.test.tsx`
  - `web/src/app/main-flow-e2e-placeholder.test.tsx`

### 风险与影响面
- 本轮主要收口的是管理员首页、任务详情、复核、缺失材料、分摊和导出这些主链路页面的信息架构，未改动后端业务语义。
- 共享壳层引入后，若后续继续新增管理员页面，应复用同一壳层，否则导航骨架会再次分裂。
- `vite build` 仍有既有的单 chunk 超过 500 kB 告警；这属于仓库现存构建体积问题，本轮未引入新的构建失败。

### 修改文件
- `web/src/app/admin-task-stage.ts`
- `web/src/app/admin-workspace-shell.tsx`
- `web/src/app/admin-task-list.tsx`
- `web/src/app/admin-task-create.tsx`
- `web/src/app/admin-task-detail.tsx`
- `web/src/app/admin-review-overview.tsx`
- `web/src/app/task-missing-materials.tsx`
- `web/src/app/admin-split-editor.tsx`
- `web/src/app/admin-export-tasks.tsx`
- `web/src/styles.css`
- `web/src/app/admin-task-list.test.tsx`
- `web/src/app/admin-task-create.test.tsx`
- `web/src/app/admin-task-detail.test.tsx`
- `web/src/app/admin-review-overview.test.tsx`
- `web/src/app/admin-export-tasks.test.tsx`
- `web/src/app/App.test.tsx`
- `web/src/app/main-flow-e2e-placeholder.test.tsx`
- `TASKS.md`
- `WORKLOG.md`

### 验证结果
- 已通过：
  - `cd web && npm test -- --run src/app/admin-task-list.test.tsx src/app/admin-task-detail.test.tsx src/app/admin-review-overview.test.tsx src/app/admin-export-tasks.test.tsx src/app/task-missing-materials.test.tsx src/app/admin-split-editor.test.tsx src/app/admin-task-create.test.tsx`
    - 7 个测试文件、18 个测试通过
  - `cd web && npm run lint`
  - `cd web && npm test`
    - 21 个测试文件、66 个测试通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic `upgrade -> downgrade -> upgrade` 验证通过
    - `pytest` 350 个用例通过
    - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过
    - Docker Compose 配置检查通过
    - `git diff --check` 通过
- 备注：
  - `pytest` 期间仍有 3 条既有 `DeprecationWarning`，来源于导出测试中的旧 `HTTP_422_UNPROCESSABLE_ENTITY` 常量；
  - Web 测试期间仍打印 Node `--localstorage-file` 既有警告；
  - `vite build` 仍提示单个 chunk 超过 500 kB，这是仓库既有体积告警，本轮未新增构建失败。

### 假设
- 本轮把“稳定导航骨架”优先落实在管理员主处理链路页面上，后续若新增管理员模块，应继续沿用当前壳层和阶段描述文件。
- 首页“当前优先推进任务”的规则仍是基于现有异常/逾期计分启发式排序；若后续产品要求更细的任务优先级策略，应单独定义评分规则，而不是在页面里继续堆条件分支。

## 2026-04-29 03:00 - Share task invoice summaries among members

### 完成内容
- 新增任务内共享发票摘要读接口：
  - 后端增加 `GET /api/tasks/{task_id}/shared-invoices`；
  - 同任务成员和任务管理员可读取当前任务下全部发票的共享摘要；
  - 共享摘要只返回发票基础元数据、当前分摊去向、必要附件类型摘要，不返回税号、交易时间、附件原始文件名、附件存储位置、分摊备注或识别原始响应。
- 成员发票工作台接入共享摘要区：
  - 在“本人发票完整工作台”之外，新增“任务内其他成员已上传发票”只读区域；
  - 同任务成员现在可在单任务上下文中查看队友已上传发票的基础信息、当前分摊去向和附件摘要；
  - 页面文案显式说明该区域不提供原始文件下载、支付截图全文或识别原始响应。
- 同步更新权限测试假设：
  - 保留原有原始接口边界，成员仍不能通过原材料、识别、校验、附件详情等读接口查看无关成员的完整原件信息；
  - 新增测试覆盖“共享摘要可见，但原始附件/无关账号信息仍不可见”的产品边界。

### 根因
- 需求分析文档 V0.2 与架构文档 V0.1 的原始约束默认成员只能查看本人相关材料和费用，但 `TASKS.md` 已明确记录新的产品变更：同一比赛任务内成员之间应可互相查看当前已上传发票。
- 当前实现虽然已经允许发票提交人看到本人上传发票的完整分摊信息，但其他成员仍完全看不到同任务已上传发票，导致成员无法在任务内建立共享报销上下文。
- 直接放开现有材料、识别、校验和附件详情接口会把原件文件名、支付截图全文、识别原始响应等敏感信息一并暴露，因此不能简单靠“放宽已有接口”完成任务。

### 关键改动点
- 新增领域模型 `src/trms_backend/domain/task_shared_invoices.py`，专门构造共享摘要响应。
- 在 `src/trms_backend/api/tasks.py` 增加共享摘要路由，并沿用 bearer 身份绑定当前成员/管理员权限。
- 前端 `web/src/app/member-invoice-workbench.tsx` 新增共享摘要展示区；`web/src/lib/api/trms.ts`、`web/src/lib/api/types.ts` 补充对应接口和类型。
- 新增后端测试 `tests/test_task_shared_invoices_api.py`，并扩展 `tests/test_web_bearer_request_identity_api.py`；前端补充 `web/src/app/member-invoice-workbench.test.tsx` 回归。

### 风险与影响面
- 本轮只新增“共享摘要”读模型，不改变既有原始材料、识别任务、校验详情、附件详情和分摊编辑接口的权限语义；若后续需要共享更多字段，应继续单独定义脱敏边界。
- 共享摘要目前按附件类型聚合计数，不展示附件原始文件名或正文内容；如果后续产品要求展示更细粒度附件信息，需要重新评估支付账号、订单号等敏感字段脱敏规则。
- 这是相对需求分析文档 V0.2/架构文档 V0.1 的产品变更；后续涉及“成员可见性”的任务和测试，都应以“共享摘要可见、敏感原件不可见”为新默认假设。

### 修改文件
- `src/trms_backend/domain/task_shared_invoices.py`
- `src/trms_backend/api/tasks.py`
- `tests/test_task_shared_invoices_api.py`
- `tests/test_web_bearer_request_identity_api.py`
- `web/src/app/member-invoice-workbench.tsx`
- `web/src/app/member-invoice-workbench.test.tsx`
- `web/src/lib/api/trms.ts`
- `web/src/lib/api/types.ts`
- `TASKS.md`
- `WORKLOG.md`

### 验证结果
- 已通过：
  - `uv run pytest tests/test_task_shared_invoices_api.py tests/test_web_bearer_request_identity_api.py tests/test_task_member_status_api.py`
    - 18 个测试通过
  - `cd web && npm test -- --run member-invoice-workbench.test.tsx`
    - 6 个测试通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic `upgrade -> downgrade -> upgrade` 验证通过
    - `pytest` 350 个用例通过
    - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过
    - Docker Compose 配置检查通过
    - `git diff --check` 通过
- 备注：
  - `pytest` 期间仍有 3 条既有 `DeprecationWarning`，来源于导出测试中的旧 `HTTP_422_UNPROCESSABLE_ENTITY` 常量；
  - Web 测试期间仍打印 Node `--localstorage-file` 既有警告；
  - `vite build` 仍提示单个 chunk 超过 500 kB，这是仓库既有体积告警，本轮未新增构建失败。

### 假设
- “共享发票可见”本轮仅指任务内共享摘要可见，不等于开放原始文件下载、附件全文预览、识别原始输出、税号或交易时间等更敏感字段。
- 本轮没有把成员端其它页面统一改成共享摘要模式，只在单任务发票工作台内提供这部分读视图；如果后续要求在更多页面暴露共享摘要，应优先复用本轮新增的专用接口，而不是继续放宽原始读接口。

## 2026-04-29 02:42 - Funnel member entry points into invoice workbench

### 完成内容
- 收口成员端主入口到单任务发票工作台：
  - 成员任务列表顶部主按钮改为进入发票工作台；
  - 每个任务行的主按钮改为“进入工作台”，保留状态驱动的次级直达动作；
  - `closed` 任务的次级直达动作改为进入缺失材料页，避免继续把材料状态页当作默认下一步。
- 收口相关页面的返回路径：
  - 成员材料上传、材料状态、费用确认、缺失材料页都新增“返回当前任务工作台”主链接；
  - 这些页面的说明文案明确为“工作台下的专项入口”，不再把自己表达成并列主入口。
- 补充前端回归测试：
  - `member-task-list.test.tsx` 断言任务列表主入口和任务行主入口都进入工作台；
  - `member-material-upload.test.tsx`、`member-material-status.test.tsx`、`member-expense-confirmation.test.tsx` 断言相关页面可回到当前任务工作台。

### 根因
- 现有成员端虽然已经有单任务发票工作台，但成员任务列表仍把“上传材料 / 查看状态 / 费用确认”作为并列主入口，导致工作台没有成为默认处理上下文。
- 上传、材料状态、缺失材料、费用确认页面也仍以各自页面为中心组织返回路径，用户一旦跳入专项页，就容易丢失“当前任务工作台”这一主上下文。
- 这与 `docs/UI原型图对照与交互规范补充.md` 中“成员端应形成单任务处理闭环”的约束不一致，属于信息架构层面的入口优先级问题，而不是后端能力缺失。

### 修改文件
- `web/src/app/member-task-list.tsx`
- `web/src/app/member-task-list.test.tsx`
- `web/src/app/member-material-upload.tsx`
- `web/src/app/member-material-upload.test.tsx`
- `web/src/app/member-material-status.tsx`
- `web/src/app/member-material-status.test.tsx`
- `web/src/app/member-expense-confirmation.tsx`
- `web/src/app/member-expense-confirmation.test.tsx`
- `web/src/app/task-missing-materials.tsx`
- `TASKS.md`
- `WORKLOG.md`

### 验证结果
- 已通过：
  - `cd web && npm test -- --run member-task-list.test.tsx member-material-upload.test.tsx member-material-status.test.tsx member-expense-confirmation.test.tsx member-invoice-workbench.test.tsx`
    - 5 个测试文件、17 个测试通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic `upgrade -> downgrade -> upgrade` 验证通过
    - `pytest` 347 个用例通过
    - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过
    - Docker Compose 配置检查通过
    - `git diff --check` 通过
- 备注：
  - `pytest` 期间仍有 3 条既有 `DeprecationWarning`，来源于导出测试中的旧 `HTTP_422_UNPROCESSABLE_ENTITY` 常量；
  - Web 测试期间仍打印 Node `--localstorage-file` 既有警告；
  - `vite build` 仍提示单个 chunk 超过 500 kB，这是仓库既有体积告警，本轮未新增构建失败。

### 假设
- 本轮只收口“成员入口优先级”和“返回当前任务工作台”的导航，不重写成员端页面布局，也不把 `/member` 默认路由直接改成工作台。
- 上传、缺失材料、材料状态、费用确认等专项页仍然保留直接访问能力，方便从通知或深链接进入；但它们不再作为成员主流程的首选入口。

## 2026-04-29 02:36 - Add member self-service split adjustment in invoice workbench

### 完成内容
- 在成员发票工作台补齐金额分配对象自助调整入口：
  - 每张本人发票新增“分配对象 / 金额 / 备注”可编辑表单；
  - 支持新增分摊对象、修改金额和分摊备注，并沿用既有后端总额约束；
  - 保存后自动刷新当前任务工作台，避免成员继续看到过期的分摊与确认状态。
- 收口成员侧可见性与失败反馈：
  - 工作台继续只针对“本人上传发票”暴露完整分摊编辑入口，不扩展到无关成员发票；
  - 分摊保存失败时优先展示后端返回的真实拒绝原因，而不是泛化成统一失败文案；
  - 页面显式提示“保存后，受影响成员需要重新确认费用”，并在刷新后展示最新确认状态。
- 补充回归测试：
  - 后端 `tests/test_web_bearer_request_identity_api.py` 新增 bearer 场景，覆盖本人提交人成功调整和无关成员被拒绝；
  - 前端 `web/src/app/member-invoice-workbench.test.tsx` 新增工作台测试，覆盖分摊对象调整后的确认状态刷新，以及后端拒绝原因在成员端可见。

### 根因
- 现有后端已经具备分摊替换、总额校验和确认状态重置能力，但成员端没有稳定入口去编辑“这张票分配给谁、备注是什么”，导致该任务在实际产品链路上仍未闭环。
- 工作台此前只能读到当前分摊结果，成员修改后也无法在同一上下文中立即看到“哪些确认被打回待确认”，这会让成员误以为修改已经完全完成。
- 前端保存失败时默认走通用 4xx 文案归一化，具体的业务拒绝原因会被抹平，不满足任务要求中的“失败原因在成员端可见”。

### 修改文件
- `web/src/app/member-invoice-workbench.tsx`
- `web/src/app/member-invoice-workbench.test.tsx`
- `tests/test_web_bearer_request_identity_api.py`
- `TASKS.md`
- `WORKLOG.md`

### 验证结果
- 已通过：
  - `uv run pytest tests/test_web_bearer_request_identity_api.py`
    - 11 个测试通过
  - `cd web && npm test -- --run member-invoice-workbench.test.tsx`
    - 5 个测试通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic `upgrade -> downgrade -> upgrade` 验证通过
    - `pytest` 347 个用例通过
    - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过
    - Docker Compose 配置检查通过
    - `git diff --check` 通过
- 备注：
  - `pytest` 期间仍有 3 条既有 `DeprecationWarning`，来源于导出测试中的旧 `HTTP_422_UNPROCESSABLE_ENTITY` 常量；
  - Web 测试期间仍打印 Node `--localstorage-file` 既有警告；
  - `vite build` 仍提示单个 chunk 超过 500 kB，这是仓库既有体积告警，本轮未新增构建失败。

### 假设
- 本轮只在“成员发票工作台”中为本人上传发票开放自助分摊调整入口，不改动管理员侧分摊编辑流，也不改动 CLI 交互。
- 本轮复用既有后端权限语义：工作台入口只暴露给发票提交人本人；更宽的 API 语义和后续是否继续收口，仍由后续权限任务统一处理。

## 2026-04-29 02:17 - Add member self-service material type correction

### 完成内容
- 新增成员侧材料类型更正主链路：
  - 后端增加 `PATCH /api/materials/{material_id}/material-type`；
  - 仅允许材料提交人修改本人、已归属、且所属任务仍处于 `open` 的材料类型；
  - 修改后立即刷新关联发票校验结果，避免“材料类型已改但缺失材料/校验状态仍旧滞后”。
- 收口不一致状态边界：
  - 已形成发票主记录的材料，不允许再从 `invoice` 改成辅助材料；
  - 已作为辅助材料挂到发票上的材料，不允许再改成 `invoice`；
  - 越权访问、非法类型和非 `open` 任务下的修改都会返回明确错误。
- 成员发票工作台接入材料类型编辑入口：
  - 每条本人材料卡片增加材料类型下拉和保存按钮；
  - 保存成功后自动刷新当前任务摘要；
  - 保存失败时在卡片内显示明确错误信息。
- 新增测试覆盖：
  - 后端 `tests/test_member_material_type_update_api.py` 覆盖本人成功、越权失败、非法类型、非开放任务拒绝和校验刷新；
  - 前端 `web/src/app/member-invoice-workbench.test.tsx` 覆盖成员在工作台修改材料类型并触发摘要刷新。

### 根因
- 现有成员端虽然能查看材料类型，但没有稳定的自助更正入口；成员一旦上传时选错类型，只能依赖管理员后续人工兜底。
- `material_type` 直接参与支付记录、比赛通知、行程单等附件完整性校验；如果只改前端展示而不刷新后端校验，成员看到的缺失项会长期滞后，形成假状态。
- 材料类型又和发票主记录/辅助材料关联共同构成业务不变量；若不限制某些方向的修改，会出现“已有发票主记录却不是 invoice 类型”这类自相矛盾状态。

### 修改文件
- `src/trms_backend/api/materials.py`
- `src/trms_backend/application/material_type_update.py`
- `src/trms_backend/domain/materials.py`
- `src/trms_backend/infrastructure/repositories.py`
- `src/trms_backend/main.py`
- `tests/test_member_material_type_update_api.py`
- `web/src/app/member-invoice-workbench.tsx`
- `web/src/app/member-invoice-workbench.test.tsx`
- `web/src/lib/api/trms.ts`
- `web/src/lib/api/types.ts`
- `TASKS.md`
- `WORKLOG.md`

### 验证结果
- 已通过：
  - `uv run pytest tests/test_member_material_type_update_api.py`
    - 5 个测试通过
  - `cd web && npm test -- --run member-invoice-workbench.test.tsx`
    - 3 个测试通过
  - `cd web && npm run build`
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic `upgrade -> downgrade -> upgrade` 验证通过
    - `pytest` 345 个用例通过
    - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过
    - Docker Compose 配置检查通过
    - `git diff --check` 通过
- 备注：
  - `pytest` 期间仍有 3 条既有 `DeprecationWarning`，来源于导出测试中的旧 `HTTP_422_UNPROCESSABLE_ENTITY` 常量；
  - Web 测试期间仍打印 Node `--localstorage-file` 既有警告。
  以上均为仓库已有现象，本轮未新增相关失败。

### 假设
- 本轮只提供成员对“本人材料类型”的自助更正，不扩展到管理员代改或跨成员代改；管理员更广义的审核编辑边界仍由后续审核/导航任务继续收口。
- 为避免破坏已形成的发票主链路，本轮保守拒绝“已有发票主记录的材料改成非 `invoice`”和“已挂为附件的材料改成 `invoice`”这两类修改；若后续产品要求支持，需要同时设计发票主记录迁移或解除关联流程。

## 2026-04-29 01:59 - Build member invoice workbench single-task summary view

### 完成内容
- 新增成员发票工作台页面 `web/src/app/member-invoice-workbench.tsx`，以单任务为上下文聚合展示：
  - 本人发票识别字段与当前人工值对比；
  - 材料类型、关联附件、缺失材料项；
  - 当前分摊去向与确认状态；
  - 任务级待处理事项、异常原因和下一步动作。
- 前端接入后端既有 `GET /api/tasks/{task_id}/member-status` 聚合接口，并补齐 `web/src/lib/api/types.ts`、`web/src/lib/api/trms.ts` 的类型和调用封装。
- 为满足“按本人上传发票查看当前分摊方案和确认状态”的读路径，收窄式放宽成员只读边界：
  - 发票提交人现在可查看自己上传发票的完整分摊列表和确认列表；
  - 非提交人的普通成员仍只能看到与自己相关的分摊和确认，不扩展到同任务全部成员可见。
- 新增前端测试 `web/src/app/member-invoice-workbench.test.tsx`，覆盖：
  - 任务切换时工作台摘要刷新；
  - 单任务摘要展示；
  - 关键异常提示、人工更正对比和下一步动作入口。

### 根因
- 现有成员端能力分散在 `member-material-status` 和 `member-expense-confirmation` 两个页面，用户需要自己在“材料状态”和“费用确认”之间重建上下文，不满足当前任务要求的单任务汇总视图。
- 前端此前未接入后端已有的 `member-status` 聚合接口，导致摘要计数、缺失材料和确认统计只能在多个页面重复拼接。
- 成员侧只读分摊/确认接口此前默认按“我是分摊成员”过滤；这会让发票提交人在“本人上传发票”场景下拿不到完整分摊去向与确认状态，无法形成真正的发票工作台视图。

### 修改文件
- `src/trms_backend/api/confirmations.py`
- `src/trms_backend/api/splits.py`
- `src/trms_backend/main.py`
- `tests/test_web_bearer_request_identity_api.py`
- `web/src/app/member-invoice-workbench.tsx`
- `web/src/app/member-invoice-workbench.test.tsx`
- `web/src/app/routes.tsx`
- `web/src/lib/api/trms.ts`
- `web/src/lib/api/types.ts`
- `TASKS.md`
- `WORKLOG.md`

### 验证结果
- 已通过：
  - `uv run pytest tests/test_web_bearer_request_identity_api.py`
    - 9 个测试通过
  - `cd web && npm test -- --run member-invoice-workbench.test.tsx`
    - 2 个测试通过
  - `cd web && npm run lint`
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic `upgrade -> downgrade -> upgrade` 验证通过
    - `pytest` 340 个用例通过
    - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过
    - Docker Compose 配置检查通过
    - `git diff --check` 通过
- 备注：
  - `pytest` 期间仍有 3 条既有 `DeprecationWarning`，来源于导出测试中的旧 `HTTP_422_UNPROCESSABLE_ENTITY` 常量；
  - 前端测试期间仍打印 Node `--localstorage-file` 既有警告。
  以上均为仓库已有现象，本轮未新增相关行为。

### 假设
- 本轮只收口“本人上传发票”的单任务工作台视图，不把成员任务列表主入口改到该页面；入口优先级和主流程重排仍留给后续“收口成员发票工作台入口与下一步动作”任务处理。
- 本轮只把发票提交人的分摊/确认只读可见范围扩到其本人上传的发票，不等同于完成“同任务成员共享发票可见性策略”任务；同任务其他成员的基础元数据可见边界仍待后续单独收口。

## 2026-04-29 02:10 - Split oversized member invoice workspace task

### 完成内容
- 将 `TASKS.md` 中原单条“重构成员发票工作台并补齐自助元数据管理”拆成 4 个可单轮验证的子任务：
  - 成员发票工作台单任务汇总视图；
  - 成员侧材料类型自助更正；
  - 成员侧金额分配对象自助调整；
  - 工作台入口与下一步动作收口。
- 保留该需求原始边界，但把“信息聚合”“可编辑元数据”“分摊对象调整”“导航入口收口”拆开，避免在一轮里同时改动成员端页面结构、后端权限接口和交互流转。

### 拆分依据
- 当前成员端能力分散在 `web/src/app/member-material-status.tsx` 和 `web/src/app/member-expense-confirmation.tsx` 两个页面，任务上下文需要用户自己拼接，不符合原任务 Done when 中“围绕待处理事项、异常原因、下一步动作组织”的要求。
- 当前仓库已有成员侧发票内容更正和分摊查看能力，但仍缺少成员侧 `material_type` 更正入口，也没有单任务发票工作台汇总页；若强行在一轮内同时补齐，会跨前端信息架构、路由入口和后端接口边界，超出“最小可验证任务”范围。
- 该任务与后续“按原型图收口成员端单任务处理闭环”存在交叉；先拆分可避免把“发票工作台能力补齐”和“成员主流程重排”混成一次大改。

### 修改文件
- `TASKS.md`
- `WORKLOG.md`

### 验证结果
- 已通过：
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic `upgrade -> downgrade -> upgrade` 验证通过
    - `pytest` 340 个用例通过
    - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过
    - Docker Compose 配置检查通过
    - `git diff --check` 通过
- 备注：
  - `pytest` 期间仍有 3 条既有 `DeprecationWarning`，来源于导出测试中的旧 `HTTP_422_UNPROCESSABLE_ENTITY` 常量；
  - 前端测试期间仍打印 Node `--localstorage-file` 既有警告。
  以上均为仓库已有现象，本轮未新增相关行为。

### 假设
- 下轮默认从拆分后的第一个未完成任务“建立成员发票工作台单任务汇总视图”继续推进。
- 当前拆分不改变原需求优先级，只是把一个过大的交付项改为多个连续子任务。

## 2026-04-29 01:35 - Implement real merged PDF export artifacts

### 完成内容
- 将 `merged_pdf` 从导出占位能力改为真实产物链路：
  - 异步导出 worker 现在会读取任务内已归档材料，按系统默认顺序合并为真实 PDF，并把产物持久化到既有导出存储；
  - 合并源支持可读 PDF 与 JPEG / PNG / WebP 图片，图片会先转换成 PDF 页面再进入统一合并流程；
  - 导出任务状态接口继续只暴露脱敏后的 artifact 元数据，正式文件仍通过既有下载接口访问。
- 收口 merged PDF 的错误暴露边界：
  - 加密 PDF、损坏 PDF、损坏图片、存储缺文件和不支持的内容类型都会以 `merged pdf source material <material_id> ...` 的形式显式失败；
  - 失败原因会进入导出任务状态和审计日志，不再以“未实现”占位失败或静默跳过材料。
- 同步前端导出页与能力说明：
  - 管理员导出页现在会显示真实 artifact 元数据和下载按钮；
  - `merged_pdf` 能力说明、预览提示文案和导出历史空状态文案已改成“真实产物已可下载”的前提；
  - 修复了前端 `merged_pdf` 预览错误把查询参数写成 `format=json` 的问题，现已按 `format=pdf` 请求真实排序预览。
- 同步文档与任务台账：
  - `TASKS.md` 已将“实现真实合并打印 PDF 导出”标记完成；
  - `README.md` 与 `docs/第一阶段验收映射.md` 已同步去掉“真实合并 PDF 未实现”的过期描述；
  - 新增 `Pillow` 依赖并更新 `uv.lock`，用于把图片材料转换为 PDF 页面。

### 根因
- `src/trms_backend/application/export_async_jobs.py` 之前只会为 CSV / JSON 导出生成真实 artifact，`merged_pdf` 会直接落到 `TaskExportFormatNotImplementedError`；
- `src/trms_backend/domain/exports.py` 中 merged PDF 预览长期混入“报销汇总表 / 成员明细 / 发票明细”的 placeholder 页面，既没有真实文件渲染，也没有和实际导出产物建立一致性；
- `web/src/app/admin-export-tasks.tsx` 与前端 API 类型仍停留在“显示占位说明、不展示 artifact、无下载入口”的阶段，导致即使后端补齐产物也无法在页面上闭环交付。

### 修改文件
- `pyproject.toml`
- `uv.lock`
- `src/trms_backend/application/export_async_jobs.py`
- `src/trms_backend/application/merged_pdf_export.py`
- `src/trms_backend/domain/exports.py`
- `tests/test_exports_api.py`
- `tests/test_export_async_jobs.py`
- `web/src/lib/api/client.ts`
- `web/src/lib/api/trms.ts`
- `web/src/lib/api/types.ts`
- `web/src/app/admin-export-tasks.tsx`
- `web/src/app/admin-export-tasks.test.tsx`
- `README.md`
- `docs/第一阶段验收映射.md`
- `TASKS.md`
- `WORKLOG.md`

### 验证结果
- 已通过：
  - `uv run pytest tests/test_exports_api.py tests/test_export_async_jobs.py`
    - 27 个测试通过
  - `npm test -- --run admin-export-tasks.test.tsx`
    - 2 个测试通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic `upgrade -> downgrade -> upgrade` 验证通过
    - `pytest` 340 个用例通过
    - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过
    - Docker Compose 配置检查通过
    - `git diff --check` 通过
- 备注：
  - `pytest` 期间仍有 3 条既有 `DeprecationWarning`，来源于导出测试中的旧 `HTTP_422_UNPROCESSABLE_ENTITY` 常量；
  - 前端测试期间仍打印 Node `--localstorage-file` 既有警告。
  以上均为仓库已有现象，本轮未新增相关行为。

### 假设
- 本轮对 merged PDF 采用保守支持边界：只合并当前仓库已允许上传且可稳定转换的 PDF / JPEG / PNG / WebP；`zip` 或其他不可打印类型继续显式失败，而不是尝试隐式降级。
- merged PDF 现在只合并真实电子材料本体，不再把汇总表/明细表占位页混入打印包；这些结构化表格继续作为独立导出物存在，更符合需求文档中“表格导出”和“打印材料包”分离的边界。

## 2026-04-29 01:24 - Add VLM-based direct recognition for scanned PDFs and images

### 完成内容
- 接入扫描 PDF / 图片直提识别链路：
  - `RecognitionPreparationService` 不再把图片和纯扫描 PDF 统一打回 `ocr_not_configured`；
  - 文本型 PDF 继续走本地文本提取；
  - 纯扫描 PDF 改为把 PDF 文件本体以 base64 data URL 形式直接交给 OpenAI 兼容多模态模型；
  - JPEG / PNG / WebP 图片改为以 `image_url` data URL 形式直接交给 OpenAI 兼容多模态模型。
- 保持原有“AI 结果只是识别建议”的边界：
  - 结构化输出仍走既有 Pydantic 模型校验；
  - 字段置信度仍决定 `recognized` / `needs_confirmation`；
  - 多模态模型失败仍显式记录 `stage=ai` 和具体 `reason`，不会伪装成识别成功。
- 同步识别输入抽象与文档：
  - 新增文本 / PDF 文件 / 图片文件三类 `RecognitionDocumentInput` 载荷约束；
  - `README.md` 和 `docs/第一阶段验收映射.md` 已同步去掉“扫描 PDF / 图片仍未接入”的过期描述。

### 根因
- `src/trms_backend/application/recognition_preparation.py` 之前只支持“PDF 可抽取文本”这一条准备路径；
- 一旦 PDF 没有可抽取文本，或材料本身是图片，就直接失败为 `ocr_not_configured`，导致需求和架构文档中要求的“扫描件 / 图片走 VLM 直提”根本无法进入结构化识别主链路；
- 识别客户端 `src/trms_backend/application/recognition_llm.py` 之前也只会构造纯文本 `chat.completions` 请求，无法向 OpenAI 兼容多模态模型传入 PDF 文件或图片内容。

### 修改文件
- `src/trms_backend/application/recognition_preparation.py`
- `src/trms_backend/application/recognition_llm.py`
- `tests/test_recognition_execution_api.py`
- `tests/test_recognition_llm.py`
- `README.md`
- `docs/第一阶段验收映射.md`
- `TASKS.md`
- `WORKLOG.md`

### 验证结果
- 已通过：
  - `uv run pytest tests/test_recognition_llm.py`
    - 8 个测试通过
  - `uv run pytest tests/test_recognition_execution_api.py`
    - 14 个测试通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic `upgrade -> downgrade -> upgrade` 验证通过
    - `pytest` 338 个用例通过
    - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过
    - Docker Compose 配置检查通过
    - `git diff --check` 通过
- 备注：
  - `pytest` 期间仍有 3 条既有 `DeprecationWarning`，来源于导出测试中的旧 `HTTP_422_UNPROCESSABLE_ENTITY` 常量；
  - 前端测试期间仍打印 Node `--localstorage-file` 既有警告。
  以上均为仓库已有现象，本轮未新增相关行为。

### 假设
- 本轮对扫描 PDF 采用保守实现：只要 PDF 本地文本提取为空但能确认含有图像对象，就直接把原始 PDF 文件交给多模态模型，而不是在服务端新增 PDF 栅格化或传统 OCR 依赖。
- 未实际联调真实外部 VLM Provider；当前只通过请求载荷测试和伪造客户端回归测试验证 OpenAI 兼容请求格式与主链路行为。

## 2026-04-29 01:05 - Tighten formatted email submission identity trust boundary

### 完成内容
- 收口格式化邮件入站身份信任边界：
  - `/api/email/materials` 不再默认信任表单中的 `resolved_member_id`；
  - 只有后端配置了 `TRMS_AUTH_EMAIL_INBOUND_TOKEN`，且请求头 `X-TRMS-Email-Inbound-Token` 与之匹配时，才会把 `resolved_member_id` 当作可信成员身份直接写入成员主链路；
  - 未携带可信入站 token 时，即使请求里显式带了 `resolved_member_id`，材料也只进入待归属流程，不再直接按该成员归档。
- 补齐运行配置与部署说明：
  - 新增 `TRMS_AUTH_EMAIL_INBOUND_TOKEN` 运行配置；
  - `.env.example`、`.env.development.example`、`deploy/docker-compose.yml`、`README.md` 和 `docs/格式化邮件提交规范说明.md` 已同步记录该配置及其边界。
- 补齐回归测试：
  - 邮件入站覆盖“可信 token + resolved_member_id 直接归档”“缺少可信 token 时伪造成员身份失败并转待归属”“错误 token 拒绝”“未知任务转待归属”“未绑定进入待归属”和“部分附件失败”；
  - 运行配置测试覆盖 `TRMS_AUTH_EMAIL_INBOUND_TOKEN` 的读取与日志脱敏。

### 根因
- `src/trms_backend/api/email_materials.py` 之前允许匿名调用方直接在表单中提供 `resolved_member_id`；
- `src/trms_backend/application/email_material_submission.py` 收到该字段后，会直接按该成员调用统一材料提交主链路；
- 这意味着任意调用方只要知道成员编号，就能伪造“邮件适配器已确认身份”的前提，把材料直接写入成员任务，违背需求、架构文档和邮件规范中“未受控身份只能待归属”的边界。

### 修改文件
- `src/trms_backend/api/email_materials.py`
- `src/trms_backend/main.py`
- `src/trms_backend/runtime_config.py`
- `tests/test_email_materials_api.py`
- `tests/test_runtime_config.py`
- `.env.example`
- `.env.development.example`
- `deploy/docker-compose.yml`
- `README.md`
- `docs/格式化邮件提交规范说明.md`
- `TASKS.md`
- `WORKLOG.md`

### 验证结果
- 已通过：
  - `uv run pytest tests/test_email_materials_api.py tests/test_runtime_config.py`
    - 25 个测试通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic `upgrade -> downgrade -> upgrade` 验证通过
    - `pytest` 333 个用例通过
    - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过
    - Docker Compose 配置检查通过
    - `git diff --check` 通过
- 备注：
  - `pytest` 期间仍有 3 条既有 `DeprecationWarning`，来源于导出测试中的旧 `HTTP_422_UNPROCESSABLE_ENTITY` 常量；
  - 前端测试期间仍打印 Node `--localstorage-file` 既有警告。
  以上均为仓库已有现象，本轮未新增相关行为。

### 假设
- 本轮沿用 Telegram 渠道的最小可信边界：当前仓库仍未实现真实邮箱绑定，因此邮件渠道只有两条允许的成员身份来源：
  - 受信任入站器通过 `TRMS_AUTH_EMAIL_INBOUND_TOKEN` 明确声明的 `resolved_member_id`；
  - 否则一律进入待归属，由后续人工认领处理。

## 2026-04-29 00:57 - Tighten Telegram binding and inbound identity trust boundaries

### 完成内容
- 收口 Telegram 绑定管理权限：
  - `PUT /api/telegram-bindings/{telegram_user_id}`
  - `GET /api/telegram-bindings/{telegram_user_id}`
  - `GET /api/telegram-bindings/{telegram_user_id}/submission-identity`
  以上接口现在都必须携带 bearer token，且仅 `admin` / `system_admin` 可以访问。
- 收口 Telegram 入站身份信任边界：
  - `/api/telegram/materials` 不再默认信任表单中的 `telegram_user_id`；
  - 只有后端配置了 `TRMS_AUTH_TELEGRAM_INBOUND_TOKEN`，且请求头 `X-TRMS-Telegram-Inbound-Token` 与之匹配时，才会按 Telegram 绑定关系把材料直接写入成员主链路；
  - 未携带可信入站 token 时，即使 Telegram 账号已绑定，材料也只进入待归属流程，不再直接归档到成员名下。
- 补齐运行配置与部署说明：
  - 新增 `TRMS_AUTH_TELEGRAM_INBOUND_TOKEN` 运行配置；
  - `.env.example`、`.env.development.example`、`deploy/docker-compose.yml`、`README.md` 已同步记录该配置及其安全边界。
- 补齐回归测试：
  - 绑定接口覆盖匿名拒绝、普通成员拒绝、管理员成功、未绑定解析和绑定冲突；
  - Telegram 入站覆盖“可信 token + 已绑定直接归档”“缺少可信 token 转待归属”“错误 token 拒绝”“未绑定待归属”“已绑定但缺任务仍待归属”。

### 根因
- `src/trms_backend/api/telegram_bindings.py` 之前完全未鉴权，匿名调用方可以为任意 `telegram_user_id` 建立或查询绑定关系；
- `src/trms_backend/api/telegram_materials.py` 与 `src/trms_backend/application/telegram_material_submission.py` 之前直接把表单里的 `telegram_user_id` 当作真实身份来源，只要该编号已绑定成员且提供了任务编号，就会直接进入成员提交主链路；
- 这意味着调用方即使并不是真实 Telegram 入站器，也能伪造已绑定 Telegram 身份向任务提交材料，违背需求和架构文档中“渠道绑定必须受控、未确认身份只能待归属”的边界。

### 修改文件
- `src/trms_backend/api/telegram_bindings.py`
- `src/trms_backend/api/telegram_materials.py`
- `src/trms_backend/application/telegram_material_submission.py`
- `src/trms_backend/runtime_config.py`
- `tests/test_telegram_bindings_api.py`
- `tests/test_telegram_materials_api.py`
- `tests/test_runtime_config.py`
- `.env.example`
- `.env.development.example`
- `deploy/docker-compose.yml`
- `README.md`
- `TASKS.md`
- `WORKLOG.md`

### 验证结果
- 已通过：
  - `uv run pytest tests/test_telegram_bindings_api.py tests/test_telegram_materials_api.py tests/test_runtime_config.py`
    - 26 个测试通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic `upgrade -> downgrade -> upgrade` 验证通过
    - `pytest` 331 个用例通过
    - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过
    - Docker Compose 配置检查通过
    - `git diff --check` 通过
- 备注：
  - `pytest` 期间仍有 3 条既有 `DeprecationWarning`，来源于导出测试中的旧 `HTTP_422_UNPROCESSABLE_ENTITY` 常量；
  - 前端测试期间仍打印 Node `--localstorage-file` 既有警告。
  以上均为仓库已有现象，本轮未新增相关行为。

### 假设
- 本轮采用最小可信入站边界：只有持有后端配置 token 的 Telegram 入站器才被视为受信任来源；未携带该 token 的请求仍允许把文件收进待归属，便于人工后续认领，但不会再直接借已绑定 `telegram_user_id` 越权落到成员主链路。

## 2026-04-29 00:50 - Require bearer identity for member-side status/detail reads

### 完成内容
- 收口成员侧状态读取接口：
  - `GET /api/tasks/{task_id}/expense-details`
  - `GET /api/tasks/{task_id}/member-status`
  - `GET /api/tasks/{task_id}/missing-materials`
  以上接口现在都必须携带 bearer token，不再允许匿名请求仅靠 `actor_id` 读取成员数据。
- 修正 bearer 场景下的成员状态聚合：
  - `member-status` 路由现在先解析请求身份，再按解析后的成员身份筛选识别结果；
  - 修复了 bearer 请求未显式带 `actor_id` 时，识别状态可能被错误过滤为空的问题。
- 收口 CLI 对这三类成员读取接口的调用方式：
  - `status`、`missing-materials`、`confirm-expense` 读取费用明细时，不再在 URL 上主动拼接 `actor_id`；
  - 仍保留响应里的 `actor_id` 供现有 CLI 文本/JSON 输出复用。
- 补齐回归测试：
  - 后端测试覆盖匿名自报成员编号被拒绝、bearer 登录后冒充他人被拒绝、成员本人读取成功、无关成员读取被拒绝；
  - CLI 测试同步切到“成员 bearer 读取不再拼接 `actor_id` 查询参数”的新前提；
  - `tests/test_expense_disputes_api.py` 中一处旧的匿名读取 `expense-details` 假设已同步改为成员 bearer 读取。

### 根因
- `src/trms_backend/api/tasks.py` 中这三条成员侧 GET 路由此前仍使用可选身份依赖，匿名请求只要自报 `actor_id` 就能进入成员数据构建逻辑；
- `/member-status` 还在真正解析 bearer 身份前，直接使用原始查询参数筛选识别结果，导致接口既有越权风险，也有 bearer 无显式 `actor_id` 时的上下文错读问题；
- CLI 仍沿用旧协议把成员编号直接拼到查询字符串里，与“成员侧读取应以 bearer 身份为准”的收口方向不一致。

### 修改文件
- `src/trms_backend/api/tasks.py`
- `src/trms_cli/cli.py`
- `tests/test_missing_materials_api.py`
- `tests/test_expense_details_api.py`
- `tests/test_task_member_status_api.py`
- `tests/test_expense_disputes_api.py`
- `tests/test_cli_status.py`
- `tests/test_cli_missing_materials.py`
- `tests/test_cli_confirm_expense.py`
- `TASKS.md`
- `WORKLOG.md`

### 验证结果
- 已通过：
  - `uv run pytest tests/test_missing_materials_api.py tests/test_expense_details_api.py tests/test_task_member_status_api.py tests/test_web_bearer_request_identity_api.py`
    - 24 个测试通过
  - `uv run pytest tests/test_cli_status.py tests/test_cli_missing_materials.py tests/test_cli_confirm_expense.py`
    - 11 个测试通过
  - `uv run pytest tests/test_expense_disputes_api.py`
    - 3 个测试通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic `upgrade -> downgrade -> upgrade` 验证通过
    - `pytest` 328 个用例通过
    - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过
    - Docker Compose 配置检查通过
    - `git diff --check` 通过
- 备注：
  - `pytest` 期间仍有 3 条既有 `DeprecationWarning`，来源于导出测试中的旧 `HTTP_422_UNPROCESSABLE_ENTITY` 常量；
  - 前端测试期间仍打印 Node `--localstorage-file` 既有警告。
  以上均为仓库已有现象，本轮未新增相关行为。

### 假设
- 本轮按保守边界处理成员侧读取：Bearer 已登录时，以认证身份为唯一真实读取上下文；显式 `actor_id` 只作为兼容字段保留，并在与 bearer 身份不一致时显式拒绝。

## 2026-04-29 00:37 - Tighten task creation and task query auth boundaries

### 完成内容
- 收口任务创建权限：
  - `POST /api/tasks` 现在必须携带 bearer token；
  - 只有 `admin` 或 `system_admin` 角色可以创建任务；
  - 请求体里的 `administrator_id` 必须与认证身份一致，匿名请求和普通成员请求都会被拒绝。
- 收口任务查询权限：
  - `GET /api/tasks`、`GET /api/tasks/{task_id}`、`GET /api/tasks/{task_id}/members`、`GET /api/tasks/{task_id}/materials` 现在都要求 bearer 身份；
  - 成员仍只能看到自己可见的任务和本人提交的任务材料；
  - 任务管理员仍可查看本任务详情、成员和全部任务材料；
  - 无关管理员不再能读取其他管理员名下任务详情、成员或材料。
- 补齐并修正回归测试：
  - `tests/test_tasks_api.py` 增加匿名、普通成员、任务管理员、无关管理员四类路径覆盖；
  - 将全仓库受影响测试统一切到“管理员 bearer 创建任务”的新前提；
  - 同步修复 `missing_materials`、`task_member_status`、`recognition` 等 fixture 中对匿名建任务的旧假设。

### 根因
- `src/trms_backend/api/tasks.py` 中任务创建接口此前完全未鉴权，匿名请求可直接创建报销任务；
- 任务列表接口会在匿名场景下返回全部任务或按 `member_id` 过滤后的任务，详情/成员接口又把匿名身份解析成可访问 scope；
- `src/trms_backend/api/materials.py` 中任务材料列表也沿用了同样的匿名可见假设，导致任务主链路存在明显越权读取面。

### 修改文件
- `src/trms_backend/api/tasks.py`
- `src/trms_backend/api/materials.py`
- `tests/test_api_error_responses.py`
- `tests/test_automatic_reminder_tasks_api.py`
- `tests/test_email_materials_api.py`
- `tests/test_expense_details_api.py`
- `tests/test_expense_disputes_api.py`
- `tests/test_export_async_jobs.py`
- `tests/test_exports_api.py`
- `tests/test_invoices_api.py`
- `tests/test_material_storage.py`
- `tests/test_materials_api.py`
- `tests/test_metrics.py`
- `tests/test_missing_materials_api.py`
- `tests/test_overdue_confirmations_api.py`
- `tests/test_recognition_async_jobs.py`
- `tests/test_recognition_execution_api.py`
- `tests/test_recognition_tasks_api.py`
- `tests/test_task_member_status_api.py`
- `tests/test_task_review_summary_api.py`
- `tests/test_tasks_api.py`
- `tests/test_telegram_materials_api.py`
- `tests/test_web_bearer_request_identity_api.py`
- `TASKS.md`
- `WORKLOG.md`

### 验证结果
- 已通过：
  - `uv run pytest tests/test_tasks_api.py tests/test_materials_api.py tests/test_web_bearer_request_identity_api.py tests/test_api_error_responses.py tests/test_invoices_api.py tests/test_exports_api.py tests/test_recognition_tasks_api.py tests/test_recognition_execution_api.py tests/test_recognition_async_jobs.py tests/test_automatic_reminder_tasks_api.py tests/test_email_materials_api.py tests/test_telegram_materials_api.py tests/test_overdue_confirmations_api.py tests/test_task_review_summary_api.py tests/test_expense_details_api.py tests/test_expense_disputes_api.py tests/test_export_async_jobs.py tests/test_metrics.py`
    - 194 个测试通过
  - `uv run pytest tests/test_missing_materials_api.py tests/test_task_member_status_api.py`
    - 5 个测试通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic `upgrade -> downgrade -> upgrade` 验证通过
    - `pytest` 322 个用例通过
    - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过
    - Docker Compose 配置检查通过
    - `git diff --check` 通过
- 备注：
  - `pytest` 期间仍有 3 条既有 `DeprecationWarning`，来源于导出测试中的旧 `HTTP_422_UNPROCESSABLE_ENTITY` 常量；
  - 前端测试期间仍打印 Node `--localstorage-file` 既有警告。
  以上均为仓库已有现象，本轮未新增相关行为。

### 假设
- 本轮采用保守权限边界：即使是 `system_admin`，创建任务时也必须使用与 bearer 身份一致的 `administrator_id`，不开放“替其他管理员代建任务”的隐式代理能力；若后续确有代建需求，应作为独立权限任务显式设计和测试。

## 2026-04-29 00:32 - Review prototype image and document current UI design gaps

### 完成内容
- 读取并分析了新增原型图 `docs/原型图.png`。
- 新增文档 `docs/UI原型图对照与交互规范补充.md`，明确：
  - 当前阶段不要求像素级复刻原型图；
  - 但必须遵循其基础信息架构、任务推进方式、列表-详情联动和成员闭环处理规范。
- 文档中整理了当前 UI 的主要不合理之处：
  - 首页仍偏入口页，不是任务推进页；
  - 管理端缺少稳定导航骨架；
  - 任务上下文被拆散到过多独立页面；
  - 材料审核缺少同页详情联动；
  - 成员端闭环被拆成上传 / 状态 / 缺失 / 费用确认多段；
  - 成员看不到完整发票处理上下文；
  - 页面文案仍泄露实现视角；
  - 状态标签与摘要结构还不够统一。
- 将后续 UI 收口工作拆回 `TASKS.md`：
  - 按原型图收口管理员端导航与任务推进信息架构；
  - 按原型图建立材料审核列表-详情联动视图；
  - 按原型图收口成员端单任务处理闭环。

### 根因
- 当前前端虽然已经完成角色入口收口和部分业务文案清理，但页面组织方式仍主要跟随路由和接口边界，而不是跟随报销任务的真实推进链路。
- 原型图的价值不在于视觉皮肤，而在于它已经给出了“任务驱动、同页联动、成员闭环、统一状态语义”的结构化规范；如果只把它当作参考图，不写成文档约束，后续实现仍会继续碎片化。

### 修改文件
- `TASKS.md`
- `WORKLOG.md`
- `docs/UI原型图对照与交互规范补充.md`

### 验证结果
- 已通过：
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic 临时 SQLite 迁移校验通过：`upgrade head -> downgrade base -> upgrade head`
    - `pytest` 320 个用例通过
    - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过
    - 前端测试共 20 个测试文件、60 个测试通过
    - Docker Compose 配置检查通过
    - `git diff --check` 通过
- 备注：
  - `pytest` 期间仍有 3 条既有 `DeprecationWarning`，来源于导出测试中的旧 `HTTP_422_UNPROCESSABLE_ENTITY` 常量；
  - 前端测试期间仍打印 Node `--localstorage-file` 既有警告。
  以上均为仓库已有现象，本轮未新增相关行为。

### 假设
- 当前文档中的 UI 问题判断来自原型图与前端代码结构对照，不依赖浏览器人工操作录像；
- 后续具体页面不必照搬原型图布局比例或视觉风格，但不得违背其基础交互结构。

## 2026-04-29 00:08 - Record VLM-based OCR requirement update

### 完成内容
- 将“扫描 PDF / 图片 OCR”需求明确收敛为“通过支持图像输入的 VLM API 直接提取结构化信息”：
  - 需求文档 FR-003 增加该处理逻辑，不再把“先落传统 OCR 文本”写成唯一主路径；
  - 架构文档同步把扫描 PDF / 图片识别节点从泛化 `OCR` 改为 `VLM 图像直提`，并更新技术选型与设计原则；
  - `TASKS.md` 中对应未完成任务改写为“接入基于 VLM API 的扫描 PDF / 图片直提识别链路”；
  - `README.md` 中当前能力边界同步更新，明确待补齐的是 VLM 图像直提链路。

### 根因
- 现有文档里对“扫描 PDF / 图片识别”的表述仍然偏向传统 OCR 能力，但用户已明确要求该路径应以 VLM API 的直接结构化提取为主。
- 如果只改任务名而不改需求与架构文档，后续实现会继续在“传统 OCR 中间文本”与“VLM 直提”两条路径之间摇摆，造成验收口径不一致。

### 修改文件
- `TASKS.md`
- `WORKLOG.md`
- `README.md`
- `docs/同济大学ACM竞赛报销收集系统需求分析文档_V0.2.md`
- `docs/同济大学ACM竞赛报销收集系统架构设计与技术选型文档_V0.1.md`

### 验证结果
- 已通过：
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic 临时 SQLite 迁移校验通过：`upgrade head -> downgrade base -> upgrade head`
    - `pytest` 320 个用例通过
    - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过
    - 前端测试共 20 个测试文件、60 个测试通过
    - Docker Compose 配置检查通过
    - `git diff --check` 通过
- 备注：
  - `pytest` 期间仍有 3 条既有 `DeprecationWarning`，来源于导出测试中的旧 `HTTP_422_UNPROCESSABLE_ENTITY` 常量；
  - 前端测试期间仍打印 Node `--localstorage-file` 既有警告。
  以上均为仓库已有现象，本轮未新增相关行为。

### 假设
- 当前仅把“VLM API 直提”写入需求和任务，不在本轮继续决定具体 Provider、模型名称、多模态请求协议或是否保留传统 OCR 作为兜底。

## 2026-04-28 23:58 - Record review findings and new product-level task changes

### 完成内容
- 基于需求分析文档 V0.2、架构设计文档 V0.1 与当前代码实现，补充了新的高优先级任务到 `TASKS.md`：
  - 收口任务创建与匿名任务查询权限；
  - 禁止成员侧接口通过匿名自报 `actor_id` 越权读取；
  - 收口 Telegram 绑定与提交身份边界；
  - 收口格式化邮件提交成员身份解析边界；
  - 接入扫描 PDF / 图片 OCR 识别链路；
  - 实现真实合并打印 PDF 导出；
  - 重构成员发票工作台并补齐自助元数据管理。
- 记录新的产品变更要求：
  - 用户要求“同一比赛任务内的成员之间应可互相查看当前已上传发票”；
  - 该要求已写入 `TASKS.md`，作为独立未完成任务跟踪。

### 根因
- 当前任务队列虽然已经覆盖大量第一阶段功能骨架，但没有把这次文档对照 review 发现的高风险偏差系统性排进队列，后续代理容易继续沿着现有骨架修补，而不是优先处理真正偏离需求的主链路问题。
- 同时，用户对成员间发票可见性的最新要求与旧需求文档存在直接冲突；如果不显式记录为需求变更，后续实现会在权限测试、前端展示和审计边界上持续反复。

### 修改文件
- `TASKS.md`
- `WORKLOG.md`

### 验证结果
- 已通过：
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic 临时 SQLite 迁移校验通过：`upgrade head -> downgrade base -> upgrade head`
    - `pytest` 320 个用例通过
    - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过
    - 前端测试共 20 个测试文件、60 个测试通过
    - Docker Compose 配置检查通过
    - `git diff --check` 通过
- 备注：
  - `pytest` 期间仍有 3 条既有 `DeprecationWarning`，来源于导出测试中的旧 `HTTP_422_UNPROCESSABLE_ENTITY` 常量；
  - 前端测试期间仍打印 Node `--localstorage-file` 既有警告。
  以上均为仓库已有现象，本轮未新增相关行为。

### 假设
- 当前先按用户最新要求，将“同场比赛成员共享发票视图”视为新的产品方向写入任务队列；
- 但该要求尚未自动扩展为“所有成员可下载所有原始附件或支付截图全文”，后续实现时仍需单独界定敏感文件访问边界。

## 2026-04-28 23:40 - Tighten auth-gated entry visibility and member self-service recognition actions

### 完成内容
- 收口未登录与已登录用户的前端入口可见性：
  - `web/src/app/pages.tsx` 的首页不再向未登录用户展示成员、管理员或系统管理功能板块，只保留登录/注册引导；
  - 顶部导航在登录后只显示当前账号可进入的工作台入口，不再把其他角色板块混在同一账号首页和导航里；
  - `web/src/app/auth-store.ts` 增加前端会话的 `availableRoles` 兼容字段，为后续多角色账号切换保留最小前端数据边界。
- 开放成员侧发票识别自助处理：
  - `src/trms_backend/api/recognitions.py` 允许材料提交人对本人材料发起重识别与执行识别；
  - 仍保留“识别结果状态更新只能由管理员路径完成”的边界，没有把成员权限放宽成任意写入识别结果。
- 扩展成员材料状态页：
  - `web/src/app/member-material-status.tsx` 现在可展示“运行重新识别”按钮；
  - 发票材料支持成员本人在状态页直接人工填写或更正发票号码、金额、抬头、税号、交易时间和费用类型；
  - 保存后会刷新当前材料对应的校验结果，重识别后会刷新识别状态。
- 补齐回归测试：
  - 后端测试覆盖成员本人可重识别、其他成员不可重识别、成员仍不可直接改写识别状态；
  - 前端测试覆盖未登录首页不再暴露角色板块，以及成员材料状态页出现自助重识别与人工填写入口。

### 根因
- 当前 UI 体验差的根因不是单纯样式问题，而是信息架构和职责边界错位：
  - 未登录首页和导航直接暴露多个角色入口，导致用户在进入系统前就看到不属于自己的板块；
  - 登录后的首页仍混合展示其他角色信息，没有按“当前账号能做什么”收口；
  - 成员材料状态页只能看结果，不能完成“重识别 / 人工补录”这类本该由材料提交人自己完成的动作；
  - 后端又把识别重试权限收紧在管理员，进一步放大了这个职责错位。

### 修改文件
- `TASKS.md`
- `WORKLOG.md`
- `src/trms_backend/api/recognitions.py`
- `tests/test_recognition_execution_api.py`
- `tests/test_recognition_tasks_api.py`
- `web/src/app/App.test.tsx`
- `web/src/app/auth-store.ts`
- `web/src/app/member-material-status.test.tsx`
- `web/src/app/member-material-status.tsx`
- `web/src/app/pages.tsx`
- `web/src/lib/api/trms.ts`
- `web/src/lib/api/types.ts`

### 验证结果
- 已通过：
  - `uv run pytest tests/test_recognition_tasks_api.py tests/test_recognition_execution_api.py tests/test_web_bearer_request_identity_api.py`
    - 29 个测试通过
  - `cd web && npm test -- src/app/App.test.tsx src/app/member-material-status.test.tsx`
    - 2 个测试文件、10 个测试通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic 临时 SQLite 迁移校验通过：`upgrade head -> downgrade base -> upgrade head`
    - `pytest` 320 个用例通过
    - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过
    - 前端测试共 20 个测试文件、60 个测试通过
    - Docker Compose 配置检查通过
    - `git diff --check` 通过
- 备注：
  - 前端测试期间仍打印 Node `--localstorage-file` 既有警告；
  - `pytest` 期间仍有 3 条既有 `DeprecationWarning`，来源于导出测试中的旧 `HTTP_422_UNPROCESSABLE_ENTITY` 常量。
  以上均为仓库已有现象，本轮未新增相关行为。

### 假设
- 当前保守假设：本轮先把“入口按登录态/角色收口”和“成员自助识别处理”作为一个最小闭环完成；
- 用户提出的“单账号多角色”需要后端用户模型、token 身份上下文和鉴权测试同步改造，已经补入 `TASKS.md` 作为后续独立任务，本轮只把前端会话层预留为可兼容多角色列表，不把完整数据模型重构混入本次提交。

## 2026-04-28 23:15 - Add DeepSeek recognition response compatibility

### 完成内容
- 修复 DeepSeek 结构化识别请求格式：
  - `src/trms_backend/application/recognition_llm.py` 现在会根据 LLM Provider 的 `base_url` 判断是否为 DeepSeek；
  - 对 `api.deepseek.com` 发送 `response_format={"type":"json_object"}`，不再继续发送已被该接口拒绝的 `json_schema`；
  - 对其他 OpenAI 兼容 Provider 保持原有 `json_schema` 分支不变。
- 修复 DeepSeek 返回体兼容性：
  - 增加对两种 JSON 形态的兼容：
    - `{"output": {...}}`
    - 直接字段对象 `{...}`；
  - 若返回的是直接字段对象，后端会在本地归一化为 `{"output": ...}` 后再做 Pydantic 校验，避免接口已成功返回 `200` 但因为缺少顶层 `output` 而被本地当成 `llm_output_invalid`。
- 补充回归测试：
  - `tests/test_recognition_llm.py` 新增 DeepSeek 分支测试，覆盖 `json_object` 请求格式；
  - 新增对“直接字段对象”响应的兼容测试，避免以后再次回归。

### 根因
- 当前识别客户端默认向所有 OpenAI 兼容接口发送 `response_format.type=json_schema`。
- 你当前配置的 DeepSeek 接口 `https://api.deepseek.com/v1/chat/completions` 明确返回 `400 Bad Request`，错误体为 `This response_format type is unavailable now`，说明该接口当前不接受 `json_schema`。
- 进一步做最小真实请求复现时，DeepSeek 在 `json_object` 模式下可以返回 `200`，但生成内容不保证带顶层 `output` 包装；如果不做本地归一化，依然会在后端校验阶段失败。

### 修改文件
- `TASKS.md`
- `WORKLOG.md`
- `src/trms_backend/application/recognition_llm.py`
- `tests/test_recognition_llm.py`

### 验证结果
- 已通过：
  - `uv run pytest tests/test_recognition_llm.py`
    - 6 个测试通过
  - 真实最小请求复现：
    - 使用你当前 `.env` 中的 DeepSeek 配置对 `https://api.deepseek.com/v1/chat/completions` 发起最小请求；
    - `response_format={"type":"json_schema"}` 时返回 `400`，错误为 `This response_format type is unavailable now`
    - `response_format={"type":"json_object"}` 时返回 `200`
  - `env UV_CACHE_DIR=/home/gsh/.cache/uv ./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic 临时 SQLite 迁移校验通过：`upgrade head -> downgrade base -> upgrade head`
    - `pytest` 318 个用例通过
    - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过
    - 前端测试共 20 个测试文件、59 个测试通过
    - Docker Compose 配置检查通过
    - `git diff --check` 通过

### 备注
- `pytest` 期间仍有 3 条既有 `DeprecationWarning`，来源于导出测试里的旧 `HTTP_422_UNPROCESSABLE_ENTITY` 常量；
- 前端测试期间仍打印 Node `--localstorage-file` 既有警告。
以上均为仓库已有现象，本轮未新增相关行为。

### 假设
- 当前保守假设：短期内以 `base_url` 命中 `api.deepseek.com` 作为 DeepSeek 兼容分支判断条件是可接受的最小修复；如果后续需要支持更多“只接受 `json_object`”的 Provider，应该把该能力提炼为显式配置项，而不是继续堆域名特判。

## 2026-04-28 23:02 - Fix uv module entrypoints for src layout

### 完成内容
- 在 `pyproject.toml` 中补齐项目打包配置：
  - 新增 `[build-system]`，使用 `hatchling` 作为构建后端；
  - 新增 `[tool.hatch.build.targets.wheel]`，显式声明 `src/trms_backend` 与 `src/trms_cli` 两个包目录。
- 修复本地 `uv` 运行入口：
  - `uv sync` 现在会把当前仓库作为本地项目安装到 `.venv`；
  - `uv run python -m trms_backend` 与 `uv run python -m trms_cli` 不再因为 `src/` 布局未打包而报 `No module named trms_backend`。
- 补齐前端测试环境隔离：
  - 更新 `web/src/test/setup.ts`，让前端测试固定使用同源 `/api`，不再受仓库根目录 `.env` 里开发联调用绝对 `VITE_API_BASE_URL` 的影响；
  - 保持本地开发模板仍可继续使用 `http://127.0.0.1:9876/api` 做跨端口联调，不把“测试稳定”建立在回退开发配置之上。

### 根因
- 仓库使用 `src/` 布局，但此前 `pyproject.toml` 只有依赖声明，没有 `build-system` 和包发现配置。
- 这会导致 `uv sync` 只安装第三方依赖，不安装当前项目本身；随后 `uv run python -m trms_backend` 的 `sys.path` 里没有 `src/`，模块导入必然失败。

### 修改文件
- `TASKS.md`
- `WORKLOG.md`
- `pyproject.toml`
- `uv.lock`
- `web/src/test/setup.ts`

### 验证结果
- 已通过：
  - `uv sync`
    - 当前项目已成功构建并安装为 `trms==0.1.0`
  - `uv run python -c "import trms_backend, trms_cli; ..."`
    - `trms_backend` 与 `trms_cli` 导入通过
  - `uv run python -m trms_backend --help`
    - 后端模块入口可正常解析并显示帮助信息
  - `uv run python -m trms_cli --help`
    - CLI 模块入口可正常解析并显示帮助信息
  - `cd web && npm test -- src/lib/api/trms.test.ts`
    - 3 个测试通过
  - `cd web && npm test -- src/app/admin-task-list.test.tsx`
    - 4 个测试通过
  - `cd web && npm run lint && npm test && npm run build`
    - 前端 lint、测试、构建通过
  - `env UV_CACHE_DIR=/home/gsh/.cache/uv ./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic 临时 SQLite 迁移校验通过：`upgrade head -> downgrade base -> upgrade head`
    - `pytest` 316 个用例通过
    - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过
    - 前端测试共 20 个测试文件、59 个测试通过
    - Docker Compose 配置检查通过
    - `git diff --check` 通过

### 备注
- `pytest` 期间仍有 3 条既有 `DeprecationWarning`，来源于导出测试里的旧 `HTTP_422_UNPROCESSABLE_ENTITY` 常量；
- 前端测试期间仍打印 Node `--localstorage-file` 既有警告。
以上均为仓库已有现象，本轮未新增相关行为。

### 假设
- 当前保守假设：仓库短期内继续使用 `hatchling + src/` 作为最小打包方案即可，不需要为此额外引入更复杂的发布或 console script 配置。

## 2026-04-28 22:05 - Change default dev port to 9876 and add development env template

### 完成内容
- 修改默认开发端口：
  - `src/trms_backend/runtime_config.py` 的默认 API 端口从 `8000` 调整为 `9876`；
  - `src/trms_cli/cli.py` 的默认后端地址同步改为 `http://127.0.0.1:9876`；
  - `tests/test_runtime_config.py` 的开发默认值断言同步更新。
- 收口 `.env` 自动加载边界：
  - `src/trms_backend/runtime_config.py` 不再在通用配置加载阶段隐式读取根目录 `.env`，避免测试和纯模块导入被本地生产配置污染；
  - `src/trms_backend/__main__.py` 改为只在 `python -m trms_backend` / `python -m trms_backend worker` 入口合并根目录 `.env` 与当前进程环境变量；
  - 保留“本地直跑自动读取 `.env`”的行为，同时让 `pytest` 和直接 `import trms_backend.main` 继续使用显式传入配置或进程环境。
- 收口容器与部署默认端口：
  - 更新 `deploy/Dockerfile.api` 的 `EXPOSE` 和默认启动端口到 `9876`；
  - 更新 `deploy/reverse-proxy.nginx.conf` 的上游目标端口到 `9876`；
  - 更新 `deploy/docker-compose.yml` 的 API 健康检查端口到 `9876`；
  - 更新 `scripts/backup-restore-drill.sh` 生成的隔离环境变量模板，使其与新的默认端口一致。
- 补充开发环境模板：
  - 新增根目录 `.env.development.example`，覆盖本地 SQLite、本地材料目录、`9876` API 端口、`5173` 前端端口和本地联调用 `VITE_API_BASE_URL`；
  - 保留根目录 `.env.example` 作为部署 / 生产基线模板；
  - 更新 `.gitignore` 白名单，确保新的开发模板会被纳入版本控制。
- 更新文档：
  - `README.md` 明确区分生产模板 `.env.example` 与开发模板 `.env.development.example`；
  - 本地开发默认 `TRMS_PUBLIC_API_BASE_URL` 和 `TRMS_API_PORT` 示例同步改为 `9876`；
  - 部署文档补充“本地开发优先使用开发模板”的说明。

### 根因
- 当前仓库虽然已经统一根目录 `.env` 入口，但默认开发端口仍是 `8000`，且这个值散落在后端默认值、CLI 默认地址、容器启动参数、反向代理和健康检查中。
- 如果只修改后端默认常量，不同步调整这些入口，最终会出现“本地直跑默认 9876，但 CLI、容器和代理仍默认 8000”的不一致状态，开发联调和部署自检都会产生假故障。
- 同时，仓库当前根目录已有一份部署型 `.env`；如果在通用配置加载函数里全局隐式读取 `.env`，`pytest` 导入 `trms_backend.main` 时会直接吃到生产数据库连接串，导致测试阶段错误连向不存在的 `postgres` 主机。

### 修改文件
- `.env.development.example`
- `.env.example`
- `.gitignore`
- `README.md`
- `TASKS.md`
- `WORKLOG.md`
- `deploy/Dockerfile.api`
- `deploy/docker-compose.yml`
- `deploy/reverse-proxy.nginx.conf`
- `docs/生产部署清单与Docker Compose基线.md`
- `scripts/backup-restore-drill.sh`
- `src/trms_backend/runtime_config.py`
- `src/trms_backend/__main__.py`
- `src/trms_cli/cli.py`
- `tests/test_runtime_config.py`

### 验证结果
- 已通过：
  - `uv run pytest tests/test_runtime_config.py tests/test_health_api.py`
    - 18 个测试通过
  - `uv run pytest tests/test_async_jobs.py tests/test_cli_login.py tests/test_runtime_config.py`
    - 26 个测试通过
  - `env UV_CACHE_DIR=/home/gsh/.cache/uv ./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic 临时 SQLite 迁移校验通过：`upgrade head -> downgrade base -> upgrade head`
    - `pytest` 316 个用例通过
    - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过
    - 前端测试共 20 个测试文件、59 个测试通过
    - Docker Compose 配置检查通过
    - `git diff --check` 通过
- 备注：
  - 调整 `.env` 自动加载边界前，曾因根目录现有部署型 `.env` 被测试导入阶段误读取，触发对 `postgres` 主机的错误连接；本轮已通过把 `.env` 合并收口到 `python -m trms_backend` / `worker` 入口修复该问题；
  - `pytest` 期间仍有 3 条既有 `DeprecationWarning`，来源于导出测试里的旧 `HTTP_422_UNPROCESSABLE_ENTITY` 常量；
  - 前端测试期间仍打印 Node `--localstorage-file` 既有警告。
  以上后两项均为仓库已有现象，本轮未新增相关行为。

### 假设
- 当前保守假设：用户要求的“开发环境 `.env.example`”是新增一份本地开发专用模板，而不是替换现有部署模板，因此本轮采用 `.env.development.example` 命名并保留原 `.env.example` 作为部署基线。

## 2026-04-28 21:10 - Unify root .env configuration entry

### 完成内容
- 收口后端配置入口：
  - 修改 `src/trms_backend/runtime_config.py`，当调用方未显式传入 `env` 时，默认先读取仓库根目录 `.env`，再用当前进程环境变量覆盖；
  - 支持最小 `.env` 语法：空行、注释、`export KEY=...`、单/双引号值；
  - 保持现有显式参数和 shell 环境变量优先级，不把 `.env` 变成无法覆盖的硬编码来源。
- 收口前端配置入口：
  - 修改 `web/vite.config.ts`，把 Vite 的 `envDir` 指向仓库根目录；
  - `npm run dev` / `npm run build` 现在会和后端、Compose 一样，从根目录 `.env` 读取 `TRMS_WEB_*` 与 `VITE_*` 变量，而不是只看 `web/.env`。
- 补齐统一配置模板和文档：
  - 更新根目录 `.env.example`，补入 `TRMS_WEB_HOST`、`TRMS_WEB_PORT`；
  - 更新 `README.md` 和 `docs/生产部署清单与Docker Compose基线.md`，明确根目录 `.env` 是统一配置文件，且显式环境变量优先。
- 补充测试：
  - `tests/test_runtime_config.py` 新增 `.env` 读取与“进程环境变量覆盖 `.env`”的回归测试。

### 根因
- 仓库虽然已经有根目录 `.env.example`，但配置入口并未真正统一：
  - Docker Compose 文档使用根目录 `.env`；
  - 后端 `uv run python -m trms_backend` / `worker` 只读取进程环境变量，不会主动加载 `.env`；
  - Vite 默认按 `web/` 目录找 `.env`，导致前端开发配置和仓库根目录模板脱节。
- 这会让“复制 `.env.example` 到 `.env`”只在部分场景生效，用户必须记住不同入口各自去哪读配置，和当前仓库已经提供的统一模板相冲突。

### 修改文件
- `.env.example`
- `README.md`
- `TASKS.md`
- `WORKLOG.md`
- `docs/生产部署清单与Docker Compose基线.md`
- `src/trms_backend/runtime_config.py`
- `tests/test_runtime_config.py`
- `web/vite.config.ts`

### 验证结果
- 已通过：
  - `uv run pytest tests/test_runtime_config.py`
    - 17 个测试通过
  - `env UV_CACHE_DIR=/home/gsh/.cache/uv ./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic 临时 SQLite 迁移校验通过：`upgrade head -> downgrade base -> upgrade head`
    - `pytest` 316 个用例通过
    - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过
    - 前端测试共 20 个测试文件、59 个测试通过
    - Docker Compose 配置检查通过
    - `git diff --check` 通过
- 备注：
  - `pytest` 期间仍有 3 条既有 `DeprecationWarning`，来源于导出测试里的旧 `HTTP_422_UNPROCESSABLE_ENTITY` 常量；
  - 前端测试期间仍打印 Node `--localstorage-file` 既有警告。
  以上均为仓库已有现象，本轮未新增相关行为。

### 假设
- 当前保守假设：根目录 `.env.example` 继续作为仓库内唯一配置模板，具体部署环境仍可在复制为 `.env` 后按场景改成开发或生产值，而不是再拆出第二套前端或后端专用模板。

## 2026-04-28 20:36 - Refine web dashboards and user-facing copy

### 完成内容
- 重构前端工作台壳层与首页信息架构：
  - 新增 [web/src/components/dashboard.tsx](web/src/components/dashboard.tsx)，统一 `PageHeader`、`StatCard`、`SectionCard`、`StatusBadge`、`EmptyState`、`RoleWorkspace`、`TaskTable`；
  - 重写 [web/src/app/pages.tsx](web/src/app/pages.tsx) 与 [web/src/styles.css](web/src/styles.css)，把原来的宣传式 Hero 改成紧凑导航、后台页头、统计卡片和任务主工作区；
  - 新增 [web/src/app/system-admin-dashboard.tsx](web/src/app/system-admin-dashboard.tsx)，让系统管理员默认看到配置、角色、系统状态与审计入口，而不是占位说明。
- 建立统一业务文案映射层：
  - 新增 [web/src/lib/ui-text.ts](web/src/lib/ui-text.ts)，统一角色、任务状态、材料类型、费用类型、识别状态、校验级别、字段名和常见后端错误的业务文案映射；
  - [web/src/components/ApiErrorNotice.tsx](web/src/components/ApiErrorNotice.tsx) 改为通过统一 `ErrorMessage` 组件输出用户可执行提示，不再显示 `HTTP`、`API Error` 等开发者视角文案。
- 重构管理员与成员主工作台：
  - [web/src/app/admin-task-list.tsx](web/src/app/admin-task-list.tsx) 改成“统计卡片 + 筛选区 + 任务表格”为主视觉；
  - [web/src/app/member-task-list.tsx](web/src/app/member-task-list.tsx) 改成“我的报销任务”表格视图，突出截止时间与下一步动作；
  - [web/src/app/auth.tsx](web/src/app/role-routes.tsx) 更新登录页、角色入口和角色错配提示，统一为业务语言。
- 清理多处普通业务页中的技术暴露文案：
  - 已修改 [web/src/app/admin-task-detail.tsx](web/src/app/admin-task-detail.tsx)、[web/src/app/admin-review-overview.tsx](web/src/app/admin-review-overview.tsx)、[web/src/app/admin-export-tasks.tsx](web/src/app/admin-export-tasks.tsx)、[web/src/app/admin-invoice-editor.tsx](web/src/app/admin-invoice-editor.tsx)、[web/src/app/member-material-upload.tsx](web/src/app/member-material-upload.tsx)、[web/src/app/member-material-status.tsx](web/src/app/member-material-status.tsx)、[web/src/app/member-expense-confirmation.tsx](web/src/app/member-expense-confirmation.tsx)、[web/src/app/task-missing-materials.tsx](web/src/app/task-missing-materials.tsx) 等页面的显性技术文案。

### 根因
- 当前前端的核心问题不是“少几个颜色或卡片”，而是信息架构从一开始就站在开发者视角：首页像宣传页，后台页像边界说明文档，任务表格不在视觉中心，普通用户还能直接看到 API、路径、字段名和内部状态术语。
- 如果只做局部样式修补，任务列表仍然不会成为后台主工作区，且技术化文案会继续污染成员和管理员界面，因此本轮必须同时收口布局层、设计系统组件和统一文案映射层。

### 修改文件
- `TASKS.md`
- `web/src/app/App.test.tsx`
- `web/src/app/admin-corrections-reminders.test.tsx`
- `web/src/app/admin-corrections-reminders.tsx`
- `web/src/app/admin-export-tasks.test.tsx`
- `web/src/app/admin-export-tasks.tsx`
- `web/src/app/admin-invoice-editor.test.tsx`
- `web/src/app/admin-invoice-editor.tsx`
- `web/src/app/admin-review-overview.test.tsx`
- `web/src/app/admin-review-overview.tsx`
- `web/src/app/admin-split-editor.test.tsx`
- `web/src/app/admin-split-editor.tsx`
- `web/src/app/admin-task-create.test.tsx`
- `web/src/app/admin-task-create.tsx`
- `web/src/app/admin-task-detail.test.tsx`
- `web/src/app/admin-task-detail.tsx`
- `web/src/app/admin-task-list.test.tsx`
- `web/src/app/admin-task-list.tsx`
- `web/src/app/auth.tsx`
- `web/src/app/main-flow-e2e-placeholder.test.tsx`
- `web/src/app/member-expense-confirmation.test.tsx`
- `web/src/app/member-expense-confirmation.tsx`
- `web/src/app/member-material-status.test.tsx`
- `web/src/app/member-material-status.tsx`
- `web/src/app/member-material-upload.test.tsx`
- `web/src/app/member-material-upload.tsx`
- `web/src/app/member-task-list.test.tsx`
- `web/src/app/member-task-list.tsx`
- `web/src/app/pages.tsx`
- `web/src/app/permission-visibility.test.tsx`
- `web/src/app/role-routes.tsx`
- `web/src/app/routes.tsx`
- `web/src/app/system-admin-dashboard.tsx`
- `web/src/app/task-missing-materials.tsx`
- `web/src/components/ApiErrorNotice.test.tsx`
- `web/src/components/ApiErrorNotice.tsx`
- `web/src/components/RoleShell.tsx`
- `web/src/components/dashboard.tsx`
- `web/src/lib/api/client.test.ts`
- `web/src/lib/api/errors.ts`
- `web/src/lib/ui-text.ts`
- `web/src/styles.css`

### 验证结果
- 已通过：
  - `env UV_CACHE_DIR=/home/gsh/.cache/uv ./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic 临时 SQLite 迁移校验通过：`upgrade head -> downgrade base -> upgrade head`
    - `pytest` 314 个用例通过
    - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过
    - 前端测试共 20 个测试文件、59 个测试通过
    - Docker Compose 配置检查通过
    - `git diff --check` 通过
- 额外说明：
  - 本轮在 full access 环境下改用用户目录 `UV_CACHE_DIR=/home/gsh/.cache/uv` 后，根目录 `verify.sh` 已稳定跑完整套验证；
  - 修复过程中补删了 [web/src/app/member-task-list.tsx](web/src/app/member-task-list.tsx) 与 [web/src/app/pages.tsx](web/src/app/pages.tsx) 末尾多余空行，以消除 `git diff --check` 的尾部空白报错；
  - 新增 `.gitignore` 规则忽略本地 `data/` 材料目录和 `*.tsbuildinfo` 构建缓存，避免把本地产物带入工作树。
  - `pytest` 期间仍有 3 条既有 `DeprecationWarning`，来源于导出测试里的旧 `HTTP_422_UNPROCESSABLE_ENTITY` 常量；
  - 前端测试期间仍打印 Node `--localstorage-file` 既有警告。
  以上均为仓库已有现象，本轮未新增相关行为。

### 假设
- 当前保守假设：成员学号/成员编号仍是业务上可识别的身份信息，因此在管理员页里可以显示为“成员 2250001”一类标签，但不再暴露 `member_id`、`administrator_id` 等字段名。
- 当前保守假设：部分导出预览仍以结构化文本展示是可接受的第一阶段边界，但界面文案必须改成“在线预览/草稿预览”，不能把 `JSON`、`API 输出` 直接当成业务页面标题。

## 2026-04-28 20:05 - Add backup and recovery strategy notes

### 完成内容
- 新增 [docs/备份与恢复策略说明.md](docs/备份与恢复策略说明.md)，明确当前第一阶段部署基线下的备份与恢复边界：
  - PostgreSQL 需要至少保留逻辑备份和存储级快照两类能力；
  - S3 兼容对象存储需要覆盖原始材料、导出产物和识别中间文件，并建议启用版本管理或周期镜像；
  - 原始材料恢复优先级高于可再生成的导出产物，不能只备份 `_exports/` 前缀。
- 在策略文档中补充了基于当前 `deploy/docker-compose.yml` 的参考命令边界：
  - 使用 `pg_dump -Fc` 执行 PostgreSQL 逻辑备份；
  - 使用 `mc mirror` 作为 MinIO / S3 兼容对象存储镜像的参考方案；
  - 明确这些命令仅为建议，不代表仓库已内置自动化调度。
- 更新 `README.md` 增加策略文档入口，避免部署文档与恢复策略分散后不可见。

### 根因
- 架构文档已经要求 PostgreSQL、对象存储和原始材料具备备份机制，并明确“上线前需要恢复演练”，但仓库里此前只有零散的迁移和部署说明，没有单独的恢复策略文档。
- 如果继续保持现状，后续代理或运维人员只能从部署文档里看到“删卷前先备份”这类弱提示，无法明确知道该备份什么、优先级如何排序、以及为什么恢复演练仍是上线阻断项。

### 修改文件
- `README.md`
- `TASKS.md`
- `WORKLOG.md`
- `docs/备份与恢复策略说明.md`

### 验证结果
- 已通过：
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic 临时 SQLite 迁移校验通过：`upgrade head -> downgrade base -> upgrade head`
    - `pytest` 314 个用例通过
    - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过
    - 前端测试共 20 个测试文件、59 个测试通过
    - Docker Compose 配置检查通过
    - `git diff --check` 通过
- 备注：
  - `pytest` 期间仍有 3 条既有 `DeprecationWarning`，来源于导出测试里的旧 `HTTP_422_UNPROCESSABLE_ENTITY` 常量；
  - 前端测试期间仍打印 Node `--localstorage-file` 既有警告。
  以上均为仓库已有现象，本轮未新增相关行为。

### 假设
- 当前保守假设：第一阶段生产部署继续以 PostgreSQL + S3 兼容对象存储为正式持久化边界，因此恢复策略不再为生产环境设计本地目录备份方案。
- 当前保守假设：导出产物虽然理论上可再生成，但在恢复演练里仍应抽样验证其可读性，避免数据库元数据恢复后下载链路仍然失效。

## 2026-04-28 19:24 - Add baseline metrics boundaries

### 完成内容
- 为后端增加零依赖指标收集边界：
  - 新增 `src/trms_backend/application/metrics.py`，定义 `MetricsCollector` 协议、`NoOpMetricsCollector` 和 `InMemoryMetricsCollector`；
  - 当前快照聚合四类基础指标：上传成功/失败与成功率、识别任务状态、校验失败/待确认规则分布、导出任务状态；
  - `create_app()` 与 worker 入口统一注入同一类指标收集器，并把实例挂到 `app.state.metrics_collector`，为后续 `/metrics` 接口或外部适配器保留扩展点。
- 将指标接入四条稳定业务边界：
  - `MaterialSubmissionService` 记录逐文件上传成功/失败，并在识别占位任务创建时记录 `pending`；
  - `RecognitionPreparationService`、识别任务管理 API 和异步识别处理器记录识别状态变更，并在校验刷新时透传指标收集器；
  - `refresh_invoice_validations()` 与发票人工录入路径记录校验失败类型和待确认类型分布；
  - 导出任务创建、worker `running/succeeded/failed` 状态变化和手动状态更新统一记录导出状态指标。
- 补充测试：
  - `tests/test_material_submission_service.py` 覆盖上传成功、上传失败与识别占位指标；
  - `tests/test_async_jobs.py` 覆盖导出状态指标接线；
  - 新增 `tests/test_metrics.py`，通过应用实例验证上传、校验和导出指标快照。

### 根因
- 当前仓库已经有日志、审计和 request id 边界，但仍缺少最基础的指标抽象，导致上传、识别、校验和导出这些关键链路只能靠数据库和日志事后排查。
- 如果直接在业务代码里散落第三方监控 SDK，不但会把当前第一阶段单体实现绑死在具体监控产品上，还会把“事件采集”和“指标导出”两类职责混在一起，增加后续替换成本。

### 修改文件
- `TASKS.md`
- `WORKLOG.md`
- `src/trms_backend/__main__.py`
- `src/trms_backend/api/exports.py`
- `src/trms_backend/api/invoice_validation_refresh.py`
- `src/trms_backend/api/invoices.py`
- `src/trms_backend/api/recognitions.py`
- `src/trms_backend/application/export_async_jobs.py`
- `src/trms_backend/application/material_submission.py`
- `src/trms_backend/application/metrics.py`
- `src/trms_backend/application/recognition_async_jobs.py`
- `src/trms_backend/application/recognition_preparation.py`
- `src/trms_backend/main.py`
- `tests/test_async_jobs.py`
- `tests/test_material_submission_service.py`
- `tests/test_metrics.py`

### 验证结果
- 已通过：
  - `uv run pytest tests/test_material_submission_service.py tests/test_async_jobs.py tests/test_metrics.py`
    - 10 个测试通过
  - `uv run pytest tests/test_recognition_async_jobs.py tests/test_export_async_jobs.py tests/test_invoices_api.py tests/test_recognition_tasks_api.py`
    - 49 个测试通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic 临时 SQLite 迁移校验通过：`upgrade head -> downgrade base -> upgrade head`
    - `pytest` 314 个用例通过
    - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过
    - 前端测试共 20 个测试文件、59 个测试通过
    - Docker Compose 配置检查通过
    - `git diff --check` 通过
- 备注：
  - `pytest` 期间仍有 3 条既有 `DeprecationWarning`，来源于导出测试里的旧 `HTTP_422_UNPROCESSABLE_ENTITY` 常量；
  - 前端测试期间仍打印 Node `--localstorage-file` 既有警告。
  以上均为仓库已有现象，本轮未新增相关行为。

### 假设
- 当前保守假设：第一阶段指标先统计“事件计数”而不是实时数据库快照，因此重复重试会累计到对应状态计数中；如果后续需要稳定 gauge，应在独立导出层基于仓储查询实现，而不是把聚合逻辑塞回业务服务。
- 当前保守假设：内存指标收集器仅用于建立统一调用边界和本地可验证快照，不承担跨进程汇总职责；后续若接入 Prometheus/OpenTelemetry，应优先实现新的 `MetricsCollector` 适配器，而不是改动现有业务调用点。

## 2026-04-28 19:00 - Add sensitive log redaction rules

### 完成内容
- 为普通日志场景补齐统一脱敏辅助：
  - 新增 `src/trms_backend/logging_safety.py`，集中处理敏感键、Bearer token、文件 URL 和本地路径的日志脱敏；
  - 对 `telegram_bot_token`、`oauth_*_secret`、`mail_password`、`authorization=Bearer ...` 等键值或文本片段统一输出 `[redacted]`；
  - 对 `artifact_url`、`download_url` 等文件 URL 仅保留协议和主机，路径统一替换为 `[redacted-path]`；
  - 对 `root_dir`、`storage_path` 一类本地路径统一替换为 `[redacted-path]`。
- 将 `src/trms_backend/runtime_config.py` 中现有各类 `to_safe_log_fields()` 收口到同一辅助函数：
  - 保留 LLM base URL、S3 endpoint、bucket、模式等非敏感配置；
  - 继续显式隐藏 API key、bootstrap token、S3 access key / secret；
  - 新增 `RuntimeConfig.to_safe_log_fields()`，为后续启动日志或错误日志提供统一安全序列化入口。
- 补充回归测试：
  - 新增 `tests/test_logging_safety.py`，覆盖 secret、Bearer token、文件 URL 和本地路径脱敏；
  - `tests/test_runtime_config.py` 新增本地存储根目录和嵌套配置脱敏断言。

### 根因
- 仓库此前只有零散的“安全日志字段”实现，主要覆盖 API key、bootstrap token 和 S3 凭据，没有统一普通日志脱敏入口。
- 这种分散实现会留下两个问题：
  - 本地材料目录等路径仍可能以明文形式进入日志；
  - 后续若新增日志字段或直接记录文本消息，容易遗漏 Telegram Bot Token、邮件密码、Bearer token 等敏感值。

### 修改文件
- `TASKS.md`
- `WORKLOG.md`
- `src/trms_backend/logging_safety.py`
- `src/trms_backend/runtime_config.py`
- `tests/test_logging_safety.py`
- `tests/test_runtime_config.py`

### 验证结果
- 已通过：
  - `uv run pytest tests/test_logging_safety.py tests/test_runtime_config.py`
    - 17 个测试通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic 临时 SQLite 迁移校验通过：`upgrade head -> downgrade base -> upgrade head`
    - `pytest` 310 个用例通过
    - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过
    - 前端测试共 20 个测试文件、59 个测试通过
    - Docker Compose 配置检查通过
    - `git diff --check` 通过
- 备注：
  - `pytest` 期间仍有 3 条既有 `DeprecationWarning`，来源于导出测试里的旧 `HTTP_422_UNPROCESSABLE_ENTITY` 常量；
  - 前端测试期间仍打印 Node `--localstorage-file` 既有警告。
  以上均为仓库已有现象，本轮未新增相关行为。

### 假设
- 当前保守假设：对文件 URL 的日志脱敏只保留协议和主机，完整路径、query 和 fragment 一律不进入日志；这样既能区分存储来源，也不会泄露对象 key、签名参数或下载路径。
- 当前保守假设：本地路径在日志中统一折叠为 `[redacted-path]`，不保留目录层级或文件名；若未来排障确实需要更细粒度路径信息，应单独设计受控白名单字段，而不是在通用日志里放开明文路径。

## 2026-04-28 18:52 - Record export job and download audit logs

### 完成内容
- 为导出任务链路补齐统一审计：
  - 新增 `src/trms_backend/application/export_audit.py`，集中序列化导出任务创建、终态和产物下载三类审计明细；
  - `src/trms_backend/api/exports.py` 的 `POST /api/tasks/{task_id}/exports` 在成功创建导出任务后写入 `create_task_export_job` 审计；
  - `src/trms_backend/api/exports.py` 的 `GET /api/tasks/exports/{export_job_id}/artifact` 在成功下载导出产物后写入 `download_task_export_artifact` 审计；
  - `src/trms_backend/application/export_async_jobs.py` 的 worker 在导出任务成功或失败收敛到终态时，分别写入 `complete_task_export_job` / `fail_task_export_job` 审计；
  - `src/trms_backend/api/exports.py` 的手动状态更新接口也会在任务被显式置为 `succeeded` 或 `failed` 时复用同一终态审计辅助函数。
- 补充导出审计回归测试：
  - `tests/test_export_async_jobs.py` 断言创建、worker 成功、下载三类审计都会落库，且不暴露 `storage_key`；
  - `tests/test_export_async_jobs.py` 断言未实现的 `merged_pdf` 导出任务失败时会写入包含导出类型和失败原因的失败审计；
  - `tests/test_async_jobs.py` 跟进 `ExportAsyncJobProcessor` 新增的审计仓储依赖。

### 根因
- 导出能力虽然已经具备异步任务模型、状态查询和下载接口，但导出域仍未接入统一 `audit_logs`。
- 如果继续保持现状，就无法回答“谁创建了哪类导出任务、worker 为什么失败、谁下载了最终导出产物”，不满足需求文档与架构文档对敏感导出操作可追溯的要求。

### 修改文件
- `TASKS.md`
- `WORKLOG.md`
- `src/trms_backend/__main__.py`
- `src/trms_backend/api/exports.py`
- `src/trms_backend/application/export_async_jobs.py`
- `src/trms_backend/application/export_audit.py`
- `src/trms_backend/main.py`
- `tests/test_async_jobs.py`
- `tests/test_export_async_jobs.py`

### 验证结果
- 已通过：
  - `uv run pytest tests/test_export_async_jobs.py tests/test_async_jobs.py`
    - 10 个测试通过
  - `uv run pytest tests/test_exports_api.py -k 'export'`
    - 21 个测试通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic 临时 SQLite 迁移校验通过：`upgrade head -> downgrade base -> upgrade head`
    - `pytest` 306 个用例通过
    - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过
    - 前端测试共 20 个测试文件、59 个测试通过
    - Docker Compose 配置检查通过
    - `git diff --check` 通过
- 备注：
  - `pytest` 期间仍有 3 条既有 `DeprecationWarning`，来源于导出测试里的旧 `HTTP_422_UNPROCESSABLE_ENTITY` 常量；
  - 前端测试期间仍打印 Node `--localstorage-file` 既有警告。
  以上均为仓库已有现象，本轮未新增相关行为。

### 假设
- 当前保守假设：导出审计对象统一记录为 `export_job`，以便围绕异步任务主键串联“创建 -> 终态 -> 下载”的完整链路；同步导出占位接口仍不额外写入审计，避免和异步导出任务重复记账。
- 当前保守假设：审计中记录导出产物的文件名、类型、大小和哈希已足够满足追溯需求，因此不记录 `artifact_storage_key`、下载 URL 或任何长期访问凭证，避免泄露本地路径或存储实现细节。

## 2026-04-28 18:49 - Record split and confirmation audit logs

### 完成内容
- 为费用分摊与成员确认主链路补齐统一审计：
  - 新增 `src/trms_backend/application/expense_audit.py`，集中序列化“分摊替换”“成员确认/异议”“管理员处理异议恢复为 pending”三类审计明细；
  - `src/trms_backend/api/splits.py` 的 `PUT /api/invoices/{invoice_id}/splits` 现在会在成功替换分摊后写入 `replace_invoice_splits` 审计，按成员记录新增/删除/金额或备注变更前后差异；
  - `src/trms_backend/api/confirmations.py` 的 `PUT /api/splits/{split_id}/confirmation` 现在会分别写入 `confirm_expense_split`、`dispute_expense_split` 成功审计，并为默认禁止的代确认路径写入 `submit_split_confirmation` 拒绝审计；
  - `src/trms_backend/api/tasks.py` 的 `POST /api/tasks/{task_id}/expense-disputes/{split_id}/resolve` 现在会在管理员将异议恢复为 `pending` 时写入 `resolve_split_dispute` 审计。
- 补充回归测试：
  - `tests/test_splits_api.py` 断言分摊金额变更会生成包含 before/after 差异的发票级审计；
  - `tests/test_confirmations_api.py` 断言成员确认、成员异议与管理员代确认拒绝都会留下对应 split 审计；
  - `tests/test_expense_disputes_api.py` 断言管理员处理异议恢复 `pending` 会写入成功审计。

### 根因
- 统一 `audit_logs` 骨架已经落地，材料和识别相关动作也已接入审计，但费用分摊和成员确认这两条财务主链路仍直接修改业务仓储，不留下统一审计记录。
- 如果继续保持现状，就无法追溯“谁改了分摊金额、谁确认或提出了异议、管理员何时处理了异议”，不满足需求文档与架构文档对敏感金额操作可追溯的要求。

### 修改文件
- `TASKS.md`
- `WORKLOG.md`
- `src/trms_backend/api/confirmations.py`
- `src/trms_backend/api/splits.py`
- `src/trms_backend/api/tasks.py`
- `src/trms_backend/application/expense_audit.py`
- `src/trms_backend/main.py`
- `tests/test_confirmations_api.py`
- `tests/test_expense_disputes_api.py`
- `tests/test_splits_api.py`

### 验证结果
- 已通过：
  - `uv run pytest tests/test_splits_api.py tests/test_confirmations_api.py tests/test_expense_disputes_api.py`
    - 21 个测试通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic 临时 SQLite 迁移校验通过：`upgrade head -> downgrade base -> upgrade head`
    - `pytest` 306 个用例通过
    - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过
    - 前端测试共 20 个测试文件、59 个测试通过
    - Docker Compose 配置检查通过
    - `git diff --check` 通过
- 备注：
  - `pytest` 期间仍有 3 条既有 `DeprecationWarning`，来源于导出测试里的旧 `HTTP_422_UNPROCESSABLE_ENTITY` 常量；
  - 前端测试期间仍打印 Node `--localstorage-file` 既有警告。
  以上均为仓库已有现象，本轮未新增相关行为。

### 假设
- 当前保守假设：分摊替换属于发票级动作，因此审计对象记录为 `invoice`，并在 `detail.changed_splits` 中保存逐成员差异；成员确认、异议和异议处理仍以 `expense_split` 作为审计对象，便于按个人费用项追溯。
- 当前保守假设：第一阶段仍不存在“管理员代成员成功确认”的业务路径，因此本轮只为该默认拒绝路径落拒绝审计，而不新增任何代确认成功分支。

## 2026-04-28 18:21 - Record material deletion mark audit logs

### 完成内容
- 为材料删除标记接口补齐统一审计：
  - 在 `src/trms_backend/api/materials.py` 的 `POST /api/materials/{material_id}/deletion-mark` 接口新增 `mark_material_deleted` 审计写入；
  - 成功路径记录操作者、材料对象、任务 ID、请求 ID 和删除后的最小材料摘要；
  - 失败路径记录材料不存在、任务不存在、操作者越权、删除冲突，以及 bearer 身份与 `administrator_id` 不一致时的拒绝结果。
- 补充删除标记审计回归测试：
  - 成功删除后，断言同一材料存在 `submit_material -> mark_material_deleted` 两条审计；
  - 成员越权删除、主发票引用冲突、认证身份与请求体不一致三类失败路径均断言写入拒绝审计。

### 根因
- 上一轮已经建立了“材料删除标记”业务边界，但删除接口仍未接入统一审计仓储。
- 如果继续保持现状，管理员撤出材料主路径这一关键动作将无法回答“谁在什么时候删掉了哪份材料、是成功还是被拒绝”，不满足需求文档和架构文档对敏感材料操作可追溯的要求。

### 修改文件
- `TASKS.md`
- `WORKLOG.md`
- `src/trms_backend/api/materials.py`
- `tests/test_materials_api.py`

### 验证结果
- 已通过：
  - `uv run pytest tests/test_materials_api.py -k 'mark_material_deleted or mismatched_authenticated_administrator_id or primary_invoice_material_deleted'`
    - 4 个测试通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic 临时 SQLite 迁移校验通过：`upgrade head -> downgrade base -> upgrade head`
    - `pytest` 305 个用例通过
    - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过
    - 前端测试共 20 个测试文件、59 个测试通过
    - Docker Compose 配置检查通过
    - `git diff --check` 通过
- 备注：
  - `pytest` 期间仍有 3 条既有 `DeprecationWarning`，来源于导出测试里的旧 `HTTP_422_UNPROCESSABLE_ENTITY` 常量；
  - 前端测试期间仍打印 Node `--localstorage-file` 既有警告。
  以上均为仓库已有现象，本轮未新增相关行为。

### 假设
- 当前保守假设：未携带或携带无效 bearer token 的请求会在认证依赖层直接被 `401` 拒绝，因此本轮不额外为这类请求补写删除审计；此类失败仍可通过统一错误响应中的 `request_id` 追踪。

## 2026-04-28 18:14 - Establish material deletion mark boundary

### 完成内容
- 为材料域补齐最小软删除边界：
  - 在 `src/trms_backend/domain/materials.py` 新增 `deleted` 状态，并为仓储补充 `mark_deleted` 能力；
  - 新增 `src/trms_backend/application/material_deletion.py`，集中处理“材料存在性、任务归属、任务负责人权限、发票引用冲突”四类删除标记约束；
  - 在 `src/trms_backend/api/materials.py` 新增 `POST /api/materials/{material_id}/deletion-mark`，要求认证请求，并校验 `administrator_id` 与 bearer 身份一致。
- 收口删除标记的最小可见性与引用规则：
  - 删除标记后的材料不再出现在 `list_by_task` 及其复用的任务级材料列表/导出输入中；
  - 若材料已作为主发票材料，或已作为辅助材料挂到某张发票上，则拒绝删除标记，避免留下悬挂业务引用；
  - 删除标记不会物理删除材料记录，也不会删除原始文件。
- 补充回归测试：
  - 管理员可成功标记删除，且材料从任务列表中隐藏；
  - 原始文件仍保留在存储目录，数据库记录仍存在且状态变为 `deleted`；
  - 成员越权删除被 `403` 拒绝，匿名请求被 `401` 拒绝；
  - 已被主发票或辅助材料链路引用的材料删除被 `409` 拒绝。

### 根因
- 现有材料域只有 `assigned` / `pending_assignment` 两种状态，没有“误传后撤出主路径但保留追溯信息”的中间语义。
- 如果直接物理删除材料，会破坏架构文档要求的“原始上传文件不得被覆盖、关键操作可审计、材料可追溯”约束。
- 如果仅在 API 层临时屏蔽而不建立正式状态，又会让导出、复核、任务材料列表等复用 `list_by_task` 的路径继续把本应撤出的材料当作有效输入。

### 修改文件
- `TASKS.md`
- `WORKLOG.md`
- `src/trms_backend/api/materials.py`
- `src/trms_backend/application/material_deletion.py`
- `src/trms_backend/domain/materials.py`
- `src/trms_backend/infrastructure/repositories.py`
- `src/trms_backend/main.py`
- `tests/test_materials_api.py`

### 验证结果
- 已通过：
  - `uv run pytest tests/test_materials_api.py`
    - 27 个测试通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic 临时 SQLite 迁移校验通过：`upgrade head -> downgrade base -> upgrade head`
    - `pytest` 304 个用例通过
    - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过
    - 前端测试共 20 个测试文件、59 个测试通过
    - Docker Compose 配置检查通过
    - `git diff --check` 通过
- 备注：
  - `pytest` 期间仍有 3 条既有 `DeprecationWarning`，来源于导出测试里的旧 `HTTP_422_UNPROCESSABLE_ENTITY` 常量；
  - 前端测试期间仍打印 Node `--localstorage-file` 既有警告。
  以上均为仓库已有现象，本轮未新增相关行为。

### 假设
- 当前保守假设：第一阶段“材料删除”仅表现为任务内软删除标记，不提供物理删除、回收站恢复或跨任务迁移能力。
- 当前保守假设：只有任务负责人管理员可以标记已归属任务的材料删除；`pending_assignment` 材料的清理策略留给后续任务单独定义。
- 当前保守假设：删除标记后的材料主要从任务级主列表和导出输入中隐藏；按材料 ID 的识别历史等追溯路径暂不额外屏蔽，以便后续审计和恢复设计继续沿用现有记录。

## 2026-04-28 18:05 - Record material submission and claim audit logs

### 完成内容
- 为材料提交主链路接入统一审计：
  - `MaterialSubmissionService` 现在会在材料成功落库后，为每个材料写入 `submit_material` 审计日志；
  - 当批量上传出现校验失败时，会额外写入 `material_submission` 类型的拒绝审计，记录失败文件名、失败码和失败原因，但不记录文件内容。
- 为待归属材料认领接入统一审计：
  - `POST /api/materials/{material_id}/claim` 在成功认领时写入 `claim_pending_assignment` 审计；
  - 对材料不存在、状态不对、任务不存在、管理员越权、成员不属于任务等失败路径，也会写入失败或拒绝审计，保留失败原因。
- 将请求级 `request_id` 透传到 Web、邮件、Telegram 三类材料提交入口，保证审计记录可和现有统一错误响应/request id 机制关联。
- 补充最小测试覆盖：
  - `tests/test_materials_api.py` 断言直接材料提交会落成功审计；
  - `tests/test_materials_api.py` 断言待归属认领会落成功审计；
  - `tests/test_material_submission_service.py` 跟随构造参数更新，继续覆盖服务层主路径。

### 根因
- 上一轮虽然已经建立了统一 `audit_logs` 模型和脱敏骨架，但材料域最核心的两个动作仍未真正接入写入点：
  - 材料提交；
  - 待归属材料认领。
- 如果继续只保留骨架而不先打通这两条最常用路径，审计能力会停留在“有表无数据”，既无法追溯是谁上传了哪份材料，也无法追溯管理员何时把待归属材料认领进具体任务。

### 修改文件
- `TASKS.md`
- `WORKLOG.md`
- `src/trms_backend/api/email_materials.py`
- `src/trms_backend/api/materials.py`
- `src/trms_backend/api/telegram_materials.py`
- `src/trms_backend/application/email_material_submission.py`
- `src/trms_backend/application/material_submission.py`
- `src/trms_backend/application/telegram_material_submission.py`
- `src/trms_backend/main.py`
- `tests/test_material_submission_service.py`
- `tests/test_materials_api.py`

### 验证结果
- 已通过：
  - `uv run pytest tests/test_material_submission_service.py tests/test_materials_api.py`
    - 24 个测试通过
  - `uv run pytest tests/test_email_materials_api.py tests/test_telegram_materials_api.py`
    - 9 个测试通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic 临时 SQLite 迁移校验通过：`upgrade head -> downgrade base -> upgrade head`
    - `pytest` 299 个用例通过
    - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过
    - 前端测试共 20 个测试文件、59 个测试通过
    - Docker Compose 配置检查通过
    - `git diff --check` 通过
- 备注：
  - `pytest` 期间仍有 3 条既有 `DeprecationWarning`，来源于导出测试里的旧 `HTTP_422_UNPROCESSABLE_ENTITY` 常量；
  - 前端测试期间仍打印 Node `--localstorage-file` 既有警告。
  以上均为仓库已有现象，本轮未新增相关行为。

### 假设
- 当前保守假设：外部渠道的审计操作者优先记录为已解析出的成员 `member_id`；若尚未解析成功，则回退为 `email:<sender>`、`telegram_user_id:<id>` 或 `pending-assignment:<channel>` 这类最小可追溯标识，而不是阻塞提交流程去强行补齐统一外部账号主数据。
- 当前保守假设：上传失败时由于材料记录尚未创建，失败审计以 `material_submission` 作为对象类型记录请求级失败，而不是伪造一个不存在的材料 `material_id`。

## 2026-04-28 18:05 - Split oversized material audit task

### 完成内容
- 仅调整任务拆分，不修改业务代码：
  - 将 `TASKS.md` 中原本合并的“记录材料提交审计”拆为三个更小任务：
    - `记录材料提交和待归属认领审计`
    - `建立材料删除标记边界`
    - `记录材料删除标记审计`
  - 保持“首个未完成且未阻塞任务”仍落在材料审计域，但先把当前仓库已存在的上传/认领动作与尚未建模的“删除标记”动作分开处理。

### 根因
- 当前仓库已经存在两类可直接接入审计的材料动作：
  - 材料提交；
  - 待归属材料认领。
- 但“材料删除标记”在现有领域模型、应用服务和 API 中尚无独立边界；架构文档只要求必须审计该动作，并未留下现成实现可直接挂接。
- 如果继续把“提交/认领审计”和“删除标记能力 + 审计”绑在同一轮完成，就会被迫顺手设计新的删除业务语义、权限和可见性规则，超出“单轮一个最小可验证任务”的约束。

### 修改文件
- `TASKS.md`
- `WORKLOG.md`

### 验证结果
- 已通过：
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic 临时 SQLite 迁移校验通过：`upgrade head -> downgrade base -> upgrade head`
    - `pytest` 299 个用例通过
    - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过
    - 前端测试共 20 个测试文件、59 个测试通过
    - Docker Compose 配置检查通过
    - `git diff --check` 通过
- 备注：
  - `pytest` 期间仍有 3 条既有 `DeprecationWarning`，来源于导出测试里的旧 `HTTP_422_UNPROCESSABLE_ENTITY` 常量；
  - 前端测试期间仍打印 Node `--localstorage-file` 既有警告。
  以上均为仓库已有现象，本轮未新增相关行为。

### 假设
- 当前保守假设：材料删除在第一阶段应表现为“删除标记/软删除”而不是物理删除，以满足架构文档对原始材料可追溯和审计留痕的要求；具体字段、列表可见性和与发票关联的联动规则留待后续拆分任务单独实现。

## 2026-04-28 17:50 - Add audit log model skeleton

### 完成内容
- 为后续审计任务建立统一骨架：
  - 新增 `src/trms_backend/domain/audit_logs.py`，定义 `AuditLogCreate`、`AuditLogRecord`、`AuditLogRepository`，并提供最小内存仓储；
  - 审计模型统一记录 `actor_id`、`object_type`、`object_id`、`action`、`result`、`summary`、`detail`、`request_id` 和时间，满足“谁对什么做了什么，结果如何”的最小追溯要求；
  - 审计 `detail` 在进入模型时即做最小脱敏与截断，避免把 `password`、`token`、`secret`、`authorization`、完整文档内容或超长文本原样写入审计数据。
- 补齐持久化与迁移：
  - 在 `src/trms_backend/infrastructure/models.py` 新增 `AuditLogRow`；
  - 在 `src/trms_backend/infrastructure/repositories.py` 新增 `SqlAlchemyAuditLogRepository`，支持写入和按对象查询；
  - 新增 Alembic revision `20260428_03_audit_log_skeleton.py`，使生产迁移链与 `create_all` 路径一致。
- 补最小测试：
  - 新增 `tests/test_audit_logs.py`，覆盖敏感字段脱敏、长文本截断和 SQLAlchemy 持久化查询；
  - 更新 `tests/test_database_migrations.py`，验证本地自举和 Alembic head 都包含 `audit_logs` 表。

### 根因
- 当前仓库虽然已有导出任务记录、识别历史和用户注册来源等零散追溯信息，但不存在统一的审计日志模型。
- 如果继续等到各业务点逐个补日志再回头统一，会把字段命名、脱敏规则和查询边界散落到各模块，后续很容易形成彼此不兼容的“半审计”实现。
- 因此本轮先补统一骨架，把数据结构、最小脱敏规则和迁移链立住，再让后续“材料提交审计”“识别更正审计”“分摊确认审计”“导出下载审计”沿同一仓储扩展。

### 修改文件
- `TASKS.md`
- `WORKLOG.md`
- `alembic/versions/20260428_03_audit_log_skeleton.py`
- `src/trms_backend/domain/audit_logs.py`
- `src/trms_backend/infrastructure/models.py`
- `src/trms_backend/infrastructure/repositories.py`
- `tests/test_audit_logs.py`
- `tests/test_database_migrations.py`

### 验证结果
- 已通过：
  - `uv run pytest tests/test_audit_logs.py tests/test_database_migrations.py`
    - 5 个测试通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic 临时 SQLite 迁移校验通过：`upgrade head -> downgrade base -> upgrade head`
    - `pytest` 299 个用例通过
    - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过
    - 前端测试共 20 个测试文件、59 个测试通过
    - Docker Compose 配置检查通过
    - `git diff --check` 通过
- 备注：
  - `pytest` 期间仍有 3 条既有 `DeprecationWarning`，来源于导出测试里的旧 `HTTP_422_UNPROCESSABLE_ENTITY` 常量；
  - 前端测试期间仍打印 Node `--localstorage-file` 既有警告。
  以上均为仓库已有现象，本轮未新增相关行为。

### 假设
- 当前保守假设：审计摘要只保存简短操作摘要，结构化 `detail` 承担结果细节；若未来需要全文检索或更复杂检索条件，应单独扩展索引和查询接口，而不是在本轮提前扩散。
- 当前保守假设：本轮只建立审计数据模型和仓储，不把具体业务写入点一并接入；后续任务将分别把材料、识别、更正、分摊、确认和导出动作接到该仓储。

## 2026-04-28 17:40 - Standardize API error response payloads

### 完成内容
- 统一后端常见错误响应结构：
  - 新增 `src/trms_backend/api/error_responses.py`，为 `HTTPException` 和 `RequestValidationError` 提供统一 JSON 结构，包含 `code`、`message`、`detail`、`request_id`；
  - 在 `src/trms_backend/main.py` 请求入口生成 `request_id`，并通过 `X-Request-ID` 响应头回传；
  - `src/trms_backend/api/cli_compatibility.py` 的 `426 Upgrade Required` 响应也补齐 `message` 和 `request_id`，避免 CLI 门禁错误继续游离在统一格式之外。
- 调整测试断言语义：
  - 新增 `tests/test_api_error_responses.py` 和 `tests/api_error_assertions.py`，覆盖 400、403、404、409、422 的统一错误结构；
  - 将 `tests/test_auth_api.py`、`tests/test_tasks_api.py`、`tests/test_materials_api.py`、`tests/test_export_async_jobs.py`、`tests/test_cli_compatibility_api.py` 中的部分既有断言改为校验稳定错误码、`request_id` 和关键 `detail` 语义，而不是只盯整段文本。

### 根因
- 仓库此前的错误出口不一致：
  - 大多数路由直接透传 FastAPI 默认 `{"detail": ...}`；
  - CLI 版本门禁单独返回 `code + detail`；
  - 请求校验错误继续使用框架默认结构。
- 这导致同一类 API 失败在不同路径下无法稳定提供错误码和请求编号，测试也只能耦合到脆弱的整段 `detail` 文本，无法真正约束错误语义。

### 修改文件
- `TASKS.md`
- `WORKLOG.md`
- `src/trms_backend/api/cli_compatibility.py`
- `src/trms_backend/api/error_responses.py`
- `src/trms_backend/main.py`
- `tests/api_error_assertions.py`
- `tests/test_api_error_responses.py`
- `tests/test_auth_api.py`
- `tests/test_cli_compatibility_api.py`
- `tests/test_export_async_jobs.py`
- `tests/test_materials_api.py`
- `tests/test_tasks_api.py`

### 验证结果
- 已通过：
  - `uv run pytest tests/test_api_error_responses.py tests/test_auth_api.py tests/test_tasks_api.py tests/test_materials_api.py tests/test_export_async_jobs.py tests/test_cli_compatibility_api.py`
    - 84 个测试通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic 临时 SQLite 迁移校验通过：`upgrade head -> downgrade base -> upgrade head`
    - `pytest` 297 个用例通过
    - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过
    - 前端测试共 20 个测试文件、59 个测试通过
    - Docker Compose 配置检查通过
    - `git diff --check` 通过
- 备注：
  - `pytest` 期间仍有 3 条既有 `DeprecationWarning`，来源于导出测试里的旧 `HTTP_422_UNPROCESSABLE_ENTITY` 常量；
  - 前端测试期间仍打印 Node `--localstorage-file` 既有警告。
  以上均为仓库已有现象，本轮未新增相关行为。

### 假设
- 当前保守假设：统一错误响应格式先覆盖通用 HTTP/请求校验错误出口；邮件材料批量失败、材料批量上传部分成功等领域专用响应仍保留现有 `status` / `error_code` 结构，因为这些接口本身已承载批处理结果语义，不在本轮强行改成单一错误信封。
- 当前保守假设：`request_id` 先用于响应体与响应头透传，日志上下文绑定和全链路审计继续留给后续“建立请求 ID 日志上下文”和审计任务处理。

## 2026-04-28 17:30 - Add export artifact access control coverage

### 完成内容
- 仅补测试，不修改导出业务逻辑：
  - 在 `tests/test_export_async_jobs.py` 补充导出产物下载接口的访问控制覆盖；
  - 新增“负责人管理员可下载已生成导出文件、无关管理员 `403`、匿名请求 `401`”断言；
  - 在导出产物尚未生成的边界测试中补充成员直接访问下载接口会被 `403` 拒绝，避免只验证导出状态查询而遗漏真实文件下载路径。

### 根因
- 上一轮已经收口导出与异步作业接口的权限边界，但自动化测试仍缺一段关键闭环：
  - 已覆盖导出状态详情接口的匿名/成员拒绝；
  - 已覆盖负责人管理员能下载成功产物；
  - 但没有显式证明“下载接口本身”会拒绝成员和无关管理员。
- 这会让导出文件访问控制只停留在实现层推断，而不是由回归测试稳定约束。

### 修改文件
- `TASKS.md`
- `WORKLOG.md`
- `tests/test_export_async_jobs.py`

### 验证结果
- 已通过：
  - `uv run pytest tests/test_export_async_jobs.py tests/test_exports_api.py`
    - 25 个测试通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic 临时 SQLite 迁移校验通过：`upgrade head -> downgrade base -> upgrade head`
    - `pytest` 292 个用例通过
    - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过
    - 前端测试共 20 个测试文件、59 个测试通过
    - Docker Compose 配置检查通过
    - `git diff --check` 通过
- 备注：
  - `pytest` 期间仍有 3 条既有 `DeprecationWarning`，来源于导出测试中的旧 `HTTP_422_UNPROCESSABLE_ENTITY` 常量；
  - 前端测试期间仍打印 Node `--localstorage-file` 既有警告。
  以上均为仓库已有现象，本轮未新增相关行为。

### 假设
- 当前保守假设：第一阶段导出产物下载仍统一走管理员导出管理边界，不在本轮把成员可下载“与本人相关的导出子集”扩展为新需求；若后续需要更细粒度授权，应单独新增任务并补对应测试。

## 2026-04-28 17:24 - Close export and async job permission boundaries

### 完成内容
- 收口导出任务与导出文件访问边界：
  - `GET /api/tasks/{task_id}/exports/capabilities`、各类导出预览接口、`POST /api/tasks/{task_id}/exports`、`GET /api/tasks/{task_id}/exports`、`GET /api/tasks/exports/{export_job_id}`、`GET /api/tasks/exports/{export_job_id}/artifact`、`PATCH /api/tasks/exports/{export_job_id}/status` 全部改为必须消费 bearer 请求身份；
  - 导出任务详情、下载和状态更新不再接受匿名 `actor_id` 伪装，已认证请求仍可保留显式 `actor_id`，但与 bearer 身份不一致时会显式拒绝。
- 收口识别异步作业管理边界：
  - `POST /api/materials/{material_id}/recognition-tasks`、`PATCH /api/recognition-tasks/{recognition_task_id}/status`、`POST /api/recognition-tasks/{recognition_task_id}/execute` 改为要求已认证身份；
  - 对已归属任务的材料，上述识别任务管理接口只允许任务负责人执行；成员即使能查看本人材料识别历史，也不能自行重试、执行或改写识别任务状态。
- 补回归测试覆盖：
  - `tests/test_exports_api.py`、`tests/test_export_async_jobs.py` 新增导出路由 bearer 正向、匿名 `401` 和成员越权 `403` 覆盖；
  - `tests/test_recognition_tasks_api.py`、`tests/test_recognition_execution_api.py` 新增识别任务管理接口的管理员 bearer、匿名拒绝和成员越权覆盖；
  - 受影响的发票、复核汇总等测试统一切到管理员 bearer 调用新的识别任务管理接口。

### 根因
- 上一轮虽然已经收口了成员侧与管理员侧的任务/复核接口，但导出和异步作业接口仍残留两类旧边界：
  - 导出任务详情、下载和状态更新继续依赖裸 `actor_id` 查询参数或请求体字段，匿名请求仍可伪装任务负责人；
  - 识别任务的重试、执行和状态更新接口没有接入请求身份上下文，导致任何知道任务编号的人都可直接驱动异步作业状态。
- 这会使“只有任务负责人才能管理自己任务的导出和相关异步作业”在后端层面仍不成立。

### 修改文件
- `TASKS.md`
- `WORKLOG.md`
- `src/trms_backend/api/exports.py`
- `src/trms_backend/api/recognitions.py`
- `tests/test_export_async_jobs.py`
- `tests/test_exports_api.py`
- `tests/test_invoices_api.py`
- `tests/test_recognition_execution_api.py`
- `tests/test_recognition_tasks_api.py`
- `tests/test_task_review_summary_api.py`

### 验证结果
- 已通过：
  - `uv run pytest tests/test_exports_api.py tests/test_export_async_jobs.py tests/test_recognition_tasks_api.py tests/test_recognition_execution_api.py tests/test_invoices_api.py tests/test_task_review_summary_api.py`
    - 81 个测试通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic 临时 SQLite 迁移校验通过：`upgrade head -> downgrade base -> upgrade head`
    - `pytest` 291 个用例通过
    - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过
    - 前端测试共 20 个测试文件、59 个测试通过
    - Docker Compose 配置检查通过
    - `git diff --check` 通过
- 备注：
  - `pytest` 期间仍有 3 条既有 `DeprecationWarning`，来源于导出测试中的旧 `HTTP_422_UNPROCESSABLE_ENTITY` 常量；
  - 前端测试期间仍打印 Node `--localstorage-file` 既有警告。
  以上均为仓库已有现象，本轮未新增相关行为。

### 假设
- 当前保守假设：第一阶段识别任务的“管理者”仍以 `task.administrator_id` 对应的账号 `actor_id` 表达，不在本轮扩展为独立的异步作业管理员模型。
- 当前保守假设：对 `task_id` 仍为空的待归属材料，识别任务管理先仅开放给已认证 `admin` / `system_admin` 角色，避免成员通过材料编号直接驱动未归属异步作业；更细的待归属材料处理权限边界留待后续任务单独收口。

## 2026-04-28 17:15 - Close administrator task management and review permissions

### 完成内容
- 收口管理员侧 bearer 身份上下文与管理范围：
  - `GET /api/tasks` 在管理员 bearer 会话下默认只返回本人负责任务，避免后台任务列表继续暴露无关任务；
  - `GET /api/tasks/{task_id}`、`GET /api/tasks/{task_id}/members` 在已认证场景下开始校验任务访问范围，非任务负责人和非任务成员不再能读取无关任务详情；
  - `PUT /api/tasks/{task_id}/members`、`PATCH /api/tasks/{task_id}/status` 改为必须使用 bearer 身份上下文，匿名请求不再能直接伪装管理员修改任务。
- 收口管理员复核与提醒接口：
  - `POST/GET /api/tasks/{task_id}/automatic-reminder-tasks`、`POST/GET /api/tasks/{task_id}/material-reminders`、`GET /api/tasks/{task_id}/overdue-confirmations`、`GET /api/tasks/{task_id}/review-summary`、`GET /api/tasks/{task_id}/expense-disputes`、`POST /api/tasks/{task_id}/expense-disputes/{split_id}/resolve` 全部切到已认证请求身份；
  - 对仍保留显式 `actor_id` / `administrator_id` 的接口，bearer 身份与显式字段不一致时会显式拒绝，而不是继续按请求自报身份执行。
- 补管理员 bearer 越权回归测试：
  - `tests/test_web_bearer_request_identity_api.py` 新增管理员任务列表过滤、任务详情/成员详情、成员管理、状态流转、匿名拒绝和无关管理员拒绝覆盖；
  - 任务提醒、复核摘要、逾期确认、自动提醒、异议处理及其依赖测试统一切到 bearer 管理员或 bearer 成员场景，验证新边界不会回退到匿名旧契约。

### 根因
- 上一轮完成成员侧可见范围收口后，管理员侧仍残留两类权限缺口：
  - 一批任务管理接口完全没有接入请求身份上下文，例如成员管理、状态流转和部分任务详情读取；
  - 一批复核接口虽然接受 `actor_id` / `administrator_id`，但匿名请求仍可直接自报管理员身份执行。
- 这使得 bearer 登录虽然已经进入 Web 管理台，但后端仍没有真正保证“只有任务负责人才能管理该任务并执行复核动作”。

### 修改文件
- `TASKS.md`
- `WORKLOG.md`
- `src/trms_backend/api/tasks.py`
- `tests/test_automatic_reminder_tasks_api.py`
- `tests/test_email_materials_api.py`
- `tests/test_expense_details_api.py`
- `tests/test_expense_disputes_api.py`
- `tests/test_invoices_api.py`
- `tests/test_material_storage.py`
- `tests/test_materials_api.py`
- `tests/test_missing_materials_api.py`
- `tests/test_overdue_confirmations_api.py`
- `tests/test_recognition_async_jobs.py`
- `tests/test_recognition_execution_api.py`
- `tests/test_recognition_tasks_api.py`
- `tests/test_task_member_status_api.py`
- `tests/test_task_review_summary_api.py`
- `tests/test_tasks_api.py`
- `tests/test_telegram_materials_api.py`
- `tests/test_web_bearer_request_identity_api.py`

### 验证结果
- 已通过：
  - `uv run pytest tests/test_tasks_api.py tests/test_web_bearer_request_identity_api.py tests/test_task_review_summary_api.py tests/test_overdue_confirmations_api.py tests/test_automatic_reminder_tasks_api.py tests/test_expense_disputes_api.py tests/test_task_member_status_api.py tests/test_missing_materials_api.py tests/test_expense_details_api.py`
    - 70 个测试通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic 临时 SQLite 迁移校验通过：`upgrade head -> downgrade base -> upgrade head`
    - `pytest` 288 个用例通过
    - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过
    - 前端测试共 20 个测试文件、59 个测试通过
    - Docker Compose 配置检查通过
    - `git diff --check` 通过
- 备注：
  - `pytest` 期间仍有 3 条既有 `DeprecationWarning`，来源于导出测试中的旧 `HTTP_422_UNPROCESSABLE_ENTITY` 常量；
  - 前端测试期间仍打印 Node `--localstorage-file` 既有警告。
  以上均为仓库已有现象，本轮未新增相关行为。

### 假设
- 当前保守假设：第一阶段 `task.administrator_id` 仍直接绑定账号 `actor_id`，因此管理员侧权限收口继续以“bearer 的 `actor_id` 必须等于任务负责人”表达，而不在本轮扩展到独立任务负责人实体。
- 当前保守假设：`GET /api/tasks/{task_id}` 与 `GET /api/tasks/{task_id}/members` 的匿名旧契约暂未整体移除；本轮只确保已认证请求不能越权读取无关任务，并优先收紧真正的管理员管理/复核写操作。

## 2026-04-28 16:56 - Close member-facing API identity and visibility scope

### 完成内容
- 收口成员侧 bearer 身份上下文与可见范围：
  - `GET /api/tasks` 在成员 bearer 会话下默认只返回本人可见任务，并在显式 `member_id` 与认证身份不一致时显式拒绝；
  - `GET /api/tasks/{task_id}/member-status` 改为统一消费请求身份上下文，在 bearer 成员场景下不再要求显式 `actor_id`；
  - `GET /api/tasks/{task_id}/materials`、`GET /api/tasks/{task_id}/invoices`、`GET /api/materials/{material_id}/recognition-tasks`、`GET /api/invoices/{invoice_id}/validations`、`GET /api/invoices/{invoice_id}/supporting-materials`、`GET /api/invoices/{invoice_id}/splits`、`GET /api/invoices/{invoice_id}/confirmations` 对已认证成员改为只暴露本人相关记录。
- 新增共享任务访问边界：
  - 新增 `src/trms_backend/api/request_task_access.py`，统一表达“匿名兼容 / 任务管理员 / 任务成员”三类访问范围；
  - 相关成员侧查询接口在 bearer 场景下共享该边界，避免继续在各路由内散落判断。
- 补成员侧 bearer 越权回归测试：
  - `tests/test_web_bearer_request_identity_api.py` 新增成员可见任务过滤、`submitter_id` / `actor_id` 不一致拒绝、只返回本人材料/发票/确认/分摊/附件摘要等测试。

### 根因
- 上一轮虽然已经把 Web 关键业务请求迁到 bearer token，但多个成员页面仍依赖“任务内全量列表接口 + 前端本地过滤”：
  - 成员任务列表先拉全量任务再按 `task.member_ids` 过滤；
  - 成员材料状态页会直接读取任务下全部材料、全部发票，再在前端裁剪本人数据；
  - 相关发票校验、识别历史、分摊和确认列表接口也没有真正按已认证成员收口。
- 这意味着 bearer 身份虽然已进入请求链路，但成员侧查询边界仍停留在调用方自觉过滤阶段，后端没有真正保证“成员只能访问本人相关材料、费用和确认记录”。

### 修改文件
- `TASKS.md`
- `WORKLOG.md`
- `src/trms_backend/api/confirmations.py`
- `src/trms_backend/api/invoices.py`
- `src/trms_backend/api/materials.py`
- `src/trms_backend/api/recognitions.py`
- `src/trms_backend/api/request_task_access.py`
- `src/trms_backend/api/splits.py`
- `src/trms_backend/api/tasks.py`
- `src/trms_backend/main.py`
- `tests/test_web_bearer_request_identity_api.py`

### 验证结果
- 已通过：
  - `uv run pytest tests/test_web_bearer_request_identity_api.py tests/test_materials_api.py tests/test_invoices_api.py tests/test_confirmations_api.py tests/test_task_member_status_api.py tests/test_missing_materials_api.py tests/test_splits_api.py`
    - 87 个测试通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic 临时 SQLite 迁移校验通过：`upgrade head -> downgrade base -> upgrade head`
    - `pytest` 286 个用例通过
    - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过
    - 前端测试共 20 个测试文件、59 个测试通过
    - Docker Compose 配置检查通过
    - `git diff --check` 通过
- 备注：
  - `pytest` 期间仍有 3 条既有 `DeprecationWarning`，来源于导出测试中的旧 `HTTP_422_UNPROCESSABLE_ENTITY` 常量；
  - 前端测试期间仍打印 Node `--localstorage-file` 既有警告。
  以上均为仓库已有现象，本轮未新增相关行为。

### 假设
- 当前保守假设继续成立：第一阶段任务成员语义仍主要绑定 `actor_id`，因此本轮“成员侧身份收口”仍按当前账号 `actor_id` 与任务成员编号对齐，而不提前把全链路重构为独立 `member_code` 主键语义。
- 当前保守假设：匿名旧契约和 CLI/Telegram/邮件的显式身份字段兼容边界暂时保留；本轮只对 bearer 成员场景补齐真正的后端可见范围约束。

## 2026-04-28 17:25 - Split basic permission control task

### 完成内容
- 仅调整任务边界，不修改业务代码：
  - 将 `TASKS.md` 中过大的“增加基础权限控制”拆成三个更小的后续任务：成员侧业务 API、管理员侧任务管理/复核、导出与异步作业权限边界；
  - 保留原任务的目标，但按当前代码实际耦合点切到更可验证的落点，避免下一轮同时改动匿名旧接口、CLI bearer 调用链、管理员管理路径和导出/识别作业路径；
  - 明确后续顺序：先收口成员侧可见范围，再收口管理员任务管理，最后收口导出和异步作业权限，为“导出文件访问控制测试”保留稳定前置条件。

### 根因
- 当前仓库虽然已经完成：
  - 用户名密码登录；
  - 统一 `RequestIdentity` 占位；
  - Web 关键业务路径的 bearer 透传与关键字段对齐。
- 但“基础权限控制”仍横跨多个尚未统一的边界：
  - 一批成员侧接口仍保留匿名 `actor_id` / `member_id` / `submitter_id` 旧契约；
  - 一批管理员侧任务管理与复核接口还没有统一接入请求身份上下文；
  - 导出任务、导出文件下载、识别/导出异步作业接口和后续测试又是另一组独立切片。
- 直接在一轮内完成原任务，会同时牵动后端多组路由、CLI 兼容调用和大量测试入口，超出“一个最小可验证任务”的边界。

### 修改文件
- `TASKS.md`
- `WORKLOG.md`

### 验证结果
- 已通过：
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic 临时 SQLite 迁移校验通过：`upgrade head -> downgrade base -> upgrade head`
    - `pytest` 283 个用例通过
    - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过
    - 前端测试共 20 个测试文件、59 个测试通过
    - Docker Compose 配置检查通过
    - `git diff --check` 通过
- 备注：
  - `pytest` 期间仍有 3 条既有 `DeprecationWarning`，来源于导出测试中的旧 `HTTP_422_UNPROCESSABLE_ENTITY` 常量；
  - 前端测试期间仍打印 Node `--localstorage-file` 既有警告。
  以上均为仓库已有现象，本轮未新增相关行为。

### 假设
- 当前保守假设：外部渠道接入（Telegram、邮件）仍维持其独立身份边界，本轮拆分只针对核心业务 API 的权限收口顺序，不在任务层面把渠道 webhook 直接并入 Web/CLI bearer 会话模型。
- 当前保守假设：`RequestIdentity` 的“需要身份上下文”先按“逐路由收口并比对 bearer 与显式身份字段”的方式推进；是否把所有匿名旧契约一次性移除，将在拆分后的子任务中分别处理并验证。

## 2026-04-28 16:38 - Migrate web business APIs to bearer request identity

### 完成内容
- 将 Web 业务请求迁到 bearer 身份上下文，同时保留非 Web 渠道兼容边界：
  - 新增 `src/trms_backend/api/request_identity_http.py`，统一把“请求自报 actor 字段”和 bearer token 身份做对齐，并在缺失或不一致时返回明确的 422 / 403；
  - `tasks`、`materials`、`invoices`、`splits`、`confirmations`、`exports` 路由在收到 bearer token 时优先解析当前用户，不再要求 Web 关键路径显式传 `actor_id`、`submitter_id`、`member_id`；
  - 路由仍保留匿名/非 Web 调用方显式传参的旧边界，没有把 CLI、Telegram、邮件接入器强行改成 Web 会话模型。
- 收口前端 bearer 透传与 mock 回退：
  - `web/src/lib/api/client.ts` 增加统一 access token provider，真实登录态下自动为业务请求附带 `Authorization: Bearer ...`；
  - `web/src/lib/api/trms.ts` 在检测到 bearer token 时，自动去掉关键请求里的 `actor_id` / `submitter_id` / `member_id`；若当前是无 token 的 mock 调试会话，则继续保留旧字段回退，避免把现有调试页直接改废；
  - `web/src/app/auth-store.ts` 将持久化登录态里的 access token 接入 API client。
- 增加 bearer 迁移回归测试：
  - 新增 `tests/test_web_bearer_request_identity_api.py`，覆盖成员上传、管理员复核摘要/补材料提醒、发票录入、分摊、成员确认、导出任务等 bearer 场景；
  - 新增 `web/src/lib/api/trms.test.ts`，校验前端在有 token 时剥离身份字段、无 token mock 会话时保留旧查询参数；
  - `web/src/lib/api/client.test.ts` 补充 access token 自动注入测试。

### 根因
- 仓库已经有用户名密码登录和 bearer token，但 Web 业务 API 仍大量依赖前端自报 `actor_id`、`submitter_id`、`member_id`，导致登录态存在却没有真正进入业务请求链路。
- 如果直接在各路由里散落地改参数解析，会继续复制身份判断逻辑；同时，当前任务成员语义仍主要绑定 `actor_id`，若不显式保留这层边界，简单把成员路径机械切到 `member_code` 会破坏现有成员任务主链路。

### 修改文件
- `TASKS.md`
- `WORKLOG.md`
- `src/trms_backend/api/confirmations.py`
- `src/trms_backend/api/exports.py`
- `src/trms_backend/api/invoices.py`
- `src/trms_backend/api/materials.py`
- `src/trms_backend/api/request_identity_http.py`
- `src/trms_backend/api/splits.py`
- `src/trms_backend/api/tasks.py`
- `src/trms_backend/main.py`
- `tests/test_web_bearer_request_identity_api.py`
- `web/src/app/auth-store.ts`
- `web/src/lib/api/client.test.ts`
- `web/src/lib/api/client.ts`
- `web/src/lib/api/trms.test.ts`
- `web/src/lib/api/trms.ts`

### 验证结果
- 已通过：
  - `uv run pytest tests/test_web_bearer_request_identity_api.py tests/test_materials_api.py tests/test_confirmations_api.py tests/test_exports_api.py`
    - 53 个测试通过
  - `cd web && npm test -- src/lib/api/client.test.ts src/lib/api/trms.test.ts`
    - 2 个前端测试文件、9 个测试通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic 临时 SQLite 迁移校验通过：`upgrade head -> downgrade base -> upgrade head`
    - `pytest` 283 个用例通过
    - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过
    - 前端测试共 20 个测试文件、59 个测试通过
    - Docker Compose 配置检查通过
    - `git diff --check` 通过
- 备注：
  - `pytest` 期间仍有 3 条既有 `DeprecationWarning`，来源于导出测试中的旧 `HTTP_422_UNPROCESSABLE_ENTITY` 常量；
  - 前端测试期间仍打印 Node `--localstorage-file` 既有警告。
  以上均为仓库已有现象，本轮未新增相关行为。

### 假设
- 当前保守假设：Web 成员关键路径里的“当前成员”仍以账号 `actor_id` 对齐任务成员与分摊成员，而不是在本轮同步重构为独立的 `member_code` 体系；后续若要把权限模型完全切到 `member_code`，需要先统一任务成员主键语义。
- 当前保守假设：无 token 的 mock 调试会话仍可继续通过旧字段访问现有调试页面，这只是开发过渡边界，不代表“基础权限控制”已经完成；下一任务仍应继续收口真正的业务鉴权要求。

## 2026-04-28 16:19 - Establish minimal request identity context placeholder

### 完成内容
- 建立统一请求身份上下文占位：
  - 新增 `src/trms_backend/api/request_identity.py`，统一解析 bearer token 并输出 `RequestIdentity`；
  - 上下文显式表达 `is_authenticated`、`source`、`role`、`actor_id`、`member_id` 和当前 `user`，为后续业务 API 迁移提供单一入口；
  - 对匿名请求保持显式 `anonymous` 状态，不把无 token 与无效 token 混为一谈。
- 收口认证路由对身份解析的重复实现：
  - `src/trms_backend/api/auth.py` 改为复用统一请求身份依赖；
  - 新增 `GET /api/auth/request-context`，用于稳定返回当前请求身份上下文；
  - `GET /api/auth/me` 与 `POST /api/auth/logout` 继续保持既有 bearer 行为，但不再各自维护独立 token 解析逻辑。
- 补迁移边界辅助函数与测试：
  - 新增 `resolve_actor_id_for_request()`、`resolve_member_id_for_request()`、`resolve_submitter_id_for_request()`；
  - 这些辅助函数用于后续将 Web 业务 API 从显式 `actor_id` / `member_id` / `submitter_id` 参数迁移到 bearer 身份上下文时，校验“请求自报身份”和“token 身份”是否一致；
  - 新增认证 API 和迁移辅助函数测试，覆盖匿名上下文、已认证上下文和不一致拒绝路径。

### 根因
- 当前仓库虽然已经有用户名密码登录、bearer token 和 `/api/auth/me`，但 bearer 解析逻辑只存在于认证路由内部，业务 API 没有可复用的统一请求身份入口。
- 同时，现有业务路径仍大量依赖调用方直接传 `actor_id`、`member_id` 或 `submitter_id`。如果不先建立统一上下文和迁移辅助边界，后续把 Web 业务 API 迁到 bearer 身份时只能在各路由内重复堆逻辑，容易继续扩散身份判断。

### 修改文件
- `TASKS.md`
- `WORKLOG.md`
- `src/trms_backend/api/auth.py`
- `src/trms_backend/api/request_identity.py`
- `tests/test_auth_api.py`
- `tests/test_request_identity.py`

### 验证结果
- 已通过：
  - `uv run pytest tests/test_auth_api.py tests/test_request_identity.py`
    - 16 个测试通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic 临时 SQLite 迁移校验通过：`upgrade head -> downgrade base -> upgrade head`
    - `pytest` 279 个用例通过
    - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过
    - 前端测试共 19 个测试文件、55 个测试通过
    - Docker Compose 配置检查通过
    - `git diff --check` 通过
- 备注：
  - `pytest` 期间仍有 3 条既有 `DeprecationWarning`，来源于导出测试中的旧 `HTTP_422_UNPROCESSABLE_ENTITY` 常量；
  - 前端测试期间仍打印 Node `--localstorage-file` 既有警告。
  以上均为仓库已有现象，本轮未新增相关行为。

### 假设
- 当前保守假设：请求身份上下文中的 `member_id` 暂时映射自账号模型里的 `member_code`，用于表达“当前登录成员编号”，而不是在本轮提前重构用户模型字段命名。
- 本轮只建立身份上下文和迁移辅助边界，不提前修改 Web 业务 API 的请求参数契约；下一任务仍应是把 Web 业务请求逐步迁到 bearer 身份上下文。

## 2026-04-28 16:05 - Split pre-launch security and recovery drill task

### 完成内容
- 仅调整任务拆分，不改动业务代码：
  - 将 `TASKS.md` 中过大的“完成上线前安全与恢复演练”拆成更小的可验证任务；
  - 保留当前回归与演练目标，但拆分为“备份恢复演练”“上线前安全回归验证”“主流程 E2E 演练并记录风险”等独立任务；
  - 保持这些演练任务排在其前置能力之后，避免后续代理在权限、日志脱敏、备份策略和 E2E 骨架尚未完成时错误宣称已经完成上线演练。

### 根因
- 原任务同时要求：
  - 权限越权、导出下载、日志脱敏、CORS 与生产注册策略回归；
  - 数据库与对象存储备份恢复演练；
  - 覆盖创建任务到导出的主流程 E2E 演练。
- 这些内容横跨权限收口、审计与可观测性、备份恢复策略和端到端测试，当前队列中已有多项前置任务尚未完成，包括：
  - `建立最小请求身份上下文占位`
  - `将 Web 业务 API 迁移到 bearer 身份上下文`
  - `增加基础权限控制`
  - `增加导出文件访问控制测试`
  - `增加敏感信息日志脱敏规则`
  - `增加备份和恢复策略说明`
  - `建立主流程 E2E 测试骨架`
- 若本轮直接尝试“完成上线前安全与恢复演练”，只能依赖大量未落地前置项，无法形成真实、最小、可验证的单轮变更。

### 修改文件
- `TASKS.md`
- `WORKLOG.md`

### 验证结果
- 已通过：
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic 临时 SQLite 迁移校验通过：`upgrade head -> downgrade base -> upgrade head`
    - `pytest` 272 个用例通过
    - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过
    - 前端测试共 19 个测试文件、55 个测试通过
    - Docker Compose 配置检查通过
    - `git diff --check` 通过
- 备注：
  - `pytest` 期间仍有 3 条既有 `DeprecationWarning`，来源于导出测试中的旧 `HTTP_422_UNPROCESSABLE_ENTITY` 常量；
  - 前端测试期间仍打印 Node `--localstorage-file` 既有警告。
  以上均为仓库已有现象，本轮未新增相关行为。

### 假设
- 当前保守假设：上线前综合演练应建立在权限收口、日志脱敏、备份策略和 E2E 骨架已存在的前提上，而不是在这些基础能力未完成时用一次人工检查替代。
- 拆分完成后，队列中下一个未完成且未阻塞的任务应回到 `建立最小请求身份上下文占位`。

## 2026-04-28 16:01 - Establish production deployment checklist and Docker Compose baseline

### 完成内容
- 补齐第一阶段部署资产：
  - 新增根目录 `.env.example`，集中提供反向代理端口、PostgreSQL、MinIO、后端运行配置和 LLM Provider 占位变量；
  - 新增 `deploy/docker-compose.yml`，提供 `api`、`worker`、`web`、`postgres`、`redis`、`minio`、`reverse-proxy` 以及 `migrate`、`minio-init` 一次性辅助服务；
  - 新增 `deploy/Dockerfile.api`、`deploy/Dockerfile.web`、`deploy/web.nginx.conf`、`deploy/reverse-proxy.nginx.conf`，固化后端镜像、前端静态构建与统一入口代理配置。
- 收口 PostgreSQL 运行依赖：
  - `pyproject.toml` 增加 `psycopg[binary]`，使 README 和 Compose 基线里的 `postgresql+psycopg://...` 连接串在实际部署镜像中可用；
  - 通过 `uv lock` 更新锁文件，避免部署时临时解析依赖。
- 补部署文档与验证：
  - 新增 `docs/生产部署清单与Docker Compose基线.md`，记录部署前检查、启动顺序、健康检查、日志位置、迁移命令、运行边界和首个管理员初始化方式；
  - `README.md` 增加部署基线入口说明；
  - `scripts/verify.sh` 增加 Docker Compose 配置自检，在本机存在 `docker compose` 时校验 `deploy/docker-compose.yml` 与 `.env.example`。
- 更新任务记录：
  - `TASKS.md` 将“建立生产部署清单和 Docker Compose 基线”标记为完成；
  - `docs/第一阶段验收映射.md` 同步把部署差距表述收敛为“仍缺上线前演练”，不再声称完全没有部署基线。

### 根因
- 当前仓库虽然已经逐步收口迁移、对象存储、异步 worker 和生产注册策略，但仍缺少一套可直接落地的部署资产。
- `TASKS.md` 的该项要求不仅是写说明，还要求提供可运行的 Compose 组合、环境变量模板和管理员初始化方式。
- README 先前示例宣称支持 `postgresql+psycopg://...`，但依赖清单里没有 `psycopg`，这会让 PostgreSQL 部署基线在真正启动时失败。

### 修改文件
- `.env.example`
- `TASKS.md`
- `WORKLOG.md`
- `README.md`
- `docs/第一阶段验收映射.md`
- `docs/生产部署清单与Docker Compose基线.md`
- `deploy/Dockerfile.api`
- `deploy/Dockerfile.web`
- `deploy/docker-compose.yml`
- `deploy/reverse-proxy.nginx.conf`
- `deploy/web.nginx.conf`
- `pyproject.toml`
- `scripts/verify.sh`
- `uv.lock`

### 验证结果
- 已通过：
  - `uv lock`
    - 锁文件已更新，新增 `psycopg`、`psycopg-binary` 与 `tzdata`
  - `docker compose --env-file .env.example -f deploy/docker-compose.yml config`
    - Compose 配置和环境变量占位可被成功解析
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic 临时 SQLite 迁移校验通过：`upgrade head -> downgrade base -> upgrade head`
    - `pytest` 272 个用例通过
    - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过
    - 前端测试共 19 个测试文件、55 个测试通过
    - Docker Compose 配置检查通过
    - `git diff --check` 通过
- 备注：
  - `pytest` 期间仍有 3 条既有 `DeprecationWarning`，来源于导出测试中的旧 `HTTP_422_UNPROCESSABLE_ENTITY` 常量；
  - 前端测试期间仍打印 Node `--localstorage-file` 既有警告。
  以上均为仓库已有现象，本轮未新增相关行为。

### 假设
- 当前保守把 `redis` 纳入 Compose 基线，作为架构文档建议的 Broker / 缓存预留服务；本轮不伪装成后端已经切换到 Redis 队列。
- 当前 MinIO bucket 初始化通过一次性 `minio-init` 容器完成，避免把“自动建 bucket”逻辑塞进业务代码路径。

## 2026-04-28 15:56 - Close production account bootstrap and registration policy

### 完成内容
- 收口后端生产注册策略：
  - `src/trms_backend/runtime_config.py` 新增 `auth` 配置块，支持 `TRMS_AUTH_ALLOW_ADMIN_SELF_REGISTER` 与 `TRMS_AUTH_BOOTSTRAP_ADMIN_TOKEN`；
  - 开发/测试环境默认仍允许高权限自注册，`TRMS_ENV=production` 下默认禁止 `admin` / `system_admin` 通过 `POST /api/auth/register` 自注册。
- 增加受控的高权限初始化入口：
  - `src/trms_backend/api/auth.py` 新增 `POST /api/auth/bootstrap-admin`，要求请求头提供 `X-TRMS-Bootstrap-Token`；
  - `src/trms_backend/domain/auth.py` 将高权限初始化与普通自注册分成两条路径，只允许该入口创建首个 `admin` 或 `system_admin`；
  - 一旦库中已经存在任一高权限账号，初始化入口会显式拒绝再次使用，并把后续邀请/审批流程保留为明确的后续边界。
- 补最小审计元数据：
  - `src/trms_backend/infrastructure/models.py` 与 `alembic/versions/20260428_02_auth_registration_audit_fields.py` 为 `user_accounts` 增加 `registration_source` 与 `created_by_user_id`；
  - 当前能区分 `self_service` 与 `bootstrap_token` 两类创建来源，为后续邀请/审批留出字段边界。
- 收口前端登录页暴露面：
  - 新增 `web/src/app/auth-ui-config.ts`，默认在生产构建下关闭开发调试角色入口和高权限自注册入口；
  - `web/src/app/auth.tsx` 在关闭时隐藏 mock 角色卡片，并把注册页收敛到成员自注册提示；
  - `README.md` 更新生产注册策略、初始化入口和 `VITE_ENABLE_DEV_AUTH_ROUTES` 的使用说明。
- 更新任务记录：
  - `TASKS.md` 将“收口生产账号初始化和注册策略”标记为完成。

### 根因
- 现有账号闭环虽然已经提供用户名密码注册登录，但注册接口无条件接受 `admin` 和 `system_admin`，生产环境缺少任何收口。
- 前端登录页默认公开开发调试角色入口和高权限角色注册选项，会把仅用于本地调试的能力直接暴露到生产构建。
- 仓库当时也没有记录“高权限账号是自注册还是初始化创建”的最小审计来源，无法为后续邀请/审批演进保留可信边界。

### 修改文件
- `TASKS.md`
- `WORKLOG.md`
- `README.md`
- `src/trms_backend/api/auth.py`
- `src/trms_backend/domain/auth.py`
- `src/trms_backend/infrastructure/models.py`
- `src/trms_backend/infrastructure/repositories.py`
- `src/trms_backend/main.py`
- `src/trms_backend/runtime_config.py`
- `tests/test_auth_api.py`
- `tests/test_database_migrations.py`
- `tests/test_runtime_config.py`
- `web/src/app/App.test.tsx`
- `web/src/app/auth-ui-config.test.ts`
- `web/src/app/auth-ui-config.ts`
- `web/src/app/auth.tsx`
- `web/src/vite-env.d.ts`
- `alembic/versions/20260428_02_auth_registration_audit_fields.py`

### 验证结果
- 已通过：
  - `uv run pytest tests/test_auth_api.py tests/test_runtime_config.py tests/test_database_migrations.py`
    - 25 个测试通过
  - `cd web && npm test -- src/app/App.test.tsx src/app/auth-ui-config.test.ts`
    - 2 个前端测试文件、8 个测试通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic 临时 SQLite 迁移校验通过：`upgrade head -> downgrade base -> upgrade head`
    - `pytest` 272 个用例通过
    - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过
    - 前端测试共 19 个测试文件、55 个测试通过
    - `git diff --check` 通过
- 备注：
  - `pytest` 期间仍有 3 条既有 `DeprecationWarning`，来源于导出测试中的旧 `HTTP_422_UNPROCESSABLE_ENTITY` 常量；
  - 前端测试期间仍打印 Node `--localstorage-file` 既有警告。
  以上均为仓库已有现象，本轮未新增相关行为。

### 假设
- 当前把“生产首个高权限账号创建”保守收敛为一次性 bootstrap token 入口，而不是在本轮直接实现完整邀请/审批工作流；后者仍需与统一身份上下文、审计和权限模型一起设计。
- `created_by_user_id` 本轮先作为后续邀请/审批的预留审计字段，当前 bootstrap 场景保持为空，不伪装成已经实现了完整审批链。
- 生产环境如需临时恢复高权限自注册，只能通过显式配置 `TRMS_AUTH_ALLOW_ADMIN_SELF_REGISTER=true` 开启；该能力默认不应在正式部署中启用。

## 2026-04-28 15:38 - Productionize object storage and export artifact access

### 完成内容
- 扩展运行配置模型：
  - `src/trms_backend/runtime_config.py` 新增 `file_storage` 配置块，区分 `local` 与 `s3` 两类后端；
  - 增加 `TRMS_STORAGE_BACKEND`、`TRMS_STORAGE_S3_ENDPOINT`、`TRMS_STORAGE_S3_BUCKET`、`TRMS_STORAGE_S3_ACCESS_KEY_ID`、`TRMS_STORAGE_S3_SECRET_ACCESS_KEY`、`TRMS_STORAGE_S3_REGION`、`TRMS_STORAGE_S3_KEY_PREFIX`；
  - 开发/测试环境默认继续使用本地目录，`TRMS_ENV=production` 下显式拒绝 `local` 存储，要求改用 S3 兼容对象存储。
- 新增 S3 兼容存储适配器：
  - `src/trms_backend/infrastructure/storage.py` 新增 `S3CompatibleMaterialFileStorage` 和统一工厂 `build_material_file_storage()`；
  - 原始材料与导出产物继续复用既有 `MaterialFileStorage` 协议，不扩散到业务层；
  - 对象存储读取缺失对象时会显式转成 `FileNotFoundError`，保持现有 API/worker 错误语义。
- 更新 API 与 worker 装配：
  - `src/trms_backend/main.py`、`src/trms_backend/__main__.py` 改为从运行配置统一构建存储实例；
  - 导出产物下载继续走后端 `GET /api/tasks/exports/{export_job_id}/artifact`，不暴露长期公开对象 URL。
- 补测试与文档：
  - `tests/test_material_storage.py` 增加对象存储适配器契约测试；
  - `tests/test_runtime_config.py` 增加生产环境 S3 配置、生产环境拒绝本地存储和凭据脱敏测试；
  - `README.md`、`docs/第一阶段验收映射.md`、`TASKS.md` 更新对象存储与生产访问边界说明；
  - `pyproject.toml`、`uv.lock` 增加 `boto3` 依赖。

### 根因
- 现有仓库虽然已经具备原始材料落盘、导出产物持久化和下载接口，但底层仍只支持本地目录 `MATERIAL_STORAGE_DIR`。
- 这会直接带来三类问题：
  - 生产环境 API / worker 容器重建后，本地盘上的原始材料和导出产物缺少可靠持久化边界；
  - 运行配置无法表达对象存储 endpoint、bucket 和凭据，也缺少显式脱敏出口；
  - “导出产物可下载”虽然已存在，但底层还没有和生产级对象存储适配，导致 README 与验收映射里对生产差距的描述仍然成立。

### 修改文件
- `TASKS.md`
- `WORKLOG.md`
- `README.md`
- `docs/第一阶段验收映射.md`
- `pyproject.toml`
- `uv.lock`
- `src/trms_backend/__main__.py`
- `src/trms_backend/infrastructure/storage.py`
- `src/trms_backend/main.py`
- `src/trms_backend/runtime_config.py`
- `tests/test_material_storage.py`
- `tests/test_runtime_config.py`

### 验证结果
- 已通过：
  - `uv lock`
    - 锁文件已更新，新增 `boto3`、`botocore` 及其依赖
  - `uv run pytest tests/test_runtime_config.py tests/test_material_storage.py tests/test_export_async_jobs.py`
    - 20 个测试通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic 临时 SQLite 迁移校验通过：`upgrade head -> downgrade base -> upgrade head`
    - `pytest` 267 个用例通过
    - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过
    - 前端测试共 18 个测试文件、52 个测试通过
    - `git diff --check` 通过
- 备注：
  - `pytest` 期间仍有 3 条既有 `DeprecationWarning`，来源于导出相关测试里的旧 `HTTP_422_UNPROCESSABLE_ENTITY` 常量；
  - 前端测试期间仍打印 Node `--localstorage-file` 既有警告。
  以上均为仓库已有现象，本轮未新增相关行为。

### 假设
- 本轮保守选择“导出下载继续经过后端读取存储内容”而不是直接发放预签名 URL；这样能满足“不暴露长期公开 URL”的要求，同时不提前把下载鉴权模型与后续 bearer 权限收口任务耦合在一起。
- 本轮未实际连接真实 MinIO/S3 服务做联机演练；当前只验证了运行配置解析、凭据脱敏和对象存储适配器接口契约。真实对象存储备份/恢复与联机兼容性仍属于后续部署和恢复演练任务范围。

## 2026-04-28 15:29 - Productionize database migration baseline with Alembic

### 完成内容
- 新增 Alembic 基线迁移：
  - 增加 `alembic.ini`、`alembic/env.py`、`alembic/script.py.mako` 和 `alembic/versions/20260428_01_baseline_schema.py`；
  - 用 `20260428_01` 固化当前 SQLAlchemy schema 基线，覆盖现有表、索引和约束。
- 更新 `src/trms_backend/infrastructure/database.py`：
  - 新增 `build_alembic_config()`、`get_alembic_head_revisions()` 和 `ensure_database_schema_is_current()`；
  - 新增 `DatabaseSchemaNotReadyError`，用于显式暴露“数据库未迁移到 Alembic head”；
  - `init_database()` 现在区分“允许本地自举建表”和“只校验迁移状态”两条路径。
- 更新 `src/trms_backend/main.py` 与 `src/trms_backend/__main__.py`：
  - 开发/测试环境继续允许 `create_all` 自举；
  - `TRMS_ENV=production` 下 API 与 worker 启动不再自动建表或自动演进 schema，必须先完成迁移。
- 更新 `scripts/verify.sh`：
  - 新增 Alembic 自检，使用临时 SQLite 数据库执行 `upgrade head -> downgrade base -> upgrade head`；
  - 确保迁移脚本可执行，而不是只存在文件但从未跑过。
- 更新文档：
  - `README.md` 补充迁移、回滚、生产启动前先迁移以及旧本地库处理方式；
  - `docs/数据库迁移策略说明.md` 从“暂不引入 Alembic”更新为“已引入 Alembic 基线并限制生产环境自动建表”；
  - `docs/第一阶段验收映射.md` 同步数据库迁移差距描述。
- 新增测试 `tests/test_database_migrations.py`：
  - 覆盖本地 SQLite 自举建表；
  - 覆盖生产路径拒绝未迁移库；
  - 覆盖 Alembic `head` 数据库可被启动路径接受。
- 更新 `TASKS.md`，将“生产化数据库迁移机制”标记为已完成。

### 根因
- 当前仓库虽然已经进入生产化相关任务，但数据库仍完全依赖应用启动期 `Base.metadata.create_all(...)`。
- 该做法对共享环境有三个直接问题：
  - schema 演进没有版本号和审计链，无法确认实例处于哪个结构版本；
  - 启动期静默补表无法覆盖列调整、约束变更和回滚需求；
  - 生产环境如果继续沿用 `create_all`，后续引入 Alembic 时旧库状态会更难确认和收口。

### 修改文件
- `TASKS.md`
- `WORKLOG.md`
- `README.md`
- `docs/数据库迁移策略说明.md`
- `docs/第一阶段验收映射.md`
- `pyproject.toml`
- `uv.lock`
- `scripts/verify.sh`
- `src/trms_backend/__main__.py`
- `src/trms_backend/main.py`
- `src/trms_backend/infrastructure/database.py`
- `tests/test_database_migrations.py`
- `alembic.ini`
- `alembic/env.py`
- `alembic/script.py.mako`
- `alembic/versions/20260428_01_baseline_schema.py`

### 验证结果
- 已通过：
  - `python3 -m compileall src tests alembic`
    - 编译检查通过
  - `uv run pytest tests/test_database_migrations.py tests/test_runtime_config.py tests/test_async_jobs.py`
    - 19 个测试通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic 临时 SQLite 迁移校验通过：`upgrade head -> downgrade base -> upgrade head`
    - `pytest` 263 个用例通过
    - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过
    - 前端测试共 18 个测试文件、52 个测试通过
    - `git diff --check` 通过
- 备注：
  - `pytest` 期间仍有 3 条既有 `DeprecationWarning`，来源于导出相关测试里旧的 `HTTP_422_UNPROCESSABLE_ENTITY` 常量；
  - 前端测试期间仍打印 Node `--localstorage-file` 既有警告。
  以上均为仓库已有现象，本轮未新增相关行为。

### 假设
- 本轮保守保留开发/测试环境的 `create_all` 自举能力，避免强行改动现有 pytest 和临时 SQLite 工作流；共享环境的 schema 管理边界则切换为 Alembic。
- 对历史本地 SQLite 库，不默认提供自动迁移脚本；只有在人工确认 schema 与当前基线一致时才建议 `alembic stamp head`，否则优先备份后重建。

## 2026-04-28 15:40 - Implement async export worker consumption and artifact status query

### 完成内容
- 新增 `src/trms_backend/application/export_async_jobs.py`：
  - 建立 `ExportAsyncJobProcessor`，由 worker 轮询并消费待执行的导出任务；
  - 对已实现的 CSV / JSON 导出生成真实产物并落盘；
  - 对未实现的 merged PDF 导出显式标记失败，不伪装成功。
- 更新 `src/trms_backend/domain/exports.py` 与 `src/trms_backend/infrastructure/repositories.py`：
  - 为导出任务补齐 `artifact`、`retry_count` 与内部 `artifact_storage_key` 边界；
  - 新增 `list_pending(limit=...)` 和 `update_status(..., expected_current_status=...)`，让 worker 可以原子抢占 pending 任务；
  - 复用现有 `export_jobs.parameters` JSON 列持久化产物元数据，避免本轮引入新的 schema 迁移。
- 更新 `src/trms_backend/__main__.py`：
  - worker 启动时不再挂 `export` 占位处理器；
  - 会装配真实导出处理器，与识别任务共用同一个异步 worker 入口。
- 更新 `src/trms_backend/api/exports.py`：
  - 创建、列表和状态更新响应现在会返回 `retry_count` 与产物元数据；
  - 新增 `GET /api/tasks/exports/{export_job_id}` 状态查询接口；
  - 新增 `GET /api/tasks/exports/{export_job_id}/artifact` 下载接口；
  - 产物未就绪时返回明确 409，非任务管理员访问状态或下载时返回 403。
- 更新 `README.md`、`docs/第一阶段验收映射.md`、`TASKS.md`：
  - 修正“导出 worker 仍是 placeholder”的过时描述；
  - 将“实现导出任务异步执行与产物状态查询”标记为已完成；
  - 同步第一阶段导出能力边界为“异步消费 + 持久化产物 + 管理员下载已完成，merged PDF / XLSX 仍未完成”。
- 新增/更新测试：
  - `tests/test_export_async_jobs.py` 覆盖导出 worker 消费、成功产物下载、未就绪状态和未实现格式失败；
  - `tests/test_async_jobs.py` 覆盖同一导出任务重复投递时只会被真正处理一次；
  - `tests/test_exports_api.py` 覆盖 `retry_count` 与新产物字段；
  - `web/src/app/admin-export-tasks.test.tsx` 同步新的导出能力说明文案。

### 根因
- 上一轮虽然已经有导出任务模型、状态机和管理员导出页面，但 `export` processor 仍是空实现。
- 这会导致三个问题：
  - `TRMS_ASYNC_JOB_MODE=worker` 下导出任务不会被实际消费，异步边界只有模型没有行为；
  - 导出任务只能停留在 `pending/running/failed/succeeded` 占位状态，没有真实产物元数据和下载入口；
  - 同一导出任务如果被重复投递，原实现缺少最小抢占和幂等边界，无法证明不会重复生成业务结果。

### 修改文件
- `TASKS.md`
- `WORKLOG.md`
- `README.md`
- `docs/第一阶段验收映射.md`
- `src/trms_backend/__main__.py`
- `src/trms_backend/api/exports.py`
- `src/trms_backend/application/export_async_jobs.py`
- `src/trms_backend/domain/exports.py`
- `src/trms_backend/infrastructure/repositories.py`
- `tests/test_async_jobs.py`
- `tests/test_export_async_jobs.py`
- `tests/test_exports_api.py`
- `web/src/app/admin-export-tasks.test.tsx`

### 验证结果
- 已通过：
  - `python3 -m compileall src tests`
    - 编译检查通过
  - `uv run pytest tests/test_async_jobs.py tests/test_export_async_jobs.py tests/test_exports_api.py`
    - 29 个测试通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - `pytest` 260 个用例通过
    - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过
    - 前端测试共 18 个测试文件、52 个测试通过
    - `git diff --check` 通过
- 备注：
  - `pytest` 期间仍有 3 条既有 `DeprecationWarning`，来源于导出相关测试里旧的 `HTTP_422_UNPROCESSABLE_ENTITY` 常量；
  - 前端测试期间仍打印 Node `--localstorage-file` 既有警告。
  以上均为仓库已有现象，本轮未新增相关行为。

### 假设
- 本轮保守复用现有 `MaterialFileStorage` 在 `task_id/_exports/` 前缀下保存导出产物，而不是额外引入新的导出存储抽象；后续“生产化对象存储和导出文件访问”任务再统一收口存储适配层。
- 当前只为已实现的 CSV / JSON 导出生成真实异步产物；merged PDF 与 XLSX 仍按明确失败边界暴露，不在本轮伪装为可用。

## 2026-04-28 15:27 - Implement async recognition worker consumption and retry observability

### 完成内容
- 新增 `src/trms_backend/application/recognition_async_jobs.py`：
  - 建立 `RecognitionAsyncJobProcessor`，由 worker 轮询并消费待执行的识别任务；
  - 每次成功执行后立即刷新对应材料的校验结果；
  - 保留 `export` processor 占位，避免本轮把导出异步链路一并拉进来。
- 更新 `src/trms_backend/__main__.py`：
  - worker 启动时不再只是空壳；
  - 会按当前运行配置装配识别处理器、仓储、文件存储和可选 LLM 客户端；
  - `uv run python -m trms_backend worker --once` 现在会真实消费 pending 识别任务。
- 更新 `src/trms_backend/domain/recognitions.py` 与 `src/trms_backend/infrastructure/repositories.py`：
  - 新增 `list_pending(limit=...)`，供 worker 按创建时间顺序拉取待执行识别任务；
  - `update_status(...)` 新增 `expected_current_status` 条件更新边界，防止同一识别任务被重复投递时发生终态覆盖。
- 更新 `src/trms_backend/application/recognition_preparation.py`：
  - 识别执行落库时强制要求任务仍处于 `pending`；
  - 如果任务已被其他执行路径处理完，会显式返回冲突，而不是覆盖已有成功/失败结果。
- 更新 `src/trms_backend/api/recognitions.py`：
  - 识别任务列表增加 `retry_count`，以材料维度显式返回已创建的重试次数；
  - 保留现有手动 `POST /api/recognition-tasks/{id}/execute` 入口，继续作为开发和排障入口。
- 更新 `README.md` 与 `docs/第一阶段验收映射.md`：
  - 修正“worker 仍未消费识别任务”的过时描述；
  - 将识别链路状态更新为“文本 PDF + LLM + worker 异步闭环已完成，OCR 和生产级队列仍未完成”。
- 新增/更新测试：
  - `tests/test_recognition_async_jobs.py` 覆盖真实 pending 识别任务被 worker 消费、失败原因可查询，以及重复轮询不重复执行；
  - `tests/test_async_jobs.py` 覆盖同一识别任务重复投递时，处理器按冲突边界跳过重复结果写入；
  - `tests/test_recognition_tasks_api.py` 覆盖 `retry_count` 查询结果。
- 更新 `TASKS.md`，将“实现识别任务异步执行与重试可观测性”标记为已完成。

### 根因
- 上一轮虽然已经有共享 worker 入口、真实 PDF 文本提取和 OpenAI 兼容 LLM 结构化识别，但识别执行仍只存在手动 `/execute` 路径。
- 这会导致两个问题：
  - `TRMS_ASYNC_JOB_MODE=worker` 下 worker 实际不会消费任何识别任务，异步边界名义存在、行为缺失；
  - 同一识别任务如果被 worker / 手动接口重复投递，原有 `update_status` 会直接覆盖终态，缺少最小幂等保护和可观测的重试计数。

### 修改文件
- `TASKS.md`
- `WORKLOG.md`
- `README.md`
- `docs/第一阶段验收映射.md`
- `src/trms_backend/__main__.py`
- `src/trms_backend/api/recognitions.py`
- `src/trms_backend/application/recognition_async_jobs.py`
- `src/trms_backend/application/recognition_preparation.py`
- `src/trms_backend/domain/recognitions.py`
- `src/trms_backend/infrastructure/repositories.py`
- `tests/test_async_jobs.py`
- `tests/test_recognition_async_jobs.py`
- `tests/test_recognition_tasks_api.py`

### 验证结果
- 已通过：
  - `uv run pytest tests/test_async_jobs.py tests/test_recognition_async_jobs.py tests/test_recognition_tasks_api.py tests/test_recognition_execution_api.py`
    - 22 个测试通过
  - `python3 -m compileall src tests`
    - 编译检查通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - `pytest` 255 个用例通过
    - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过
    - 前端测试共 18 个测试文件、52 个测试通过
    - `git diff --check` 通过
- 备注：
  - `pytest` 期间仍有 3 条既有 `DeprecationWarning`，来源于导出相关测试路径中的旧 `HTTP_422_UNPROCESSABLE_ENTITY` 常量引用；
  - 前端测试期间仍打印 Node `--localstorage-file` 既有警告。
  以上均为仓库已有现象，本轮未新增相关行为。

### 假设
- 本轮把“重试可观测性”保守落在材料维度的 `retry_count` 和识别任务历史列表上，不在此轮引入新的数据库字段或单独的任务运行审计表。
- 本轮只让 worker 真实消费识别任务；导出任务异步消费、产物状态查询和下载边界仍留给 `TASKS.md` 的下一项独立任务。

## 2026-04-28 14:56 - Establish shared async job runtime mode and worker entrypoint

### 完成内容
- 更新 `src/trms_backend/runtime_config.py`：
  - 新增共享异步任务配置 `async_jobs`；
  - 收口 `TRMS_ASYNC_JOB_MODE` 和 `TRMS_ASYNC_JOB_POLL_INTERVAL_SECONDS`；
  - 开发/测试环境默认使用 `in_process`，生产环境默认使用 `worker`；
  - 当 `TRMS_ENV=production` 且显式配置 `TRMS_ASYNC_JOB_MODE=in_process` 时，启动阶段直接报错，拒绝把耗时任务留在请求线程。
- 新增 `src/trms_backend/application/async_jobs.py`：
  - 建立最小 worker 骨架 `AsyncJobWorker`；
  - 用统一模式校验和 processor 注册机制承接后续识别/导出异步消费链；
  - 当前只提供共享运行边界和命令入口，不提前实现识别或导出任务消费逻辑。
- 更新 `src/trms_backend/__main__.py`：
  - 保留既有 `uv run python -m trms_backend --reload` API 启动方式；
  - 新增 `uv run python -m trms_backend worker` 与 `worker --once` 入口，供后续识别/导出任务共用。
- 更新 `src/trms_backend/main.py`：
  - 将 `async_job_config` 挂到 `app.state`，为后续 API/worker 共享读取点预留稳定边界。
- 更新 `README.md`：
  - 补充异步任务运行模式、worker 启动命令和生产环境限制说明；
  - 修正此前仍写“尚未接入真实 PDF/LLM 识别执行器”的过时描述。
- 新增/更新测试：
  - `tests/test_runtime_config.py` 覆盖异步模式默认值、生产环境默认 worker、非法模式和生产环境拒绝 `in_process`；
  - `tests/test_async_jobs.py` 覆盖 worker 聚合执行、非法模式拒绝，以及 `python -m trms_backend` 的 API / worker 启动入口兼容性。
- 更新 `TASKS.md`，将“建立异步任务共享运行模式与执行入口”标记为已完成。

### 根因
- 当前仓库虽然已有识别任务模型、导出任务模型和若干同步执行入口，但还没有统一表达“这些耗时任务到底在请求线程里跑，还是交给外部 worker 跑”的运行时边界。
- 如果继续直接实现后续异步识别/导出而不先收口运行模式，会把以下问题扩散到多个模块：
  - 配置散落在识别、导出和启动脚本中；
  - 生产环境无法稳定拒绝同步执行；
  - 后续 worker 入口只能临时拼接，缺少共享执行骨架。

### 修改文件
- `README.md`
- `TASKS.md`
- `WORKLOG.md`
- `src/trms_backend/__main__.py`
- `src/trms_backend/application/async_jobs.py`
- `src/trms_backend/main.py`
- `src/trms_backend/runtime_config.py`
- `tests/test_async_jobs.py`
- `tests/test_runtime_config.py`

### 验证结果
- 已通过：
  - `uv run pytest tests/test_runtime_config.py tests/test_async_jobs.py`
    - 14 个测试通过
  - `python3 -m compileall src tests`
    - 编译检查通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - `pytest` 253 个用例通过
    - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过
    - 前端测试共 18 个测试文件、52 个测试通过
    - `git diff --check` 通过
- 备注：
  - `pytest` 期间仍有 3 条既有 `DeprecationWarning`，来源于导出相关测试路径中的旧 `HTTP_422_UNPROCESSABLE_ENTITY` 常量引用；
  - 前端测试期间仍打印 Node `--localstorage-file` 既有警告。
  以上均为仓库已有现象，本轮未新增相关行为。

### 假设
- 本轮只建立共享运行模式、配置和 worker 命令入口，不在这里提前把识别任务或导出任务真正改造成异步消费链；这些属于 `TASKS.md` 中紧随其后的两个独立任务。
- 当前保守保留手动 `/execute` 和同步导出能力，作为开发/排障入口继续存在；是否完全切走请求内执行，应由后续“识别异步执行”和“导出异步执行”任务分别处理。

## 2026-04-28 14:39 - Redesign web shell and role workbench information architecture

### 完成内容
- 更新 `web/src/app/pages.tsx` 与 `web/src/styles.css`：
  - 用统一工作台壳层替换原先“首页大段边界说明”布局；
  - 新增顶部导航、会话摘要、统一品牌区和五阶段流程条；
  - 首页改成流程总览 + 角色入口 + 操作原则三段式结构，优先展示“当前阶段”“下一步动作”而不是静态说明。
- 重做 `web/src/app/admin-task-list.tsx`：
  - 管理员入口从普通列表改成工作台；
  - 增加任务概览指标、异常优先级排序、推荐动作和复核快捷入口；
  - 任务卡片直接暴露“先处理 Must 级失败校验 / 成员异议 / 识别异常 / 导出准备”等推进建议。
- 重做 `web/src/app/member-task-list.tsx`：
  - 成员入口改成按状态排序的任务工作台；
  - 增加“开放提交 / 等待补充或确认 / 进入归档阶段”概览指标；
  - 每个任务卡片直接给出推荐动作，并把上传、缺失材料、材料状态和费用确认入口收敛到同一卡片。
- 更新前端测试：
  - `web/src/app/App.test.tsx`
  - `web/src/app/admin-task-list.test.tsx`
  - `web/src/app/member-task-list.test.tsx`
  使其覆盖新版首页、管理员工作台和成员工作台的关键文案与主操作入口。
- 更新 `TASKS.md`，将“重构 Web 首页与角色工作台信息架构”标记为已完成。

### 根因
- 现有前端不是功能不够，而是首页、管理员入口和成员入口都在重复解释系统边界，缺少工作台视角。
- 这导致两个直接问题：
  - 视觉上表现为大量同质化卡片堆叠，缺少层级、节奏和重点；
  - 交互上表现为用户先读说明再找入口，无法一眼判断“当前阶段是什么”“下一步该做什么”“哪些任务最急”。
- 因此本轮没有继续堆更多页面，而是先重构共享壳层和两类角色首屏的信息架构，把前端主逻辑从“读说明”改为“看状态 -> 看异常 -> 进下一步”。

### 修改文件
- `TASKS.md`
- `WORKLOG.md`
- `web/src/app/App.test.tsx`
- `web/src/app/admin-task-list.test.tsx`
- `web/src/app/admin-task-list.tsx`
- `web/src/app/member-task-list.test.tsx`
- `web/src/app/member-task-list.tsx`
- `web/src/app/pages.tsx`
- `web/src/styles.css`

### 验证结果
- 已通过：
  - `cd web && npm test -- src/app/App.test.tsx src/app/admin-task-list.test.tsx src/app/member-task-list.test.tsx`
    - 3 个测试文件、11 个测试通过
  - `cd web && npm run lint`
  - `cd web && npm run build`
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - `pytest` 246 个用例通过
    - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过
    - 前端测试共 18 个测试文件、52 个测试通过
    - `git diff --check` 通过
- 备注：
  - `pytest` 期间仍有 3 条既有 `DeprecationWarning`，来源于导出相关测试路径中的旧 `HTTP_422_UNPROCESSABLE_ENTITY` 常量引用；
  - 前端测试期间仍打印 Node `--localstorage-file` 既有警告。
  以上均为仓库已有现象，本轮未新增相关行为。

### 假设
- 本轮只重构共享壳层、首页和管理员/成员两个角色工作台首屏，不顺手重写发票编辑、复核详情、导出等深层页面，避免把“前端变丑”问题扩散成无边界重写。
- 本轮保守假设最优先的“工作逻辑”问题是信息架构和入口排序，而不是后端 API 语义变化；因此没有改动任何业务接口，也没有引入新依赖或组件库。
- 本轮继续沿用现有 mock / bearer 会话边界；真实生产级权限收口仍应由后续权限任务处理，而不是在视觉改版中偷偷混入业务语义变更。

## 2026-04-28 13:55 - Integrate OpenAI-compatible structured LLM recognition

### 完成内容
- 新增 `src/trms_backend/application/recognition_llm.py`，建立可替换的 OpenAI 兼容结构化识别客户端：
  - 通过 `/chat/completions` 调用 OpenAI 兼容接口；
  - 使用 `response_format=json_schema` 下发结构化提取 Schema；
  - 仅在 Pydantic 校验通过后，才把识别结果映射为系统内 `recognized_fields`；
  - 至少支持 `invoice_number`、`amount_cents`、`buyer_name`、`tax_number`、`transaction_time`、`location`、`expense_type`、`material_type` 八类结构化字段；
  - 对 LLM 超时、请求失败、非 JSON、Schema 校验失败和“无任何可用字段”分别返回稳定失败原因。
- 更新 `src/trms_backend/application/recognition_preparation.py` 与 `src/trms_backend/main.py`：
  - 现有 `POST /api/recognition-tasks/{recognition_task_id}/execute` 从“预处理后直接失败占位”改为“预处理 -> LLM 识别 -> 落库状态更新”；
  - 未配置 LLM Provider 时仍显式返回 `llm_provider_not_configured`；
  - 已配置 LLM 时，识别成功写入结构化字段并进入 `succeeded`，低置信度字段存在时进入 `needs_confirmation`，不再把 AI 阶段统一伪装成失败。
- 更新 `pyproject.toml` 与 `uv.lock`：
  - 将 `httpx` 从开发依赖提升为运行时依赖，因为真实 LLM 调用链在后端主代码路径中直接使用它。
- 新增/更新测试：
  - `tests/test_recognition_llm.py` 使用 fake provider 覆盖成功解析、低置信度映射、非 JSON、字段缺失和超时重试路径；
  - `tests/test_recognition_execution_api.py` 覆盖执行接口的真实结构化落库、低置信度转 `needs_confirmation`、以及 LLM 失败原因透传落库。
- 更新 `TASKS.md`，将“接入 OpenAI 兼容 LLM 结构化识别最小闭环”标记为已完成。

### 根因
- 上一轮虽然已经补齐 PDF 文本提取和识别输入构建，但执行入口在拿到 `recognition_input` 后仍会直接以 `structured_recognition_not_implemented` 或 `llm_provider_not_configured` 结束。
- 这意味着系统仍然没有真实的 AI 结构化识别主链路，发票字段只能依赖人工 PATCH 或人工录入，既不满足需求中的 AI 辅助识别，也无法把“LLM 失败”“输出格式错误”“低置信度待确认”这些不同状态清晰落库。

### 修改文件
- `pyproject.toml`
- `uv.lock`
- `src/trms_backend/application/recognition_llm.py`
- `src/trms_backend/application/recognition_preparation.py`
- `src/trms_backend/main.py`
- `tests/test_recognition_llm.py`
- `tests/test_recognition_execution_api.py`
- `TASKS.md`
- `WORKLOG.md`

### 验证结果
- 已通过：
  - `uv run pytest tests/test_recognition_llm.py tests/test_recognition_execution_api.py tests/test_recognition_tasks_api.py tests/test_recognition_runtime.py`
    - 22 个测试通过
  - `python3 -m compileall src tests`
    - 编译检查通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - `pytest` 246 个用例通过
    - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过
    - 前端测试共 18 个测试文件、52 个测试通过
    - `git diff --check` 通过
- 备注：
  - `pytest` 期间仍有 3 条既有 `DeprecationWarning`，来源于导出相关测试路径中的旧 `HTTP_422_UNPROCESSABLE_ENTITY` 常量引用；
  - 前端测试期间仍打印 Node `--localstorage-file` 既有警告。
  以上均为仓库已有现象，本轮未新增相关行为。

### 假设
- 本轮将“低置信度字段进入 `needs_confirmation`”收敛为固定阈值 `confidence < 0.8`；当前任务只要求形成最小闭环，不在本轮引入新的全局配置项。若后续需要按字段或任务细化阈值，应拆成单独配置任务。
- 本轮继续只处理“文本 PDF -> LLM 结构化识别”主路径；图片和扫描 PDF 仍保持 `ocr_not_configured` 的显式失败边界，没有借机扩展到真实 OCR。
- 本轮将“附件类型”落到现有领域字段名 `material_type`，以保持与当前材料枚举和后续校验链一致，不另起一套平行命名。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“建立异步识别和导出任务执行机制”，把当前同步 `/execute` 入口下沉到 worker 或显式任务执行器，避免真实 LLM 调用长期停留在请求线程内。

## 2026-04-28 13:44 - Implement real PDF text extraction and recognition input preparation

### 完成内容
- 新增 `src/trms_backend/application/recognition_preparation.py`，建立最小识别预处理执行链：
  - 读取已上传材料文件；
  - 对文本 PDF 使用 `pypdf` 提取可复制文本并构建识别输入；
  - 对普通图片和 image-only/scanned PDF 在未接入真实 OCR 时显式返回 `ocr_not_configured`；
  - 对损坏、加密、空白或不可解析 PDF 分别返回稳定失败原因；
  - 在 `raw_response.preparation` 中记录材料编号、原始文件名、内容类型和已构建的识别输入，避免失败时丢失上下文。
- 更新 `src/trms_backend/api/recognitions.py` 与 `src/trms_backend/main.py`：
  - 新增 `POST /api/recognition-tasks/{recognition_task_id}/execute` 最小执行入口；
  - 只允许从 `pending` 状态执行；
  - 成功完成预处理后，如当前未配置 LLM Provider，则显式以 `llm_provider_not_configured` 失败结束，不伪造识别成功。
- 新增 `tests/test_recognition_execution_api.py`，覆盖：
  - 文本 PDF 提取成功并写入识别输入；
  - 普通图片与 image-only PDF 的 `ocr_not_configured` 路径；
  - 损坏 PDF、空白 PDF、加密 PDF 的稳定失败路径。
- 更新 `TASKS.md`，将“实现真实 PDF 文本提取和识别输入构建”标记为已完成。

### 根因
- 仓库此前只有识别任务占位模型和手工状态更新接口；上传材料后虽然会创建 `recognition_task`，但并没有任何真实执行链去读取文件、提取 PDF 文本或把失败原因落库。
- 如果直接进入下一步 LLM 接入而不先补上这一层，后续识别链仍然只能依赖手工 PATCH 状态或让 LLM“猜文件内容”，既不满足任务定义，也会把 PDF/扫描件解析失败与 LLM 失败混在一起。

### 修改文件
- `src/trms_backend/application/recognition_preparation.py`
- `src/trms_backend/api/recognitions.py`
- `src/trms_backend/main.py`
- `tests/test_recognition_execution_api.py`
- `TASKS.md`
- `WORKLOG.md`

### 验证结果
- 已通过：
  - `uv run pytest tests/test_recognition_execution_api.py tests/test_recognition_tasks_api.py tests/test_recognition_runtime.py`
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - pytest 239 个用例通过
    - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过
    - `git diff --check` 通过
- 备注：
  - `pytest` 期间仍有 3 条既有 `DeprecationWarning`，来自导出相关测试路径对旧 HTTP 422 常量的引用；本轮未改动该区域，也未把它们包装成失败。

### 假设
- 当前“真实 PDF 文本提取”范围仅覆盖可直接复制文本的 PDF；OCR 与结构化 LLM 识别仍分别留给后续任务。
- image-only PDF 通过页内图片对象判定为“需要 OCR”；普通图片材料在本轮不尝试做文件内容级图像解码，因为当前任务目标是显式暴露 `ocr_not_configured`，不是实现 OCR。
- 当 LLM Provider 已配置但结构化识别尚未接入时，本轮保守返回 `structured_recognition_not_implemented`；当前默认验证路径因未配置 LLM Provider，实际失败原因仍是 `llm_provider_not_configured`。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“接入 OpenAI 兼容 LLM 结构化识别最小闭环”，直接复用本轮写入的 `recognition_input`，把当前 `failed` 的 AI 阶段占位改成真实结构化识别调用与结果校验。

## 2026-04-28 13:33 - Add OpenAI-compatible LLM provider runtime configuration

### 完成内容
- 更新 `src/trms_backend/runtime_config.py`：
  - 新增可选 `llm_provider` 配置块，统一收口 `TRMS_LLM_API_KEY`、`TRMS_LLM_BASE_URL`、`TRMS_LLM_MODEL`、`TRMS_LLM_TIMEOUT_SECONDS`、`TRMS_LLM_MAX_RETRIES`；
  - 仅当检测到任一 `TRMS_LLM_*` 配置时才尝试启用该配置块；
  - 一旦开始配置 `TRMS_LLM_*`，强制要求 `TRMS_LLM_API_KEY` 和 `TRMS_LLM_MODEL` 存在；
  - 对 `base_url` 做绝对 `http(s)` URL 校验和尾部 `/` 规范化；
  - 为日志场景增加 `to_safe_log_fields()`，显式脱敏 `api_key`。
- 新增 `src/trms_backend/application/recognition_runtime.py`：
  - 提供 `resolve_recognition_llm_capability()`；
  - 未配置 LLM Provider 时，明确返回识别能力 `disabled` 和 `llm_provider_not_configured` 失败原因；
  - 已配置时返回可供后续真实识别执行链复用的 `base_url`、`model`、超时和重试上限。
- 更新 `src/trms_backend/main.py`：
  - 启动时将 LLM 能力判定挂到 `app.state.recognition_llm_capability`，作为后续识别执行入口的统一读点。
- 新增/更新测试：
  - `tests/test_runtime_config.py` 覆盖默认禁用、配置读取、缺失密钥、`base_url` 规范化和日志脱敏；
  - `tests/test_recognition_runtime.py` 覆盖识别能力 `enabled` / `disabled` 判定。
- 更新 `README.md`：
  - 补充后端 LLM Provider 环境变量说明、默认值、示例和安全边界；
  - 明确当前仓库尚未接入真实 PDF/LLM 执行器，本轮只建立配置和禁用状态边界。
- 更新 `TASKS.md`，将“增加 OpenAI 兼容 LLM Provider 配置”标记为已完成。

### 修改文件
- `src/trms_backend/runtime_config.py`
- `src/trms_backend/application/recognition_runtime.py`
- `src/trms_backend/main.py`
- `tests/test_runtime_config.py`
- `tests/test_recognition_runtime.py`
- `README.md`
- `TASKS.md`
- `WORKLOG.md`

### 根因
- 现有统一运行配置只覆盖数据库、文件存储、CORS 和 API 地址，尚未把外部 LLM Provider 的 `api_key`、`base_url`、`model`、超时和重试边界纳入同一个配置模型。
- 如果继续让后续识别链各处自行读取 `TRMS_LLM_*` 环境变量，会重复出现：
  - 配置散落；
  - 缺失密钥或模型时只能到运行期才暴露；
  - `api_key` 容易在调试输出里泄露；
  - “未配置 LLM” 与 “识别成功” 之间缺少明确状态边界。

### 当前结论
- 后端现在已经可以用统一配置模型承载 OpenAI 兼容 LLM Provider 设置，并在启动阶段尽早拒绝缺失关键配置的半配置状态。
- 未配置 LLM Provider 时，系统现在至少有了明确的 `disabled` 能力判定和标准失败原因，后续真实 PDF/LLM 识别执行器可以直接复用，而不是再自行发明一套隐式降级逻辑。

### 验证结果
- 已通过：
  - `uv run pytest tests/test_runtime_config.py tests/test_recognition_runtime.py`
    - 9 个测试通过
  - `python3 -m compileall src tests`
    - 编译检查通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - `pytest` 233 个用例通过
    - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过
    - 前端测试共 18 个测试文件、52 个测试通过
    - `git diff --check` 通过
- 既有警告：
  - `pytest` 仍有 3 条第三方 `DeprecationWarning`，来源于 `HTTP_422_UNPROCESSABLE_ENTITY`
  - 前端测试期间仍打印 Node `--localstorage-file` 既有警告
  这些均为仓库已有现象，本轮未新增相关行为。

### 假设
- 本轮保守假设 LLM Provider 配置在当前阶段应保持“可选但显式”，即：完全未配置时允许系统继续运行，但一旦开始配置 `TRMS_LLM_*`，就必须把关键字段一次配齐。
- 本轮保守假设 `TRMS_LLM_MODEL` 不应存在隐式默认值；与数据库地址不同，错误的默认模型会把问题从启动阶段推迟到真实识别请求阶段。
- 本轮不接入真实 PDF 文本提取、OCR、OpenAI 兼容请求发送或异步 worker；这些仍留给后续 `TASKS.md` 中紧随其后的识别流水线任务。

## 2026-04-28 13:28 - Add web runtime host/port and API base URL boundaries

### 完成内容
- 更新 `web/vite.config.ts`：
  - 新增 `TRMS_WEB_HOST`、`TRMS_WEB_PORT` 开发态配置读取；
  - 仅对 `vite dev` 生效，不进入前端构建产物；
  - 对非法端口直接报错，避免开发联调时静默落到错误端口。
- 更新 `web/src/lib/api/client.ts`：
  - 将前端 API base URL 解析提炼为 `resolveApiBaseUrl()`；
  - 默认继续使用同源 `/api`，显式配置 `VITE_API_BASE_URL` 时会去掉首尾空白和尾部 `/`。
- 更新 `web/src/lib/api/client.test.ts`：
  - 新增默认 `/api` 行为测试；
  - 新增自定义 `VITE_API_BASE_URL` 规范化测试。
- 更新 `README.md`：
  - 补充前端开发服务 `host` / `port` 配置方式；
  - 明确同源 `/api`、本地跨端口联调、生产反向代理三种 API 地址场景；
  - 明确 `VITE_*` 变量是公开构建配置，禁止承载 LLM API key、后端 secret 或长期 token。
- 更新 `TASKS.md`，将“建立前端运行端口和 API 地址配置边界”标记为已完成。

### 修改文件
- `web/vite.config.ts`
- `web/src/lib/api/client.ts`
- `web/src/lib/api/client.test.ts`
- `README.md`
- `TASKS.md`
- `WORKLOG.md`

### 根因
- 当前前端虽然已经支持 `VITE_API_BASE_URL`，但 Vite 开发服务的监听 `host` / `port` 没有项目内统一边界。
- `README.md` 只记录了本地通过 `VITE_API_BASE_URL` 直连后端的一个示例，没有覆盖同源 `/api` 和生产反向代理两种主路径，也没有明确 `VITE_*` 变量不能承载 secret。
- 如果继续让这些配置停留在“默认 Vite 行为 + 零散说明”，后续部署时容易把开发联调配置和生产公开配置混在一起，甚至误把敏感配置放进前端构建产物。

### 当前结论
- 前端开发服务现在可通过 `TRMS_WEB_HOST`、`TRMS_WEB_PORT` 显式配置监听地址，且该配置只作用于开发态。
- 前端 API 地址边界现在明确区分：
  - 默认同源 `/api`；
  - 本地跨端口联调使用 `VITE_API_BASE_URL`；
  - 生产优先通过反向代理保持 `/api`，避免把不必要的环境细节硬编码进构建产物。

### 验证结果
- 已通过：
  - `cd web && npm test -- src/lib/api/client.test.ts`
    - 1 个测试文件、5 个测试通过
  - `cd web && npm run build`
    - 构建通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - `pytest` 228 个用例通过
    - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过
    - 前端测试共 18 个测试文件、52 个测试通过
    - `git diff --check` 通过
- 既有警告：
  - `pytest` 仍有 3 条第三方 `DeprecationWarning`，来源于 `HTTP_422_UNPROCESSABLE_ENTITY`
  - 前端测试期间仍打印 Node `--localstorage-file` 既有警告
  这些均为仓库已有现象，本轮未新增相关行为。

### 假设
- 本轮保守假设前端开发服务配置只需要覆盖 Vite `dev server` 的监听 `host` / `port`，不额外引入独立的生产前端端口配置系统。
- 本轮保守假设生产部署推荐同源 `/api` + 反向代理；仅当确实需要跨域部署时，才在构建时写入公开可见的 `VITE_API_BASE_URL`。
- 本轮不新增任何前端 secret 配置入口；后续 OpenAI 兼容 LLM Provider、后端 secret 和对象存储凭据仍应只留在后端配置层处理。

## 2026-04-28 13:44 - Add unified backend runtime configuration

### 完成内容
- 新增 `src/trms_backend/runtime_config.py`，集中解析并校验后端运行配置：
  - `TRMS_ENV`
  - `DATABASE_URL`
  - `MATERIAL_STORAGE_DIR`
  - `TRMS_CORS_ALLOWED_ORIGINS`
  - `TRMS_PUBLIC_API_BASE_URL`
  - `TRMS_API_HOST`
  - `TRMS_API_PORT`
- 更新 `src/trms_backend/main.py`：
  - `create_app()` 改为通过统一配置对象初始化数据库、文件存储和 CORS 中间件；
  - 将运行配置挂到 `app.state.runtime_config`，为后续权限、审计和导出配置收口保留统一入口。
- 新增 `src/trms_backend/__main__.py` 启动入口：
  - 支持 `uv run python -m trms_backend --host ... --port ...`
  - `--host`、`--port` 会覆盖对应环境变量，并在启动前经过统一配置校验。
- 新增 `tests/test_runtime_config.py`，覆盖：
  - 开发环境默认配置；
  - `TRMS_ENV=production` 时缺少必填配置直接报错；
  - 非法端口配置直接报错；
  - 配置过的 CORS 允许源实际生效。
- 更新 `README.md`，补充开发/生产配置说明与启动示例。
- 更新 `TASKS.md`，将“建立统一后端运行配置模型”标记为已完成。

### 修改文件
- `src/trms_backend/runtime_config.py`
- `src/trms_backend/main.py`
- `src/trms_backend/__main__.py`
- `tests/test_runtime_config.py`
- `README.md`
- `TASKS.md`
- `WORKLOG.md`

### 根因
- 当前后端只在 `main.py` 中零散读取 `DATABASE_URL` 和 `MATERIAL_STORAGE_DIR`，其余运行参数没有统一模型，导致：
  - CORS、公开 API base URL、监听 host/port 缺少集中约束；
  - 开发默认值与生产必填值边界不清；
  - 后续接入 LLM Provider、对象存储、部署基线时缺少统一配置入口。
- 继续沿用“在各处直接 `os.getenv()`”会让生产配置散落在多个模块里，既难验证，也容易在生产环境静默回退到开发默认值。

### 当前结论
- 后端运行配置现在已经形成统一模型，开发环境仍保留最小默认值，生产环境则要求显式提供全部关键配置。
- 监听 host/port 现在既可通过环境变量配置，也可通过 `python -m trms_backend --host/--port` 在启动时覆盖，且会经过同一套校验逻辑。

### 验证结果
- 已通过：
  - `uv run pytest tests/test_runtime_config.py tests/test_health_api.py`
    - 5 个测试通过
  - `python3 -m compileall src tests`
    - 编译检查通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - `pytest` 228 个用例通过
    - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过
    - `git diff --check` 通过
- 既有警告：
  - `pytest` 仍有 3 条第三方 `DeprecationWarning`，来源于 `HTTP_422_UNPROCESSABLE_ENTITY`
  - 前端测试期间仍打印 Node `--localstorage-file` 既有警告
  这些均为仓库已有现象，本轮未新增相关行为。

### 假设
- 本轮保守假设“生产环境”由 `TRMS_ENV=production` 明确声明；只有该模式下才禁止静默回退到开发默认值。
- 本轮保守假设 `TRMS_PUBLIC_API_BASE_URL` 是后端对外公开的绝对 API 前缀，允许带 `/api` 路径，但不允许 query 或 fragment。
- 本轮保守假设 CORS 允许源应为不带路径的 `http(s)` origin，因此对带 path 的配置直接视为错误，而不是尝试自动纠正。

## 2026-04-28 13:20 - Refresh acceptance mapping and production readiness gaps

### 完成内容
- 重写 `docs/第一阶段验收映射.md`，按当前代码、测试、Web/CLI 入口和 `TASKS.md` 现状重新标注：
  - FR-001 至 FR-015；
  - AC-001 至 AC-018。
- 在映射文档中新增统一状态定义，明确区分：
  - 已完成；
  - 部分完成；
  - 占位完成；
  - 未开始；
  - 范围外。
- 在同一文档中补齐“生产就绪差距”清单，明确当前仍阻止上线的系统性问题，包括：
  - bearer 身份与权限未收口；
  - 运行配置分散；
  - 真实 OCR / PDF / OpenAI 兼容 LLM 识别链路未接入；
  - 对象存储、导出下载控制、数据库迁移、审计、部署与恢复基线未完成。
- 更新 `TASKS.md`，将“刷新需求验收映射和生产就绪差距清单”标记为已完成。

### 修改文件
- `docs/第一阶段验收映射.md`
- `TASKS.md`

### 根因
- 原 `docs/第一阶段验收映射.md` 只覆盖 AC-001 至 AC-018，且内容明显滞后于当前仓库状态。
- 当前仓库已经新增：
  - Web 管理/成员页面；
  - CLI 登录、任务查询、提交、状态查询、缺失材料查看和费用确认；
  - Telegram / 邮件入站占位；
  - 识别任务历史、人工更正、复核总览、导出任务与 PDF 合并计划。
- 如果继续沿用旧映射，会把若干已实现能力误记为未开始，也会把“占位完成”与“可生产使用完成”混为一谈，无法指导后续 P3 任务。

### 当前结论
- 当前系统的第一阶段功能覆盖已经明显超过旧映射文档描述，特别是在 CLI、复核视图、缺失材料聚合和基础导出方面。
- 但当前系统仍不能描述为生产就绪，主要阻断点仍是统一鉴权、真实识别链路、对象存储/迁移、审计与部署恢复基线。

### 验证结果
- 已通过：
  - `./scripts/verify.sh`
    - Python 编译检查通过；
    - `pytest` 224 个用例通过；
    - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过；
    - `git diff --check` 通过。
- 既有警告：
  - `pytest` 仍有 3 条第三方 `DeprecationWarning`，来源于 `HTTP_422_UNPROCESSABLE_ENTITY`；
  - 前端测试期间仍打印 Node `--localstorage-file` 既有警告。
  这些均为仓库已有现象，本轮未新增相关行为。

### 假设
- 本轮将“已完成”定义为“第一阶段功能行为已有代码和测试依据”，不等同于“可直接生产上线”。
- 对 Telegram、邮件、识别和导出相关能力的状态判断，按“仓库内是否已经形成真实外部链路”区分“部分完成”和“占位完成”，避免把接入边界误记为真实交付。

## 2026-04-28 13:18 - Analyze production readiness and extend task list

### 完成内容
- 对照需求文档 V0.2、架构设计 V0.1、README、当前 `TASKS.md` 和代码入口，完成当前系统生产就绪性分析。
- 确认当前系统不能上生产环境：
  - AI/OCR/LLM 识别仍主要是任务、结果和人工录入边界，未接入真实 OpenAI 兼容 LLM Provider；
  - Web 登录已具备基础账号闭环，但业务 API 仍存在 `actor_id` / `submitter_id` / `member_id` 由前端或调用方自报的迁移边界；
  - 注册流程仍允许用户选择角色，生产环境下不能允许任意注册管理员或系统管理员；
  - 端口、CORS、公开 API base URL、LLM `api_key` / `base_url` / `model`、对象存储、worker 等生产运行配置未形成统一配置模型；
  - 数据库仍使用 `create_all` 建表策略，缺少生产迁移机制；
  - 原始文件默认本地存储，缺少 S3/MinIO 等对象存储适配、下载鉴权和备份恢复演练；
  - 审计日志、请求 ID、指标、权限越权回归和上线部署基线仍在未完成任务中。
- 更新 `TASKS.md`，新增“P3 - 生产配置、真实识别与部署补齐”任务组，覆盖：
  - 刷新验收映射和生产差距清单；
  - 后端与前端端口/API 地址配置；
  - OpenAI 兼容 LLM API key/base URL/model 配置；
  - PDF 文本提取、LLM 结构化识别、异步 worker；
  - Alembic 迁移、对象存储、生产账号注册策略、Docker Compose 部署和上线前演练。

### 修改文件
- `TASKS.md`
- `WORKLOG.md`

### 根因
- 当前 `TASKS.md` 已覆盖大量第一阶段业务功能，但其中一部分是“占位/边界/骨架”完成，不等同于生产环境可用。
- 需求文档明确要求 AI Agent 识别、基础权限、操作日志、数据备份和多渠道可用；架构文档进一步要求对象存储、异步任务队列、审计日志、私有文件访问、生产部署和敏感配置管理。
- 用户追加要求“系统前后端端口可以配置，以及配置 OpenAI 兼容的 LLM API key/base url”，当前仓库仅有 `DATABASE_URL`、`MATERIAL_STORAGE_DIR`、`VITE_API_BASE_URL`、CLI base URL 等零散配置，缺少统一生产配置和 LLM Provider 配置。

### 当前结论
- 当前系统适合继续作为本地开发和第一阶段闭环验证基础，不适合直接上生产环境。
- 现有未完成任务可以覆盖权限、审计、可观测性和测试质量的一部分，但不能完全补齐生产上线要求；新增任务完成后，任务队列才覆盖“满足需求文档并可上线”的必要边界。

### 验证结果
- 首次在沙箱内运行 `./scripts/verify.sh` 失败：
  - `uv` 需要写入 `/home/gsh/.cache/uv`，当前沙箱对该路径只读；
  - 该失败是环境权限问题，不是代码或文档变更导致。
- 已在获批的沙箱外环境通过：
  - `./scripts/verify.sh`
    - Python 编译检查通过；
    - `pytest` 224 个用例通过；
    - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过；
    - `git diff --check` 通过。
- 既有警告：
  - `pytest` 仍有 3 条第三方 `DeprecationWarning`，来源于 `HTTP_422_UNPROCESSABLE_ENTITY`；
  - 前端测试期间仍打印 Node `--localstorage-file` 既有警告。

### 假设
- “上生产环境”按至少小规模内网生产使用理解，需要真实持久化数据库、私有文件存储、身份权限收口、审计、备份恢复、部署基线、可配置端口和外部 LLM 配置，不接受开发调试入口和本地 `create_all` 作为生产方案。
- OpenAI 兼容 LLM Provider 只要求兼容接口配置和可替换 Provider，不要求把 API key 写入数据库或前端配置。

## 2026-04-28 12:56 - Add username password account auth

### 完成内容
- 新增后端基础账号认证闭环：
  - `POST /api/auth/register` 注册用户名密码账号并返回 bearer session；
  - `POST /api/auth/login` 校验用户名密码并返回新 session；
  - `GET /api/auth/me` 通过 bearer token 恢复当前用户；
  - `POST /api/auth/logout` 吊销当前 token。
- 新增 `user_accounts` 与 `auth_sessions` 表模型：
  - 密码使用 PBKDF2-SHA256 加盐哈希保存；
  - session 只保存 token hash，不保存明文 token；
  - 用户身份包含 `role`、`actor_id`、`display_name`、可选 `member_code`。
- 前端登录页从纯 mock 角色入口升级为账号登录/注册表单：
  - 注册/登录成功后保存后端返回的 bearer token 和用户身份；
  - 既有成员、管理员、系统管理员业务页面继续通过统一 `useAuthSession()` 读取角色和 `actorId`；
  - 保留开发调试角色入口，仅用于现有页面测试和本地调试。
- 更新 `TASKS.md`：
  - 新增并完成“实现用户名密码注册登录基础闭环”；
  - 新增后续任务“将 Web 业务 API 迁移到 bearer 身份上下文”；
  - 保留“建立最小请求身份上下文占位”和“基础权限控制”为后续未完成工作，避免把当前登录能力伪装成全量权限收口。
- 更新 `README.md`，记录账号 API、前端 API 地址配置和当前权限迁移限制。

### 修改文件
- `src/trms_backend/domain/auth.py`
- `src/trms_backend/api/auth.py`
- `src/trms_backend/infrastructure/models.py`
- `src/trms_backend/infrastructure/repositories.py`
- `src/trms_backend/main.py`
- `tests/test_auth_api.py`
- `web/src/app/auth-store.ts`
- `web/src/app/auth.tsx`
- `web/src/app/pages.tsx`
- `web/src/app/App.test.tsx`
- `web/src/lib/api/trms.ts`
- `web/src/lib/api/types.ts`
- `TASKS.md`
- `README.md`
- `WORKLOG.md`

### 根因
- 现有 Web 端只有本地 mock 角色会话，无法交付一个可用的基础系统；用户无法注册账号、登录、退出或恢复后端会话。
- 架构文档第 5.1 节已要求 Web 端优先支持账号密码或轻量 OAuth，并且当前 `TASKS.md` 已进入 P3 权限与身份收口阶段。
- 如果继续让业务页面只依赖 mock 身份，后续权限控制、审计和 Web 真实使用都会缺少可信用户来源。

### 验证结果
- 已通过：
  - `uv run pytest tests/test_auth_api.py`
    - 5 个认证 API 测试通过
  - `cd web && npm run lint && npm test`
    - 前端 lint 通过
    - 18 个前端测试文件、50 个测试通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - `pytest` 224 个用例通过
    - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过
    - `git diff --check` 通过
- 既有警告：
  - `pytest` 仍有 3 条第三方 `DeprecationWarning`，来源于 `HTTP_422_UNPROCESSABLE_ENTITY`；
  - 前端测试期间仍打印 Node `--localstorage-file` 既有警告。
  这些均为仓库已有现象，本轮未新增相关行为。

### 假设
- 当前保守假设第一阶段允许用户在注册时选择 `member`、`admin` 或 `system_admin` 角色；这解决本地可用性，不等同于生产级管理员邀请或审批机制。
- 当前 `actor_id` 仍由注册表单提供或默认使用用户名，目的是兼容既有业务页面和 API；后续需要把业务 API 从前端自报身份迁移到 bearer token 解析出的身份上下文。
- 当前不新增第三方密码库，使用 Python 标准库 PBKDF2-SHA256，避免为基础闭环引入额外依赖；若进入正式部署，应进一步评估密码策略、速率限制、管理员初始化和账号禁用机制。

### 后续建议
- 下一轮优先继续 `TASKS.md` 中“建立最小请求身份上下文占位”，把已实现的账号 token 接入统一请求身份依赖。
- 随后推进“将 Web 业务 API 迁移到 bearer 身份上下文”，避免继续扩大 `actor_id` / `submitter_id` 由前端自报的范围。

## 2026-04-28 12:35 - Add email material submission placeholder

### 完成内容
- 新增 `src/trms_backend/application/email_material_submission.py`，建立 `EmailMaterialSubmissionService`：
  - 解析格式化邮件主题和正文元数据，固化 `[TRMS] task:<task_id>`、`material_type`、可选 `submitter_id` / `task_id` / `note` 的最小边界；
  - 对 `invalid_subject_prefix`、`missing_task_id`、`duplicate_task_id_marker`、`missing_metadata_block`、`missing_material_type`、`unsupported_material_type`、`task_id_mismatch` 等格式错误显式抛出稳定失败码；
  - 已有 `resolved_member_id` 且任务存在时，复用统一 `MaterialSubmissionService.submit_to_task`；
  - 发件人未解析到成员身份，或主题里的任务编号在系统内不存在时，复用 `submit_pending_assignment`，把邮件转入待归属材料主链路而不是静默丢弃或直接 404。
- 新增 `src/trms_backend/api/email_materials.py`，提供 `/api/email/materials` 占位入站接口：
  - 接口只接收 `sender_email`、`subject`、`body`、可选 `resolved_member_id` 和附件；
  - 对缺少附件返回 `missing_attachments`；
  - 对附件缺少文件名的逐文件失败结果映射为 `attachment_missing_filename`，并保留现有批量部分成功语义。
- 更新 `src/trms_backend/main.py`，把邮件接入占位路由接入主应用。
- 新增 `tests/test_email_materials_api.py`，覆盖：
  - 已解析成员身份时进入已归属材料主链路；
  - 未解析成员身份时进入待归属材料；
  - 主题任务不存在时进入待归属材料；
  - 主题前缀错误、正文 `task_id` 不一致等格式错误返回稳定失败码；
  - 合法附件与缺少文件名附件混合时返回 `partial_success`。
- 更新 `TASKS.md`，将“增加邮件材料提交接入占位”标记为已完成。

### 修改文件
- `src/trms_backend/application/email_material_submission.py`
- `src/trms_backend/api/email_materials.py`
- `src/trms_backend/main.py`
- `tests/test_email_materials_api.py`
- `TASKS.md`
- `WORKLOG.md`

### 根因
- 需求文档 FR-002、异常场景 30 和架构文档中的邮件接入边界都要求“格式化邮件提交”进入统一材料池，并在格式错误时返回明确失败原因。
- 上一轮虽然已经冻结了邮件主题/正文/附件规范，但仓库里仍然没有任何“邮件入站 -> 统一材料提交服务”的接线层。
- 如果继续缺这层占位，后续真实 IMAP 或邮件网关接入只能在适配器里临时发明主题解析、失败码和待归属策略，容易绕过既有 `MaterialSubmissionService`，也会让“任务不存在时应待归属而不是丢件”的需求边界失真。

### 验证结果
- 已通过：
  - `uv run pytest tests/test_email_materials_api.py tests/test_materials_api.py tests/test_telegram_materials_api.py`
    - 31 个相关后端测试通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - `pytest` 219 个用例通过
    - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过
    - `git diff --check` 通过
- 既有警告：
  - `pytest` 仍有 3 条第三方 `DeprecationWarning`，来源于 `HTTP_422_UNPROCESSABLE_ENTITY`；
  - 前端测试期间仍打印 Node `--localstorage-file` 既有警告。
  这些均为仓库已有现象，本轮未新增相关行为。

### 假设
- 当前保守假设邮件接入占位不实现邮箱绑定持久化；`resolved_member_id` 由未来真实邮件适配器在进入该接口前解析得到，本轮只固化“已解析身份/未解析身份”两条主链路。
- 当前保守假设邮件主题中的 `task_id` 是唯一权威任务来源；正文中的 `task_id` 只做冗余校验，不参与自动纠错。
- 由于现有待归属材料模型只有一个 `submitter_id_hint` 字段，本轮将“发件人邮箱 + 可选正文 `submitter_id` 线索”串成单个字符串保存，供后续管理员认领时参考。
- 当前保守假设邮件元数据中的 `material_type: other` 需要兼容映射到现有领域枚举 `other_attachment`，以保持邮件规范文档与现有后端材料类型边界一致。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“建立最小请求身份上下文占位”，不要在当前邮件占位基础上提前扩展真实邮箱绑定、IMAP 轮询或 SMTP 回执。

## 2026-04-28 12:26 - Define formatted email submission specification

### 完成内容
- 新增 `docs/格式化邮件提交规范说明.md`，固化第一阶段邮件渠道的最小格式化约束：
  - 规定主题必须使用 `[TRMS] task:<task_id>` 格式，并把主题中的 `task_id` 作为权威任务编号来源；
  - 规定正文开头使用连续 `key: value` 元数据块，至少包含 `material_type`，并定义 `submitter_id`、`task_id`、`note` 的用途和边界；
  - 规定附件必须至少有一个普通附件、同一封邮件只允许一种 `material_type`，并沿用统一材料上传规则处理大小、空文件和内容类型校验；
  - 列出稳定失败码，区分“格式错误”与“格式合法但无法直接归属”的场景，明确后者应进入既有待归属或权限校验路径。
- 更新 `TASKS.md`，将“定义格式化邮件提交规范”标记为已完成。

### 修改文件
- `docs/格式化邮件提交规范说明.md`
- `TASKS.md`
- `WORKLOG.md`

### 根因
- 需求文档中的 `Q-007` 和架构文档中的 `A-005` 都明确指出邮件格式规范尚未定义，而下一项任务已经是“增加邮件材料提交接入占位”。
- 如果在格式未冻结前直接做邮件入站占位，后续接入器就只能在解析逻辑里临时猜主题、正文和附件语义，容易出现：
  - 任务编号来源不一致；
  - 一封邮件混入多种材料类型；
  - 格式错误邮件被静默丢弃；
  - 邮件接入层自行发明业务特判，破坏统一材料提交边界。

### 验证结果
- 已通过：
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - `pytest` 213 个用例通过
    - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过
    - `git diff --check` 通过
- 既有警告：
  - `pytest` 仍有 3 条第三方 `DeprecationWarning`，来源于 `HTTP_422_UNPROCESSABLE_ENTITY`；
  - 前端测试期间仍打印 Node `--localstorage-file` 既有警告。
  这些均为仓库已有现象，本轮未新增相关行为。

### 假设
- 当前保守假设一封格式化邮件只提交一种 `material_type`；如果成员需要同时提交发票和支付记录，应拆成多封邮件，而不是在邮件接入器里做按附件逐类推断。
- 当前保守假设发件人邮箱是邮件渠道的首选身份线索；正文中的 `submitter_id` 只作为待归属认领线索，不直接绕过后续成员校验。
- 当前保守假设主题中的 `task_id` 为权威来源，正文中的 `task_id` 仅用于冗余校验；若两者不一致，按格式错误处理，而不是自动猜测取其一。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“增加邮件材料提交接入占位”，只实现格式解析、失败码映射和统一材料提交服务接线，不提前实现真实 IMAP 轮询、SMTP 回执或邮箱绑定体系。

## 2026-04-28 12:24 - Add Telegram material submission placeholder

### 完成内容
- 新增 `src/trms_backend/application/telegram_material_submission.py`，建立 `TelegramMaterialSubmissionService`：
  - 先复用既有 Telegram 账号绑定解析边界判断 `bound` / `pending_assignment`；
  - 已绑定且已提供 `task_id` 时，直接调用统一 `MaterialSubmissionService.submit_to_task`；
  - 未绑定账号或尚未确定任务时，统一转入 `submit_pending_assignment`，并保留 `task_id_hint` 与 Telegram 身份线索。
- 新增 `src/trms_backend/api/telegram_materials.py`，提供 `/api/telegram/materials` 占位入站接口：
  - 接口只接收 `telegram_user_id`、可选 `telegram_username`、可选 `task_id`、材料类型和附件；
  - 不接入真实 Telegram Bot、Webhook 签名校验或 Bot Token 管理，只固定后端接入边界。
- 新增 `src/trms_backend/api/material_submission_http.py`，把多文件上传读取和批量成功/部分成功/失败响应拼装从 `api/materials.py` 抽成共享辅助函数，避免 Telegram 接入器复制一套 HTTP 结果映射逻辑。
- 新增 `tests/test_telegram_materials_api.py`，覆盖：
  - 已绑定账号且任务明确时进入已归属材料主链路；
  - 未绑定账号时进入待归属材料；
  - 已绑定账号但未提供任务时仍进入待归属，锁定“任务未识别不强行归档”的边界。
- 更新 `src/trms_backend/main.py` 接入 Telegram 材料占位路由，并将 `TASKS.md` 中“增加 Telegram 材料提交接入占位”标记为已完成。

### 修改文件
- `src/trms_backend/api/material_submission_http.py`
- `src/trms_backend/api/materials.py`
- `src/trms_backend/api/telegram_materials.py`
- `src/trms_backend/application/telegram_material_submission.py`
- `src/trms_backend/main.py`
- `tests/test_telegram_materials_api.py`
- `TASKS.md`
- `WORKLOG.md`

### 根因
- 虽然上一轮已经建立了统一材料提交服务和 Telegram 账号绑定模型，但仓库里仍然没有一个明确的“Telegram 入站材料 -> 统一材料流程”的接入边界。
- 如果继续缺这层占位，后续真实 Telegram Webhook 接入只能在 API 层或 Bot 适配层临时拼任务/成员分流逻辑，容易复制上传响应处理、绕过既有 `MaterialSubmissionService`，并破坏“渠道层只负责接入”的架构约束。

### 验证结果
- 已通过：
  - `uv run pytest tests/test_telegram_materials_api.py tests/test_telegram_bindings_api.py tests/test_material_submission_service.py tests/test_materials_api.py`
    - 30 个相关后端测试通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - `pytest` 213 个用例通过
    - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过
    - `git diff --check` 通过
- 既有警告：
  - `pytest` 仍有 3 条第三方 `DeprecationWarning`，来源于 `HTTP_422_UNPROCESSABLE_ENTITY`；
  - 前端测试期间仍打印 Node `--localstorage-file` 既有警告。
  这些均为仓库已有现象，本轮未新增相关行为。

### 假设
- 当前保守假设 Telegram 占位接口只需要固化“账号身份解析 + 任务是否明确”的分流逻辑，不需要在本轮实现真实 Bot Webhook、消息轮询或 Telegram 平台签名校验。
- 对未绑定 Telegram 账号，当前将原始外部身份线索保存在 `submitter_id_hint`，格式为 `telegram_user_id:<id>` 或 `telegram_user_id:<id> (@username)`；该字段在待归属阶段被视为人工认领线索，而不是已确认的成员 ID。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“定义格式化邮件提交规范”，先把邮件主题、任务编号、正文元数据和附件约束写死，再接入邮件入站占位。

## 2026-04-28 12:14 - Establish unified channel material submission boundary

### 完成内容
- 新增 `src/trms_backend/application/material_submission.py`，把材料提交主链路从 `api/materials.py` 抽为独立应用服务：
  - 统一处理文件校验、批量部分成功语义、原始文件存储、材料记录创建和识别任务占位创建；
  - 提供 `submit_to_task` 和 `submit_pending_assignment` 两个入口，分别覆盖“已识别任务/成员”的提交和“待归属材料”的提交。
- 调整 `src/trms_backend/api/materials.py`：
  - 路由层只保留 HTTP 参数解析、`UploadFile` 读取和错误映射；
  - `/api/tasks/{task_id}/materials` 与 `/api/materials/pending-assignment` 都改为调用统一服务，不再各自拼装材料创建逻辑。
- 调整 `src/trms_backend/main.py`，在应用启动时集中构造 `MaterialSubmissionService` 并注入材料路由，明确后续 Telegram/邮件入口应复用同一服务边界。
- 新增 `tests/test_material_submission_service.py`，覆盖：
  - Web、CLI、Telegram、Email 四种 `channel` 走同一“已归属材料提交”主链路；
  - 待归属提交不会在渠道层派生独立业务规则，而是统一进入 `pending_assignment` 路径。
- 更新 `TASKS.md`，将“建立渠道提交统一入口边界”标记为已完成。

### 修改文件
- `src/trms_backend/application/__init__.py`
- `src/trms_backend/application/material_submission.py`
- `src/trms_backend/api/materials.py`
- `src/trms_backend/main.py`
- `tests/test_material_submission_service.py`
- `TASKS.md`
- `WORKLOG.md`

### 根因
- 当前仓库虽然已经让 Web、CLI、待归属材料共用同一数据库模型，但真正的材料提交主链路仍然堆在 `api/materials.py`：
  - 文件校验、批量失败处理、存储、材料创建和识别任务占位都由路由直接编排；
  - `/api/tasks/{task_id}/materials` 和 `/api/materials/pending-assignment` 各自维护一份近似逻辑。
- 这种结构会把后续 Telegram 和邮件接入逼到 API 层复制业务规则，违背需求文档和架构文档中“渠道只负责接入，不各自实现业务主流程”的边界。

### 验证结果
- 已通过：
  - `uv run pytest tests/test_material_submission_service.py tests/test_materials_api.py tests/test_cli_submit.py`
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - `pytest` 207 个用例通过
    - `cd web && npm run lint` 通过
    - `cd web && npm test` 通过，18 个前端测试文件、50 个测试通过
    - `cd web && npm run build` 通过
    - `git diff --check` 通过

### 说明
- 本轮只建立统一材料提交服务边界，没有提前实现下一项“Telegram 账号绑定模型”，也没有实现真实 Telegram Bot、邮件收取或渠道身份绑定。
- `./scripts/verify.sh` 期间仍出现两类既有警告：
  - `pytest` 中 3 条第三方 `DeprecationWarning`，来源于 `HTTP_422_UNPROCESSABLE_ENTITY`；
  - 前端测试期间若干 Node `--localstorage-file` 警告。
  这些警告均为既有现象，本轮未新增相关行为。

### 假设
- 当前保守假设“统一渠道提交入口边界”的最小闭环是：
  - 所有渠道最终都调用同一个后端材料提交服务；
  - 渠道层只负责拿到文件、渠道标识和可选身份/任务提示，不在渠道层复制成员校验、文件存储、识别任务创建或批量失败语义。
- 当前尚未接入真实 Telegram/邮件适配器，因此本轮通过服务注入边界和服务层测试来锁定未来调用方式；后续渠道实现应直接复用该服务，而不是重新实现一套材料提交流程。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“建立 Telegram 账号绑定模型”，并让未绑定 Telegram 账号的材料通过本轮建立的 `submit_pending_assignment` 路径进入待归属状态。

## 2026-04-28 12:10 - Evaluate CLI recursive directory upload

### 完成内容
- 阅读 `TASKS.md`、近期 `WORKLOG.md`、需求分析文档中的 FR-012、第 7 节 CLI 能力表和 Q-012，以及架构文档的 CLI 模块边界。
- 结论：`CLI 目录递归上传` 继续保留为第一阶段 `Could` 能力，不并入当前 `Must` / `Should` 主链路，也不降级为第一阶段 `Won't have`。
- 更新 `TASKS.md`：
  - 将“评估 CLI 目录递归上传”标记为已完成；
  - 在 `P4 - Could 与后续增强评估` 区域新增独立后续任务“实现 CLI 目录递归上传”，避免把 `Could` 功能插到 Telegram、权限和审计等更高优先级任务之前。

### 修改文件
- `TASKS.md`
- `WORKLOG.md`

### 根因
- 需求文档已明确把“目录递归上传”列为 CLI `Could` 能力，而不是 `Must` 或 `Won't have`，但任务队列里此前只有评估项，没有明确保留/放弃结论，也没有拆出后续独立任务。
- 当前 CLI `submit` 已形成“显式文件列表 -> 本地预检查 -> 后端批量上传 -> 逐文件结果输出”的稳定闭环；目录递归上传若直接混入当前任务，会额外引入本地遍历语义：
  - 目录展开顺序；
  - 是否跟随符号链接；
  - 遇到目录内不支持文件、不可读文件时如何并入现有 `partial_success` / `failed` 结果；
  - 跨平台路径处理边界。
- 这些问题都属于 CLI 本地文件发现层，不要求扩展后端业务规则，因此适合作为后续独立 `Could` 实现任务，而不是在本轮评估任务里顺手实现。

### 验证结果
- 已通过：
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - `pytest` 205 个用例通过
    - `cd web && npm run lint` 通过
    - `cd web && npm test` 通过，18 个前端测试文件、50 个测试通过
    - `cd web && npm run build` 通过
    - `git diff --check` 通过

### 说明
- 本轮只完成范围评估和任务拆分，没有实现目录递归上传，也没有改动 CLI、后端或测试业务逻辑。
- `./scripts/verify.sh` 期间仍出现两类既有警告：
  - `pytest` 中 3 条第三方 `DeprecationWarning`，来源于 `HTTP_422_UNPROCESSABLE_ENTITY`；
  - 前端测试期间若干 Node `--localstorage-file` 警告。
  这些警告均为既有现象，本轮未新增相关行为。

### 假设
- 当前保守假设后续若实现目录递归上传，应继续遵守既有 CLI 边界：
  - 只扩展本地文件发现与预检查；
  - 不在 CLI 复制服务端材料归属、重复判断或校验规则；
  - 递归发现出的本地失败项继续并入现有批量上传结果模型。

### 后续建议
- 下一轮继续按 `TASKS.md` 顺序处理 `P2 - Telegram 与邮件渠道` 中的“建立渠道提交统一入口边界”，不要因为递归上传已保留为 `Could` 就提前改变高优先级任务顺序。

## 2026-04-28 12:05 - Record CLI compatibility strategy

### 完成内容
- 为 `src/trms_cli/cli.py` 增加统一 CLI 协商请求头：
  - `X-TRMS-Client: cli`
  - `X-TRMS-CLI-Version: 1`
  - `X-TRMS-CLI-Capabilities: ...`
- 让 `health`、`tasks`、`submit`、`status`、`missing-materials`、`split`、`confirm-expense` 全部复用同一请求头构造函数，避免不同命令各自维护版本协商口径。
- 为 `src/trms_backend/main.py` 增加轻量 CLI 兼容检查中间件，并新增 `src/trms_backend/api/cli_compatibility.py`：
  - 仅对显式声明 `X-TRMS-Client: cli` 的请求生效；
  - 当 `X-TRMS-CLI-Version` 缺失、不可解析或小于最小支持版本时，返回 `426 Upgrade Required`；
  - 错误响应包含 `code=cli_version_too_old`、`detail`、`minimum_supported_cli_version` 和 `received_cli_version`。
- 新增 `docs/CLI版本兼容策略说明.md`，记录：
  - 当前 CLI 协议版本和能力标识；
  - 服务端如何返回“版本过旧”错误；
  - `--json` 输出的破坏性变更升级规则。
- 新增/更新测试：
  - `tests/test_cli_compatibility_api.py` 覆盖服务端接受当前 CLI 版本、拒绝过旧 CLI 版本；
  - 更新 CLI 命令测试，覆盖所有已实现命令都会携带统一兼容协商请求头。
- 将 `TASKS.md` 中“记录 CLI 版本兼容策略”标记为已完成。

### 修改文件
- `src/trms_backend/api/cli_compatibility.py`
- `src/trms_backend/main.py`
- `src/trms_cli/cli.py`
- `docs/CLI版本兼容策略说明.md`
- `tests/test_cli_compatibility_api.py`
- `tests/test_cli_health.py`
- `tests/test_cli_tasks.py`
- `tests/test_cli_submit.py`
- `tests/test_cli_status.py`
- `tests/test_cli_missing_materials.py`
- `tests/test_cli_split.py`
- `tests/test_cli_confirm_expense.py`
- `TASKS.md`
- `WORKLOG.md`

### 根因
- 当前 CLI 功能已经覆盖上传、状态、分摊和确认，但客户端与服务端之间没有显式兼容协商：
  - 服务端无法区分“请求来自 CLI”还是“来自其他调用方”；
  - CLI 即使未来新增破坏性协议变更，也没有统一位置声明自己支持哪些能力；
  - `--json` 输出虽然已有 `schema_version`，但缺少明确的升级规则记录，后续很容易在无边界情况下破坏脚本调用。

### 验证结果
- 已通过：
  - `uv run pytest tests/test_cli_compatibility_api.py tests/test_cli_health.py tests/test_cli_tasks.py tests/test_cli_submit.py tests/test_cli_status.py tests/test_cli_missing_materials.py tests/test_cli_split.py tests/test_cli_confirm_expense.py`
  - `./scripts/verify.sh`

### 说明
- 本轮只处理“CLI 版本兼容策略”，没有提前实现下一项“评估 CLI 目录递归上传”。
- 服务端当前只对显式声明 `X-TRMS-Client: cli` 的请求做兼容门禁，不会把普通 Web/API 请求误判为 CLI。

### 假设
- 本轮保守假设“CLI 兼容版本”先使用独立整数协议版本 `1`，而不是直接复用 Python 包版本 `0.1.0`：
  - 当前仓库没有独立 CLI 发版链路，协议版本更适合表达“是否能和当前服务端正常对话”；
  - 后续即使 CLI 包版本前进，只要请求/响应契约不破坏，也不需要同步升级协议版本。
- 当前最小闭环先只做到“声明式门禁”：
  - 新 CLI 稳定发送版本头和能力头；
  - 真正完全不发送这些请求头的历史客户端，服务端暂时无法仅凭通用 REST 路径与非 CLI 调用方完全区分。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“评估 CLI 目录递归上传”，先判断它是否属于第一阶段 Could 功能，再决定是否拆独立实现任务。

## 2026-04-28 11:46 - Add CLI expense confirmation

### 完成内容
- 为 `src/trms_cli/cli.py` 新增独立 `confirm-expense` 命令：
  - 仅传 `--task-id` 时，从已登录 session 读取 `base_url`、`member_id` 和 access token，调用后端既有 `GET /api/tasks/{task_id}/expense-details` 接口列出本人当前费用明细；
  - 传 `--split-id --split-version --status` 时，调用后端既有 `PUT /api/splits/{split_id}/confirmation` 接口提交确认或异议；
  - `disputed` 状态要求显式传入 `--dispute-reason`，避免把空异议原因提交给服务端。
- 固化命令输出契约：
  - 文本模式按任务输出费用明细数量、总金额、`split_id`、`split_version`、发票号、金额和当前确认状态；
  - `--json` 模式区分 `mode=list` 和 `mode=submit`，分别输出结构化明细列表或确认结果。
- 增加版本过旧保护：
  - 提交确认前先重新拉取当前费用明细；
  - 若目标 `split_id` 已不再可见，或当前 `split_version` 与用户传入版本不一致，CLI 直接提示重新拉取，不把旧明细静默当作当前版本。
- 新增 `tests/test_cli_confirm_expense.py`，覆盖：
  - 文本模式列出本人费用明细；
  - `--json` 模式提交确认；
  - 提交异议说明；
  - 明细版本过旧时拒绝提交并提示刷新；
  - 未登录 session 时的错误输出。
- 将 `TASKS.md` 中“增加 CLI 个人费用确认能力”标记为已完成。

### 修改文件
- `src/trms_cli/cli.py`
- `tests/test_cli_confirm_expense.py`
- `TASKS.md`
- `WORKLOG.md`

### 根因
- 当前 CLI 已支持成员查询综合状态、缺失材料和分摊提交，但仍缺少“查看本人费用明细并完成确认”的闭环入口。
- 费用确认链路的关键约束不是简单调用确认接口，而是成员确认必须绑定到自己刚查看过的费用明细版本：
  - 现有 CLI 没有独立明细列表输出，成员看不到 `split_version`；
  - 现有 CLI 也没有在提交前校验“我现在要确认的是否还是刚才那版明细”，因此无法在分摊已变化时给出明确的重新拉取提示。

### 验证结果
- 已通过：
  - `uv run pytest tests/test_cli_confirm_expense.py`
    - 5 个 CLI 费用确认命令测试通过
  - `uv run pytest tests/test_expense_details_api.py tests/test_confirmations_api.py`
    - 11 个费用明细/确认 API 测试通过
  - `uv run pytest tests/test_cli_status.py`
    - 3 个 CLI 状态查询回归测试通过
  - `uv run pytest tests/test_cli_split.py`
    - 4 个 CLI 分摊提交回归测试通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - pytest 203 个用例通过
    - `cd web && npm run lint` 通过
    - `cd web && npm test` 通过，18 个前端测试文件、50 个测试通过
    - `cd web && npm run build` 通过
    - `git diff --check` 通过

### 说明
- 本轮只处理“CLI 个人费用确认能力”，没有提前实现下一项“记录 CLI 版本兼容策略”。
- CLI 继续复用后端既有费用明细与确认接口，没有在本地复制“谁能确认谁、确认状态是否合法”这类服务端业务规则。
- `./scripts/verify.sh` 期间 pytest 仍有 3 条既有 `DeprecationWarning`，来源于第三方栈内对 `HTTP_422_UNPROCESSABLE_ENTITY` 的使用，不是本轮新增问题。
- 前端测试期间仍打印 Node `--localstorage-file` 既有警告，但 lint、测试和构建均通过，本轮未新增对此行为的依赖。

### 假设
- 本轮保守假设“CLI 版本过旧提示”的最小闭环是：
  - 提交前重新拉取一次当前费用明细；
  - 以 `split_id + split_version` 比对用户正在确认的对象是否还是刚看到的那一版。
- 当前后端确认接口仍未提供显式 `expected_split_version` 的原子校验，因此 CLI 可以在提交前发现大多数陈旧视图，但不能单靠客户端彻底消除“拉取后到提交前又发生并发变更”的竞态。本轮先不扩展后端协议，后续若要彻底封闭该竞态，应在服务端增加基于版本号的乐观并发校验。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“记录 CLI 版本兼容策略”，优先明确客户端能力标识和服务端版本过旧错误语义，再决定是否需要补专用请求头或查询参数。

## 2026-04-28 11:36 - Add CLI split submission

### 完成内容
- 为 `src/trms_cli/cli.py` 新增独立 `split` 命令：
  - 从已登录 session 读取 `base_url`、`member_id` 和 access token；
  - 调用后端既有 `PUT /api/invoices/{invoice_id}/splits` 接口替换发票分摊；
  - 使用重复 `--member MEMBER_ID:AMOUNT_CENTS` 参数提交一个或多个分摊项。
- 固化命令输出契约：
  - 文本模式按发票输出分摊数量和逐项列表；
  - `--json` 模式输出 `schema_version`、`invoice_id`、`member_id`、`item_count` 和结构化 `items`。
- 新增 `tests/test_cli_split.py`，覆盖：
  - 文本模式成功提交分摊；
  - `--json` 模式结构化输出；
  - 分摊金额合计不匹配时透传服务端 `409` 错误；
  - 未登录 session 时的错误输出。
- 将 `TASKS.md` 中“增加 CLI 分摊提交能力”标记为已完成。

### 修改文件
- `src/trms_cli/cli.py`
- `tests/test_cli_split.py`
- `TASKS.md`
- `WORKLOG.md`

### 根因
- 当前 CLI 已支持成员登录、查询任务、上传材料、查看状态和缺失材料，但成员仍无法通过 CLI 直接补充分摊信息。
- 后端分摊接口和金额一致性约束已经存在，CLI 缺的只是最小接入层：
  - 没有面向成员的命令把分摊参数组织成后端请求；
  - 没有稳定的文本和 JSON 输出契约用于反馈分摊结果；
  - 没有显式证明“金额合计不匹配”由服务端裁决，而不是在 CLI 复制业务规则。

### 验证结果
- 已通过：
  - `uv run pytest tests/test_cli_split.py`
    - 4 个 CLI 分摊命令测试通过
  - `uv run pytest tests/test_splits_api.py`
    - 10 个分摊 API 测试通过
  - `uv run pytest tests/test_cli_submit.py tests/test_cli_status.py tests/test_cli_missing_materials.py tests/test_cli_tasks.py tests/test_cli_login.py`
    - 21 个相邻 CLI 回归测试通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - pytest 198 个用例通过
    - `cd web && npm run lint` 通过
    - `cd web && npm test` 通过，18 个前端测试文件、50 个测试通过
    - `cd web && npm run build` 通过
    - `git diff --check` 通过

### 说明
- 本轮只处理“CLI 分摊提交能力”，没有提前实现下一项“CLI 个人费用确认能力”。
- CLI 只做参数格式校验和整数分解析，没有复制“金额合计必须等于发票金额”这类服务端业务规则；金额不匹配仍由后端返回明确错误。
- `./scripts/verify.sh` 期间 pytest 仍有 3 条既有 `DeprecationWarning`，来源于第三方栈内对 `HTTP_422_UNPROCESSABLE_ENTITY` 的使用，不是本轮新增问题。
- 前端测试期间仍打印 Node `--localstorage-file` 既有警告，但 lint、测试和构建均通过，本轮未新增对此行为的依赖。

### 假设
- 本轮保守假设第一阶段 CLI 分摊的最小输入格式是重复 `--member MEMBER_ID:AMOUNT_CENTS`：
  - 先满足成员通过 CLI 替换整张发票的分摊列表；
  - 分摊备注 `note`、从文件导入分摊明细等更复杂输入留给后续独立任务。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“增加 CLI 个人费用确认能力”，优先复用已有费用明细与确认接口，避免在 CLI 侧重新拼装确认状态机。

## 2026-04-28 11:30 - Add CLI missing materials query

### 完成内容
- 为 `src/trms_cli/cli.py` 新增独立 `missing-materials` 命令：
  - 从已登录 session 读取 `base_url`、`member_id` 和 access token；
  - 调用后端既有 `GET /api/tasks/{task_id}/missing-materials` 接口；
  - 不再要求成员从综合 `status` 输出里手动筛缺失材料。
- 固化命令输出契约：
  - 文本模式按任务输出本人缺失材料数量和逐项列表；
  - `--json` 模式输出 `schema_version`、`task_id`、`member_id`、`scope`、`count` 和结构化 `items`。
- 新增 `tests/test_cli_missing_materials.py`，覆盖：
  - 有缺失材料时的文本输出；
  - 无缺失材料时的 JSON 输出；
  - 未登录 session 时的错误输出。
- 将 `TASKS.md` 中“增加 CLI 缺失材料查询能力”标记为已完成。

### 修改文件
- `src/trms_cli/cli.py`
- `tests/test_cli_missing_materials.py`
- `TASKS.md`
- `WORKLOG.md`

### 根因
- 上一轮虽然已经实现了 `status` 命令，并在综合状态里包含缺失材料列表，但它的职责是聚合材料识别、校验、缺失项和费用确认四类信息。
- 需求文档的 CLI 流程单独要求“成员通过 CLI 查询缺失材料、异常项和待确认费用”，因此当前 CLI 仍缺一个更聚焦的缺失材料查询入口：
  - 成员只想补材料时，需要先阅读一整段综合状态输出，交互成本偏高；
  - `status` 的 JSON 契约面向综合状态，调用方若只关心缺失材料，仍要额外拆解无关字段。

### 验证结果
- 已通过：
  - `uv run pytest tests/test_cli_missing_materials.py`
    - 3 个 CLI 缺失材料命令测试通过
  - `uv run pytest tests/test_cli_missing_materials.py tests/test_cli_status.py`
    - 6 个 CLI 状态/缺失材料相关测试通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - pytest 194 个用例通过
    - `cd web && npm run lint` 通过
    - `cd web && npm test` 通过，18 个前端测试文件、50 个测试通过
    - `cd web && npm run build` 通过
    - `git diff --check` 通过

### 说明
- 本轮只处理“CLI 缺失材料查询能力”，没有提前实现下一项“CLI 分摊提交能力”。
- 缺失材料命令直接复用后端已有 `/missing-materials` 只读接口，没有新增后端业务规则，也没有把 `status` 命令拆成新的后端聚合。
- `./scripts/verify.sh` 期间 pytest 仍有 3 条既有 `DeprecationWarning`，来源于第三方栈内对 `HTTP_422_UNPROCESSABLE_ENTITY` 的使用，不是本轮新增问题。
- 前端测试期间仍打印 Node `--localstorage-file` 既有警告，但 lint、测试和构建均通过，本轮未新增对此行为的依赖。

### 假设
- 本轮保守假设“CLI 缺失材料查询能力”的最小闭环是提供一个聚焦缺失项的独立命令，而不是继续扩展 `status` 的筛选参数：
  - 先满足成员按任务快速查看“还缺什么”；
  - 更复杂的筛选、按发票编号过滤或和异常项混合输出，留待后续独立任务再补。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“增加 CLI 分摊提交能力”，优先复用现有分摊接口，避免在 CLI 复制金额合计等服务端业务规则。

## 2026-04-28 11:27 - Add CLI member status query

### 完成内容
- 为任务路由新增成员隔离的聚合状态接口 `GET /api/tasks/{task_id}/member-status`：
  - 仅允许任务成员查询；
  - 聚合本人提交材料的识别状态、校验汇总状态、缺失材料和费用确认状态；
  - 不返回同任务其他成员的材料详情。
- 新增 `src/trms_backend/domain/task_member_status.py`，集中封装成员状态聚合模型与计数逻辑：
  - 输出材料级状态列表；
  - 输出缺失材料列表；
  - 输出本人费用确认明细和确认状态计数。
- 扩展 `src/trms_cli/cli.py`，新增 `status` 命令：
  - 读取已登录 session 中的 `member_id`；
  - 请求新的成员状态聚合接口；
  - 同时支持文本输出和 `--json` 结构化输出。
- 新增测试：
  - `tests/test_task_member_status_api.py` 覆盖成员仅能看到本人相关状态，以及非成员禁止访问；
  - `tests/test_cli_status.py` 覆盖 CLI 文本输出、JSON 输出和未登录错误。
- 将 `TASKS.md` 中“增加 CLI 状态查询能力”标记为已完成。

### 修改文件
- `src/trms_backend/api/tasks.py`
- `src/trms_backend/domain/task_member_status.py`
- `src/trms_cli/cli.py`
- `tests/test_task_member_status_api.py`
- `tests/test_cli_status.py`
- `TASKS.md`
- `WORKLOG.md`

### 根因
- 当前 CLI 已经具备登录、任务查询和材料上传能力，但成员仍无法通过 CLI 查看自己材料的后续处理状态。
- 现有后端能力虽然分别提供了缺失材料和费用明细等接口，但缺少一个面向 CLI 的最小聚合视图：
  - CLI 若直接拼接现有原始任务材料列表，会把同任务其他成员的材料详情暴露到客户端；
  - CLI 若只调用单个已有接口，又无法一次拿到识别、校验、缺失材料和确认状态四类结果。

### 验证结果
- 已通过：
  - `uv run pytest tests/test_task_member_status_api.py`
    - 2 个成员状态聚合接口测试通过
  - `uv run pytest tests/test_cli_status.py`
    - 3 个 CLI 状态查询测试通过
  - `uv run pytest tests/test_cli_tasks.py tests/test_cli_submit.py tests/test_cli_status.py tests/test_task_member_status_api.py tests/test_missing_materials_api.py tests/test_expense_details_api.py`
    - 24 个相关 CLI/任务状态测试通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - pytest 191 个用例通过
    - `cd web && npm run lint` 通过
    - `cd web && npm test` 通过，18 个前端测试文件、50 个测试通过
    - `cd web && npm run build` 通过
    - `git diff --check` 通过

### 说明
- 本轮只处理“CLI 状态查询能力”，没有提前实现下一项“CLI 缺失材料查询能力”：
  - 当前 `status` 命令已经包含缺失材料结果，但仍以综合状态查询的形式提供；
  - 面向缺失材料的独立命令、独立输出契约和更精简交互仍留给下一轮任务。
- `./scripts/verify.sh` 期间 pytest 仍有 3 条既有 `DeprecationWarning`，来源于第三方栈内对 `HTTP_422_UNPROCESSABLE_ENTITY` 的使用，不是本轮新增问题。
- 前端测试期间仍打印 Node `--localstorage-file` 既有警告，但 lint、测试和构建均通过，本轮未新增对此行为的依赖。

### 假设
- 本轮保守假设“CLI 状态查询能力”的最小闭环是按任务聚合本人状态，不提前实现需求文档里提到的可选“按材料编号过滤”：
  - 先保证成员能安全拿到本人材料、缺失项和确认状态；
  - 更细粒度的材料筛选留待后续独立任务再补。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“增加 CLI 缺失材料查询能力”，基于本轮已落地的成员状态聚合边界，抽出更聚焦的缺失材料命令和 JSON 契约。

## 2026-04-28 11:12 - Add CLI local upload precheck

### 完成内容
- 扩展 `src/trms_cli/cli.py` 的 `submit` 命令，在发起 multipart 请求前增加本地预检查：
  - 继续保留既有的路径存在、必须为文件、可读检查；
  - 新增零字节文件、文件大小上限和基础内容类型检查；
  - 大小和基础类型直接复用后端上传规则使用的常量，避免 CLI 和服务端口径漂移。
- 为批量提交流程补齐本地失败合并逻辑：
  - 本地通过预检查的文件继续上传；
  - 本地已知必失败的文件不发起上传，但保留为逐文件失败结果；
  - 当全部文件都在本地预检查失败时，不触发任何网络请求，直接返回失败结果。
- 扩充 `tests/test_cli_submit.py`，新增覆盖：
  - 本地不支持的基础类型不会触发上传，JSON 输出包含具体文件路径；
  - 本地超大文件不会触发上传，文本输出包含具体文件路径；
  - 批量上传时，本地失败文件不会进入请求，但会和成功上传结果一起组成 `partial_success`。
- 将 `TASKS.md` 中“增加 CLI 本地预检查”标记为已完成。

### 修改文件
- `src/trms_cli/cli.py`
- `tests/test_cli_submit.py`
- `TASKS.md`
- `WORKLOG.md`

### 根因
- 当前 CLI 虽然已经支持批量上传和逐文件结果，但仍会把本地已知必失败的文件直接发给后端，由服务端再返回不支持类型或超限错误。
- 这带来两个问题：
  - 明显可在本地提前发现的失败仍然消耗一次上传请求；
  - 服务端错误只能给出原始文件名，不能像 CLI 本地路径错误一样直接指出用户传入的具体路径。

### 验证结果
- 已通过：
  - `uv run pytest tests/test_cli_submit.py`
    - 8 个 CLI 提交相关测试通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - pytest 186 个用例通过
    - `cd web && npm run lint` 通过
    - `cd web && npm test` 通过，18 个前端测试文件、50 个测试通过
    - `cd web && npm run build` 通过
    - `git diff --check` 通过

### 说明
- 本轮只处理“CLI 本地预检查”，没有提前实现下一项“CLI 状态查询能力”。
- `./scripts/verify.sh` 期间 pytest 仍有 3 条既有 `DeprecationWarning`，来源于第三方栈内对 `HTTP_422_UNPROCESSABLE_ENTITY` 的使用，不是本轮新增问题。
- 前端测试期间仍打印 Node `--localstorage-file` 既有警告，但 lint、测试和构建均通过，本轮未新增对此行为的依赖。

### 假设
- 本轮保守假设“预检查失败不发起上传”在批量场景下按文件生效：
  - 零字节、超限和基础类型不支持的文件作为本地逐文件失败保留；
  - 已通过预检查的其他文件仍可继续上传，避免一个坏文件把整批有效文件都拦住。
- 同时保守假设缺失路径、目录路径和不可读文件属于命令输入错误：
  - 这类错误继续沿用既有 `CliError` 路径直接终止命令；
  - 本轮不把它们改造成新的批量失败输出契约，避免无关扩大 CLI 错误语义变更。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“增加 CLI 状态查询能力”，优先明确成员可见的材料识别、校验和确认状态聚合输出。

## 2026-04-28 11:04 - Add CLI batch submit per-file results

### 完成内容
- 扩展 `src/trms_cli/cli.py` 的 `submit` 命令，从单文件上传改为支持一次提交一个或多个本地文件：
  - 保留既有 session 读取、成员绑定和单次 multipart 请求方式；
  - 多文件仍通过同一个后端批量上传接口提交，不额外引入新的业务入口。
- 为 CLI 对齐后端批量上传返回契约，新增逐文件结果解析：
  - 解析 `success`、`partial_success`、`failed` 三种批量状态；
  - 成功项返回材料编号、任务编号、文件名和识别占位状态；
  - 失败项返回原始文件名、错误码和失败原因。
- 明确批量提交退出码和输出语义：
  - 全部成功返回退出码 `0`；
  - 部分成功返回退出码 `2`，同时输出成功项和失败项；
  - 全部失败返回退出码 `1`，JSON 模式仍输出结构化逐文件失败结果。
- 保留单文件成功场景的既有兼容输出：
  - 文本模式继续输出单行 `Uploaded material ...`；
  - JSON 模式继续保留原来的单项 `item` 结构，避免本轮把旧调用方一起打破。
- 扩充 `tests/test_cli_submit.py`，新增覆盖：
  - 多文件批量提交的部分成功文本输出与退出码；
  - 多文件全部失败时的结构化 JSON 返回。
- 将 `TASKS.md` 中“增加 CLI 批量上传逐文件结果”标记为已完成。

### 修改文件
- `src/trms_cli/cli.py`
- `tests/test_cli_submit.py`
- `TASKS.md`
- `WORKLOG.md`

### 根因
- 上一轮 CLI `submit` 命令虽然已经能把单个文件上传到后端，但需求文档中的 CLI 提交流程明确要求“上传一个或多个文件”。
- 后端批量上传接口早已支持逐文件成功/失败和 `partial_success` 语义，而 CLI 仍把响应强行收缩为“只允许一项成功结果”，导致：
  - 成员无法在一次命令中上传多个材料；
  - 接口返回部分成功时，CLI 无法准确暴露逐文件结果；
  - 批量失败的结构化失败项会被退化成笼统 HTTP 错误，和需求里的“逐文件结果”不一致。

### 验证结果
- 已通过：
  - `uv run pytest tests/test_cli_submit.py`
    - 6 个 CLI 提交相关测试通过
  - `uv run pytest tests/test_cli_health.py tests/test_cli_login.py tests/test_cli_tasks.py tests/test_cli_submit.py`
    - 17 个 CLI 相关测试通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - pytest 184 个用例通过
    - `cd web && npm run lint` 通过
    - `cd web && npm test` 通过，18 个前端测试文件、50 个测试通过
    - `cd web && npm run build` 通过
    - `git diff --check` 通过

### 说明
- 本轮只处理“批量上传逐文件结果”，没有提前实现下一项“CLI 本地预检查”：
  - CLI 仍只保留现有的本地路径存在、是否为文件、是否可读检查；
  - 文件大小和基础类型的本地预检查仍留给下一轮独立任务。
- 批量全部失败时，CLI 仍把后端的结构化失败列表输出到标准输出，并通过退出码 `1` 表示命令未成功完成；这和此前“普通错误输出到标准错误”的路径不同，是为了满足“逐文件失败结果可见”的任务要求。
- `./scripts/verify.sh` 期间 pytest 仍有 3 条既有 `DeprecationWarning`，来源于第三方栈内对 `HTTP_422_UNPROCESSABLE_ENTITY` 的使用，不是本轮新增问题。
- 前端测试期间仍打印 Node `--localstorage-file` 既有警告，但 lint、测试和构建均通过，本轮未新增对此行为的依赖。

### 假设
- 本轮保守假设“批量上传逐文件结果”的最小闭环是：
  - 多个本地文件一次性提交到既有后端批量接口；
  - CLI 负责忠实暴露接口逐文件成功/失败结果；
  - 不在本轮提前增加目录递归、自动拆批、大小阈值预判或内容类型本地拦截。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“增加 CLI 本地预检查”，优先把大小和基础类型检查补到 CLI 本地侧，并保持错误信息逐文件可定位。

## 2026-04-28 10:58 - Add CLI material submission placeholder

### 完成内容
- 为 `src/trms_cli/cli.py` 新增 `submit` 命令，建立 CLI 材料提交最小闭环：
  - 从本地 session 读取 `base_url`、`member_id` 和 access token；
  - 接收 `--task-id`、`--material-type` 和单个本地文件路径；
  - 以 `channel=cli` 调用后端 `POST /api/tasks/{task_id}/materials` multipart 上传接口。
- 在 CLI 侧补充最小本地文件装载边界：
  - 缺失路径、目录路径、不可读文件时显式失败；
  - 根据文件名推断 `Content-Type`，其余校验继续交给服务端，不提前复制服务端业务规则。
- 固定上传结果输出：
  - 文本模式输出材料编号、目标任务和识别占位状态 `pending`；
  - JSON 模式继续复用 `trms-cli.v1` envelope，返回 `task_id`、`member_id` 和单个上传结果。
- 新增 `tests/test_cli_submit.py`，覆盖：
  - 从已登录 session 发起上传并携带 `Authorization`、`submitter_id`、`channel=cli`；
  - JSON 输出结构；
  - 本地文件不存在时显式失败；
  - 服务端返回错误时不泄露 token。
- 将 `TASKS.md` 中“增加 CLI 材料提交占位流程”标记为已完成。

### 修改文件
- `src/trms_cli/cli.py`
- `tests/test_cli_submit.py`
- `TASKS.md`
- `WORKLOG.md`

### 根因
- 当前 CLI 已具备登录和任务查询能力，但成员在查询到可见任务后，仍无法从本地把实际发票或附件提交到后端，CLI 主流程卡在“看到任务但不能上传”这一步。
- 后端材料上传接口和识别占位链路已经存在，如果 CLI 不尽快补上最小 multipart 提交边界，后续“批量逐文件结果”“本地预检查”“状态查询”都缺少实际上传入口作为前提。

### 验证结果
- 已通过：
  - `uv run pytest tests/test_cli_submit.py tests/test_cli_tasks.py tests/test_cli_login.py`
    - 11 个 CLI 相关测试通过
  - `uv run pytest tests/test_materials_api.py tests/test_recognition_tasks_api.py`
    - 29 个上传与识别相关测试通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - pytest 182 个用例通过
    - `cd web && npm run lint` 通过
    - `cd web && npm test` 通过，18 个前端测试文件、50 个测试通过
    - `cd web && npm run build` 通过
    - `git diff --check` 通过

### 说明
- 本轮只实现单文件上传占位流程，没有提前实现下一项“CLI 批量上传逐文件结果”：
  - 当前命令固定接收一个本地文件路径；
  - 部分成功、逐文件退出码和多文件结果语义留给下一轮独立处理。
- 上传成功后的 `recognition_status` 当前按后端既有契约保守固定为 `pending`：
  - 后端材料上传后立即创建识别任务占位；
  - 本轮不额外新增 CLI 轮询识别状态接口。
- `./scripts/verify.sh` 期间 pytest 仍有 3 条既有 `DeprecationWarning`，来源于第三方栈内对 `HTTP_422_UNPROCESSABLE_ENTITY` 的使用，不是本轮新增问题。
- 前端测试期间仍打印 Node `--localstorage-file` 既有警告，但 lint、测试和构建均通过，本轮未新增对此行为的依赖。

### 假设
- 本轮保守假设“增加 CLI 材料提交占位流程”的最小闭环是：
  - CLI 基于已登录 session 和已选任务发起单文件上传；
  - 服务端继续负责材料类型、成员资格、截止时间和上传内容校验；
  - CLI 只承担必要的本地文件读取与明确错误暴露，不提前复制完整预检查规则。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“增加 CLI 批量上传逐文件结果”，在保留本轮单文件命令边界的前提下扩展多文件输入、部分成功输出和退出码语义。

## 2026-04-28 10:52 - Add CLI visible-task membership filter

### 完成内容
- 为 CLI 会话增加显式成员绑定：
  - `src/trms_cli/cli.py` 的 `login` 命令新增必填 `--member-id`；
  - `src/trms_cli/token_store.py` 在本地 session 中保存 `member_id`，`tasks` 命令读取后自动附加到任务列表请求。
- 为后端任务列表增加最小成员过滤：
  - `GET /api/tasks` 新增可选 `member_id` 查询参数；
  - `src/trms_backend/infrastructure/repositories.py` 增加 `list_for_member`，仅返回成员编号出现在任务 `member_ids` 中的任务。
- 增补回归测试，覆盖：
  - CLI 登录会话保存成员编号且不泄露 token；
  - CLI 任务列表请求会自动携带 `member_id`；
  - 有可见任务和无可见任务两条路径；
  - API 按 `member_id` 过滤任务列表。
- 将 `TASKS.md` 中“增加 CLI 可见任务权限过滤”标记为已完成。

### 修改文件
- `src/trms_cli/cli.py`
- `src/trms_cli/token_store.py`
- `src/trms_backend/api/tasks.py`
- `src/trms_backend/domain/tasks.py`
- `src/trms_backend/infrastructure/repositories.py`
- `tests/test_cli_login.py`
- `tests/test_cli_tasks.py`
- `tests/test_tasks_api.py`
- `TASKS.md`
- `WORKLOG.md`

### 根因
- 上一轮 CLI `tasks` 命令虽然已经能列出开放且未过期的任务，但底层仍直接读取未过滤的 `/api/tasks` 全量列表。
- 这会把与当前成员无关的比赛任务暴露给 CLI，和需求文档中“成员先查询自己当前可提交任务”的链路不一致，也会让后续 CLI 上传命令缺少稳定的任务可见性边界。

### 验证结果
- 已通过：
  - `uv run pytest tests/test_cli_login.py tests/test_cli_tasks.py tests/test_tasks_api.py`
    - 47 个相关测试通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - pytest 178 个用例通过
    - `cd web && npm run lint` 通过
    - `cd web && npm test` 通过，18 个前端测试文件、50 个测试通过
    - `cd web && npm run build` 通过
    - `git diff --check` 通过

### 说明
- 本轮只实现 CLI 任务列表的最小成员过滤，没有提前实现 P3 中“统一请求身份上下文”和“基础权限控制”。
- 当前后端仍然把 `member_id` 视为 CLI 显式传入的占位身份信息；真正把访问控制与 token/角色统一绑定，仍属于后续 P3 任务范围。
- `./scripts/verify.sh` 期间 pytest 仍有 3 条既有 `DeprecationWarning`，来源于第三方栈内对 `HTTP_422_UNPROCESSABLE_ENTITY` 的使用，不是本轮新增问题。
- 前端测试期间仍打印 Node `--localstorage-file` 既有警告，但 lint、测试和构建均通过，本轮未新增对此行为的依赖。

### 假设
- 本轮保守假设“CLI 可见任务权限过滤”的最小闭环是：
  - CLI 登录时先显式绑定成员编号；
  - CLI 任务列表请求只按该成员编号过滤任务；
  - 不在本轮提前引入真实 token 解析、统一角色模型或全局身份上下文。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“增加 CLI 材料提交占位流程”，优先复用本轮的 `member_id` 会话绑定，把材料上传请求也收敛到同一 CLI 身份边界中。

## 2026-04-28 10:45 - Add CLI task listing command

### 完成内容
- 为 `src/trms_cli/cli.py` 新增 `tasks` 命令，建立 CLI 查询当前可提交任务的最小闭环：
  - 复用本地 token 会话文件读取 `base_url` 和 access token；
  - 调用后端任务列表接口并带上 `Authorization: Bearer ...` 请求头；
  - 仅输出状态为 `open` 且截止时间晚于当前时间的任务，避免把草稿、已关闭或已过期任务伪装成“当前可提交”。
- 为文本和 JSON 两种输出模式固定任务列表字段：
  - 输出包含任务编号、比赛名称、状态和截止时间；
  - JSON 输出继续复用 `trms-cli.v1` envelope，并返回 `count` 与 `items`。
- 在 `src/trms_cli/token_store.py` 增加会话读取能力：
  - 校验 token 文件存在、JSON 格式、schema version 和必要字段；
  - 会话缺失或损坏时显式失败，而不是静默退化为匿名请求。
- 新增 `tests/test_cli_tasks.py`，覆盖：
  - 从本地会话读取 token 并成功查询任务列表；
  - JSON 输出结构；
  - 未登录时显式失败。
- 将 `TASKS.md` 中“增加 CLI 任务查询能力”标记为已完成。

### 修改文件
- `src/trms_cli/cli.py`
- `src/trms_cli/token_store.py`
- `tests/test_cli_tasks.py`
- `TASKS.md`
- `WORKLOG.md`

### 根因
- 当前 CLI 虽然已有 `health` 和 `login` 占位，但成员完成登录后仍无法查询有哪些任务可供后续提交材料，CLI 主流程停在“拿到 token”这一步。
- 需求文档中的 CLI 提交流程明确要求“登录后先查询当前可提交任务，再选择目标任务上传”；如果不先建立这一最小查询能力，后续材料上传命令就只能要求用户手填任务编号，CLI 侧会缺少最基本的任务发现链路。

### 验证结果
- 已通过：
  - `uv run pytest tests/test_cli_health.py tests/test_cli_login.py tests/test_cli_tasks.py`
    - 10 个 CLI 相关测试通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - pytest 175 个用例通过
    - `cd web && npm run lint` 通过
    - `cd web && npm test` 通过，18 个前端测试文件、50 个测试通过
    - `cd web && npm run build` 通过
    - `git diff --check` 通过

### 说明
- 本轮只实现“任务查询能力”，没有提前实现下一项“CLI 可见任务权限过滤”：
  - 当前 CLI 通过 access token 建立认证请求边界；
  - “只返回当前成员可参与任务”的服务端权限过滤仍留给下一轮按 `TASKS.md` 顺序处理。
- 为兼容此前 `login` 可保存 `http://host/api` 这类 base URL 的情况，`tasks` 命令在请求任务列表时会识别已带 `/api` 前缀的 base URL，避免拼出重复的 `/api/api/tasks`。
- 任务是否“当前可提交”当前按两个条件保守判断：
  - 任务状态必须为 `open`；
  - 任务截止时间必须晚于当前时间。
- `./scripts/verify.sh` 期间 pytest 仍有 3 条既有 `DeprecationWarning`，来源于第三方栈内对 `HTTP_422_UNPROCESSABLE_ENTITY` 的使用，不是本轮新增问题。
- 前端测试期间仍打印 Node `--localstorage-file` 既有警告，但 lint、测试和构建均通过，本轮未新增对此行为的依赖。

### 假设
- 本轮保守假设“增加 CLI 任务查询能力”的最小闭环是：
  - CLI 先基于现有后端 `GET /api/tasks` 建立列表查询命令；
  - 成员可见性过滤作为紧随其后的独立任务处理，而不是在本轮提前引入未成型的权限系统。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“增加 CLI 可见任务权限过滤”，优先把“当前成员只看到自己可参与任务”的约束下沉到 API 或明确的身份上下文边界中，再补对应 CLI 回归测试。

## 2026-04-28 10:38 - Establish CLI login and token storage placeholder

### 完成内容
- 为 `src/trms_cli/cli.py` 新增 `login` 命令，占位支持 CLI 登录边界：
  - 命令读取 `TRMS_CLI_ACCESS_TOKEN` 和 `TRMS_CLI_REFRESH_TOKEN`；
  - 若环境变量未提供，则仅在交互式终端下通过 `getpass` 安全提示输入；
  - 非交互模式且未提供 token 时显式失败，不伪装为登录成功。
- 新增 `src/trms_cli/token_store.py`，建立本地 token 存储策略：
  - 默认落盘到 `XDG_CONFIG_HOME/trms/session.json`，若未设置则使用 `~/.config/trms/session.json`；
  - 支持通过 `TRMS_CLI_CONFIG_DIR` 覆盖配置目录，便于测试和后续运行环境定制；
  - 在 Unix 平台上强制把目录权限收敛到 `0700`、文件权限收敛到 `0600`，并在权限不满足时显式报错。
- 新增 `tests/test_cli_login.py`，覆盖：
  - 文本模式登录成功；
  - JSON 模式登录成功；
  - 非交互模式缺少 token 时失败；
  - 成功和失败输出均不泄露 access token 或 refresh token。
- 将 `TASKS.md` 中“建立 CLI 登录和 Token 存储占位”标记为已完成。

### 修改文件
- `src/trms_cli/cli.py`
- `src/trms_cli/token_store.py`
- `tests/test_cli_login.py`
- `TASKS.md`
- `WORKLOG.md`

### 根因
- 当前 CLI 只有 `health` 命令，没有任何“成员如何以 CLI 身份访问后端”的本地边界，后续任务查询、材料上传和状态查询都缺少可复用的认证载体。
- 同时，需求和架构文档都要求 CLI 采用 Token 登录，并明确禁止把 token 打到日志；如果不先固定最小登录命令和本地落盘约束，后续 CLI 功能容易各自临时拼接 token 读取方式，导致安全边界和兼容行为失控。

### 验证结果
- 已通过：
  - `uv run pytest tests/test_cli_health.py tests/test_cli_login.py`
    - 7 个 CLI 相关测试通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - pytest 172 个用例通过
    - `cd web && npm run lint` 通过
    - `cd web && npm test` 通过，18 个前端测试文件、50 个测试通过
    - `cd web && npm run build` 通过
    - `git diff --check` 通过

### 说明
- 当前实现是“登录占位”而不是真实 OAuth / Token 交换流程：CLI 只负责安全读取和保存预先签发的 access token / refresh token，尚未对接后端登录接口。
- 按架构文档长期目标，优先方案应是系统密钥链；本轮由于仓库当前无跨平台密钥链依赖，也无真实登录后端，因此先采用“权限受限本地文件”这一明确记录的降级方案，为后续任务提供可复用存储边界。
- `./scripts/verify.sh` 期间 pytest 仍有 3 条既有 `DeprecationWarning`，来源于第三方栈内对 `HTTP_422_UNPROCESSABLE_ENTITY` 的使用，不是本轮新增问题。
- 前端测试期间仍打印 Node `--localstorage-file` 既有警告，但 lint、测试和构建均通过，本轮未新增对此行为的依赖。

### 假设
- 在后端真实 CLI 登录 API 尚未落地前，本轮将“建立 CLI 登录和 Token 存储占位”保守解释为：CLI 建立安全输入、稳定落盘和可测试错误语义，不提前实现服务端 token 签发、刷新或身份绑定交换。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“增加 CLI 任务查询能力”，优先复用本轮 token 存储边界，为任务列表请求补 `Authorization` 头和最小输出格式。

## 2026-04-28 10:32 - Define CLI JSON output schema

### 完成内容
- 为 `src/trms_cli/cli.py` 的 `health` 命令增加 `--json` 输出模式，并固定第一版 JSON schema：
  - `schema_version` 使用稳定值 `trms-cli.v1`；
  - 成功输出包含 `ok`、`command` 和 `data`；
  - 失败输出包含 `ok`、`command` 和结构化 `error.code` / `error.message`。
- 保持原有非 JSON 模式不变：
  - 成功仍输出 `TRMS API health: ok`；
  - 失败仍输出 `Error: ...` 到标准错误。
- 为现有 CLI 错误补充稳定错误码，占位区分 `http_error`、`network_error`、`invalid_json_response`、`health_unexpected_status`、`health_not_ready`。
- 扩展 `tests/test_cli_health.py`，新增 `--json` 成功和失败路径测试。
- 将 `TASKS.md` 中“定义 CLI JSON 输出规范”标记为已完成。

### 修改文件
- `src/trms_cli/cli.py`
- `tests/test_cli_health.py`
- `TASKS.md`
- `WORKLOG.md`

### 根因
- 当前 CLI 只有纯文本成功输出和纯文本错误输出，虽然足够人工查看，但不满足需求文档和架构文档中“CLI 需支持 `--json` 机器可读输出”的约束。
- 如果不先固定第一版 JSON envelope 和 schema version，后续任务查询、上传、状态查询等 CLI 能力即使补上，也会缺少稳定的脚本消费契约，后续改动容易破坏自动化调用方。

### 验证结果
- 已通过：
  - `uv run pytest tests/test_cli_health.py`
    - 4 个 CLI 测试通过，覆盖文本成功、文本失败、JSON 成功、JSON 失败
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - pytest 169 个用例通过
    - `cd web && npm run lint` 通过
    - `cd web && npm test` 通过，18 个前端测试文件、50 个测试通过
    - `cd web && npm run build` 通过
    - `git diff --check` 通过

### 说明
- 本轮只为已存在的 `health` 命令定义并验证 JSON 输出契约，没有提前扩展登录、任务列表、材料上传或状态查询命令。
- `--json` 成功结果写入标准输出，`--json` 错误结果写入标准错误；两种情况下都只输出合法 JSON，不混入普通文本。
- `./scripts/verify.sh` 期间 pytest 仍有 3 条既有 `DeprecationWarning`，来源于第三方栈内对 `HTTP_422_UNPROCESSABLE_ENTITY` 的使用，不是本轮新增问题。
- 前端测试期间仍打印 Node `--localstorage-file` 既有警告，但 lint、测试和构建均通过，本轮未新增对此行为的依赖。

### 假设
- 本轮将“定义 CLI JSON 输出规范”保守限定为给现有 `health` 命令建立可复用的第一版 envelope，而不是提前为所有未来命令设计完整字段集合；后续命令在保持 `schema_version`、`ok`、`command` 和结构化错误字段稳定的前提下扩展各自 `data` 载荷。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“建立 CLI 登录和 Token 存储占位”，优先固定登录命令边界、Token 落盘权限要求，以及避免在日志和错误输出中泄露凭据。

## 2026-04-28 10:26 - Establish CLI project skeleton

### 完成内容
- 新增最小 CLI 包 `src/trms_cli/`，建立独立模块边界和 `python -m trms_cli` 入口。
- 新增独立启动脚本 `scripts/trms-cli`，统一设置 `PYTHONPATH=src` 并优先通过 `uv run` 调起 CLI，避免当前仓库未安装为可导入包时命令直接失效。
- 实现最小占位命令 `health`：
  - 调用后端 `GET /health`；
  - 仅在返回 `{"status": "ok"}` 时输出 `TRMS API health: ok`；
  - 网络失败、非 JSON 响应或非预期健康状态时显式失败，不伪装为成功。
- 新增 `tests/test_cli_health.py`，覆盖健康检查成功与失败路径。
- 将 `TASKS.md` 中“建立 CLI 项目骨架”标记为已完成。

### 修改文件
- `src/trms_cli/__init__.py`
- `src/trms_cli/__main__.py`
- `src/trms_cli/cli.py`
- `scripts/trms-cli`
- `tests/test_cli_health.py`
- `TASKS.md`
- `WORKLOG.md`

### 根因
- 仓库此前只有后端 API 和 Web 前端，没有任何 CLI 工程目录、命令入口或可执行骨架。
- 这使需求文档和任务队列里关于 CLI 渠道的后续工作都缺少承载位置；即使只是先做最小占位命令，也需要先固定模块边界、调用方式和最基本的失败语义。

### 验证结果
- 已通过：
  - `uv run pytest tests/test_cli_health.py`
    - 2 个 CLI 测试通过
  - `./scripts/trms-cli --help`
    - 独立 CLI 入口可正常显示帮助信息
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - pytest 167 个用例通过
    - `cd web && npm run lint` 通过
    - `cd web && npm test` 通过，18 个前端测试文件、50 个测试通过
    - `cd web && npm run build` 通过
    - `git diff --check` 通过

### 说明
- `scripts/trms-cli` 当前本地运行方式为：
  - `./scripts/trms-cli health --base-url http://127.0.0.1:8000`
- 之所以提供脚本包装层，而不是直接要求 `uv run python -m trms_cli`，是因为当前仓库默认不会把 `src/` 自动加入导入路径；若不显式补 `PYTHONPATH`，CLI 模块无法被直接导入。
- `./scripts/verify.sh` 期间 pytest 仍有 3 条既有 `DeprecationWarning`，来源于第三方栈内对 `HTTP_422_UNPROCESSABLE_ENTITY` 的使用，不是本轮新增问题。
- 前端测试期间仍打印 Node `--localstorage-file` 既有警告，但 lint、测试和构建均通过，本轮未新增对此行为的依赖。

### 假设
- 本轮将“CLI 项目骨架”保守限定为最小可运行入口和健康检查占位，不提前实现 `--json`、登录、任务列表或上传能力，以保持与后续 CLI 任务拆分一致。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“定义 CLI JSON 输出规范”，先固定成功/失败输出结构和 `schema version`，再决定是否把 `health` 命令扩展为 JSON 模式。

## 2026-04-28 10:21 - Establish frontend main-flow E2E placeholder

### 完成内容
- 新增 `web/src/app/main-flow-e2e-placeholder.test.tsx`，用单个状态化 mock API 测试串起第一阶段前端主流程占位：
  - 管理员创建任务并进入任务列表；
  - 管理员将草稿任务切换为开放提交；
  - 成员上传发票材料；
  - 管理员录入发票字段；
  - 管理员保存费用分摊；
  - 成员确认个人费用；
  - 管理员查看复核总览并进入导出管理页。
- 本测试明确把 E2E 边界固定为 `Vitest + Testing Library + createMemoryRouter + mock API`：
  - 不接真实浏览器自动化；
  - 不接真实后端、AI、Telegram、邮件或对象存储；
  - 重点验证前端主流程路由、页面协作和关键交互是否仍能串联。
- 将 `TASKS.md` 中“建立前端主流程 E2E 占位”标记为已完成。

### 修改文件
- `web/src/app/main-flow-e2e-placeholder.test.tsx`
- `TASKS.md`
- `WORKLOG.md`

### 根因
- 当前前端虽然已经具备任务创建、材料上传、发票录入、分摊、确认、复核和导出等分页面测试，但这些测试大多按单页拆开，缺少一条从“任务创建后如何一路走到导出入口”的跨页面主流程占位。
- 结果是单页回归虽然在，但页面之间的路由衔接、角色切换和前后步骤依赖没有被统一锁定；后续任何页面改动都可能让主链路断在中间，却不一定会被现有页面级测试及时发现。

### 验证结果
- 已通过：
  - `cd web && npm test -- main-flow-e2e-placeholder`
    - 1 个前端测试文件、1 个测试通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - pytest 165 个用例通过
    - `cd web && npm run lint` 通过
    - `cd web && npm test` 通过，18 个前端测试文件、50 个测试通过
    - `cd web && npm run build` 通过
    - `git diff --check` 通过

### 说明
- 本任务是“E2E 占位”而不是真浏览器端到端自动化：测试重点是固定第一阶段主流程的前端协作边界，而不是引入新的浏览器测试栈。
- pytest 仍有 3 条既有 `DeprecationWarning`，来源于第三方栈内对 `HTTP_422_UNPROCESSABLE_ENTITY` 的使用，不是本轮新增问题。
- 前端测试期间仍打印 Node `--localstorage-file` 既有警告，但 lint、测试和构建均通过，本轮未新增对此行为的依赖。

### 假设
- 本轮保守采用仓库现有的 Vitest/Memory Router 测试基础设施完成主流程占位，而不是额外引入 Playwright；后续若需要真实浏览器级回归，可在这一占位链路基础上迁移或并行补充。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“建立 CLI 项目骨架”，优先固定 CLI 入口、最小命令集和本地运行方式，再补 JSON 输出与登录占位。

## 2026-04-28 10:12 - Establish frontend form and upload component tests

### 完成内容
- 补齐现有前端表单/上传测试中的服务端拒绝分支：
  - 在 `web/src/app/member-material-upload.test.tsx` 新增材料上传被后端拒绝时的回归用例，确认页面显示 `ApiErrorNotice`，不把失败伪装成上传成功；
  - 在 `web/src/app/member-expense-confirmation.test.tsx` 新增成员确认提交被后端拒绝时的回归用例，确认页面显式展示服务端错误，而不是静默吞掉失败。
- 结合仓库内既有测试，完成本任务定义的四类页面覆盖闭环：
  - 任务创建表单：`web/src/app/admin-task-create.test.tsx`
  - 材料上传：`web/src/app/member-material-upload.test.tsx`
  - 分摊编辑：`web/src/app/admin-split-editor.test.tsx`
  - 成员确认：`web/src/app/member-expense-confirmation.test.tsx`
- 将 `TASKS.md` 中“建立前端表单和上传组件测试”标记为已完成。

### 修改文件
- `web/src/app/member-material-upload.test.tsx`
- `web/src/app/member-expense-confirmation.test.tsx`
- `TASKS.md`
- `WORKLOG.md`

### 根因
- 该任务对应的四类前端页面测试主路径其实已经大体存在，但覆盖不均衡：任务创建和分摊编辑已经锁定了服务端错误展示，材料上传和成员确认仍缺少“后端明确拒绝时必须显式报错”的回归用例。
- 结果是 `TASKS.md` 的 Done when 虽然接近满足，但“覆盖服务端错误展示”这一条件并没有在四类关键交互上形成完整约束，后续页面改动时仍可能把失败状态退化成静默无响应或误导性成功反馈。

### 验证结果
- 已通过：
  - `cd web && npm test -- member-material-upload member-expense-confirmation`
    - 2 个前端测试文件、7 个测试通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - pytest 165 个用例通过
    - `cd web && npm run lint` 通过
    - `cd web && npm test` 通过，17 个前端测试文件、49 个测试通过
    - `cd web && npm run build` 通过
    - `git diff --check` 通过

### 说明
- pytest 仍有 3 条既有 `DeprecationWarning`，来源于第三方栈内对 `HTTP_422_UNPROCESSABLE_ENTITY` 的使用，不是本轮新增问题。
- 前端测试期间仍打印 Node `--localstorage-file` 既有警告，但 lint、测试和构建均通过，本轮未新增对此行为的依赖。

### 假设
- 本轮将“建立前端表单和上传组件测试”保守解释为：在不新增业务实现的前提下，补齐任务定义要求的关键测试边界，尤其是服务端错误展示；不额外扩展到新的组件抽象或 E2E 场景。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“建立前端主流程 E2E 占位”，优先确定使用 Vitest + Memory Router mock API 继续占位，还是引入 Playwright 仅搭建最小骨架。

## 2026-04-28 10:06 - Establish frontend permission visibility tests

### 完成内容
- 新增 `web/src/app/permission-visibility.test.tsx`，集中补齐前端权限可见性测试：
  - 覆盖成员任务页只渲染成员操作，不出现“创建新任务”“录入或更正发票”“进入复核总览”“进入导出管理”“编辑费用分摊”等管理员操作入口；
  - 覆盖成员身份直接访问管理员路由时，由 `ProtectedRoleRoute` 在发起任何管理员数据请求前拦截，并显示明确的角色错配提示；
  - 覆盖成员页加载中状态，以及管理员页错误状态；
  - 覆盖管理员页不渲染系统管理员入口文案，也不出现 `access token`、`refresh token`、`cookie`、`VITE_API_BASE_URL` 等无关长期凭证或敏感配置文本。
- 将 `TASKS.md` 中“建立前端权限可见性测试”标记为已完成。

### 修改文件
- `web/src/app/permission-visibility.test.tsx`
- `TASKS.md`
- `WORKLOG.md`

### 根因
- 当前前端已经具备成员/管理员路由门禁和多页业务入口，但已有测试主要按页面功能拆分，缺少一组从“权限可见性”视角出发的回归用例。
- 结果是“成员页面不应出现管理员操作”“错误或未授权状态下不应先发起越权请求”“管理员页面不应混入系统级敏感配置提示”这些边界虽然在实现里已有约束，却没有被独立锁定，后续页面迭代时容易回归。

### 验证结果
- 已通过：
  - `cd web && npm test -- permission-visibility`
    - 1 个前端测试文件、5 个测试通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - pytest 165 个用例通过
    - `cd web && npm run lint` 通过
    - `cd web && npm test` 通过，17 个前端测试文件、47 个测试通过
    - `cd web && npm run build` 通过
    - `git diff --check` 通过

### 说明
- `./scripts/verify.sh` 期间 pytest 仍有 3 条既有 `DeprecationWarning`，来源于第三方栈内对 `HTTP_422_UNPROCESSABLE_ENTITY` 的使用，不是本轮新增问题。
- 前端测试期间仍打印 Node `--localstorage-file` 既有警告，但 lint、测试和构建均通过，本轮未新增对此行为的依赖。

### 假设
- 本轮将“管理员页面不泄露无关长期凭证或敏感配置”保守解释为：管理员业务页不渲染系统管理员入口文案，也不暴露与当前页面职责无关的长期凭证或配置关键字；真实敏感配置展示与否，后续应由系统管理员页面和服务端鉴权单独约束。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“建立前端表单和上传组件测试”，优先补任务创建、材料上传、分摊编辑和成员确认这四类已落地页面的组件/集成测试边界。

## 2026-04-28 10:00 - Implement export management page

### 完成内容
- 新增管理员导出任务页面：
  - 新增 `web/src/app/admin-export-tasks.tsx`，在 `/admin/tasks/:taskId/exports` 聚合展示任务导出门禁、支持的导出类型、既有导出任务历史和即时输出预览入口；
  - 页面可创建 6 类导出任务：报销汇总表、成员明细表、发票明细表、缺失材料清单、财务填报草稿和 PDF 合并材料包；
  - 当任务尚未进入 `ready_to_export` 或 `completed` 时，直接展示后端返回的阻塞原因，并禁用导出创建与即时预览按钮，不在前端伪装成功。
- 补齐导出入口与前端契约：
  - 更新 `web/src/app/routes.tsx` 注册 `/admin/tasks/:taskId/exports`；
  - 更新 `web/src/app/admin-task-detail.tsx`，从任务详情页增加“进入导出管理”入口；
  - 修正 `web/src/lib/api/trms.ts` 中导出任务列表客户端类型，避免把后端数组响应误当成 `items` 包装结构。
- 补齐前端测试与样式：
  - 新增 `web/src/app/admin-export-tasks.test.tsx`，覆盖“创建导出任务并查看失败历史/即时输出”“导出前置条件未满足时直接阻止操作并展示原因”；
  - 更新 `web/src/app/admin-task-detail.test.tsx`，覆盖任务详情页到导出管理页的入口；
  - 更新 `web/src/styles.css`，补齐导出卡片、即时输出预览和导出任务历史的布局样式。
- 将 `TASKS.md` 中“实现导出任务页面”标记为已完成。

### 修改文件
- `web/src/app/admin-export-tasks.tsx`
- `web/src/app/admin-export-tasks.test.tsx`
- `web/src/app/admin-task-detail.tsx`
- `web/src/app/admin-task-detail.test.tsx`
- `web/src/app/routes.tsx`
- `web/src/lib/api/trms.ts`
- `web/src/styles.css`
- `TASKS.md`
- `WORKLOG.md`

### 根因
- 仓库后端此前已经具备导出边界、导出任务模型和多类即时导出接口，但管理员前端仍缺少“从复核完成到发起导出”的页面闭环。
- 结果是管理员只能通过接口或测试触发导出能力，无法在 Web 端看到导出门禁、失败原因、导出任务状态以及“当前只到占位/即时输出”的边界，第一阶段主流程停在复核后没有页面承接。

### 验证结果
- 已通过：
  - `cd web && npm test -- admin-export-tasks admin-task-detail`
    - 2 个前端测试文件、5 个测试通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - pytest 165 个用例通过
    - `cd web && npm run lint` 通过
    - `cd web && npm test` 通过，16 个前端测试文件、42 个测试通过
    - `cd web && npm run build` 通过
    - `git diff --check` 通过

### 说明
- 开发过程中 `./scripts/verify.sh` 首次失败于前端 lint 与 TypeScript 构建，原因分别是新测试中的 `act` 回调写法不满足 ESLint 规则，以及导出页事件处理函数里 `taskId` 的空值收窄不足。本轮已做最小修复后重新执行全量验证，最终通过。
- pytest 仍有 3 条既有 `DeprecationWarning`，来源于第三方栈内对 `HTTP_422_UNPROCESSABLE_ENTITY` 的使用，不是本轮新增问题。
- 前端测试期间仍打印 Node `--localstorage-file` 既有警告，但 lint、测试和构建均通过，本轮未新增对此行为的依赖。

### 假设
- “下载入口占位”当前通过页面内的即时 CSV/JSON 预览和 PDF 合并计划预览来承接，明确提示它们不是持久化产物下载链接；后续若接入对象存储或落盘文件，应替换为真实下载地址而不是继续复用占位文案。
- 创建导出任务时默认按最终目标格式建模：表格类和财务草稿统一记为 `xlsx`，PDF 合并材料包记为 `pdf`；即时预览则继续复用当前已实现的 CSV/JSON/计划接口，不提前扩展新的后端协议。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“建立前端权限可见性测试”，优先覆盖成员页不渲染管理员操作，以及管理员页不泄露无关敏感配置这两条当前最接近主流程的前端边界。

## 2026-04-28 09:46 - Implement admin corrections and reminders page

### 完成内容
- 新增管理员“人工更正与补材料提醒”页面：
  - 新增 `web/src/app/admin-corrections-reminders.tsx`，在 `/admin/tasks/:taskId/corrections` 聚合展示复核后需要人工处理的两类入口：
    - 识别字段待确认或尚未补录发票的材料，深链到发票录入页并自动定位 `materialId`；
    - 存在异常校验或成员异议的发票，深链到发票录入页进行金额/字段更正，并提供到分摊编辑页的 `invoiceId` 深链。
  - 页面同时接入 `GET /api/tasks/{taskId}/material-reminders` 与 `POST /api/tasks/{taskId}/material-reminders`，支持管理员记录补材料提醒并查看已记录历史。
- 打通复核页入口与上下文跳转：
  - 更新 `web/src/app/routes.tsx` 注册 `/admin/tasks/:taskId/corrections`；
  - 更新 `web/src/app/admin-review-overview.tsx`，从复核总览增加“处理更正与提醒”入口，并在材料/发票卡片内增加“更正识别字段”“更正金额与字段”“调整分摊”的上下文链接。
- 补齐前端测试与类型边界：
  - 扩展 `web/src/lib/api/types.ts` 和 `web/src/lib/api/trms.ts`，补齐补材料提醒类型与客户端调用；
  - 新增 `web/src/app/admin-corrections-reminders.test.tsx`，覆盖“展示更正入口并记录提醒”“后端拒绝提醒创建时直接展示错误”；
  - 更新 `web/src/app/admin-review-overview.test.tsx`，覆盖复核页到更正/分摊入口的深链。
- 将 `TASKS.md` 中“实现管理员人工更正与提醒页面”标记为已完成。

### 修改文件
- `web/src/app/admin-corrections-reminders.tsx`
- `web/src/app/admin-corrections-reminders.test.tsx`
- `web/src/app/admin-review-overview.tsx`
- `web/src/app/admin-review-overview.test.tsx`
- `web/src/app/routes.tsx`
- `web/src/lib/api/trms.ts`
- `web/src/lib/api/types.ts`
- `web/src/styles.css`
- `TASKS.md`
- `WORKLOG.md`

### 根因
- 现有仓库已经有管理员发票人工录入、更正分摊和补材料提醒后端接口，但这些能力仍然分散：复核总览只能看风险，不能把“哪一张发票、哪一份材料需要处理”直接带到更正页面，也没有前端入口记录提醒。
- 因此管理员在“发现问题 -> 进入更正 -> 记录提醒”这条链路上仍需要手工切换页面和手工定位对象，Web 主链路在复核阶段并不闭合。

### 验证结果
- 已通过：
  - `cd web && npm test -- admin-corrections-reminders admin-review-overview`
    - 2 个前端测试文件、4 个测试通过
  - `cd web && npm run lint`
    - 通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - pytest 165 个用例通过
    - `cd web && npm run lint` 通过
    - `cd web && npm test` 通过，15 个前端测试文件、40 个测试通过
    - `cd web && npm run build` 通过
    - `git diff --check` 通过

### 说明
- 开发过程中第一次全量验证曾在 `cd web && npm run build` 阶段暴露一个真实 TypeScript 空值检查错误：`submitReminder` 内对 `session.actorId` 的访问未被类型收窄。本轮已修复后再次执行 `./scripts/verify.sh`，最终全量验证通过。
- pytest 仍有 3 条既有 `DeprecationWarning`，来源于第三方栈内对 `HTTP_422_UNPROCESSABLE_ENTITY` 的使用，不是本轮新增问题。
- 前端测试期间仍打印 Node `--localstorage-file` 既有警告，但 lint、测试和构建均通过，本轮未新增对此行为的依赖。

### 假设
- “人工更正与提醒页面”当前只负责把复核发现的问题准确导向现有发票录入页和分摊编辑页，不在本页重复实现发票编辑或分摊编辑表单，避免和既有页面职责重叠。
- 补材料提醒当前仍是系统内记录，不调用真实短信、邮件或 Telegram 发送；后续若接入通知渠道，应复用这里的提醒记录作为审计来源，而不是绕过记录直接发送。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“实现导出任务页面”，优先复用现有导出能力边界、任务模型和下载占位，不新增新的导出后端协议。

## 2026-04-28 09:34 - Implement missing materials pages

### 完成内容
- 为缺失材料清单补齐后端读取接口：
  - 在 `src/trms_backend/domain/missing_materials.py` 新增面向页面的可见视图模型与权限边界，管理员可查看任务内全部缺失项，成员只能查看本人缺失项；
  - 在 `src/trms_backend/api/tasks.py` 新增 `GET /api/tasks/{taskId}/missing-materials`，复用现有缺失材料聚合逻辑，不再把 `ready_to_export` 约束的导出接口硬套成页面数据源。
- 为 Web 前端补齐管理员/成员缺失材料页面：
  - 新增 `web/src/app/task-missing-materials.tsx`，提供 `/admin/tasks/:taskId/missing-materials` 与 `/member/materials/missing` 两个入口；
  - 管理员页支持按成员、发票、费用类型切换查看；成员页只展示当前成员本人缺失项，并支持按发票或费用类型查看；
  - 两端均补齐加载、错误和空清单状态。
- 打通前端入口与测试：
  - 更新 `web/src/app/routes.tsx` 注册新路由；
  - 更新 `web/src/app/admin-task-detail.tsx` 与 `web/src/app/member-task-list.tsx` 增加页面入口；
  - 新增 `tests/test_missing_materials_api.py` 与 `web/src/app/task-missing-materials.test.tsx`，并更新 `web/src/app/admin-task-detail.test.tsx`、`web/src/app/member-task-list.test.tsx`；
  - 将 `TASKS.md` 中“实现缺失材料清单页面”标记为已完成。

### 修改文件
- `src/trms_backend/domain/missing_materials.py`
- `src/trms_backend/api/tasks.py`
- `tests/test_missing_materials_api.py`
- `web/src/app/task-missing-materials.tsx`
- `web/src/app/task-missing-materials.test.tsx`
- `web/src/app/routes.tsx`
- `web/src/app/admin-task-detail.tsx`
- `web/src/app/admin-task-detail.test.tsx`
- `web/src/app/member-task-list.tsx`
- `web/src/app/member-task-list.test.tsx`
- `web/src/lib/api/trms.ts`
- `web/src/lib/api/types.ts`
- `TASKS.md`
- `WORKLOG.md`

### 根因
- 仓库已经有缺失材料聚合模型和 CSV 导出实现，但唯一现成入口是导出接口，其访问边界要求任务达到 `ready_to_export` 且只允许管理员调用，无法满足“管理员复核中先查看缺失项”和“成员查看本人缺失材料”这两个页面场景。
- 现有成员材料状态页虽然能从发票校验中看到零散的缺失提示，但缺少一个按任务聚合、按成员/发票/费用类型切换视角的清单页面，导致“补材料”这条前端主链路仍然不完整。

### 验证结果
- 已通过：
  - `uv run pytest tests/test_missing_materials.py tests/test_missing_materials_api.py`
    - 6 个后端相关用例通过
  - `cd web && npm test -- task-missing-materials member-task-list admin-task-detail`
    - 3 个前端测试文件、7 个测试通过
  - `cd web && npm run lint`
    - 通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - pytest 165 个用例通过
    - `cd web && npm run lint` 通过
    - `cd web && npm test` 通过，14 个前端测试文件、38 个测试通过
    - `cd web && npm run build` 通过
    - `git diff --check` 通过

### 说明
- pytest 仍有 3 条既有 `DeprecationWarning`，来源于第三方栈内对 `HTTP_422_UNPROCESSABLE_ENTITY` 的使用，不是本轮新增问题。
- 前端测试期间仍打印 Node `--localstorage-file` 既有警告，但 lint、测试和构建均通过，本轮未新增对此行为的依赖。

### 假设
- 缺失材料页面当前只聚合“缺失材料类规则且状态为 failed”的结果，不把 `pending` 待确认规则伪装成缺失项。
- 成员页严格依赖服务端返回的 `member_id == 当前成员` 条目做展示；即使前端已知道任务成员名单，也不会自行拼接或推断其他成员缺失项。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“实现管理员人工更正与提醒页面”，优先复用现有复核总览、材料提醒和费用异议处理能力。

## 2026-04-28 09:21 - Implement admin review overview page

### 完成内容
- 为管理员补齐复核总览页面：
  - 新增 `web/src/app/admin-review-overview.tsx`，在 `/admin/tasks/:taskId/review` 聚合展示任务级风险摘要、待归属材料、材料识别状态、发票校验结果以及分摊/确认状态；
  - 页面只复用 `GET /api/tasks/{taskId}`、`GET /api/tasks/{taskId}/review-summary` 和 `GET /api/tasks/{taskId}/overdue-confirmations`，不新增独立前端业务流程。
- 为满足复核页“待归属材料突出显示”要求，最小扩展后端复核摘要：
  - 更新 `src/trms_backend/domain/task_review_summary.py` 与 `src/trms_backend/api/tasks.py`，把当前任务 `task_id_hint` 下的待归属材料和计数并入 `review-summary` 返回；
  - 不新增单独待归属查询接口，避免把本轮任务扩散为新的后台能力。
- 打通管理员入口与测试：
  - 更新 `web/src/app/routes.tsx` 注册 `/admin/tasks/:taskId/review`；
  - 更新 `web/src/app/admin-task-detail.tsx`，从任务详情页增加“进入复核总览”入口；
  - 新增 `web/src/app/admin-review-overview.test.tsx`，覆盖“突出显示 Must 级失败/待归属/待确认/异议并展示复核明细”“成员身份不可访问管理员复核页”；
  - 更新 `tests/test_task_review_summary_api.py` 和 `web/src/app/admin-task-detail.test.tsx`，覆盖新的复核摘要字段和详情页入口。
- 将 `TASKS.md` 中“实现管理员复核总览页面”标记为已完成。

### 修改文件
- `src/trms_backend/api/tasks.py`
- `src/trms_backend/domain/task_review_summary.py`
- `tests/test_task_review_summary_api.py`
- `web/src/app/admin-review-overview.tsx`
- `web/src/app/admin-review-overview.test.tsx`
- `web/src/app/admin-task-detail.tsx`
- `web/src/app/admin-task-detail.test.tsx`
- `web/src/app/routes.tsx`
- `web/src/lib/api/types.ts`
- `web/src/styles.css`
- `TASKS.md`
- `WORKLOG.md`

### 根因
- 前几轮已经完成管理员发票录入、分摊编辑和成员确认页面，但管理员仍缺少一个聚合视图，在单页内同时判断“哪些材料还待归属、哪些识别/校验仍异常、哪些成员尚未确认或已提出异议”，导致 Web 端主链路在“成员确认 -> 管理员复核 -> 准备导出”之间仍然断开。
- 现有后端 `review-summary` 已能覆盖材料、识别、校验、分摊和确认大部分明细，但没有暴露与当前任务 `task_id_hint` 相关的待归属材料；如果不先补这块摘要，前端无法满足任务要求中的“待归属材料突出显示”。

### 验证结果
- 已通过：
  - `uv run pytest tests/test_task_review_summary_api.py`
    - 3 个用例通过
  - `cd web && npm test -- admin-review-overview admin-task-detail`
    - 2 个前端测试文件、5 个测试通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - pytest 162 个用例通过
    - `cd web && npm run lint` 通过
    - `cd web && npm test` 通过，13 个前端测试文件、36 个测试通过
    - `cd web && npm run build` 通过
    - `git diff --check` 通过
- 说明：
  - pytest 仍有 3 条既有 `DeprecationWarning`，来源于第三方栈内对 `HTTP_422_UNPROCESSABLE_ENTITY` 的使用，不是本轮新增问题。
  - 前端测试期间仍打印 Node `--localstorage-file` 既有警告，但 lint、测试和构建均通过，本轮未新增对此行为的依赖。

### 假设
- 复核页当前把“待归属材料”限定为 `task_id_hint` 已指向当前任务、但尚未被管理员认领的材料；对完全没有任务提示的待归属材料，本页不会越权展示。
- “未完成确认成员”当前保守地按 `confirmation` 缺失或状态为 `pending` 的分摊来聚合；`disputed` 会在风险摘要和异议列表中单独高亮，但不伪装成已确认。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“实现缺失材料清单页面”，优先复用现有缺失材料导出与校验聚合结果，分别补管理员视角和成员本人视角。

## 2026-04-28 09:08 - Implement member expense confirmation page

### 完成内容
- 为成员入口补齐费用确认页面：
  - 新增 `web/src/app/member-expense-confirmation.tsx`，在 `/member/expenses/confirm` 按任务展示当前成员本人相关的费用明细、归属金额、分摊版本、关联发票摘要和辅助材料摘要；
  - 页面只复用现有 `GET /api/tasks/{taskId}/expense-details`、`GET /api/invoices/{invoice_id}/supporting-materials` 和 `PUT /api/splits/{split_id}/confirmation`，不新增后端接口。
- 打通成员入口：
  - 更新 `web/src/app/routes.tsx` 注册成员确认路由；
  - 更新 `web/src/app/member-task-list.tsx`，从成员任务列表增加“确认费用明细”入口。
- 补齐前端类型与测试：
  - 扩展 `web/src/lib/api/types.ts` 和 `web/src/lib/api/trms.ts`，补齐费用明细和关联附件列表调用边界；
  - 新增 `web/src/app/member-expense-confirmation.test.tsx`，覆盖“展示个人费用与附件摘要并确认”“异议原因必填并可提交异议”“分摊版本失效时提示刷新”；
  - 更新 `web/src/app/member-task-list.test.tsx`，覆盖成员任务卡片到费用确认页的导航入口。
- 将 `TASKS.md` 中“实现成员费用确认页面”标记为已完成。

### 修改文件
- `web/src/app/member-expense-confirmation.tsx`
- `web/src/app/member-expense-confirmation.test.tsx`
- `web/src/app/member-task-list.tsx`
- `web/src/app/member-task-list.test.tsx`
- `web/src/app/routes.tsx`
- `web/src/lib/api/trms.ts`
- `web/src/lib/api/types.ts`
- `web/src/styles.css`
- `TASKS.md`
- `WORKLOG.md`

### 根因
- 前一轮管理员已经具备发票录入与分摊编辑能力，但成员端仍缺少“查看自己最终被分到哪些费用，并对金额作确认或提出异议”的页面，导致“分摊完成 -> 成员确认 -> 管理员最终复核”的 Web 主链路仍然断开。
- 后端实际上已经提供成员费用明细查询、分摊确认/异议提交和关联附件列表接口，当前缺口集中在成员前端的路由、聚合展示和失效版本提示，而不是新的后端业务实现。

### 验证结果
- 已通过：
  - `cd web && npm test -- member-expense-confirmation member-task-list`
    - 2 个前端测试文件、5 个测试通过
  - `cd web && npm run lint`
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - pytest 161 个用例通过
    - `cd web && npm run lint` 通过
    - `cd web && npm test` 通过，12 个前端测试文件、34 个测试通过
    - `cd web && npm run build` 通过
    - `git diff --check` 通过
- 说明：
  - pytest 仍有 3 条既有 `DeprecationWarning`，来源于第三方栈内对 `HTTP_422_UNPROCESSABLE_ENTITY` 的使用，不是本轮新增问题。
  - 前端测试期间仍打印 Node `--localstorage-file` 既有警告，但 lint、测试和构建均通过，本轮未新增对此行为的依赖。

### 假设
- 成员确认页当前按任务维度选择，并只展示 `expense-details` 接口返回的“当前成员本人相关分摊”；不会在前端推断或暴露无关成员费用。
- 分摊版本过旧或已失效的提示当前保守地基于服务端返回 `404 split not found` 识别；页面不会把该失败伪装成确认成功，而是明确提示成员刷新最新明细后再提交。
- 关联附件摘要当前只展示已由后端正式关联到发票的辅助材料；如果成员已上传但管理员尚未关联，页面不会自行猜测“应该属于哪张发票”。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“实现管理员复核总览页面”，直接复用本轮已接入的成员确认状态、异议展示和分摊版本语义。

## 2026-04-28 08:56 - Implement admin split editor page

### 完成内容
- 为管理员补齐费用分摊编辑页面：
  - 新增 `web/src/app/admin-split-editor.tsx`，在 `/admin/tasks/:taskId/splits` 展示任务内已录入发票列表，并允许对单张发票添加、删除和调整一个或多个分摊成员、金额与备注；
  - 页面直接复用 `GET /api/tasks/{taskId}`、`GET /api/tasks/{taskId}/review-summary` 和 `PUT /api/invoices/{invoice_id}/splits`，不新增后端接口。
- 将分摊金额差额与确认状态接入前端：
  - 页面实时显示发票金额、分摊合计、差额和未完成金额行数量，不在前端自动“修正”为成功；
  - 保存后重新拉取任务复核摘要，展示最新分摊记录和成员确认状态，显式暴露服务端拒绝原因。
- 打通管理员入口：
  - 更新 `web/src/app/routes.tsx` 注册 `/admin/tasks/:taskId/splits`；
  - 更新 `web/src/app/admin-task-detail.tsx`，从任务详情页增加“编辑费用分摊”入口。
- 补齐前端测试：
  - 新增 `web/src/app/admin-split-editor.test.tsx`，覆盖“新增分摊行并保存刷新摘要”“服务端拒绝时错误展示”；
  - 更新 `web/src/app/admin-task-detail.test.tsx`，覆盖任务详情页到分摊编辑页的入口链接。
- 将 `TASKS.md` 中“实现费用分摊编辑页面”标记为已完成。

### 修改文件
- `web/src/app/admin-split-editor.tsx`
- `web/src/app/admin-split-editor.test.tsx`
- `web/src/app/admin-task-detail.tsx`
- `web/src/app/admin-task-detail.test.tsx`
- `web/src/app/routes.tsx`
- `web/src/styles.css`
- `TASKS.md`
- `WORKLOG.md`

### 根因
- 前一轮管理员已经可以录入和更正发票字段，但发票事实落库后仍缺少一个前端入口把金额继续分配到任务成员，导致“发票录入 -> 分摊 -> 成员确认”的主链路在 Web 端仍然断开。
- 后端实际上已经具备发票分摊替换接口、管理员复核摘要和确认状态聚合能力；当前缺口集中在管理员页面、差额反馈和错误展示，而不是新的后端业务实现。

### 验证结果
- 已通过：
  - `cd web && npm test -- admin-split-editor admin-task-detail`
    - 2 个前端测试文件、5 个测试通过
  - `cd web && npm run lint`
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - pytest 161 个用例通过
    - `cd web && npm run lint` 通过
    - `cd web && npm test` 通过，11 个前端测试文件、31 个测试通过
    - `cd web && npm run build` 通过
    - `git diff --check` 通过
- 说明：
  - pytest 仍有 3 条既有 `DeprecationWarning`，来源于第三方栈内对 `HTTP_422_UNPROCESSABLE_ENTITY` 的使用，不是本轮新增问题。
  - 前端测试期间仍打印 Node `--localstorage-file` 既有警告，但 lint、测试和构建均通过，本轮未新增对此行为的依赖。

### 假设
- 对尚无既有分摊记录的发票，页面默认把首条分摊行预填为“材料提交人承担整张发票金额”；若提交人缺失或不在任务成员名单中，则回退到任务成员列表中的第一个成员。该保守假设仅用于降低首次录入成本，不改变服务端成员合法性约束。
- 前端当前只校验“成员已选择、金额为正数”，但不会在差额非零时本地伪装失败结论；是否允许保存，仍以服务端真实规则为准。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“实现成员费用确认页面”，直接复用本轮已接入的分摊确认状态、最新版本提示和发票摘要信息。

## 2026-04-28 08:40 - Implement admin invoice entry and correction page

### 完成内容
- 为管理员补齐发票人工录入与更正页面：
  - 新增 `web/src/app/admin-invoice-editor.tsx`，在 `/admin/tasks/:taskId/invoices` 展示当前任务内 `invoice` 类型材料列表，并允许对选中材料录入或更正发票号码、开票日期、交易时间、抬头、税号、销售方、金额和费用类型；
  - 页面直接复用 `GET /api/tasks/{taskId}`、`GET /api/tasks/{taskId}/review-summary` 和 `POST /api/materials/{material_id}/invoice`，不新增后端接口。
- 将识别结果与人工更正边界接入前端：
  - 扩展 `web/src/lib/api/types.ts`，补齐 `review-summary` 中的材料/发票聚合结构，以及识别任务 `manual_corrections`、字段来源、置信度和重新校验状态类型；
  - 页面按字段展示识别来源、置信度、待确认状态和人工更正历史，并在保存后显式刷新任务摘要与校验结果，不在前端伪装“应该已重算”。
- 打通管理员入口：
  - 更新 `web/src/app/routes.tsx` 注册 `/admin/tasks/:taskId/invoices`；
  - 更新 `web/src/app/admin-task-detail.tsx`，从任务详情页增加“录入或更正发票”入口。
- 补齐前端测试：
  - 新增 `web/src/app/admin-invoice-editor.test.tsx`，覆盖“识别字段与待确认提示展示”“成功保存并刷新校验结果”“服务端拒绝时错误展示”；
  - 更新 `web/src/app/admin-task-detail.test.tsx`，覆盖任务详情页到发票录入页的入口链接。
- 将 `TASKS.md` 中“实现发票人工录入和更正页面”标记为已完成。

### 修改文件
- `web/src/app/admin-invoice-editor.tsx`
- `web/src/app/admin-invoice-editor.test.tsx`
- `web/src/app/admin-task-detail.tsx`
- `web/src/app/admin-task-detail.test.tsx`
- `web/src/app/routes.tsx`
- `web/src/lib/api/types.ts`
- `web/src/styles.css`
- `TASKS.md`
- `WORKLOG.md`

### 根因
- 前一轮成员侧已能上传并查看材料状态，但管理员仍缺少一个前端入口，把“识别建议”真正转成当前系统中的发票事实记录，也无法在页面上直接查看字段来源、低置信度提示和更正后的重新校验反馈。
- 后端实际上已经具备 `review-summary` 聚合、发票录入/更正、识别字段人工更正记录和校验刷新能力；缺口集中在管理员页面、前端类型和交互串联，而不是新的后端业务实现。

### 验证结果
- 已通过：
  - `cd web && npm test -- admin-invoice-editor admin-task-detail`
    - 2 个前端测试文件、6 个测试通过
  - `cd web && npm run lint`
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - pytest 161 个用例通过
    - `cd web && npm run lint` 通过
    - `cd web && npm test` 通过，10 个前端测试文件、29 个测试通过
    - `cd web && npm run build` 通过
    - `git diff --check` 通过
- 说明：
  - pytest 仍有 3 条既有 `DeprecationWarning`，来源于第三方栈内对 `HTTP_422_UNPROCESSABLE_ENTITY` 的使用，不是本轮新增问题。
  - 前端测试期间仍打印 Node `--localstorage-file` 既有警告，但 lint、测试和构建均通过，本轮未新增对此行为的依赖。

### 假设
- 本轮保守地先把“发票人工录入与更正”入口落在管理员路径 `/admin/tasks/:taskId/invoices`；成员侧若后续需要直接编辑，可复用本轮字段展示与保存边界在独立任务中扩展。
- 金额输入在前端按“元”展示并转换为后端 `amount_cents`；交易时间使用本地 `datetime-local` 输入并在提交时显式带上本地时区偏移，避免前端静默丢失时间语义。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“实现费用分摊编辑页面”，直接复用本轮已接入的发票列表、当前校验状态和任务允许费用类型信息。

## 2026-04-28 08:25 - Implement member material status page

### 完成内容
- 为成员入口补齐 Web 材料状态页面：
  - 新增 `web/src/app/member-material-status.tsx`，在 `/member/materials/status` 按任务查看当前成员本人提交材料的识别状态、校验状态和缺失材料提示；
  - 页面继续复用现有 `GET /api/tasks`、`GET /api/tasks/{task_id}/materials`、`GET /api/tasks/{task_id}/invoices`、`GET /api/materials/{material_id}/recognition-tasks` 和 `GET /api/invoices/{invoice_id}/validations`，不新增后端接口。
- 将成员任务列表、上传页与状态页连通：
  - 更新 `web/src/app/member-task-list.tsx`，为成员可见任务增加“查看材料状态”入口；
  - 更新 `web/src/app/member-material-upload.tsx` 与 `web/src/app/routes.tsx`，支持从上传页跳转到当前任务状态页，并注册 `/member/materials/status` 路由。
- 补齐成员状态页前端测试：
  - 新增 `web/src/app/member-material-status.test.tsx`，覆盖“只显示当前成员材料，不暴露同任务其他成员材料”“展示识别状态、校验异常和缺失材料提示”“无本人材料时空状态”“聚合失败时错误展示”；
  - 更新 `web/src/app/member-task-list.test.tsx`，覆盖任务卡片到状态页的导航入口。
- 将 `TASKS.md` 中“实现成员材料状态页面”标记为已完成。

### 修改文件
- `web/src/app/member-material-status.tsx`
- `web/src/app/member-material-status.test.tsx`
- `web/src/app/member-material-upload.tsx`
- `web/src/app/member-task-list.tsx`
- `web/src/app/member-task-list.test.tsx`
- `web/src/app/routes.tsx`
- `web/src/lib/api/trms.ts`
- `web/src/lib/api/types.ts`
- `web/src/styles.css`
- `TASKS.md`
- `WORKLOG.md`

### 根因
- 前一轮成员入口已经具备任务列表和材料上传，但成员仍无法在前端看到“自己已交材料目前识别到哪一步、是否有校验异常、还缺什么附件”，导致成员 Web 主流程在上传后仍然断开。
- 后端已经提供材料列表、识别任务、发票列表和校验结果等读接口；当前缺口只在前端聚合和只看本人材料的展示边界，不需要扩散到新的后端业务实现。

### 验证结果
- 已通过：
  - `cd web && npm test -- member-material-status member-task-list member-material-upload App`
    - 7 个前端测试文件、22 个测试通过
  - `cd web && npm run lint`
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - pytest 161 个用例通过
    - `cd web && npm run lint` 通过
    - `cd web && npm test` 通过，9 个前端测试文件、26 个测试通过
    - `cd web && npm run build` 通过
    - `git diff --check` 通过
- 说明：
  - pytest 仍有 3 条既有 `DeprecationWarning`，来源于后端已有 `HTTP_422_UNPROCESSABLE_ENTITY` 常量使用，不是本轮新增问题。
  - 前端测试期间仍打印 Node `--localstorage-file` 既有警告，但测试与构建均通过，本轮未新增对此行为的依赖。

### 假设
- 成员状态页当前只聚合当前成员本人提交的材料；同任务其他成员材料即使存在于后端列表中，也不会在前端展示。
- 缺失材料提示当前保守地基于已有发票校验结果推导；对尚未录入为发票的材料，页面明确显示“暂无独立发票校验”，不伪造不存在的校验状态。
- 当前页只做只读状态查看，不提前实现成员费用确认、管理员提醒或人工更正入口；这些内容留给后续对应任务。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“实现发票人工录入和更正页面”，直接复用本轮已经接入的材料状态视图、识别任务结果和发票校验反馈。

## 2026-04-28 08:08 - Implement member web material upload page

### 完成内容
- 为成员入口补齐 Web 材料上传页面：
  - 新增 `web/src/app/member-material-upload.tsx`，在 `/member/materials/upload` 提供任务选择、材料类型选择和多文件上传表单；
  - 上传请求固定走现有 `POST /api/tasks/{task_id}/materials`，前端显式写死 `channel=web`，不伪造其他渠道。
- 将成员任务列表与上传页连通：
  - 更新 `web/src/app/member-task-list.tsx` 与 `web/src/app/routes.tsx`，对开放中的可见任务增加“上传材料”入口，并支持通过 `taskId` 查询参数预选任务。
- 补齐成员上传页测试与结果展示：
  - 新增 `web/src/app/member-material-upload.test.tsx`，覆盖“仅允许当前成员可见且开放的任务上传”“批量上传部分成功时展示材料编号、重复状态和逐文件失败原因”“无开放任务时空状态”；
  - 更新 `web/src/app/member-task-list.test.tsx`，覆盖成员任务卡片到上传页的导航入口。
- 将 `TASKS.md` 中“实现成员 Web 材料上传页面”标记为已完成。

### 修改文件
- `web/src/app/member-material-upload.tsx`
- `web/src/app/member-material-upload.test.tsx`
- `web/src/app/member-task-list.tsx`
- `web/src/app/member-task-list.test.tsx`
- `web/src/app/routes.tsx`
- `web/src/styles.css`
- `TASKS.md`
- `WORKLOG.md`

### 根因
- 前一轮成员入口已经能列出本人可见任务，但仍缺少“成员实际把发票或附件交进系统”的下一步页面，导致成员 Web 主流程停在任务浏览，无法覆盖 FR-002 的 Web 提交主路径。
- 后端已经具备材料上传接口、批量部分成功返回、重复文件标记和失败原因暴露能力；当前缺口只在前端路由、表单和结果展示边界，不需要扩散到新的后端实现。

### 验证结果
- 已通过：
  - `npm test -- member-material-upload member-task-list App`
    - 6 个前端测试文件、19 个测试通过
  - `npm run lint`
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - pytest 161 个用例通过
    - `cd web && npm run lint` 通过
    - `cd web && npm test` 通过，8 个前端测试文件、23 个测试通过
    - `cd web && npm run build` 通过
    - `git diff --check` 通过
- 说明：
  - pytest 仍有 3 条既有 `DeprecationWarning`，来源于后端已有 `HTTP_422_UNPROCESSABLE_ENTITY` 常量使用，不是本轮新增问题。
  - `npm test` 期间仍打印 Node `--localstorage-file` 既有警告，但前端测试与构建均通过，本轮未新增对此行为的依赖。

### 假设
- 成员上传页当前只允许选择状态为 `open` 且 `task.member_ids` 包含当前 mock 成员的任务；对已关闭、复核中或已归档任务，不在前端伪造“补交仍可成功”的路径。
- 提交渠道在成员 Web 页固定为 `web`，页面只暴露材料类型选择，不提前实现 CLI、Telegram 或邮件渠道切换入口。
- 上传结果当前仅展示后端已直接返回的材料记录、重复关系和失败原因，不额外推断识别状态、校验状态或缺失材料提示；这些内容留给后续“成员材料状态页面”任务。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“实现成员材料状态页面”，直接复用本轮已经接入的成员任务可见性边界和上传结果入口。

## 2026-04-28 07:58 - Implement member web task list page

### 完成内容
- 为成员入口补齐首个真实业务页面：
  - 新增 `web/src/app/member-task-list.tsx`，在 `/member` 展示当前 mock 成员可见的报销任务列表；
  - 页面复用现有 `GET /api/tasks`，前端按 `task.member_ids` 包含当前成员 `actor_id` 做可见范围过滤，不新增后端接口。
- 将成员路由从占位页接入真实页面：
  - 更新 `web/src/app/routes.tsx` 与 `web/src/app/auth.tsx`，让成员入口像管理员入口一样走嵌套路由；
  - 保留系统管理员入口占位，不提前实现无关页面。
- 补齐成员任务页测试：
  - 新增 `web/src/app/member-task-list.test.tsx`，覆盖“只显示当前成员可见任务”和“无任务时空状态”；
  - 更新 `web/src/app/App.test.tsx`，覆盖从 `/login?next=/member` 进入成员真实页面。
- 将 `TASKS.md` 中“实现成员 Web 可提交任务页面”标记为已完成。

### 修改文件
- `web/src/app/member-task-list.tsx`
- `web/src/app/member-task-list.test.tsx`
- `web/src/app/routes.tsx`
- `web/src/app/auth.tsx`
- `web/src/app/pages.tsx`
- `web/src/app/App.test.tsx`
- `TASKS.md`
- `WORKLOG.md`

### 根因
- 现有前端只有管理员链路已进入真实业务页面，成员入口仍停留在纯占位提示，导致 Web 主流程缺少“成员先看到自己该向哪个任务提交材料”的起点。
- 后端已经提供任务列表契约，且任务模型自带 `member_ids`；当前缺口只在前端可见性过滤、成员路由接入和空状态展示，不需要扩散到新的后端实现。

### 验证结果
- 已通过：
  - `npm test -- member-task-list App`
    - `web/src/app/member-task-list.test.tsx` 与相关路由测试通过，共 5 个测试文件、17 个测试通过
  - `npm run lint`
  - `./scripts/verify.sh`
- 说明：
  - `npm test` 期间仍打印 Node `--localstorage-file` 既有警告，但测试通过，本轮未新增对此行为的依赖。

### 假设
- 在真实鉴权、成员参与历史和“已参与任务”专用聚合接口接入前，成员页当前只按 `task.member_ids` 过滤可见任务；这覆盖“本人可参与任务”主路径，但不额外推断已脱离成员名单的历史参与任务。
- 本轮只实现成员任务列表页，不提前实现材料上传、材料状态、费用确认或成员侧其他业务页面。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“实现成员 Web 材料上传页面”，直接复用本轮已经打通的 `/member` 入口和可见任务列表。

## 2026-04-28 07:53 - Implement admin task detail page

### 完成内容
- 为管理员后台补齐任务详情与状态操作页面：
  - 新增 `web/src/app/admin-task-detail.tsx`，在 `/admin/tasks/:taskId` 展示任务基础信息、成员名单、允许费用类别和当前状态；
  - 页面直接接入现有 `GET /api/tasks/{taskId}` 与 `PATCH /api/tasks/{taskId}/status`，不新增后端接口或额外业务逻辑。
- 补齐管理员详情页状态流转边界：
  - 前端只展示当前状态机允许的下一步流转按钮，避免在 mock 阶段提供与后端状态机不一致的伪操作；
  - 当后端因发布条件不足、复核未完成或未记录导出完成事实而拒绝流转时，通过统一 `ApiErrorNotice` 显式展示错误，不在前端伪装成功。
- 将管理员列表与详情页连通：
  - 在 `web/src/app/routes.tsx` 新增 `/admin/tasks/:taskId` 路由；
  - 在 `web/src/app/admin-task-list.tsx` 每个任务卡片增加“查看详情与状态操作”入口，避免详情页成为孤页。
- 新增 `web/src/app/admin-task-detail.test.tsx`，覆盖：
  - 任务基础信息、成员名单、费用类别和允许流转按钮渲染；
  - 状态流转成功后页面状态更新；
  - 状态流转被后端拒绝时的错误展示。
- 将 `TASKS.md` 中“实现任务详情与状态操作页面”标记为已完成。

### 修改文件
- `web/src/app/admin-task-detail.tsx`
- `web/src/app/admin-task-detail.test.tsx`
- `web/src/app/admin-task-list.tsx`
- `web/src/app/routes.tsx`
- `web/src/styles.css`
- `TASKS.md`
- `WORKLOG.md`

### 根因
- 前一轮已经有管理员任务列表和任务创建页，但管理员仍无法在前端进入单个任务查看完整配置，也无法从前端触发现有后端状态流转接口。
- 如果继续实现成员上传、复核或导出页，而不先补任务详情页，管理员主链路会长期停留在“能看到列表、能创建任务，但无法进入任务内部操作”的断点状态。
- 后端已经具备任务详情查询和状态流转契约，本轮缺口仅在前端页面、路由和错误展示边界，不需要扩散到新的后端实现。

### 验证结果
- 已通过：
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - pytest 161 个用例通过
    - `cd web && npm run lint` 通过
    - `cd web && npm test` 通过，6 个前端测试文件、18 个测试通过
    - `cd web && npm run build` 通过
    - `git diff --check` 通过
- 说明：
  - pytest 仍有 3 条既有 `DeprecationWarning`，来源于后端已有 `HTTP_422_UNPROCESSABLE_ENTITY` 常量使用，不是本轮新增问题。
  - `npm test` 期间仍打印 Node `--localstorage-file` 既有警告，但前端测试与构建均通过，本轮未新增对此行为的依赖。

### 假设
- 任务详情页当前保守地仅在前端允许操作 `administrator_id` 与当前 mock 管理员一致的任务；若直接访问其他管理员任务，只展示范围提示，不暴露状态流转按钮。
- 状态流转页当前只调用已有任务状态接口，不提前实现任务成员编辑、复核汇总或导出能力，以避免超出本轮最小任务范围。
- 费用类别当前继续复用后端枚举值到中文标签的静态映射，不引入新的配置接口或元数据服务。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“实现成员 Web 可提交任务页面”，把成员前端入口从当前占位页推进到真实可见任务列表。

## 2026-04-28 07:43 - Implement admin task create page

### 完成内容
- 为管理员后台补齐独立的任务创建页面：
  - 新增 `web/src/app/admin-task-create.tsx`，在 `/admin/tasks/new` 提供比赛信息、成员名单、费用类别、管理员、项目、报销人、抬头和税号表单；
  - 成员名单使用可增删行输入，前端显式拦截“空成员项”；费用类别使用固定选项复选框，避免提交不受支持的自由文本。
- 调整管理员入口路由边界：
  - 将 `/admin` 改为受保护的嵌套路由，保留任务列表首页，并新增 `/admin/tasks/new` 创建页；
  - 在管理员任务列表页补充“创建新任务”入口，避免新页面成为不可达孤页。
- 补齐任务创建页面的前端校验和错误展示：
  - 前端校验比赛名称、地点、起止日期、截止时间、成员名单、费用类别、管理员、项目和报销人信息；
  - 当前端发现比赛结束日期早于开始日期或成员名单存在空项时，不发请求，直接在页面展示错误；
  - 抬头和税号保守地允许留空，由后端决定是否继承全局配置；若后端返回 `422`，页面通过统一 `ApiErrorNotice` 显式展示。
- 新增 `web/src/app/admin-task-create.test.tsx`，覆盖：
  - 页面渲染与成功提交后回到管理员任务列表；
  - 前端校验阻止非法日期和空成员项提交；
  - 后端创建失败时展示服务端错误。
- 将 `TASKS.md` 中“实现管理员任务创建页面”标记为已完成。

### 修改文件
- `web/src/app/admin-task-create.tsx`
- `web/src/app/admin-task-create.test.tsx`
- `web/src/app/admin-task-list.tsx`
- `web/src/app/auth.tsx`
- `web/src/app/routes.tsx`
- `web/src/styles.css`
- `TASKS.md`
- `WORKLOG.md`

### 根因
- 前一轮虽然已经有管理员任务列表，但管理员仍无法在前端创建任务，导致后台只有“看已有任务”的入口，没有“进入主流程的起点”。
- 如果继续做任务详情、成员上传或复核页，而不先补任务创建页，前端管理员主链路会长期缺少起点，后续页面只能依赖手工预置数据，验证链路不完整。
- 后端现有 `POST /api/tasks` 已具备创建契约和字段校验能力，本轮只需补前端表单和路由，不需要新增后端接口或业务逻辑。

### 验证结果
- 已通过：
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - pytest 161 个用例通过
    - `cd web && npm run lint` 通过
    - `cd web && npm test` 通过，5 个前端测试文件、15 个测试通过
    - `cd web && npm run build` 通过
    - `git diff --check` 通过
- 说明：
  - pytest 仍有 3 条既有 `DeprecationWarning`，来源于后端已有 `HTTP_422_UNPROCESSABLE_ENTITY` 常量使用，不是本轮新增问题。
  - `npm test` 期间仍打印 Node `--localstorage-file` 既有警告，但前端测试和构建均通过，本轮未新增对此行为的依赖。

### 假设
- 任务创建页中的发票抬头和税号当前允许留空，前端不重复实现“是否有全局默认配置”的判断，交由后端按现有规则决定是否继承或报错。
- 当前 `/admin` 嵌套路由只扩展到创建页，不提前实现任务详情、状态操作或成员页面，以避免超出本轮最小任务范围。
- 成员名单当前按“每行一个成员标识”的输入行模型处理，不额外引入成员搜索、自动补全或批量导入。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“实现任务详情与状态操作页面”，直接复用本轮已经建立的 `/admin/tasks/new` 与 `/admin` 路由边界。

## 2026-04-28 07:33 - Implement admin task list page

### 完成内容
- 将 `/admin` 从纯占位页替换为首个真实业务页面“管理员任务列表”：
  - 新增 `web/src/app/admin-task-list.tsx`，接入 `/api/tasks`、`/api/tasks/{id}/review-summary` 和 `/api/tasks/{id}/overdue-confirmations`；
  - 列表页展示任务编号、比赛名称、状态、截止时间、材料/发票数量、确认进度和异常摘要；
  - 支持按任务状态筛选，以及按任务编号或比赛名称做基础搜索。
- 补齐管理员列表的异常摘要聚合：
  - 显式展示 Must 级失败校验、识别失败、识别待人工确认、成员异议、待确认费用明细和逾期未确认成员；
  - 当任务当前无异常时，返回明确“当前无异常”提示，而不是留空。
- 为前端 mock 会话补充稳定 actor id：
  - 在 `auth-store.ts` 和 `role-routes.tsx` 中为成员、管理员、系统管理员增加 mock actor id；
  - 管理员页面据此调用需要 `actor_id` 的后端接口，不再伪造匿名管理员访问。
- 扩展前端 API 合同和测试：
  - 在 `web/src/lib/api/types.ts`、`web/src/lib/api/trms.ts` 中补充复核摘要和逾期确认摘要类型/请求；
  - 新增 `web/src/app/admin-task-list.test.tsx`，覆盖列表渲染、异常摘要、搜索/筛选、加载态、空态和错误态；
  - 更新 `web/src/app/App.test.tsx`，把 `/admin` 登录跳转断言改为真实列表页。
- 将 `TASKS.md` 中“实现管理员任务列表页面”标记为已完成。

### 修改文件
- `web/src/app/admin-task-list.tsx`
- `web/src/app/admin-task-list.test.tsx`
- `web/src/app/App.test.tsx`
- `web/src/app/auth-store.ts`
- `web/src/app/auth.tsx`
- `web/src/app/pages.tsx`
- `web/src/app/role-routes.tsx`
- `web/src/lib/api/trms.ts`
- `web/src/lib/api/types.ts`
- `web/src/styles.css`
- `TASKS.md`
- `WORKLOG.md`

### 根因
- 前两轮前端已经具备路由门禁、mock 登录态、统一 API 客户端和错误展示边界，但 `/admin` 仍只是纯静态占位。
- 如果继续做任务创建页或详情页而不先落地管理员任务列表，管理员后台仍没有任何“从入口进入真实数据”的主导航页面，后续页面会缺少统一的任务上下文入口。
- 后端现有接口已经能提供任务列表、复核摘要和逾期确认摘要，足够支撑管理员列表页的最小实现，没有必要为这一轮再扩散到新的后端接口或额外状态模型。

### 验证结果
- 已通过：
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - pytest 161 个用例通过
    - `cd web && npm run lint` 通过
    - `cd web && npm test` 通过，4 个前端测试文件、12 个测试通过
    - `cd web && npm run build` 通过
    - `git diff --check` 通过
- 说明：
  - pytest 仍有 3 条既有 `DeprecationWarning`，来源于后端已有 `HTTP_422_UNPROCESSABLE_ENTITY` 常量使用，不是本轮新增问题。
  - `npm test` 期间仍打印 Node `--localstorage-file` 既有警告，但前端测试和构建均通过；本轮未新增对该行为的依赖。

### 假设
- 在真实鉴权尚未接入前，管理员任务列表当前保守地只展示 `administrator_id` 与当前 mock 管理员 `actor_id` 一致的任务，避免前端在无权限边界时误展示其他管理员任务。
- “异常摘要”当前只使用现有后端可直接提供的复核摘要和逾期确认摘要，不额外虚构“任务级综合健康分”之类的新字段。
- 基础搜索当前仅覆盖任务编号和比赛名称；更复杂的后端分页、服务端搜索或多字段组合筛选留给后续任务。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“实现管理员任务创建页面”，直接复用本轮已经补齐的管理员列表入口、mock actor id 和统一错误展示边界。

## 2026-04-28 07:23 - Add web login placeholder and role gate

### 完成内容
- 在 `web/src/app/` 建立前端 mock 登录态边界：
  - 新增 `auth-store.ts`，集中管理本地 mock 角色会话、登录跳转路径和测试环境下的内存回退；
  - 新增 `auth.tsx`，提供 `/login` 登录占位页和角色受保护路由包装。
- 为成员、管理员、系统管理员三类入口补齐前端门禁：
  - 未登录访问 `/member`、`/admin`、`/system` 时会被重定向到 `/login`；
  - 已登录但角色不匹配时，显式展示角色错配占位，而不是静默放行或吞掉问题。
- 调整首页和角色占位页文案：
  - 首页显示当前 mock 会话状态、切换入口和“未接真实 OAuth”的边界说明；
  - `RoleShell` 改为通用容器，供受保护角色页和错配提示复用。
- 补充前端测试，覆盖：
  - 首页角色入口与登录占位文案；
  - 未登录访问管理员页会跳转到登录页；
  - 以 mock 管理员身份登录后可进入请求页；
  - 角色错配时返回明确提示。
- 将 `TASKS.md` 中“建立 Web 登录和角色入口占位”标记为已完成。

### 修改文件
- `web/src/app/auth-store.ts`
- `web/src/app/auth.tsx`
- `web/src/app/role-routes.tsx`
- `web/src/app/routes.tsx`
- `web/src/app/pages.tsx`
- `web/src/app/App.test.tsx`
- `web/src/components/RoleShell.tsx`
- `web/src/styles.css`
- `TASKS.md`
- `WORKLOG.md`

### 根因
- 前一轮已经有前端路由骨架和 API 合同层，但还没有任何“未登录不可进入业务页”的统一前端门禁。
- 如果继续直接做管理员列表或成员上传页，每个页面都需要各自拼接临时登录态和角色判断，前端权限边界会立刻分散，后续再收敛会产生返工。
- 需求文档和架构文档都要求成员、管理员、系统管理员三类角色入口明确分离；在真实 OAuth 尚未接入前，需要先把 mock 会话和路由守卫边界固定下来。

### 验证结果
- 已通过：
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - pytest 161 个用例通过
    - `cd web && npm run lint` 通过
    - `cd web && npm test` 通过，3 个前端测试文件、8 个测试通过
    - `cd web && npm run build` 通过
    - `git diff --check` 通过
- 说明：
  - pytest 仍有 3 条既有 `DeprecationWarning`，来源于后端已有 `HTTP_422_UNPROCESSABLE_ENTITY` 常量使用，不是本轮新增问题。
  - `npm test` 期间仍打印 1 条 Node `--localstorage-file` 警告，但测试与构建均通过；本轮已在前端 mock 会话 store 中对非标准 `localStorage` 环境做了显式内存回退，不影响当前任务结论。

### 假设
- 本轮 Web 登录只服务于前端页面开发和权限入口联调，不与后端认证、真实用户资料或令牌交换耦合。
- mock 会话仅保存角色和占位身份信息；不模拟刷新令牌、会话过期或后端鉴权失败，这些边界留给后续真实认证任务。
- 角色错配时当前选择显式展示“不可访问”占位页，而不是自动跳转到当前角色首页，以避免掩盖权限问题。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“实现管理员任务列表页面”，直接复用当前 `/admin` 受保护入口、mock 管理员身份和统一错误展示边界。

## 2026-04-28 07:12 - Establish frontend API contract and error boundary

### 完成内容
- 在 `web/src/lib/api/` 建立前端 API 合同层：
  - 新增 `types.ts`，补齐任务、材料、发票、分摊、确认、校验和导出相关的基础类型定义；
  - 新增 `trms.ts`，集中封装前端对现有后端接口的请求入口，避免后续业务页面重复手写路径和返回类型。
- 统一前端错误处理边界：
  - 新增 `errors.ts`，统一解析 FastAPI 常见 `detail` 字符串、字段校验数组和网络失败；
  - 调整 `web/src/lib/api/client.ts`，请求失败时抛出带 `summary` 的 `ApiError`，不再把服务端错误或网络错误裸漏给页面自行拼接。
- 新增 `web/src/components/ApiErrorNotice.tsx`，作为页面级统一错误展示组件占位。
- 更新首页骨架文案和样式，显式记录“合同层”和“错误展示”边界。
- 新增前端测试，覆盖：
  - `ApiClient` 对字段校验错误、普通服务端错误和网络错误的归一化；
  - `ApiErrorNotice` 的用户可见渲染；
  - 首页对新合同边界说明的展示。
- 将 `TASKS.md` 中“建立前端 API 类型与错误处理边界”标记为已完成。

### 修改文件
- `web/src/lib/api/client.ts`
- `web/src/lib/api/errors.ts`
- `web/src/lib/api/trms.ts`
- `web/src/lib/api/types.ts`
- `web/src/components/ApiErrorNotice.tsx`
- `web/src/components/ApiErrorNotice.test.tsx`
- `web/src/lib/api/client.test.ts`
- `web/src/app/pages.tsx`
- `web/src/app/App.test.tsx`
- `web/src/styles.css`
- `TASKS.md`
- `WORKLOG.md`

### 根因
- 前一轮只固化了前端工程、路由和基础 `ApiClient`，但还没有任何与后端领域模型对齐的前端类型定义。
- 当前 `ApiClient` 只能把部分字符串错误抛出来，无法统一表达 FastAPI 的字段校验错误，也没有网络失败的统一展示语义。
- 如果继续推进管理员列表、创建页或上传页，而不先补齐合同层和错误边界，后续每个页面都会重复定义字段、拼接路径并各自处理错误，直接制造前端技术债。

### 验证结果
- 已通过：
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - pytest 161 个用例通过
    - `cd web && npm run lint` 通过
    - `cd web && npm test` 通过，3 个前端测试文件、6 个测试通过
    - `cd web && npm run build` 通过
    - `git diff --check` 通过
- 说明：
  - pytest 仍有 3 条既有 `DeprecationWarning`，来源于后端已有 `HTTP_422_UNPROCESSABLE_ENTITY` 常量使用，不是本轮新增问题。

### 假设
- 当前前端合同层只覆盖仓库内已经存在的后端接口形状，不额外虚构新的接口字段。
- 导出相关接口按当前后端事实处理：
  - 报销汇总、成员明细、发票明细、缺失材料清单仍按 CSV 文本下载边界封装；
  - 财务填报草稿和合并 PDF 计划按 JSON 结构封装。
- 本轮只建立合同层与错误展示边界，不接入真实业务页面的数据加载和交互状态管理。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“建立 Web 登录和角色入口占位”，把未登录拦截、角色入口选择和 mock 身份上下文接到现有路由骨架上。

## 2026-04-28 07:08 - Bootstrap web frontend skeleton

### 完成内容
- 在 `web/` 下建立独立 React + TypeScript + Vite 工程骨架：
  - 新增前端入口 `web/src/main.tsx`；
  - 新增路由边界 `web/src/app/routes.tsx`，为成员、管理员、系统管理员三类入口保留独立路径；
  - 新增 API 客户端边界 `web/src/lib/api/client.ts`，统一封装基础 URL、JSON 请求和错误抛出，不在前端静默吞掉服务端错误。
- 建立最小前端验证链路：
  - 新增 `eslint`、`vitest`、`vite build` 配置；
  - 新增前端路由骨架测试 `web/src/app/App.test.tsx`；
  - 扩展 `scripts/verify.sh`，在检测到 `web/package.json` 后自动进入 `web/` 执行 `npm run lint`、`npm test` 和 `npm run build`。
- 更新 `README.md` 记录前端本地安装、启动与统一验证方式。
- 将 `TASKS.md` 中“建立 Web 前端项目骨架”标记为已完成。

### 修改文件
- `web/package-lock.json`
- `web/package.json`
- `web/tsconfig.json`
- `web/tsconfig.app.json`
- `web/tsconfig.node.json`
- `web/vite.config.ts`
- `web/eslint.config.js`
- `web/index.html`
- `web/src/main.tsx`
- `web/src/app/App.tsx`
- `web/src/app/router.tsx`
- `web/src/app/routes.tsx`
- `web/src/app/pages.tsx`
- `web/src/app/role-routes.tsx`
- `web/src/app/App.test.tsx`
- `web/src/components/RoleShell.tsx`
- `web/src/lib/api/client.ts`
- `web/src/styles.css`
- `web/src/vite-env.d.ts`
- `web/src/test/setup.ts`
- `scripts/verify.sh`
- `README.md`
- `TASKS.md`
- `WORKLOG.md`

### 根因
- 当前仓库虽然已经确认前端技术栈和目录边界，但仍完全缺少 `web/` 工程、路由入口和前端 API 访问边界。
- 如果继续推进管理员列表或成员上传页面，而不先固化前端工程和统一验证方式，后续每个页面任务都会在工程初始化、脚本命名和错误处理边界上重复返工。

### 验证结果
- 已通过：
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - pytest 161 个用例通过
    - `cd web && npm run lint` 通过
    - `cd web && npm test` 通过，2 个前端测试通过
    - `cd web && npm run build` 通过
    - `git diff --check` 通过

### 假设
- 当前任务只建立前端工程骨架，不引入真实登录态、业务 API 类型明细或具体业务页面。
- 路由先按成员、管理员、系统管理员三类入口拆分路径；真实鉴权门禁和角色切换占位将在下一任务实现。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“建立前端 API 类型与错误处理边界”，把任务、材料、发票、分摊、确认、校验和导出的类型定义补齐到前端。

## 2026-04-28 06:48 - Confirm web frontend stack boundary

### 完成内容
- 确认第一阶段 Web 前端继续采用架构文档建议的 `React + TypeScript + Vite`，管理后台组件库采用 `Ant Design` 方向，不在本轮引入其他前端框架分支。
- 明确前端工程边界：
  - 前端目录规划为仓库根目录下独立 `web/`；
  - 前端作为单独 Node 工程维护自身 `package.json`，不与当前 Python 根工程混写；
  - 成员提交入口和管理员后台共用同一个 Web 工程，通过路由做角色入口隔离，而不是拆成两个前端项目。
- 明确后续命令边界：
  - 安装：`cd web && npm install`
  - 启动：`cd web && npm run dev`
  - 构建：`cd web && npm run build`
  - 测试：`cd web && npm test`
  - 代码检查：`cd web && npm run lint`
- 将 `TASKS.md` 中“确认 Web 前端技术栈和工程边界”标记为已完成。

### 修改文件
- `TASKS.md`
- `WORKLOG.md`

### 根因
- 当前仓库只有后端 FastAPI 工程，没有任何 Web 前端目录、Node 工程边界或命令约定。
- 如果直接进入“建立 Web 前端项目骨架”而不先固化技术栈和目录边界，下一轮很容易在目录命名、组件库选择和验证命令上反复返工，污染后续页面任务的最小改动边界。

### 验证结果
- 已通过：
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - pytest 161 个用例通过
    - `git diff --check` 通过
- 说明：
  - 当前仓库尚未创建 `web/` 前端工程，因此前端启动、构建、测试和 lint 命令本轮只完成边界确认，未实际执行；这符合本任务“不实现业务页面”的约束。

### 假设
- 采用单一 `web/` 工程同时承载成员端和管理员端，优先降低第一阶段工程复杂度；若后续出现完全不同的认证域或部署边界，再评估拆分多前端工程。
- 本轮不新增 `package.json`，因此 `scripts/verify.sh` 仍只验证现有 Python 工程；待下一轮建立前端骨架时，再把前端 lint/test/build 接入统一验证。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“建立 Web 前端项目骨架”，在 `web/` 下补最小 Vite + React + TypeScript 入口，并同步扩展 `./scripts/verify.sh` 的前端验证路径。

## 2026-04-28 06:45 - Bind export jobs to task data version

### 完成内容
- 在 `src/trms_backend/domain/exports.py` 增加导出任务版本快照边界：
  - 新增 `TaskExportVersionSnapshot`；
  - 基于任务、材料、发票、校验、分摊和当前确认记录计算稳定的 `task_data_version` 哈希；
  - 为导出任务记录补充 `task_status_at_request`、`task_data_version` 和 `is_latest_for_task` 语义。
- 在 `src/trms_backend/api/exports.py` 为导出任务创建、列表和状态更新统一计算当前任务导出版本：
  - 创建导出任务时把当前任务状态和数据版本写入记录；
  - 列表和状态接口返回 `is_latest_for_task`，显式标记旧导出是否已过期。
- 在 `src/trms_backend/infrastructure/repositories.py` 复用现有 `parameters` 持久化版本元数据：
  - 以保留键写入任务状态和版本；
  - 对外响应时把这些内部元数据从用户参数中剥离，避免污染原始导出参数。
- 在 `tests/test_exports_api.py` 增加回归测试，覆盖：
  - 导出任务创建后会返回版本元数据；
  - 任务数据变化后，旧导出会被标记为非最新；
  - 导出任务状态流转返回仍保留最新标记。
- 将 `TASKS.md` 中“绑定导出结果到任务版本”标记为已完成。

### 修改文件
- `src/trms_backend/domain/exports.py`
- `src/trms_backend/api/exports.py`
- `src/trms_backend/infrastructure/repositories.py`
- `tests/test_exports_api.py`
- `TASKS.md`
- `WORKLOG.md`

### 根因
- 现有导出链路虽然已经有导出任务记录，但记录只保存导出类型、参数和状态，没有绑定“这份导出对应哪一版任务数据”。
- 一旦管理员在导出后继续修改任务字段、发票、分摊或确认状态，系统无法区分旧导出和当前最新数据，旧结果会被误当作最新版本使用。

### 验证结果
- 已通过：
  - `uv run pytest tests/test_exports_api.py`
    - 19 个用例通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - pytest 161 个用例通过
    - `git diff --check` 通过

### 假设
- 当前“导出结果到任务版本”的最小落点仍是导出任务记录，而不是新增真实导出文件实体；仓库现状还没有持久化导出文件模型，本轮不伪装成已经实现文件归档。
- 为避免在仍使用 `create_all` 且未引入迁移工具的阶段直接追加数据库列，本轮把版本元数据保存在导出任务现有 `parameters` 存储中，并通过专门字段对外暴露；这样不引入新的共享库迁移要求。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“确认 Web 前端技术栈和工程边界”，先固化前端目录、命令和测试边界，再进入页面骨架实现。

## 2026-04-28 06:38 - Add merged PDF export placeholder

### 完成内容
- 在 `src/trms_backend/domain/exports.py` 增加合并打印 PDF 占位服务边界：
  - 新增 `MergedPdfExportPlan` 和顺序项模型，显式保留“汇总表、成员明细表、发票明细表、发票、附件”的默认顺序；
  - 对任务内待合并材料执行 PDF 预检查；
  - 当文件加密、损坏、不可读取或不是 PDF 时，抛出包含具体材料编号的明确错误，而不是静默跳过。
- 在 `src/trms_backend/domain/materials.py` 与 `src/trms_backend/infrastructure/storage.py` 为材料存储抽象补充 `read` 能力，允许导出模块按 `storage_key` 回读原始文件。
- 在 `src/trms_backend/api/exports.py` 增加 `GET /api/tasks/{task_id}/exports/merged-pdf`：
  - 仅允许任务管理员访问；
  - 仅允许任务处于 `ready_to_export` 或 `completed` 时调用；
  - 当前返回 JSON 形式的合并计划与校验结果，占位真实 PDF 输出边界。
- 在 `tests/test_exports_api.py` 和 `tests/test_material_storage.py` 增加回归测试，覆盖：
  - 合并计划默认顺序；
  - 加密 PDF 返回具体材料编号；
  - 损坏 PDF 返回具体材料编号；
  - 本地存储可按 `storage_key` 读取文件。
- 将 `TASKS.md` 中“合并打印 PDF 占位”标记为已完成。

### 修改文件
- `pyproject.toml`
- `uv.lock`
- `src/trms_backend/domain/exports.py`
- `src/trms_backend/domain/materials.py`
- `src/trms_backend/infrastructure/storage.py`
- `src/trms_backend/api/exports.py`
- `src/trms_backend/main.py`
- `tests/test_exports_api.py`
- `tests/test_material_storage.py`
- `TASKS.md`
- `WORKLOG.md`

### 根因
- 现有导出模块虽然已经有 `merged_pdf` 导出种类枚举和导出任务状态，但还没有真正可调用的合并打印入口，也没有任何对 PDF 顺序或损坏文件的显式处理。
- 架构文档 5.8 节明确要求 PDF 合并遇到加密、损坏或不可读取文件时必须失败并报告具体材料编号；如果继续只保留枚举占位，管理员无法在导出前发现坏文件，也无法验证默认打印顺序是否被固化。

### 验证结果
- 已通过：
  - `uv run pytest tests/test_material_storage.py tests/test_exports_api.py`
    - 21 个用例通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - pytest 160 个用例通过
    - `git diff --check` 通过

### 假设
- 本轮保守把“合并打印 PDF”实现为“计划与校验占位接口”，而不是直接输出最终 PDF 文件；这样可以先锁定顺序、权限和坏文件显式失败边界，不伪装成已经完成真实 PDF 渲染。
- 当前仅接受 `application/pdf` 材料进入合并计划。图片、压缩包等其他电子件的转 PDF 处理不在本轮范围，后续若需要支持，应单独补文件转换边界。
- 由于报销汇总表、成员明细表和发票明细表当前还没有 PDF 渲染能力，本轮在合并计划中为它们保留顺序占位，但不生成页面内容。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“绑定导出结果到任务版本”，把当前各类导出物和合并计划与任务数据版本绑定，避免管理员修改数据后旧导出被误判为最新。

## 2026-04-28 06:31 - Add finance draft export

### 完成内容
- 在 `src/trms_backend/domain/exports.py` 增加财务填报草稿导出模型与聚合逻辑：
  - 新增 `FinanceDraftExport`、发票行和分摊行结构；
  - 汇总任务的项目、报销人、抬头、税号、总金额、费用类别总额、成员分摊总额和发票明细；
  - 财务草稿只暴露人工录入所需字段，不输出材料存储路径等实现细节。
- 在 `src/trms_backend/api/exports.py` 增加 `GET /api/tasks/{task_id}/exports/finance-draft`：
  - 仅允许任务管理员访问；
  - 仅允许任务处于 `ready_to_export` 或 `completed` 时导出；
  - 当前先实现 `format=json`，以 `application/json` 响应返回财务填报草稿。
- 在 `tests/test_exports_api.py` 增加回归测试，覆盖：
  - 导出能力声明包含 `finance_draft` 的已实现 JSON 格式；
  - 财务草稿可导出项目、报销人、总金额、费用分摊和发票明细；
  - 响应中不暴露 `storage_key` 或本地临时路径；
  - `format=xlsx` 仍显式返回“尚未实现”错误，而不是伪装成功。
- 将 `TASKS.md` 中“生成财务填报草稿”标记为已完成。

### 修改文件
- `src/trms_backend/domain/exports.py`
- `src/trms_backend/api/exports.py`
- `tests/test_exports_api.py`
- `TASKS.md`
- `WORKLOG.md`

### 根因
- 现有导出链路已经补齐汇总表、成员明细表、发票明细表和缺失材料清单，但管理员仍缺少一份可直接用于人工录入财务系统的结构化草稿。
- 需求文档 FR-010 和架构文档 5.8 节都要求系统生成财务填报草稿；如果继续缺失这类导出，管理员仍需从多张导出表手工拼接项目、报销人、总额和逐张发票信息，导出链路就无法闭合到“人工录入前辅助结果”这一阶段目标。

### 验证结果
- 已通过：
  - `uv run pytest tests/test_exports_api.py`
    - 15 个用例通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - pytest 157 个用例通过
    - `git diff --check` 通过

### 假设
- 本轮保守把“财务填报草稿”实现为 JSON 导出，而不是同时引入 XLSX 生成；这样先满足架构文档中“JSON 供后续自动化扩展”的边界，同时避免在本轮增加额外表格生成依赖。
- 财务草稿中的成员总额来自当前有效分摊，任务总金额来自当前发票金额求和；在 `ready_to_export` 状态下，分摊和发票应已由现有门禁保证一致。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“合并打印 PDF 占位”，继续复用导出模块和导出任务边界。

## 2026-04-28 06:21 - Add missing materials export

### 完成内容
- 在 `src/trms_backend/domain/exports.py` 增加缺失材料清单导出模型与 CSV 渲染逻辑：
  - 按成员、费用类型、发票号码导出缺失材料项；
  - 输出所需材料类型、来源规则码和原始提示消息；
  - 将 `missing_materials` 导出能力声明为已实现的 CSV 导出。
- 在 `src/trms_backend/api/exports.py` 增加 `GET /api/tasks/{task_id}/exports/missing-materials`：
  - 仅允许任务管理员访问；
  - 仅允许任务处于 `ready_to_export` 或 `completed` 时导出；
  - 以 `text/csv` 响应返回缺失材料清单。
- 在 `src/trms_backend/domain/missing_materials.py` 扩展缺失材料规则映射：
  - 继续支持支付记录和比赛通知；
  - 新增航空行程单与网约车行程信息缺失项聚合。
- 在 `tests/test_exports_api.py` 和 `tests/test_missing_materials.py` 增加回归测试，覆盖：
  - 导出能力声明包含缺失材料 CSV；
  - 非空清单可导出支付记录、比赛通知、行程信息；
  - 空清单仅输出表头；
  - 缺失材料聚合支持行程信息相关规则。
- 将 `TASKS.md` 中“导出缺失材料清单”标记为已完成。

### 修改文件
- `src/trms_backend/domain/missing_materials.py`
- `src/trms_backend/domain/exports.py`
- `src/trms_backend/api/exports.py`
- `tests/test_missing_materials.py`
- `tests/test_exports_api.py`
- `TASKS.md`
- `WORKLOG.md`

### 根因
- 现有导出链路已经补齐汇总表、成员明细表和发票明细表，但管理员仍无法把“哪些成员缺什么材料”直接导出为可操作清单。
- 需求文档 FR-010 与架构文档 5.8 节都要求系统生成缺失材料清单；如果继续缺少该导出物，管理员仍需手工从校验结果中逐条筛缺口，无法形成可直接催补的名单。

### 验证结果
- 已通过：
  - `uv run pytest tests/test_missing_materials.py`
    - 3 个用例通过
  - `uv run pytest tests/test_exports_api.py`
    - 13 个用例通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - pytest 155 个用例通过
    - `git diff --check` 通过

### 假设
- 当前缺失材料领域模型没有独立的“行程信息”材料类型；本轮保守把航空行程单和网约车行程信息统一映射为 `itinerary` 导出类型，同时保留来源规则码和原始消息，避免在本轮扩展新的材料类型枚举。
- 空清单导出仍返回带表头的 CSV，而不是空文件，便于管理员直接在表格工具中确认“当前无缺失项”。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“生成财务填报草稿”，复用当前导出模块边界继续补齐导出产物。

## 2026-04-28 06:14 - Add invoice detail export

### 完成内容
- 在 `src/trms_backend/domain/exports.py` 增加发票明细导出模型与 CSV 渲染逻辑：
  - 按发票导出发票号码、金额、费用类型、提交人；
  - 聚合当前发票校验结果，输出总校验状态、失败规则码、待确认规则码和异常消息；
  - 将 `invoice_details` 导出能力声明为已实现的 CSV 导出。
- 在 `src/trms_backend/api/exports.py` 增加 `GET /api/tasks/{task_id}/exports/invoice-details`：
  - 仅允许任务管理员访问；
  - 仅允许任务处于 `ready_to_export` 或 `completed` 时导出；
  - 以 `text/csv` 响应返回发票明细表。
- 在 `src/trms_backend/main.py` 为导出路由补充材料仓储和校验仓储依赖注入。
- 在 `tests/test_exports_api.py` 增加回归测试，覆盖：
  - 导出能力声明包含发票明细 CSV；
  - 发票明细可导出提交人和聚合校验状态；
  - 重复发票与缺少比赛通知等异常会在 CSV 中显式暴露。
- 将 `TASKS.md` 中“导出发票明细表”标记为已完成。

### 修改文件
- `src/trms_backend/domain/exports.py`
- `src/trms_backend/api/exports.py`
- `src/trms_backend/main.py`
- `tests/test_exports_api.py`
- `TASKS.md`
- `WORKLOG.md`

### 根因
- 现有导出链路已经补齐汇总表和成员明细表，但管理员仍缺少“逐张发票核对金额、费用类型、提交人和当前异常状态”的基础表。
- 需求文档 FR-010 与任务清单都要求导出发票明细表；如果继续缺少这类导出，管理员无法在导出阶段直接看见重复发票、缺失比赛通知或待确认校验项，也无法对照提交人做最终复核。

### 验证结果
- 已通过：
  - `uv run pytest tests/test_exports_api.py`
    - 11 个用例通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - pytest 152 个用例通过
    - `git diff --check` 通过

### 假设
- 本轮保守把“发票明细表”的校验状态定义为当前发票校验结果的聚合视图，优先级为 `failed > pending > passed > not_applicable`，不额外引入新的导出专用状态机。
- 发票明细中的“提交人”取自主发票材料记录的 `submitter_id`，不尝试把多人分摊成员展开进本表；成员级金额视图仍由“成员报销明细表”承担。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“导出缺失材料清单”，复用现有缺失材料聚合模型和导出模块边界继续补齐导出产物。

## 2026-04-28 06:08 - Add member detail export

### 完成内容
- 在 `src/trms_backend/domain/exports.py` 增加成员报销明细导出模型和 CSV 渲染逻辑：
  - 按成员输出当前有效分摊的费用明细、分摊金额、分摊版本、确认状态和备注；
  - 只读取当前活动分摊和当前确认记录，不导出旧版本分摊历史；
  - 将 `member_details` 导出能力声明为已实现的 CSV 导出。
- 在 `src/trms_backend/api/exports.py` 增加 `GET /api/tasks/{task_id}/exports/member-details`：
  - 仅允许任务管理员访问；
  - 仅允许任务处于 `ready_to_export` 或 `completed` 时导出；
  - 以 `text/csv` 响应返回成员报销明细表。
- 在 `src/trms_backend/main.py` 为导出路由注入确认仓储，用于读取当前有效分摊版本对应的确认状态。
- 在 `tests/test_exports_api.py` 增加回归测试，覆盖：
  - 导出能力声明包含成员明细 CSV；
  - 多人分摊场景可导出成员明细；
  - 分摊替换后仅导出当前有效版本，不混入旧版本金额。
- 将 `TASKS.md` 中“导出成员报销明细表”标记为已完成。

### 修改文件
- `src/trms_backend/domain/exports.py`
- `src/trms_backend/api/exports.py`
- `src/trms_backend/main.py`
- `tests/test_exports_api.py`
- `TASKS.md`
- `WORKLOG.md`

### 根因
- 现有导出链路只有汇总表真实产物，仍缺少管理员核对“每个成员具体报销哪些费用、金额是多少”的明细视图。
- 需求文档 FR-010 和架构文档 5.8 节都要求系统生成成员报销明细表；如果继续只导出汇总表，管理员无法直接核对多人分摊后的成员级明细，也无法验证“当前有效费用版本”这一约束是否被正确落实到导出结果。

### 验证结果
- 已通过：
  - `uv run pytest tests/test_exports_api.py`
    - 10 个用例通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - pytest 151 个用例通过
    - `git diff --check` 通过

### 假设
- 本轮保守把“成员报销明细表”实现为逐条分摊明细 CSV，而不是额外引入 XLSX、多工作表或对象存储落盘；这些增强仍留给后续导出任务处理。
- 当前有效费用版本以活动分摊记录和其对应的当前确认记录为准；旧分摊版本及其历史确认不出现在成员明细导出中。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“导出发票明细表”，继续补齐导出模块的第二类核对产物。

## 2026-04-28 06:01 - Add reimbursement summary export

### 完成内容
- 在 `src/trms_backend/domain/exports.py` 增加报销汇总表导出模型和 CSV 渲染逻辑：
  - 基于任务当前有效分摊，按费用类型聚合总金额；
  - 同时按成员列输出每个费用类型下的分摊金额；
  - 增加 `implemented_formats` 能力声明，明确当前仅实现 `reimbursement_summary` 的 CSV 导出。
- 在 `src/trms_backend/api/exports.py` 增加 `GET /api/tasks/{task_id}/exports/reimbursement-summary`：
  - 仅允许任务管理员访问；
  - 仅允许任务处于 `ready_to_export` 或 `completed` 时导出；
  - 以 `text/csv` 响应返回汇总表，并带导出文件名。
- 在 `src/trms_backend/main.py` 为导出路由注入发票和分摊仓储依赖。
- 在 `tests/test_exports_api.py` 增加回归测试，覆盖：
  - 导出能力声明更新；
  - 汇总 CSV 的费用类型/成员金额聚合正确；
  - 非管理员禁止导出汇总表。
- 将 `TASKS.md` 中“导出报销汇总表”标记为已完成。

### 修改文件
- `src/trms_backend/domain/exports.py`
- `src/trms_backend/api/exports.py`
- `src/trms_backend/main.py`
- `tests/test_exports_api.py`
- `TASKS.md`
- `WORKLOG.md`

### 根因
- 现有导出模块只有能力边界和导出任务占位，仍缺少第一个真实可验证的导出物。
- 需求文档 FR-010、验收项 AC-013 和架构文档 5.8 节都要求系统能输出报销汇总表；如果继续只保留导出任务占位，导出链路就没有任何实际产物，无法验证“按费用类型统计金额”的核心能力。
- 因此本轮先落地最小闭环：直接基于已实现的发票和分摊数据生成 CSV 汇总表，不提前引入对象存储落盘、任务版本绑定或 XLSX 生成。

### 验证结果
- 已通过：
  - `uv run pytest tests/test_exports_api.py`
    - 9 个用例通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - pytest 150 个用例通过
    - `git diff --check` 通过

### 假设
- 本轮保守把“报销汇总表”定义为按任务成员列展开、按费用类型汇总金额的 CSV 矩阵；这是对 AC-013 中“按费用类型和成员统计”的最小实现。
- 当前只实现同步 CSV 响应，不把导出结果持久化到对象存储，也不把导出任务状态自动推进到 `succeeded`；这些能力留给后续“成员明细表”“发票明细表”“绑定导出结果到任务版本”等任务处理。
- 对于任务已配置但当前无金额的费用类别，导出中仍保留零金额行，避免管理员误判该类别被漏统。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“导出成员报销明细表”，直接复用本轮导出模块边界和 CSV 响应模式，继续补齐真实导出物。

## 2026-04-28 05:52 - Add export job model

### 完成内容
- 在 `src/trms_backend/domain/exports.py` 扩展导出领域模型，新增：
  - 导出任务状态 `pending`、`running`、`succeeded`、`failed`；
  - 导出任务创建请求、状态更新和持久化记录模型；
  - 导出格式约束、管理员权限校验、导出前置状态门禁和状态流转校验。
- 在 `src/trms_backend/infrastructure/models.py` 与 `src/trms_backend/infrastructure/repositories.py` 增加 `export_jobs` 表和 SQLAlchemy 仓储，实现导出任务创建、查询、按任务列出和状态更新。
- 在 `src/trms_backend/api/exports.py` 增加：
  - `POST /api/tasks/{task_id}/exports`，用于管理员创建导出任务占位；
  - `GET /api/tasks/{task_id}/exports`，用于管理员查询导出任务；
  - `PATCH /api/tasks/exports/{export_job_id}/status`，用于更新导出任务占位状态。
- 在 `src/trms_backend/main.py` 注入导出任务仓储。
- 在 `tests/test_exports_api.py` 增加回归测试，覆盖：
  - 导出任务创建与列表持久化；
  - `pending`、`running`、`succeeded`、`failed` 状态覆盖；
  - 未进入 `ready_to_export` / `completed` 时禁止创建导出任务；
  - 非管理员禁止创建、查询和更新导出任务。
- 将 `TASKS.md` 中“建立导出任务模型”标记为已完成。

### 修改文件
- `src/trms_backend/domain/exports.py`
- `src/trms_backend/api/exports.py`
- `src/trms_backend/infrastructure/models.py`
- `src/trms_backend/infrastructure/repositories.py`
- `src/trms_backend/main.py`
- `tests/test_exports_api.py`
- `TASKS.md`
- `WORKLOG.md`

### 根因
- 上一轮只建立了“导出能力查询边界”，但需求文档 FR-010 和架构文档 5.8 节都明确要求导出以异步任务形式存在，并记录导出类型、参数、操作者和生成时间。
- 当前仓库虽然已经有导出能力入口，但仍缺少可持久化的导出任务对象：
  - 无法表达导出任务正在排队、执行成功或失败；
  - 后续汇总表、明细表、财务草稿和 PDF 合并都没有统一的任务挂载点；
  - 也无法为后续真实导出执行保留最小审计事实。
- 因此本轮先补“导出任务模型 + API + 持久化”，而不提前实现真实文件生成。

### 验证结果
- 已通过：
  - `uv run pytest tests/test_exports_api.py`
    - 7 个用例通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - pytest 148 个用例通过
    - `git diff --check` 通过

### 假设
- 本轮保守把导出任务状态更新暴露为占位 API，仅记录导出流程状态和失败原因，不提前落地导出文件、对象存储路径或任务版本绑定；这些内容留给后续“导出具体产物”和“绑定导出结果到任务版本”任务处理。
- 当前只允许任务已进入 `ready_to_export` 或 `completed` 时创建导出任务，占位模型与现有导出门禁保持一致，避免在最终确认前静默开启导出链路。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“导出报销汇总表”，直接复用本轮导出任务模型作为挂载点，把第一种具体导出物闭合出来。

## 2026-04-28 05:45 - Add export module boundary skeleton

### 完成内容
- 新增 `src/trms_backend/domain/exports.py`，建立导出模块领域边界，定义：
  - 第一阶段支持的导出物类型与格式枚举；
  - 管理员访问约束；
  - 任务处于 `ready_to_export` 或 `completed` 时才允许真实导出的占位门禁语义。
- 新增 `src/trms_backend/api/exports.py`，提供 `GET /api/tasks/{task_id}/exports/capabilities` 接口，返回导出能力说明、当前任务是否允许导出以及阻塞原因。
- 在 `src/trms_backend/main.py` 挂载导出路由，使导出模块具备独立 API 边界，但本轮不生成真实文件、不创建导出任务。
- 新增 `tests/test_exports_api.py`，覆盖：
  - 管理员可查询导出能力；
  - 未到最终可导出状态时返回明确阻塞原因；
  - 非管理员禁止访问。
- 将 `TASKS.md` 中“建立导出模块边界骨架”标记为已完成。

### 修改文件
- `src/trms_backend/domain/exports.py`
- `src/trms_backend/api/exports.py`
- `src/trms_backend/main.py`
- `tests/test_exports_api.py`
- `TASKS.md`
- `WORKLOG.md`

### 根因
- 需求文档 FR-010 和架构文档 5.8 节都把导出视为独立模块，并明确要求导出入口、输出物类型和异步执行边界。
- 当前仓库虽然已经有 `ready_to_export` / `completed` 任务状态，但完全没有导出模块边界：
  - 没有独立的导出领域对象或接口；
  - 后续“导出任务模型”“汇总表导出”“PDF 合并”没有可复用的挂载点；
  - 导出权限与状态门禁也没有最小可验证表达。
- 因此本轮先补“可调用的导出边界”，而不是直接越级实现持久化任务或真实文件生成。

### 验证结果
- 已通过：
  - `uv run pytest tests/test_exports_api.py`
    - 3 个用例通过
  - `uv run pytest tests/test_tasks_api.py`
    - 38 个用例通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - pytest 144 个用例通过
    - `git diff --check` 通过

### 假设
- 本轮保守把导出能力边界设计为“能力查询接口”，只暴露支持的导出物、格式和当前任务门禁，不提前创建任何导出任务记录，避免与下一项“建立导出任务模型”重叠。
- 当前将“允许真实导出”的最小前置条件定义为任务状态已经进入 `ready_to_export` 或 `completed`；更细粒度的版本绑定、任务幂等和对象存储落盘留待后续任务实现。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“建立导出任务模型”，在现有导出模块边界上增加 `pending`、`running`、`succeeded`、`failed` 的持久化任务骨架。

## 2026-04-28 05:47 - Add automatic reminder task placeholders

### 完成内容
- 新增 `src/trms_backend/domain/automatic_reminders.py`，建立系统自动提醒任务占位模型、管理员权限校验、缺失材料与未确认费用聚合逻辑，以及基于去重键的幂等生成规则。
- 在 `src/trms_backend/api/tasks.py` 增加：
  - `POST /api/tasks/{task_id}/automatic-reminder-tasks`，用于生成当前任务的自动提醒任务占位；
  - `GET /api/tasks/{task_id}/automatic-reminder-tasks`，用于管理员查询已生成的自动提醒任务占位。
- 在 `src/trms_backend/infrastructure/models.py` 与 `src/trms_backend/infrastructure/repositories.py` 增加自动提醒任务表和 SQLAlchemy 仓储实现，持久化提醒类型、摘要、载荷、去重键和请求人。
- 新增 `tests/test_automatic_reminder_tasks_api.py`，覆盖：
  - 缺失材料与未确认费用两类提醒占位生成；
  - 重复生成同一快照时的幂等复用；
  - 非管理员禁止生成和查询。
- 将 `TASKS.md` 中“建立系统自动提醒占位”标记为已完成。

### 修改文件
- `src/trms_backend/api/tasks.py`
- `src/trms_backend/domain/automatic_reminders.py`
- `src/trms_backend/infrastructure/models.py`
- `src/trms_backend/infrastructure/repositories.py`
- `src/trms_backend/main.py`
- `tests/test_automatic_reminder_tasks_api.py`
- `TASKS.md`
- `WORKLOG.md`

### 根因
- 需求文档 FR-009 要求“管理员可查看自动提醒记录”，任务清单也要求系统能基于缺失材料和未确认状态生成提醒占位。
- 当前仓库只有管理员手动提醒记录，没有任何系统自动提醒任务骨架：
  - 缺失材料和未确认状态虽然已经能分别聚合或识别，但没有统一入口把它们转成可查询、可追踪的提醒任务；
  - 后续若接入邮件、Telegram 或定时任务，也缺少幂等的本地任务占位可供复用。
- 因此管理员复核链路里“系统自动提醒”仍停留在文档要求，没有最小可验证实现。

### 验证结果
- 已通过：
  - `uv run pytest tests/test_automatic_reminder_tasks_api.py`
    - 3 个用例通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - pytest 141 个用例通过
    - `git diff --check` 通过

### 假设
- 本轮保守把“未确认状态”定义为当前有效费用分摊上所有非 `confirmed` 状态，而不是只在截止后才生成提醒；由于本轮只生成占位、不发送外部通知，这样能先把提醒任务骨架和幂等边界落库。
- 自动提醒任务目前仅保留 `pending` 占位状态，不提前设计真实发送、重试和失败流转，避免在未接入通知渠道前过度扩展。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“建立导出模块边界骨架”，先把导出服务与任务边界建立出来，再分别补导出任务模型和具体导出物。

## 2026-04-28 05:29 - Record administrator material reminders

### 完成内容
- 新增 `src/trms_backend/domain/material_reminders.py`，建立管理员手动补材料提醒记录的领域模型、管理员权限校验和任务成员约束。
- 在 `src/trms_backend/api/tasks.py` 增加：
  - `POST /api/tasks/{task_id}/material-reminders`，用于管理员记录提醒；
  - `GET /api/tasks/{task_id}/material-reminders`，用于查询该任务下的提醒记录。
- 在 `src/trms_backend/infrastructure/models.py` 与 `src/trms_backend/infrastructure/repositories.py` 增加提醒记录表和 SQLAlchemy 仓储实现。
- 在 `tests/test_tasks_api.py` 新增回归测试，覆盖管理员创建与查询、非管理员拒绝、目标成员不属于任务拒绝。
- 将 `TASKS.md` 中“支持管理员补材料提醒记录”标记为已完成。

### 修改文件
- `src/trms_backend/api/tasks.py`
- `src/trms_backend/domain/material_reminders.py`
- `src/trms_backend/infrastructure/models.py`
- `src/trms_backend/infrastructure/repositories.py`
- `src/trms_backend/main.py`
- `tests/test_tasks_api.py`
- `TASKS.md`
- `WORKLOG.md`

### 根因
- 需求文档 FR-009 和架构文档的管理员复核模块都要求“管理员可手动提醒成员补材料”，但当前仓库只有缺失材料、逾期确认和复核汇总等只读能力，没有任何提醒记录入口：
  - 管理员无法把“已提醒谁、提醒了什么、何时提醒”的事实落库；
  - 后续自动提醒任务也缺少可并列的人工提醒基线；
  - 因此复核链路里“提醒补材料”仍停留在文档要求，没有最小可验证实现。

### 验证结果
- 已通过：
  - `uv run pytest tests/test_tasks_api.py`
    - 38 个用例通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - pytest 138 个用例通过
    - `git diff --check` 通过

### 假设
- 本轮保守把“提醒可查询”限定为任务管理员可查询手动提醒记录；成员侧查看提醒和系统自动提醒仍留给后续任务，不在本轮提前扩展接口权限或通知渠道。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“建立系统自动提醒占位”，在不接入真实通知渠道的前提下，把缺失材料和未确认状态转成幂等的提醒任务骨架。

## 2026-04-28 05:31 - Close final-confirmation gate for unconfirmed members

### 完成内容
- 在 `tests/test_tasks_api.py` 新增回归测试，显式覆盖“成员确认处于 `disputed` 时，任务不能从 `reviewing` 进入 `ready_to_export`”。
- 将 `TASKS.md` 中“阻止存在未确认成员的最终确认”标记为已完成。

### 修改文件
- `tests/test_tasks_api.py`
- `TASKS.md`
- `WORKLOG.md`

### 根因
- 当前仓库的 `ready_to_export` 门禁代码实际上已经拒绝三类成员确认缺口：
  - 缺失确认；
  - 金额变更后回退到 `pending`；
  - 成员提出异议后的 `disputed`。
- 但现有回归测试只显式覆盖了缺失确认和回退到 `pending` 的路径，没有直接锁定 `disputed` 分支。
- 结果是：任务清单要求的“异议状态不能被静默当作确认”虽然在实现上已成立，但缺少可回归证明，任务无法严谨结项。

### 验证结果
- 已通过：
  - `uv run pytest tests/test_tasks_api.py`
    - 34 个用例通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - pytest 134 个用例通过
    - `git diff --check` 通过

### 假设
- 本轮保守认定“未确认成员”任务的最小闭环是把现有服务端门禁语义用测试锁定，而不是在尚未引入成员级费用明细版本模型前继续重写确认数据结构。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“支持管理员补材料提醒记录”，不要把提醒能力和真实外部通知发送耦合在同一轮。

## 2026-04-28 05:19 - Block ready-to-export when pending-assignment materials exist

### 完成内容
- 在 `src/trms_backend/domain/materials.py` 和 `src/trms_backend/infrastructure/repositories.py` 增加“按 `task_id_hint` 查询待归属材料”的只读仓储能力。
- 在 `src/trms_backend/api/tasks.py` 把待归属材料检查接入 `ready_to_export` 门禁；当任务仍有待归属材料时，拒绝进入可导出状态。
- 在 `src/trms_backend/domain/tasks.py` 扩展最终确认校验，错误信息显式返回待处理材料数量和材料编号。
- 在 `tests/test_tasks_api.py` 新增回归测试，覆盖“存在待归属材料时不能最终确认”路径。
- 将 `TASKS.md` 中“阻止存在待归属材料的最终确认”标记为已完成。

### 修改文件
- `src/trms_backend/api/tasks.py`
- `src/trms_backend/domain/materials.py`
- `src/trms_backend/domain/tasks.py`
- `src/trms_backend/infrastructure/repositories.py`
- `tests/test_tasks_api.py`
- `TASKS.md`
- `WORKLOG.md`

### 根因
- 仓库此前已经实现了 `pending_assignment` 材料状态和管理员认领流程，但管理员把任务从 `reviewing` 置为 `ready_to_export` 时，门禁只检查发票校验、分摊和成员确认：
  - 待归属材料虽然被正确隐藏在普通任务材料列表之外，却不会阻止最终确认；
  - 这与需求文档和架构文档中“最终确认前不得存在待归属材料”的约束不一致；
  - 因此会出现“仍有未处理渠道材料，但任务已被视为可导出”的状态漏洞。

### 验证结果
- 已通过：
  - `uv run pytest tests/test_tasks_api.py`
    - 33 个用例通过
  - `uv run pytest tests/test_materials_api.py`
    - 22 个用例通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - pytest 133 个用例通过
    - `git diff --check` 通过

### 假设
- 当前只把 `task_id_hint == task.id` 的待归属材料视为“该任务存在待处理材料”的确定证据；没有任务提示的待归属材料本轮不阻断任何具体任务的最终确认，因为系统尚无更可靠的任务归属推断链路。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“阻止存在未确认成员的最终确认”，继续把管理员最终确认门禁从“分摊级确认缺失”收敛为更明确的任务级成员确认约束。

## 2026-04-28 05:14 - Add administrator review summary API

### 完成内容
- 新增 `GET /api/tasks/{task_id}/review-summary` 管理员复核汇总接口，聚合返回：
  - 任务内材料及其最新识别状态；
  - 材料对应发票或被哪些发票作为辅助材料引用；
  - 发票校验结果；
  - 发票分摊及当前确认状态。
- 新增 `src/trms_backend/domain/task_review_summary.py`，把复核汇总的只读聚合、管理员权限校验和统计计数收敛为独立领域模型。
- 调整 `src/trms_backend/api/tasks.py` 和 `src/trms_backend/main.py`，为任务路由注入材料仓储和识别仓储，接入复核汇总接口。
- 新增 `tests/test_task_review_summary_api.py`，覆盖管理员成功查询和普通成员禁止访问两条最小回归路径。
- 将 `TASKS.md` 中“建立复核汇总查询接口”标记为已完成。

### 修改文件
- `src/trms_backend/api/tasks.py`
- `src/trms_backend/domain/task_review_summary.py`
- `src/trms_backend/main.py`
- `tests/test_task_review_summary_api.py`
- `TASKS.md`
- `WORKLOG.md`

### 根因
- 现有仓库已经分别具备材料列表、识别任务、发票校验、费用分摊、费用明细和异议查询能力，但这些数据仍分散在多个接口和仓储调用里：
  - 管理员无法通过单一入口查看某个任务在复核阶段的整体状态；
  - 现有 `expense-details`、`expense-disputes`、`overdue-confirmations` 只能覆盖复核面的一部分；
  - `TASKS.md` 要求的“复核汇总查询接口”因此尚未闭合，即使底层数据已基本齐备。

### 验证结果
- 已通过：
  - `uv run pytest tests/test_task_review_summary_api.py`
    - 2 个用例通过
  - `uv run pytest tests/test_tasks_api.py tests/test_expense_details_api.py tests/test_expense_disputes_api.py tests/test_overdue_confirmations_api.py`
    - 42 个用例通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - pytest 132 个用例通过
    - `git diff --check` 通过

### 假设
- 本轮保守将“复核汇总”定义为管理员复核阶段所需的只读聚合视图，不在该接口中继续叠加待归属材料阻断、未确认成员阻断、补材料提醒等后续任务逻辑。
- 材料识别状态使用“该材料最新一次识别任务”的结果，而不是“最新有效识别结果”，因为复核界面需要优先暴露当前最新识别尝试是否失败、待确认或仍在处理中。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“阻止存在待归属材料的最终确认”，把复核入口的只读汇总继续收敛为最终确认门禁。

## 2026-04-28 05:07 - Close administrator review state flow task

### 完成内容
- 在 `tests/test_tasks_api.py` 补充两条管理员复核状态流转回归测试：
  - 显式覆盖任务从 `closed` 进入 `reviewing`；
  - 显式覆盖仅剩 warning 级校验时，任务仍可从 `reviewing` 进入 `ready_to_export`，验证“只有 Must/blocker 问题阻止最终确认”的门禁语义。
- 将 `TASKS.md` 中“建立管理员复核状态流转”标记为已完成。

### 修改文件
- `tests/test_tasks_api.py`
- `TASKS.md`
- `WORKLOG.md`

### 根因
- 该任务对应的核心业务能力实际上已在仓库中存在：
  - `src/trms_backend/domain/tasks.py` 已定义 `closed -> reviewing -> ready_to_export` 状态流转；
  - `src/trms_backend/api/tasks.py` 已在进入 `ready_to_export` 前执行 Must/blocker 校验和成员确认门禁；
  - `tests/test_tasks_api.py` 已覆盖 blocker 校验失败、确认缺失、确认失效和禁止直接完成等关键失败路径。
- 但任务清单仍未结项，主要缺口是“主要状态流转”的直接回归覆盖不够直观，导致当前事实没有被 `TASKS.md` 明确收口。

### 验证结果
- 已通过：
  - `uv run pytest tests/test_tasks_api.py`
    - 32 个用例通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - pytest 130 个用例通过
    - `git diff --check` 通过

### 假设
- 本轮保守认定“建立管理员复核状态流转”只要求收敛任务状态机和最终确认门禁，不包含管理员复核汇总视图、待归属材料阻断、补材料提醒等后续独立任务；这些仍按 `TASKS.md` 后续顺序推进。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“建立复核汇总查询接口”，把当前已有的材料、识别、校验、分摊和确认数据聚合为管理员复核视图。

## 2026-04-28 05:02 - Forbid proxy split confirmations by default

### 完成内容
- 在 `src/trms_backend/domain/confirmations.py` 为确认提交模型补充 `actor_id`，让“谁发起确认”成为显式输入，而不是继续隐含假设为成员本人。
- 在 `src/trms_backend/api/confirmations.py` 增加默认代理确认拦截：
  - `actor_id != member_id` 时直接返回 `403`，明确拒绝任何代成员确认路径；
  - 仍保留“成员只能确认自己所属 split”的既有约束，避免通过伪造 `member_id` 越权确认他人费用。
- 在 `src/trms_backend/api/tasks.py` 补齐管理员处理异议后重置为 `pending` 的内部确认构造，确保新增 `actor_id` 约束不会破坏现有异议处理链路。
- 扩展 `tests/test_confirmations_api.py`，新增“管理员默认不能代成员确认”的回归测试，并同步更新确认相关测试请求体。
- 将 `TASKS.md` 中“禁止管理员代确认默认路径”标记为已完成。

### 修改文件
- `src/trms_backend/api/confirmations.py`
- `src/trms_backend/api/tasks.py`
- `src/trms_backend/domain/confirmations.py`
- `tests/test_confirmations_api.py`
- `tests/test_expense_details_api.py`
- `tests/test_expense_disputes_api.py`
- `tests/test_overdue_confirmations_api.py`
- `tests/test_splits_api.py`
- `tests/test_tasks_api.py`
- `TASKS.md`
- `WORKLOG.md`

### 根因
- 现有确认接口只接收 `member_id`，没有任何操作者上下文，服务端无法区分“成员本人确认”与“管理员或其他人代确认”：
  - 只要请求体填入正确的 `member_id`，接口就会把调用者视为该成员本人；
  - “禁止管理员代确认”因此只是一条隐含假设，而不是可验证的服务端约束；
  - 一旦后续接入真实 Web/CLI 身份上下文，这个缺口会直接变成越权确认风险。

### 验证结果
- 已通过：
  - `uv run pytest tests/test_confirmations_api.py tests/test_splits_api.py tests/test_expense_disputes_api.py tests/test_overdue_confirmations_api.py tests/test_tasks_api.py tests/test_expense_details_api.py`
    - 57 个用例通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - pytest 128 个用例通过
    - `git diff --check` 通过

### 假设
- 第一阶段当前不保留“管理员代成员确认”的业务入口占位；在尚无审计日志与代确认原因记录能力前，默认直接禁止比保留半成品兼容层更安全，也更符合任务边界。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“建立管理员复核状态流转”，把现有确认、异议、校验和任务状态门禁收敛为显式复核闭环。

## 2026-04-28 04:57 - Identify overdue member confirmations

### 完成内容
- 新增 `src/trms_backend/domain/overdue_confirmations.py`，把“任务截止后仍未完成当前版本费用确认”的识别逻辑收敛为独立只读聚合：
  - 仅允许任务管理员查询；
  - 基于任务当前有效分摊和当前版本确认记录判断逾期；
  - 对缺失确认、显式 `pending` 和 `disputed` 三类未确认状态分别暴露，不再把它们混同为“已确认”或静默忽略。
- 在 `src/trms_backend/api/tasks.py` 新增 `GET /api/tasks/{task_id}/overdue-confirmations`，返回逾期确认清单、逾期成员列表和确认截止时间。
- 新增 `tests/test_overdue_confirmations_api.py`，覆盖：
  - 截止后管理员可查询逾期未确认成员；
  - 截止前查询返回空清单；
  - 非管理员查询返回 `403`。
- 将 `TASKS.md` 中“支持成员逾期未确认识别”标记为已完成。

### 修改文件
- `src/trms_backend/api/tasks.py`
- `src/trms_backend/domain/overdue_confirmations.py`
- `tests/test_overdue_confirmations_api.py`
- `TASKS.md`
- `WORKLOG.md`

### 根因
- 现有仓库虽然已经有“当前有效确认”和“历史确认”的版本边界，但仍缺少一个任务级聚合入口去显式回答“截止后还有哪些成员没确认当前费用明细”：
  - 管理员无法直接区分哪些成员是缺失确认、哪些成员是确认失效后回到 `pending`；
  - 未确认状态只能隐含在复核门禁错误里，不能被主动查询；
  - 这会让后续复核提醒和自动提醒任务缺少明确的数据入口。

### 验证结果
- 已通过：
  - `uv run pytest tests/test_overdue_confirmations_api.py`
    - 3 个用例通过
  - `uv run pytest tests/test_tasks_api.py tests/test_expense_details_api.py tests/test_confirmations_api.py tests/test_splits_api.py`
    - 50 个用例通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - pytest 127 个用例通过
    - `git diff --check` 通过

### 假设
- 当前仓库尚无独立“确认截止时间”配置，本轮保守使用 `task.deadline` 作为逾期判断边界；若后续新增确认截止规则，应优先替换该聚合中的截止来源，而不是在调用方拼接特判。
- 本轮把 `disputed` 也视为“尚未完成最终确认”的逾期状态之一，因为它在管理员复核前同样不能进入可导出状态。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“禁止管理员代确认默认路径”，把当前“只有成员本人可提交确认”的边界补齐为显式的管理员默认禁止语义和回归测试。

## 2026-04-28 04:51 - Introduce expense detail version tracking

### 完成内容
- 在 `src/trms_backend/infrastructure/models.py` 为 `expense_splits` 增加 `version`、`is_active` 字段，为 `confirmations` 增加 `split_version` 和费用快照字段，使确认记录不再只依赖“当前一条 split”。
- 在 `src/trms_backend/infrastructure/repositories.py` 调整分摊替换语义：
  - 同一成员金额或备注变化时递增当前分摊版本；
  - 若旧版本已有确认，则为新版本创建显式 `pending` 确认；
  - 被移除的旧分摊不再物理删除，而是归档为非活跃记录，保留历史确认可追溯性。
- 在 `src/trms_backend/domain/confirmations.py`、`src/trms_backend/domain/splits.py`、`src/trms_backend/domain/expense_details.py` 扩展领域模型，显式暴露分摊版本、当前有效标记和确认快照版本。
- 在 `src/trms_backend/api/tasks.py` 把费用明细、异议处理和任务复核门禁统一改为只消费“当前有效确认”；同时保留 `GET /api/invoices/{invoice_id}/confirmations` 返回历史确认，并通过 `is_current` 区分当前与历史。
- 扩展 `tests/test_splits_api.py`、`tests/test_confirmations_api.py`、`tests/test_expense_details_api.py`，覆盖：
  - 分摊变更后版本号递增；
  - 当前确认与历史确认可区分；
  - 费用明细查询返回当前版本及其确认版本。
- 将 `TASKS.md` 中“引入费用明细版本号”标记为已完成。

### 修改文件
- `src/trms_backend/api/confirmations.py`
- `src/trms_backend/api/tasks.py`
- `src/trms_backend/domain/confirmations.py`
- `src/trms_backend/domain/expense_details.py`
- `src/trms_backend/domain/splits.py`
- `src/trms_backend/infrastructure/models.py`
- `src/trms_backend/infrastructure/repositories.py`
- `tests/test_confirmations_api.py`
- `tests/test_expense_details_api.py`
- `tests/test_splits_api.py`
- `TASKS.md`
- `WORKLOG.md`

### 根因
- 现有实现把成员确认直接绑在 `split_id` 上，且分摊变化时要么原地覆盖确认状态，要么直接删除旧分摊和确认：
  - 无法表达“同一费用明细已经进入第几个版本”；
  - 旧确认一旦被覆盖或删除，就不能区分“当前有效确认”和“历史确认”；
  - 这与需求中“成员确认绑定到具体费用明细版本”的约束不一致，也会让后续逾期未确认识别、复核审计等任务缺少可靠基础。

### 验证结果
- 已通过：
  - `uv run pytest tests/test_splits_api.py tests/test_confirmations_api.py tests/test_expense_details_api.py tests/test_expense_disputes_api.py tests/test_tasks_api.py`
    - 53 个用例通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - pytest 124 个用例通过
    - `git diff --check` 通过

### 假设
- 本轮保守把“费用明细版本”收敛为“当前活跃分摊记录上的递增版本号 + 确认记录内保存的版本快照”，不额外引入独立版本表。
- 对于被移除的分摊，本轮采用“归档旧 split，不再对外暴露为当前明细”的方式保留历史；当前业务接口仍只返回活跃分摊。
- 分摊版本变更后，仅当旧版本已存在确认记录时，才自动为新版本创建显式 `pending`；新增成员分摊仍保持“当前缺少确认”的语义。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“支持成员逾期未确认识别”，直接基于当前版本确认集合统计任务内未确认成员，避免再依赖历史确认推断。

## 2026-04-28 04:42 - Invalidate changed split confirmations explicitly

### 完成内容
- 在 `src/trms_backend/infrastructure/repositories.py` 将发票分摊替换从“整张发票全删全建”改为“按成员差量替换”：
  - 未变化的分摊保留原 `split_id`；
  - 同一成员的金额或备注发生变化时，保留原分摊记录，但把已有确认显式重置为 `pending`；
  - 被移除的旧分摊会同步清理其确认记录，避免旧确认残留为孤儿数据。
- 在 `tests/test_splits_api.py` 补充两条回归测试，覆盖：
  - 金额调整后，已确认成员会被重置为 `pending`；
  - 未变化的成员分摊继续保留原确认，不会被无关失效。
- 在 `tests/test_tasks_api.py` 补充任务状态回归测试，覆盖“成员已确认后，管理员重新调整分摊金额，任务进入复核时会因 `pending` 确认而被阻止进入 `ready_to_export`”。
- 将 `TASKS.md` 中“实现费用分摊确认失效规则”标记为已完成。

### 修改文件
- `src/trms_backend/infrastructure/repositories.py`
- `tests/test_splits_api.py`
- `tests/test_tasks_api.py`
- `TASKS.md`
- `WORKLOG.md`

### 根因
- 现有分摊替换实现直接删除整张发票的全部 `expense_splits` 后重建，成员确认是否“失效”完全依赖旧 `split_id` 被替换掉这一副作用：
  - 无法区分“哪些成员的明细真的变了”；
  - 对于被修改过的成员，也只会表现为“确认记录消失”，而不是显式进入 `pending`；
  - 这和架构文档要求的“金额变更后相关确认失效并重新确认”不一致，也会让后续复核门禁只能看到缺失确认，无法区分“从未确认”和“确认已失效”。

### 验证结果
- 已通过：
  - `uv run pytest tests/test_splits_api.py tests/test_tasks_api.py tests/test_confirmations_api.py tests/test_expense_details_api.py`
    - 50 个用例通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - pytest 124 个用例通过
    - `git diff --check` 通过

### 假设
- 本轮保守把“确认失效”收敛为：只有此前已经存在确认记录、且当前分摊明细确实发生变化的成员，才会被显式重置为 `pending`；新增分摊仍保持“尚未确认”的现状，不提前为其自动创建确认记录。
- 在“引入费用明细版本号”任务完成前，仍以当前 `split_id` 作为确认绑定对象；本轮只修正失效语义，不提前引入版本表或历史版本查询。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“引入费用明细版本号”，把当前基于 `split_id` 的确认失效进一步提升为真正的“费用明细版本确认”模型。

## 2026-04-28 04:35 - Support expense dispute review workflow

### 完成内容
- 在 `src/trms_backend/domain/confirmations.py` 为确认记录补上显式 `pending` 状态，并拆分成员提交模型，禁止成员直接把自己的费用明细提交为 `pending`。
- 在 `src/trms_backend/domain/expense_disputes.py` 新增任务级异议聚合模型，明确“异议列表只对任务管理员开放”的查询边界。
- 在 `src/trms_backend/api/tasks.py` 新增两条管理员接口：
  - `GET /api/tasks/{task_id}/expense-disputes`：按任务聚合当前仍处于 `disputed` 的费用明细；
  - `POST /api/tasks/{task_id}/expense-disputes/{split_id}/resolve`：管理员处理异议后，将该确认状态重置为显式 `pending`，要求成员重新确认。
- 在 `src/trms_backend/domain/tasks.py` 更新复核门禁：`pending` 确认和缺失确认一样都会阻止任务进入 `ready_to_export`，避免管理员处理异议后被误当作已完成确认。
- 补充 `tests/test_expense_disputes_api.py`，并扩展 `tests/test_confirmations_api.py`，覆盖以下关键路径：
  - 成员仍可提交 `disputed`，但不能伪造 `pending`；
  - 管理员可查看任务内异议清单；
  - 管理员处理异议后，该明细回到 `pending`，并继续阻止任务进入 `ready_to_export`。
- 将 `TASKS.md` 中“支持成员费用异议处理状态”标记为已完成。

### 修改文件
- `src/trms_backend/api/confirmations.py`
- `src/trms_backend/api/tasks.py`
- `src/trms_backend/domain/confirmations.py`
- `src/trms_backend/domain/expense_disputes.py`
- `src/trms_backend/domain/tasks.py`
- `src/trms_backend/infrastructure/repositories.py`
- `tests/test_confirmations_api.py`
- `tests/test_expense_disputes_api.py`
- `TASKS.md`
- `WORKLOG.md`

### 根因
- 现有实现虽然已经支持成员把单条分摊标记为 `disputed`，但确认状态模型只有 `confirmed` 和 `disputed`，把“待确认”隐含为“根本没有确认记录”。这会导致管理员处理异议后没有可持久化的“重新等待成员确认”状态边界，也无法区分“从未确认”与“异议已处理、等待重确认”。
- 同时，仓库缺少一个按任务聚合当前异议明细的管理员入口，管理员只能间接查看全部费用明细，无法围绕“异议处理”形成最小闭环。

### 验证结果
- 已通过：
  - `uv run pytest tests/test_confirmations_api.py tests/test_expense_disputes_api.py tests/test_expense_details_api.py tests/test_tasks_api.py`
    - 42 个用例通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - pytest 121 个用例通过
    - `git diff --check` 通过

### 假设
- 本轮保守把“管理员处理异议”定义为“把当前确认记录重置为显式 `pending`，并保留原异议说明供后续重新确认时参考”，不提前引入独立的异议工单、处理备注或历史状态流。
- 当前异议查询入口只开放给任务管理员，不扩展到系统管理员或全局审计视图；更高层的审计与提醒能力留给后续任务处理。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“实现费用分摊确认失效规则”，把管理员改金额或替换分摊后的确认失效逻辑统一收敛到现在新增的显式 `pending` 状态上。

## 2026-04-28 04:28 - Add task expense detail query API

### 完成内容
- 新增领域模块 `src/trms_backend/domain/expense_details.py`，把当前“个人费用明细”收敛为“任务内现有分摊记录 + 关联发票快照 + 当前确认状态”的只读聚合模型。
- 在 `src/trms_backend/api/tasks.py` 新增 `GET /api/tasks/{task_id}/expense-details`，以显式 `actor_id` 作为当前最小身份上下文：
  - 任务管理员可查询任务内全部费用明细；
  - 普通成员仅返回自己相关的费用明细；
  - 非任务成员直接返回 `403`。
- 补充 `tests/test_expense_details_api.py`，覆盖四条关键路径：
  - 成员只能看到自己的费用明细；
  - 无相关分摊的任务成员返回空列表，而不是看到他人数据；
  - 管理员可查看任务内全部分摊明细；
  - 非任务成员访问返回 `403`。
- 将 `TASKS.md` 中“建立个人费用明细查询接口”标记为已完成。

### 修改文件
- `src/trms_backend/domain/expense_details.py`
- `src/trms_backend/api/tasks.py`
- `tests/test_expense_details_api.py`
- `TASKS.md`
- `WORKLOG.md`

### 根因
- 现有仓库虽然已经有按发票查询分摊和确认记录的接口，但缺少一个以“任务 + 当前查看者”为边界的聚合查询入口，导致成员无法直接查看自己待确认的个人费用明细，管理员也无法按任务一次性看到全部费用归属，而权限隔离只能依赖调用方自行拼装，和需求文档、架构文档要求的“成员只能查看本人相关费用明细”不一致。

### 验证结果
- 已通过：
  - `uv run pytest tests/test_expense_details_api.py`
    - 4 个用例通过
  - `uv run pytest tests/test_tasks_api.py tests/test_splits_api.py tests/test_confirmations_api.py`
    - 42 个用例通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - pytest 117 个用例通过
    - `git diff --check` 通过

### 假设
- 在“引入费用明细版本号”任务完成前，本轮保守把“个人费用明细”定义为当前有效的 `expense_splits` 记录及其关联发票快照，不提前发明新的持久化版本表。
- 对于属于任务成员但当前没有任何分摊记录的成员，查询结果返回空列表和 `0` 金额；后续如需区分“暂未生成明细”和“已全部确认”，应在版本化或确认状态聚合任务中单独补齐。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“支持成员费用异议处理状态”，把当前单条分摊上的 `disputed` 记录进一步提升为管理员可查询、可处理的任务级异议视图。

## 2026-04-28 04:21 - Restrict expense split submission actors

### 完成内容
- 为分摊替换请求新增 `actor_id`，把“谁在提交分摊”显式纳入 API 输入，而不是继续允许任何知道发票 ID 的调用方直接改写分摊。
- 在 `src/trms_backend/domain/splits.py` 新增最小权限判断：仅允许任务管理员、发票主材料提交人，以及当前或目标分摊中的归属成员提交分摊变更。
- 在 `src/trms_backend/api/splits.py` 接入上述权限校验，并通过发票主材料 `submitter_id`、任务 `administrator_id` 和现有/目标分摊成员集合共同判断是否越权。
- 补充分摊 API 回归测试，覆盖三条关键路径：
  - 归属成员可直接提交分摊；
  - 任务管理员可提交分摊；
  - 无关成员提交分摊返回 `403`。
- 将 `TASKS.md` 中“完善费用分摊提交权限”标记为已完成。

### 修改文件
- `src/trms_backend/domain/splits.py`
- `src/trms_backend/api/splits.py`
- `src/trms_backend/main.py`
- `tests/test_splits_api.py`
- `tests/test_confirmations_api.py`
- `tests/test_tasks_api.py`
- `TASKS.md`
- `WORKLOG.md`

### 根因
- 现有 `PUT /api/invoices/{invoice_id}/splits` 只校验“分摊成员属于任务成员”和“金额合计等于发票金额”，完全没有操作者权限边界，导致任何知道发票 ID 的成员甚至任务外调用方都能直接替换无关发票分摊，和需求文档、架构文档里的成员隔离原则不一致。

### 验证结果
- 已通过：
  - `uv run pytest tests/test_splits_api.py`
    - 8 个用例通过
  - `uv run pytest tests/test_confirmations_api.py`
    - 5 个用例通过
  - `uv run pytest tests/test_tasks_api.py`
    - 29 个用例通过

### 假设
- 在“建立最小请求身份上下文占位”任务完成前，本轮保守采用显式 `actor_id` 作为最小身份输入，不提前扩散为统一鉴权中间件。
- “归属成员可提交分摊”当前收敛为：操作者只要属于现有分摊成员或本次目标分摊成员集合之一，即可提交变更；若后续业务要求更细的“仅本人份额可改”或“多人共同确认后才能改”，应在后续权限任务中单独细化。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“建立个人费用明细查询接口”，继续补齐成员只能查看本人费用、管理员可查看任务内全量费用的查询边界。

## 2026-04-28 04:17 - Revalidate invoices after material recognition updates

### 完成内容
- 新增 `src/trms_backend/api/invoice_validation_refresh.py`，抽出统一的发票校验刷新逻辑，按当前主材料识别结果、辅助材料关联和最新有效识别结果重新生成整张发票的校验集合。
- 为发票仓储补充“按主材料查询发票”和“按辅助材料反查关联发票”能力，使识别任务更新后可以定位受影响的发票，而不依赖手工重新挂载附件。
- 将识别任务状态更新接口接入上述刷新链路：无论补充的是主发票材料还是已关联辅助材料，只要新的识别结果生效，就会立即重算相关发票校验，避免继续沿用旧的失败或待确认结果。
- 保持“创建发票时按识别前快照给出待确认/失败语义”的现有行为不变，避免把人工录入字段误当成 AI 已识别字段，造成原有抬头、税号待确认语义回归。
- 补充发票 API 回归测试，覆盖两条关键路径：
  - 支付记录首次识别金额错误导致金额匹配失败，重试识别后自动转为通过；
  - 主发票材料地点识别首次不匹配导致 warning 失败，重试识别后自动转为通过。
- 将 `TASKS.md` 中“支持材料补充后重新校验”标记为已完成。

### 修改文件
- `src/trms_backend/api/invoice_validation_refresh.py`
- `src/trms_backend/api/invoices.py`
- `src/trms_backend/api/recognitions.py`
- `src/trms_backend/domain/invoices.py`
- `src/trms_backend/infrastructure/repositories.py`
- `src/trms_backend/main.py`
- `tests/test_invoices_api.py`
- `TASKS.md`
- `WORKLOG.md`

### 根因
- 现有代码只会在“创建发票”和“挂载/解绑辅助材料”两个动作时刷新校验结果；一旦材料已经关联，后续识别任务重试或补充出新的结构化字段，相关发票不会被重新计算，旧的失败/待确认结果会继续残留，和材料当前事实脱节。

### 验证结果
- 已通过：
  - `uv run pytest tests/test_invoices_api.py`
    - 36 个用例通过
  - `uv run pytest tests/test_recognition_tasks_api.py`
    - 7 个用例通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - pytest 110 个用例通过
    - `git diff --check` 通过

### 假设
- 本轮保守把“材料补充后重新校验”收敛为“识别任务状态更新后，自动刷新所有直接依赖该材料的发票校验”；其中包括主发票材料本身，以及通过辅助材料关联表反查到的发票。
- 当前仍只刷新与该材料直接关联的发票，不扩散为任务级批量重算或后台调度任务；若后续需要跨发票、跨任务的批量重建，应作为独立任务处理。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“完善费用分摊提交权限”，继续补齐分摊与成员确认阶段的权限边界。

## 2026-04-28 04:07 - Add missing material aggregation model

### 完成内容
- 新增领域模块 `src/trms_backend/domain/missing_materials.py`，把现有发票校验结果中的“明确缺少附件”规则聚合成统一的缺失材料清单模型。
- 清单同时输出任务维度 `items` 和成员维度 `members` 两层结构，当前按发票主材料的 `submitter_id` 归属成员，便于后续复核、CLI 查询和导出模块复用。
- 当前先收敛支持两类明确缺失项：`invoice_payment_record_required` 对应 `payment_record`，`invoice_competition_notice_required` 对应 `competition_notice`；不会把抬头错误、金额不匹配或待确认 warning 误聚合成“缺失材料”。
- 新增 `tests/test_missing_materials.py`，覆盖任务级聚合、成员级分组，以及“非缺失类校验结果不应进入清单”的过滤逻辑。
- 将 `TASKS.md` 中“建立缺失材料清单模型”标记为已完成。

### 修改文件
- `src/trms_backend/domain/missing_materials.py`
- `tests/test_missing_materials.py`
- `TASKS.md`
- `WORKLOG.md`

### 根因
- 仓库已经具备支付记录、比赛通知等附件完整性规则，但这些结果仍停留在逐发票校验层，尚无统一模型把“明确缺少哪些材料、对应哪个成员/任务”聚合出来，导致后续 FR-009 复核、FR-010 导出和 FR-014 CLI 缺失材料查询都缺少稳定基础。

### 验证结果
- 已通过：
  - `uv run pytest tests/test_missing_materials.py`
    - 2 个用例通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - pytest 108 个用例通过
    - `git diff --check` 通过

### 假设
- 在尚未引入费用明细版本和成员权限上下文前，本轮保守采用“发票主材料提交人即缺失材料责任成员”的归属规则；若后续业务确认应按分摊成员或任务管理员视角归属，应在独立任务中调整聚合口径。
- 本轮只把“明确缺少附件”的 blocker 失败聚合进清单，不把金额不一致、识别待确认或比赛范围 warning 视为缺失材料，避免把异常校验与缺件问题混为一类。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“支持材料补充后重新校验”，把补挂附件后的校验刷新与当前缺失材料清单联动起来。

## 2026-04-28 04:02 - Implement competition location range validation

### 完成内容
- 为发票校验新增 `invoice_competition_location_range` 规则，默认对 `railway`、`airfare`、`local_transport`、`hotel` 四类与比赛行程直接相关的费用执行地点范围检查。
- 规则会从发票主材料及已关联辅助材料的最新有效识别结果中提取地点信息，支持按 `transaction_location`、`location`、`trip_route` 以及 `departure/arrival`、`pickup/dropoff` 等字段组做基础匹配。
- 当任一地点信息与任务 `competition_location` 做基础归一化匹配时返回 `passed`；存在地点信息但均不匹配时返回 `failed`；完全缺少地点信息时返回 `pending`，显式暴露“无法判断”的状态。
- 将地点规则接入发票创建时的统一校验链路，并纳入发票辅助材料关联/取消关联后的局部重算，保证成员后补行程单、订单截图等地点材料后，相关 warning 结果可同步刷新。
- 补充发票 API 回归测试，覆盖“地点缺失返回待确认”“往返路径包含比赛城市时通过”“路线与比赛地点无关时 warning 失败”三条主路径。
- 将 `TASKS.md` 中“实现比赛地点范围校验”标记为已完成。

### 修改文件
- `src/trms_backend/domain/invoice_validation.py`
- `src/trms_backend/api/invoices.py`
- `tests/test_invoices_api.py`
- `TASKS.md`
- `WORKLOG.md`

### 根因
- 当前仓库已经覆盖比赛时间范围校验，但 FR-006 的地点范围规则仍未进入统一校验结果，也没有利用现有识别结果和辅助材料关联模型对出发地、到达地或往返路径做基础判断，导致系统无法显式提示“地点缺失需人工确认”或“路线明显与比赛地点不相关”。

### 验证结果
- 已通过：
  - `uv run pytest tests/test_invoices_api.py`
    - 34 个用例通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - pytest 106 个用例通过
    - `git diff --check` 通过

### 假设
- 需求文档只要求“基础匹配”，未定义更细的行政区、机场三字码、火车站别名或中转策略；本轮保守收敛为基于归一化文本的包含匹配，不引入额外城市词典或地理编码依赖。
- 当存在多份地点证据时，本轮只要任一材料能与比赛地点形成基础匹配即返回 `passed`；其余不匹配地点仍保留在结构化证据中，但不单独升级为冲突状态。若后续需要“匹配与不匹配同时出现时返回待确认”，应在单独任务中细化冲突策略。
- 当前地点规则只在发票创建、辅助材料关联和取消关联时刷新；若后续需要在识别任务状态更新后自动反推相关发票重校验，应在单独任务中补齐，而不是在本轮扩散为新的通用机制。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“建立缺失材料清单模型”，把现有支付记录、比赛通知和时间/地点 warning 结果继续聚合为可复核清单。

## 2026-04-28 03:59 - Implement competition time range validation

### 完成内容
- 为发票校验新增 `invoice_competition_time_range` 规则，默认对 `railway`、`airfare`、`local_transport`、`hotel` 四类与行程直接相关的费用执行比赛时间范围检查。
- 规则优先使用 `transaction_time` 判断是否落在比赛起止日期前后各 1 天的默认缓冲窗口内；若命中窗口则返回 `passed`，超出窗口则返回 `failed` 且严重级别为 `warning`，不把 Should 级规则误当作 Must 级阻断。
- 当发票只有 `issue_date`、缺少 `transaction_time` 时，规则返回 `pending`，显式暴露“无法判断”的状态，而不是回退用开票日期静默判定通过。
- 补充发票 API 回归测试，覆盖“基础通过”“缺少交易时间返回待确认”“超出默认缓冲范围返回 warning 失败”三条主路径。
- 将 `TASKS.md` 中“实现比赛时间范围校验”标记为已完成。

### 修改文件
- `src/trms_backend/domain/invoice_validation.py`
- `tests/test_invoices_api.py`
- `TASKS.md`
- `WORKLOG.md`

### 根因
- 当前仓库的发票校验链路已经覆盖抬头、税号、重复发票和附件完整性，但 FR-006 的比赛范围检查仍未落到统一校验结果里，导致系统既无法优先依据实际交易时间给出范围判断，也无法在交易时间缺失时显式提示“仍需人工确认”。

### 验证结果
- 已通过：
  - `uv run pytest tests/test_invoices_api.py`
    - 32 个用例通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - pytest 104 个用例通过
    - `git diff --check` 通过

### 假设
- 需求文档和架构文档只明确了“比赛时间范围校验”与默认前后缓冲建议，但没有定义报名费、其他杂项费用的统一合理窗口；本轮保守收敛为仅对 `railway`、`airfare`、`local_transport`、`hotel` 执行该规则，`registration` 与 `other` 暂返回 `not_applicable`，避免把尚未确认的业务边界硬编码成错误失败。
- 默认缓冲窗口采用架构文档 A-002 建议值：比赛开始日前 1 天至结束日后 1 天。若后续业务确认需要更宽或按费用类型区分，应在单独任务中抽出配置，而不是在本轮直接扩散改动。
- 当前时间比较基于发票记录中的 `transaction_time.date()`；仓库尚未定义比赛时区字段，因此本轮不额外引入跨时区换算策略。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“实现比赛地点范围校验”，继续补齐 FR-006 的剩余范围规则。

## 2026-04-28 03:50 - Implement rideshare trip information validation for local transport invoices

### 完成内容
- 为发票校验新增 `invoice_local_transport_rideshare_trip_required` 规则：当费用类型为 `local_transport` 时，系统先根据识别结果判断是否为网约车；若无法判断，则返回 `pending`；若已识别为网约车但缺少行程信息，则返回 `failed`；若已具备行程信息，则返回 `passed`。
- 将网约车规则接入发票创建时的即时校验链路，并纳入发票辅助材料关联/取消关联后的局部重算，保证成员补挂订单截图等辅助材料后，校验结果会同步刷新。
- 补充发票 API 回归测试，覆盖“非市内交通不适用”“无法判断是否为网约车返回待确认”“已识别为网约车但缺少行程信息失败”“补挂含上下车地点的订单截图后通过”四条主路径。
- 将 `TASKS.md` 中“实现网约车行程信息校验”标记为已完成。

### 修改文件
- `src/trms_backend/domain/invoice_validation.py`
- `src/trms_backend/api/invoices.py`
- `tests/test_invoices_api.py`
- `TASKS.md`
- `WORKLOG.md`

### 根因
- 当前仓库已经具备统一的发票校验结果模型、辅助材料关联模型和附件重算入口，但附件完整性规则仍缺少“市内交通是否为网约车”与“网约车是否具备行程信息”这条 Must 级规则，导致系统无法显式暴露该类缺失材料问题，也无法区分“材料不足”与“识别结论仍不确定”。

### 验证结果
- 已通过：
  - `uv run pytest tests/test_invoices_api.py`
    - 30 个用例通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - pytest 102 个用例通过
    - `git diff --check` 通过

### 假设
- 当前仓库尚无单独的“网约车”领域字段或专用附件类型，因此本轮保守收敛为：只基于识别结果中的 `is_rideshare`、`transport_mode`、`transport_type`、`ride_service_type` 判断是否为网约车；若这些字段都缺失，系统返回 `pending`，不静默假定“不是网约车”。
- 本轮将“行程信息”收敛为识别结果中至少具备以下任一信息组：`trip_route`、`trip_itinerary`、`trip_start_location + trip_end_location`、`pickup_location + dropoff_location`、`start_location + end_location`。若后续需要更细的字段标准，应在单独任务中固化识别 schema。
- 网约车规则当前只在发票创建、辅助材料关联和取消关联时刷新；若后续需要在订单截图或其他辅助材料识别结果更新后自动触发相关发票重校验，应作为单独任务补齐。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“实现比赛时间范围校验”，继续补齐比赛范围类规则。

## 2026-04-28 03:44 - Implement airfare attachment completeness validation

### 完成内容
- 为发票校验新增两条航空费用规则：`invoice_airfare_itinerary_required` 和 `invoice_airfare_cabin_proof_required`。前者用于校验航空费用是否已关联行程单，后者用于校验是否存在可用的舱位信息，或在缺少舱位信息时是否至少补充了订单截图。
- 将航空规则接入发票创建时的即时校验链路，并纳入发票辅助材料关联/取消关联后的局部重算，保证成员补挂行程单或订单截图后，校验结果会同步刷新。
- 补充发票 API 回归测试，覆盖“非航空费用不适用”“航空费用缺少行程单与舱位信息失败”“补挂带舱位信息的行程单后通过”“缺少舱位信息但已补订单截图时转为待确认”四条主路径。
- 将 `TASKS.md` 中“实现航空费用附件完整性校验”标记为已完成。

### 修改文件
- `src/trms_backend/domain/invoice_validation.py`
- `src/trms_backend/api/invoices.py`
- `tests/test_invoices_api.py`
- `TASKS.md`
- `WORKLOG.md`

### 根因
- 当前仓库已经有统一的发票校验结果模型、辅助材料关联模型和局部重算入口，但附件完整性规则只覆盖了支付记录和比赛通知，尚未把航空费用所需的行程单、舱位信息和订单截图边界落到统一校验结果中，因此系统无法显式暴露这类 Must 级缺失材料问题。

### 验证结果
- 已通过：
  - `uv run pytest tests/test_invoices_api.py`
    - 27 个用例通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - pytest 99 个用例通过
    - `git diff --check` 通过

### 假设
- 由于当前实现是“先有发票材料，再创建发票记录”的发票中心模型，`TASKS.md` 中“航空费用缺少发票或行程单”在现有代码路径里若直接按字面实现会退化为恒真条件。本轮保守收敛为：航空费用发票除主发票材料外，仍必须额外关联至少一份 `itinerary` 类型材料，借此形成可执行、可测试的附件完整性闭环。
- 舱位信息当前只从最新有效识别结果中的 `cabin_class`、`seat_class`、`cabin` 三个字段名读取；若这些字段都缺失但已关联订单截图，则返回 `pending`，表示“材料已补，但仍需人工确认”，而不是静默通过。
- 本轮只在发票创建、辅助材料关联和取消关联时刷新航空规则；如果后续需要在行程单或订单截图识别结果更新后自动触发相关发票重校验，应作为单独任务补齐。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“实现网约车行程信息校验”，继续补齐费用类型对应的附件完整性规则。

## 2026-04-28 03:35 - Implement competition notice validation for registration invoices

### 完成内容
- 为发票校验新增 `invoice_competition_notice_required` 规则：当发票费用类型为 `registration` 时，若未关联 `competition_notice` 类型辅助材料，则返回 `failed`；已关联时返回 `passed`；其他费用类型返回 `not_applicable`。
- 将该规则接入发票创建时的即时校验链路，并纳入发票辅助材料关联/取消关联后的局部重算，保证成员补挂或解绑比赛通知后，校验结果会同步更新。
- 补充发票 API 回归测试，覆盖“非参赛费不适用”“参赛费缺少比赛通知失败”“补挂比赛通知后通过”三条主路径。
- 将 `TASKS.md` 中“实现参赛费比赛通知校验”标记为已完成。

### 修改文件
- `src/trms_backend/domain/invoice_validation.py`
- `src/trms_backend/api/invoices.py`
- `tests/test_invoices_api.py`
- `TASKS.md`
- `WORKLOG.md`

### 根因
- 当前仓库已经具备发票与辅助材料关联模型，也已实现大额支付记录类的附件完整性校验，但参赛费“必须补比赛通知”这一 Must 规则尚未进入统一校验结果，因此系统无法显式暴露该类缺失材料问题，也无法在后续复核状态流转中据此阻断。

### 验证结果
- 已通过：
  - `uv run pytest tests/test_invoices_api.py`
    - 24 个用例通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - pytest 96 个用例通过
    - `git diff --check` 通过

### 假设
- 本轮将“比赛通知校验”收敛为“参赛费发票是否已关联至少一份 `competition_notice` 类型材料”，不进一步解析通知内容中是否明确包含支付要求；这是因为当前 `TASKS.md` 的 Done when 只要求存在性校验，仓库内也尚未定义比赛通知内容识别结构。
- 规则只依据材料类型字段 `material_type=competition_notice` 判断，不依赖文件名猜测，满足当前任务的最小闭环要求；后续若要校验“通知内容确有支付要求”，应在单独任务中引入识别字段和更细粒度规则。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“实现航空费用附件完整性校验”，继续补齐费用类型对应的附件完整性规则。

## 2026-04-28 03:31 - Implement payment record amount match validation

### 完成内容
- 为发票校验新增 `invoice_payment_record_amount_match` 规则：仅在单张发票金额达到支付记录阈值且已关联 `payment_record` 类型附件时生效，默认按“支付记录金额求和后与发票金额精确匹配”执行比对。
- 金额匹配规则会读取每个已关联支付记录材料的最新有效识别结果中的 `amount_cents` 字段；金额一致时返回 `passed`，金额不一致时返回 `failed`，金额缺失时返回 `pending`，避免把“已有关联但金额还没识别出来”误报为通过或失败。
- 将该规则接入发票创建和支付记录附件关联/取消关联后的局部重算链路，与既有 `invoice_payment_record_required` 一起刷新，但不覆盖抬头、税号、重复号码等无关校验结果。
- 补充发票 API 回归测试，覆盖“未达阈值不适用”“达到阈值但未关联支付记录时不执行金额匹配”“支付记录金额一致通过”“金额不一致失败”“金额缺失待确认”五条路径。
- 将 `TASKS.md` 中“实现支付记录金额匹配校验”标记为已完成。

### 修改文件
- `src/trms_backend/domain/invoice_validation.py`
- `src/trms_backend/api/invoices.py`
- `tests/test_invoices_api.py`
- `TASKS.md`
- `WORKLOG.md`

### 根因
- 当前仓库已经能校验“大额发票必须关联支付记录”，但支付记录只停留在“存在性”层面，没有把支付记录识别出的金额接入统一校验结果，因此系统无法显式判断“附件已经补齐，但金额仍不一致或尚未识别”的关键复核场景。

### 验证结果
- 已通过：
  - `uv run pytest tests/test_invoices_api.py`
    - 22 个用例通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - pytest 94 个用例通过
    - `git diff --check` 通过

### 假设
- 本轮默认将“金额匹配”收敛为 `trms_backend.domain.invoice_validation.PAYMENT_RECORD_AMOUNT_MATCH_MODE = "exact_sum"`，即所有已关联支付记录材料的识别金额求和后，必须与发票金额精确相等；后续如需容差、单条匹配或任务级配置，应在单独任务中扩展。
- 支付记录金额来源暂时只读取辅助材料最新有效识别结果中的 `amount_cents` 字段，不新增单独的支付记录领域模型；若识别结果缺少该字段，则返回 `pending`，由后续人工补录或识别增强任务处理。
- 本轮只在发票创建、支付记录附件关联和取消关联时刷新该规则；若后续需要在支付记录识别结果更新后自动重算，应单独补“识别完成触发相关发票重校验”的任务，而不是在本轮顺手扩散实现。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“实现参赛费比赛通知校验”，继续补齐费用类型对应的附件完整性规则。

## 2026-04-28 03:25 - Add large-amount payment record validation skeleton

### 完成内容
- 为发票校验新增 `invoice_payment_record_required` 规则：当单张发票金额达到阈值时，若未关联 `payment_record` 类型附件，则返回 `failed`；低于阈值时返回 `not_applicable`；已关联支付记录时返回 `passed`。
- 将该规则接入现有发票创建校验链，并在结构化 `evidence` 中记录发票金额、阈值、配置来源和已关联支付记录材料 ID，避免后续调用方只能依赖自然语言消息判断。
- 在发票辅助材料关联/取消关联后，新增局部重算逻辑，仅刷新支付记录规则，保证成员补传支付记录后校验结果会立即变化，同时不覆盖此前“识别缺失需人工确认”的校验语义。
- 补充发票 API 回归测试，覆盖“低于阈值不适用”“达到阈值且缺少支付记录失败”“补充支付记录后重算通过”三条路径。
- 将 `TASKS.md` 中“实现金额超过阈值需要支付记录的校验骨架”标记为已完成。

### 修改文件
- `src/trms_backend/domain/invoice_validation.py`
- `src/trms_backend/api/invoices.py`
- `tests/test_invoices_api.py`
- `TASKS.md`
- `WORKLOG.md`

### 根因
- 现有发票校验只覆盖抬头、税号和重复号码，虽然仓库已经有发票与辅助材料关联模型，但“大额发票必须附支付记录”这一主链路规则尚未落到统一校验结果里，导致系统无法显式暴露该类缺失材料问题。

### 验证结果
- 已通过：
  - `uv run pytest tests/test_invoices_api.py`
    - 20 个用例通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - pytest 92 个用例通过
    - `git diff --check` 通过

### 假设
- 本轮将“金额超过阈值”收敛为“`amount_cents >= 100000`”，即默认阈值为 1000 元；该默认值当前以代码常量 `trms_backend.domain.invoice_validation.PAYMENT_RECORD_REQUIRED_AMOUNT_THRESHOLD_CENTS` 表达，后续若需要任务级或系统级配置，再在单独任务中抽出配置入口。
- 本轮只判断“是否存在至少一份 `payment_record` 类型附件”，不比较支付记录金额，也不校验支付记录内容完整性；这些能力留给 `TASKS.md` 中后续“支付记录金额匹配校验”等任务处理。
- 为避免附件关联操作把既有“识别缺失 -> pending”语义意外覆盖，本轮在附件增删后只局部重算支付记录规则，不对抬头、税号、重复号码规则做全量重跑。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“实现支付记录金额匹配校验”，把当前“有无支付记录”骨架推进到支付金额一致性校验。

## 2026-04-28 03:19 - Mark unrecognized invoice title and tax number validations as pending

### 完成内容
- 将发票抬头/税号校验接入“人工覆盖前的最新有效识别快照”：创建发票时会先读取材料最近一次非 `pending` 的识别任务，再执行人工录入覆盖，避免把“原本未识别”直接静默抹掉。
- 当识别结果里缺少 `buyer_name` 或 `tax_number` 时，抬头/税号规则不再仅凭人工录入值直接判定通过；若人工录入值与任务配置一致，校验结果返回 `pending`，明确表示“识别缺失，仍需人工确认”。
- 若识别缺失同时人工录入值又与任务配置不一致，规则直接返回 `failed`，并在结构化证据中同时记录“识别缺失”和当前人工值，避免把“未识别”和“值错误”混成一个模糊状态。
- 补充发票 API 回归测试，覆盖“识别结果已产出但缺少抬头/税号时返回 `pending`”和“识别失败且人工录入值错误时继续返回 `failed`”两条路径。
- 将 `TASKS.md` 中“未识别抬头或税号时输出待确认校验”标记为已完成。

### 修改文件
- `src/trms_backend/api/invoices.py`
- `src/trms_backend/domain/invoice_validation.py`
- `tests/test_invoices_api.py`
- `TASKS.md`
- `WORKLOG.md`

### 根因
- 现有发票创建流程会先把人工录入字段写回识别任务，再运行抬头/税号校验；校验层只看发票当前字段，不看此前的识别结果，因此一旦人工录入补齐抬头或税号，系统就无法区分“AI 已识别且正确”与“AI 根本没识别出来但被人工补录”，从而把“未识别”静默伪装成“通过”。

### 验证结果
- 已通过：
  - `uv run pytest tests/test_invoices_api.py`
    - 18 个用例通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - pytest 90 个用例通过
    - `git diff --check` 通过

### 假设
- 本轮把“未识别”收敛为“存在最近一次有效识别任务，但其中缺少 `buyer_name` 或 `tax_number` 字段”；如果材料当前只有默认占位识别任务、尚未产出任何有效识别结果，则继续沿用现有人工录入的通过/失败判定，不把“尚未开始识别”和“识别后缺失字段”混为同一状态。
- 当前仍以人工录入后的发票字段作为最终比较对象；因此当识别缺失但人工录入值本身已经与任务配置不一致时，本轮直接返回 `failed`，不降级为 `pending`。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“单张发票金额达到阈值时校验支付记录附件”，继续把发票校验从抬头/税号/重复号码扩展到附件完整性主链路。

## 2026-04-28 03:12 - Extend invoice validation result schema with structured evidence

### 完成内容
- 扩展发票校验结果模型 `ValidationResult`，在原有 `rule_code`、`target_type`、`target_id`、`severity`、`status`、`message` 之外新增结构化 `evidence`，让规则输出既能给人看，也能给后续复核/聚合逻辑稳定消费。
- 为现有三条发票规则补齐证据内容：抬头校验返回期望/实际抬头，税号校验返回期望/实际税号，重复发票校验返回发票号码和重复目标发票编号，不再只有自然语言消息。
- 持久化层新增 `validation_results.evidence` JSON 列，并保证创建发票后的实时校验结果和 `GET /api/invoices/{invoice_id}/validations` 查询结果都能稳定返回结构化证据。
- 补充发票 API 回归测试，覆盖“创建发票时返回完整结构化校验结果”“抬头/税号失败时证据准确”“重复发票时证据保留重复目标”“校验查询接口返回结构化证据”四条路径。
- 将 `TASKS.md` 中“扩展发票校验规则结果”标记为已完成。

### 修改文件
- `src/trms_backend/domain/invoices.py`
- `src/trms_backend/domain/invoice_validation.py`
- `src/trms_backend/infrastructure/models.py`
- `src/trms_backend/infrastructure/repositories.py`
- `tests/test_invoices_api.py`
- `TASKS.md`
- `WORKLOG.md`

### 根因
- 现有发票校验虽然已经有 `rule_code`、目标编号、严重级别和状态，但缺少结构化 `evidence`，调用方只能依赖 `message` 文本理解失败原因，无法稳定支持后续规则聚合、复核界面展示或按字段精确提示。

### 验证结果
- 已通过：
  - `uv run pytest tests/test_invoices_api.py`
    - 16 个用例通过
  - `uv run pytest tests/test_tasks_api.py`
    - 29 个用例通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - pytest 88 个用例通过
    - `git diff --check` 通过

### 假设
- 本轮将“目标对象”继续收敛为现有稳定字段 `target_type` + `target_id`，不额外引入新的嵌套 target 结构，避免在没有明确消费方之前制造重复表示。
- `evidence` 先按 JSON 结构保存当前规则的最小必要证据；后续新增金额、附件完整性或时间地点规则时，可在同一字段下继续扩展更复杂的结构化证据。
- 当前仓库仍依赖 `Base.metadata.create_all(...)` 初始化数据库，因此新增 `validation_results.evidence` 列会自动体现在新建数据库上；已有旧库若要保留数据，仍需按现有迁移策略单独处理，当前未对共享旧库执行迁移验证。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“未识别抬头或税号时输出待确认校验”，把当前“字段缺失/低置信度不能静默通过”的规则语义补齐到发票校验结果中。

## 2026-04-28 03:24 - Preserve recognition attempt history and expose latest effective result

### 完成内容
- 为材料维度的识别任务查询补充 `latest_effective` 视图，在保留完整 `items` 历史列表的同时，显式返回最近一条已产出有效结果的识别尝试，避免调用方只能自己从历史里猜“当前应采用哪条结果”。
- 修正人工更正落点：当同一材料已经创建了新的重试占位任务但仍停留在 `pending` 时，人工录入发票字段现在会把这次更正落到最新那次尝试，并将其状态提升为 `needs_confirmation`，不再把结构化字段静默写进纯占位任务。
- 保留旧识别记录不被覆盖：新的识别失败、待确认或人工更正都只更新对应的新尝试，旧任务上的识别字段与审计历史保持原样，满足“同一材料多次识别尝试可追溯”的边界。
- 补充识别与发票 API 回归测试，覆盖“仅有占位任务时 `latest_effective` 为空”“创建重试后仍能查询旧的最新有效结果”“新重试失败后最新有效结果切换到新任务”“人工更正发生在重试任务时旧历史保持不变”四条关键路径。
- 将 `TASKS.md` 中“支持多次识别历史”标记为已完成。

### 修改文件
- `src/trms_backend/api/recognitions.py`
- `src/trms_backend/domain/recognitions.py`
- `src/trms_backend/infrastructure/repositories.py`
- `tests/test_invoices_api.py`
- `tests/test_materials_api.py`
- `tests/test_recognition_tasks_api.py`
- `TASKS.md`
- `WORKLOG.md`

### 验证结果
- 已通过：
  - `uv run pytest tests/test_recognition_tasks_api.py`
    - 7 个用例通过
  - `uv run pytest tests/test_invoices_api.py`
    - 15 个用例通过
  - `uv run pytest tests/test_materials_api.py`
    - 22 个用例通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - pytest 87 个用例通过
    - `git diff --check` 通过

### 假设
- 本轮将“最新有效结果”定义为同一材料下最近一条状态已脱离 `pending` 的识别任务；纯占位重试任务在尚未产出结果前不会抢占该视图。
- 当前人工更正接口仍按 `material_id` 工作，不支持显式指定“要修正哪一次识别尝试”；因此本轮保守地把更正落到最新创建的那次尝试上，并在它仍是占位任务时提升为 `needs_confirmation`，使其成为可审计的当前有效尝试。
- 本轮不新增数据库表或列，只在现有 `recognition_tasks` 模型上补充查询与状态语义，因此不改变既有 `create_all` 迁移边界。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“扩展发票校验规则结果”，把当前发票校验输出从最小结果扩展为带 `rule_code`、目标对象、严重级别、状态和结构化证据的统一模型。

## 2026-04-28 03:02 - Expose recognition failures explicitly

### 完成内容
- 为识别任务新增结构化失败详情 `failure`，包含失败阶段 `ocr` / `pdf` / `ai` 和失败原因，避免识别任务只有 `failed` 状态却没有可追溯上下文。
- 收紧识别状态更新边界：当识别任务切到 `failed` 时，接口现在必须同时提交失败详情；非 `failed` 状态禁止携带失败详情，避免把失败原因混入成功或待确认结果。
- 识别任务查询接口 `GET /api/materials/{material_id}/recognition-tasks` 现在会直接返回失败状态和失败详情，因此材料维度可以显式看到识别失败，而不是只能猜测识别没有成功。
- 补充识别与材料 API 回归测试，覆盖“缺少失败详情时拒绝写入失败状态”“失败详情可持久化并再次查询”以及占位识别任务默认无失败详情三条路径。
- 将 `TASKS.md` 中“支持识别失败显式暴露”标记为已完成。

### 修改文件
- `src/trms_backend/domain/recognitions.py`
- `src/trms_backend/api/recognitions.py`
- `src/trms_backend/infrastructure/models.py`
- `src/trms_backend/infrastructure/repositories.py`
- `tests/test_recognition_tasks_api.py`
- `tests/test_materials_api.py`
- `TASKS.md`
- `WORKLOG.md`

### 验证结果
- 已通过：
  - `uv run pytest tests/test_recognition_tasks_api.py`
    - 6 个用例通过
  - `uv run pytest tests/test_materials_api.py`
    - 22 个用例通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - pytest 85 个用例通过
    - `git diff --check` 通过

### 假设
- 本轮将“API 返回材料识别失败状态”收敛为材料维度的识别任务查询接口 `GET /api/materials/{material_id}/recognition-tasks`；当前仓库尚无单独的材料详情接口，因此不额外扩展新的读取入口。
- `failed` 状态默认必须携带失败详情，因为没有失败原因的失败记录仍然无法满足“显式暴露”目标；后续若接入真实 OCR / PDF / AI worker，应在任务失败时统一写入阶段和原因。
- 当前仓库仍依赖 `Base.metadata.create_all(...)` 初始化数据库，因此新增 `recognition_tasks.failure_detail` 列只会自动体现在新建数据库上；已有旧库若需保留数据，仍需按现有迁移策略单独处理。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“支持多次识别历史”，把当前失败详情与多次重试历史串起来，避免新的识别尝试覆盖旧失败记录。

## 2026-04-28 02:56 - Record manual correction history for recognized invoice fields

### 完成内容
- 为识别字段结果补充 `updated_at`，并在识别任务里新增 `manual_corrections` 历史，显式保存每次人工更正的字段名、操作者、修改前值、修改后值、重校验触发状态和更正时间。
- 将 `POST /api/materials/{material_id}/invoice` 接入识别结果覆盖层：人工录入或再次更正发票字段后，会把最新结构化字段同步写回该材料最近一次识别任务，并将字段来源标记为 `manual`，不再让人工修订停留在发票表里而无法回溯到识别链路。
- 保留现有发票重校验主链：人工更正后仍立即重跑抬头、税号和重复发票校验，因此关键字段的修订不会静默绕过验证。
- 补充发票与识别 API 回归测试，覆盖“AI 识别结果被人工修正后字段来源切换为 manual”“同一字段多次修正能追溯前后差异”“关键字段再次修正后校验结果随之变化”三条主路径。
- 将 `TASKS.md` 中“增加人工更正识别字段记录”标记为已完成。

### 修改文件
- `src/trms_backend/domain/recognitions.py`
- `src/trms_backend/infrastructure/models.py`
- `src/trms_backend/infrastructure/repositories.py`
- `src/trms_backend/api/invoices.py`
- `src/trms_backend/main.py`
- `tests/test_invoices_api.py`
- `tests/test_recognition_tasks_api.py`
- `TASKS.md`
- `WORKLOG.md`

### 验证结果
- 已通过：
  - `uv run pytest tests/test_recognition_tasks_api.py`
    - 6 个用例通过
  - `uv run pytest tests/test_invoices_api.py`
    - 14 个用例通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - pytest 85 个用例通过
    - `git diff --check` 通过

### 假设
- 本轮把“人工更正识别字段”收敛为覆盖该材料最近一次识别任务上的当前有效字段视图，并将更正前值保存在 `manual_corrections` 历史中；这样既能让当前识别结果体现 `manual` 来源，又不会丢失差异审计。
- 关键字段集合按当前人工录入发票接口的全部结构化字段处理，因此每次人工修正这些字段都会记录为 `revalidation_status=triggered`；现阶段真正执行的仍是现有发票校验规则，后续新增更多规则时可复用同一触发语义。
- 当前仓库依旧使用 `create_all` 初始化数据库，因此新增 `manual_corrections` 列只会自动体现在新建数据库上；已有共享旧库若需保留数据，仍需按既有迁移策略单独处理。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“支持识别失败显式暴露”，把失败原因、失败状态暴露和当前人工更正历史串起来，避免识别失败路径继续停留在黑盒状态。

## 2026-04-28 02:49 - Establish manual invoice entry boundary

### 完成内容
- 将 `POST /api/materials/{material_id}/invoice` 收敛为显式人工录入入口：请求体新增 `actor_id`，只有材料提交人本人或该任务管理员可以录入/覆盖发票字段，避免“任何人都能替任意材料写发票”的权限空洞。
- 将同一材料的发票写入语义改为按 `material_id` upsert：重复人工录入不会再为同一材料创建多条发票记录，而是覆盖原记录并刷新 `updated_at`，为后续人工更正链路保留稳定主键边界。
- 保留现有基础校验链：每次人工录入或重复录入后，仍会重新执行抬头匹配、税号匹配和同任务发票号码重复校验，不把“人工覆盖”伪装成跳过校验。
- 补充发票 API 回归测试，覆盖“成员本人录入成功”“任务管理员代录入成功”“无关用户越权失败”“同一材料重复录入更新原记录而非新增重复行”四条关键路径。
- 将 `TASKS.md` 中“建立人工录入发票字段边界”标记为已完成。

### 修改文件
- `src/trms_backend/domain/invoices.py`
- `src/trms_backend/api/invoices.py`
- `src/trms_backend/infrastructure/repositories.py`
- `tests/test_invoices_api.py`
- `tests/test_tasks_api.py`
- `TASKS.md`
- `WORKLOG.md`

### 验证结果
- 已通过：
  - `uv run pytest tests/test_invoices_api.py`
    - 13 个用例通过
  - `uv run pytest tests/test_splits_api.py`
    - 5 个用例通过
  - `uv run pytest tests/test_confirmations_api.py`
    - 5 个用例通过
  - `uv run pytest tests/test_tasks_api.py`
    - 29 个用例通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - pytest 84 个用例通过
    - `git diff --check` 通过

### 假设
- 当前仓库仍未实现统一登录态与认证上下文，因此本轮把“管理员或成员可录入”收敛为显式 `actor_id` 边界：允许材料提交人本人或任务 `administrator_id` 录入，其他人拒绝；这不是完整鉴权，只是当前第一阶段最小可验证权限模型。
- 需求和现有数据模型都把“发票结构化信息”视为材料的一份当前有效表示，因此本轮将同一材料的重复人工录入定义为覆盖更新，而不是继续新增第二条发票记录；字段级修改差异与来源审计留给下一项“增加人工更正识别字段记录”处理。
- 当前任务不额外限制任务状态；只要材料已归属到任务且录入者身份满足最小边界，就允许人工录入或覆盖发票字段。若后续需求要求“仅开放中/复核中允许修改”，应在单独任务中补充状态门禁。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“增加人工更正识别字段记录”，在当前 upsert 边界之上补充字段来源、修改时间和更正前后差异追溯。

## 2026-04-28 02:42 - Establish recognition task trigger boundary

### 完成内容
- 将材料上传链路接入识别占位触发：`POST /api/tasks/{task_id}/materials` 和 `POST /api/materials/pending-assignment` 在每个成功落库的材料后，都会自动创建一个 `pending` 状态的识别任务，占位后续异步 OCR / AI 处理，但本轮不接入任何真实外部服务。
- 保持上传响应边界不变：接口仍同步返回材料上传结果，不等待真实识别执行；本轮只增加本地数据库中的识别任务占位，不把耗时识别工作塞进上传请求。
- 调整识别任务测试语义：上传产生的首个识别任务现在视为默认尝试；原有手工 `POST /api/materials/{material_id}/recognition-tasks` 继续保留，用于显式追加新的重试/历史尝试。
- 补充材料与识别 API 回归测试，覆盖“已归属材料上传后自动创建识别任务”“待归属材料上传后自动创建识别任务”“手工追加第二次识别尝试”三条主路径。
- 将 `TASKS.md` 中“建立识别任务触发边界”标记为已完成。

### 修改文件
- `src/trms_backend/api/materials.py`
- `src/trms_backend/main.py`
- `tests/test_materials_api.py`
- `tests/test_recognition_tasks_api.py`
- `TASKS.md`
- `WORKLOG.md`

### 验证结果
- 已通过：
  - `uv run pytest tests/test_materials_api.py`
    - 22 个用例通过
  - `uv run pytest tests/test_recognition_tasks_api.py`
    - 6 个用例通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - pytest 81 个用例通过
    - `git diff --check` 通过

### 假设
- 本轮将“材料提交后触发识别”收敛为“为每个成功创建的材料自动插入一个 `pending` 识别任务占位”，而不是在上传请求中直接执行 OCR、PDF 解析或外部 AI 调用；这满足架构文档里“识别属于异步辅助能力”的边界，同时避免把上传响应和识别耗时耦合在一起。
- 自动触发同时覆盖已归属材料和待归属材料；原因是需求与架构都把比赛通知、行程单、订单截图、支付记录等所有材料纳入统一识别链路，待归属材料不应因为身份未解析而失去后续识别入口。
- 管理员认领待归属材料时，本轮不额外再生成新的默认识别任务；认领改变的是归属关系，不是新一次文件提交。若后续需要在认领后重新识别，当前保留的手工创建识别任务接口可作为显式重试入口。
- 当前仓库仍依赖 `Base.metadata.create_all(...)` 初始化数据库，因此本轮没有新增 schema，只在现有 `recognition_tasks` 表基础上补上上传触发逻辑；共享旧库若此前已缺少该表，仍需按已有迁移策略处理。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“建立人工录入发票字段边界”，把成员/管理员录入发票关键字段的最小接口和基础校验边界补齐。

## 2026-04-28 02:37 - Persist recognition raw results and field confidence

### 完成内容
- 为识别任务模型补充字段级结果结构，显式保存 `raw_response`、字段值、字段来源和 `0..1` 置信度；识别任务列表和详情返回也同步暴露这些内容，避免识别状态存在但结果内容丢失。
- 在 `recognition_tasks` 持久化表中新增 `raw_response`、`recognized_fields` 两个 JSON 字段，并在仓储层保证结果可写入、可读取、可随状态更新一起持久化。
- 扩展 `PATCH /api/recognition-tasks/{recognition_task_id}/status` 请求体，允许在状态流转时一并提交识别结果；当字段被显式标记为 `needs_confirmation` 时，接口拒绝把该任务直接更新为 `succeeded`，防止低置信度结果被静默当作已确认事实。
- 补充识别任务 API 回归测试，覆盖低置信度字段必须进入 `needs_confirmation`、以及原始响应与字段置信度能被持久化和再次查询的路径。
- 将 `TASKS.md` 中“保存识别原始结果和字段置信度”标记为已完成。

### 修改文件
- `src/trms_backend/domain/recognitions.py`
- `src/trms_backend/api/recognitions.py`
- `src/trms_backend/infrastructure/models.py`
- `src/trms_backend/infrastructure/repositories.py`
- `tests/test_recognition_tasks_api.py`
- `TASKS.md`
- `WORKLOG.md`

### 验证结果
- 已通过：
  - `uv run pytest tests/test_recognition_tasks_api.py`
    - 5 个用例通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - pytest 80 个用例通过
    - `git diff --check` 通过

### 假设
- 本轮将“低置信度字段可标记为待确认”收敛为显式字段状态 `needs_confirmation`，不在当前任务内再引入全局置信度阈值配置；原因是需求和现有代码尚未定义统一阈值，强行硬编码会把策略和存储边界混在一起。后续若要自动根据置信度判定待确认，应在单独规则或配置任务里补齐阈值来源。
- 当前仍未接入真实 OCR / PDF / AI provider，本轮只提供“识别结果如何保存和暴露”的稳定边界，不把占位任务自动触发或外部调用混入当前任务；上传后自动创建识别任务的动作仍留给下一项“建立识别任务触发边界”处理。
- 当前仓库仍依赖 `Base.metadata.create_all(...)` 初始化数据库，因此本轮新增的 `recognition_tasks.raw_response`、`recognition_tasks.recognized_fields` 列只会自动体现在新建数据库上；已有旧库若需要保留数据，仍需后续迁移机制统一处理。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“建立识别任务触发边界”，把材料提交后的识别任务创建或排队动作做成显式但不阻塞上传响应的占位链路。

## 2026-04-28 02:31 - Establish AI recognition task placeholders

### 完成内容
- 新增独立识别任务领域模型 `RecognitionTask`，显式支持 `pending`、`succeeded`、`failed`、`needs_confirmation` 四种状态，并用 `is_final_fact=false` 固化“AI 输出只是识别建议，不是最终事实来源”的第一阶段边界。
- 新增 `recognition_tasks` 持久化表与 SQLAlchemy 仓储，实现材料维度的识别任务创建、查询和状态更新，占位后续 OCR / AI / 异步处理链路，但本轮不接入任何真实外部识别服务。
- 新增最小识别任务 API：`POST /api/materials/{material_id}/recognition-tasks`、`GET /api/materials/{material_id}/recognition-tasks`、`PATCH /api/recognition-tasks/{recognition_task_id}/status`，用于显式创建占位任务、查询状态，以及在无外部 AI 的前提下验证状态流转边界。
- 补充识别任务 API 回归测试，覆盖占位创建、`pending -> needs_confirmation -> succeeded`、`pending -> failed` 和终态非法回退四条主路径。
- 将 `TASKS.md` 中“建立 AI 识别任务占位模型”标记为已完成。

### 修改文件
- `src/trms_backend/domain/recognitions.py`
- `src/trms_backend/api/recognitions.py`
- `src/trms_backend/infrastructure/models.py`
- `src/trms_backend/infrastructure/repositories.py`
- `src/trms_backend/main.py`
- `tests/test_recognition_tasks_api.py`
- `TASKS.md`
- `WORKLOG.md`

### 验证结果
- 已通过：
  - `uv run pytest tests/test_recognition_tasks_api.py`
    - 4 个用例通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - pytest 79 个用例通过
    - `git diff --check` 通过

### 假设
- 本轮把“识别任务占位”严格收敛为任务状态骨架，不在当前任务内继续保存 OCR 原文、字段值、字段来源、置信度或失败原因；这些内容留给后续“保存识别原始结果和字段置信度”“支持识别失败显式暴露”等任务分别补齐，避免一次性把识别链路做散。
- 当前未把材料上传自动接入识别任务创建；原因是 `TASKS.md` 下一项已单独定义“建立识别任务触发边界”。本轮只提供显式创建占位任务的最小入口，不把“自动排队”提前实现成隐藏副作用。
- 当前仓库仍依赖 `Base.metadata.create_all(...)` 初始化数据库，因此本轮新增的 `recognition_tasks` 表只会自动体现在新建数据库上；已有旧库若需要保留数据，仍需后续迁移机制统一处理。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“保存识别原始结果和字段置信度”，先把识别原始响应、字段值、来源和置信度挂到当前识别任务骨架上，再决定低置信度字段的待确认表达方式。

## 2026-04-28 03:10 - Establish invoice supporting-material associations

### 完成内容
- 为发票补充显式辅助材料关联模型 `invoice_supporting_material_links`，支持把支付记录、比赛通知、行程单、订单截图及其他非发票材料关联到指定发票，并保留关联创建时间。
- 在发票 API 新增最小关联操作：`PUT /api/invoices/{invoice_id}/supporting-materials/{material_id}`、`GET /api/invoices/{invoice_id}/supporting-materials` 和 `DELETE /api/invoices/{invoice_id}/supporting-materials/{material_id}`，覆盖建立关联、查询关联和取消关联三条主路径。
- 为避免模型语义混乱，补充发票来源约束：只有 `material_type=invoice` 且已归属到任务的材料才能创建发票；辅助材料关联仅允许同任务、已归属、非发票类型材料。
- 补充发票 API 回归测试，覆盖“同一辅助材料可关联多张同任务发票”的第一阶段规则，以及取消关联、拒绝把发票型材料当作辅助材料、拒绝从非发票材料创建发票等边界。
- 将 `TASKS.md` 中“建立发票与辅助材料关联模型”标记为已完成。

### 修改文件
- `src/trms_backend/domain/invoices.py`
- `src/trms_backend/api/invoices.py`
- `src/trms_backend/infrastructure/models.py`
- `src/trms_backend/infrastructure/repositories.py`
- `tests/test_invoices_api.py`
- `TASKS.md`
- `WORKLOG.md`

### 验证结果
- 已通过：
  - `uv run pytest tests/test_invoices_api.py`
    - 10 个用例通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - pytest 75 个用例通过
    - `git diff --check` 通过

### 假设
- 本轮将“一个附件是否可关联多张发票”收敛为允许同一辅助材料关联多张同任务发票；原因是第一阶段附件完整性校验更关心“某张发票是否具备所需佐证”，而不是强制每个佐证文件只能服务单张发票。若后续业务证明某些材料类型必须一对一，应在规则层按材料类型单独收紧，而不是把当前关联模型做成不可扩展的一刀切限制。
- 当前关联对象限定为已归属任务的非发票材料，不允许把原始发票材料再次作为“辅助材料”挂到其他发票下，避免把“发票主单据”和“辅助佐证”两种语义混在同一关系里。
- 当前仓库仍依赖 `Base.metadata.create_all(...)` 初始化数据库，因此本轮新增的 `invoice_supporting_material_links` 表只会自动体现在新建数据库上；已有旧库若需要保留数据，仍需后续迁移机制统一处理。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“建立 AI 识别任务占位模型”，先补识别任务状态骨架和“AI 输出不是最终事实来源”的显式边界，再决定如何触发上传后的异步识别占位。

## 2026-04-28 02:43 - Confirm cross-channel duplicate material detection

### 完成内容
- 补充材料上传回归测试，显式覆盖“同一任务内先经 Web、后经 CLI 提交相同文件内容但不同文件名”时仍按 `sha256` 标记重复，避免后续实现误把渠道或文件名引入判重条件。
- 基于现有仓储实现确认当前重复文件检测边界：判重仅依赖 `task_id + sha256 + assigned`，不依赖渠道字段，也不依赖原始文件名；因此本轮不扩展业务逻辑，只把该能力固化为可验证约束。
- 将 `TASKS.md` 中“增加跨渠道重复文件检测”标记为已完成。

### 修改文件
- `tests/test_materials_api.py`
- `TASKS.md`
- `WORKLOG.md`

### 验证结果
- 已通过：
  - `uv run pytest tests/test_materials_api.py`
    - 22 个用例通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - pytest 71 个用例通过
    - `git diff --check` 通过

### 假设
- 当前第一阶段把“跨渠道重复文件检测”收敛为同一任务下基于原始文件 `sha256` 的重复标记；它解决的是重复上传归档问题，不等同于发票号码重复校验，也不试图判断“内容相似但二进制不完全相同”的近重复文件。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“建立发票与辅助材料关联模型”，把支付记录、比赛通知、行程单、订单截图等附件与发票的关联关系显式建模，为后续附件完整性校验提供基础。

## 2026-04-28 02:28 - Add pending-assignment material claim flow

### 完成内容
- 为待归属材料新增显式认领入口 `POST /api/materials/{material_id}/claim`，允许任务管理员将 `pending_assignment` 材料绑定到目标任务和提交人，并把材料状态切换为 `assigned`。
- 在材料记录中新增 `claimed_by`、`claimed_at` 审计字段，显式记录认领操作者和认领时间，避免管理员处理动作不可追溯。
- 认领时增加最小权限与一致性校验：只有目标任务的 `administrator_id` 可认领；被绑定的 `submitter_id` 必须属于任务成员；非待归属材料不能重复认领。
- 调整材料仓储认领逻辑：待归属材料转入任务时会重新参与同任务文件哈希重复检测，并在任务材料列表中可见。
- 补充材料 API 测试，覆盖管理员成功认领、非管理员拒绝、已归属材料拒绝三条最小回归路径。
- 将 `TASKS.md` 中“建立待归属材料认领流程”标记为已完成。

### 修改文件
- `src/trms_backend/domain/materials.py`
- `src/trms_backend/domain/tasks.py`
- `src/trms_backend/api/materials.py`
- `src/trms_backend/infrastructure/models.py`
- `src/trms_backend/infrastructure/repositories.py`
- `tests/test_materials_api.py`
- `TASKS.md`
- `WORKLOG.md`

### 验证结果
- 已通过：
  - `uv run pytest tests/test_materials_api.py`
    - 22 个用例通过
  - `uv run pytest tests/test_material_storage.py tests/test_invoices_api.py tests/test_tasks_api.py`
    - 38 个用例通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - pytest 71 个用例通过
    - `git diff --check` 通过

### 假设
- 当前仓库尚未实现统一认证上下文，因此本轮把“管理员可认领”收敛为显式提交 `administrator_id` 并校验其必须等于目标任务的 `administrator_id`；这是第一阶段最小权限边界，不把它伪装成完整登录鉴权。
- 待归属材料的认领视为管理员归档动作，而不是成员新增提交，因此本轮不复用成员提交截止时间门禁；即使任务已过截止时间，只要管理员仍在处理该任务，仍允许把此前已收进系统的待归属材料绑定到目标任务和成员。
- 材料原始 `task_id_hint`、`submitter_id_hint` 在线索被人工确认后仍保留，用于追溯提交时的原始猜测，不在认领时覆盖或删除。
- 当前仓库仍依赖 `Base.metadata.create_all(...)` 初始化数据库，因此本轮新增的 `materials.claimed_by`、`materials.claimed_at` 列只会自动体现在新建数据库上；已有旧库若缺少这些列，仍需后续迁移机制统一处理。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“增加跨渠道重复文件检测”，补上待归属/已归属之外的跨渠道重复材料识别与展示边界。

## 2026-04-28 02:11 - Add pending-assignment material status

### 完成内容
- 在材料领域模型中新增显式 `status`，区分 `assigned` 和 `pending_assignment` 两类材料；待归属材料允许暂不绑定 `task_id` 和 `submitter_id`，同时保留 `task_id_hint`、`submitter_id_hint` 作为后续管理员认领的线索。
- 为无法确定任务或提交人的渠道新增独立接入口 `POST /api/materials/pending-assignment`，复用现有文件校验和批量部分成功语义，把未归属材料收敛为显式状态，而不是继续靠直接失败或混入普通任务材料列表。
- 调整材料仓储与任务内列表边界：只有 `assigned` 材料会参与任务维度查询和同任务文件哈希重复检测，确保待归属材料不会通过 `/api/tasks/{task_id}/materials` 暴露给普通成员视图。
- 补充材料 API 测试，覆盖“无已解析身份时进入待归属状态”以及“带任务提示的待归属材料不会出现在任务材料列表中”两条最小回归路径。
- 将 `TASKS.md` 中“增加待归属材料状态”标记为已完成。

### 修改文件
- `src/trms_backend/domain/materials.py`
- `src/trms_backend/api/materials.py`
- `src/trms_backend/infrastructure/models.py`
- `src/trms_backend/infrastructure/repositories.py`
- `tests/test_materials_api.py`
- `TASKS.md`
- `WORKLOG.md`

### 验证结果
- 已通过：
  - `uv run pytest tests/test_materials_api.py`
    - 19 个用例通过
  - `uv run pytest tests/test_material_storage.py tests/test_invoices_api.py tests/test_tasks_api.py`
    - 38 个用例通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - pytest 68 个用例通过
    - `git diff --check` 通过

### 假设
- 本轮将“待归属材料”接入边界收敛为独立入口：现有 `POST /api/tasks/{task_id}/materials` 仍然坚持“任务已确定且提交人属于成员名单”这一显式不变量，不把原本应返回的成员校验错误静默降级为待归属。
- 当前仓库尚未实现真实认证和管理员权限模型，因此本轮不伪造“管理员专用列表/处理接口”来声称完成权限控制；只保证待归属材料不会出现在任务内普通材料列表中，管理员认领和权限隔离的实际处理链路留给下一任务实现。
- 当前仓库仍依赖 `Base.metadata.create_all(...)` 初始化数据库，因此本轮新增的 `materials.status`、`materials.task_id_hint`、`materials.submitter_id_hint` 以及空值约束调整只会自动体现在新建数据库上；已有旧库若缺少这些列，仍需后续迁移机制任务统一处理。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“建立待归属材料认领流程”，补上管理员将待归属材料绑定到任务和提交人的操作入口，并显式记录操作者与处理时间。

## 2026-04-28 02:04 - Support partial success for batch material upload

### 完成内容
- 调整 `POST /api/tasks/{task_id}/materials` 的批量上传语义：多文件请求不再因为单个文件校验失败而整体短路，而是逐文件执行上传校验，并聚合返回成功记录和失败明细。
- 保持单文件上传现有兼容边界：单文件缺少文件名、空文件、内容类型不支持和超出大小限制时，仍分别返回原有 `422`、`415`、`413` 错误，不改变已存在调用方的错误码语义。
- 为多文件上传新增聚合返回状态：全部成功返回 `201 success`，部分成功返回 `207 partial_success`，全部失败返回 `422 failed`；失败项显式返回 `original_filename`、`error_code` 和 `detail`，避免把“部分成功”伪装成“全部成功”或“单一错误”。
- 补充材料上传 API 测试，覆盖“一个成功一个失败”的部分成功场景，以及“全部失败但逐文件暴露原因”的批量失败场景；同时确认只有成功文件会真正落库。
- 将 `TASKS.md` 中“支持批量上传部分成功结果”标记为已完成。

### 修改文件
- `src/trms_backend/api/materials.py`
- `tests/test_materials_api.py`
- `TASKS.md`
- `WORKLOG.md`

### 验证结果
- 已通过：
  - `uv run pytest tests/test_materials_api.py`
    - 17 个用例通过
  - `uv run pytest tests/test_material_storage.py`
    - 3 个用例通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - pytest 66 个用例通过
    - `git diff --check` 通过

### 假设
- 本轮把“批量上传部分成功”限定在文件级输入校验错误上：缺少文件名、空文件、不支持内容类型和超出大小限制会被聚合到失败列表；若后续出现磁盘写入、数据库故障等基础设施异常，当前仍按服务端错误直接失败显式暴露，不在本轮内继续扩展为更宽泛的补偿逻辑。
- 为降低现有接口回归风险，本轮只对多文件请求引入聚合状态和逐文件失败列表；单文件请求继续保持既有 HTTP 错误码和 `detail` 响应格式，供现有 Web/CLI 调用方继续复用。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“增加待归属材料状态”，把“无法识别任务或提交人”的异常路径从当前直接失败，收敛为管理员可见、普通成员不可见的待归属材料模型。

## 2026-04-28 01:59 - Add material upload validation rules

### 完成内容
- 在材料领域新增显式上传校验边界，统一校验缺少文件名、空文件、不支持的内容类型和超出大小限制四类失败场景；支持的内容类型和大小上限直接固化在代码常量中，避免隐藏规则。
- 调整 `POST /api/tasks/{task_id}/materials` 的处理顺序：先读取并验证本次请求中的全部上传文件，再执行落盘和建库，避免无效文件在失败前先产生部分副作用。
- 补充材料上传 API 测试，覆盖支持类型成功路径，以及缺少文件名、空文件、不支持内容类型、超出大小限制四类明确失败路径。
- 将 `TASKS.md` 中“增加材料上传文件校验规则”标记为已完成。

### 修改文件
- `src/trms_backend/domain/materials.py`
- `src/trms_backend/api/materials.py`
- `tests/test_materials_api.py`
- `TASKS.md`
- `WORKLOG.md`

### 验证结果
- 已通过：
  - `uv run pytest tests/test_materials_api.py`
    - 15 个用例通过
  - `uv run pytest tests/test_material_storage.py`
    - 3 个用例通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - pytest 64 个用例通过
    - `git diff --check` 通过

### 假设
- 本轮采用保守上传白名单：`application/pdf`、`application/zip`、`image/jpeg`、`image/png`、`image/webp`；未在需求和现有代码中明确出现的内容类型暂不放行，后续若需要支持更多附件格式，应先补充规则和测试。
- 单文件大小上限暂定为 `10 MiB`，作为第一阶段本地部署场景下的最小明确边界；后续如果出现真实业务文件超限，再结合对象存储、反向代理和渠道接入能力统一调整。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“支持批量上传部分成功结果”，把当前请求级全量校验扩展为逐文件返回成功/失败结果，同时保持失败原因显式暴露。

## 2026-04-28 01:55 - Persist material storage key

### 完成内容
- 为材料领域模型 `MaterialCreate` / `MaterialRecord` 增加不可变 `storage_key` 字段，并在材料上传接口中把存储层返回的 `storage_key` 一并持久化，而不是只保留文件名、大小和哈希。
- 在 `materials` 表新增 `storage_key` 列，并通过 SQLAlchemy 仓储映射读写该字段，使 API 返回、数据库记录和实际落盘文件三者能稳定关联。
- 补充材料上传测试，覆盖上传返回 `storage_key`；补充存储集成测试，覆盖数据库中的 `storage_key` 能定位到已保存的原始文件，满足“数据库不保存完整文件内容，但能通过 key 找到文件”的任务边界。
- 将 `TASKS.md` 中“保存原始文件存储位置”标记为已完成。

### 修改文件
- `src/trms_backend/domain/materials.py`
- `src/trms_backend/api/materials.py`
- `src/trms_backend/infrastructure/models.py`
- `src/trms_backend/infrastructure/repositories.py`
- `tests/test_material_storage.py`
- `tests/test_materials_api.py`
- `TASKS.md`
- `WORKLOG.md`

### 验证结果
- 已通过：
  - `uv run pytest tests/test_material_storage.py tests/test_materials_api.py`
    - 14 个用例通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - pytest 60 个用例通过
    - `git diff --check` 通过

### 假设
- 本轮把“原始文件存储位置”收敛为存储层生成的 `storage_key`，其语义是对象存储或本地存储中的稳定定位键；当前默认本地实现下该 key 恰好表现为相对路径，但上层业务只依赖其“不可变定位信息”语义，不依赖本地路径格式。
- 当前仓库仍使用 `Base.metadata.create_all(...)` 初始化数据库，因此新增 `materials.storage_key` 列只会自动出现在新建数据库中；已有旧 SQLite 库若缺少该列，需要重建数据库或在后续迁移机制任务中补齐 schema。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“增加材料上传文件校验规则”，把空文件、缺少文件名、内容类型和大小限制的失败路径补齐，并保持上传失败原因显式暴露。

## 2026-04-28 01:51 - Establish material file storage abstraction

### 完成内容
- 为材料上传链路新增 `MaterialFileStorage` / `StoredMaterialFile` 抽象，并提供默认本地实现 `LocalMaterialFileStorage`，把“原始文件保存”从 API 逻辑中拆出，形成可替换的基础设施边界。
- 调整 `POST /api/tasks/{task_id}/materials`：上传时先通过存储接口落盘，再把返回的文件元数据写入材料记录，避免继续出现“只算哈希、不保存原始文件”的行为。
- 默认本地存储使用唯一 `storage_key` 生成策略，同一任务下重复上传同名文件时不会互相覆盖；同时会规范化文件名，避免路径片段直接进入落盘路径。
- 补充 `tests/test_material_storage.py`，覆盖同名文件重复保存不覆盖、文件元数据记录正确；并为涉及材料上传的 API 测试注入临时存储目录，避免验证过程污染仓库工作树。
- 将 `TASKS.md` 中“建立材料文件保存抽象”标记为已完成。

### 修改文件
- `src/trms_backend/domain/materials.py`
- `src/trms_backend/api/materials.py`
- `src/trms_backend/main.py`
- `src/trms_backend/infrastructure/storage.py`
- `tests/test_material_storage.py`
- `tests/test_materials_api.py`
- `tests/test_invoices_api.py`
- `tests/test_tasks_api.py`
- `TASKS.md`
- `WORKLOG.md`

### 验证结果
- 已通过：
  - `uv run pytest tests/test_material_storage.py tests/test_materials_api.py tests/test_invoices_api.py tests/test_tasks_api.py`
    - 48 个用例通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - pytest 59 个用例通过
    - `git diff --check` 通过

### 假设
- 本轮只建立“文件存储接口 + 默认本地实现 + 上传链路接入”，暂不把 `storage_key` 持久化到 `materials` 表；这是下一项“保存原始文件存储位置”任务的边界，避免本轮跨任务扩散修改。
- 默认运行时本地存储目录使用 `MATERIAL_STORAGE_DIR` 环境变量或 `./data/materials`；测试场景统一改用 `tmp_path` 下的临时目录，避免把验证产物写进仓库。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“保存原始文件存储位置”，把 `storage_key` 作为不可变定位信息持久化到材料记录中，使后续识别、导出和审计链路可以稳定引用原始文件。

## 2026-04-28 01:46 - Add material type classification field

### 完成内容
- 在材料领域模型中新增受限枚举 `material_type`，统一支持 `invoice`、`payment_record`、`competition_notice`、`itinerary`、`order_screenshot` 和 `other_attachment` 六类材料。
- 在统一材料提交接口 `POST /api/tasks/{task_id}/materials` 增加必填表单字段 `material_type`，并确保 API 返回体和材料列表接口都能返回该字段。
- 在 SQLAlchemy 材料表与仓储映射中持久化 `material_type`，保持内存仓储和数据库仓储行为一致。
- 补充 `tests/test_materials_api.py`，覆盖受支持材料类型保存返回、非法类型 `422` 失败路径，以及列表接口返回材料类型。
- 调整 `tests/test_tasks_api.py` 与 `tests/test_invoices_api.py` 的上传辅助方法，使现有发票与任务链路显式提交 `material_type=invoice`。
- 将 `TASKS.md` 中“增加材料类型与附件类型字段”标记为已完成。

### 修改文件
- `src/trms_backend/domain/materials.py`
- `src/trms_backend/api/materials.py`
- `src/trms_backend/infrastructure/models.py`
- `src/trms_backend/infrastructure/repositories.py`
- `tests/test_materials_api.py`
- `tests/test_tasks_api.py`
- `tests/test_invoices_api.py`
- `TASKS.md`
- `WORKLOG.md`

### 验证结果
- 已通过：
  - `uv run pytest tests/test_materials_api.py`
    - 11 个用例通过
  - `uv run pytest tests/test_invoices_api.py`
    - 6 个用例通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - pytest 57 个用例通过
    - `git diff --check` 通过

### 假设
- 本轮采用单一字段 `material_type` 承载“发票”和“各类附件”分类，不额外拆分高层 `material_type` 与低层 `attachment_type` 双字段；后续若需要做附件关联或更细规则，可在现有枚举边界上继续扩展。
- 当前仓库仍依赖 `Base.metadata.create_all(...)` 建表；因此本轮新增 `materials.material_type` 列只会体现在新建数据库上，已有本地 SQLite 若已存在旧表结构，需要重建数据库或在后续迁移任务中补齐 schema。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“建立材料文件保存抽象”，把材料记录与实际文件落盘路径解耦，为“保存原始文件存储位置”和“不覆盖同名文件”任务提供稳定接口。

## 2026-04-28 01:41 - Enforce task member-only material submission

### 完成内容
- 在任务领域的成员提交通道校验中新增显式成员门禁：提交人不在任务 `member_ids` 内时，立即拒绝提交，而不是继续落库材料。
- 在统一材料提交接口 `POST /api/tasks/{task_id}/materials` 接入该门禁；由于当前 Web、CLI、Telegram、Email 四个渠道都复用这条 API，本轮校验会统一覆盖四个渠道。
- 补充 `tests/test_materials_api.py`，覆盖任务成员在四个渠道提交成功，以及非任务成员在四个渠道提交时返回明确 `409` 错误。
- 将 `TASKS.md` 中“校验材料提交人必须属于任务成员”标记为已完成。

### 修改文件
- `src/trms_backend/domain/tasks.py`
- `src/trms_backend/api/materials.py`
- `tests/test_materials_api.py`
- `TASKS.md`
- `WORKLOG.md`

### 验证结果
- 已通过：
  - `uv run pytest tests/test_materials_api.py`
    - 9 个用例通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - pytest 55 个用例通过
    - `git diff --check` 通过

### 假设
- 当前仓库尚未实现 Telegram、邮件、CLI 的真实身份绑定和“待归属材料”流程，因此本轮采用保守边界：只要渠道已给出 `submitter_id`，就必须属于目标任务成员名单；无法识别身份后转待归属的路径，留给后续“增加待归属材料状态”和“建立待归属材料认领流程”任务建模。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“增加材料类型与附件类型字段”，先把材料主记录的类型边界建起来，再为后续支付记录、比赛通知等附件规则提供基础字段。

## 2026-04-28 01:37 - Enforce task status transition conditions

### 完成内容
- 在任务领域新增 `ready_to_export` 的最小复核门禁：对当前仓库已经落库的事实做保守检查，要求发票必须已有校验结果、不得存在 blocker 级失败或待确认校验、每张发票必须已有费用分摊、每条分摊必须已有成员确认且不能处于异议状态。
- 在任务状态更新接口接入上述复核门禁；当任务尝试从 `reviewing` 进入 `ready_to_export` 且条件不满足时，返回明确 `409` 错误，而不是只依赖状态图放行。
- 对 `completed` 增加保守完成门禁：由于当前仓库尚未实现导出模块和“导出完成”持久化事实，本轮统一拒绝进入 `completed`，避免在没有导出证据时伪装流程已完成。
- 补充 `tests/test_tasks_api.py`，覆盖复核条件满足时可进入 `ready_to_export`、blocker 校验失败拒绝进入、成员确认缺失拒绝进入，以及未记录导出完成前拒绝进入 `completed`。
- 将 `TASKS.md` 中“增加任务状态流转条件检查”标记为已完成。

### 修改文件
- `src/trms_backend/domain/tasks.py`
- `src/trms_backend/api/tasks.py`
- `src/trms_backend/main.py`
- `tests/test_tasks_api.py`
- `TASKS.md`
- `WORKLOG.md`

### 验证结果
- 已通过：
  - `uv run pytest tests/test_tasks_api.py`
    - 29 个用例通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - pytest 53 个用例通过
    - `git diff --check` 通过

### 假设
- 当前“复核条件满足”只按仓库内已实现且可验证的事实收敛：发票校验、费用分摊和成员确认；待归属材料、导出记录、管理员人工处理 blocker 等更完整的复核事实，留给后续对应任务建模后再接入。
- 在导出模块和导出任务模型落地前，本轮将 `completed` 视为不可达状态；这样比无条件放行更符合“completed 只能在导出完成后进入”的要求，也避免产生虚假的流程完成状态。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“校验材料提交人必须属于任务成员”，把 Web、CLI、Telegram、Email 共用的成员归属门禁补上。

## 2026-04-28 01:32 - Add task deadline check boundary

### 完成内容
- 在任务领域新增 `close_expired_open_tasks(...)`，统一复用 `deadline <= 当前时间` 的截止判定，只关闭已到期且仍处于 `open` 状态的任务。
- 在任务 API 新增手动触发入口 `POST /api/tasks/deadline-check`，返回本次关闭的任务数量和任务 ID，作为后续 cron 或后台调度可复用的显式检查边界。
- 补充 `tests/test_tasks_api.py`，覆盖“到期开放任务会被关闭”以及“非开放任务不会被误关”的路径。
- 将 `TASKS.md` 中“建立任务自动关闭检查边界”标记为已完成。

### 修改文件
- `src/trms_backend/domain/tasks.py`
- `src/trms_backend/api/tasks.py`
- `tests/test_tasks_api.py`
- `TASKS.md`
- `WORKLOG.md`

### 验证结果
- 已通过：
  - `uv run pytest tests/test_tasks_api.py`
    - 25 个用例通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - pytest 49 个用例通过
    - `git diff --check` 通过

### 假设
- 本轮只建立“可手动调用的截止检查边界”，不引入真实调度器；后续如需自动执行，可由 cron、后台任务或运维入口调用同一检查接口。
- 自动关闭边界与成员提交截止边界保持一致，均按 `deadline <= 当前时间` 处理，避免“成员已不可提交但任务仍长期保持 open”。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“增加任务状态流转条件检查”，把 `ready_to_export` 和 `completed` 的门禁收紧到复核与导出事实。

## 2026-04-28 01:28 - Enforce task submission deadline boundary

### 完成内容
- 在任务领域新增成员材料提交截止判断 `ensure_task_accepts_member_submission(...)`，统一定义 `deadline <= 当前时间` 即不再允许成员继续提交。
- 在材料提交接口增加截止时间门禁：任务即使仍处于 `open` 状态，只要已过截止时间，就返回明确 `409` 错误，而不是继续接收材料。
- 补充 `tests/test_materials_api.py`，覆盖已过截止时间的拒绝路径，以及“刚好等于截止时刻”这一边界行为。
- 将 `TASKS.md` 中“增加任务截止时间状态约束”标记为已完成。

### 修改文件
- `src/trms_backend/domain/tasks.py`
- `src/trms_backend/api/materials.py`
- `tests/test_materials_api.py`
- `TASKS.md`
- `WORKLOG.md`

### 验证结果
- 已通过：
  - `uv run pytest tests/test_materials_api.py`
    - 7 个用例通过
  - `uv run pytest tests/test_tasks_api.py`
    - 23 个用例通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - pytest 47 个用例通过
    - `git diff --check` 通过

### 假设
- 当前仓库还没有独立的管理员补交通道或管理员身份上下文；因此本轮采用保守边界，只对现有成员材料提交通道加截止限制，不为不存在的管理员路径隐式放行。
- “任务自动关闭”仍留给后续 `TASKS.md` 中的“建立任务自动关闭检查边界”处理；本轮只修复“任务状态仍为 open 时，超期成员仍可提交”的缺口。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“建立任务自动关闭检查边界”，为到期仍处于 `open` 的任务提供显式检查入口或服务。

## 2026-04-28 01:25 - Enforce task fee category constraints

### 完成内容
- 在任务领域层为 `fee_categories` 增加受支持类别校验，只允许当前系统已定义的费用类别进入任务配置。
- 在发票创建接口增加任务级费用类别门禁：发票 `expense_type` 若不属于任务允许类别，返回明确 `409` 错误，而不是先落库再依赖后续校验发现问题。
- 补充 `tests/test_tasks_api.py`，覆盖任务配置非法费用类别的失败路径。
- 补充 `tests/test_invoices_api.py`，覆盖任务未允许某费用类型时拒绝创建发票的失败路径。
- 将 `TASKS.md` 中“增加任务费用类别约束”标记为已完成。

### 修改文件
- `src/trms_backend/domain/tasks.py`
- `src/trms_backend/api/invoices.py`
- `tests/test_tasks_api.py`
- `tests/test_invoices_api.py`
- `TASKS.md`
- `WORKLOG.md`

### 验证结果
- 已通过：
  - `uv run pytest tests/test_tasks_api.py`
    - 23 个用例通过
  - `uv run pytest tests/test_invoices_api.py`
    - 6 个用例通过

### 假设
- 本轮把“任务允许配置受支持的费用类别”收敛到当前 `ExpenseType` 枚举集合，不额外引入独立的费用类别配置表；如后续需要任务外可配置类别，应单独建模后再扩展。
- 发票费用类型与任务允许类别不一致时返回 `409`，因为发票载荷本身是全局合法枚举，但与目标任务配置冲突。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“增加任务截止时间状态约束”，优先明确超期后成员提交通道的拒绝规则与边界时间测试。

## 2026-04-28 01:22 - Add task member management API

### 完成内容
- 为任务模块新增成员名单查询接口 `GET /api/tasks/{task_id}/members`，可返回当前任务成员列表。
- 为任务模块新增成员名单更新接口 `PUT /api/tasks/{task_id}/members`，以整表替换方式支持草稿态成员的添加、移除和更新。
- 在任务仓储层补充 `update_member_ids(...)`，同时刷新任务 `updated_at`，保持持久化与内存实现行为一致。
- 明确开放提交后的限制：任务一旦不在 `draft` 状态，成员名单更新接口返回 `409`，避免在成员已开始提交材料后静默改变任务成员边界。
- 补充 `tests/test_tasks_api.py`，覆盖成员查询、草稿态替换成功、开放态拒绝修改和缺失任务 404。
- 将 `TASKS.md` 中“增加任务成员管理接口”标记为已完成。

### 修改文件
- `src/trms_backend/api/tasks.py`
- `src/trms_backend/domain/tasks.py`
- `src/trms_backend/infrastructure/repositories.py`
- `tests/test_tasks_api.py`
- `TASKS.md`
- `WORKLOG.md`

### 验证结果
- 已通过：
  - `uv run pytest tests/test_tasks_api.py`
    - 22 个用例通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - pytest 43 个用例通过
    - `git diff --check` 通过

### 假设
- 当前“成员管理”先按成员编号字符串列表处理，不在本轮引入独立成员实体、身份绑定或权限模型。
- “可添加、移除、更新任务成员”通过草稿态整表替换实现；第一阶段当前边界下，不额外拆分单成员增删接口。
- 开放提交后的成员变更规则采用保守限制：仅允许 `draft` 状态修改成员名单；如后续需要支持 `closed` 或 `reviewing` 阶段调整，应在补材料、分摊和确认影响面明确后单独建任务处理。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“增加任务费用类别约束”，先把任务允许费用类别与发票费用类型的约束收紧，再补失败路径测试。

## 2026-04-28 01:45 - Add global invoice defaults boundary

### 完成内容
- 新增领域模型 `GlobalInvoiceConfig` 和仓储边界，用于读取系统级默认发票抬头与税号。
- 新增数据库表 `global_invoice_configs` 及其 SQLAlchemy 仓储，实现可持久化的全局默认配置读取/写入能力。
- 调整任务创建链路：任务抬头和税号改为“可省略输入”，若请求未显式提供，则从全局默认配置继承；若请求显式提供，则按任务级值覆盖默认值。
- 为缺少任务级抬头税号且系统也没有全局默认配置的场景补充明确失败路径，避免静默创建不完整任务。
- 补充 `tests/test_tasks_api.py`，覆盖默认继承、任务级覆盖和缺少默认配置时的失败路径。
- 将 `TASKS.md` 中“建立全局发票抬头和税号配置边界”标记为已完成。

### 修改文件
- `src/trms_backend/api/tasks.py`
- `src/trms_backend/domain/global_invoice_config.py`
- `src/trms_backend/domain/tasks.py`
- `src/trms_backend/infrastructure/models.py`
- `src/trms_backend/infrastructure/repositories.py`
- `src/trms_backend/main.py`
- `tests/test_tasks_api.py`
- `TASKS.md`
- `WORKLOG.md`

### 验证结果
- 已通过：
  - `uv run pytest tests/test_tasks_api.py`
    - 14 个用例通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - pytest 35 个用例通过
    - `git diff --check` 通过

### 假设
- 本轮只建立“全局默认配置的读取与任务创建继承边界”，不扩展管理员配置 API；当前全局配置通过仓储和应用装配层注入，后续如需管理入口可在此边界上继续扩展。
- 任务级覆盖允许逐字段覆盖：如果任务只显式提供抬头或税号中的一项，另一项仍可回退到全局默认值。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“完善报销任务发布前校验”，把成员名单、费用类别、项目信息和报销人信息缺失时的发布门禁补齐。

## 2026-04-28 01:32 - Clarify first-phase won't-have boundary

### 完成内容
- 新增文档 `docs/第一阶段范围边界说明.md`，固化 TRMS 第一阶段的系统定位是“财务录入前的材料整理平台”，不是财务系统自动提交流程。
- 明确记录第一阶段不实现的能力：FR-011 Browser Use 自动录入、财务系统 API 对接、财务审批状态同步、CLI 直接提交财务系统、保存完整财务登录态、自动最终提交、替代财务处审批、财务系统内个人信息维护。
- 明确“财务填报草稿、汇总表、打印材料”仍属于第一阶段范围，但只服务于管理员人工录入和线下投递，不构成自动化提交。
- 明确后续若要启用 Browser Use，必须满足人工确认提交、审计留痕、凭据管理和失败显式暴露等强制边界。
- 将 `TASKS.md` 中“明确第一阶段 Won't-have 边界”标记为已完成。

### 修改文件
- `docs/第一阶段范围边界说明.md`
- `TASKS.md`
- `WORKLOG.md`

### 验证结果
- 已通过：
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - pytest 32 个用例通过
    - `git diff --check` 通过

### 假设
- 当前需求文档中的“生成财务填报草稿”仍属于第一阶段范围，但其语义仅限于人工录入辅助信息，不包含任何财务系统自动提交能力。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“建立全局发票抬头和税号配置边界”，优先落模型或服务边界，再补默认继承测试。

## 2026-04-28 01:20 - Document database migration strategy boundary

### 完成内容
- 新增文档 `docs/数据库迁移策略说明.md`，记录当前数据库初始化仍依赖应用启动时执行 `Base.metadata.create_all(...)`。
- 明确当前仓库尚未引入 Alembic，现阶段继续保留 `create_all` 仅作为第一阶段早期开发和测试的低成本建表方案。
- 记录 `create_all` 的阶段性限制：无法做可靠的增量 schema 变更、版本追踪、回滚和数据迁移，不适合作为共享环境的长期迁移机制。
- 明确 Alembic 的引入触发条件：一旦出现已有表结构变更、需要保留历史数据、共享部署环境、数据回填或多人协作下的版本管理需求，应优先切换到版本化迁移。
- 将 `TASKS.md` 中“增加数据库迁移策略说明”标记为已完成。

### 修改文件
- `docs/数据库迁移策略说明.md`
- `TASKS.md`
- `WORKLOG.md`

### 验证结果
- 已通过：
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - pytest 32 个用例通过
    - `git diff --check` 通过

### 假设
- 当前第一阶段的主要运行场景仍是本地 SQLite 和 pytest 临时数据库，因此暂不把 Alembic 作为强制前置依赖。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“明确第一阶段 Won't-have 边界”，把 FR-011 和财务系统自动化相关能力的非目标范围写清楚。

## 2026-04-28 01:18 - Enforce task publish readiness validation

### 完成内容
- 在任务领域新增发布门禁校验，显式检查 `member_ids`、`fee_categories`、`project_info`、`reimburser_info` 四类发布前必填信息。
- 调整任务状态更新接口：仅当目标状态进入 `open` 时触发发布校验；若草稿任务缺少上述字段，则返回明确 `409` 错误，而不是只依赖状态图放行。
- 在 `tests/test_tasks_api.py` 增加发布成功与 4 条失败路径覆盖；失败路径通过数据库中篡改不完整草稿任务构造，证明发布校验独立于创建校验存在。
- 将 `TASKS.md` 中“完善报销任务发布前校验”标记为已完成。

### 修改文件
- `src/trms_backend/api/tasks.py`
- `src/trms_backend/domain/tasks.py`
- `tests/test_tasks_api.py`
- `TASKS.md`
- `WORKLOG.md`

### 验证结果
- 已通过：
  - `uv run pytest tests/test_tasks_api.py`
    - 18 个用例通过
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - pytest 39 个用例通过
    - `git diff --check` 通过

### 假设
- 发布门禁对所有进入 `open` 的状态迁移统一生效，而不只限制 `draft -> open`；原因是 `open` 代表允许成员提交材料，缺少基础任务信息时不应重新开放。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“增加任务成员管理接口”，优先补只读查询和草稿态变更边界，再决定开放状态下的成员变更限制。

## 2026-04-28 01:15 - Map first-phase acceptance criteria

### 完成内容
- 新增独立文档 `docs/第一阶段验收映射.md`，逐条映射 AC-001 至 AC-018 的当前实现状态。
- 映射结论只基于当前仓库代码和测试事实，核对了任务、材料、发票、分摊、确认五类后端能力及其测试覆盖。
- 明确当前可视为已完成的验收项主要是：
  - AC-007 抬头税号校验
  - AC-010 费用分摊
  - AC-011 成员确认
  - AC-016 重复发票检查
- 明确当前仍为部分完成或未开始的关键验收项主要集中在：
  - AC-002 全局抬头税号默认继承
  - AC-008 大额支付记录校验
  - AC-009 附件完整性校验
  - AC-012 管理员复核
  - AC-013 至 AC-014 导出能力
  - AC-015 权限隔离
  - AC-017 缺失材料提醒
  - AC-018 审计记录
- 将 `TASKS.md` 中“整理第一阶段验收映射”标记为已完成。

### 修改文件
- `docs/第一阶段验收映射.md`
- `TASKS.md`
- `WORKLOG.md`

### 验证结果
- 已通过：
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - pytest 32 个用例通过
    - `git diff --check` 通过

### 假设
- 本轮将“已完成”限定为当前代码和测试已经满足验收项核心行为；若只具备后端基础能力但缺少用户入口、权限边界或关键链路，则标记为“部分完成”或“未开始”。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“增加数据库迁移策略说明”，先把当前 `create_all` 的阶段性限制写清楚，再决定是否引入 Alembic。

## 2026-04-28 01:10 - Inventory current API capability coverage

### 完成内容
- 梳理当前后端已实现的 API 能力，只记录事实，不改动业务逻辑。
- 确认当前已实现的接口清单：
  - 任务：`POST /api/tasks`、`GET /api/tasks`、`GET /api/tasks/{task_id}`、`PATCH /api/tasks/{task_id}/status`
  - 材料：`POST /api/tasks/{task_id}/materials`、`GET /api/tasks/{task_id}/materials`
  - 发票：`POST /api/materials/{material_id}/invoice`、`GET /api/tasks/{task_id}/invoices`、`GET /api/invoices/{invoice_id}/validations`
  - 分摊：`PUT /api/invoices/{invoice_id}/splits`、`GET /api/invoices/{invoice_id}/splits`
  - 确认：`PUT /api/splits/{split_id}/confirmation`、`GET /api/invoices/{invoice_id}/confirmations`
- 确认当前测试已覆盖上述接口的主路径和主要失败路径，相关测试文件为 `tests/test_tasks_api.py`、`tests/test_materials_api.py`、`tests/test_invoices_api.py`、`tests/test_splits_api.py`、`tests/test_confirmations_api.py`。
- 记录需求文档 FR-001 至 FR-015 与当前 API 的覆盖关系：

| 需求 | 当前覆盖 | 依据 |
|---|---|---|
| FR-001 创建比赛报销收集任务 | 部分覆盖 | 已有任务创建、查询、列表、状态流转接口；已校验空成员、截止时间、比赛日期顺序；尚无全局抬头/税号默认继承，也无发布前完整性校验。 |
| FR-002 多渠道材料提交 | 部分覆盖 | 已有统一材料上传接口，`channel` 支持 `web`、`cli`、`telegram`、`email`，并限制任务必须为 `open`；尚无成员身份校验、待归属材料流程、独立渠道接入器。 |
| FR-003 AI Agent 辅助识别元数据 | 未覆盖 | 当前只有人工创建发票接口，没有识别任务、置信度或原始识别结果模型。 |
| FR-004 发票抬头和税号校验 | 部分覆盖 | 创建发票时会生成 `invoice_title_match`、`invoice_tax_number_match`、`invoice_number_unique` 三条校验结果。 |
| FR-005 附件完整性校验 | 未覆盖 | 尚无支付记录、比赛通知、行程单等附件关联和完整性规则。 |
| FR-006 比赛范围校验 | 未覆盖 | 尚无交易时间、地点与比赛范围的校验逻辑。 |
| FR-007 费用归属与多人分摊 | 部分覆盖 | 已有发票分摊替换与查询接口；校验成员必须属于任务且分摊总额必须等于发票金额；尚无费用归属向导或团队公共费用专门流程。 |
| FR-008 成员费用确认 | 部分覆盖 | 已有成员确认/异议接口和按发票查询确认记录接口；尚无成员个人费用汇总视图。 |
| FR-009 管理员复核与确认 | 部分覆盖 | 任务状态机包含 `reviewing`、`ready_to_export`、`completed`；但尚无管理员复核、更正、最终确认专用接口和规则门禁。 |
| FR-010 输出报销材料 | 未覆盖 | 尚无汇总表、明细表、打印 PDF 或财务草稿导出接口。 |
| FR-011 财务系统 Browser Use 录入 | 按第一阶段不实现 | 当前无自动录入能力，符合第一阶段 Won't-have 边界。 |
| FR-012 CLI 材料提交渠道 | 部分覆盖 | 后端上传接口接受 `channel=cli`；但尚无 CLI 客户端、认证绑定和命令行交互。 |
| FR-013 CLI 任务查询 | 部分覆盖 | 已有通用 `GET /api/tasks`、`GET /api/tasks/{task_id}` 可作为 CLI 后端基础；尚无 CLI 程序和成员视角的可提交任务筛选。 |
| FR-014 CLI 状态查询与缺失材料查看 | 部分覆盖 | 已有材料列表、发票校验结果、确认记录查询接口；尚无缺失材料聚合视图、成员待办视图和 CLI 程序。 |
| FR-015 CLI 个人费用确认 | 部分覆盖 | 后端已有分摊确认接口，可被未来 CLI 复用；尚无 CLI 确认命令和成员个人账单查询。 |

### 修改文件
- `TASKS.md`
- `WORKLOG.md`

### 验证结果
- 已通过：
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - pytest 32 个用例通过
    - `git diff --check` 通过

### 假设
- 本轮“API 能力清单”仅按当前 FastAPI 路由、领域约束和现有测试事实梳理，不把未来 CLI、Telegram、邮件适配器视为已实现。

### 后续建议
- 下一轮可继续处理 `TASKS.md` 中“整理第一阶段验收映射”，把 AC-001 至 AC-018 和上述 FR 覆盖状态对齐。

## 2026-04-28 00:55 - Add frontend backlog tasks

### 完成内容
- 补充 `TASKS.md` 的 Web 前端与管理员后台任务。
- 覆盖架构文档建议的 React、TypeScript、Vite 前端边界，以及成员提交入口、管理员任务管理、复核、缺失材料、费用确认和导出入口。
- 增加前端权限可见性、表单/上传组件测试和主流程 E2E 占位任务。

### 修改文件
- `TASKS.md`
- `WORKLOG.md`

### 验证结果
- 已通过：
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - pytest 32 个用例通过
    - `git diff --check` 通过

### 假设
- 当前仓库尚无前端工程，本轮只补齐任务队列，不创建前端项目。

## 2026-04-28 00:50 - Expand task backlog from requirements

### 完成内容
- 按需求分析文档 V0.2 的 FR-001 至 FR-015、CLI 能力、非功能需求、权限需求、异常场景和第一阶段交付物，扩展 `TASKS.md`。
- 按架构设计文档 V0.1 的模块边界、安全审计、可观测性、测试策略和验收映射，把大需求拆成单轮可验证任务。
- 保留已完成的 P0 任务状态；FR-011 Browser Use 自动录入仅记录为第一阶段 Won't-have 边界和后续评估任务，不实现自动录入。

### 修改文件
- `TASKS.md`
- `WORKLOG.md`

### 验证结果
- 已通过：
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - pytest 32 个用例通过
    - `git diff --check` 通过

### 假设
- 用户消息中的 `TASKL` 理解为 `TASKS.md` 任务清单。
- 本轮只写入任务队列，不修改业务代码。

## 2026-04-28 00:45 - Harden backend health check coverage

### 完成内容
- 为 `/health` 新增独立 API 测试文件，明确覆盖健康检查接口返回 `200` 和 `{"status": "ok"}`。
- 确认统一验证脚本 `./scripts/verify.sh` 会运行 pytest，因此会覆盖新增的健康检查测试。
- 记录后端本地启动命令：`uv run uvicorn trms_backend.main:app --reload`。

### 修改文件
- `tests/test_health_api.py`
- `TASKS.md`
- `WORKLOG.md`

### 验证结果
- 已通过：
  - `uv run pytest tests/test_tasks_api.py::test_health_check`
  - `uv run pytest tests/test_health_api.py`
  - `./scripts/verify.sh`

### 假设
- 当前 `/health` 的语义是后端进程级健康检查，只保证应用可响应，不额外执行数据库连通性探测。

### 后续建议
- 下一轮可继续处理 `TASKS.md` 中“梳理当前 API 能力清单”，只记录现有接口与 FR-001 至 FR-015 的覆盖关系，不改业务逻辑。

## 2026-04-28 00:42 - Confirm project stack and run commands

### 完成内容
- 确认当前代码切片是 Python 3.12 后端项目，使用 FastAPI、Pydantic、SQLAlchemy、uvicorn、pytest 和 uv。
- 确认后端应用入口为 `trms_backend.main:app`，应用工厂为 `trms_backend.main:create_app`。
- 确认默认数据库为本地 SQLite `sqlite:///./trms.db`，可通过 `DATABASE_URL` 切换到 PostgreSQL 连接。
- 确认本地启动命令为 `uv run uvicorn trms_backend.main:app --reload`。
- 确认测试命令为 `uv run pytest`，统一基础验证命令为 `./scripts/verify.sh`。
- 确认 `./scripts/verify.sh` 当前会运行 Python 编译检查、pytest，并执行 `git diff --check`；其他语言检查仅在对应工程文件存在时启用。

### 修改文件
- `TASKS.md`
- `WORKLOG.md`

### 验证结果
- 已通过：
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - pytest 31 个用例通过
    - `git diff --check` 通过

### 假设
- 当前 `pyproject.toml` 和 README 中声明的 uv 工作流是本项目现阶段的标准本地开发方式。
- 本轮只完成技术栈与启动方式确认，不实现任何新业务功能。

### 后续建议
- 下一轮可继续处理 `TASKS.md` 中“固化后端健康检查验证”，为 `/health` 接口补齐明确测试覆盖并记录后端启动命令。

## 2026-04-28 00:38 - Run Codex nightly with full filesystem access

### 完成内容
- 按要求调整 `scripts/codex-nightly.sh`，夜间 Codex 子进程改为使用 `danger-full-access` 沙箱策略。
- 保留 `--ask-for-approval never`，继续满足无人值守执行需求。

### 修改文件
- `scripts/codex-nightly.sh`
- `WORKLOG.md`

### 验证结果
- 已通过：
  - `codex --ask-for-approval never exec --sandbox danger-full-access --help`
  - `bash -n scripts/codex-nightly.sh`
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - pytest 31 个用例通过
    - `git diff --check` 通过

### 假设
- 用户所说“full access”对应当前 Codex CLI 的 `--sandbox danger-full-access`，不是跳过审批与沙箱的 `--dangerously-bypass-approvals-and-sandbox`。
- 工作区开始时已有 `.gitignore`、`TASKS.md`、`WORKLOG.md`、`scripts/verify.sh` 和 `.codex` 的未提交改动；除本次追加日志外，本轮不处理这些既有改动。

## 2026-04-28 00:37 - Fix Codex nightly approval flag

### 完成内容
- 修复 `scripts/codex-nightly.sh` 中 Codex CLI 参数顺序。
- 当前 Codex CLI 的 `--ask-for-approval` 是顶层 `codex` 参数，不能放在 `exec` 子命令之后。

### 修改文件
- `scripts/codex-nightly.sh`
- `WORKLOG.md`

### 验证结果
- 已复现：
  - `codex exec --ask-for-approval never --help` 失败，报错 `unexpected argument '--ask-for-approval' found`
- 已通过：
  - `codex --ask-for-approval never exec --help`
  - `bash -n scripts/codex-nightly.sh`
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - pytest 31 个用例通过
    - `git diff --check` 通过

### 假设
- 夜间脚本仍应保持无人值守执行语义，即审批策略为 `never`，沙箱仍为 `workspace-write`。

### 后续建议
- 如果后续 Codex CLI 再调整参数结构，应优先用 `codex exec --help` 和 `codex --help` 同时确认顶层参数与子命令参数边界。

## 2026-04-28 00:16 - Bootstrap Codex worker framework

### 完成内容
- 建立项目级代理工作规范，约束后续 Codex 每轮只完成一个最小可验证任务。
- 根据 README、需求文档和架构文档生成第一批任务队列。
- 建立工作日志和阻塞问题记录文件。
- 建立统一验证脚本和夜间无人值守执行脚本。
- 将 `.codex-nightly/` 加入忽略规则，避免夜间日志进入版本库。

### 修改文件
- `AGENTS.md`
- `TASKS.md`
- `WORKLOG.md`
- `BLOCKERS.md`
- `scripts/verify.sh`
- `scripts/codex-nightly.sh`
- `.gitignore`

### 验证结果
- 已通过：
  - `bash -n scripts/verify.sh`
  - `bash -n scripts/codex-nightly.sh`
  - `git diff --check`
  - `./scripts/verify.sh`
- 说明：首次在沙箱内运行 `./scripts/verify.sh` 时，`uv` 无法写入 `/home/gsh/.cache/uv` 导致失败；随后按权限流程在沙箱外重跑，通过 Python 编译检查、pytest 31 个用例和 `git diff --check`。

### 假设
- 当前仓库是 Python 3.12 后端项目，使用 FastAPI、SQLAlchemy、pytest 和 uv。
- README 中的本地验证命令 `uv run pytest` 是当前主测试入口。
- 夜间执行由外部调度器重复启动 `scripts/codex-nightly.sh`，脚本本身只负责单次进程内多轮循环。
- 当前不引入新的业务依赖，也不实现新业务功能。

### 后续建议
- 下一轮优先执行 `TASKS.md` 中“确认项目技术栈和启动方式”，把当前技术栈、入口、测试命令和需求覆盖状态记录清楚。

## 2026-04-28 12:14 - Establish Telegram account binding model

### 完成内容
- 新增 `src/trms_backend/domain/telegram_bindings.py`，建立 Telegram 账号绑定领域模型、冲突约束和提交身份解析边界：
  - 绑定以 `telegram_user_id` 作为稳定身份键；
  - 同一 Telegram 账号只能绑定一个成员，同一成员也只能绑定一个 Telegram 账号，冲突时显式返回错误；
  - 未绑定账号解析结果显式返回 `pending_assignment`，为后续 Telegram 入站接入复用现有待归属材料流程提供边界。
- 新增 `src/trms_backend/infrastructure/models.py` 与 `src/trms_backend/infrastructure/repositories.py` 中的持久化实现，落地 `telegram_account_bindings` 表和 SQLAlchemy 仓储。
- 新增 `src/trms_backend/api/telegram_bindings.py` 并接入 `src/trms_backend/main.py`：
  - `PUT /api/telegram-bindings/{telegram_user_id}` 用于绑定账号；
  - `GET /api/telegram-bindings/{telegram_user_id}` 用于查询绑定；
  - `GET /api/telegram-bindings/{telegram_user_id}/submission-identity` 用于解析“已绑定 / 待归属”提交身份。
- 新增 `tests/test_telegram_bindings_api.py`，覆盖绑定成功、未绑定解析为待归属、成员冲突拒绝三条主路径。
- 将 `TASKS.md` 中“建立 Telegram 账号绑定模型”标记为已完成。

### 根因
- 上一轮虽然已经把 Web、CLI、Telegram、邮件的材料提交主链路统一到 `MaterialSubmissionService`，但 Telegram 渠道仍缺少最基础的“外部账号 -> 成员身份”绑定层。
- 如果不先固定这一层，后续 Telegram 入站只能在渠道代码里临时拼接成员识别逻辑，既会破坏“渠道层只接入、不复制业务规则”的架构约束，也无法稳定落到“未绑定即待归属”的需求边界。

### 修改文件
- `src/trms_backend/domain/telegram_bindings.py`
- `src/trms_backend/api/telegram_bindings.py`
- `src/trms_backend/infrastructure/models.py`
- `src/trms_backend/infrastructure/repositories.py`
- `src/trms_backend/main.py`
- `tests/test_telegram_bindings_api.py`
- `TASKS.md`
- `WORKLOG.md`

### 验证结果
- 已通过：
  - `uv run pytest tests/test_telegram_bindings_api.py`
  - `uv run pytest tests/test_material_submission_service.py tests/test_materials_api.py`
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - pytest 210 个用例通过
    - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过
    - `git diff --check` 通过

### 假设
- 当前将 Telegram 账号绑定的稳定键保守定义为 `telegram_user_id`，而不是可变的 `username`；`telegram_username` 仅作为可选展示信息保存。
- 本轮只建立绑定模型和解析边界，不接入真实 Telegram Bot、Webhook、Bot Token 管理或消息收取流程；因此仓库和日志中不新增任何 Telegram token。
- 当前没有独立成员主数据表，因此成员身份仍沿用既有 `member_id` 字符串边界，不在本轮扩展到统一认证或权限上下文。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“增加 Telegram 材料提交接入占位”，直接复用本轮的 `submission-identity` 解析边界，把已绑定账号导入统一材料提交流程，未绑定账号导入 `pending_assignment` 路径。

## 2026-04-28 14:49 - Split oversized async execution task

### 完成内容
- 将 `TASKS.md` 中原本合并的“建立异步识别和导出任务执行机制”拆分为三个更小的任务：
  - 共享异步运行模式与 worker 入口；
  - 识别任务异步执行与重试可观测性；
  - 导出任务异步执行与产物状态查询。
- 保留每个子任务各自的 Done when，避免单轮同时改动运行配置、识别链、导出链和幂等测试。
- 将原始总任务替换为已完成的拆分记录，明确本轮只调整任务边界，不修改业务代码。

### 根因
- 当前仓库虽然已经有识别手动执行入口、导出任务记录和部分状态流转骨架，但还没有共享 worker 运行模式、统一执行入口和识别/导出两条链路的完整异步闭环。
- 原任务把运行模式配置、识别执行、导出执行、重试可观测性和幂等验证捆绑在一起，超出了单轮“最小可验证任务”的范围；如果直接实现，改动面会同时跨 `runtime_config`、API、领域模型、仓储和测试，违背仓库要求的聚焦改动原则。

### 修改文件
- `TASKS.md`
- `WORKLOG.md`

### 验证结果
- 已通过：
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - pytest 246 个用例通过
    - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过
    - `git diff --check` 通过

### 假设
- 下一轮应按新的任务顺序，先处理“建立异步任务共享运行模式与执行入口”，再分别落地识别链和导出链。
- 当前 `POST /api/recognition-tasks/{id}/execute` 以及导出任务状态接口仍可作为后续拆分的落脚点，但本轮不对它们的语义做任何变更。

### 后续建议
- 下一轮先收敛共享运行模式和 worker 命令入口，避免识别与导出各自发散出不同的异步执行配置。

## 2026-04-28 18:35 - Record recognition result and manual correction audit logs

### 完成内容
- 为识别结果与人工更正新增统一审计写入：
  - 新增 `src/trms_backend/application/recognition_audit.py`，集中生成识别结果审计和人工更正差异审计；
  - `RecognitionPreparationService` 在真实识别执行完成或失败后写入 `record_recognition_result` 审计，覆盖 API 手动执行和 worker 异步执行两条链路；
  - `PATCH /api/recognition-tasks/{id}/status` 在直接写入识别结果或失败原因时补写识别结果审计；
  - `POST /api/materials/{material_id}/invoice` 在人工录入/更正发票字段后写入 `apply_manual_recognition_corrections` 审计，并记录字段级前后差异摘要。
- 审计明细只记录字段名、来源、状态、置信度、失败原因和人工更正前后摘要，不写入 `raw_response`、原始文件内容或完整文档文本。
- 补充测试覆盖：
  - `tests/test_recognition_tasks_api.py` 断言手动写入识别结果后存在识别审计；
  - `tests/test_recognition_async_jobs.py` 断言 worker 异步识别失败时存在系统审计且不暴露 `raw_response`；
  - `tests/test_invoices_api.py` 断言人工更正会写入差异审计，并能追踪前后字段变化。
- 将 `TASKS.md` 中“记录识别和人工更正审计”标记为已完成。

### 根因
- 上一轮已经建立了统一 `audit_logs` 骨架，并接入了材料提交、认领和删除标记，但识别链路仍缺少正式审计写入点。
- 这会导致两类关键事实无法追溯：
  - 识别任务何时生成了什么结果、由谁触发或由哪个系统执行器写入；
  - 管理员/成员人工覆盖识别字段时，哪些字段从什么值改成了什么值。
- 如果继续只依赖 `recognition_tasks.manual_corrections` 内部历史，而不把结果和差异接到统一审计仓储，就无法和其他审计记录共享查询边界、请求 ID 和结果语义，也不满足当前任务对“更正摘要可追溯”的要求。

### 修改文件
- `src/trms_backend/application/recognition_audit.py`
- `src/trms_backend/application/recognition_preparation.py`
- `src/trms_backend/api/recognitions.py`
- `src/trms_backend/api/invoices.py`
- `src/trms_backend/main.py`
- `src/trms_backend/__main__.py`
- `tests/test_recognition_tasks_api.py`
- `tests/test_recognition_async_jobs.py`
- `tests/test_invoices_api.py`
- `TASKS.md`
- `WORKLOG.md`

### 验证结果
- 已通过：
  - `uv run pytest tests/test_recognition_tasks_api.py tests/test_recognition_async_jobs.py tests/test_invoices_api.py`
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic 升降级验证通过
    - pytest 305 个用例通过
    - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过
    - Docker Compose 配置检查通过
    - `git diff --check` 通过

### 假设
- worker 异步识别路径当前保守记录为系统操作者 `system:recognition-worker`，用于区分人工触发和后台执行。
- 只有真正写入识别结果或失败原因的状态更新才记为“识别结果审计”；不携带 `result`/`failure` 的纯状态切换不单独记这类审计，避免把无结果的管理动作伪装成识别产出。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“记录分摊和确认审计”，继续沿用统一 `audit_logs` 仓储和结果语义，不要在分摊/确认 API 内另起一套日志格式。

## 2026-04-28 19:09 - Establish request ID logging context

### 完成内容
- 为 API 请求补齐 `request_id` 透传与日志上下文：
  - 新增 `src/trms_backend/request_context_logging.py`，使用 `ContextVar` 绑定当前请求的 `request_id`，并通过 `LogRecordFactory` 为日志记录补充 `request_id` 字段；
  - `src/trms_backend/main.py` 中的 HTTP 中间件改为在请求入口统一生成或透传 `X-Request-ID`，并在请求结束后清理上下文；
  - `src/trms_backend/api/error_responses.py` 支持优先透传合法入站 `X-Request-ID`，否则回退到服务端生成的 `req_*`；
  - 为未处理异常增加统一 500 错误处理，错误响应继续返回标准化 `request_id`，同时记录带 `request_id` 的错误日志。
- 新增 API 测试覆盖：
  - 断言客户端自带 `X-Request-ID` 时，404 错误响应会原样透传；
  - 断言未处理异常会返回标准化 500 错误响应，并调用带 `request_id` 的错误日志。
- 将 `TASKS.md` 中“建立请求 ID 日志上下文”标记为已完成。

### 根因
- 仓库此前已经在错误响应体、响应头和多处审计日志里生成 `request_id`，但它还只是“响应字段”，没有形成真正的请求级上下文。
- 具体缺口有两处：
  - API 不会透传调用方提供的 `X-Request-ID`，导致外部调用链无法稳定对齐后端请求；
  - 统一错误处理没有把 `request_id` 绑定到错误日志，出现 500 或后端异常时，日志与响应之间缺少可直接关联的键。
- 如果继续维持现状，请求审计和错误排查仍需靠时间与路径人工拼接，达不到当前任务要求的最小可追溯性。

### 修改文件
- `src/trms_backend/request_context_logging.py`
- `src/trms_backend/api/error_responses.py`
- `src/trms_backend/main.py`
- `tests/test_api_error_responses.py`
- `TASKS.md`
- `WORKLOG.md`

### 验证结果
- 已通过：
  - `uv run pytest tests/test_api_error_responses.py`
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic 升降级验证通过
    - pytest 312 个用例通过
    - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过
    - Docker Compose 配置检查通过
    - `git diff --check` 通过

### 假设
- 本轮对客户端透传的 `X-Request-ID` 采用保守白名单格式，只接受长度不超过 64 且由字母、数字、`.`、`_`、`-` 组成的值；非法值回退为服务端生成的 `req_*`，避免把异常 header 值直接写入响应头和日志。
- “错误日志包含 `request_id`” 当前先收敛到统一未处理异常日志，不额外把全部 4xx 业务拒绝都升级为错误级别日志，避免把正常用户输入错误误记为服务端故障。

### 后续建议
- 下一轮按顺序处理 `TASKS.md` 中“增加基础指标边界”，优先为上传、识别、校验和导出建立最小指标抽象，不要直接引入重量级监控组件。

## 2026-04-28 19:51 - Execute backup and object-storage restore drill

### 完成内容
- 新增 `scripts/backup-restore-drill.sh`，固化一套可重复执行的恢复演练流程：
  - 生成隔离 `.env`；
  - 按 `deploy/docker-compose.yml` 拉起 `postgres`、`minio`、`api`、`web`、`reverse-proxy` 和 `worker`；
  - 通过真实 API 创建管理员、成员、任务并上传样本材料；
  - 执行 PostgreSQL 逻辑备份、MinIO bucket 镜像备份；
  - 销毁卷后恢复数据库与对象存储对象，再核对材料记录、`storage_key` 对象和材料审计记录。
- 修复两处直接阻塞本次演练的部署基线问题：
  - `deploy/docker-compose.yml` 中 `minio` 健康检查原先调用镜像内不存在的 `wget`，导致 `minio-init` 永远等待；本轮改为使用镜像内实际存在的 `curl`。
  - `deploy/Dockerfile.api` 原先未把 `/app/src` 加入 `PYTHONPATH`，导致容器内 `python -m trms_backend` 启动失败；本轮补齐 `PYTHONPATH=/app/src`。
- 演练脚本中补齐了三类运行时细节，确保后续可重复执行：
  - 启动前显式 `compose build`，避免复用旧镜像掩盖部署问题；
  - `minio/mc` 容器显式覆盖 entrypoint 为 `/bin/sh`；
  - `mc` 镜像运行时显式设置 `MC_CONFIG_DIR=/tmp/.mc` 并以宿主机 UID/GID 写入挂载目录，避免对象备份目录清理失败。
- 将 `TASKS.md` 中“执行数据库与对象存储备份恢复演练”标记为已完成。

### 根因
- 当前仓库虽然已经补了部署文档和恢复策略文档，但在真正按 Compose 基线执行恢复演练前，仍有两处未被验证脚本覆盖的部署缺陷：
  - `minio` 健康检查命令与镜像内容不一致；
  - API 镜像运行时找不到 `src/` 下的应用模块。
- 如果不先做这次真实演练，这两处问题会一直藏在“文档完整、配置可读”表象下，直到上线前或故障恢复现场才暴露。

### 修改文件
- `deploy/docker-compose.yml`
- `deploy/Dockerfile.api`
- `scripts/backup-restore-drill.sh`
- `TASKS.md`
- `WORKLOG.md`

### 演练命令
- 主命令：
  - `./scripts/backup-restore-drill.sh`
- 脚本内部执行的关键命令：
  - `docker compose --project-name trms-backup-drill --env-file <temp-env> -f deploy/docker-compose.yml up -d postgres redis minio`
  - `docker compose --project-name trms-backup-drill --env-file <temp-env> -f deploy/docker-compose.yml up minio-init`
  - `docker compose --project-name trms-backup-drill --env-file <temp-env> -f deploy/docker-compose.yml build api worker web migrate`
  - `docker compose --project-name trms-backup-drill --env-file <temp-env> -f deploy/docker-compose.yml run --rm migrate`
  - `docker compose --project-name trms-backup-drill --env-file <temp-env> -f deploy/docker-compose.yml exec -T postgres pg_dump -U trms -d trms -Fc`
  - `docker compose --project-name trms-backup-drill --env-file <temp-env> -f deploy/docker-compose.yml exec -T postgres pg_restore -U trms -d trms --clean --if-exists`
  - `docker run --rm --network trms-backup-drill_default -v <backup-dir>:/backup --entrypoint /bin/sh minio/mc:latest -ec 'mc mirror ...'`

### 演练结果
- 已通过：
  - `./scripts/backup-restore-drill.sh`
  - 首次恢复前核对：
    - `task_count_before=1`
    - `material_count_before=1`
    - `audit_count_before=1`
    - `object_count_before=1`
  - 恢复后核对：
    - `task_count_after=1`
    - `material_count_after=1`
    - `audit_count_after=1`
    - `object_count_after=1`
    - `material_audit=submit_material|succeeded|req_8c3bd401c54e43bcb05d67c2662b6620`
  - 样本核对：
    - 恢复前后 `material_id` 一致；
    - 恢复前后 `storage_key` 一致；
    - MinIO 中样本对象内容可读；
    - 恢复后 `worker` 能在当前基线上启动。
  - 耗时：
    - `duration_seconds=66`

### 验证结果
- 已通过：
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic 升降级验证通过
    - pytest 314 个用例通过
    - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过
    - Docker Compose 配置检查通过
    - `git diff --check` 通过

### 假设
- 本轮沿用第一阶段生产边界：数据库使用 PostgreSQL，原始材料存储使用 S3 兼容对象存储；不为生产环境补充本地目录恢复方案。
- 演练样本保守选择“原始材料对象”而不是“导出产物对象”，因为当前任务 Done when 允许二选一，且原始材料优先级更高。
- 为避免恢复核对阶段被识别 worker 异步写入新审计干扰，脚本在完成数据库/对象/材料审计核对后才启动 `worker`。

### 未覆盖风险
- 本轮只验证了单任务、单材料、单对象的最小恢复闭环，未覆盖多任务、多成员、大体量对象和长时间运行下的恢复耗时。
- 本轮没有额外抽样导出产物恢复；当前结论只证明“数据库 + 原始材料对象”闭环成立，不代表 `_exports/` 前缀已经完成同等强度验证。
- 脚本运行过程中，`mc find` 会输出一条 `Requested path `` not found` 的噪音日志，但不影响对象镜像、恢复和最终计数核对；后续可单独收敛这条输出。

### 后续建议
- 下一轮优先补“增加规则层单元测试覆盖矩阵”，继续按 `TASKS.md` 顺序推进。
- 如果后续需要把恢复演练纳入上线清单，建议把 `scripts/backup-restore-drill.sh` 再拆成“造数 + 备份 + 恢复 + 报告”四段，便于共享环境按需复用。

## 2026-04-29 04:27 - Add permission regression coverage for forbidden access paths

### 完成内容
- 新增 `tests/test_permission_regressions.py`，集中补齐一组权限越权回归测试，覆盖五类关键敏感路径：
  - 任务内成员不能预览其他成员原始材料内容；
  - 非任务成员不能查看无关任务的费用明细；
  - 非任务成员不能查看无关发票的确认记录；
  - 普通成员不能访问任务导出产物下载接口；
  - 普通成员不能进入管理员复核摘要入口。
- 以上断言全部通过统一错误响应校验，明确要求返回 `403 forbidden`，而不是靠 `404` 或空结果掩盖越权。
- 将 `TASKS.md` 中“增加权限越权回归测试”标记为已完成。

### 根因
- 仓库此前已经在材料预览、费用明细、导出管理、复核摘要等单点文件中存在部分权限测试，但覆盖是分散的，且对“越权时必须显式返回 403”这一上线前安全边界没有形成集中回归。
- 对确认记录这类高敏感接口，现有测试主要覆盖正常读取和成员视角过滤，缺少“无关成员直接被拒绝”的显式回归；如果后续改动把拒绝错误退化成 `404`、空列表或静默过滤，现有测试不一定能第一时间发现。

### 修改文件
- `tests/test_permission_regressions.py`
- `TASKS.md`
- `WORKLOG.md`

### 验证结果
- 已通过：
  - `uv run pytest tests/test_permission_regressions.py`
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic 升降级验证通过
    - pytest 387 个用例通过
    - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过
    - Docker Compose 配置检查通过
    - `git diff --check` 通过

### 假设
- 本轮将“无关确认记录不可访问”保守解释为“非任务成员不能读取该任务发票确认记录”，不额外收紧当前已存在的“发票提交人可见与本人提交发票相关确认记录”边界。
- 本轮只补回归测试，不修改业务权限语义；若后续产品要求继续收紧同任务成员之间的确认记录可见性，应拆成单独权限任务处理。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“增加材料上传集成测试”，优先覆盖批量部分成功、重复文件 hash 和统一提交流程入口。

## 2026-04-29 05:44 - Support recursive directory upload in CLI submit

### 完成内容
- 为 `src/trms_cli/cli.py` 的 `submit` 命令补齐显式目录参数递归展开能力：
  - 顶层参数仍按用户传入顺序处理；
  - 目录内部按文件名排序做深度优先递归展开，保证上传顺序稳定可测试；
  - 递归过程中发现的本地失败继续并入现有 `MaterialUploadBatchResult`，沿用 `success` / `partial_success` / `failed` 语义和退出码。
- 明确目录递归上传的本地边界：
  - 递归上传不跟随符号链接；目录内或作为目录参数传入的符号链接会以 `local_symlink_not_supported` 进入逐项失败列表；
  - 目录内不支持的文件类型继续走现有本地预检查失败，和服务端批量结果一起汇总输出；
  - 空目录不会被伪装成“成功上传 0 个文件”，而是显式返回 `local_directory_empty` 本地失败。
- 补充 CLI 回归测试：
  - `tests/test_cli_submit.py` 新增目录递归上传用例，覆盖遍历顺序、符号链接不跟随和不支持文件类型并入 `partial_success`；
  - 新增空目录失败用例，确保不会误触发上传请求。
- 将 `TASKS.md` 中“实现 CLI 目录递归上传”标记为已完成。

### 根因
- 现有 CLI `submit` 只接受显式文件路径列表，`prepare_upload_files` 会逐个把参数当作文件加载，本地目录参数会直接触发 `local_file_invalid`。
- 这与任务要求不一致：成员在本地通常按比赛/票据目录整理材料，如果 CLI 不能直接递归展开目录，就需要手动枚举每个文件，既破坏批量提交流程，也让已有的“逐文件部分成功”语义无法覆盖目录场景。
- 同时，目录递归如果不先明确顺序和符号链接边界，后续实现很容易出现两类问题：
  - 遍历顺序不稳定，导致测试和实际批量结果不可预测；
  - 跟随符号链接把重复文件、目录环或意外路径带进上传主链路，扩大本地敏感文件暴露面。

### 修改文件
- `src/trms_cli/cli.py`
- `tests/test_cli_submit.py`
- `TASKS.md`
- `WORKLOG.md`

### 验证结果
- 已通过：
  - `uv run pytest tests/test_cli_submit.py`
  - `uv run pytest tests/test_cli_argument_parsing.py`
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic 升降级验证通过
    - pytest 420 个用例通过
    - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过
    - Docker Compose 配置检查通过
    - `git diff --check` 通过

### 假设
- 本轮将“显式目录参数的递归展开”保守解释为只增强 CLI 本地参数处理，不修改后端上传 API、材料模型或服务端批量结果格式。
- “是否跟随符号链接”当前收敛为“递归目录上传一律不跟随”；显式普通文件参数保持原有行为，不额外重写单文件上传路径。
- 目录内部遍历顺序当前定义为“按文件名排序的深度优先递归展开”；只要后续不改变这个顺序，CLI 的逐文件结果和测试都应保持稳定。

### 未覆盖风险
- 本轮没有额外补目录读取权限异常、设备文件等非常规本地路径的专门测试；当前实现会把这类条目按本地失败并入结果，但仍主要依赖静态逻辑覆盖。
- 本轮只验证了 CLI 本地展开和结果汇总，没有新增真实后端集成场景；服务端仍沿用既有多文件上传语义。

### 后续建议
- 下一轮按 `TASKS.md` 顺序处理“评估自动生成成员补材料消息”，保持评估任务和实现任务分离，不要顺手扩展通知模块。
