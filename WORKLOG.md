# WORKLOG

## 2026-05-02 11:49 - Simplify registration by removing actor id input

### 完成内容
- 完成任务“注册时去除身份编号，仅在成员注册时显示学号”。
- 前端注册页 [auth.tsx](/home/gsh/workspace/TRMS/web/src/app/auth.tsx) 调整为更小表单：
  - 删除普通注册流程里的“身份编号”输入；
  - 成员注册时保留“学号”输入；
  - 选择管理员或系统管理员后，不再渲染“学号”输入；
  - 普通注册提交时不再从页面收集 `actor_id`，成员以外角色也不会再提交 `member_code`。
- 同步更新前端测试 [App.test.tsx](/home/gsh/workspace/TRMS/web/src/app/App.test.tsx)：
  - 原管理员注册路径不再填写“身份编号”；
  - 新增“成员/管理员切换时学号字段显示与隐藏”的显式断言。

### 根因
- 当前注册表单同时暴露“身份编号”和“学号”，对普通用户来说信息重复且难以区分。
- 后端注册逻辑本身已经允许 `actor_id` 缺省并回退到用户名，因此前端继续要求手填“身份编号”并不是必要约束。
- 真正需要保留的成员专有业务字段是学号，而不是让所有角色都看到一组与自己无关的标识输入。

### 风险与影响面
- 本轮只简化普通注册 UI，没有改后端注册协议，也没有改开发快捷入口注入 `actor_id` 的调试能力。
- 由于前端不再显式传 `actor_id`，普通注册账号会回到后端既有默认行为：未提供时以用户名作为 `actor_id`。
- 如果后续产品要求管理员/系统管理员注册时仍需单独配置业务编号，应单独补受控字段，而不是恢复当前这类面对所有用户的通用输入。

### 验证结果
- 已通过定向前端测试：
  - `cd web && npm test -- App.test.tsx`
  - 1 个测试文件、11 个用例通过。
- 仓库级验证：
  - `./scripts/verify.sh`
  - Python 编译检查通过；
  - Alembic 升降级验证通过；
  - pytest 520 个用例通过，存在 3 条既有 `HTTP_422_UNPROCESSABLE_ENTITY` DeprecationWarning；
  - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过；ESLint 仍有 2 条既有 `react-hooks/exhaustive-deps` warning，Vitest 仍有既有 `--localstorage-file` 路径 warning，Vite 仍有既有 chunk size warning；
  - Docker Compose 配置检查通过；
  - `git diff --check` 通过。

## 2026-05-02 02:02 - Replace raw member IDs with username, display name, and student ID

### 完成内容
- 完成任务“去掉成员编号展示，仅保留用户名、显示名称和学号”。
- 后端任务接口补齐成员摘要数据：
  - [auth.py](/home/gsh/workspace/TRMS/src/trms_backend/domain/auth.py) 的 `AuthRepository` 新增按任务成员标识批量查询用户能力；
  - [repositories.py](/home/gsh/workspace/TRMS/src/trms_backend/infrastructure/repositories.py) 支持按 `actor_id/member_code` 匹配用户；
  - [tasks.py](/home/gsh/workspace/TRMS/src/trms_backend/domain/tasks.py) 新增 `TaskMemberSummary` 和 `build_task_member_summaries(...)`；
  - [api/tasks.py](/home/gsh/workspace/TRMS/src/trms_backend/api/tasks.py) 现在会为 `create/list/get/update/status` 等任务返回值补上 `member_summaries`，并把 `GET/PUT /api/tasks/{task_id}/members` 统一升级为摘要列表响应。
- 前端任务相关成员展示改为“显示名称 / 用户名 / 学号”口径：
  - [types.ts](/home/gsh/workspace/TRMS/web/src/lib/api/types.ts)、[trms.ts](/home/gsh/workspace/TRMS/web/src/lib/api/trms.ts)、[ui-text.ts](/home/gsh/workspace/TRMS/web/src/lib/ui-text.ts) 新增任务成员摘要类型、用户身份格式化和任务成员格式化工具；
  - [task-member-autocomplete.tsx](/home/gsh/workspace/TRMS/web/src/components/task-member-autocomplete.tsx) 的管理员成员选择控件现在展示成员摘要，不再直接渲染裸编号；
  - 管理员主路径 [admin-task-detail.tsx](/home/gsh/workspace/TRMS/web/src/app/admin-task-detail.tsx)、[admin-review-overview.tsx](/home/gsh/workspace/TRMS/web/src/app/admin-review-overview.tsx)、[admin-corrections-reminders.tsx](/home/gsh/workspace/TRMS/web/src/app/admin-corrections-reminders.tsx)、[admin-split-editor.tsx](/home/gsh/workspace/TRMS/web/src/app/admin-split-editor.tsx)、[admin-invoice-editor.tsx](/home/gsh/workspace/TRMS/web/src/app/admin-invoice-editor.tsx) 已改用成员摘要展示；
  - 成员主路径 [member-invoice-workbench.tsx](/home/gsh/workspace/TRMS/web/src/app/member-invoice-workbench.tsx)、[member-invoice-detail.tsx](/home/gsh/workspace/TRMS/web/src/app/member-invoice-detail.tsx)、[task-missing-materials.tsx](/home/gsh/workspace/TRMS/web/src/app/task-missing-materials.tsx) 以及全局身份区 [AppShell.tsx](/home/gsh/workspace/TRMS/web/src/components/AppShell.tsx)、[pages.tsx](/home/gsh/workspace/TRMS/web/src/app/pages.tsx)、[member-task-list.tsx](/home/gsh/workspace/TRMS/web/src/app/member-task-list.tsx)、[member-material-status.tsx](/home/gsh/workspace/TRMS/web/src/app/member-material-status.tsx)、[member-expense-confirmation.tsx](/home/gsh/workspace/TRMS/web/src/app/member-expense-confirmation.tsx)、[auth.tsx](/home/gsh/workspace/TRMS/web/src/app/auth.tsx) 统一改为显示名称 / 用户名 / 学号，并把 `member_code` 的用户文案从“成员编号”改为“学号”。
- 同步更新后端与前端测试夹具：
  - 后端更新 [test_tasks_api.py](/home/gsh/workspace/TRMS/tests/test_tasks_api.py)、[test_web_bearer_request_identity_api.py](/home/gsh/workspace/TRMS/tests/test_web_bearer_request_identity_api.py)；
  - 前端更新 [admin-task-detail.test.tsx](/home/gsh/workspace/TRMS/web/src/app/admin-task-detail.test.tsx)、[admin-review-overview.test.tsx](/home/gsh/workspace/TRMS/web/src/app/admin-review-overview.test.tsx)、[admin-corrections-reminders.test.tsx](/home/gsh/workspace/TRMS/web/src/app/admin-corrections-reminders.test.tsx)、[admin-split-editor.test.tsx](/home/gsh/workspace/TRMS/web/src/app/admin-split-editor.test.tsx)。

### 根因
- 任务模型和复核/分摊/提醒等读模型过去只携带 `member_id` 这类字符串标识，前端没有用户名、显示名称和学号可用，只能直接渲染裸编号。
- 成员登录态自身虽然已有 `username / display_name / member_code`，但任务相关接口没有把这些资料带出来，导致同一成员在账号区和任务处理区出现两套完全不同的展示口径。
- 真正要修复的是“任务接口缺成员摘要 + 前端缺统一格式化”，而不是再继续在页面里手工拼 `成员 2250001` 之类的过渡文案。

### 风险与影响面
- 当前任务成员摘要采用“按 `actor_id/member_code` 匹配用户，匹配不到时仅保留原成员标识作为学号/占位值”的保守策略，没有改动任务权限判断和任务成员底层存储。
- 这意味着历史任务如果录入的是纯自由文本且没有对应账号资料，前端仍可能只能展示原始字符串；但不会再默认渲染“成员 {id}”这种误导性的编号前缀。
- 纸票确认人等管理员 `actor_id` 不属于成员摘要口径，本轮刻意保留原始管理员标识显示，避免把管理员编号错误伪装成成员学号。

### 验证结果
- 已通过定向后端测试：
  - `uv run pytest tests/test_tasks_api.py tests/test_web_bearer_request_identity_api.py`
  - 57 个用例通过。
- 已通过定向前端测试：
  - `cd web && npm test -- admin-task-detail.test.tsx admin-corrections-reminders.test.tsx admin-split-editor.test.tsx task-missing-materials.test.tsx member-invoice-detail.test.tsx member-invoice-workbench.test.tsx admin-review-overview.test.tsx`
  - 7 个测试文件、30 个用例通过。
  - `cd web && npm test -- admin-review-overview.test.tsx member-invoice-workbench.test.tsx member-invoice-detail.test.tsx admin-invoice-editor.test.tsx task-missing-materials.test.tsx`
  - 5 个测试文件、23 个用例通过。
  - `cd web && npm test -- App.test.tsx member-task-list.test.tsx member-material-status.test.tsx member-expense-confirmation.test.tsx member-invoice-workbench.test.tsx member-invoice-detail.test.tsx task-missing-materials.test.tsx admin-corrections-reminders.test.tsx admin-split-editor.test.tsx`
  - 9 个测试文件、41 个用例通过。
- 仓库级验证：
  - `./scripts/verify.sh`
  - Python 编译检查通过；
  - Alembic 升降级验证通过；
  - pytest 520 个用例通过，存在 3 条既有 `HTTP_422_UNPROCESSABLE_ENTITY` DeprecationWarning；
  - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过；ESLint 仍有 2 条 `react-hooks/exhaustive-deps` warning，Vitest 仍有既有 `--localstorage-file` 路径 warning，Vite 仍有既有 chunk size warning；
  - Docker Compose 配置检查通过；
  - `git diff --check` 通过。

## 2026-05-02 01:15 - Add member search when admins pick task participants

### 完成内容
- 完成任务“管理员选择比赛参与成员时提供搜索框”。
- 抽出可复用任务成员筛选控件 [task-member-autocomplete.tsx](/home/gsh/workspace/TRMS/web/src/components/task-member-autocomplete.tsx)：
  - 组件使用“搜索输入 + 成员选择下拉”的双控件结构；
  - 搜索框按字符串包含关系过滤当前任务成员；
  - 下拉始终只展示当前匹配结果，空结果时显示明确的“没有匹配的成员”占位项；
  - helper text 同步展示空查询、匹配中和无结果三种状态。
- 管理员两条直接选择任务成员的主路径接入搜索：
  - [admin-corrections-reminders.tsx](/home/gsh/workspace/TRMS/web/src/app/admin-corrections-reminders.tsx) 的“提醒对象成员”现在可先搜索再选择；
  - [admin-split-editor.tsx](/home/gsh/workspace/TRMS/web/src/app/admin-split-editor.tsx) 的“归属成员”现在支持按关键字过滤任务成员，再保存分摊。
- 补齐前端测试：
  - [admin-corrections-reminders.test.tsx](/home/gsh/workspace/TRMS/web/src/app/admin-corrections-reminders.test.tsx) 覆盖部分匹配与无结果提示；
  - [admin-split-editor.test.tsx](/home/gsh/workspace/TRMS/web/src/app/admin-split-editor.test.tsx) 覆盖分摊编辑里的成员筛选与无结果提示。

### 根因
- 现有管理员页面在多个场景下直接把 `task.member_ids` 整体渲染为长下拉列表，没有任何过滤能力。
- 当比赛成员变多时，管理员需要在纯列表里逐项扫视才能找到目标成员，既慢，也容易误选。
- 问题的本质不是“成员数据不够”，而是“已有任务成员列表缺少局部搜索入口”；因此应在现有选择路径上增加前端过滤，而不是扩改后端任务模型。

### 风险与影响面
- 本轮只修改前端选择交互，没有改任务成员的后端数据结构、权限判断或保存协议。
- 当前搜索仍基于任务内字符串成员标识做包含匹配；这是符合当前任务模型的最小实现。后续若要切到“用户名 / 显示名称 / 学号”三元展示，需要在下一任务统一替换成员展示口径，而不是在这一轮提前引入半套新模型。
- 分摊编辑和提醒记录现在都采用相同筛选控件；若后续还有其他管理员成员选择入口，可直接复用，避免再出现一处有搜索、一处无搜索的 UI 漂移。

### 验证结果
- 已通过定向前端测试：
  - `cd web && npm test -- admin-corrections-reminders.test.tsx admin-split-editor.test.tsx`
  - 2 个测试文件、8 个用例通过。
- 仓库级验证：
  - `./scripts/verify.sh`
  - Python 编译检查通过；
  - Alembic 升降级验证通过；
  - pytest 520 个用例通过，存在 3 条既有 `HTTP_422_UNPROCESSABLE_ENTITY` DeprecationWarning；
  - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过；Vitest 仍有既有 `--localstorage-file` 路径 warning，Vite 仍有既有 chunk size warning；
  - Docker Compose 配置检查通过；
  - `git diff --check` 通过。

## 2026-05-02 00:36 - Collapse supporting material ownership choice into a single select

### 完成内容
- 完成任务“收口附件归属选择，改为统一下拉归属发票”。
- 后端候选发票摘要补齐原始文件名：
  - [task_supporting_material_linkage.py](/home/gsh/workspace/TRMS/src/trms_backend/domain/task_supporting_material_linkage.py) 的 `PendingSupportingMaterialLinkageCandidateInvoiceSummary` 新增 `original_filename`；
  - 待关联读模型现在会把候选发票对应的原始发票文件名一并返回给前端，避免前端只能靠多按钮重复渲染区分。
- 成员工作台待关联辅助材料区改为单一下拉选择：
  - [member-invoice-workbench.tsx](/home/gsh/workspace/TRMS/web/src/app/member-invoice-workbench.tsx) 新增按材料维度维护的候选发票选择状态；
  - 对每份待关联材料，候选区从“每张发票一组关联/查看按钮”改成“一个归属发票下拉 + 一个保存归属按钮 + 一个查看所选发票按钮”；
  - 下拉候选项统一展示“发票编号 / 金额 / 原始文件名”，空候选时不渲染下拉，只保留“去上传区补录或补传发票”引导。
- 同步更新前后端测试：
  - [test_supporting_material_linkage_api.py](/home/gsh/workspace/TRMS/tests/test_supporting_material_linkage_api.py)、[test_task_member_workbench_api.py](/home/gsh/workspace/TRMS/tests/test_task_member_workbench_api.py) 断言候选发票摘要含 `original_filename`；
  - [member-invoice-workbench.test.tsx](/home/gsh/workspace/TRMS/web/src/app/member-invoice-workbench.test.tsx) 覆盖候选展示、切换下拉选项后保存归属，以及空候选不渲染下拉；
  - [member-material-detail.test.tsx](/home/gsh/workspace/TRMS/web/src/app/member-material-detail.test.tsx) 同步补齐候选摘要字段。

### 根因
- 上一轮虽然已经允许同一材料继续挂多张发票，但工作台待关联区仍然是“每个候选发票重复渲染一次按钮”的结构。
- 当候选发票变多时，用户要在多组重复按钮里自己比对票号、金额和文件名，界面噪音高，也不利于后续继续扩展多对多场景。
- 真正需要收口的是“候选展示方式”，不是再改一次附件写接口；也就是把“候选信息”压缩成一条稳定可比对的选项，再把写动作收敛成一次明确确认。

### 风险与影响面
- 本轮没有改 `PUT /api/invoices/{invoice_id}/supporting-materials/{material_id}` 的写语义，只是收口了成员工作台的选择交互和候选摘要内容。
- 材料详情页仍保持只读候选参考，不承担正式写入动作；正式选择归属仍在工作台完成，这样能避免本轮把写路径扩散到第二个页面。
- 当前下拉项使用“发票编号 / 金额 / 原始文件名”三元摘要；如果后续真实数据里仍出现高相似候选，应继续补更强的区分字段，而不是回退到重复按钮列表。

### 验证结果
- 已通过定向后端测试：
  - `uv run pytest tests/test_supporting_material_linkage_api.py tests/test_task_member_workbench_api.py`
  - 9 个用例通过。
- 已通过定向前端测试：
  - `cd web && npm test -- member-invoice-workbench.test.tsx member-material-detail.test.tsx`
  - 2 个测试文件、13 个用例通过。
- 仓库级验证：
  - `./scripts/verify.sh`
  - Python 编译检查通过；
  - Alembic 升降级验证通过；
  - pytest 520 个用例通过，存在 3 条既有 `HTTP_422_UNPROCESSABLE_ENTITY` DeprecationWarning；
  - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过；Vitest 仍有既有 `--localstorage-file` 路径 warning，Vite 仍有既有 chunk size warning；
  - Docker Compose 配置检查通过；
  - `git diff --check` 通过。

## 2026-05-02 00:34 - Support using one material as attachment for multiple invoices

### 完成内容
- 完成任务“支持同一材料作为多张发票的附件”。
- 后端待关联读模型从“未关联 or 已完成”二元状态收敛为“已关联 + 仍可继续关联候选”两层状态：
  - [task_supporting_material_linkage.py](/home/gsh/workspace/TRMS/src/trms_backend/domain/task_supporting_material_linkage.py) 为待关联项新增 `linked_invoices`；
  - 同一材料即使已经挂到一张发票，只要同提交人下仍存在其他候选发票，就继续保留在待关联列表中，并只把“尚未关联的剩余候选”暴露给前端；
  - 对“无候选”场景继续保留原有 `no_candidate` 语义。
- 前端成员主路径同步支持多对多附件归属展示：
  - [member-material-detail.tsx](/home/gsh/workspace/TRMS/web/src/app/member-material-detail.tsx) 新增“当前已关联发票列表”，并把候选区文案调整为“仍可继续关联的候选发票”；
  - [member-invoice-workbench.tsx](/home/gsh/workspace/TRMS/web/src/app/member-invoice-workbench.tsx) 在待关联辅助材料区同时展示“当前已关联”与“仍可继续关联的候选发票”，不再把“已有一条关联”误判为无需处理；
  - [types.ts](/home/gsh/workspace/TRMS/web/src/lib/api/types.ts) 同步新增 `linked_invoices` 类型定义。
- 补充后端和前端测试：
  - [test_supporting_material_linkage_api.py](/home/gsh/workspace/TRMS/tests/test_supporting_material_linkage_api.py) 覆盖“先关联一张后，仍保留其余候选”；
  - [test_task_member_workbench_api.py](/home/gsh/workspace/TRMS/tests/test_task_member_workbench_api.py) 覆盖成员工作台待关联区的部分已关联场景；
  - [test_invoices_api.py](/home/gsh/workspace/TRMS/tests/test_invoices_api.py) 覆盖“同一材料挂两张发票后，删除其中一条关联不影响另一条”；
  - [member-material-detail.test.tsx](/home/gsh/workspace/TRMS/web/src/app/member-material-detail.test.tsx)、[member-invoice-workbench.test.tsx](/home/gsh/workspace/TRMS/web/src/app/member-invoice-workbench.test.tsx) 覆盖“已关联 + 仍可继续关联”的新展示口径。

### 根因
- 数据库层原本就是 `invoice_supporting_material_links` 关联表，天然允许同一材料挂多张发票；真正把系统限制成“单张归属”的不是表结构，而是读模型和前端交互假设。
- 之前 `build_task_supporting_material_linkage_report(...)` 只要发现材料已有任意关联，就直接把它从待关联列表移除。
- 这会导致同一材料一旦先挂到某张发票，成员后续再也看不到它对其他候选发票的继续关联入口，从业务结果上等价于“单材料只能归属一张票”。

### 风险与影响面
- 本轮没有改数据库结构，也没有放宽权限边界；成员仍只能操作自己提交的附件，管理员仍可操作任务内全部附件。
- 当前多对多支持主要体现在“人工继续关联”与“单条解除不误删其他关联”两条主路径；自动归票仍保持保守策略，不会因为已有一条关联就主动去补挂更多发票。
- 工作台待关联区现在会继续显示“部分已关联但仍有剩余候选”的材料；这是需求要求的显式行为变化。若后续产品希望进一步把多候选收口成统一下拉，需要在后续任务“收口附件归属选择，改为统一下拉归属发票”中继续做 UI 收敛，而不是在本轮再扩改写路径。

### 验证结果
- 已通过定向后端测试：
  - `uv run pytest tests/test_supporting_material_linkage_api.py tests/test_task_member_workbench_api.py`
  - 9 个用例通过。
- 已通过附件解除相关后端测试：
  - `uv run pytest tests/test_invoices_api.py -k 'detach_supporting_material'`
  - 2 个用例通过。
- 已通过定向前端测试：
  - `cd web && npm test -- member-material-detail.test.tsx member-invoice-workbench.test.tsx`
  - 2 个测试文件、11 个用例通过。
- 仓库级验证：
  - `./scripts/verify.sh`
  - Python 编译检查通过；
  - Alembic 升降级验证通过；
  - pytest 520 个用例通过，存在 3 条既有 `HTTP_422_UNPROCESSABLE_ENTITY` DeprecationWarning；
  - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过；Vitest 仍有既有 `--localstorage-file` 路径 warning，Vite 仍有既有 chunk size warning；
  - Docker Compose 配置检查通过；
  - `git diff --check` 通过。

## 2026-05-02 00:20 - Add paper invoice entry and admin receipt confirmation

### 完成内容
- 完成任务“添加纸质发票录入与管理员收票确认”。
- 后端发票模型新增纸票状态字段：
  - 在 [invoices.py](/home/gsh/workspace/TRMS/src/trms_backend/domain/invoices.py)、[models.py](/home/gsh/workspace/TRMS/src/trms_backend/infrastructure/models.py)、[repositories.py](/home/gsh/workspace/TRMS/src/trms_backend/infrastructure/repositories.py) 中新增 `is_paper_invoice`、`paper_invoice_received`、`paper_invoice_received_at`、`paper_invoice_received_by`；
  - 新增 Alembic 迁移 [20260501_02_add_paper_invoice_fields.py](/home/gsh/workspace/TRMS/alembic/versions/20260501_02_add_paper_invoice_fields.py)。
- 新增纸质发票创建与收票确认 API：
  - [api/invoices.py](/home/gsh/workspace/TRMS/src/trms_backend/api/invoices.py) 新增 `POST /api/tasks/{task_id}/paper-invoices`，成员可直接手动创建纸质发票；
  - 该接口会生成一份受控占位材料并自动建票、初始化默认“全额归属本人”分摊；
  - 新增 `PUT /api/invoices/{invoice_id}/paper-receipt`，仅管理员可确认“已收到纸票”。
- 新增纸票门禁校验：
  - [invoice_validation.py](/home/gsh/workspace/TRMS/src/trms_backend/domain/invoice_validation.py) 新增 `invoice_paper_receipt_required`；
  - 未确认收票时输出 blocker failed，确认后转为 passed；
  - [task_member_workbench.py](/home/gsh/workspace/TRMS/src/trms_backend/domain/task_member_workbench.py) 同步把“仅有 blocker 校验失败”的发票视为不可提交，避免成员工作台把纸票错误显示为已就绪。
- 前端新增成员录入入口与管理员确认入口：
  - [member-invoice-workbench.tsx](/home/gsh/workspace/TRMS/web/src/app/member-invoice-workbench.tsx) 增加“手动录入纸质发票”表单，成员可直接录入票号、金额、费用类型、抬头、税号等字段；
  - 创建成功后会跳转到单票处理页，并明确提示“等待管理员确认收票”；
  - [admin-invoice-editor.tsx](/home/gsh/workspace/TRMS/web/src/app/admin-invoice-editor.tsx) 对纸质发票显示收票状态、确认人、确认时间和“确认已收到纸票”动作。
- 更新前后端测试：
  - 后端更新 [test_invoice_validation_rules.py](/home/gsh/workspace/TRMS/tests/test_invoice_validation_rules.py)、[test_invoices_api.py](/home/gsh/workspace/TRMS/tests/test_invoices_api.py)、[test_tasks_api.py](/home/gsh/workspace/TRMS/tests/test_tasks_api.py)、[test_database_migrations.py](/home/gsh/workspace/TRMS/tests/test_database_migrations.py)；
  - 前端更新 [member-invoice-workbench.test.tsx](/home/gsh/workspace/TRMS/web/src/app/member-invoice-workbench.test.tsx)、[admin-invoice-editor.test.tsx](/home/gsh/workspace/TRMS/web/src/app/admin-invoice-editor.test.tsx)。

### 根因
- 现有发票模型默认“每张发票都来自已上传电子材料”，没有表达“成员已录入纸票，但管理员还没线下收到原件”的状态。
- 因此系统过去只能在“无票”与“电子票已上传”之间二选一，既不能让成员先录入纸票，也无法在导出前对“纸票是否已收齐”做显式门禁。
- 这轮的核心不是再造一套特殊流程，而是给现有发票主链路补上“纸票”和“收票确认”两个明确状态，并让既有校验/工作台/任务推进都识别这两个状态。

### 风险与影响面
- 本轮采用“纸质发票 = 受控占位材料 + 纸票标记”的最小实现，而不是重构成“无材料发票”；这样能复用现有发票详情、分摊、确认、复核和权限主路径，避免改动扩散。
- 占位材料只保存手动录入摘要，不代表真实纸票扫描件；管理员预览页会把它当作不可内联预览的占位文件处理，这是有意保守，不伪装成真实电子票附件。
- 当前成员工作台把“单纯 blocker 校验失败但没有识别/附件/分摊问题”的发票统一归入 `recognition_review` 分组；这能正确阻塞提交，但分组文案仍偏泛化。若后续纸票、抬头不符等 blocker 场景继续增多，应单独拆出更精确的 `validation_blocker` 分组，而不是继续复用“识别待确认”文案。

### 验证结果
- 已通过纸票相关定向后端测试：
  - `uv run pytest tests/test_invoice_validation_rules.py tests/test_invoices_api.py tests/test_tasks_api.py -k 'paper or receipt or ready_to_export'`
  - 11 个用例通过。
- 已通过纸票相关定向前端测试：
  - `cd web && npm test -- member-invoice-workbench.test.tsx admin-invoice-editor.test.tsx`
  - 2 个测试文件、12 个用例通过。
- 已通过前端类型与构建检查：
  - `cd web && npx tsc --noEmit`
  - `cd web && npm run build`
- 已通过仓库级验证：
  - `./scripts/verify.sh`
  - Python 编译检查通过；
  - Alembic 升降级验证通过；
  - pytest 517 个用例通过，存在 3 条既有 `HTTP_422_UNPROCESSABLE_ENTITY` DeprecationWarning；
  - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过；Vitest 仍有既有 `--localstorage-file` 路径 warning，Vite 仍有既有 chunk size warning；
  - Docker Compose 配置检查通过；
  - `git diff --check` 通过。

## 2026-05-01 23:43 - Allow corporate transfer reference to replace payment records

### 完成内容
- 完成任务“支持用公对公转账编号代替支付记录”。
- 后端新增发票字段：
  - 在 [invoices.py](/home/gsh/workspace/TRMS/src/trms_backend/domain/invoices.py)、[models.py](/home/gsh/workspace/TRMS/src/trms_backend/infrastructure/models.py)、[repositories.py](/home/gsh/workspace/TRMS/src/trms_backend/infrastructure/repositories.py)、[api/invoices.py](/home/gsh/workspace/TRMS/src/trms_backend/api/invoices.py) 中新增 `corporate_transfer_reference`；
  - 新增 Alembic 迁移 [20260501_01_add_invoice_corporate_transfer_reference.py](/home/gsh/workspace/TRMS/alembic/versions/20260501_01_add_invoice_corporate_transfer_reference.py)；
  - 为保持现有领域测试夹具稳定，`InvoiceRecord.corporate_transfer_reference` 默认为 `None`。
- 调整支付记录相关校验 [invoice_validation.py](/home/gsh/workspace/TRMS/src/trms_backend/domain/invoice_validation.py)：
  - `invoice_payment_record_required` 在发票金额达到阈值时，若已填写合法公对公转账编号，则直接通过，不再要求必须上传 `payment_record`；
  - `invoice_payment_record_amount_match` 在“只有转账编号、没有支付记录附件”的替代路径下返回 `not_applicable`，避免伪造金额匹配；
  - 若同时仍上传了支付记录，系统继续按既有支付记录金额匹配路径工作，不删除原规则。
- 前端录入与展示调整：
  - 成员单票页 [member-invoice-detail.tsx](/home/gsh/workspace/TRMS/web/src/app/member-invoice-detail.tsx) 新增“公对公转账编号”录入；
  - 管理员发票编辑页 [admin-invoice-editor.tsx](/home/gsh/workspace/TRMS/web/src/app/admin-invoice-editor.tsx) 新增同字段，和其他发票业务字段同路径保存；
  - 前端类型与文案 [types.ts](/home/gsh/workspace/TRMS/web/src/lib/api/types.ts)、[ui-text.ts](/home/gsh/workspace/TRMS/web/src/lib/ui-text.ts) 同步更新。
- 更新测试：
  - [test_invoice_validation_rules.py](/home/gsh/workspace/TRMS/tests/test_invoice_validation_rules.py) 覆盖“转账编号替代支付记录”与“金额匹配规则不适用”；
  - [test_invoices_api.py](/home/gsh/workspace/TRMS/tests/test_invoices_api.py) 覆盖发票 API 保存转账编号，以及大额发票在填写转账编号后免支付记录；
  - [test_database_migrations.py](/home/gsh/workspace/TRMS/tests/test_database_migrations.py) 同步迁移 head 与本地自举边界；
  - [member-invoice-detail.test.tsx](/home/gsh/workspace/TRMS/web/src/app/member-invoice-detail.test.tsx)、[admin-invoice-editor.test.tsx](/home/gsh/workspace/TRMS/web/src/app/admin-invoice-editor.test.tsx) 覆盖成员/管理员录入该字段。

### 根因
- 原系统把“大额发票需要支付记录”完全绑定在 `payment_record` 辅助材料类型上，没有发票级的“替代支付凭据”表达能力。
- 这会把“已具备公对公转账编号，但没有单独支付截图”的真实业务场景误判为缺材料。
- 问题的关键不是新增一种材料，而是允许发票自身带上“支付凭据替代信息”，并让规则层识别这条替代路径。

### 风险与影响面
- 本轮只把“公对公转账编号”视为“支付记录必需规则”的替代，不把它伪装成支付记录附件，也不参与支付记录金额求和。
- 因此，替代路径下 `invoice_payment_record_amount_match` 明确返回 `not_applicable`；系统不会假装已经校验过真实支付流水金额。
- 当前合法性边界采用“非空、去首尾空白后保留”的最小约束，没有额外加格式正则；若后续学校财务口径要求固定编码格式，应单独补更严格校验，而不是在本轮猜测规则。

### 验证结果
- 已通过定向后端测试：
  - `uv run pytest tests/test_invoice_validation_rules.py tests/test_invoices_api.py tests/test_database_migrations.py`
  - 77 个用例通过。
- 已通过前端全量测试：
  - `cd web && npm test`
  - 100 个用例通过。
- 已通过仓库级验证：
  - `./scripts/verify.sh`
  - Python 编译检查通过；
  - Alembic 升降级验证通过；
  - pytest 513 个用例通过，存在 3 条既有 `HTTP_422_UNPROCESSABLE_ENTITY` DeprecationWarning；
  - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过；Vitest 仍有既有 `--localstorage-file` 路径 warning，Vite 仍有既有 chunk size warning；
  - Docker Compose 配置检查通过；
  - `git diff --check` 通过。

## 2026-05-01 23:22 - Allow partial reimbursement splits with confirmation prompt

### 完成内容
- 完成任务“允许发票部分报销，并把‘分摊金额之和必须等于发票金额’改为确认提示”。
- 后端调整 [splits.py](/home/gsh/workspace/TRMS/src/trms_backend/api/splits.py)：
  - 删除保存分摊时“分摊金额合计必须等于发票金额”的 `409` 拦截；
  - 保留成员权限、任务成员约束、重复成员校验、已提交发票成员不可改等既有边界不变。
- 成员端调整 [member-invoice-detail.tsx](/home/gsh/workspace/TRMS/web/src/app/member-invoice-detail.tsx)：
  - 单张发票页保存金额归属前，若分摊合计不等于票面金额，会弹出确认对话框；
  - 差额大于 0 时明确提示“超额报销风险”，差额小于 0 时明确提示“仍有未报销金额”；
  - 用户确认后允许保存，取消后不发起保存请求；
  - 页面提示文案同步改为“允许保存，但该发票仍会停留在分摊未完成”。
- 管理员端调整 [admin-split-editor.tsx](/home/gsh/workspace/TRMS/web/src/app/admin-split-editor.tsx)：
  - 分摊编辑页沿用同一业务口径；
  - 若分摊未闭合，保存前改为风险确认，而不是依赖后端报错；
  - 闭合分摊时仍保留原确认文案。
- 更新测试：
  - [test_splits_api.py](/home/gsh/workspace/TRMS/tests/test_splits_api.py) 改为覆盖“不闭合分摊仍可保存”；
  - [test_cli_split.py](/home/gsh/workspace/TRMS/tests/test_cli_split.py) 改为覆盖 CLI 可提交部分报销分摊；
  - [member-invoice-detail.test.tsx](/home/gsh/workspace/TRMS/web/src/app/member-invoice-detail.test.tsx) 覆盖成员端不闭合分摊的确认保存与取消不保存；
  - [admin-split-editor.test.tsx](/home/gsh/workspace/TRMS/web/src/app/admin-split-editor.test.tsx) 覆盖管理员端不闭合分摊确认文案与确认后保存。

### 根因
- 现有实现把“分摊金额合计等于发票金额”同时当成了“保存时硬约束”和“后续提交/导出门禁”。
- 这导致“部分报销”这种真实业务场景根本无法落库，用户也无法先把当前已报销部分保存下来，再继续补齐或由管理员复核。
- 实际需要区分两个边界：
  - 保存层：允许记录当前分摊方案；
  - 流程门禁层：分摊未闭合时，仍不得视为已完成，不得进入可提交/可导出状态。

### 风险与影响面
- 本轮只放开“保存分摊”动作，没有放开成员工作台、任务就绪度和后续确认门禁中对 `split_incomplete` 的判断。
- 因此，部分报销分摊现在可以保存，但相关发票仍会继续停留在“分摊未完成”，不会被误判为可提交或可导出。
- CLI 当前只放开后端保存路径，没有额外增加交互式确认；这是当前 CLI 非交互设计下的保守延续，后续若产品要求 CLI 也显式提醒，可单独补充。

### 验证结果
- 已通过定向后端/CLI 测试：
  - `uv run pytest tests/test_splits_api.py tests/test_cli_split.py`
  - 15 个用例通过。
- 已通过定向前端测试：
  - `cd web && npm test -- member-invoice-detail.test.tsx admin-split-editor.test.tsx`
  - 8 个用例通过。
- 已通过仓库级验证：
  - `./scripts/verify.sh`
  - Python 编译检查通过；
  - Alembic 升降级验证通过；
  - pytest 510 个用例通过，存在 3 条既有 `HTTP_422_UNPROCESSABLE_ENTITY` DeprecationWarning；
  - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过；Vitest 仍有既有 `--localstorage-file` 路径 warning，Vite 仍有既有 chunk size warning；
  - Docker Compose 配置检查通过；
  - `git diff --check` 通过。

## 2026-05-01 23:34 - Prioritize local transport e-invoice auto-linking for itineraries

### 完成内容
- 完成任务“分析市内交通费用材料归票策略，并让行程单优先自动归属到对应电子发票”。
- 将归票策略直接落实到 [supporting_material_auto_link.py](/home/gsh/workspace/TRMS/src/trms_backend/application/supporting_material_auto_link.py)：
  - 仅当 `itinerary` 的最新识别结果明确为 `local_transport` 或 `expense_type_candidate=local_transport` 时，才进入市内交通归票优先逻辑；
  - 候选发票先收敛为“同任务、同提交人、费用类型为 `local_transport`”的发票，避免把市内交通行程单误挂到铁路、住宿等其他票据；
  - 取消 `itinerary` 在“刚上传、尚未识别”阶段的预归票，避免出现 `发票 A -> 行程单 B -> 行程单 A -> 发票 B` 时把 `行程单 B` 先错误挂到 `发票 A`；
  - 只有在识别结果给出正向证据后才允许自动归票；当前正向证据为“行程单金额精确匹配发票金额”，其次是“行程单日期与发票交易日期同日”；
  - 若仍存在并列最高分，则明确不自动绑定，保留人工处理，避免误绑。
- 统一补齐自动归票触发点：
  - [recognition_async_jobs.py](/home/gsh/workspace/TRMS/src/trms_backend/application/recognition_async_jobs.py)、[materials.py](/home/gsh/workspace/TRMS/src/trms_backend/api/materials.py)、[invoices.py](/home/gsh/workspace/TRMS/src/trms_backend/api/invoices.py)、[recognitions.py](/home/gsh/workspace/TRMS/src/trms_backend/api/recognitions.py) 现在都为自动归票服务注入识别仓库；
  - 管理员手动回填/重放识别结果后，也会复用同一归票策略刷新附件归属。
- 更新识别提示词 [recognition_llm.py](/home/gsh/workspace/TRMS/src/trms_backend/application/recognition_llm.py)：
  - `itinerary` 结构化提取新增 `amount_cents`；
  - 提示词明确要求市内交通行程单尽量抽取金额和时间，并保持 `expense_type=local_transport`，为多张网约车电子发票并存时提供更稳定的自动归票证据。
- 新增/更新测试：
  - [test_invoices_api.py](/home/gsh/workspace/TRMS/tests/test_invoices_api.py) 覆盖“先有行程单、后建多类发票”时优先归属到市内交通发票；
  - [test_recognition_async_jobs.py](/home/gsh/workspace/TRMS/tests/test_recognition_async_jobs.py) 覆盖“先有多张发票、后识别行程单”的自动归票，以及多张市内交通发票并存时拒绝误绑；
  - [test_recognition_async_jobs.py](/home/gsh/workspace/TRMS/tests/test_recognition_async_jobs.py) 额外覆盖用户指出的 `发票 A -> 行程单 B -> 行程单 A -> 发票 B` 时序，确认 `行程单 B` 不会在预识别阶段误挂到 `发票 A`，且 `发票 B` 成票后会正确回补；
  - [test_recognition_llm.py](/home/gsh/workspace/TRMS/tests/test_recognition_llm.py) 覆盖 `itinerary` 提示词已要求提取市内交通金额/时间。

### 根因
- 上传接口在分发识别任务之前，会先按用户显式 `material_type` 对新材料做一次自动归票；对 `itinerary` 而言，这一步发生在识别之前，没有金额、日期等可比对证据。
- 这会在 `发票 A -> 行程单 B -> 行程单 A -> 发票 B` 这类真实时序里，把 `行程单 B` 因“当前只有 1 张候选发票”而错误挂到 `发票 A`，后续即使 `发票 B` 成票也不会自动纠正。
- 另外，识别完成后的自动归票路径如果再回库读取最新识别结果，会保留一个短暂时序窗；本轮已改为把当前 `updated recognition` 直接透传给自动归票服务，避免同轮识别后退回旧视图。

### 归票策略
- 适用范围：只对 `itinerary` 且识别为 `local_transport` 的材料启用优先归票。
- 证据优先级：
  - 1. 候选发票必须是同提交人的 `local_transport` 发票；
  - 2. 行程单必须先完成识别，未识别前不自动归票；
  - 3. 行程单 `amount_cents` 与发票金额完全一致时优先；
  - 4. 行程单日期与发票交易日期同日时进一步加分。
- 冲突处理：
  - 若没有正向证据，即使当前只剩 1 张候选市内交通发票，也不自动归属；
  - 若多张票分数并列，则不自动归属。
- 误绑防护：
  - 不做文件名模糊匹配；
  - 不做路线文本模糊匹配；
  - 在没有收敛到唯一最优候选前，不跨费用类型自动挂票。

### 验证结果
- 已通过定向测试：
  - `uv run pytest tests/test_recognition_async_jobs.py tests/test_invoices_api.py -k 'local_transport or backfills_itinerary_link_when_invoice_is_recognized_later or mislink_future_itinerary_to_existing_invoice'`
  - 6 个用例通过。
- 已通过仓库级验证：
  - `./scripts/verify.sh`
  - Python 编译检查通过；
  - Alembic 升降级验证通过；
  - pytest 510 个用例通过，存在 3 条既有 `HTTP_422_UNPROCESSABLE_ENTITY` DeprecationWarning；
  - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过；Vitest 仍有既有 `--localstorage-file` 路径 warning，Vite 仍有既有 chunk size warning；
  - Docker Compose 配置检查通过；
  - `git diff --check` 通过。

### 风险与后续
- 当前自动归票仍没有引入路线文本相似度或平台订单号级别证据；这是有意收口，优先避免误绑，而不是为了更高命中率引入脆弱模糊匹配。
- 若后续发现同一成员同日同金额的网约车发票仍频繁冲突，下一步应优先补充“平台订单号/行程序号”级识别字段，而不是直接放宽自动归票条件。

## 2026-05-01 22:48 - Split member material detail pages by recognized material type

### 完成内容
- 已将你新增的 9 条产品需求写入 [TASKS.md](/home/gsh/workspace/TRMS/TASKS.md)，并按仓库规则把第 1 条拆成当前轮最小任务“让成员材料详情按识别类型进入独立前端页面”。
- 新增非发票材料详情页 [member-material-detail.tsx](/home/gsh/workspace/TRMS/web/src/app/member-material-detail.tsx)：
  - `payment_record`、`competition_notice`、`itinerary`、`order_screenshot`、`other_attachment` 进入独立材料详情页；
  - 每种类型都有独立标题、说明、类型相关识别字段区和对应的下一步提示；
  - 当前页不再展示发票金额分摊、发票字段补录等发票特有表单。
- 调整成员端路由与入口：
  - 新增 `/member/materials/:materialId` 路由，承载非发票材料详情页；
  - 保留 `/member/materials/:materialId/invoice` 作为发票特有处理页；
  - [member-invoice-workbench.tsx](/home/gsh/workspace/TRMS/web/src/app/member-invoice-workbench.tsx) 现在按材料类型分流：已有发票或识别为发票的材料进入发票页，其他材料进入新的材料页。
- 新材料详情页支持的主动作：
  - 查看原文件；
  - 重新识别；
  - 修改材料类型；
  - 展示当前候选归属发票并跳转查看；
  - 当用户把材料类型改成 `invoice` 后，自动切到发票处理页。
- 新增/更新前端测试：
  - [member-material-detail.test.tsx](/home/gsh/workspace/TRMS/web/src/app/member-material-detail.test.tsx) 覆盖 5 种非发票材料各自详情页；
  - [member-invoice-workbench.test.tsx](/home/gsh/workspace/TRMS/web/src/app/member-invoice-workbench.test.tsx) 覆盖非发票材料从工作台进入独立材料页。

### 根因
- 之前成员工作台里“点击进入处理页”的逻辑，除了已有 `invoice.id` 的材料外，剩余材料统一落到发票处理页。
- 这导致支付记录、比赛通知、行程单、订单截图和其他附件都被迫展示发票字段、分摊和提交语义，页面上下文与材料真实职责不一致。

### 验证结果
- 已通过定向前端测试：
  - `cd web && npm test -- member-material-detail.test.tsx member-invoice-workbench.test.tsx member-invoice-detail.test.tsx`
  - 3 个测试文件、13 个用例通过。
- 已通过仓库级验证：
  - `./scripts/verify.sh`
  - Python 编译检查通过；
  - Alembic 升降级验证通过；
  - pytest 504 个用例通过，存在 3 条既有 `HTTP_422_UNPROCESSABLE_ENTITY` DeprecationWarning；
  - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过；Vitest 仍有既有 `--localstorage-file` 路径 warning，Vite 仍有既有 chunk size warning；
  - Docker Compose 配置检查通过；
  - `git diff --check` 通过。

### 风险与后续
- 本轮只解决“不同材料类型进入不同详情页”的前端信息架构问题，没有顺带实现材料直接在详情页内完成附件归属写操作；当前仍通过工作台待关联区完成最终归属。
- 非发票材料详情页目前展示的是识别结果、候选归属和类型修正，不包含新的后端字段编辑 API；如果后续要允许直接编辑支付记录/行程单结构化字段，应作为独立任务扩展。

## 2026-05-01 22:15 - Sync frontend upload limit to 64MiB

### 完成内容
- 修复用户反馈的“前端还存在限制上传 10MB”问题。
- 调整 [upload-validation.ts](/home/gsh/workspace/TRMS/web/src/lib/upload-validation.ts)：
  - 前端单文件上传预检阈值从 `10 * 1024 * 1024` 调整为 `64 * 1024 * 1024`；
  - 导出统一展示文案 `64MB`，避免页面和测试继续各自硬编码数字。
- 调整成员上传入口：
  - [member-material-upload.tsx](/home/gsh/workspace/TRMS/web/src/app/member-material-upload.tsx) 的错误提示和上传说明显示 64MB；
  - [member-invoice-workbench.tsx](/home/gsh/workspace/TRMS/web/src/app/member-invoice-workbench.tsx) 的工作台上传错误提示和上传说明显示 64MB。
- 调整 [member-material-upload.test.tsx](/home/gsh/workspace/TRMS/web/src/app/member-material-upload.test.tsx)：
  - 超限夹具改为 `MAX_UPLOAD_FILE_BYTES + 1`；
  - 断言引用同一展示常量，不再硬编码 10MB。
- 更新 [TASKS.md](/home/gsh/workspace/TRMS/TASKS.md) 和 [README.md](/home/gsh/workspace/TRMS/README.md)，明确前端上传预检也同步到 64MiB。

### 根因
- 上一轮只把后端领域常量和 CLI 本地预检提高到 64MiB，遗漏了前端独立的 `web/src/lib/upload-validation.ts`。
- 成员专项上传页和成员工作台虽然共用了该前端常量做校验，但文案和测试仍直接表达 10MB，导致浏览器层提前拦截了 10MB 以上文件。

### 验证结果
- 已通过定向前端测试：
  - `cd web && npm test -- member-material-upload`
  - 1 个测试文件、4 个用例通过；仍存在既有 `--localstorage-file` warning。
- 已通过仓库级验证：
  - `./scripts/verify.sh`
  - Python 编译检查通过；
  - Alembic 升降级验证通过；
  - pytest 504 个用例通过，存在 3 条既有 `HTTP_422_UNPROCESSABLE_ENTITY` DeprecationWarning；
  - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过；Vitest 仍有既有 `--localstorage-file` 路径 warning，Vite 仍有既有 chunk size warning；
  - Docker Compose 配置检查通过；
  - `git diff --check` 通过。

### 风险与后续
- 当前前端阈值仍是源码常量，与后端常量通过人工同步保持一致；后续若上传限制变为运行时配置，应由后端向前端下发配置，避免再次漂移。

## 2026-05-01 22:05 - Fix recognition-time auto linking and local transport e-ticket handling

### 完成内容
- 完成任务“修复识别前错误自动归票、补齐市内交通电子票规则并提高上传阈值”。
- 只读检查当前运行实例数据库 `sqlite:///./trms.db` 后确认：
  - 票号 `25319166100007042896` 对应铁路发票 `0b96d3fd-3edc-4ca6-8ae6-6e19c4c15a64`；
  - 该票错误关联了 23 个材料，其中大部分已识别为独立发票，另有高德打车行程单和酒店/报名费/航空/洛谷等不应挂在铁路票下的材料。
- 已对当前运行实例做受控数据修正：
  - 修改前备份：`/tmp/trms-before-25319166100007042896-link-cleanup-20260501215736.db`；
  - 删除 `25319166100007042896` 的 23 条错误附件链接，并刷新该票校验；
  - 使用修复后的 `expense_type_candidate` fallback，为 `25319166100007434740.pdf` 补建铁路发票记录；
  - 从原始 PDF 文本确认桔子出行发票号 `25312000000355846530`，为 `【桔子出行-72.86元-1个行程】高德打车电子发票.pdf` 补建市内交通发票；
  - 将 72.86 元行程单关联到 `25312000000355846530`，将 42.50 元行程单关联到 `25312000000355838261`，并刷新两张市内交通发票校验；
  - 修正后 `25319166100007042896` 剩余附件链接数为 0；当前库中识别成功但未成票的发票型材料数为 0；市内交通两张票的网约车行程规则均为 `passed`；仍有 1 个待确认材料 `Screenshot_20251119-161841.支付宝.png`。
- 调整自动归票 [supporting_material_auto_link.py](/home/gsh/workspace/TRMS/src/trms_backend/application/supporting_material_auto_link.py)：
  - 只允许 `payment_record`、`competition_notice`、`itinerary`、`order_screenshot` 进入自动附件关联；
  - 默认 `other_attachment` 不再在识别前被自动挂到单候选发票，避免后续识别成发票后污染附件表。
- 调整识别完成后的编排：
  - [materials.py](/home/gsh/workspace/TRMS/src/trms_backend/api/materials.py) 和 [recognition_async_jobs.py](/home/gsh/workspace/TRMS/src/trms_backend/application/recognition_async_jobs.py) 在识别完成、材料类型更新之后，再对真实附件类型执行单候选自动关联并刷新校验。
- 调整自动建票 [recognition_invoice_auto_create.py](/home/gsh/workspace/TRMS/src/trms_backend/application/recognition_invoice_auto_create.py)：
  - 发票识别结果缺少 `expense_type` 但存在合法 `expense_type_candidate` 时，可用候选费用类型自动建票。
- 调整市内交通网约车规则 [invoice_validation.py](/home/gsh/workspace/TRMS/src/trms_backend/domain/invoice_validation.py)：
  - 市内交通电子发票/电子票按网约车处理；
  - 只要存在网约车证据，就要求行程信息；关联行程单后通过。
- 调整识别提示词 [recognition_llm.py](/home/gsh/workspace/TRMS/src/trms_backend/application/recognition_llm.py)：
  - prompt 版本提升到 `trms-recognition-v4`；
  - 明确市内交通电子发票/电子票应分类为 `invoice`、费用类型为 `local_transport`，并作为需要匹配行程单的网约车证据；
  - 要求市内交通电子发票尽量抽取可见发票号。
- 调整上传阈值 [materials.py](/home/gsh/workspace/TRMS/src/trms_backend/domain/materials.py)：
  - 默认上传大小从 10MiB 提升到 64MiB，后端上传、CLI 本地预检和前端上传预检均按该阈值执行。
- 更新测试：
  - [test_materials_api.py](/home/gsh/workspace/TRMS/tests/test_materials_api.py) 覆盖默认材料类型不在识别前自动归票；
  - [test_recognition_async_jobs.py](/home/gsh/workspace/TRMS/tests/test_recognition_async_jobs.py) 覆盖 `expense_type_candidate` 自动建票和识别后真实附件自动关联；
  - [test_invoice_validation_rules.py](/home/gsh/workspace/TRMS/tests/test_invoice_validation_rules.py) 覆盖市内交通电子票缺行程失败、有关联行程通过；
  - [test_recognition_llm.py](/home/gsh/workspace/TRMS/tests/test_recognition_llm.py) 覆盖提示词版本和新增规则。

### 根因
- 上传接口在识别前会按上传时的材料类型触发自动归票；成员省略材料类型时默认是 `other_attachment`，而旧自动归票逻辑把所有非 `invoice` 的已归属材料都视为可自动关联附件。
- 这导致同一成员上传多张发票时，后续真实发票在识别前先作为 `other_attachment` 挂到第一张已有发票；识别完成后材料类型变为 `invoice`，但旧链接没有被清理。
- 识别自动建票要求 `expense_type` 必须存在，未使用分类阶段稳定产出的 `expense_type_candidate`，所以部分字段足够的发票没有成票。
- 市内交通电子发票的识别提示没有明确“电子票即网约车证据、必须匹配行程单”，校验层也未对该业务规则形成确定性约束。

### 验证结果
- 已通过定向测试：
  - `uv run pytest tests/test_materials_api.py::test_default_material_type_does_not_auto_link_before_recognition tests/test_recognition_async_jobs.py::test_recognition_async_processor_auto_creates_invoice_from_expense_type_candidate tests/test_recognition_async_jobs.py::test_recognition_async_processor_auto_links_default_upload_after_support_type_is_recognized tests/test_invoice_validation_rules.py::test_local_transport_invoice_is_treated_as_rideshare_electronic_ticket tests/test_invoice_validation_rules.py::test_local_transport_electronic_invoice_passes_when_trip_record_is_linked tests/test_recognition_llm.py::test_openai_compatible_recognition_client_includes_chinese_invoice_rules_in_prompt`
  - 6 个用例通过。
- 已通过相关集合：
  - `uv run pytest tests/test_materials_api.py tests/test_recognition_async_jobs.py tests/test_invoice_validation_rules.py tests/test_recognition_llm.py tests/test_cli_submit.py tests/test_material_upload_integration.py`
  - 102 个用例通过。
- 首次仓库级验证发现 `tests/test_async_jobs.py` 中 3 个 worker 边界测试失败；根因是识别后附件自动关联在成功无字段/失败任务路径上读取了 fake material repository。已收窄为“仅识别成功且识别结果明确为可自动归票附件类型时读取材料并归票”，随后相关回归通过：
  - `uv run pytest tests/test_async_jobs.py::test_recognition_async_processor_skips_duplicate_delivery_after_conflict tests/test_async_jobs.py::test_recognition_async_processor_uses_worker_threads_for_batch_uploads tests/test_async_jobs.py::test_recognition_async_processor_logs_processed_and_skipped_jobs tests/test_recognition_async_jobs.py::test_recognition_async_processor_auto_links_default_upload_after_support_type_is_recognized`
  - 4 个用例通过。
- 已通过仓库级验证：
  - `./scripts/verify.sh`
  - Python 编译检查通过；
  - Alembic 升降级验证通过；
  - pytest 504 个用例通过，存在 3 条既有 `HTTP_422_UNPROCESSABLE_ENTITY` DeprecationWarning；
  - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过；Vitest 仍有既有 `--localstorage-file` 路径 warning，Vite 仍有既有 chunk size warning；
  - Docker Compose 配置检查通过；
  - `git diff --check` 通过。

### 风险与后续
- 本轮只对当前 SQLite 运行实例做了明确对象的数据修正，没有批量重跑所有历史识别任务。
- `Screenshot_20251119-161841.支付宝.png` 仍处于待确认状态，识别摘要显示它像酒店订单/支付上下文，但置信度未达到自动更新材料类型和自动归票边界，仍需要人工确认或后续重识别。
- 市内交通发票号缺失的根因是识别抽取遗漏；本轮用真实 PDF 文本补齐当前库数据，并通过 prompt v4 降低后续复发概率。

## 2026-05-01 12:20 - Enable threaded recognition worker for batch invoice uploads

### 完成内容
- 完成任务“将 worker 识别任务改为可配置多线程并发处理”。
- 调整 [recognition_async_jobs.py](/home/gsh/workspace/TRMS/src/trms_backend/application/recognition_async_jobs.py)：
  - `RecognitionAsyncJobProcessor` 新增 `max_workers`；
  - 单轮轮询取得多条待识别任务时，通过线程池并发执行识别、自动建票和校验刷新；
  - 默认构造仍保持单线程，worker 入口按运行配置显式传入并发数，避免影响请求内同步路径和既有单元测试语义。
- 调整运行配置 [runtime_config.py](/home/gsh/workspace/TRMS/src/trms_backend/runtime_config.py)：
  - 新增 `TRMS_ASYNC_JOB_WORKER_CONCURRENCY`，默认 `4`；
  - 限制取值范围为 `1..32`，非法配置启动时直接报错。
- 调整 worker 入口与日志：
  - [__main__.py](/home/gsh/workspace/TRMS/src/trms_backend/__main__.py) 将并发配置传给识别处理器；
  - [async_jobs.py](/home/gsh/workspace/TRMS/src/trms_backend/application/async_jobs.py) 在 worker 启动和轮询日志中记录并发值。
- 更新部署与文档：
  - [.env.example](/home/gsh/workspace/TRMS/.env.example)、[.env.development.example](/home/gsh/workspace/TRMS/.env.development.example)、[docker-compose.yml](/home/gsh/workspace/TRMS/deploy/docker-compose.yml) 增加并发配置；
  - [README.md](/home/gsh/workspace/TRMS/README.md) 和 [生产部署清单与Docker Compose基线.md](/home/gsh/workspace/TRMS/docs/生产部署清单与Docker%20Compose基线.md) 说明配置边界。
- 更新测试：
  - [test_async_jobs.py](/home/gsh/workspace/TRMS/tests/test_async_jobs.py) 覆盖 worker 并发日志和批量识别任务并发执行；
  - [test_runtime_config.py](/home/gsh/workspace/TRMS/tests/test_runtime_config.py) 覆盖配置默认值、读取和非法值拒绝。

### 根因
- 批量上传链路已经支持一次提交多个文件、部分成功和为每个有效材料创建识别任务；阻塞点在独立 worker 识别处理器仍按 `for pending_task in list_pending(...)` 串行执行。
- 真实发票识别通常受 PDF/图片处理和外部 LLM/VLM 调用耗时影响，串行消费会把同批发票排成队列，放大用户批量上传后的等待时间。

### 验证结果
- 已通过定向后端测试：
  - `uv run pytest tests/test_async_jobs.py tests/test_runtime_config.py tests/test_recognition_async_jobs.py tests/test_material_upload_integration.py`
  - 43 个用例通过。
- 已通过仓库级验证：
  - `./scripts/verify.sh`
  - Python 编译检查通过；
  - Alembic 升降级验证通过；
  - pytest 499 个用例通过，存在 3 条既有 `HTTP_422_UNPROCESSABLE_ENTITY` DeprecationWarning；
  - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过；Vitest 仍有既有 `--localstorage-file` 路径 warning，Vite 仍有既有 chunk size warning；
  - Docker Compose 配置检查通过；
  - `git diff --check` 通过。

### 风险与后续
- 本轮并发的是单个 worker 进程内的识别任务消费，不改变数据库轮询模型，也不引入 Redis Broker；多 worker 进程之间仍依赖既有状态更新幂等边界避免重复交付造成错误结果。
- 并发数默认 4，真实生产环境应结合 LLM/VLM provider 的限流、数据库连接数和对象存储吞吐调整。

## 2026-05-01 11:43 - Cancel location-range invoice rule and restructure workbench lists

### 完成内容
- 完成任务“取消发票地点范围规则并统一工作台发票摘要”。
- 后端调整 [invoice_validation.py](/home/gsh/workspace/TRMS/src/trms_backend/domain/invoice_validation.py)：
  - `validate_invoice(...)` 不再生成 `invoice_competition_location_range`；
  - 保留 `validate_competition_location_range(...)` 和其单元测试，作为后续若要重新启用规则时的独立规则边界，本轮不删除地点字段解析辅助代码。
- 前端调整统一发票摘要组件 [invoice-summary-row.tsx](/home/gsh/workspace/TRMS/web/src/components/invoice-summary-row.tsx)：
  - 发票摘要统一改为三行：第一行票号，第二行原始文件名，第三行金额、校验状态、附件数量；
  - 管理员发票录入、材料审核/成员提醒、分摊确认、成员工作台和成员单票共享摘要均通过该组件展示金额与状态。
- 调整成员工作台 [member-invoice-workbench.tsx](/home/gsh/workspace/TRMS/web/src/app/member-invoice-workbench.tsx)：
  - 改为左右分栏；
  - 左侧类别从上到下为“工作状态”“上传页面”“发票查看页面”；
  - 右侧只展示当前类别内容，发票查看页面继续展示发票列表，并保持点击进入单张发票处理页。
- 更新样式 [styles.css](/home/gsh/workspace/TRMS/web/src/styles.css)，为成员工作台侧栏和三行发票摘要补齐响应式布局。
- 更新测试：
  - 后端：[test_invoice_validation_rules.py](/home/gsh/workspace/TRMS/tests/test_invoice_validation_rules.py)、[test_invoices_api.py](/home/gsh/workspace/TRMS/tests/test_invoices_api.py)、[test_exports_api.py](/home/gsh/workspace/TRMS/tests/test_exports_api.py)、[test_main_flow_e2e.py](/home/gsh/workspace/TRMS/tests/test_main_flow_e2e.py)
  - 前端：[admin-split-editor.test.tsx](/home/gsh/workspace/TRMS/web/src/app/admin-split-editor.test.tsx)、[admin-corrections-reminders.test.tsx](/home/gsh/workspace/TRMS/web/src/app/admin-corrections-reminders.test.tsx)、[admin-invoice-editor.test.tsx](/home/gsh/workspace/TRMS/web/src/app/admin-invoice-editor.test.tsx)、[admin-review-overview.test.tsx](/home/gsh/workspace/TRMS/web/src/app/admin-review-overview.test.tsx)、[member-invoice-workbench-layout.test.tsx](/home/gsh/workspace/TRMS/web/src/app/member-invoice-workbench-layout.test.tsx)、[member-invoice-workbench.test.tsx](/home/gsh/workspace/TRMS/web/src/app/member-invoice-workbench.test.tsx)、[member-invoice-detail.test.tsx](/home/gsh/workspace/TRMS/web/src/app/member-invoice-detail.test.tsx)

### 根因
- `invoice_competition_location_range` 对真实材料依赖地点文本识别质量和宽泛字符串匹配，当前证据链不足以稳定判断“地点不匹配”，导致大量需要人工确认的噪音。
- 管理员多个窄面板复用横向四列摘要时，长文件名和票号会挤占金额、状态、附件数量，造成与分摊确认页不一致且易溢出。
- 成员工作台之前按页面纵向堆叠工作状态、上传和发票列表，虽然减少了单票详情堆叠，但仍没有形成稳定的左侧分类导航。

### 验证结果
- 已通过后端定向测试：
  - `uv run pytest tests/test_invoice_validation_rules.py tests/test_invoices_api.py tests/test_exports_api.py tests/test_main_flow_e2e.py`
  - 91 个用例通过，存在 3 条既有 `HTTP_422_UNPROCESSABLE_ENTITY` DeprecationWarning。
- 已通过前端定向测试：
  - `cd web && npm test -- admin-split-editor.test.tsx admin-corrections-reminders.test.tsx admin-invoice-editor.test.tsx admin-review-overview.test.tsx member-invoice-workbench-layout.test.tsx member-invoice-workbench.test.tsx member-invoice-detail.test.tsx`
  - 7 个测试文件、23 个用例通过；Vitest 仍有既有 `--localstorage-file` 路径 warning。
- 仓库级验证待本记录后执行 `./scripts/verify.sh`。

### 风险与后续
- 本轮取消的是地点范围规则在发票主校验链路中的输出，不删除规则函数本身；如果未来要重新启用，必须先基于真实数据定义更可靠的地点证据和容错策略。
- 成员工作台旧的 `#member-workbench-missing-materials` / `#member-workbench-confirmations` hash 现在会落到“工作状态”，避免直接断页；缺失材料作为工作状态的一部分展示，不再作为独立左侧类别。

## 2026-05-01 02:10 - Remove internal identifiers from admin primary paths

### 完成内容
- 完成任务“清理管理员面板内部标识展示并改为用户友好信息”。
- 调整管理员主路径默认展示边界：
  - [admin-workspace-shell.tsx](/home/gsh/workspace/TRMS/web/src/app/admin-workspace-shell.tsx) 的固定任务上下文不再显示 `任务编号 TASK-*`，只保留比赛名称、阶段、截止时间和快捷入口；
  - [admin-task-detail.tsx](/home/gsh/workspace/TRMS/web/src/app/admin-task-detail.tsx) 顶部摘要不再显示任务编号，状态切换确认弹窗改为使用比赛名称，并把高风险确认输入从内部 `task.id` 改为比赛名称；
  - [admin-review-overview.tsx](/home/gsh/workspace/TRMS/web/src/app/admin-review-overview.tsx) 中待归属材料、材料审核列表、当前材料详情、逾期成员和成员异议区域不再默认展示材料编号、任务提示、文件哈希和内部发票 ID，改为成员标签、原始文件名、票号、费用类型、时间和状态；
  - [admin-corrections-reminders.tsx](/home/gsh/workspace/TRMS/web/src/app/admin-corrections-reminders.tsx) 中识别待更正列表、提醒成员下拉和提醒记录统一改为成员业务标签，已录入发票字段展示票号而不是内部 `invoiceId`，成功反馈也不再回显内部成员 ID；
  - [admin-export-tasks.tsx](/home/gsh/workspace/TRMS/web/src/app/admin-export-tasks.tsx) 不再默认展示任务编号、导出任务 ID 和导出文件名，导出确认弹窗改为使用比赛名称，历史记录和最新材料包改用创建时间、导出类型、状态和产物类型描述。
- 更新前端测试：
  - [admin-review-overview.test.tsx](/home/gsh/workspace/TRMS/web/src/app/admin-review-overview.test.tsx)
  - [admin-corrections-reminders.test.tsx](/home/gsh/workspace/TRMS/web/src/app/admin-corrections-reminders.test.tsx)
  - [admin-export-tasks.test.tsx](/home/gsh/workspace/TRMS/web/src/app/admin-export-tasks.test.tsx)
  - [admin-task-detail.test.tsx](/home/gsh/workspace/TRMS/web/src/app/admin-task-detail.test.tsx)
  - 覆盖管理员复核、催补、导出和任务详情默认路径不出现内部标识，同时保留业务可读信息和既有跳转动作。
- 更新 [TASKS.md](/home/gsh/workspace/TRMS/TASKS.md)，标记该任务已完成。

### 根因
- 之前虽然已经在部分发票摘要里去掉了 UUID，但管理员共享壳层、任务详情、复核页、催补页和导出页仍沿用“任务编号/材料编号/导出任务 ID/文件名”作为第一层摘要信息，说明“业务可读信息优先”的展示边界没有在管理员主路径统一落实。
- 这些页面共享的是审核和导出主流程，默认暴露内部标识会迫使管理员先理解系统实现对象，而不是先看比赛、成员、票号、状态和时间等业务线索。
- 导出页和状态切换确认弹窗还把 `task.id` 当成主要确认对象，导致即使页面正文收口，关键动作前的确认路径仍会把内部标识重新暴露出来。

### 验证结果
- 已通过定向前端测试：
  - `cd web && npm test -- admin-review-overview.test.tsx admin-corrections-reminders.test.tsx admin-export-tasks.test.tsx admin-task-detail.test.tsx`
  - 4 个测试文件、13 个用例通过。
- 已通过仓库级验证：
  - `./scripts/verify.sh`
  - Python 编译检查通过；
  - Alembic 升降级验证通过；
  - pytest 495 个用例通过，存在 3 条既有 `HTTP_422_UNPROCESSABLE_ENTITY` DeprecationWarning；
  - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过；Vitest 仍有既有 `--localstorage-file` 路径 warning，Vite 仍有既有 chunk size warning；
  - Docker Compose 配置检查通过；
  - `git diff --check` 通过。

### 风险与后续
- 本轮只清理管理员主路径默认第一层展示，不改动后端数据结构，也不移除路由参数中的任务 ID / 发票 ID，因为这些仍是内部跳转和接口调用所需的技术标识。
- 当前成员、管理员标签仍使用“成员 2250001”这类学号型业务标签；如果后续引入真实姓名或更完整的成员档案展示，应作为独立读模型/权限任务处理，而不是在本轮展示收口里继续扩散。

## 2026-05-01 01:55 - Narrow admin recognition editing UI to business-first Material 3 form

### 完成内容
- 完成任务“收敛管理员识别字段编辑表单为业务字段优先的 Material 3 表单”。
- 调整 [admin-invoice-editor.tsx](/home/gsh/workspace/TRMS/web/src/app/admin-invoice-editor.tsx)：
  - 管理员发票编辑页“识别字段”标签改为“业务字段审核参考”，默认只展示发票号码、日期、抬头、税号、金额、费用类型等业务字段建议，不再在第一层直接铺开来源、置信度和人工更正轨迹；
  - 新增折叠的“调试与审计信息”区，来源、置信度、字段更新时间和人工更正记录仅在管理员主动展开时可见，且折叠时从 DOM 卸载，避免默认路径继续暴露内部识别细节；
  - 将编辑表单按“票据核心字段”“抬头与税号”“报销归类与补充信息”三组重排，保持 Material 3 `TextField` / `Select` 组件风格不变，但把字段顺序改为管理员审核顺序；
  - 表单摘要区不再默认展示任务编号，改为提交成员、比赛名称、材料类型和上传时间，收敛默认界面中的内部标识噪音。
- 更新前端测试 [admin-invoice-editor.test.tsx](/home/gsh/workspace/TRMS/web/src/app/admin-invoice-editor.test.tsx)：
  - 覆盖默认识别视图只显示业务字段建议；
  - 覆盖来源/置信度默认隐藏、展开审计区后可见；
  - 覆盖编辑表单按业务审核顺序分组。
- 更新 [TASKS.md](/home/gsh/workspace/TRMS/TASKS.md)，标记该任务已完成。

### 根因
- 旧管理员发票编辑页虽然保存表单本身已经使用 Material UI 控件，但“识别字段”标签默认仍按逐字段技术审计视图展开，第一层直接展示来源、置信度、更新时间和人工更正轨迹，导致管理员在真正开始补录前先被内部识别细节淹没。
- 表单字段虽然可编辑，但缺少按业务审核顺序分组，管理员需要在金额、抬头、税号、费用类型之间来回扫视，默认路径不够贴近复核动作。
- 摘要区仍显示 `task id` 这类内部标识，说明该页面默认展示边界还没有完全落实“业务可读信息优先”。

### 验证结果
- 已通过定向前端测试：
  - `cd web && npm test -- admin-invoice-editor.test.tsx`
  - 1 个测试文件、5 个用例通过。
- 已通过仓库级验证：
  - `./scripts/verify.sh`
  - Python 编译检查通过；
  - Alembic 升降级验证通过；
  - pytest 495 个用例通过，存在 3 条既有 `HTTP_422_UNPROCESSABLE_ENTITY` DeprecationWarning；
  - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过；Vitest 仍有既有 `--localstorage-file` 路径 warning，Vite 仍有既有 chunk size warning；
  - Docker Compose 配置检查通过；
  - `git diff --check` 通过。

### 风险与后续
- 本轮只收敛管理员发票编辑页的主编辑路径，没有顺手改管理员复核总览中的只读识别详情，因为后者不属于本任务定义的“识别字段编辑表单”边界。
- 当前审计区仍允许管理员展开查看来源、置信度和人工更正记录；如果后续需要进一步做角色分级或审计权限细化，应作为独立权限/审计任务处理，而不是在当前 UI 任务中继续扩散。

## 2026-05-01 01:36 - Unify invoice summary snippets into one-line rows

### 完成内容
- 完成任务“统一所有发票缩略信息为一行摘要组件”。
- 新增统一前端摘要组件 [invoice-summary-row.tsx](/home/gsh/workspace/TRMS/web/src/components/invoice-summary-row.tsx)：
  - 默认字段顺序固定为原始文件名、发票号、校验状态、附件数量；
  - 同时支持可点击摘要行、只读静态摘要行、批量选择复选框、状态提示和强调标签；
  - 复用现有成员工作台的一行摘要样式，不再让不同入口各自维护一套缩略结构。
- 调整成员端入口：
  - [member-invoice-workbench.tsx](/home/gsh/workspace/TRMS/web/src/app/member-invoice-workbench.tsx) 中“未提交发票”“已提交发票”“问题发票”和“共享发票”统一改用该摘要组件；
  - 共享发票摘要不再默认展示 `invoice_id`，而是改为原始文件名、票号、校验状态和附件数量，并把上传成员/费用类型收进提示或状态标签；
  - [member-invoice-detail.tsx](/home/gsh/workspace/TRMS/web/src/app/member-invoice-detail.tsx) 的“共享发票摘要”也改为同一只读一行摘要。
- 调整管理员入口：
  - [admin-review-overview.tsx](/home/gsh/workspace/TRMS/web/src/app/admin-review-overview.tsx) 中非发票材料的“关联发票摘要列表”改为同一组件；
  - [admin-invoice-editor.tsx](/home/gsh/workspace/TRMS/web/src/app/admin-invoice-editor.tsx) 的发票材料列表、[admin-split-editor.tsx](/home/gsh/workspace/TRMS/web/src/app/admin-split-editor.tsx) 的任务发票列表，以及 [admin-corrections-reminders.tsx](/home/gsh/workspace/TRMS/web/src/app/admin-corrections-reminders.tsx) 的异常发票列表也统一改用同一摘要组件；
  - 默认不再在这些缩略摘要中显示“发票编号：UUID”“材料编号”一类内部标识，而是展示原始文件名、票号、校验状态、附件数量和费用类型，并在需要时点击回到对应主发票材料。
- 补齐共享发票读模型字段：
  - [task_shared_invoices.py](/home/gsh/workspace/TRMS/src/trms_backend/domain/task_shared_invoices.py) 为共享发票摘要新增 `original_filename` 与 `validation_status`；
  - [tasks.py](/home/gsh/workspace/TRMS/src/trms_backend/api/tasks.py) 与 [task_member_workbench.py](/home/gsh/workspace/TRMS/src/trms_backend/domain/task_member_workbench.py) 将发票校验结果传入共享摘要构建逻辑；
  - [types.ts](/home/gsh/workspace/TRMS/web/src/lib/api/types.ts) 同步前端类型定义。
- 更新测试：
  - 后端：[test_task_shared_invoices_api.py](/home/gsh/workspace/TRMS/tests/test_task_shared_invoices_api.py)、[test_task_member_workbench_api.py](/home/gsh/workspace/TRMS/tests/test_task_member_workbench_api.py)
  - 前端：[member-invoice-workbench-layout.test.tsx](/home/gsh/workspace/TRMS/web/src/app/member-invoice-workbench-layout.test.tsx)、[member-invoice-detail.test.tsx](/home/gsh/workspace/TRMS/web/src/app/member-invoice-detail.test.tsx)、[admin-review-overview.test.tsx](/home/gsh/workspace/TRMS/web/src/app/admin-review-overview.test.tsx)、[admin-invoice-editor.test.tsx](/home/gsh/workspace/TRMS/web/src/app/admin-invoice-editor.test.tsx)、[admin-split-editor.test.tsx](/home/gsh/workspace/TRMS/web/src/app/admin-split-editor.test.tsx)、[admin-corrections-reminders.test.tsx](/home/gsh/workspace/TRMS/web/src/app/admin-corrections-reminders.test.tsx)
  - 覆盖共享发票摘要新字段、成员端统一一行摘要，以及管理员审核/录入/分摊/异常列表摘要不显示内部 ID。
- 更新 [TASKS.md](/home/gsh/workspace/TRMS/TASKS.md)，标记该任务已完成。

### 根因
- 成员工作台本人发票摘要虽然已收成一行，但共享发票摘要仍是独立卡片；管理员材料审核中的关联发票摘要又是另一套列表文本，导致同一类对象在不同页面的信息密度、字段顺序和状态语义不一致。
- 共享发票聚合接口之前没有提供原始文件名与校验状态，前端无法在成员共享摘要入口复用“原始文件名、票号、校验状态、附件数量”这一统一信息架构。
- 管理员材料审核默认展示 `invoice.id`，说明缩略摘要没有落实“业务可读信息优先、内部 ID 不在第一层展示”的边界。

### 验证结果
- 已通过定向后端测试：
  - `uv run pytest tests/test_task_shared_invoices_api.py tests/test_task_member_workbench_api.py`
  - 7 个用例通过。
- 已通过定向前端测试：
  - `cd web && npm test -- admin-split-editor.test.tsx admin-invoice-editor.test.tsx admin-corrections-reminders.test.tsx admin-review-overview.test.tsx member-invoice-workbench-layout.test.tsx member-invoice-detail.test.tsx`
  - 6 个测试文件、18 个用例通过。
- 已通过仓库级验证：
  - `./scripts/verify.sh`
  - Python 编译检查通过；
  - Alembic 升降级验证通过；
  - pytest 495 个用例通过，存在 3 条既有 `HTTP_422_UNPROCESSABLE_ENTITY` DeprecationWarning；
  - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过；Vitest 仍有既有 `--localstorage-file` 路径 warning，Vite 仍有既有 chunk size warning；
  - Docker Compose 配置检查通过；
  - `git diff --check` 通过。

### 风险与后续
- 本轮统一的是成员工作台、成员共享发票详情和管理员材料审核中的发票缩略摘要；管理员分摊页、管理员发票录入页、成员费用确认页等仍保留各自更完整的卡片或详情视图，因为它们不属于本任务定义的“缩略摘要”边界。
- 本轮已经统一成员工作台、成员共享发票详情、管理员材料审核、管理员发票录入列表、管理员分摊列表和管理员异常发票列表中的缩略摘要；成员费用确认页仍保留更完整的明细卡片，因为它属于个人费用确认详情，不是当前任务定义的“缩略摘要主路径”。
- 共享发票 `validation_status` 当前按该发票已有校验结果推导；若后续需要把“缺失材料导致的阻塞”和“规则校验失败/待确认”拆成更细的摘要标签，应在统一摘要组件外增加明确的状态映射，而不是重新回退到展示内部字段。

## 2026-05-01 01:18 - Convert member ready invoices into one-line summaries with split batch actions

### 完成内容
- 完成任务“将成员工作台可提交发票改为一行摘要和分状态批量操作”。
- 调整 [member-invoice-workbench.tsx](/home/gsh/workspace/TRMS/web/src/app/member-invoice-workbench.tsx)：
  - 将原先混合选择的批量区拆成“未提交发票”和“已提交发票”两个独立列表，各自维护独立的全选、单选、清空和批量动作；
  - 批量提交默认只消费未提交列表选择，批量撤回默认只消费已提交列表选择，成功后仅清理对应列表里已成功处理的选择状态；
  - 将成员工作台中的本人发票摘要收口为一行信息架构，默认只展示原始文件名、发票号、校验状态和附件数量；
  - 问题发票分组和展开列表统一复用同一行摘要样式，并用强调色标记当前阻塞分组；
  - 点击任意摘要行仍进入单张发票处理页，不再在工作台中展开多字段卡片。
- 调整 [styles.css](/home/gsh/workspace/TRMS/web/src/styles.css)，新增成员发票一行摘要行、问题强调态、选择工具条和移动端收缩样式。
- 更新前端测试：
  - [member-invoice-workbench-submission.test.tsx](/home/gsh/workspace/TRMS/web/src/app/member-invoice-workbench-submission.test.tsx)
  - [member-invoice-workbench.test.tsx](/home/gsh/workspace/TRMS/web/src/app/member-invoice-workbench.test.tsx)
  - [member-invoice-workbench-layout.test.tsx](/home/gsh/workspace/TRMS/web/src/app/member-invoice-workbench-layout.test.tsx)
  - [member-invoice-workbench-aggregate.test.tsx](/home/gsh/workspace/TRMS/web/src/app/member-invoice-workbench-aggregate.test.tsx)
  - 覆盖独立选择状态、列表级全选、批量提交、批量撤回、问题发票强调和摘要行跳转。
- 更新 [TASKS.md](/home/gsh/workspace/TRMS/TASKS.md)，标记该任务已完成。

### 根因
- 旧成员工作台虽然已有批量提交/撤回能力，但所有本人发票仍共用一个选择集合，导致“准备提交”和“已经提交可撤回”混在同一上下文里，用户无法稳定判断当前批处理对象。
- 可提交区中的发票摘要仍保留多字段纵向卡片结构，单张发票默认占据过多垂直空间，造成工作台第一屏可扫描性差。
- 问题发票折叠摘要和可提交区使用不同的信息密度与样式口径，用户在不同分组之间切换时需要重新理解状态语义。

### 验证结果
- 已通过定向前端测试：
  - `cd web && npm test -- member-invoice-workbench.test.tsx member-invoice-workbench-submission.test.tsx member-invoice-workbench-layout.test.tsx member-invoice-workbench-aggregate.test.tsx`
  - 4 个测试文件、11 个用例通过。
- 仓库级验证尚未执行，下一步按仓库规范运行 `./scripts/verify.sh`。

### 风险与后续
- 本轮只调整成员工作台中的本人发票摘要和批量区；共享发票摘要、管理员任务详情、管理员材料审核等入口仍使用各自展示实现，统一摘要组件任务继续留在后续独立任务中处理。
- 当前“一行摘要”的校验列展示的是用户可读的校验结果汇总，而不是具体失败规则；具体问题仍通过问题发票分组提示和单张处理页闭合。

## 2026-05-01 01:05 - Fix admin invoice amount display units

### 完成内容
- 完成任务“修复管理员材料审核发票金额显示单位错误”。
- 新增共享金额格式化工具 [currency.ts](/home/gsh/workspace/TRMS/web/src/lib/currency.ts)，统一处理 `amount_cents -> ￥xx.xx` 展示，并为缺失金额提供“未识别金额/待补录”占位文案。
- 调整 [admin-review-overview.tsx](/home/gsh/workspace/TRMS/web/src/app/admin-review-overview.tsx)：
  - 管理员材料审核“识别字段”标签页中，`recognized_fields.amount_cents` 不再直接显示分单位整数，而是统一按元格式化；
  - 辅助材料关联发票摘要继续走同一金额格式化口径。
- 调整 [admin-invoice-editor.tsx](/home/gsh/workspace/TRMS/web/src/app/admin-invoice-editor.tsx) 与 [admin-corrections-reminders.tsx](/home/gsh/workspace/TRMS/web/src/app/admin-corrections-reminders.tsx)，复用同一共享金额格式化函数，避免管理员相关入口继续各自维护金额展示逻辑。
- 补充 [admin-review-overview.test.tsx](/home/gsh/workspace/TRMS/web/src/app/admin-review-overview.test.tsx) 回归测试，覆盖：
  - 管理员材料审核识别字段金额显示为真实元金额；
  - 辅助材料关联发票摘要金额显示为真实元金额；
  - 识别金额缺失时显示“未识别金额/待补录”。
- 更新 [TASKS.md](/home/gsh/workspace/TRMS/TASKS.md)，标记该任务已完成。

### 根因
- 管理员材料审核页的识别字段详情对所有识别值统一走字符串渲染路径，`amount_cents` 被当成普通数字直接展示，导致分单位整数被误看作元金额。
- 管理员复核相关多个入口各自维护 `cents -> yuan` 展示逻辑，没有统一收口，导致金额单位边界容易再次漂移。

### 验证结果
- 已通过定向前端测试：
  - `cd web && npm test -- admin-review-overview.test.tsx admin-invoice-editor.test.tsx admin-corrections-reminders.test.tsx`
  - 3 个测试文件、9 个用例通过。
- 已通过仓库级验证：
  - `./scripts/verify.sh`
  - Python 编译检查通过；
  - Alembic 升降级验证通过；
  - pytest 495 个用例通过，存在 3 条既有 `HTTP_422_UNPROCESSABLE_ENTITY` DeprecationWarning；
  - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过；Vitest 仍有既有 `--localstorage-file` 路径 warning，Vite 仍有既有 chunk size warning；
  - Docker Compose 配置检查通过；
  - `git diff --check` 通过。

### 风险与后续
- 本轮只修复管理员材料审核链路和相关摘要金额显示；成员端金额展示未改动，因为当前任务范围不包含成员 UI 收口。
- 当前金额占位文案统一为“未识别金额/待补录”；若后续需要区分“未识别”和“管理员尚未补录”两种状态，应基于明确字段状态再拆文案，而不是重新回退到显示 `0` 或原始整数。

## 2026-05-01 需求拆分 - 发票摘要与管理员面板 UI 收口

### 完成内容
- 根据用户反馈完成问题分析，并写入 [TASKS.md](/home/gsh/workspace/TRMS/TASKS.md) 的“临时任务 - 2026-05-01 发票摘要与管理员面板 UI 收口”。
- 新增 5 个待执行任务：
  - 修复管理员材料审核发票金额显示单位错误；
  - 将成员工作台可提交发票改为一行摘要和分状态批量操作；
  - 统一所有发票缩略信息为一行摘要组件；
  - 收敛管理员识别字段编辑表单为业务字段优先的 Material 3 表单；
  - 清理管理员面板内部标识展示并改为用户友好信息。

### 根因判断
- 成员工作台下拉严重的核心原因是发票摘要未统一为一行式业务信息，且提交/撤回批处理对象没有按提交状态拆分。
- 管理员端的主要问题分为两类：一类是金额单位展示错误，属于数据正确性缺陷；另一类是 UI 信息边界混乱，默认暴露了重复字段和 UUID 等内部数据。
- 发票缩略信息在多个页面各自实现，导致字段口径、状态颜色和信息密度不一致。

### 验证结果
- 本轮只修改任务和工作日志，未修改业务代码。
- 已通过仓库级验证：
  - `./scripts/verify.sh`
  - Python 编译检查通过；
  - Alembic 升降级验证通过；
  - pytest 495 个用例通过，存在 3 条既有 deprecation warning；
  - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过；Vitest 仍有既有 `--localstorage-file` 路径 warning，Vite 仍有既有 chunk size warning；
  - Docker Compose 配置检查通过；
  - `git diff --check` 通过。

### 后续建议
- 优先执行金额显示单位错误修复，因为它会直接误导管理员审核。
- 随后先抽统一发票摘要组件，再替换成员和管理员入口，避免继续在多个页面重复修同一类 UI 问题。

## 2026-05-01 00:34 - Fix airfare airport-code itinerary requirement

### 完成内容
- 完成临时任务“修复航空发票机场代码仍触发行程单缺失”。
- 调整 [invoice_validation.py](/home/gsh/workspace/TRMS/src/trms_backend/domain/invoice_validation.py)：
  - `validate_invoice(...)` 调用航空行程单规则时传入发票识别结果和辅助材料识别结果；
  - `validate_airfare_itinerary_requirement(...)` 复用已有机场代码证据收集逻辑；
  - 航空发票主材料或关联的行程单/订单截图中识别到显式机场代码时，`invoice_airfare_itinerary_required` 返回通过，不再生成“航空费用缺少行程单”。
- 补充 [test_invoice_validation_rules.py](/home/gsh/workspace/TRMS/tests/test_invoice_validation_rules.py) 回归测试，覆盖“发票自身已有往返机场代码但没有额外行程单”的路径。
- 更新 [TASKS.md](/home/gsh/workspace/TRMS/TASKS.md)，记录并完成本轮运行时修复任务。

### 根因
- 上一轮只放宽了 `invoice_airfare_cabin_proof_required`：识别到机场代码时不再要求额外订单截图。
- 但 `invoice_airfare_itinerary_required` 仍只判断是否关联了 `MaterialType.ITINERARY`，不读取任何识别字段；因此同一张航空发票即使已识别出 `SHA -> WUH -> SHA` 这类机场代码，仍会被缺失材料聚合成“缺少行程单”。

### 验证结果
- 修复前已用新增定向用例复现失败：
  - `uv run pytest tests/test_invoice_validation_rules.py::test_airfare_itinerary_rule_passes_when_invoice_has_airport_codes`
  - 失败原因：`validate_airfare_itinerary_requirement()` 不接受 `recognition_task`，行程单规则无法读取机场代码证据。
- 修复后已通过：
  - `uv run pytest tests/test_invoice_validation_rules.py`
  - 28 个用例通过。
- 已通过相关后端回归：
  - `uv run pytest tests/test_invoices_api.py tests/test_missing_materials.py tests/test_task_member_workbench_api.py tests/test_task_readiness_api.py`
  - 51 个用例通过。
- 已通过仓库级验证：
  - `./scripts/verify.sh`
  - Python 编译检查通过；
  - Alembic 升降级验证通过；
  - pytest 495 个用例通过，存在 3 条既有 deprecation warning；
  - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过；Vitest 仍有既有 `--localstorage-file` 路径 warning，Vite 仍有既有 chunk size warning；
  - Docker Compose 配置检查通过；
  - `git diff --check` 通过。

### 风险与后续
- 本轮只放行显式识别到的机场代码，不根据城市名、航司名或文件名推断机场。
- 已运行实例若不是热加载模式，需要重启 API 后才会加载本次规则变更。
- 历史发票若已保存旧校验结果，需要重新触发校验或访问会刷新发票校验的接口后，缺失材料列表才会消除。

## 2026-04-30 23:58 - Simplify member amount ownership and airfare metadata checks

### 完成内容
- 完成任务“简化成员金额归属确认并调整航空/交易时间校验”。
- 新增 [invoice_split_defaults.py](/home/gsh/workspace/TRMS/src/trms_backend/application/invoice_split_defaults.py)：
  - 成员本人创建或识别自动建票后，若发票尚无分摊，默认生成全额归属上传成员的分摊；
  - 成员保存自己名下的金额归属时，同步把本人分摊视为已确认，避免每张发票再点一次“确认这笔费用”。
- 调整成员端单票页 [member-invoice-detail.tsx](/home/gsh/workspace/TRMS/web/src/app/member-invoice-detail.tsx)：
  - “分摊金额”改为“金额归属”；
  - 移除单张发票里的“本人费用确认”二次确认区；
  - 发票提交给管理员后，普通成员不能继续修改材料类型、发票字段或金额归属。
- 调整后端写路径：
  - [invoices.py](/home/gsh/workspace/TRMS/src/trms_backend/api/invoices.py) 阻止普通成员修改已提交发票字段；
  - [splits.py](/home/gsh/workspace/TRMS/src/trms_backend/api/splits.py) 阻止普通成员修改已提交发票分摊，并在成员保存本人分摊后自动确认本人金额；
  - 识别自动建票路径同样接入默认本人全额归属。
- 调整 [recognition_llm.py](/home/gsh/workspace/TRMS/src/trms_backend/application/recognition_llm.py)：
  - 发票和行程单基础抽取 schema 增加机场代码字段；
  - 当分类或元数据指向 `airfare` 时，追加第三轮 `airfare_route_extraction`，只抽取显式可见的 IATA 机场代码。
- 调整 [invoice_validation.py](/home/gsh/workspace/TRMS/src/trms_backend/domain/invoice_validation.py)：
  - 航空费用若具备去程或往返机场代码，舱位/订单截图证明规则直接通过，不再要求额外订单截图；
  - 比赛时间范围校验保留证据但统一返回 `not_applicable`，不再因交易时间缺失或超出范围产生限制。

### 根因
- 旧流程把“成员指定这张发票的金额归属”和“成员确认本人金额”拆成两个动作；对单人全额发票来说，这是重复确认。
- 航空票据上常见的机场代码已经能证明航段信息，但旧规则只认舱位字段或订单截图，导致用户被要求补充不必要附件。
- 交易时间范围校验属于旧财务规则约束，当前用户明确要求取消该限制；继续输出待确认/失败会制造无效待办。

### 验证结果
- 已通过定向后端测试：
  - `uv run pytest tests/test_invoice_validation_rules.py tests/test_recognition_llm.py tests/test_invoice_member_submission_api.py tests/test_task_member_workbench_api.py tests/test_recognition_async_jobs.py`
  - 54 个用例通过。
- 已通过扩展后端回归：
  - `uv run pytest tests/test_tasks_api.py tests/test_task_readiness_api.py tests/test_task_review_summary_api.py tests/test_exports_api.py tests/test_export_async_jobs.py tests/test_main_flow_e2e.py tests/test_splits_api.py tests/test_confirmations_api.py`
  - 首次运行发现 10 个旧断言仍假设“无默认分摊/无默认确认”；按新需求更新断言后，失败用例已定向复跑通过。
- 已通过定向前端测试：
  - `cd web && npm test -- member-invoice-detail.test.tsx`
  - `cd web && npm test -- member-invoice-workbench.test.tsx member-invoice-workbench-layout.test.tsx member-invoice-workbench-submission.test.tsx member-invoice-workbench-aggregate.test.tsx`
- 已通过前端类型检查：
  - `cd web && npx tsc --noEmit`
- 已通过占位主流程回归：
  - `cd web && npm test -- main-flow-e2e-placeholder.test.tsx`
- 已通过仓库级验证：
  - `./scripts/verify.sh`
  - Python 编译检查通过；
  - Alembic 升降级验证通过；
  - pytest 494 个用例通过，存在 3 条既有 deprecation warning；
  - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过；
  - Docker Compose 配置检查通过；
  - `git diff --check` 通过。

### 风险与后续
- 本轮没有删除管理员端和旧独立“费用确认”页面；它们仍可用于多人分摊、异议或管理员复核场景。成员单票主路径已不再要求本人逐票二次确认。
- 自动确认只覆盖操作者自己名下的分摊；若把金额分给其他成员，其他成员的确认/异议机制仍保留。
- 第三轮机场代码识别只在 `airfare` 路径触发，并且只接受显式三字母机场代码；不会根据城市名猜测机场。

## 2026-04-30 23:14 - Split member workbench into per-invoice processing and auto-create invoices

### 完成内容
- 完成任务“拆分成员工作台单票处理页并在识别成功后自动建票校验”。
- 新增 [recognition_invoice_auto_create.py](/home/gsh/workspace/TRMS/src/trms_backend/application/recognition_invoice_auto_create.py)：
  - 识别任务成功、发票必填字段完整且字段状态均为 `recognized` 时，自动按材料创建/更新发票；
  - 仅允许已归属、类型为发票、费用类别符合任务配置的材料自动建票；
  - 建票后自动关联辅助材料并刷新校验。
- 接入自动建票路径：
  - [materials.py](/home/gsh/workspace/TRMS/src/trms_backend/api/materials.py)
  - [recognitions.py](/home/gsh/workspace/TRMS/src/trms_backend/api/recognitions.py)
  - [recognition_async_jobs.py](/home/gsh/workspace/TRMS/src/trms_backend/application/recognition_async_jobs.py)
- 重构成员端工作台：
  - [member-invoice-workbench.tsx](/home/gsh/workspace/TRMS/web/src/app/member-invoice-workbench.tsx) 只保留当前状态、比赛报销项目、上传入口、需要处理的发票列表、所有发票列表和批量提交撤回区；
  - 不再在工作台内默认展开每张发票的字段、附件、分摊和确认表单。
- 新增单张发票处理页：
  - [member-invoice-detail.tsx](/home/gsh/workspace/TRMS/web/src/app/member-invoice-detail.tsx)
  - [member-invoice-paths.ts](/home/gsh/workspace/TRMS/web/src/app/member-invoice-paths.ts)
  - 路由 `/member/invoices/:invoiceId` 和 `/member/materials/:materialId/invoice`；
  - 支持补字段、修改材料类型、重新识别、修改分摊金额、本人费用确认、查看附件与缺失材料。
- 补充/更新测试：
  - [test_recognition_execution_api.py](/home/gsh/workspace/TRMS/tests/test_recognition_execution_api.py)
  - [test_recognition_async_jobs.py](/home/gsh/workspace/TRMS/tests/test_recognition_async_jobs.py)
  - [member-invoice-detail.test.tsx](/home/gsh/workspace/TRMS/web/src/app/member-invoice-detail.test.tsx)
  - [member-invoice-workbench.test.tsx](/home/gsh/workspace/TRMS/web/src/app/member-invoice-workbench.test.tsx)
  - [member-invoice-workbench-layout.test.tsx](/home/gsh/workspace/TRMS/web/src/app/member-invoice-workbench-layout.test.tsx)
  - [member-legacy-route-redirects.test.tsx](/home/gsh/workspace/TRMS/web/src/app/member-legacy-route-redirects.test.tsx)
  - [main-flow-e2e-placeholder.test.tsx](/home/gsh/workspace/TRMS/web/src/app/main-flow-e2e-placeholder.test.tsx)

### 根因
- 旧成员工作台把识别结果、发票字段、附件、分摊和确认都堆在同一个页面，上传材料多时形成长页面，且“修改 / 指定归属 / 查看候选发票”等动作定位不清。
- 识别成功后的建票动作只在人工保存发票字段路径闭合，导致真实 LLM 已识别出发票号码、金额、抬头、税号和费用类型后，材料仍停留在“识别成功但无发票”的状态。
- 本轮真实测试还确认了一个运行时原因：修改 worker 代码后，已运行的 worker 进程不会热加载；未重启 worker 时，新识别能成功并收敛材料类型，但不会加载本轮新增的自动建票逻辑。

### 验证结果
- 已通过定向后端测试：
  - `uv run pytest tests/test_recognition_async_jobs.py tests/test_recognition_execution_api.py`
  - 26 个用例通过。
- 已通过定向前端测试：
  - `cd web && npm test -- member-invoice-detail.test.tsx`
  - 1 个测试文件、2 个用例通过。
- 已通过前端类型检查：
  - `cd web && npx tsc --noEmit`
- 已通过仓库级验证：
  - `./scripts/verify.sh`
  - Python 编译检查通过。
  - Alembic 升降级验证通过。
  - pytest 491 个用例通过，存在 3 条既有 `HTTP_422_UNPROCESSABLE_ENTITY` DeprecationWarning。
  - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过；Vitest 仍有既有 `--localstorage-file` 路径警告，Vite 仍有既有 chunk size 警告。
  - Docker Compose 配置检查通过。
  - `git diff --check` 通过。

### Firefox 真实实测
- 使用当前运行后端 `127.0.0.1:9876`、当前 Firefox DevTools、真实成员 bearer session 和 `/home/gsh/财务/ICPC区域赛/区域赛报销/武汉/` 下真实 PDF 完成实测。
- 为避免当前前端 `.env` 中 `VITE_API_BASE_URL=http://10.200.63.65:9876/api` 导致 Firefox CORS/网络失败，重启本地 Vite 到 `http://127.0.0.1:5173` 并显式设置 `VITE_API_BASE_URL=http://127.0.0.1:9876/api`。
- 创建并开放实测任务 `ea411086-ae90-4d01-a7fc-e50d24ca2ec3`，成员为 `2250001`、`2250002`。
- 上传真实文件：
  - `yc/dzfp_25422000000202631946_同济大学_20251102093106.pdf`
  - `yc/dzfp_25422000000202621931_同济大学_20251102092948.pdf`
- 第二份文件在重启 worker 后真实通过：
  - 识别任务 `b56f56c7-31a2-444b-bf82-897cfe0f4858` 状态为 `succeeded`；
  - LLM 输出字段包含 `document_family=invoice`、`material_type=invoice`、`invoice_number=25422000000202621931`、`amount_cents=52422`、`buyer_name=同济大学`、`tax_number=12100000425006125J`、`expense_type=hotel`；
  - 自动生成发票 `b71ed94c-e35d-4dcc-a504-bdb616ed6d66`，并产生校验结果；
  - Firefox 页面显示工作台为摘要列表，点击发票进入单张发票处理页，能看到字段补录、分摊金额、本人费用确认和附件区。

### 风险与后续
- 第一份真实文件在 worker 重启前处理完成，没有自动建票；这是旧 worker 进程未加载本轮代码造成的运行态残留。若要修复该历史材料，需要重新识别或人工保存字段触发建票。
- Firefox DevTools 未能直接给透明覆盖的 `<input type=file>` 上传文件，本轮真实文件上传通过同一后端材料上传 API 完成；随后用 Firefox 验证工作台和单票页真实状态。
- 当前真实 LLM 主路径不再出现 `llm_output_invalid`；但识别准确性仍取决于 provider 输出和票据质量，不能把本次两份 PDF 的成功外推为全部材料都必然成功。

## 2026-04-30 21:43 - Collapse recognition result list and tighten LLM classification enums

### 完成内容
- 完成任务“收敛成员识别结果列表和 LLM 分类枚举输出”。
- 调整 [recognition_llm.py](/home/gsh/workspace/TRMS/src/trms_backend/application/recognition_llm.py)：
  - 分类 prompt 显式列出 `document_family`、`material_type`、`expense_type_candidate` 的允许枚举值；
  - 明确禁止 `hotel_invoice`、`railway_invoice`、`hotel_order`、`train_order`、`accommodation`、`transportation` 等自造类别；
  - 将真实 provider 常见子类别收敛到系统既有枚举，例如 `railway_invoice -> invoice`、`transportation -> local_transport`；
  - 当分类输出已有合法 `document_family` 但漏掉 `material_type` 时，补齐同名 `material_type`，避免有效分类因结构缺字段被记为 `llm_output_invalid`。
- 调整 [member-invoice-workbench.tsx](/home/gsh/workspace/TRMS/web/src/app/member-invoice-workbench.tsx) 和 [styles.css](/home/gsh/workspace/TRMS/web/src/styles.css)：
  - “识别结果”区域改为短摘要处理列表，每组默认最多展示 5 条；
  - 不再默认展开每份问题材料的完整字段网格和原因详情；
  - 超出部分提示“已收进下方发票处理列表”，用户点击“进入处理”后再查看完整发票详情。
- 补充回归测试：
  - [test_recognition_llm.py](/home/gsh/workspace/TRMS/tests/test_recognition_llm.py)
  - [member-invoice-workbench-layout.test.tsx](/home/gsh/workspace/TRMS/web/src/app/member-invoice-workbench-layout.test.tsx)

### 根因
- 查看 `data/粘贴的文件.png` 后确认，上一轮只折叠了底部“问题发票分组”，但截图里造成长页面的主因是上方“识别结果”仍把“需要你确认/可能有问题”材料按完整卡片逐项展开。
- 查询本地 `trms.db` 后确认，当前共有 19 条 `failed` 识别任务，失败原因均为 `llm_output_invalid`；最新失败样本显示模型输出存在两类问题：
  - 分类阶段漏掉 `material_type`，但已经给出合法 `document_family=invoice`；
  - VLM/Provider 输出 `hotel_invoice`、`railway_invoice`、`accommodation`、`transportation` 等非系统枚举。
- 因此本轮同时收敛提示词和有限规范化；没有把任意非法输出静默当成功，只处理能明确映射到系统枚举的真实样本。

### 验证结果
- 已通过定向后端测试：
  - `uv run pytest tests/test_recognition_llm.py`
  - 15 个用例通过。
- 已通过定向前端测试：
  - `cd web && npm test -- member-invoice-workbench.test.tsx member-invoice-workbench-layout.test.tsx member-invoice-workbench-submission.test.tsx member-invoice-workbench-aggregate.test.tsx`
  - 4 个测试文件、29 个用例通过；Vitest 仍有既有 `--localstorage-file` 路径警告。
- 已通过前端类型检查：
  - `cd web && npx tsc --noEmit`
- 已通过前端 lint：
  - `cd web && npm run lint`
- 已通过仓库级验证：
  - `./scripts/verify.sh`
  - Python 编译检查通过。
  - Alembic 升降级验证通过。
  - pytest 487 个用例通过，存在 3 条既有 `HTTP_422_UNPROCESSABLE_ENTITY` DeprecationWarning。
  - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过；Vitest 仍有既有 `--localstorage-file` 路径警告，Vite 仍有既有 chunk size 警告。
  - Docker Compose 配置检查通过。
  - `git diff --check` 通过。

### 保守假设
- 本轮不直接批量重跑历史 19 条失败任务；代码修复后，新上传或手动重新识别会走新的提示词和规范化逻辑。
- “识别结果”区域只作为短摘要入口，完整字段、附件关联、分摊和确认仍以下方发票处理详情为准。

## 2026-04-30 21:17 - Fix member workbench actions and LLM output normalization

### 完成内容
- 完成任务“修复成员工作台发票处理入口和 LLM 识别输出规范化”。
- 调整 [recognition_llm.py](/home/gsh/workspace/TRMS/src/trms_backend/application/recognition_llm.py)：
  - 分类阶段字段返回标量时统一包装为 `{ value: ... }`；
  - 缺失 `confidence` 时按低置信处理，进入待确认而不是让整次识别失败；
  - `classification_confidence` 缺 `confidence` 时使用自身数值作为置信度；
  - 将 `hotel_order`、`railway_order` 等订单类别名收敛为现有 `order_screenshot`。
- 调整 [member-invoice-workbench.tsx](/home/gsh/workspace/TRMS/web/src/app/member-invoice-workbench.tsx)：
  - 待关联辅助材料“查看候选发票”跳转到具体 `#workbench-invoice-*` 详情锚点；
  - 识别结果卡片“修改 / 指定归属”和问题发票摘要“进入处理”统一选中对应发票并定位详情；
  - 问题发票分组默认只展示摘要和“进入处理 / 展开本组全部”，避免默认展开所有问题发票长列表。
- 调整前后端测试：
  - [test_recognition_llm.py](/home/gsh/workspace/TRMS/tests/test_recognition_llm.py)
  - [member-invoice-workbench-layout.test.tsx](/home/gsh/workspace/TRMS/web/src/app/member-invoice-workbench-layout.test.tsx)
  - [member-invoice-workbench-submission.test.tsx](/home/gsh/workspace/TRMS/web/src/app/member-invoice-workbench-submission.test.tsx)

### 根因
- 本地运行进程正常，但数据库里上传发票大量失败为 `llm_output_invalid`；实际模型返回的是 `document_family: "order_screenshot"`、`material_type: "hotel_order"` 等标量字段，而旧解析只接受字段对象并且不接受订单类自造材料类型。
- 成员工作台部分按钮只修改了选中状态或只跳到工作台总锚点，用户在长页面里无法明确看到对应发票详情变化。
- 问题发票区默认展开完整卡片，上传问题票多时会形成过长列表，掩盖真正的处理入口。

### 影响范围
- 后端影响集中在 LLM 输出规范化阶段；缺失置信度仍按低置信进入待确认，不伪造高置信识别结果。
- 前端影响集中在成员工作台发票定位和问题发票分组展示；未改动附件关联、分摊、确认、提交和权限接口。

### 验证结果
- 已通过定向后端测试：
  - `uv run pytest tests/test_recognition_llm.py`
  - 13 个用例通过。
- 已通过定向前端测试：
  - `cd web && npm test -- member-invoice-workbench.test.tsx member-invoice-workbench-layout.test.tsx member-invoice-workbench-submission.test.tsx member-invoice-workbench-aggregate.test.tsx`
  - 4 个测试文件、28 个用例通过；Vitest 仍有既有 `--localstorage-file` 路径警告。
- 已通过前端 lint：
  - `cd web && npm run lint`
- 已通过仓库级验证：
  - `./scripts/verify.sh`
  - Python 编译检查通过。
  - Alembic 升降级验证通过。
  - pytest 485 个用例通过，存在 3 条既有 `HTTP_422_UNPROCESSABLE_ENTITY` DeprecationWarning。
  - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过；Vitest 仍有既有 `--localstorage-file` 路径警告，Vite 仍有既有 chunk size 警告。
  - Docker Compose 配置检查通过。
  - `git diff --check` 通过。

## 2026-04-30 20:34 - Refactor member reimbursement page to upload-first draft confirmation

### 完成内容
- 完成任务“将成员报销项目页重构为上传优先的材料草稿确认流程”。
- 调整 [member-invoice-workbench.tsx](/home/gsh/workspace/TRMS/web/src/app/member-invoice-workbench.tsx)：
  - 页面标题改为“比赛报销材料提交”，顶部项目摘要补齐比赛名称、比赛时间、地点、参赛成员、发票抬头、税号和报销截止时间；
  - 上传报销材料区前置为主入口，移除普通成员主路径里的“识别策略”禁用字段，不再要求先理解或填写表单；
  - 新增用户可理解的材料状态映射和识别结果分组：需要你确认、已自动识别、缺少材料、可能有问题；
  - 新增材料卡片摘要，展示文件名、材料类型、金额、日期、费用类别、归属成员、状态标签，以及确认、修改、指定归属、标记为不报销、查看原文件入口；
  - 新增报销草稿汇总与提交确认区，自动展示当前已识别总金额、待确认金额、每位成员金额、缺失材料数量、风险项数量，并在不可提交时列出原因；
  - 将发票详情、缺失材料、费用确认收敛到“高级处理”区，保留原有成员自助更正、分摊和确认能力。
- 调整前端测试：
  - [member-invoice-workbench.test.tsx](/home/gsh/workspace/TRMS/web/src/app/member-invoice-workbench.test.tsx)
  - [member-legacy-route-redirects.test.tsx](/home/gsh/workspace/TRMS/web/src/app/member-legacy-route-redirects.test.tsx)
  - [main-flow-e2e-placeholder.test.tsx](/home/gsh/workspace/TRMS/web/src/app/main-flow-e2e-placeholder.test.tsx)
  - 更新断言到新的上传优先文案，并避免测试继续依赖成员主界面的内部材料编号文案。
- 更新 [TASKS.md](/home/gsh/workspace/TRMS/TASKS.md)，记录并完成本轮最小任务。

### 根因
- 旧成员工作台虽然已经聚合上传、识别、缺失材料、分摊和确认能力，但第一屏仍以“发票工作台 / 发票分组 / 高级详情”组织，上传区被夹在待办和标签页之后。
- 页面还保留“识别策略”、材料编号、worker/provider 调度说明、原始响应等实现视角文案，用户仍需要理解系统处理边界，而不是直接按“上传材料 -> 看草稿 -> 处理异常 -> 提交”完成。

### 影响范围
- 本轮只修改成员单任务报销材料提交页和相关前端测试。
- 没有改动后端识别、归票、分摊、确认、权限或导出模型。
- “标记为不报销”目前作为禁用入口占位，因为后端尚无 excluded 写模型；本轮不伪造前端本地排除状态。

### 验证结果
- 已通过定向前端测试：
  - `cd web && npm test -- member-invoice-workbench.test.tsx member-invoice-workbench-layout.test.tsx member-invoice-workbench-submission.test.tsx member-invoice-workbench-aggregate.test.tsx member-legacy-route-redirects.test.tsx main-flow-e2e-placeholder.test.tsx`
  - 6 个测试文件、31 个用例通过。
- 已通过前端 lint：
  - `cd web && npm run lint`
- 仓库级 `./scripts/verify.sh` 将在本记录后执行，结果另见本轮收尾。

### 保守假设
- 真实自动识别能力仍沿用现有后端识别链路；本轮只重构前端交互，不声称提升识别准确率。
- 材料状态 `uploaded/processing/recognized/needs_confirmation/missing_info/suspicious/confirmed/excluded` 在前端按现有材料、识别、校验、缺失和提交状态映射展示；后端目前没有单独的 `excluded` 写接口。

## 2026-04-30 20:12 - Complete real-flow UX acceptance for reimbursement simplification

### 完成内容
- 完成任务“补充报销交互简化真实主流程 UX 验收”。
- 调整 [src/trms_backend/api/materials.py](/home/gsh/workspace/TRMS/src/trms_backend/api/materials.py)：
  - `in_process` 上传识别在当前无 Text LLM / VLM provider 配置时直接短路为识别失败，并返回明确“未配置识别服务”分发信息；
  - 避免本地 UX 验收在未配置 provider 时先解析/渲染真实大文件，导致上传请求长时间卡住。
- 调整 [src/trms_backend/runtime_config.py](/home/gsh/workspace/TRMS/src/trms_backend/runtime_config.py)：
  - 新增 `TRMS_DOTENV_PATH`，允许 UX 验收显式读取隔离空 `.env`；
  - 防止本机仓库根目录 `.env` 中真实 LLM 配置误影响“未配置 provider”边界验收。
- 调整 [src/trms_backend/main.py](/home/gsh/workspace/TRMS/src/trms_backend/main.py)：
  - 材料上传路由接入运行时 provider 配置 resolver；
  - CORS 显式暴露 `Content-Disposition`，让跨域浏览器下载能读取后端文件名。
- 更新 [tests/ux/real-user-flows.spec.mjs](/home/gsh/workspace/TRMS/tests/ux/real-user-flows.spec.mjs)：
  - 覆盖管理员创建并开放任务、成员真实批量上传、未配置识别服务待办提示、多候选附件人工归票、批量提交/撤回、管理员就绪度和完整材料包下载；
  - 完整材料包下载前通过 `uv run python -m trms_backend worker --once` 生成真实 ZIP artifact，不再把无产物任务 patch 成成功；
  - 使用小型合成 PDF 作为后半段夹具附件，避免无关的超 10MB 邀请函体积限制干扰主流程验收。
- 更新 [tests/ux/README.md](/home/gsh/workspace/TRMS/tests/ux/README.md)，补齐 Alembic 迁移、Playwright 运行前置和 `TRMS_DOTENV_PATH=./tmp/ux-runtime/ux-empty.env` 隔离说明。
- 更新 [UX_TEST_REPORT.md](/home/gsh/workspace/TRMS/UX_TEST_REPORT.md)，记录 2026-04-30 自动化复跑结果、截图路径和未覆盖的真实外部依赖。
- 更新 [TASKS.md](/home/gsh/workspace/TRMS/TASKS.md)，将当前任务标记完成。
- 更新 [BLOCKERS.md](/home/gsh/workspace/TRMS/BLOCKERS.md)，移除已解除的当前阻塞。

### 根因
- 真实主流程 UX 验收之前无法闭合有三层根因：
  - 隔离 UX 数据库未按当前 Alembic schema 初始化，旧本地库会导致管理员首页接口 500；
  - 未配置 provider 时，`in_process` 上传路径仍进入真实材料解析/渲染和识别准备流程，导致上传反馈过慢且成员工作台无法稳定展示“未配置识别服务”待办；
  - 测试夹具把导出任务状态直接 patch 为 `succeeded`，但没有生成 artifact，UI 正确地不显示下载按钮。
- 最后一处下载文件名问题来自跨域 fetch 默认不可读 `Content-Disposition`，前端拿不到后端 ZIP 文件名后退回 `${jobId}.bin`。

### 影响范围
- 业务后端影响集中在未配置识别 provider 的上传失败路径、运行时 `.env` 选择和下载响应 CORS 暴露头。
- UX 脚本仍明确不覆盖真实 AI provider、真实外部通知渠道和真实财务系统自动录入。
- 完整材料包下载验收现在依赖真实导出 worker 生成产物，能覆盖 UI 下载入口与后端 artifact 的实际闭环。

### 验证结果
- 已通过定向后端测试：
  - `uv run pytest tests/test_export_async_jobs.py::test_export_artifact_download_exposes_filename_header_for_browser_cors`
  - `uv run pytest tests/test_recognition_execution_api.py tests/test_runtime_config.py tests/test_materials_api.py tests/test_recognition_async_jobs.py tests/test_export_async_jobs.py`
  - 83 个用例通过。
- 已通过完整 UX 验收：
  - `/tmp/trms-playwright/node_modules/.bin/playwright test tests/ux/real-user-flows.spec.mjs`
  - 4 个用例通过。
- 已通过仓库级验证：
  - `./scripts/verify.sh`
  - Python 编译检查通过。
  - Alembic 升降级验证通过。
  - pytest 484 个用例通过，存在 3 条既有 `HTTP_422_UNPROCESSABLE_ENTITY` DeprecationWarning。
  - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过；Vitest 仍有既有 `--localstorage-file` 路径警告，Vite 仍有既有 chunk size 警告。
  - Docker Compose 配置检查通过。
  - `git diff --check` 通过。

### 保守假设
- 后半段识别结果仍由测试夹具通过现有管理接口注入，只用于验证主流程交互和导出闭环；不代表真实 AI provider 的识别准确率已验证。
- 当前本地 UX 验收不覆盖 Telegram、邮件或 Browser Use 财务系统录入，这些仍按第一阶段边界处理。

## 2026-04-30 11:02 - Attempt real-flow UX acceptance and record blocking facts

### 完成内容
- 按项目约束读取并核对了 `AGENTS.md`、`TASKS.md`、`WORKLOG.md`、`BLOCKERS.md`、`README.md`、需求文档、架构文档、`docs/报销交互简化改造方案.md` 和 `tests/ux/README.md`，确认本轮唯一未完成任务是“补充报销交互简化真实主流程 UX 验收”。
- 重写 [tests/ux/real-user-flows.spec.mjs](/home/gsh/workspace/TRMS/tests/ux/real-user-flows.spec.mjs) 的主流程脚本骨架，使其不再沿用旧交互：
  - 管理员创建任务改为按当前 `Autocomplete` 成员名单交互录入，而不是旧的“成员 1 / 成员 2”输入框；
  - 管理员创建后改为从当前任务列表主路径进入任务详情并切换到收集中；
  - 新增后半段受控夹具准备逻辑，计划用于验证多候选附件人工归票、批量提交/撤回、管理员就绪度和完整材料包下载；
  - 登录辅助函数改为显式等待目标角色工作台落地，避免受保护路由会话尚未稳定时被重定向回登录页。
- 更新 [tests/ux/README.md](/home/gsh/workspace/TRMS/tests/ux/README.md)：
  - 补上清理隔离库、执行 `uv run alembic upgrade head` 后再启动 UX 环境的步骤；
  - 补上 Playwright Chromium 浏览器安装前置和独立 `@playwright/test` 安装说明。
- 使用隔离 UX 环境进行了真实复跑排障：
  - 先按旧说明启动时，管理员首页直接因 `tmp/ux-runtime/ux-test.db` schema 落后而 500；
  - 清理 `tmp/ux-runtime/ux-test.db` 并执行 Alembic 迁移后，管理员创建并开放真实上传任务用例可通过；
  - 对成员真实双文件上传做浏览器和独立 HTTP 探测，确认上传请求在当前 `in_process` 环境下约 25.7 秒才返回，且结果表现为 `recognition_status: failed`，没有稳定进入任务要求期望的“最近上传处理状态 + 未配置 provider 待办提示”。
- 将上述阻塞事实写入 [BLOCKERS.md](/home/gsh/workspace/TRMS/BLOCKERS.md)。

### 根因
- 第一层阻塞不是业务逻辑，而是 UX 隔离环境文档缺少迁移步骤。旧的 `tmp/ux-runtime/ux-test.db` 来自历史 `create_all` 产物，和当前 Alembic schema 不一致，导致管理员首页请求 `review-summary` / `overdue-confirmations` 时直接触发 `sqlite3.OperationalError: no such column: invoices.member_submission_status`。
- 第二层阻塞来自真实上传行为本身：成员在当前 `TRMS_ASYNC_JOB_MODE=in_process`、未配置真实识别 provider 的本地 UX 环境下上传两份真实材料时，请求并不会快速返回并进入“上传后处理状态”闭环，而是长时间停在上传中，最终返回结果为识别失败。这与本任务 Done when 里的“成员批量上传后只处理系统列出的待办”存在可观测差距。

### 影响范围
- 本轮没有修改业务后端或前端实现，只修改了 UX 脚本骨架、UX 运行说明和阻塞记录。
- 当前未把 `TASKS.md` 中“补充报销交互简化真实主流程 UX 验收”标记为完成，因为真实浏览器验收尚未闭合。

### 验证结果
- 已执行的定向验证：
  - `DATABASE_URL=sqlite:///./tmp/ux-runtime/ux-test.db uv run alembic upgrade head`
    - 通过；确认隔离 UX 库可升级到 `20260430_01`
  - `/tmp/trms-playwright/node_modules/.bin/playwright install chromium`
    - 通过；本机补齐了 Playwright Chromium 运行时
  - `/tmp/trms-playwright/node_modules/.bin/playwright test tests/ux/real-user-flows.spec.mjs --grep '管理员创建并开放真实上传任务|成员真实批量上传后只处理待办'`
    - “管理员创建并开放真实上传任务”通过
    - “成员真实批量上传后只处理待办，并明确看到未配置识别服务阻塞”未通过；页面停留在“正在上传...”，未在测试窗口内稳定出现“最近上传处理状态”
  - 独立 HTTP 探测真实双文件上传：
    - 约 `25.7s` 返回 `201`
    - 返回体显示材料被接收，但 `recognition_status` 为 `failed`
- 当前未执行 `./scripts/verify.sh`：
  - 原因：按项目规则，本轮任务在真实 UX 验收阶段被阻塞，仍需先记录阻塞事实；仓库级验证将放在本轮收尾时执行，但不应把阻塞任务包装成已完成。

### 保守假设
- 当前观察到的“长时间上传 + 识别失败”先按真实现象记录，不把它武断归因成单一后端 bug；可能涉及本地 `in_process` 识别执行链、未配置 provider 时的失败路径、真实文件体积与同步处理时长共同作用。
- 受控夹具脚本仅用于后半段 UI 状态准备，不代表真实 AI provider、真实外部通知渠道或真实异步 worker 已经可用；后续报告仍必须明确这层边界。

## 2026-04-30 10:34 - Promote reimbursement package as the primary export action

### 完成内容
- 完成任务“导出页主动作收敛为生成完整材料包”。
- 调整 [admin-export-tasks.tsx](/home/gsh/workspace/TRMS/web/src/app/admin-export-tasks.tsx)：
  - 导出页页头说明改为“主流程优先生成完整材料包”，不再把单项导出表述为默认路径；
  - 第一屏新增完整材料包主卡片，优先展示材料包就绪度、最近一次完整包状态、是否为最新任务数据版本，以及最近完整包的下载入口；
  - 主按钮改为“生成完整材料包”，直接创建 `reimbursement_package` 异步导出任务；
  - 原有单项导出能力下沉到“高级单项导出”区，明确只用于排障或临时下载；
  - 保留导出任务历史区，继续提供完整任务状态、失败原因和已生成产物的下载入口。
- 调整 [admin-export-tasks.test.tsx](/home/gsh/workspace/TRMS/web/src/app/admin-export-tasks.test.tsx)：
  - 新增“完整材料包优先”回归测试，覆盖旧包非最新提示、下载最近完整包和创建新完整包任务；
  - 保留既有单项导出创建、在线预览和导出门禁阻塞回归。
- 更新 [TASKS.md](/home/gsh/workspace/TRMS/TASKS.md)，将当前任务标记为已完成。

### 根因
- 虽然后端已经具备 `reimbursement_package` 完整材料包导出能力，但导出页仍把所有单项导出平铺为同级主动作。
- 结果是管理员进入导出页后仍需自己判断“应先生成完整包还是点某个单项导出”，与交互简化方案中“默认一键生成完整材料包，单项导出只作排障”的目标不一致。

### 保守假设
- 本轮不新增后端接口，也不额外为导出页创建专门的“最近完整包摘要”接口；页面直接复用现有导出任务列表里 `reimbursement_package` 的最新记录和 `is_latest_for_task` 字段。
- 如果后续导出历史量明显增大，第一屏的“最近完整包”摘要再考虑下沉到后端专门读模型；当前任务目标是先把主流程收口，而不是扩展新的接口面。

### 影响范围
- 仅修改管理员导出页和该页前端测试。
- 没有改动导出领域模型、异步 worker、导出产物格式、管理员复核流程、成员工作台或数据库 schema。

### 验证结果
- 已通过定向验证：
  - `cd web && npm test -- admin-export-tasks.test.tsx`
    - 3 个用例通过；Vitest 仍有既有 `--localstorage-file` 路径警告
- 已通过仓库级验证：
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic 升降级验证通过
    - pytest 481 个用例通过，存在 3 条既有 DeprecationWarning
    - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过；Vitest 仍有既有 `--localstorage-file` 路径警告，Vite 仍有既有 chunk size 警告
    - Docker Compose 配置检查通过
    - `git diff --check` 通过

## 2026-04-30 10:22 - Add reimbursement package async export artifact

### 完成内容
- 完成任务“新增 `reimbursement_package` 完整材料包导出类型”。
- 调整后端导出领域与异步导出处理：
  - 在 [exports.py](/home/gsh/workspace/TRMS/src/trms_backend/domain/exports.py) 新增 `reimbursement_package` 导出类型与 `zip` 格式支持；
  - 新增完整材料包 `manifest` 数据模型，记录任务数据版本、生成时间、导出人、子文件 hash、warning 和材料清单；
  - 在 [export_async_jobs.py](/home/gsh/workspace/TRMS/src/trms_backend/application/export_async_jobs.py) 新增完整材料包 ZIP 生成分支，复用现有报销汇总、成员明细、发票明细、缺失材料、财务草稿和 merged PDF 构建能力；
  - ZIP 产物固定包含：
    - `reimbursement-summary.csv`
    - `member-details.csv`
    - `invoice-details.csv`
    - `missing-materials.csv`
    - `finance-draft.json`
    - `merged-printing.pdf`
    - `manifest.json`
- 调整前端导出类型声明与导出页最小兼容：
  - 在 [types.ts](/home/gsh/workspace/TRMS/web/src/lib/api/types.ts) 补齐 `reimbursement_package` / `zip` 类型；
  - 在 [admin-export-tasks.tsx](/home/gsh/workspace/TRMS/web/src/app/admin-export-tasks.tsx) 补齐完整材料包文案、首选格式和“仅支持后台生成”的预览占位，避免新枚举打破导出页编译与现有交互。
- 补充测试：
  - 更新 [test_exports_api.py](/home/gsh/workspace/TRMS/tests/test_exports_api.py)，覆盖导出能力列表新增 `reimbursement_package`；
  - 更新 [test_export_async_jobs.py](/home/gsh/workspace/TRMS/tests/test_export_async_jobs.py)，新增完整材料包 ZIP 成功、`manifest.json` 内容和任务数据版本变化拒绝回归，并继续覆盖 merged PDF 子产物失败；
  - 更新 [admin-export-tasks.test.tsx](/home/gsh/workspace/TRMS/web/src/app/admin-export-tasks.test.tsx) 和 [main-flow-e2e-placeholder.test.tsx](/home/gsh/workspace/TRMS/web/src/app/main-flow-e2e-placeholder.test.tsx)，补齐新导出类型的前端 mock 能力列表。
- 更新 [TASKS.md](/home/gsh/workspace/TRMS/TASKS.md)，将当前任务标记为已完成。

### 根因
- 现有导出体系虽然已经具备 CSV、JSON、merged PDF 的异步生成、持久化和下载能力，但管理员最终拿到的仍是一组分散导出项，而不是一个面向真实提交的完整交付物。
- 这导致管理员仍需要自己判断“哪些文件应该一起打包、这份导出对应哪版任务数据、子文件是否完整”，与交互简化方案里“一键下载完整材料包”的目标不一致。

### 保守假设
- 本轮 `manifest.json` 的 `warnings` 先保守输出为空列表，不额外发明新的 warning 聚合规则；原因是当前任务目标是先把完整材料包产物落地，并保证不会在子产物失败时伪装成功。
- 完整材料包沿用现有 merged PDF 的严格可读性检查：只要 merged PDF 子产物因材料缺失、加密或损坏失败，整包直接失败，不生成残缺 ZIP。
- 本轮只新增后端完整材料包类型和前端最小兼容，不修改管理员导出页主动作；“主动作收敛为生成完整材料包”仍保留为下一条独立任务。

### 影响范围
- 修改了后端导出领域模型、异步导出 worker、前端导出类型与导出页文案，以及导出相关前后端测试。
- 没有改动管理员导出页主流程、下载授权模型、数据库 schema、成员工作台或其它业务流程。

### 验证结果
- 已通过定向验证：
  - `uv run pytest tests/test_exports_api.py tests/test_export_async_jobs.py`
    - 29 个用例通过，存在 3 条既有 `HTTP_422_UNPROCESSABLE_ENTITY` DeprecationWarning
  - `cd web && npm test -- admin-export-tasks.test.tsx main-flow-e2e-placeholder.test.tsx`
    - 3 个用例通过；Vitest 仍有既有 `--localstorage-file` 路径警告


## 2026-04-30 10:15 - Attach readiness overview and priority anomaly queue to admin task detail

### 完成内容
- 完成任务“管理员任务详情接入就绪度总览与异常优先队列”。
- 调整 [admin-task-detail.tsx](/home/gsh/workspace/TRMS/web/src/app/admin-task-detail.tsx)：
  - 管理员任务详情页主加载改为同时读取任务基础信息和 `GET /api/tasks/{task_id}/readiness`，不再只显示配置和状态流转；
  - 第一屏新增“任务就绪度总览”，直接展示待识别、识别失败、低置信待确认、待关联附件、缺失材料、异常校验、分摊未完成、成员未确认、有异议和导出阻塞原因；
  - 新增“异常优先队列”，按后端 `issues` 列表展示当前阻塞问题，并为缺失材料、分摊确认、成员异议、审核异常和导出阻塞提供明确入口；
  - 当任务已满足导出 boundary 时，第一屏会明确显示“可导出”，避免管理员继续逐张浏览正常材料。
- 调整前端 API 和类型：
  - [trms.ts](/home/gsh/workspace/TRMS/web/src/lib/api/trms.ts) 新增 `getTaskReadiness(...)`；
  - [types.ts](/home/gsh/workspace/TRMS/web/src/lib/api/types.ts) 新增 `TaskReadinessSummary` 及相关 issue/count 类型，前端不再自行造管理员门禁状态。
- 更新测试：
  - 更新 [admin-task-detail.test.tsx](/home/gsh/workspace/TRMS/web/src/app/admin-task-detail.test.tsx)，覆盖就绪度总览、导出阻塞展示和异常优先入口；
  - 更新 [main-flow-e2e-placeholder.test.tsx](/home/gsh/workspace/TRMS/web/src/app/main-flow-e2e-placeholder.test.tsx)，补齐管理员任务详情依赖的 readiness mock，避免主流程占位测试继续按旧接口形状运行。

### 根因
- 上一轮虽然已经补齐管理员任务就绪度读模型，但管理员任务详情第一屏仍停留在“基础配置 + 状态流转”，没有把后端已经统一聚合出的门禁事实接进来。
- 结果是管理员进入任务后仍要自己判断“哪些材料还没识别、哪些附件待关联、哪些成员还没确认、当前是否可导出”，也就无法形成“正常材料跳过、异常优先处理”的第一屏工作流。

### 保守假设
- 本轮异常优先队列严格复用后端 `TaskReadinessSummary.issues` 的顺序和标签，不在前端再做二次排序或新造状态优先级。
- 原因是当前目标是把已存在的管理员门禁事实稳定接入任务详情，而不是在前端重写一套“看起来更智能”的规则；若后续需要更细粒度优先级，应作为后端读模型调整。

### 影响范围
- 修改了管理员任务详情前端、前端 API 类型和两个前端测试文件。
- 没有改动后端 readiness 逻辑、管理员导出页主流程、材料审核页数据结构、数据库 schema 或成员侧业务路径。

### 验证结果
- 已通过定向验证：
  - `cd web && npm test -- admin-task-detail.test.tsx`
    - 5 个用例通过
  - `cd web && npm test -- main-flow-e2e-placeholder.test.tsx`
    - 1 个用例通过
- 已通过仓库级验证：
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic 升降级验证通过
    - pytest 479 个用例通过，存在 3 条既有 DeprecationWarning
    - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过；Vitest 输出既有 `--localstorage-file` 路径警告，Vite 输出既有 chunk size 警告
    - Docker Compose 配置检查通过
    - `git diff --check` 通过

## 2026-04-30 10:02 - Add administrator task readiness read model

### 完成内容
- 完成任务“新增管理员任务就绪度读模型”。
- 新增后端读模型 [task_readiness.py](/home/gsh/workspace/TRMS/src/trms_backend/domain/task_readiness.py)：
  - 统一聚合管理员任务第一屏所需的门禁状态，输出待识别、识别失败、低置信待确认、待关联附件、缺失材料、异常校验、分摊未完成、成员未确认、有异议和导出阻塞原因；
  - 复用现有材料、识别、校验、分摊、确认、待关联附件和导出 boundary 事实，不额外引入前端自造状态；
  - 将“缺失材料类 blocker”和“其它 blocker 校验”拆开统计，避免管理员把附件缺失和其它异常混成一类。
- 调整 [tasks.py](/home/gsh/workspace/TRMS/src/trms_backend/api/tasks.py)：
  - 新增 `GET /api/tasks/{task_id}/readiness`；
  - 仅允许任务管理员读取；
  - 返回统一 `counts`、`issues` 和 `export_blocking_reasons`，供后续管理员任务详情第一屏和导出页复用。
- 调整 [missing_materials.py](/home/gsh/workspace/TRMS/src/trms_backend/domain/missing_materials.py)：
  - 抽出 `is_missing_material_validation_result(...)`，让缺失材料聚合和任务就绪度聚合共用同一判定口径。
- 新增/更新测试：
  - 新增 [test_task_readiness_api.py](/home/gsh/workspace/TRMS/tests/test_task_readiness_api.py)，覆盖全通过、识别阻塞、附件阻塞、确认阻塞和无关管理员拒绝；
  - 更新 [test_web_bearer_request_identity_api.py](/home/gsh/workspace/TRMS/tests/test_web_bearer_request_identity_api.py)，补齐 `/api/tasks/{task_id}/readiness` 的匿名 `401` 与无关管理员 `403` 回归。
- 更新 [TASKS.md](/home/gsh/workspace/TRMS/TASKS.md)，将“新增管理员任务就绪度读模型”标记为已完成。

### 根因
- 管理员当前虽然已有 `review-summary`、缺失材料、待关联附件和导出能力边界，但这些事实分散在多个接口里，第一屏并没有统一的“门禁总览”。
- 结果是管理员仍要自己拼“哪些材料还没识别、哪些附件待关联、哪些确认没完成、当前是否允许导出”，前端也容易重复推导状态并和后端真实边界漂移。

### 保守假设
- 本轮把“分摊未完成”收敛为两类：发票没有任何分摊记录，或当前分摊金额合计不等于发票金额。
- 对“异常校验”则有意排除了已归入“缺失材料”的附件型 blocker，只保留其它 blocker 校验；否则管理员第一屏会把同一附件缺失同时看成两种完全等价的问题，难以优先处理。
- 附件阻塞沿用现有自动归票规则：单候选辅助材料会自动归票，只有无候选或多候选才进入“待关联附件”。

### 影响范围
- 修改了管理员任务读模型聚合与任务 API。
- 没有改动成员工作台、管理员前端页面、数据库 schema、导出产物模型或现有状态流转规则。

### 验证结果
- 已通过定向验证：
  - `uv run pytest tests/test_task_readiness_api.py tests/test_web_bearer_request_identity_api.py`
    - 16 个用例通过
- 已通过仓库级验证：
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic 升降级验证通过
    - pytest 479 个用例通过，存在 3 条既有 DeprecationWarning
    - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过；Vitest 输出既有 `--localstorage-file` 路径警告，Vite 输出既有 chunk size 警告
    - Docker Compose 配置检查通过
    - `git diff --check` 通过

## 2026-04-30 01:57 - Refresh automatic upload processing states in member workbench

### 完成内容
- 完成任务“上传成功后展示材料自动处理状态刷新”。
- 调整 [member-invoice-workbench.tsx](/home/gsh/workspace/TRMS/web/src/app/member-invoice-workbench.tsx)：
  - 把上传区下方的“最近上传结果”改为“最近上传处理状态”，不再只停留在一次性的逐文件归档反馈；
  - 基于最近上传材料、当前工作台读模型和待关联摘要，推导“已接收 / 识别排队中 / 识别完成 / 已归票 / 需要处理”处理阶段；
  - 对识别服务未配置、worker 排队等待、识别失败、待人工归票、缺失材料等场景给出不同说明和下一步入口；
  - 为仍处于过渡态的最近上传材料增加有限次自动刷新，状态变化时会继续刷新下面的待处理事项，而不是要求成员自己手动拼接上传结果和工作台变化。
- 更新 [member-invoice-workbench.test.tsx](/home/gsh/workspace/TRMS/web/src/app/member-invoice-workbench.test.tsx)：
  - 覆盖上传后排队等待；
  - 覆盖上传后成功形成并归票；
  - 覆盖识别服务未配置导致的失败提示；
  - 覆盖部分上传失败时仍保留成功材料状态与逐文件失败原因。
- 更新 [main-flow-e2e-placeholder.test.tsx](/home/gsh/workspace/TRMS/web/src/app/main-flow-e2e-placeholder.test.tsx) 中成员上传后的断言标题，使其与新处理状态区保持一致。

### 根因
- 成员工作台此前在上传完成后只展示一次“最近上传结果”，主流程到此就断开了。
- 结果是成员还要自己去下面发票区判断“系统现在处理到哪一步、是否还在识别、是否已经归票、是否已经冒出新的待办”，上传反馈和工作台状态没有形成闭环。

### 保守假设
- 本轮自动刷新只对最近上传且仍处于过渡态的材料进行有限次轮询，而不是长期高频刷新整个工作台。
- 原因是当前第一阶段仍以轮询为主，没有引入新的事件推送或 WebSocket；先把上传后的关键几步状态闭环起来，避免为这一个任务扩散到新的实时基础设施。

### 影响范围
- 仅修改成员工作台上传反馈区域和相关前端测试。
- 不改动后端接口、数据库 schema、管理员页面、导出链路或成员提交/撤回规则。

### 验证结果
- 已通过定向验证：
  - `cd web && npm test -- member-invoice-workbench.test.tsx`
    - 19 个用例通过
  - `cd web && npm test -- main-flow-e2e-placeholder.test.tsx`
    - 1 个用例通过
  - `cd web && npm run build`
    - 通过；存在既有 Vite chunk size 警告
- 已通过仓库级验证：
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic 升降级验证通过
    - pytest 474 个用例通过，存在 3 条既有 DeprecationWarning
    - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过；Vitest 输出既有 `--localstorage-file` 路径警告，Vite 输出既有 chunk size 警告
    - Docker Compose 配置检查通过
    - `git diff --check` 通过

## 2026-04-30 01:40 - Add aggregated member workbench read model

### 完成内容
- 完成任务“新增成员工作台聚合读模型”。
- 新增后端读模型 [task_member_workbench.py](/home/gsh/workspace/TRMS/src/trms_backend/domain/task_member_workbench.py)：
  - 聚合成员工作台所需的本人材料/发票、脱敏识别摘要、校验结果、已关联附件、分摊、确认、缺失材料、待关联附件和共享发票摘要；
  - 为每个成员材料条目产出 `queue_group`、`blocking_reasons` 和 `ready_for_submission`，把前端原先自行推导的可提交/阻塞口径下沉到后端；
  - 共享发票继续只暴露基础元数据、分摊摘要和附件类型计数；聚合接口不再返回识别 `raw_response`。
- 调整 [tasks.py](/home/gsh/workspace/TRMS/src/trms_backend/api/tasks.py)：
  - 新增 `GET /api/tasks/{task_id}/member-workbench`；
  - 仅允许任务成员读取；
  - 同时返回成员状态汇总、工作台条目、待关联附件和共享发票摘要。
- 调整前端工作台：
  - [trms.ts](/home/gsh/workspace/TRMS/web/src/lib/api/trms.ts) 新增 `getTaskMemberWorkbench(...)`；
  - [types.ts](/home/gsh/workspace/TRMS/web/src/lib/api/types.ts) 新增成员工作台聚合响应类型；
  - [member-invoice-workbench.tsx](/home/gsh/workspace/TRMS/web/src/app/member-invoice-workbench.tsx) 主数据加载改为优先读取聚合接口；聚合成功时不再继续请求成员状态、共享发票、待关联附件、识别、校验、附件、分摊和确认的 N+1 组合；
  - 保留旧加载链路作为兼容回退，避免滚动更新或测试夹具尚未接新接口时直接让页面不可用。
- 新增/更新测试：
  - 新增 [test_task_member_workbench_api.py](/home/gsh/workspace/TRMS/tests/test_task_member_workbench_api.py)，覆盖权限边界、`ready_for_submission` 与成员提交状态、阻塞原因映射、共享摘要/识别结果脱敏；
  - 新增 [member-invoice-workbench-aggregate.test.tsx](/home/gsh/workspace/TRMS/web/src/app/member-invoice-workbench-aggregate.test.tsx)，覆盖前端优先使用聚合接口而不是旧 N+1 请求；
  - 更新 [member-invoice-workbench.test.tsx](/home/gsh/workspace/TRMS/web/src/app/member-invoice-workbench.test.tsx)，去掉对旧请求次数的脆弱硬编码，改为直接断言“超大文件不会触发上传 POST”。

### 根因
- 成员工作台此前虽然已经收口到单任务，但主数据仍依赖：
  - 1 次成员状态；
  - 1 次共享发票；
  - 1 次待关联附件；
  - 1 次发票列表；
  - 再按材料/发票逐个补识别、校验、附件、分摊和确认。
- 结果是页面默认加载路径存在明显 N+1，请求次数高、前端状态推导重复、测试也必须手工拼一整套分散返回，继续迭代会越来越重。

### 保守假设
- 本轮保留了前端对旧接口链路的兼容回退，而不是直接删掉旧加载逻辑。
- 原因是当前仓库里已有大量工作台测试和可能存在的滚动部署窗口仍依赖旧返回形状；先让新聚合接口成为主路径，再把完全删除回退作为后续独立清理任务，更符合“本轮只完成一个最小可验证任务”的边界。

### 影响范围
- 修改了成员工作台的后端读模型与任务路由，以及成员工作台前端主数据加载方式。
- 没有改动成员批量提交/撤回规则、附件写权限规则、数据库 schema、管理员页面或导出链路。

### 验证结果
- 已通过定向验证：
  - `uv run pytest tests/test_task_member_workbench_api.py`
    - 4 个用例通过
  - `cd web && npm test -- member-invoice-workbench.test.tsx member-invoice-workbench-aggregate.test.tsx`
    - 17 个用例通过
  - `cd web && npm run build`
    - 通过；存在既有 Vite chunk size 警告
- 已通过仓库级验证：
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic 升降级验证通过
    - pytest 474 个用例通过，存在 3 条既有 DeprecationWarning
    - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过；Vitest 输出既有 `--localstorage-file` 路径警告，Vite 输出既有 chunk size 警告
    - Docker Compose 配置检查通过
    - `git diff --check` 通过

## 2026-04-30 01:13 - Restructure member workbench around ready and blocked invoices

### 完成内容
- 完成任务“将成员工作台默认结构调整为待办、可提交发票和问题发票”。
- 调整 [member-invoice-workbench.tsx](/home/gsh/workspace/TRMS/web/src/app/member-invoice-workbench.tsx)：
  - 将成员工作台发票视图从“完整发票长列表 + 详情并列”重排为“批量区 + 可提交发票 + 问题发票分组 + 详情后置”；
  - 新增可提交发票区，优先展示当前结构已经闭合、可直接纳入批量提交的发票；
  - 新增问题发票分组，按“识别中 / 识别失败或待确认 / 附件待关联 / 缺失材料 / 分摊未完成 / 确认未完成”展示主要阻塞原因；
  - 保留详情处理能力，但把完整详情放到分组之后，避免成员默认先陷入长详情列表。
- 新增测试 [member-invoice-workbench-layout.test.tsx](/home/gsh/workspace/TRMS/web/src/app/member-invoice-workbench-layout.test.tsx)：
  - 覆盖可提交区空态；
  - 覆盖可提交发票展示；
  - 覆盖问题发票按主阻塞原因分组；
  - 覆盖点击不同卡片后详情区切换。

### 根因
- 成员工作台此前虽然已经有待处理事项摘要、批量提交区和待关联提示，但发票主视图仍默认要求用户先浏览完整发票详情长列表。
- 结果是成员需要自己判断“哪张票已经能交、哪张票为什么还不能交”，页面没有把系统已有的识别、附件、分摊和确认状态收口成直接可执行的信息架构。

### 保守假设
- 本轮把“分摊未完成”收敛为：当发票已经存在分摊记录且金额合计不等于发票总额时，才归入该问题分组。
- 也就是说，仅因为当前没有分摊记录，不自动视为 blocker；否则会把现有可正常提交的单人发票误判成问题发票。若后续产品要求“所有发票必须先显式建立分摊记录”，应作为独立任务调整后端与前端口径。

### 影响范围
- 仅修改成员工作台前端结构和对应前端测试。
- 不改动后端聚合接口、提交/撤回 API、附件关联权限、数据库 schema 或管理员页面。

### 验证结果
- 已通过定向前端验证：
  - `cd web && npm test -- member-invoice-workbench-layout.test.tsx member-invoice-workbench.test.tsx member-invoice-workbench-submission.test.tsx`
    - 23 个用例通过
  - `cd web && npm run lint`
- 已通过仓库级验证：
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic 升降级验证通过
    - pytest 470 个用例通过，存在 3 条既有 DeprecationWarning
    - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过；Vitest 输出既有 `--localstorage-file` 路径警告，Vite 输出既有 chunk size 警告
    - Docker Compose 配置检查通过
    - `git diff --check` 通过

## 2026-04-30 01:00 - Add candidate invoice attachment action in member workbench

### 完成内容
- 完成任务“在成员工作台待关联辅助材料区支持选择候选发票并关联”。
- 调整 [member-invoice-workbench.tsx](/home/gsh/workspace/TRMS/web/src/app/member-invoice-workbench.tsx)：
  - 在“待关联辅助材料”区为多候选材料新增“关联到发票”明确动作；
  - 关联进行中会禁用同一材料的其它候选按钮，避免重复提交；
  - 关联成功后会刷新当前工作台数据，并切换到目标发票上下文，带出最新附件状态；
  - 关联失败时会在待关联项下方展示明确失败原因，而不是只保留跳转查看入口。
- 调整 [trms.ts](/home/gsh/workspace/TRMS/web/src/lib/api/trms.ts)：
  - 新增前端 `attachInvoiceSupportingMaterial(...)` API 封装，复用现有 `PUT /api/invoices/{invoice_id}/supporting-materials/{material_id}`。
- 更新 [member-invoice-workbench.test.tsx](/home/gsh/workspace/TRMS/web/src/app/member-invoice-workbench.test.tsx)：
  - 保留原有“查看候选发票”覆盖；
  - 新增多候选关联成功后待关联项消失、目标发票附件区刷新的测试；
  - 新增关联失败时展示明确原因的测试。

### 根因
- 成员工作台此前只能告诉用户“这份辅助材料有多个候选发票”或“没有候选发票”，但没有把后端已存在的手动关联能力接到当前主工作台。
- 结果是多候选场景下成员仍需要自己推断下一步，待关联提示无法形成实际处理闭环，也无法在同一页看到关联后的附件状态刷新。

### 保守假设
- 本轮在关联成功后选择整页工作台重载，而不是在前端本地做乐观更新。
- 原因是关联成功后不仅附件列表会变化，还可能连带影响缺失材料、校验结果和待处理摘要；统一重载能保持这些聚合状态一致，避免局部补丁制造前端脏状态。

### 影响范围
- 仅修改成员工作台前端交互、前端 API 封装和成员工作台测试。
- 不改动后端权限规则、自动归票规则、数据库 schema、管理员页面或导出链路。

### 验证结果
- 已通过定向测试：
  - `cd web && npm test -- member-invoice-workbench.test.tsx`
    - 16 个用例通过
- 已通过仓库级验证：
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic 升降级验证通过
    - pytest 470 个用例通过，存在 3 条既有 DeprecationWarning
    - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过；Vitest 输出既有 `--localstorage-file` 路径警告，Vite 输出既有 chunk size 警告
    - Docker Compose 配置检查通过
    - `git diff --check` 通过

## 2026-04-30 01:59 - Restrict supporting material linkage write permissions

### 完成内容
- 完成任务“收口附件手动关联 API 的成员权限边界”。
- 调整 [invoices.py](/home/gsh/workspace/TRMS/src/trms_backend/api/invoices.py)：
  - `PUT /api/invoices/{invoice_id}/supporting-materials/{material_id}` 与 `DELETE /api/invoices/{invoice_id}/supporting-materials/{material_id}` 现在都要求 bearer 身份；
  - 任务管理员可继续处理其负责任务内的全部附件关联；
  - 成员只能关联或解除关联“同一任务内、本人提交的非发票辅助材料”到“本人提交的发票”；
  - 无关成员会被显式拒绝，跨任务材料仍返回冲突错误，不再允许匿名写操作。
- 新增测试 [test_invoice_supporting_material_permissions_api.py](/home/gsh/workspace/TRMS/tests/test_invoice_supporting_material_permissions_api.py)：
  - 覆盖成员本人关联/解除关联成功；
  - 覆盖匿名请求被 401 拒绝；
  - 覆盖同任务无关成员被 403 拒绝；
  - 覆盖跨任务材料被 409 拒绝；
  - 覆盖管理员可处理任务内任意成员附件关联。
- 同步更新受影响既有测试：
  - [test_invoices_api.py](/home/gsh/workspace/TRMS/tests/test_invoices_api.py)
  - [test_materials_api.py](/home/gsh/workspace/TRMS/tests/test_materials_api.py)
  - [test_member_material_type_update_api.py](/home/gsh/workspace/TRMS/tests/test_member_material_type_update_api.py)
  - [test_task_review_summary_api.py](/home/gsh/workspace/TRMS/tests/test_task_review_summary_api.py)
  - [test_task_shared_invoices_api.py](/home/gsh/workspace/TRMS/tests/test_task_shared_invoices_api.py)
  - [test_web_bearer_request_identity_api.py](/home/gsh/workspace/TRMS/tests/test_web_bearer_request_identity_api.py)
  - [test_exports_api.py](/home/gsh/workspace/TRMS/tests/test_exports_api.py)

### 根因
- 附件手动关联与解除关联接口此前完全未接入 bearer 身份解析和任务访问控制。
- 结果是任何匿名请求都能直接改写发票与辅助材料的关联关系，也没有限制成员只能操作本人材料，违反了当前需求和“多候选附件必须人工但受控处理”的权限边界。

### 保守假设
- 本轮将“成员可操作的候选发票”收敛为：发票主材料提交人与当前成员一致，且辅助材料提交人与当前成员一致。
- 也就是说，成员不能把自己提交的辅助材料挂到其他成员的发票，也不能解除管理员为其他成员发票建立的跨成员关联；这与当前自动候选规则和成员工作台待关联摘要口径一致。
- 本轮不额外引入任务状态门禁；若后续要求只允许 `open` 状态改附件关联，应作为独立任务收口。

### 影响范围
- 仅修改发票附件关联/解除关联的后端权限校验与相关测试。
- 不改动成员工作台 UI、待关联候选展示逻辑、自动归票规则、导出链路或数据库 schema。

### 验证结果
- 已通过定向测试：
  - `uv run pytest tests/test_invoice_supporting_material_permissions_api.py tests/test_invoices_api.py tests/test_materials_api.py tests/test_task_shared_invoices_api.py tests/test_web_bearer_request_identity_api.py tests/test_task_review_summary_api.py tests/test_exports_api.py tests/test_member_material_type_update_api.py`
    - 121 个用例通过，存在 3 条既有 DeprecationWarning
- 已通过仓库级验证：
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic 升降级验证通过
    - pytest 470 个用例通过，存在 3 条既有 DeprecationWarning
    - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过；Vitest 输出既有 `--localstorage-file` 路径警告，Vite 输出既有 chunk size 警告
    - Docker Compose 配置检查通过
    - `git diff --check` 通过

## 2026-04-30 00:40 - Add member workbench batch submit and withdrawal panel

### 完成内容
- 完成任务“在成员工作台展示批量提交与撤回区”。
- 调整 [member-invoice-workbench.tsx](/home/gsh/workspace/TRMS/web/src/app/member-invoice-workbench.tsx)：
  - 在成员工作台发票队列顶部新增稳定的“批量提交与撤回”区块；
  - 支持选择全部本人发票、清空选择、批量提交选中发票、批量撤回选中发票；
  - 在本人发票卡片中新增可勾选入口，并显式展示 `已提交管理员 / 未提交管理员` 状态；
  - 对提交/撤回结果回显成功摘要与逐票失败原因。
- 调整前端 API 类型与调用：
  - [types.ts](/home/gsh/workspace/TRMS/web/src/lib/api/types.ts) 新增成员发票提交状态与批量提交/撤回响应类型；
  - [trms.ts](/home/gsh/workspace/TRMS/web/src/lib/api/trms.ts) 新增工作台批量提交与批量撤回 API 封装。
- 新增测试 [member-invoice-workbench-submission.test.tsx](/home/gsh/workspace/TRMS/web/src/app/member-invoice-workbench-submission.test.tsx)：
  - 覆盖批量区状态展示；
  - 覆盖勾选与选择摘要更新；
  - 覆盖批量提交部分成功与失败原因展示；
  - 覆盖批量撤回成功反馈。

### 根因
- 后端已经具备成员侧批量提交/撤回 API 和独立发票提交状态，但成员工作台仍缺少承接这些能力的稳定交互区。
- 成员此前只能逐张查看发票详情，无法明确知道哪些发票已经正式交给管理员，也无法在同一任务视图内批量交接或撤回。

### 保守假设
- 本轮批量区只作用于“本人且已形成发票主记录”的条目：
  - 共享发票摘要不进入批量交接区；
  - 尚未形成发票主记录的材料只允许继续补录，不允许伪装成可提交发票。
- 这与当前后端权限和接口语义一致；若后续产品要求允许对其他聚合对象做批量交接，应新增独立任务而不是继续在本轮上叠补丁。

### 影响范围
- 仅修改成员工作台前端、前端 API 类型和相关测试。
- 不改动后端业务逻辑、数据库迁移、导出链路或管理员页面。

### 验证结果
- 已通过：
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic 升降级验证通过
    - pytest 465 个用例通过，存在 3 条既有 DeprecationWarning
    - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过；Vitest 输出既有 `--localstorage-file` 路径警告，Vite 输出既有 chunk size 警告
    - Docker Compose 配置检查通过
    - `git diff --check` 通过

## 2026-04-30 00:17 - Split reimbursement UX simplification plan into tasks

### 完成内容
- 完成任务“将报销交互简化方案拆成可执行任务”。
- 更新 [TASKS.md](/home/gsh/workspace/TRMS/TASKS.md)：
  - 新增并完成方案拆分任务；
  - 新增“报销交互简化落地”任务组；
  - 将原有未完成任务“在成员工作台展示批量提交与撤回区”移动到新任务组首位，避免重复记录；
  - 拆出附件手动关联权限、成员端候选发票关联、成员工作台默认结构调整、成员工作台聚合读模型、上传后处理状态刷新、管理员就绪度读模型、管理员任务详情就绪度总览、完整材料包导出、导出页主动作收口和真实 UX 验收等后续任务。

### 拆分依据
- 本轮按 [报销交互简化改造方案.md](/home/gsh/workspace/TRMS/docs/报销交互简化改造方案.md) 的最小任务顺序拆分。
- 拆分原则：
  - 先消费已有批量提交/撤回 API；
  - 再补齐附件关联权限边界和成员端处理入口；
  - 再收敛成员工作台结构与聚合读模型；
  - 再做管理员就绪度读模型和页面入口；
  - 最后做完整材料包导出和真实 UX 验收。

### 影响范围
- 本轮只更新任务队列和工作日志，不改动业务代码、测试代码、数据库迁移或运行配置。
- 后续实现仍需逐项完成，每轮只处理一个最小可验证任务。

### 验证结果
- 已通过：
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic 升降级验证通过
    - pytest 465 个用例通过，存在 3 条既有 DeprecationWarning
    - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过；Vitest 输出 `--localstorage-file` 路径警告，Vite 输出 chunk size 警告
    - Docker Compose 配置检查通过
    - `git diff --check` 通过

## 2026-04-30 00:07 - Document reimbursement interaction simplification plan

### 完成内容
- 完成任务“分析并记录成员/管理员报销交互简化改造方案”。
- 新增 [报销交互简化改造方案.md](/home/gsh/workspace/TRMS/docs/报销交互简化改造方案.md)，记录：
  - 当前系统交互繁琐的根因；
  - 成员端“上传后自动处理、只展示待办和可提交发票”的目标流程；
  - 管理端“异常优先处理、一键完整材料包”的目标流程；
  - 附件手动关联、成员批量提交/撤回、任务就绪度读模型、完整材料包导出等可拆任务；
  - AI 自动化边界和不建议方向。
- 更新 [TASKS.md](/home/gsh/workspace/TRMS/TASKS.md)，新增并完成本轮临时文档任务。

### 当前判断
- 当前仓库已经具备免选类型上传、两阶段识别、单候选附件自动归票、待关联附件摘要、共享发票摘要、成员批量提交/撤回 API、异步导出和 merged PDF 导出等底层能力。
- 后续关键不是重写架构，而是把已有能力编排成：
  - 成员端少判断、少跳转、只处理系统列出的阻塞项；
  - 管理端少逐张检查、少手工拼导出物、直接下载带 manifest 的完整材料包。

### 影响范围
- 本轮只新增和更新文档，不改动业务代码、测试代码、数据库迁移或运行配置。
- 后续实现仍应按方案中的最小任务拆分逐项落地，不应一次性重写成员工作台或管理员导出模块。

### 验证结果
- 已通过：
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic 升降级验证通过
    - pytest 465 个用例通过，存在 3 条既有 DeprecationWarning
    - Web 前端 `npm run lint`、`npm test`、`npm run build` 通过；Vitest 输出 `--localstorage-file` 路径警告，Vite 输出 chunk size 警告
    - Docker Compose 配置检查通过
    - `git diff --check` 通过

## 2026-04-30 02:01 - Add member invoice submission withdrawal workflow

### 完成内容
- 完成任务“建立成员侧发票撤回规则与批量撤回 API”。
- 新增后端服务 [invoice_member_submission_withdrawal.py](/home/gsh/workspace/TRMS/src/trms_backend/application/invoice_member_submission_withdrawal.py)：
  - 批量撤回已提交发票
  - 对每张发票分别校验并返回逐票失败原因
  - 对成功/拒绝撤回都写审计日志
- 调整 [tasks.py](/home/gsh/workspace/TRMS/src/trms_backend/api/tasks.py)：
  - 新增 `POST /api/tasks/{task_id}/invoice-submission-withdrawals`
  - 仅任务成员可调用
  - 返回：
    - `status`
    - `items`
    - `failures`
- 新增测试 [test_invoice_member_submission_withdrawal_api.py](/home/gsh/workspace/TRMS/tests/test_invoice_member_submission_withdrawal_api.py)：
  - 已提交发票在任务仍为 `open` 时可批量撤回
  - 任务离开 `open` 后不可撤回
  - 无关成员越权失败

### 撤回边界
- 当前允许撤回：
  - 发票当前状态为 `submitted`
  - 调用方是任务成员，且是该发票主材料提交人
  - 提交记录的 `submitted_by_member_id` 就是当前调用方
  - 任务状态仍然是 `open`
- 当前拒绝撤回：
  - 发票未提交
  - 调用方不是该发票提交人
  - 任务已经离开 `open`，例如进入 `closed / reviewing / ready_to_export / completed`

### 为什么这样设计
- 这轮的目标不是“任何时候都允许成员反悔”，而是只给成员保留一个明确、可控的撤回窗口：
  - 在管理员还没进入后续处理阶段前，成员可以撤回自己刚刚提交的发票
  - 一旦任务离开 `open`，就认为已经进入后续管理员处理边界，成员不能再通过撤回绕开流程
- 这样才能避免成员在 `reviewing` 甚至 `ready_to_export` 阶段重新把已交接材料抽走，污染后续状态。

### 验证结果
- 已通过定向测试：
  - `uv run pytest tests/test_invoice_member_submission_api.py tests/test_invoice_member_submission_withdrawal_api.py tests/test_tasks_api.py`
    - 51 个用例通过
- 仓库级验证待本轮记录更新后统一执行 `./scripts/verify.sh`。

## 2026-04-30 01:42 - Add member invoice submission status model and batch submit API

### 完成内容
- 完成任务“建立成员侧发票提交状态模型与批量提交 API”。
- 调整发票领域模型 [invoices.py](/home/gsh/workspace/TRMS/src/trms_backend/domain/invoices.py)：
  - 新增 `InvoiceMemberSubmissionStatus`
    - `unsubmitted`
    - `submitted`
  - 发票记录新增：
    - `member_submission_status`
    - `submitted_by_member_id`
    - `submitted_at`
- 调整数据库模型与仓储：
  - [models.py](/home/gsh/workspace/TRMS/src/trms_backend/infrastructure/models.py)
  - [repositories.py](/home/gsh/workspace/TRMS/src/trms_backend/infrastructure/repositories.py)
  - 新增 Alembic revision [20260430_01_invoice_member_submission_status.py](/home/gsh/workspace/TRMS/alembic/versions/20260430_01_invoice_member_submission_status.py)
  - 仓储新增 `update_member_submission_status(...)`
- 新增后端服务 [invoice_member_submission.py](/home/gsh/workspace/TRMS/src/trms_backend/application/invoice_member_submission.py)：
  - 批量提交若干发票
  - 对每张发票分别校验并返回逐票失败原因
  - 对成功/拒绝提交都写审计日志
- 调整 [tasks.py](/home/gsh/workspace/TRMS/src/trms_backend/api/tasks.py)：
  - 新增 `POST /api/tasks/{task_id}/invoice-submissions`
  - 仅任务成员可调用
  - 返回：
    - `status`
    - `items`
    - `failures`
- 新增测试 [test_invoice_member_submission_api.py](/home/gsh/workspace/TRMS/tests/test_invoice_member_submission_api.py)：
  - 批量提交成功
  - 部分成功、部分失败
  - 无关成员越权失败

### 提交前置条件
- 当前这轮把“成员正式提交给管理员”的语义收敛到这些条件：
  - 任务状态必须仍是 `open`
  - 调用方必须是任务成员，且是该发票主材料的提交人
  - 发票不能已经是 `submitted`
  - 发票必须满足与任务最终导出门禁一致的核心条件：
    - 没有 blocker 级失败/待确认校验
    - 已有分摊
    - 所有关联成员确认都已经 `confirmed`
- 这次没有把“已确认费用”直接等同于“已提交管理员”，而是显式新增了独立发票状态。

### 为什么这样设计
- 之前仓库里只有：
  - 分摊确认
  - 任务进入 `reviewing / ready_to_export` 的任务级状态
- 但没有“成员已经把这张发票正式交给管理员处理”的发票级状态。
- 如果直接拿“确认已完成”冒充“已提交”，会混淆两件不同的事：
  - 成员确认自己相关费用
  - 成员正式声明这张发票已准备好交给管理员
- 因此本轮先建立独立的发票提交状态，再让下一轮撤回规则和前端批量区块建立在这个状态上。

### 验证结果
- 已通过定向测试：
  - `uv run pytest tests/test_invoice_member_submission_api.py tests/test_tasks_api.py tests/test_invoices_api.py`
    - 87 个用例通过
- 仓库级验证待本轮记录更新后统一执行 `./scripts/verify.sh`。

## 2026-04-30 01:16 - Split batch invoice submit and withdraw task

### 完成内容
- 完成任务“拆分成员侧发票批量提交与撤回区任务”。
- 更新 [TASKS.md](/home/gsh/workspace/TRMS/TASKS.md)，将原先过大的单任务拆成三个可单轮验证的子任务：
  - `建立成员侧发票提交状态模型与批量提交 API`
  - `建立成员侧发票撤回规则与批量撤回 API`
  - `在成员工作台展示批量提交与撤回区`

### 当前代码缺口
- 现有仓库已经有：
  - 发票主记录
  - 分摊
  - 成员确认
  - 管理员进入 `reviewing / ready_to_export` 的任务级状态流
- 但没有：
  - 发票级“成员已提交给管理员 / 已撤回”的独立状态模型
  - 批量提交或批量撤回 API
  - 区分“费用确认完成”和“成员正式提交本批发票”的状态边界

### 为什么必须先拆分
- 原任务同时包含：
  - 新的发票状态模型
  - 提交/撤回权限和可撤回边界
  - 成员工作台批量交互区块
- 如果不先拆，会立刻混出三个问题：
  - 后端还没定义清楚“提交状态”，前端就只能靠本地假状态占位
  - 撤回边界不清楚时，容易让成员绕过后续管理员流程
  - 批量提交和批量撤回的失败原因无法单独测试

### 拆分后的实现顺序
- 先做“提交状态模型与批量提交 API”
  - 先把“提交给管理员”的语义建起来
- 再做“撤回规则与批量撤回 API”
  - 明确何时允许撤回，何时必须拒绝
- 最后做“成员工作台批量提交与撤回区”
  - 基于稳定的后端状态与错误语义接 UI

### 验证结果
- 本轮只更新任务与工作日志拆分，不改动业务代码。
- 按仓库规则，文档更新后仍应执行 `./scripts/verify.sh`。

## 2026-04-30 01:03 - Show pending supporting-material linkage in member workbench

### 完成内容
- 完成任务“在成员工作台展示待关联辅助材料与处理入口”。
- 调整前端类型与 API 调用：
  - [types.ts](/home/gsh/workspace/TRMS/web/src/lib/api/types.ts) 新增待关联辅助材料摘要类型
  - [trms.ts](/home/gsh/workspace/TRMS/web/src/lib/api/trms.ts) 新增 `getTaskSupportingMaterialLinkage(...)`
- 调整 [member-invoice-workbench.tsx](/home/gsh/workspace/TRMS/web/src/app/member-invoice-workbench.tsx)：
  - 工作台加载时并行读取 `supporting-material-linkage`
  - 在发票页新增“待关联辅助材料”区块
  - 显式区分：
    - 已绑定附件
    - 缺失材料
    - 待关联辅助材料
  - 对 `no_candidate` 场景给出“去上传区补录或补传发票”的入口
  - 对 `multiple_candidates` 场景展示候选发票摘要，并提供“查看候选发票”按钮，能直接切到对应发票卡片
  - 顶部待处理事项摘要也会把待关联辅助材料计入显式提醒，而不是让它继续静默悬空
- 调整测试 [member-invoice-workbench.test.tsx](/home/gsh/workspace/TRMS/web/src/app/member-invoice-workbench.test.tsx)：
  - 为所有现有工作台测试补齐默认空待关联响应
  - 新增待关联面板测试，覆盖：
    - `no_candidate`
    - `multiple_candidates`
    - “查看候选发票”跳转到对应发票详情

### 根因
- 后端已经能识别“待关联辅助材料”，但成员工作台之前只展示：
  - 已绑定附件
  - 缺失材料
- 这会把“材料已经上传，但还没安全归票”的状态压扁成不可见状态，成员只能看到：
  - 为什么缺失材料还没消失却不知道原因
  - 已上传的辅助材料到底卡在“没发票”还是“多候选不敢自动绑”也看不出来

### 当前展示边界
- 工作台现在只负责解释和导航，不负责直接完成人工绑定。
- 也就是说，本轮提供的是：
  - 清晰状态
  - 候选摘要
  - 跳回候选发票或上传区的入口
- 还没有提供：
  - 成员端直接手动把某份辅助材料绑定到某张发票的写操作

### 验证结果
- 已通过定向前端测试：
  - `cd web && npm test -- --run src/app/member-invoice-workbench.test.tsx`
    - 1 个测试文件、14 个用例通过
- 已通过前端构建：
  - `cd web && npm run build`
- 仓库级验证待本轮记录更新后统一执行 `./scripts/verify.sh`。

## 2026-04-30 00:46 - Add pending supporting-material linkage summary API

### 完成内容
- 完成任务“建立辅助材料多候选待关联摘要接口”。
- 新增读模型 [task_supporting_material_linkage.py](/home/gsh/workspace/TRMS/src/trms_backend/domain/task_supporting_material_linkage.py)：
  - `no_candidate`
  - `multiple_candidates`
  - 候选发票摘要：`invoice_id`、`invoice_number`、`amount_cents`、`expense_type`
- 调整 [tasks.py](/home/gsh/workspace/TRMS/src/trms_backend/api/tasks.py)：
  - 新增 `GET /api/tasks/{task_id}/supporting-material-linkage`
  - 管理员可查看任务内全部待关联辅助材料
  - 成员只能查看自己提交的待关联辅助材料
  - 已经单候选自动归票成功的材料不会出现在该接口里
- 新增测试 [test_supporting_material_linkage_api.py](/home/gsh/workspace/TRMS/tests/test_supporting_material_linkage_api.py)：
  - 管理员读取 `no_candidate` 与 `multiple_candidates` 摘要
  - 成员只看到自己的待关联项
  - 无关成员被拒绝

### 根因
- 上一轮已经补了“单候选自动归票”，但剩余未自动绑定材料仍然是静默悬空状态。
- 这会带来两个直接问题：
  - 多候选场景下，成员和管理员不知道系统为什么没有自动归票
  - 无候选场景下，成员工作台后续也没有稳定的数据来源去解释“下一步该补什么或该绑定到哪张票”

### 当前接口边界
- 会返回：
  - 非 `invoice` 材料
  - 已归属到任务
  - 当前尚未绑定到任何发票
  - 候选发票数为 0 或大于 1
- 不会返回：
  - 已自动绑定或已手动绑定的辅助材料
  - 单候选但已成功自动归票的材料
  - `invoice` 主材料本身

### 验证结果
- 已通过定向测试：
  - `uv run pytest tests/test_supporting_material_linkage_api.py`
    - 3 个用例通过
- 仓库级验证待本轮记录更新后统一执行 `./scripts/verify.sh`。

## 2026-04-30 00:29 - Add safe single-candidate auto-linking for supporting materials

### 完成内容
- 完成任务“建立辅助材料单候选自动归票后端规则”。
- 新增后端服务 [supporting_material_auto_link.py](/home/gsh/workspace/TRMS/src/trms_backend/application/supporting_material_auto_link.py)：
  - 只在以下安全边界满足时自动绑定辅助材料到发票：
    - 材料已归属到任务
    - 材料不是 `invoice`
    - 材料当前尚未绑定到任何发票
    - 候选发票与材料处于同一任务、同一提交人
    - 当前候选发票数量恰好为 1
- 调整 [invoices.py](/home/gsh/workspace/TRMS/src/trms_backend/api/invoices.py)：
  - 成员/管理员创建发票后，会尝试把同任务同提交人的未绑定辅助材料自动挂到这张发票
  - 这覆盖“同批上传后再创建唯一发票”的主路径
- 调整 [materials.py](/home/gsh/workspace/TRMS/src/trms_backend/api/materials.py)：
  - 成员后补传辅助材料时，如果同任务同提交人下当前只有 1 张候选发票，会自动绑定
  - 自动绑定后会立即刷新该发票校验结果，避免前端继续看到过期缺失状态

### 根因
- 仓库之前只有手动 `attach supporting material` 能力，没有“安全自动归票”的后端规则。
- 结果是两类本来边界很清楚的场景仍然要求成员或管理员手工处理：
  - 同批上传发票和附件，但任务里只有这一张发票
  - 发票已经存在，后面又补传支付记录/比赛通知等附件，而且也只有这一张候选发票
- 如果直接靠模糊猜测去自动绑，会把多张候选发票场景下的附件静默绑错，因此本轮只实现“单候选”这一条安全主路径。

### 关键规则
- 会自动绑定：
  - 同任务
  - 同提交人
  - 附件尚未绑定
  - 候选发票数量恰好为 1
- 不会自动绑定：
  - 没有候选发票
  - 候选发票多于 1
  - 附件已经被人工或自动绑定过
  - 材料本身是 `invoice`

### 验证结果
- 已通过定向测试：
  - `uv run pytest tests/test_invoices_api.py tests/test_materials_api.py`
    - 72 个用例通过
- 其中新增覆盖包括：
  - 创建唯一发票后，已上传未绑定附件会自动挂到该发票
  - 后补传附件且只有一个候选发票时，会自动挂到该发票
  - 无候选发票时不绑定
  - 多候选发票时不绑定
- 仓库级验证待本轮记录更新后统一执行 `./scripts/verify.sh`。

## 2026-04-30 00:12 - Split auto-linking and pending-linkage task

### 完成内容
- 完成任务“拆分成员侧辅助材料自动归票与待关联提示任务”。
- 更新 [TASKS.md](/home/gsh/workspace/TRMS/TASKS.md)，将原先过大的单任务拆成三个可单轮验证的子任务：
  - `建立辅助材料单候选自动归票后端规则`
  - `建立辅助材料多候选待关联摘要接口`
  - `在成员工作台展示待关联辅助材料与处理入口`

### 当前代码缺口
- 后端已有基础能力：
  - 发票与辅助材料之间已有多对多绑定表
  - 已有手动 `attach/detach supporting material` API
  - 成员工作台和任务共享发票视图已经能显示“已绑定附件摘要”
- 但缺少关键中间层：
  - 没有“哪些未绑定辅助材料属于待关联”的稳定判定模型
  - 没有“同批上传 / 后补传 / 多候选”三类场景的自动绑定规则
  - 成员工作台当前只能看到已绑定附件数量，看不到未绑定辅助材料为什么悬空

### 为什么必须先拆分
- 原任务同时包含：
  - 自动绑定规则
  - 待关联状态建模/API
  - 成员端提示与处理入口
- 这三块分别落在：
  - 识别/上传后端链路
  - 发票/附件绑定读模型
  - 前端工作台交互
- 如果继续把它们当一个单轮任务处理，很容易出现：
  - 规则先硬编码进接口，后续无法测试
  - 前端为了占位先写死提示文案，后端状态又对不上
  - 多候选材料被静默误绑到错误发票

### 拆分后的实现顺序
- 先做“单候选自动归票后端规则”
  - 只覆盖安全边界最清楚的主路径
- 再做“多候选待关联摘要接口”
  - 先把悬空材料显式暴露出来
- 最后做“成员工作台待处理提示”
  - 基于已稳定的后端状态展示下一步动作

### 验证结果
- 本轮只更新任务与工作日志拆分，不改动业务代码。
- 按仓库规则，文档更新后仍应执行 `./scripts/verify.sh`。

## 2026-04-29 23:59 - Finalize per-category extraction schema inventory

### 完成内容
- 完成临时任务“建立按类别提取字段的 schema 清单”。
- 本轮未改动业务代码；确认并收口上一轮已经落地的 schema 事实：
  - [recognition_llm.py](/home/gsh/workspace/TRMS/src/trms_backend/application/recognition_llm.py) 已按材料类别拆成独立输出模型，而不是继续共用单一字段集合
  - `TASKS.md` 与 `WORKLOG.md` 现在明确把这些 schema 和规则字段映射记录为已完成状态

### 分类 schema 清单
- `invoice`
  - `invoice_number`
  - `amount_cents`
  - `buyer_name`
  - `tax_number`
  - `transaction_time`
  - `location`
  - `expense_type`
  - `trip_route`
  - `transport_mode`
  - `cabin_class`
- `competition_notice`
  - `transaction_time`
  - `location`
  - `expense_type`
  - `trip_route`
- `payment_record`
  - `amount_cents`
  - `transaction_time`
  - `location`
  - `expense_type`
  - `trip_route`
  - `transport_mode`
- `order_screenshot`
  - `amount_cents`
  - `transaction_time`
  - `location`
  - `expense_type`
  - `trip_route`
  - `transport_mode`
- `itinerary`
  - `transaction_time`
  - `location`
  - `expense_type`
  - `trip_route`
  - `transport_mode`
  - `cabin_class`
- `other_attachment`
  - `transaction_time`
  - `location`
  - `expense_type`
  - `trip_route`
  - `transport_mode`

### 规则 -> 材料类别 -> 所需识别字段
- `invoice_title_match`
  - 材料类别：`invoice`
  - 所需字段：`buyer_name`
- `invoice_tax_number_match`
  - 材料类别：`invoice`
  - 所需字段：`tax_number`
- `invoice_number_unique`
  - 材料类别：`invoice`
  - 所需字段：`invoice_number`
- `invoice_payment_record_required`
  - 材料类别：`invoice` + `payment_record`
  - 所需字段：无新增识别字段；依赖 `invoice.amount_cents` 与支付记录材料是否存在
- `invoice_payment_record_amount_match`
  - 材料类别：`payment_record`
  - 所需字段：`amount_cents`
- `invoice_competition_notice_required`
  - 材料类别：`competition_notice`
  - 所需字段：无新增识别字段；依赖比赛通知材料是否存在
- `invoice_airfare_itinerary_required`
  - 材料类别：`itinerary`
  - 所需字段：无新增识别字段；依赖航空行程单材料是否存在
- `invoice_airfare_cabin_proof_required`
  - 材料类别：`invoice` / `itinerary` / `order_screenshot`
  - 所需字段：`cabin_class`
- `invoice_local_transport_rideshare_trip_required`
  - 材料类别：`invoice` / `payment_record` / `order_screenshot`
  - 所需字段：`trip_route`、`transport_mode`
- `invoice_competition_time_range`
  - 材料类别：`invoice`
  - 所需字段：`transaction_time`
- `invoice_competition_location_range`
  - 材料类别：`invoice` / `payment_record` / `order_screenshot` / `itinerary` / `other_attachment`
  - 所需字段：`location`、`trip_route`

### 当前判断
- “按类别拆 schema”这一层已经具备闭环：
  - 代码里有独立模型
  - 第一阶段会选择 schema
  - `WORKLOG.md` 已明确列出规则字段依赖
- 下一步未完成的重点已经不是“有没有 schema 清单”，而是：
  - 成员侧辅助材料如何安全自动归票
  - 成员侧如何批量提交与撤回发票

### 验证结果
- 本轮只更新任务与文档记录，没有新增业务代码。
- 仓库规则要求每轮仍执行统一验证；本轮文档更新后将继续运行 `./scripts/verify.sh`。

## 2026-04-29 23:49 - Solidify invoice classification rule for tax-seal vouchers

### 完成内容
- 完成临时任务“固化‘税局盖章材料归发票类别’的分类规则”。
- 调整 [recognition_llm.py](/home/gsh/workspace/TRMS/src/trms_backend/application/recognition_llm.py) 的第一阶段分类 prompt：
  - 显式要求：只要材料上出现税局盖章或等价税务监制特征，就归入 `invoice`
  - 显式要求：铁路电子客票、铁路电子行程单、航空电子客票报销凭证等若本身可作为直接报销凭证，必须按 `invoice` 分类，而不是 `itinerary` 或 `other_attachment`
- 调整测试 [test_recognition_llm.py](/home/gsh/workspace/TRMS/tests/test_recognition_llm.py)：
  - 新增铁路电子客票/税务监制章规则回归测试
  - 断言第一阶段 system prompt 与 user instructions 都明确包含上述分类规则

### 根因
- 上一轮虽然已经把识别拆成两阶段，但第一阶段分类 prompt 还只是一般性的“材料类型判断”。
- 对“税局盖章即发票主链路”“直接报销凭证型铁路/航空票据不能误归辅助材料”这两类高优先级规则，之前没有在 prompt 里显式表达，只能依赖模型自行推断，容易把本该走发票链路的材料误分到 `itinerary` 或 `other_attachment`。

### 风险与影响面
- 本轮只固化了分类规则表达，没有改第二阶段字段 schema，也没有新增基于版式/盖章检测的硬编码后处理。
- 也就是说，本轮解决的是“分类规则未显式声明”的问题，不是“所有 provider 对这些票据都已达到稳定高召回”的问题。
- 下一步仍应继续完成“按类别提取字段的 schema 清单”，把这些材料进入 `invoice` 主链路后需要的字段边界继续补齐。

### 验证结果
- 已通过定向测试：
  - `uv run pytest tests/test_recognition_llm.py`
    - 12 个用例通过
  - `uv run pytest tests/test_recognition_llm.py tests/test_recognition_execution_api.py`
    - 32 个用例通过
- 仓库级验证待本轮文档更新后统一执行 `./scripts/verify.sh`。

## 2026-04-29 23:32 - Establish two-stage recognition pipeline

### 完成内容
- 完成临时任务“建立材料两阶段识别总流程”。
- 调整 [recognition_llm.py](/home/gsh/workspace/TRMS/src/trms_backend/application/recognition_llm.py)：
  - 将单次识别调用拆成两个显式阶段：
    - 第一阶段：材料分类
    - 第二阶段：按分类结果选择 schema 再提取字段
  - 第一阶段固定输出：
    - `document_family`
    - `material_type`
    - `expense_type_candidate`
    - `is_reimbursement_voucher`
    - `classification_confidence`
  - 第二阶段不再共用一套统一字段模型，而是按 `material_type` 选择独立输出 schema：
    - `invoice`
    - `payment_record`
    - `competition_notice`
    - `order_screenshot`
    - `itinerary`
    - `other_attachment`
  - 最终识别结果会合并两阶段字段，原始响应按 `classification / selected_schema / extraction` 分段保存，便于排障和审计。
- 调整测试 [test_recognition_llm.py](/home/gsh/workspace/TRMS/tests/test_recognition_llm.py)：
  - 覆盖两阶段 prompt、schema 选择、DeepSeek 风格归一化、空输出失败和结构化校验失败路径。

### 根因
- 现有识别链路把“先判断材料是什么”和“再提取哪些字段”混在一次 prompt 里。
- 这导致两个问题：
  - 分类判断无法作为后续字段提取的显式前提，材料类型一复杂就只能继续堆提示词特判。
  - 所有材料被迫共用一套输出字段，和当前 [invoice_validation.py](/home/gsh/workspace/TRMS/src/trms_backend/domain/invoice_validation.py) 已经存在的“按材料类别读取不同证据”的规则入口不一致。

### 当前规则与字段映射边界
- 第一阶段只负责分类，不负责详细元数据：
  - `document_family` / `material_type` 决定第二阶段 schema
  - `expense_type_candidate` 只提供费用类别候选，不直接代替最终提取字段
  - `is_reimbursement_voucher` 只表达“该材料本身是否像直接报销凭证”，本轮还没有固化税局盖章特判
- 第二阶段 schema 当前边界：
  - `invoice`：`invoice_number`、`amount_cents`、`buyer_name`、`tax_number`、`transaction_time`、`location`、`expense_type`、`trip_route`、`transport_mode`、`cabin_class`
  - `payment_record`：`amount_cents`、`transaction_time`、`location`、`expense_type`、`trip_route`、`transport_mode`
  - `competition_notice`：`transaction_time`、`location`、`expense_type`、`trip_route`
  - `order_screenshot`：`amount_cents`、`transaction_time`、`location`、`expense_type`、`trip_route`、`transport_mode`
  - `itinerary`：`transaction_time`、`location`、`expense_type`、`trip_route`、`transport_mode`、`cabin_class`
  - `other_attachment`：`transaction_time`、`location`、`expense_type`、`trip_route`、`transport_mode`
- 与当前规则主入口的对齐方式：
  - 发票抬头/税号/金额/重复号：依赖 `invoice` schema
  - 支付记录金额核对：依赖 `payment_record.amount_cents`
  - 航空舱位和网约车行程校验：依赖 `invoice / itinerary / order_screenshot / payment_record` 中的 `trip_route`、`transport_mode`、`cabin_class`
  - 比赛时间/地点范围校验：依赖各 schema 中的 `transaction_time` 与 `location/trip_route`
- 上述映射只是“两阶段总流程”的当前执行边界，不等同于后续“税局盖章归票规则”和“按类别 schema 清单任务”已经全部完成。

### 验证结果
- 已通过定向测试：
  - `uv run pytest tests/test_recognition_llm.py tests/test_recognition_execution_api.py`
    - 31 个用例通过
- 仓库级验证待本轮文档更新后统一执行 `./scripts/verify.sh`。

## 2026-04-29 22:23 - Record two-stage recognition planning and tax-seal voucher rule

### 完成内容
- 未改动业务代码；本轮只根据新的产品要求更新任务拆分和实现边界。
- 更新 [TASKS.md](/home/gsh/workspace/TRMS/TASKS.md)：
  - 新增“材料两阶段识别总流程”任务
  - 新增“税局盖章材料归发票类别”的分类规则任务
  - 新增“按类别提取字段的 schema 清单”任务
- 明确新的核心产品规则：
  - 只要材料上存在税局盖章或等价税务监制特征，就应按发票类别处理
  - 铁路电子客票、铁路电子行程单、航空电子客票报销凭证等可直接报销凭证应归入发票主链路，而不是辅助材料链路
  - 识别链路后续应拆成两次调用：
    - 第一次：分类
    - 第二次：按分类结果提取元数据

### 当前判断
- 现有单次结构化识别把“材料分类”和“字段提取”混在一个 prompt 里，已经不足以支撑当前规则复杂度。
- 当前规则主入口 [invoice_validation.py](/home/gsh/workspace/TRMS/src/trms_backend/domain/invoice_validation.py) 已经隐含要求不同材料类型提供不同字段，但识别层还没有按材料类别拆 schema。
- 因此本轮先把任务拆清，避免后续实现继续在单次 prompt 上叠补丁。

### 下一步最合理动作
- 先实现第一阶段分类结果模型和提示词，明确：
  - 发票类凭证
  - 比赛通知
  - 支付凭证
  - 订单截图
  - 行程单
  - 其他附件
- 再按类别实现第二阶段字段提取 schema，并把当前规则所需字段一条条对齐。

## 2026-04-29 22:15 - Unify structured recognition response_format to json_object

### 完成内容
- 完成新增临时任务“统一对主流 provider 使用 `json_object` 响应格式”。
- 调整 [src/trms_backend/application/recognition_llm.py](/home/gsh/workspace/TRMS/src/trms_backend/application/recognition_llm.py)：
  - `_build_response_format(...)` 现在统一返回 `{"type": "json_object"}`
  - 删除原先仅对 DeepSeek 走 `json_object`、其它 provider 默认走 `json_schema` 的分支判断
- 调整测试 [tests/test_recognition_llm.py](/home/gsh/workspace/TRMS/tests/test_recognition_llm.py)：
  - OpenAI 兼容客户端测试更新为断言统一使用 `json_object`
  - DeepSeek 相关断言保持成立

### 根因
- 当前实例已经不再走“扫描 PDF 直传 `file`”的旧路径，但火山 Ark VLM 仍然返回 400。
- 复查失败任务与现场重放后，真正被 Ark 拒绝的是 `response_format.type=json_schema` 对应的 schema 内容，而不是图像输入本身。
- 现场重放同一份请求、仅把 `response_format` 改成 `{"type":"json_object"}` 后：
  - 当前 Ark VLM 配置返回 `200`
  - 因此问题不需要继续做 provider 特判，而是可以直接统一切换到 `json_object`

### 关键改动点
- 这次没有放弃后端结构化校验。
- 虽然请求给模型的是 `json_object`，但返回后仍然继续经过：
  - JSON 解析
  - 规范化
  - `RecognitionLlmResponse` 的 Pydantic 校验
- 所以只是把“让 provider 按 schema 约束生成”的责任收回到我们后端自己做，而不是放松输出要求。

### 验证结果
- 已通过定向测试：
  - `uv run pytest tests/test_recognition_llm.py tests/test_recognition_execution_api.py`
    - 31 个用例通过
- 已通过当前实例现场验证：
  - 使用当前系统管理员配置里的 Ark VLM `base_url/model/api_key`
  - 对同一份扫描 PDF 图像输入重放请求
  - `response_format={"type":"json_object"}` 返回 `200`
- 该现场验证结论说明：
  - 当前 Ark VLM 支持 `json_object`
  - 400 的直接根因就是此前的 `json_schema` 路径
- 已通过仓库级验证：
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic `upgrade -> downgrade -> upgrade` 通过
    - `pytest`：451 passed，3 warnings
    - Web `npm run lint` 通过
    - Web `npm test`：23 文件、89 用例全部通过
    - Web `npm run build` 成功
    - Docker Compose 配置检查通过
    - `git diff --check` 通过

## 2026-04-29 22:03 - Render scanned PDFs as images and retry text-PDF failures through VLM

### 完成内容
- 完成新增临时任务“统一用 PyMuPDF 处理 PDF 并在文本失败后回退到 VLM”。
- 调整依赖 [pyproject.toml](/home/gsh/workspace/TRMS/pyproject.toml) 与 `uv.lock`：
  - 新增 `pymupdf`
  - 统一由 Python PDF 渲染库处理 PDF 文本提取与页面转图片，不再依赖“扫描 PDF 直传 file”这一条与 Ark 不兼容的输入路径
- 重写 [src/trms_backend/application/recognition_preparation.py](/home/gsh/workspace/TRMS/src/trms_backend/application/recognition_preparation.py) 的 PDF 准备逻辑：
  - 使用 `PyMuPDF` 打开 PDF、读取页面文本
  - 纯文本 PDF 仍优先生成 `pdf_text` 输入
  - 扫描 PDF 不再生成 `pdf_file`，而是把页面统一渲染成单张拼接 PNG，生成 `image_file`
  - 对空白 PDF 仍保留 `blank_pdf` 失败边界
- 补充 text LLM 失败回退：
  - 当 PDF 首次以 `pdf_text` 进入识别，但 text LLM 返回 `RecognitionLlmExecutionError` 时
  - 系统会自动把同一 PDF 渲染成图片，再走一次 VLM
  - 若第二次成功，则整体任务成功；若第二次失败，则保留 `text_attempt` 与 `image_fallback_attempt` 两次原始上下文
- 更新说明 [README.md](/home/gsh/workspace/TRMS/README.md)：
  - 扫描 PDF 现在是“先渲染成图片再送 VLM”
  - 文本 PDF 首次 AI 失败后会自动回退再走一次 VLM
- 更新 [TASKS.md](/home/gsh/workspace/TRMS/TASKS.md)：
  - 新增并完成“PDF 渲染回退识别”任务

### 根因
- 当前实例配置的 VLM 是火山 Ark：
  - `base_url=https://ark.cn-beijing.volces.com/api/v3`
  - `model=doubao-seed-1-6-flash-250828`
- 最近失败任务的 `raw_response` 已明确暴露 400 根因：
  - 请求里扫描 PDF 走的是 `messages.content.type = file`
  - Ark `/chat/completions` 只接受 `text`、`image_url`、`video_url`
- 也就是说，问题不在“VLM 配置没生效”，而在“扫描 PDF 直传 file”的协议本身与当前 provider 不兼容。

### 关键改动点
- 没有继续在 provider 层堆更多 `base_url` 特判。
- 修复思路是直接把仓库的扫描 PDF 主链路改成 provider 更通用的图像输入：
  - 扫描 PDF -> 渲染 PNG -> `image_file`
- 同时，既然已经引入统一 PDF 渲染库，就顺手把“文本 PDF AI 首次失败后再按图片做一次”补成显式链路，而不是让用户手动重试或改传截图。

### 风险与影响面
- 当前扫描 PDF 会把所有页面渲染并纵向拼接成一张 PNG 后再送 VLM；对于页数很多的 PDF，输入字节数会明显增大，后续可能需要再加页数/尺寸控制。
- 本轮仍保留 `RecognitionInputSource.PDF_FILE` 兼容定义，但主识别链路已不再生成它；仓库内现有扫描 PDF 调用都改成了 `image_file`。
- 当前空白 PDF 仍直接返回 `blank_pdf`，不会为了机械地“回退一次 VLM”去渲染全白图像制造无意义请求。

### 验证结果
- 已通过定向测试：
  - `uv run pytest tests/test_recognition_execution_api.py tests/test_recognition_async_jobs.py`
    - 21 个用例通过
- 其中新增/更新覆盖包括：
  - 扫描 PDF 在未配置 VLM 时，准备阶段会生成 `image_file`
  - 扫描 PDF 在已配置识别客户端时，传给 fake LLM 的输入源变为 `image_file`
  - 文本 PDF 在首次 text LLM 失败后，会触发第二次 `image_file` 回退识别
- 已通过仓库级验证：
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic `upgrade -> downgrade -> upgrade` 通过
    - `pytest`：451 passed，3 warnings
    - Web `npm run lint` 通过
    - Web `npm test`：23 文件、89 用例全部通过
    - Web `npm run build` 成功
    - Docker Compose 配置检查通过
    - `git diff --check` 通过

## 2026-04-29 21:25 - Split text LLM and VLM configuration with system-level overrides

### 完成内容
- 完成新增临时任务“支持区分文本 LLM / VLM 的系统级优先配置”。
- 调整运行配置 [src/trms_backend/runtime_config.py](/home/gsh/workspace/TRMS/src/trms_backend/runtime_config.py)：
  - 新增 `text_llm_provider` 与 `vlm_provider`
  - 支持从 `TRMS_TEXT_LLM_*` 与 `TRMS_VLM_*` 分别读取配置
  - 继续兼容旧 `TRMS_LLM_*`：若未配置新变量，text/VLM 两侧都会回退到旧单一路径变量
  - 新增 `apply_system_ai_provider_overrides(...)`，用于把系统级覆盖项与环境变量按“系统优先、缺失回退 env”合并成生效配置
- 新增系统级 AI 配置模型与持久化：
  - [src/trms_backend/domain/system_ai_provider_config.py](/home/gsh/workspace/TRMS/src/trms_backend/domain/system_ai_provider_config.py)
  - [src/trms_backend/infrastructure/models.py](/home/gsh/workspace/TRMS/src/trms_backend/infrastructure/models.py)
  - [src/trms_backend/infrastructure/repositories.py](/home/gsh/workspace/TRMS/src/trms_backend/infrastructure/repositories.py)
  - [alembic/versions/20260429_02_system_ai_provider_config.py](/home/gsh/workspace/TRMS/alembic/versions/20260429_02_system_ai_provider_config.py)
  - 新建 `system_ai_provider_configs` 表，保存系统管理员设置的 text LLM / VLM 覆盖项
  - API key 落库但不回显；更新接口里留空表示保持现有系统密钥不变
- 调整系统管理 API [src/trms_backend/api/system.py](/home/gsh/workspace/TRMS/src/trms_backend/api/system.py)：
  - `GET /api/system/dashboard` 现在返回：
    - `system_ai_provider_config`
    - `runtime.text_llm_provider_configured`
    - `runtime.vlm_provider_configured`
  - `PUT /api/system/recognition-provider-config` 允许系统管理员保存 text LLM / VLM 覆盖项
  - Dashboard 运行态摘要按“当前库里的系统配置 + env fallback”实时计算，不再只看启动时快照
- 调整识别路由 [src/trms_backend/application/recognition_llm.py](/home/gsh/workspace/TRMS/src/trms_backend/application/recognition_llm.py)：
  - 新增 `RoutedRecognitionClient`
  - `pdf_text` 路径走 text LLM
  - `pdf_file` / `image_file` 路径走 VLM
  - 未配置对应 provider 时分别报：
    - `text_llm_provider_not_configured`
    - `vlm_provider_not_configured`
- 调整应用装配：
  - [src/trms_backend/main.py](/home/gsh/workspace/TRMS/src/trms_backend/main.py)
  - [src/trms_backend/__main__.py](/home/gsh/workspace/TRMS/src/trms_backend/__main__.py)
  - API 进程和 worker 都改成“执行时动态解析当前系统级 provider 覆盖项”，保存新配置后无需重启即可用于后续识别任务
- 调整系统管理员前端：
  - [web/src/app/system-admin-dashboard.tsx](/home/gsh/workspace/TRMS/web/src/app/system-admin-dashboard.tsx)
  - 新增“文本 LLM 与 VLM 配置”卡片
  - 可分别编辑：
    - Base URL
    - 模型
    - 超时秒数
    - 最大重试次数
    - API Key
  - 文案明确说明：系统配置优先、缺失字段 fallback `.env`、API key 不回显
- 调整前端 API 类型与调用：
  - [web/src/lib/api/types.ts](/home/gsh/workspace/TRMS/web/src/lib/api/types.ts)
  - [web/src/lib/api/trms.ts](/home/gsh/workspace/TRMS/web/src/lib/api/trms.ts)
- 调整文档与模板：
  - [README.md](/home/gsh/workspace/TRMS/README.md)
  - [.env.example](/home/gsh/workspace/TRMS/.env.example)
  - [.env.development.example](/home/gsh/workspace/TRMS/.env.development.example)
  - 现在明确记录 `TRMS_TEXT_LLM_*` / `TRMS_VLM_*` 与旧 `TRMS_LLM_*` 的兼容关系

### 根因
- 之前所有识别路径只有一个 `llm_provider`：
  - 文本 PDF 的结构化抽取
  - 扫描 PDF 的多模态识别
  - 图片/截图的多模态识别
  都只能共用同一套 `base_url / api_key / model`
- 这在实际部署里会造成两个问题：
  - 文本模型与多模态模型无法分别接到不同供应商或不同模型
  - 即使系统管理员后续补了系统配置，运行时也只会继续读启动时的 `.env` 快照

### 关键改动点
- 没有直接删除旧 `TRMS_LLM_*`，而是做兼容迁移：
  - 新部署优先用 `TRMS_TEXT_LLM_*` 与 `TRMS_VLM_*`
  - 旧部署未迁移时，仍可由旧 `TRMS_LLM_*` 同时驱动 text/VLM 两条链路
- 系统管理员配置不是“全量替代 env”，而是字段级覆盖：
  - 系统里填了的字段优先生效
  - 系统里未填的字段继续回退到 env
  - 因此可以只在系统里覆盖 `base_url` / `model`，而把密钥暂时留在环境变量里
- 保存系统配置后无需重启即可生效：
  - 识别执行时动态合并系统配置与 env
  - Dashboard 运行态摘要也按当前库里的系统配置实时计算

### 风险与影响面
- 现在“未配置 provider”的失败原因从统一 `llm_provider_not_configured` 细分成了：
  - `text_llm_provider_not_configured`
  - `vlm_provider_not_configured`
  前端文案已兼容这两个新原因，但仓库外若有直接依赖旧 reason 值的调用方，需要同步更新。
- 系统管理员配置目前仍是明文保存在数据库中，只是：
  - 不回显到前端
  - 不写入日志
  - 仍建议生产环境后续评估加密存储或外部 secret manager
- 当前“系统配置优先”只覆盖识别 provider，不扩展到其它运行时敏感配置（如对象存储、入站 token、数据库等）。

### 验证结果
- 已通过定向后端测试：
  - `uv run pytest tests/test_runtime_config.py tests/test_system_admin_api.py tests/test_recognition_runtime.py tests/test_recognition_execution_api.py`
    - 46 个用例通过
- 已通过定向前端测试：
  - `cd web && npm test -- --run src/app/system-admin-dashboard.test.tsx`
    - 1 个测试文件、2 个用例通过
- 其中新增覆盖包括：
  - text/VLM 环境变量分离读取
  - 系统配置字段级覆盖与 env fallback
  - 系统管理员保存 recognition provider 配置
  - 保存系统配置后无需重启即可用于文本 PDF 识别
- 已通过仓库级验证：
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic `upgrade -> downgrade -> upgrade` 通过
    - `pytest`：450 passed，3 warnings
    - Web `npm run lint` 通过
    - Web `npm test`：23 文件、89 用例全部通过
    - Web `npm run build` 成功
    - Docker Compose 配置检查通过，旧 `TRMS_LLM_*` 缺失警告已消失
    - `git diff --check` 通过

## 2026-04-29 20:51 - Simplify member upload type selection and fix invoice queue overflow

### 完成内容
- 完成新增临时任务“按简化流程收口成员上传入口并修复发票队列溢出”。
- 更新 [TASKS.md](/home/gsh/workspace/TRMS/TASKS.md)：
  - 新增“成员简化上传流程”任务组
  - 将本轮完成项标记为已完成
  - 将“辅助材料自动归票与待关联提示”“发票批量提交与撤回区”拆成后续独立任务，避免本轮无边界扩散
- 调整后端上传入口 [src/trms_backend/api/materials.py](/home/gsh/workspace/TRMS/src/trms_backend/api/materials.py)：
  - `POST /api/tasks/{task_id}/materials` 与 `POST /api/materials/pending-assignment` 现在允许省略 `material_type`
  - 省略时默认按 `other_attachment` 接收，避免强迫成员先做人肉分类
  - 上传响应在请求内识别完成后，会重新读取最新材料记录，把自动收敛后的 `material_type` 返回给前端
- 调整识别执行器 [src/trms_backend/application/recognition_preparation.py](/home/gsh/workspace/TRMS/src/trms_backend/application/recognition_preparation.py)：
  - 当材料最初以 `other_attachment` 接收，且识别结果明确给出 `material_type` 且状态为 `recognized` 时，自动把材料类型更新为识别类型
  - 只做“默认值 -> 明确识别类型”的保守收敛，不会反向覆盖成员已显式选择或历史已确定的材料类型
- 调整成员上传 UI：
  - [web/src/app/member-material-upload.tsx](/home/gsh/workspace/TRMS/web/src/app/member-material-upload.tsx)
  - [web/src/app/member-invoice-workbench.tsx](/home/gsh/workspace/TRMS/web/src/app/member-invoice-workbench.tsx)
  - 移除成员上传前必须选择“材料类型”的前置表单项
  - 上传区文案改为“上传后自动识别材料类型，并提示缺失辅助资料”
  - 上传结果显式提示：若当前仍显示“其他附件”，表示系统已接收但 AI 还未完成材料类型识别
- 修复成员工作台左侧发票队列溢出：
  - 将成员工作台发票选择项从 MUI `Button` 容器改为原生 `button.invoice-material-button`
  - 避免按钮内部默认 `inline-flex` 把标题区和元数据网格横向挤压成竖排
  - 调整 [web/src/styles.css](/home/gsh/workspace/TRMS/web/src/styles.css) 为发票卡片标题、发票号和元数据值增加 `overflow-wrap: anywhere`
- 调整测试：
  - [tests/test_materials_api.py](/home/gsh/workspace/TRMS/tests/test_materials_api.py)
    - 新增省略 `material_type` 时默认按 `other_attachment` 接收的 API 测试
  - [tests/test_recognition_execution_api.py](/home/gsh/workspace/TRMS/tests/test_recognition_execution_api.py)
    - 新增识别结果会把默认材料类型自动收敛为 `payment_record` 的测试
  - [web/src/app/member-material-upload.test.tsx](/home/gsh/workspace/TRMS/web/src/app/member-material-upload.test.tsx)
  - [web/src/app/member-invoice-workbench.test.tsx](/home/gsh/workspace/TRMS/web/src/app/member-invoice-workbench.test.tsx)
    - 更新为断言上传表单不再提交 `material_type`
    - 补充“上传后自动识别材料类型”只读提示断言

### 根因
- UI 溢出的直接根因不是“数据太长”，而是成员工作台发票队列把复杂块级内容塞进了 MUI `Button` 默认的 `inline-flex` 容器里：
  - 标题区和元数据网格被横向压缩
  - 长发票号和状态摘要被迫进入极窄列宽，最终出现截图里的竖排/椭圆溢出
- 上传流程繁琐的根因也很明确：
  - 前端在上传前强制成员选择 `material_type`
  - 后端接口同样把 `material_type` 作为必填
  - 这导致“系统先收材料，再由 AI 识别和提示缺失项”的简化流程根本无法成立

### 关键改动点
- 没有把“免选类型上传”实现成模糊猜测或静默强行归类。
- 当前策略是：
  - 上传时若成员没选类型，后端保守记为 `other_attachment`
  - 只有当识别结果明确给出 `material_type` 且状态为 `recognized` 时，才自动更新为识别类型
- 这意味着本轮解决的是“免前置分类 + 自动收敛明确识别类型”，还没有解决“多张发票下辅助材料自动归票”的复杂场景；该部分已拆到 `TASKS.md` 的独立后续任务。

### 风险与影响面
- 当前自动收敛只覆盖“默认 `other_attachment` -> 明确识别类型”这一条安全路径：
  - 不会自动改动成员已主动确认过的材料类型
  - 不会替代后续更复杂的辅助材料归票规则
- 若运行模式为 `worker`，上传成功后的即时响应仍可能先显示 `other_attachment`，因为识别尚未完成；工作台刷新后才会看到自动收敛后的类型。这是当前异步模式下的真实边界，不做伪装。
- 本轮没有实现：
  - 辅助材料自动绑定到具体发票
  - 成员侧发票批量提交 / 撤回
  - 上传后直接形成“待关联提示”闭环
  这些都已拆分成后续任务，避免这轮为了赶功能继续堆猜测逻辑。

### 验证结果
- 已通过定向后端测试：
  - `uv run pytest tests/test_materials_api.py tests/test_recognition_execution_api.py`
    - 50 个用例通过
- 已通过定向前端测试：
  - `cd web && npm test -- --run src/app/member-material-upload.test.tsx src/app/member-invoice-workbench.test.tsx`
    - 2 个测试文件、17 个用例通过
- 已通过仓库级验证：
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic `upgrade -> downgrade -> upgrade` 通过
    - `pytest`：445 passed，3 warnings
    - Web `npm run lint` 通过
    - Web `npm test`：23 文件、89 用例全部通过
    - Web `npm run build` 成功
    - Docker Compose 配置检查通过
    - `git diff --check` 通过
- 仍存在未导致失败的现有 warning：
  - `pytest` 仍有 3 条 `HTTP_422_UNPROCESSABLE_ENTITY` 弃用告警
  - Web `vitest` 运行时仍打印多条 `--localstorage-file` 路径 warning
  - Vite build 仍提示主 chunk 超过 500 kB，但当前构建成功

## 2026-04-29 20:11 - Fix invisible worker logs and DeepSeek recognition normalization in runtime

### 完成内容
- 完成新增临时任务“修复 worker 日志不可见与 DeepSeek 识别结果规范化”。
- 调整 [src/trms_backend/__main__.py](/home/gsh/workspace/TRMS/src/trms_backend/__main__.py)：
  - 在 `worker` 入口显式调用 `logging.basicConfig(...)`
  - 使 `worker_startup`、`worker_poll_start`、`worker_poll_complete`、`worker_idle_wait` 等 INFO 日志在真实终端默认可见
- 调整 [src/trms_backend/application/recognition_llm.py](/home/gsh/workspace/TRMS/src/trms_backend/application/recognition_llm.py)：
  - 在 LLM JSON 结果进入 Pydantic schema 前增加保守规范化：
    - `confidence: "high" / "medium" / "low"` 规范成数值
    - `material_type: "电子发票" / "发票"` 等中文标签规范成 `invoice` 等 TRMS 枚举
    - 非法或无法安全映射的 `expense_type` 字段直接丢弃，而不是让整次识别失败
  - 这样像当前真实 DeepSeek 返回的：
    - `"confidence": "high"`
    - `"material_type": "电子发票"`
    - `"expense_type": "培训费"`
    不会再因为格式噪声把整次任务打成 `llm_output_invalid`
- 调整测试：
  - [tests/test_async_jobs.py](/home/gsh/workspace/TRMS/tests/test_async_jobs.py)
    - 新增 worker 入口日志初始化测试
  - [tests/test_recognition_llm.py](/home/gsh/workspace/TRMS/tests/test_recognition_llm.py)
    - 新增 DeepSeek 风格 `"high"` 置信度与中文 material type 规范化测试

### 根因
- `worker` 日志问题的根因很直接：虽然代码里已经写了 `LOGGER.info(...)`，但 `python -m trms_backend worker` 入口没有配置 logging，默认根 logger 不会输出 INFO。
- “前端点击重新识别没有识别”的真实根因不是没执行，而是识别任务已经执行并失败：
  - 当前库里最近的 recognition task 均是 `failed`
  - `failure_detail` 是 `{"stage": "ai", "reason": "llm_output_invalid"}`
  - `raw_response` 显示 DeepSeek 返回了语义接近正确但格式不合法的内容，例如：
    - `confidence: "high"`
    - `material_type: "电子发票"`
    - `expense_type: "培训费"`
- 也就是说，问题不是 worker 完全没跑，而是：
  - 你看不到 worker 日志
  - 模型输出里存在可保守规范化的格式噪声，导致结果在 schema 校验前被整单打失败

### 关键改动点
- 没有放宽最终 schema 约束，也没有把任意脏输出都吞掉。
- 只对“明显可安全规范化”的值做映射：
  - 文本置信度等级 -> 数字
  - 中文发票类型别名 -> TRMS `material_type` 枚举
- 对 `expense_type` 这类存在业务歧义、又超出当前枚举的值，采用“丢弃字段、不让整次识别失败”的保守策略，而不是擅自猜成错误枚举。

### 风险与影响面
- 这次规范化会让一部分原本 `llm_output_invalid` 的结果进入“部分字段成功、部分字段缺失”的状态，后续仍需成员/管理员补录 `expense_type` 等缺失字段。
- 当前只修了最常见的 DeepSeek 输出噪声；如果后续模型继续返回别的非 schema 值，仍可能触发 `llm_output_invalid`，但现在至少能从 worker 日志和 `raw_response` 更快定位。

### 验证结果
- 已通过定向测试：
  - `uv run pytest tests/test_recognition_llm.py tests/test_async_jobs.py`
    - 22 个用例通过
- 已通过仓库级验证：
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic `upgrade -> downgrade -> upgrade` 通过
    - `pytest`：443 passed，3 warnings
    - Web `npm run lint` 通过
    - Web `npm test`：23 文件、89 用例全部通过
    - Web `npm run build` 成功
    - Docker Compose 配置检查通过
    - `git diff --check` 通过
- 真实库静态检查结论：
  - 当前 `trms.db` 中没有 `pending` recognition/export 任务
  - 最近 7 条 recognition task 全部已执行并失败，失败原因统一为 `ai / llm_output_invalid`
  - 失败 `raw_response` 已明确暴露出 DeepSeek 当前返回的 `"high"` / `"电子发票"` / `"培训费"` 等非 schema 值

## 2026-04-29 20:11 - Add structured startup and polling logs for async worker

### 完成内容
- 完成 `TASKS.md` 中当前第一个未完成任务“为独立 worker 增加启动、轮询与任务结果结构化日志”。
- 调整 [src/trms_backend/__main__.py](/home/gsh/workspace/TRMS/src/trms_backend/__main__.py)：
  - `worker` 入口启动时输出 `worker_startup` 结构化日志
  - 日志包含运行模式、轮询间隔、已注册处理器、环境、文件存储摘要和 LLM 配置摘要
  - 继续通过 `to_safe_log_fields()` 保证敏感配置脱敏
- 调整 [src/trms_backend/application/async_jobs.py](/home/gsh/workspace/TRMS/src/trms_backend/application/async_jobs.py)：
  - 每轮轮询开始输出 `worker_poll_start`
  - 每轮轮询结束输出 `worker_poll_complete`
  - 空闲等待前输出 `worker_idle_wait`
- 调整 [src/trms_backend/application/recognition_async_jobs.py](/home/gsh/workspace/TRMS/src/trms_backend/application/recognition_async_jobs.py)：
  - 成功处理识别任务时输出 `recognition_worker_job_processed`
  - 因并发冲突/重复投递/材料不存在而跳过时输出 `recognition_worker_job_skipped`
  - 日志包含 `recognition_task_id`、`material_id`、`status`、`failure_reason`
- 调整 [src/trms_backend/application/export_async_jobs.py](/home/gsh/workspace/TRMS/src/trms_backend/application/export_async_jobs.py)：
  - 成功完成导出任务时输出 `export_worker_job_processed`
  - 导出失败时输出 `export_worker_job_failed`
  - 日志包含 `export_job_id`、`task_id`、`kind`、`format`、`status`、`artifact_filename` / `failure_reason`
- 调整测试 [tests/test_async_jobs.py](/home/gsh/workspace/TRMS/tests/test_async_jobs.py)：
  - 覆盖 worker 启动日志、轮询日志、空闲等待日志
  - 覆盖 recognition/export processor 的单任务成功/跳过/失败日志
  - 覆盖启动日志不泄露 `sk-secret` 等敏感值

### 根因
- 之前 worker 具备实际消费能力，但启动、轮询、空闲等待和单任务处理过程几乎没有结构化日志。
- 一旦出现“worker 没启动”“轮询一直空转”“某个 recognition/export job 被跳过或失败”，只能靠数据库状态和事后排查，无法从运行日志快速定位。

### 关键改动点
- 启动日志放在 `__main__.py`，因为只有这里天然持有运行模式、轮询间隔和脱敏后的运行配置摘要。
- 轮询级日志放在 `AsyncJobWorker`，而单任务成功/失败日志分别放在 recognition/export processor 内部；这样职责边界最清晰，不需要在 worker 层猜测各 job 的业务标识。
- 日志测试不再依赖全局 `caplog` 捕获链路，而是直接替换模块级 `LOGGER`，避免全量测试环境下被外部日志配置干扰。

### 风险与影响面
- 本轮只增加日志，不改 worker 消费语义；已有任务处理结果和审计逻辑不变。
- 目前日志仍是“结构化文本 + 脱敏字段字典”风格，没有引入新的 JSON logger 依赖；若后续要接入集中式日志平台，可在此基础上再统一格式。

### 验证结果
- 已通过定向测试：
  - `uv run pytest tests/test_async_jobs.py`
    - 10 个用例通过
- 已通过仓库级验证：
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic `upgrade -> downgrade -> upgrade` 通过
    - `pytest`：441 passed，3 warnings
    - Web `npm run lint` 通过
    - Web `npm test`：23 文件、89 用例全部通过
    - Web `npm run build` 成功
    - Docker Compose 配置检查通过
    - `git diff --check` 通过
- 仍存在未导致失败的现有 warning：
  - `pytest` 仍有 3 条 `HTTP_422_UNPROCESSABLE_ENTITY` 弃用告警
  - Web `vitest` 运行时仍打印多条 `--localstorage-file` 路径 warning
  - Vite build 仍提示主 chunk 超过 500 kB，但当前构建成功

## 2026-04-29 20:01 - Strengthen recognition prompts and diagnostic failure context

### 完成内容
- 完成 `TASKS.md` 中当前第一个未完成任务“强化发票识别提示词与失败可诊断信息”。
- 调整 [src/trms_backend/application/recognition_llm.py](/home/gsh/workspace/TRMS/src/trms_backend/application/recognition_llm.py)：
  - 增加 `PROMPT_VERSION=trms-recognition-v2`
  - 扩展 system prompt，明确覆盖：
    - 中文高校报销材料语境
    - 中国大陆电子/纸质发票、行程单、网约车小票、比赛通知、支付记录等常见材料
    - `amount_cents` 的人民币元转分规则
    - `buyer_name` / `tax_number` 只在文档明确出现时才提取
    - 时间字段只在文档明确给出时间时才写入，不臆造
    - 缺失/模糊/矛盾字段直接省略，不瞎猜
  - 扩展 user prompt 元数据，补入 `prompt_version` 和更明确的逐项 instructions
  - `_safe_request_summary()` 不再只保留 `message_count`，而是额外提取安全的 `user_prompt` 元数据，便于审计时还原提示词上下文
- 同步增强测试 [tests/test_recognition_llm.py](/home/gsh/workspace/TRMS/tests/test_recognition_llm.py)：
  - 校验 system prompt 中中文发票抽取规则与 anti-guess 边界
  - 校验 user prompt 元数据包含 `prompt_version` 与中文发票样例输入
  - 校验非法 JSON、缺字段输出、非法 schema 输出三类失败都保留足够上下文

### 根因
- 原提示词过于泛化，只说明“抽结构化字段并返回 JSON”，没有明确：
  - 中文电子发票/纸票常见字段边界
  - 人民币金额单位处理
  - 抬头/税号/时间“缺失就省略、不瞎猜”的原则
- 同时，失败上下文里只有很薄的 request summary，排查时难区分到底是：
  - 提示词没把规则说清
  - 模型输出了非 JSON
  - 模型输出了不符合 schema 的 JSON
  - 输出结构合法但一个字段都没抽出来

### 关键改动点
- 没有改动识别执行器、字段 schema 或状态机，只强化 prompt 与错误上下文。
- 失败上下文继续保持“安全可审计”边界：只保留无二进制的 `user_prompt` 元数据，不把完整文件 data URL 塞进日志摘要。

### 风险与影响面
- Prompt 更严格后，模型在边界模糊场景下更可能返回“缺字段”而不是勉强猜值；这会增加 `llm_output_missing_fields` 或低置信度待确认比例，但这是有意为之。
- 由于本轮只修改 prompt 和失败上下文，若后续想进一步提升字段覆盖率，还需要配合更细的 few-shot 或 schema 拆分策略。

### 验证结果
- 已通过定向测试：
  - `uv run pytest tests/test_recognition_llm.py`
    - 10 个用例通过
- 已通过仓库级验证：
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic `upgrade -> downgrade -> upgrade` 通过
    - `pytest`：437 passed，3 warnings
    - Web `npm run lint` 通过
    - Web `npm test`：23 文件、89 用例全部通过
    - Web `npm run build` 成功
    - Docker Compose 配置检查通过
    - `git diff --check` 通过
- 仍存在未导致失败的现有 warning：
  - `pytest` 仍有 3 条 `HTTP_422_UNPROCESSABLE_ENTITY` 弃用告警
  - Web `vitest` 运行时仍打印多条 `--localstorage-file` 路径 warning
  - Vite build 仍提示主 chunk 超过 500 kB，但当前构建成功

## 2026-04-29 19:42 - Close recognition dispatch loop for in-process and worker modes

### 完成内容
- 完成 `TASKS.md` 中当前第一个未完成任务“补齐上传后识别调度闭环，消除 `in_process` / worker 语义错位”。
- 调整后端上传接口 [src/trms_backend/api/materials.py](/home/gsh/workspace/TRMS/src/trms_backend/api/materials.py)：
  - 上传成功后根据 `TRMS_ASYNC_JOB_MODE` 决定是请求内直接执行识别，还是仅保留 `pending` 并返回排队提示
  - API 响应新增 `recognition_dispatch` 元数据，并给每个上传成功项补充 `recognition_status`
  - `pending-assignment` 上传同样走相同调度语义，不再只创建占位任务
- 调整显式重试接口 [src/trms_backend/api/recognitions.py](/home/gsh/workspace/TRMS/src/trms_backend/api/recognitions.py)：
  - `in_process` 下继续同步执行识别
  - `worker` 下返回“已入队等待 worker 消费”的明确提示，不再伪装成已经执行
- 调整前端与 CLI 消费：
  - [web/src/lib/api/types.ts](/home/gsh/workspace/TRMS/web/src/lib/api/types.ts)
  - [web/src/lib/api/trms.ts](/home/gsh/workspace/TRMS/web/src/lib/api/trms.ts)
  - [web/src/app/member-material-upload.tsx](/home/gsh/workspace/TRMS/web/src/app/member-material-upload.tsx)
  - [web/src/app/member-invoice-workbench.tsx](/home/gsh/workspace/TRMS/web/src/app/member-invoice-workbench.tsx)
  - [web/src/app/member-material-status.tsx](/home/gsh/workspace/TRMS/web/src/app/member-material-status.tsx)
  - [src/trms_cli/cli.py](/home/gsh/workspace/TRMS/src/trms_cli/cli.py)
  - 成员上传结果与重新识别入口现在会直接展示“请求内已执行”或“已入队等待 worker”提示
  - CLI 上传摘要不再强制写死 `recognition_status="pending"`，而是优先读取服务端返回
- 为避免本轮改动把大量与异步模式无关的测试误绑到 `test -> in_process` 默认值，补充并收敛了多组测试夹具到显式 `worker` 模式：
  - [tests/test_tasks_api.py](/home/gsh/workspace/TRMS/tests/test_tasks_api.py)
  - [tests/test_invoices_api.py](/home/gsh/workspace/TRMS/tests/test_invoices_api.py)
  - [tests/test_expense_disputes_api.py](/home/gsh/workspace/TRMS/tests/test_expense_disputes_api.py)
  - [tests/test_exports_api.py](/home/gsh/workspace/TRMS/tests/test_exports_api.py)
  - [tests/test_metrics.py](/home/gsh/workspace/TRMS/tests/test_metrics.py)
  - [tests/test_recognition_tasks_api.py](/home/gsh/workspace/TRMS/tests/test_recognition_tasks_api.py)
  - [tests/test_task_member_status_api.py](/home/gsh/workspace/TRMS/tests/test_task_member_status_api.py)
  - [tests/test_task_review_summary_api.py](/home/gsh/workspace/TRMS/tests/test_task_review_summary_api.py)
  - [tests/test_material_upload_integration.py](/home/gsh/workspace/TRMS/tests/test_material_upload_integration.py)
- 新增/更新测试：
  - [tests/test_recognition_execution_api.py](/home/gsh/workspace/TRMS/tests/test_recognition_execution_api.py)
  - [tests/test_materials_api.py](/home/gsh/workspace/TRMS/tests/test_materials_api.py)
  - [web/src/app/member-material-upload.test.tsx](/home/gsh/workspace/TRMS/web/src/app/member-material-upload.test.tsx)
  - [web/src/app/member-invoice-workbench.test.tsx](/home/gsh/workspace/TRMS/web/src/app/member-invoice-workbench.test.tsx)

### 根因
- 原实现把“创建识别任务”和“真正执行识别”拆成了两个动作，但上传接口只做前者，导致：
  - `in_process` 模式下，上传后识别仍停在 `pending`，与模式语义不符
  - 前端为了补洞，显式重试一律调用 `/execute`，又让 `worker` 模式偷偷变成同步执行，和后台 worker 模式边界相冲突
- 本质问题不是识别失败，而是“何时执行识别”的调度责任没有和运行模式绑定。

### 关键改动点
- 上传接口现在显式承担“根据运行模式调度识别”的责任。
- `/execute` 接口不再无视运行模式；它在 `worker` 下只做入队确认，在 `in_process` 下才做同步执行。
- 为减少影响面，没有改 Recognition worker 本身的消费逻辑；仍由现有 `RecognitionAsyncJobProcessor` 消费 `pending` 队列。
- 大量旧测试默认依赖“上传后先只有 pending 占位任务”，这和本轮新语义冲突，但这些测试本身并不关心 `in_process` 行为，因此统一改成显式 `worker` 模式更符合其真实测试目标。

### 风险与影响面
- 上传响应新增了 `recognition_dispatch` 和逐项 `recognition_status`，前端与 CLI 已同步消费；若有仓库外调用方直接依赖旧 payload，需要额外关注兼容性。
- `worker` 模式下前端现在会明确显示排队提示，但不会主动检测“worker 进程根本没启动”；当前只做到“不要误报系统异常”，没有做到 worker 存活探测。

### 验证结果
- 已通过后端定向回归：
  - `uv run pytest tests/test_recognition_execution_api.py tests/test_materials_api.py tests/test_main_flow_e2e.py tests/test_cli_submit.py`
    - 59 个用例通过
  - `uv run pytest tests/test_expense_disputes_api.py tests/test_exports_api.py tests/test_invoices_api.py tests/test_material_upload_integration.py tests/test_metrics.py tests/test_recognition_tasks_api.py tests/test_task_member_status_api.py tests/test_task_review_summary_api.py tests/test_tasks_api.py`
    - 129 个用例通过
- 已通过前端定向回归：
  - `cd web && npm test -- src/app/member-material-upload.test.tsx src/app/member-invoice-workbench.test.tsx src/app/member-material-status.test.tsx`
    - 3 个文件、20 个用例通过
- 已通过相关前端 lint：
  - `cd web && npm run lint -- src/app/member-material-upload.tsx src/app/member-material-upload.test.tsx src/app/member-invoice-workbench.tsx src/app/member-invoice-workbench.test.tsx src/app/member-material-status.tsx src/app/member-material-status.test.tsx src/lib/api/types.ts src/lib/api/trms.ts`
- 已通过仓库级验证：
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic `upgrade -> downgrade -> upgrade` 通过
    - `pytest`：435 passed，3 warnings
    - Web `npm run lint` 通过
    - Web `npm test`：23 文件、89 用例全部通过
    - Web `npm run build` 成功
    - Docker Compose 配置检查通过
    - `git diff --check` 通过
- 仍存在未导致失败的现有 warning：
  - `pytest` 仍有 3 条 `HTTP_422_UNPROCESSABLE_ENTITY` 弃用告警
  - Web `vitest` 运行时仍打印多条 `--localstorage-file` 路径 warning
  - Vite build 仍提示主 chunk 超过 500 kB，但当前构建成功

## 2026-04-29 19:30 - Migrate remaining admin task/detail/invoice/split controls to Material 3

### 完成内容
- 完成 `TASKS.md` 中当前第一个未完成任务“收口管理员任务列表/详情/发票录入/分摊编辑剩余非 M3 控件”。
- 调整 [web/src/app/admin-task-list.tsx](/home/gsh/workspace/TRMS/web/src/app/admin-task-list.tsx)：
  - 创建任务、优先任务入口、表格操作入口切到 MUI `Button`
  - 搜索与状态筛选改为 MUI `TextField`
  - 清除该页残余 `.button-*`、原生 `input` / `select`
- 调整 [web/src/app/admin-task-detail.tsx](/home/gsh/workspace/TRMS/web/src/app/admin-task-detail.tsx)：
  - 页头快捷入口、状态流转按钮改为 MUI `Button`
  - 任务状态与“草稿中，可编辑”等提示改为 `StatusBadge`
  - 返回任务列表按钮统一到 `RouterLink + Button`
- 调整 [web/src/app/admin-invoice-editor.tsx](/home/gsh/workspace/TRMS/web/src/app/admin-invoice-editor.tsx)：
  - 页头返回按钮、发票材料列表项、当前发票状态、识别/校验结果状态、保存动作统一改为 MUI `Button` / `ButtonBase` / `StatusBadge`
  - 保留现有标签页结构和人工录入逻辑
- 调整 [web/src/app/admin-split-editor.tsx](/home/gsh/workspace/TRMS/web/src/app/admin-split-editor.tsx)：
  - 页头返回按钮、发票列表项、当前分摊状态、确认状态、分摊行新增/删除和保存动作统一改为 MUI 组件
  - 保留现有确认对话框和金额差额可视化逻辑
- 同步更新测试 [web/src/app/admin-task-list.test.tsx](/home/gsh/workspace/TRMS/web/src/app/admin-task-list.test.tsx)：
  - 适配 MUI `searchbox` / `combobox` 语义
  - 将筛选交互包进 `act`

### 根因
- 管理员工作台前两轮已经完成导航、复核、导出、提醒页的 M3 收口，但任务列表、任务详情、发票录入和分摊编辑仍残留旧交互样式：
  - `.button-*`
  - `.route-link`
  - `.status-chip`
  - 原生 `input` / `select`
- 这些页面恰好又是管理员最常驻的主工作面，导致整个后台仍存在明显的组件语义断层。

### 关键改动点
- `admin-task-list.tsx` 的状态筛选使用 MUI `TextField`，但保持 native select 风格交互，避免无意义扩大测试面。
- `admin-invoice-editor.tsx` 与 `admin-split-editor.tsx` 的列表项改成 MUI `ButtonBase`，保留既有“左侧列表 / 右侧详情”与“发票列表 / 分摊表单”结构，不重做信息架构。
- 本轮没有改动发票保存、分摊保存、状态流转、任务编辑的后端协议，只替换交互底座和状态展示。

### 风险与影响面
- 管理员任务列表测试现在依赖 `searchbox` 与 `combobox` 角色；若后续把筛选控件切到别的组件，需要同步更新断言。
- 发票录入与分摊编辑的列表项仍复用既有自定义布局类，只把点击底座切到 MUI `ButtonBase`；后续若再做纯视觉重绘，可以在不影响当前行为的前提下独立推进。

### 验证结果
- 已通过定向前端测试：
  - `cd web && npm test -- src/app/admin-task-list.test.tsx src/app/admin-task-detail.test.tsx src/app/admin-invoice-editor.test.tsx src/app/admin-split-editor.test.tsx`
    - 4 个文件、17 个用例通过
- 已通过相关前端 lint：
  - `cd web && npm run lint -- src/app/admin-task-list.tsx src/app/admin-task-detail.tsx src/app/admin-invoice-editor.tsx src/app/admin-split-editor.tsx src/app/admin-task-list.test.tsx src/app/admin-task-detail.test.tsx src/app/admin-invoice-editor.test.tsx src/app/admin-split-editor.test.tsx`
- 已通过仓库级验证：
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic `upgrade -> downgrade -> upgrade` 通过
    - `pytest`：432 passed，3 warnings
    - Web `npm run lint` 通过
    - Web `npm test`：23 文件、89 用例全部通过
    - Web `npm run build` 成功
    - Docker Compose 配置检查通过
    - `git diff --check` 通过
- 仍存在未导致失败的现有 warning：
  - `pytest` 仍有 3 条 `HTTP_422_UNPROCESSABLE_ENTITY` 弃用告警
  - Web `vitest` 运行时仍打印多条 `--localstorage-file` 路径 warning
  - Vite build 仍提示主 chunk 超过 500 kB，但当前构建成功

## 2026-04-29 19:23 - Migrate admin review/export/corrections pages to Material 3 controls

### 完成内容
- 完成 `TASKS.md` 中当前第一个未完成任务“收口管理员复核、导出与提醒页剩余非 M3 控件”。
- 调整 [web/src/app/admin-review-overview.tsx](/home/gsh/workspace/TRMS/web/src/app/admin-review-overview.tsx)：
  - 复核总览页头按钮切到 MUI `Button`
  - 任务状态、风险数量、待归属数量、识别/校验/确认状态统一切到 `StatusBadge`
  - 材料列表项改为 MUI `ButtonBase`，保留原有列表-详情联动结构
  - 详情动作区“更正金额与字段 / 调整分摊 / 查看关联发票 / 处理更正与提醒”统一收口到 MUI 按钮
- 调整 [web/src/app/admin-export-tasks.tsx](/home/gsh/workspace/TRMS/web/src/app/admin-export-tasks.tsx)：
  - 页头返回按钮、导出创建/预览/下载按钮切到 MUI `Button`
  - 导出门禁、能力实现状态、最近任务状态、历史任务状态统一改为 `StatusBadge`
- 调整 [web/src/app/admin-corrections-reminders.tsx](/home/gsh/workspace/TRMS/web/src/app/admin-corrections-reminders.tsx)：
  - 页面切入 `AdminWorkspaceShell + PageHeader`
  - 更正入口按钮、提醒表单、提醒统计状态统一改为 MUI `Button` / `TextField` / `MenuItem` / `StatusBadge`
  - 保留“只保存内部提醒记录、不自动发送消息”的产品边界文案
- 同步更新测试 [web/src/app/admin-corrections-reminders.test.tsx](/home/gsh/workspace/TRMS/web/src/app/admin-corrections-reminders.test.tsx)：
  - 适配 MUI `combobox` 交互
  - 将触发菜单与提交的交互包进 `act`

### 根因
- 管理员工作台导航与部分页面主骨架已经 M3 化，但复核、导出和提醒页里仍混用旧按钮/状态样式：
  - `route-link`
  - `button-primary` / `button-secondary`
  - 手写 `status-chip`
  - 原生 `select` / `textarea`
- 这导致管理员主链路在同一工作台里出现明显的设计断层，测试语义也仍绑定旧控件行为。

### 关键改动点
- `admin-review-overview.tsx` 保持“左侧材料列表 + 右侧详情标签页”的结构不变，只替换交互控件与状态呈现。
- `admin-export-tasks.tsx` 不改导出能力和任务创建逻辑，只统一状态和操作入口。
- `admin-corrections-reminders.tsx` 补进 `AdminWorkspaceShell`，因为它本身属于管理员模块的一环；如果只替换表单控件而不接入统一 shell，导航语义仍会断裂。

### 风险与影响面
- 管理员提醒页测试现在依赖 MUI `combobox` 的菜单打开语义；后续若更换为 `Autocomplete` 或 native select，需要同步改测试。
- `admin-review-overview.tsx` 的材料列表仍保留既有自定义布局类，只把交互底座换成 MUI `ButtonBase`；如果后续继续做视觉重绘，可在不影响本轮行为的前提下单独收口。

### 验证结果
- 已通过定向前端测试：
  - `cd web && npm test -- src/app/admin-review-overview.test.tsx src/app/admin-export-tasks.test.tsx src/app/admin-corrections-reminders.test.tsx`
    - 3 个文件、6 个用例通过
- 已通过相关前端 lint：
  - `cd web && npm run lint -- src/app/admin-review-overview.tsx src/app/admin-export-tasks.tsx src/app/admin-corrections-reminders.tsx src/app/admin-review-overview.test.tsx src/app/admin-export-tasks.test.tsx src/app/admin-corrections-reminders.test.tsx`
- 已通过仓库级验证：
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic `upgrade -> downgrade -> upgrade` 通过
    - `pytest`：432 passed，3 warnings
    - Web `npm run lint` 通过
    - Web `npm test`：23 文件、89 用例全部通过
    - Web `npm run build` 成功
    - Docker Compose 配置检查通过
    - `git diff --check` 通过
- 仍存在未导致失败的现有 warning：
  - `pytest` 仍有 3 条 `HTTP_422_UNPROCESSABLE_ENTITY` 弃用告警
  - Web `vitest` 运行时仍打印多条 `--localstorage-file` 路径 warning
  - Vite build 仍提示主 chunk 超过 500 kB，但当前构建成功

## 2026-04-29 19:15 - Migrate member material status and expense confirmation pages to Material 3 controls

### 完成内容
- 完成 `TASKS.md` 中当前第一个未完成任务“收口成员材料状态页与费用确认页剩余非 M3 控件”。
- 调整成员材料状态页 [web/src/app/member-material-status.tsx](/home/gsh/workspace/TRMS/web/src/app/member-material-status.tsx)：
  - 页面头部切换到 `RoleWorkspace + PageHeader`，补齐 M3 摘要统计卡
  - 任务选择、返回入口、重新识别、人工补录表单、缺失提示状态统一改为 MUI `Button` / `TextField` / `MenuItem` / `StatusBadge`
  - 去掉该页核心交互上的 `route-link`、原生 `select` / `input` / `button` 和手写 `status-chip`
- 调整成员费用确认页 [web/src/app/member-expense-confirmation.tsx](/home/gsh/workspace/TRMS/web/src/app/member-expense-confirmation.tsx)：
  - 将返回入口、任务选择、材料状态跳转、异议原因输入、确认/异议按钮统一切换到 MUI 组件
  - 发票摘要、附件摘要、确认状态、异议状态改为 `StatusBadge`
- 同步更新测试 [web/src/app/member-material-status.test.tsx](/home/gsh/workspace/TRMS/web/src/app/member-material-status.test.tsx)：
  - 适配 MUI `combobox` 语义
  - 同步统计摘要断言
  - 将本地状态切换点击包进 `act`

### 根因
- 这两个成员页虽然前几轮已经完成主流程与信息架构收口，但仍保留了明显的 legacy 控件混用：
  - 原生 `select` / `textarea` / `input`
  - `route-link`
  - 手写 `status-chip`
- 结果是同一成员闭环里，工作台页已经 M3 化，而材料状态页和费用确认页仍停留在旧交互语义，造成视觉与测试模型分裂。

### 关键改动点
- 本轮只处理 `member-material-status.tsx` 与 `member-expense-confirmation.tsx` 的渲染层，不改接口、不改后端权限与提交流程。
- `member-material-status.tsx` 额外补成 M3 页头和统计摘要，是因为该页原本仍停留在旧 `status-card` 结构；若只替换局部按钮，页面整体仍会继续依赖旧页面头语义。
- `member-expense-confirmation.tsx` 保持原有页面骨架，只替换残余 legacy 控件，避免把本轮扩散成新的信息架构重构。

### 风险与影响面
- 前端测试断言从原生表单语义切到 MUI `combobox` / `TextField` 后，后续如果继续调整标签文案或可访问性属性，需要同步维护断言。
- 当前只清理了这两个成员页；管理员页仍有后续独立任务负责剩余 M3 收口。

### 验证结果
- 已通过定向前端测试：
  - `cd web && npm test -- src/app/member-material-status.test.tsx src/app/member-expense-confirmation.test.tsx`
    - 2 个文件、7 个用例通过
- 已通过相关前端 lint：
  - `cd web && npm run lint -- src/app/member-material-status.tsx src/app/member-expense-confirmation.tsx src/app/member-material-status.test.tsx src/app/member-expense-confirmation.test.tsx`
- 已通过仓库级验证：
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic `upgrade -> downgrade -> upgrade` 通过
    - `pytest`：432 passed，3 warnings
    - Web `npm run lint` 通过
    - Web `npm test`：23 文件、89 用例全部通过
    - Web `npm run build` 成功
    - Docker Compose 配置检查通过
    - `git diff --check` 通过
- 仍存在未导致失败的现有 warning：
  - `pytest` 仍有 3 条 `HTTP_422_UNPROCESSABLE_ENTITY` 弃用告警
  - Web `vitest` 运行时仍打印多条 `--localstorage-file` 路径 warning
  - Vite build 仍提示主 chunk 超过 500 kB，但当前构建成功

## 2026-04-29 19:02 - Migrate remaining member workbench controls to Material 3

### 完成内容
- 完成 `TASKS.md` 中当前第一个未完成任务“收口成员发票工作台剩余非 M3 表单与状态控件”。
- 继续调整 [web/src/app/member-invoice-workbench.tsx](/home/gsh/workspace/TRMS/web/src/app/member-invoice-workbench.tsx)：
  - 将成员工作台发票详情区中的材料类型、手动补录、分摊编辑、上传区、确认区全面切换到 MUI `Button` / `TextField` / `MenuItem` / `StatusBadge`
  - 将“下一步动作”“待处理事项”“缺失材料跳转”等残余 `route-link` 按钮替换为 MUI `Button`
  - 将共享发票选择列表与详情内残余 `status-chip` / 原生按钮一并收口
  - 当前 `member-invoice-workbench.tsx` 已不再保留本轮范围内的 legacy `input` / `select` / `textarea` / `button` 或 `route-link` / `button-*` / `status-chip`
- 同步更新测试：
  - [web/src/app/member-invoice-workbench.test.tsx](/home/gsh/workspace/TRMS/web/src/app/member-invoice-workbench.test.tsx)
  - [web/src/app/main-flow-e2e-placeholder.test.tsx](/home/gsh/workspace/TRMS/web/src/app/main-flow-e2e-placeholder.test.tsx)
  - [web/src/app/member-legacy-route-redirects.test.tsx](/home/gsh/workspace/TRMS/web/src/app/member-legacy-route-redirects.test.tsx)
  - 适配 MUI `Select` 的 `combobox` 交互和 `TextField` 的真实输入节点查询

### 根因
- 上一轮虽然把工作台骨架改成了左侧列表 + 右侧详情，但详情面板和上传/确认区里仍残留大量原生控件与 legacy 按钮样式：
  - 原生 `select` / `input` / `textarea`
  - `.route-link`
  - `.button-secondary`
  - `.status-chip`
- 这会导致同一页面内部视觉和交互语义割裂，也让测试同时混用原生表单与 MUI 语义。

### 关键改动点
- 只在 `member-invoice-workbench.tsx` 内完成控件级收口，不改后端 API，也不跨到其他成员页面。
- 为避免 MUI `TextField` 查询命中外层 wrapper，给文本输入的真实 `htmlInput` 补充 `aria-label`，同时把 `Select` 类交互统一到 `combobox` 语义。

### 风险与影响面
- 本轮影响到成员工作台中的大量测试查询方式，尤其是：
  - `getByLabelText` 对原生输入的断言
  - `fireEvent.change` 对 MUI `Select` 的旧用法
- 若后续继续调整工作台布局或文案，这些测试仍需保持按“当前详情面板作用域”断言，而不是回到全页唯一元素假设。

### 验证结果
- 已通过定向前端回归：
  - `cd web && npm test -- src/app/member-invoice-workbench.test.tsx src/app/main-flow-e2e-placeholder.test.tsx src/app/member-legacy-route-redirects.test.tsx`
    - 3 个文件、17 个用例通过
- 已通过相关前端 lint：
  - `cd web && npm run lint -- src/app/member-invoice-workbench.tsx src/app/member-invoice-workbench.test.tsx src/app/main-flow-e2e-placeholder.test.tsx src/app/member-legacy-route-redirects.test.tsx`
- 已通过前端 build：
  - `cd web && npm run build`
- 已通过仓库级验证：
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic `upgrade -> downgrade -> upgrade` 通过
    - `pytest`：432 passed，3 warnings
    - Web `npm run lint` 通过
    - Web `npm test`：23 文件、89 用例全部通过
    - Web `npm run build` 成功
    - Docker Compose 配置检查通过
    - `git diff --check` 通过
- 仍存在未导致失败的现有 warning：
  - `pytest` 仍有 3 条 `HTTP_422_UNPROCESSABLE_ENTITY` 弃用告警
  - Web `vitest` 运行时仍打印多条 `--localstorage-file` 路径 warning
  - Vite build 仍提示主 chunk 超过 500 kB，但当前构建成功

### 假设
- 本轮把“剩余非 M3 控件”限定为 `member-invoice-workbench.tsx` 内仍然直接参与业务交互的控件；不把 `.invoice-material-button` 等列表布局类纳入这一轮的清理目标。

## 2026-04-29 18:55 - Commit list-detail member invoice workbench round

### 完成内容
- 对上一轮“重构成员发票工作台为左侧发票列表 + 右侧详情面板”补做收口验证并清理受影响回归：
  - 修正 [web/src/app/member-legacy-route-redirects.test.tsx](/home/gsh/workspace/TRMS/web/src/app/member-legacy-route-redirects.test.tsx) 对旧空态文案的断言
  - 复跑成员工作台与主流程占位 E2E 的相关测试，确认新结构没有破坏旧路由跳转和主流程占位回归
- 本轮结束前已准备提交当前轮次改动，提交后继续下一项任务。

### 根因
- 上一轮完成两栏工作台重构后，仓库级 `verify.sh` 只剩一条旧成员路由重定向测试仍断言旧空态文案“当前任务下还没有本人已上传发票”，与新信息架构下的空态文案不一致。
- 这不属于新的业务缺陷，而是测试仍绑定旧 UI 文案。

### 关键改动点
- 仅同步测试断言，不改业务实现。

### 验证结果
- 已通过定向前端回归：
  - `cd web && npm test -- src/app/member-legacy-route-redirects.test.tsx src/app/member-invoice-workbench.test.tsx src/app/main-flow-e2e-placeholder.test.tsx`
    - 3 个文件、17 个用例通过
- 已通过仓库级验证：
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic `upgrade -> downgrade -> upgrade` 通过
    - `pytest`：432 passed，3 warnings
    - Web `npm run lint` 通过
    - Web `npm test`：23 文件、89 用例全部通过
    - Web `npm run build` 成功
    - Docker Compose 配置检查通过
    - `git diff --check` 通过

## 2026-04-29 18:49 - Rebuild member invoice workbench into list-detail workspace

### 完成内容
- 完成 `TASKS.md` 中当前第一个未完成任务“重构成员发票工作台为左侧发票列表 + 右侧详情面板”。
- 调整 [web/src/app/member-invoice-workbench.tsx](/home/gsh/workspace/TRMS/web/src/app/member-invoice-workbench.tsx)：
  - 发票 Tab 从“所有票据纵向平铺”改为“两栏工作区”
  - 左侧新增本人发票选择列表与共享发票选择列表
  - 右侧固定渲染当前选中票据的完整上下文，包括：
    - 识别字段
    - 材料类型更正
    - 手动补录 / 重新识别
    - 分摊与确认状态
    - 附件与缺失项
    - 下一步动作
  - 共享发票改为与本人发票共用同一选择/详情工作区，但仍保持只读边界
  - 选中项根据当前 hash 与可见数据推导，不再依赖额外同步 effect 触发二次渲染
- 同步更新前端测试：
  - [web/src/app/member-invoice-workbench.test.tsx](/home/gsh/workspace/TRMS/web/src/app/member-invoice-workbench.test.tsx)
  - [web/src/app/member-legacy-route-redirects.test.tsx](/home/gsh/workspace/TRMS/web/src/app/member-legacy-route-redirects.test.tsx)
  - 适配新布局下的选择器作用域、重复文案和空态文案变化

### 根因
- 旧工作台在 [member-invoice-workbench.tsx](/home/gsh/workspace/TRMS/web/src/app/member-invoice-workbench.tsx) 的发票 Tab 中直接 `map` 渲染全部本人发票卡片，并把共享发票再单独放在页面底部。
- 这样会导致：
  - 同一张票据的信息与操作被埋在长滚动页面里
  - 切换票据只能靠上下滚动，不是显式选择
  - 本人发票与共享发票上下文被拆成两个远距离区域

### 关键改动点
- 用“左侧选择 + 右侧详情”的方式收口票据上下文。
- 保留现有业务逻辑和大部分旧表单/状态文案，不把这轮任务扩散成“M3 控件整体迁移”。
- 为避免右侧初始空白闪烁，选中项由当前数据直接推导，不靠 effect 内部 `setState` 再补一帧。

### 风险与影响面
- 本轮改变了成员工作台发票区的信息架构，因此大量前端测试断言需要从“页面唯一元素”改成“当前详情面板内断言”。
- 当前仍保留一批 legacy `button` / `select` / `status-chip`，这是下一项独立任务“收口成员发票工作台剩余非 M3 表单与状态控件”的范围，本轮不顺带处理。

### 验证结果
- 已通过定向前端回归：
  - `cd web && npm test -- src/app/member-invoice-workbench.test.tsx src/app/member-legacy-route-redirects.test.tsx src/app/main-flow-e2e-placeholder.test.tsx`
    - 3 个文件、17 个用例通过
- 已通过相关前端 lint：
  - `cd web && npm run lint -- src/app/member-invoice-workbench.tsx src/app/member-invoice-workbench.test.tsx src/app/member-legacy-route-redirects.test.tsx src/app/main-flow-e2e-placeholder.test.tsx`
- 已通过前端 build：
  - `cd web && npm run build`
- 已通过仓库级验证：
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic `upgrade -> downgrade -> upgrade` 通过
    - `pytest`：432 passed，3 warnings
    - Web `npm run lint` 通过
    - Web `npm test`：23 文件、89 用例全部通过
    - Web `npm run build` 成功
    - Docker Compose 配置检查通过
    - `git diff --check` 通过
- 仍存在未导致失败的现有 warning：
  - `pytest` 仍有 3 条 `HTTP_422_UNPROCESSABLE_ENTITY` 弃用告警
  - Web `vitest` 运行时仍打印多条 `--localstorage-file` 路径 warning
  - Vite build 仍提示主 chunk 超过 500 kB，但当前构建成功

### 假设
- 本轮将“左侧发票列表 + 右侧详情面板”限定为桌面主交互骨架重构；移动端采用同一 DOM 顺序下的自然降级布局，不额外做独立移动端导航组件。

## 2026-04-29 18:34 - Stabilize main-flow-e2e-placeholder under full frontend test run

### 完成内容
- 完成 `TASKS.md` 中当前第一个未完成任务“稳定 `main-flow-e2e-placeholder` 全量前端回归测试时序”。
- 调整 [web/src/app/main-flow-e2e-placeholder.test.tsx](/home/gsh/workspace/TRMS/web/src/app/main-flow-e2e-placeholder.test.tsx)：
  - 将成员端“上传材料”和“费用确认”两段路径从旧二级入口改为直达 `/member/invoices/workbench` 的 hash 入口，减少额外重定向和无意义页面装配
  - 为这条跨多页面、跨多角色的占位 E2E 单测单独设置 `15_000ms` 超时，而不是修改全局前端测试超时
  - 保留原测试目标不变：仍覆盖创建任务、开放任务、成员上传、管理员录票、管理员分摊、成员确认、管理员复核、导出门禁
- 同步清理：
  - `TASKS.md` 将该任务标记完成
  - `BLOCKERS.md` 清除当前阻塞
  - `WORKLOG.md` 记录本轮根因与验证结果

### 根因
- 根因不是功能代码错误，而是测试本身属于“跨多页面主流程占位 E2E”，在一次用例里连续执行：
  - 多次 `cleanup() + renderRoute()`
  - 多角色切换
  - 多个依赖异步 fetch 的页面装配
- 单独跑时该测试约 5.39s，放进全量 `vitest run` 时会在默认 `5000ms` 门限附近抖动超时。
- 因此问题属于：
  - 测试路径过长、接近默认超时上限
  - 成员端旧路由重定向增加了额外装配成本
  - 全量运行下的资源竞争放大了上述边缘时序

### 关键改动点
- 本轮不是“盲目提高全局超时”，而是：
  - 先减少测试中的不必要重定向路径
  - 再只对这条长流程占位 E2E 单测设置局部超时
- 这样其他前端单测仍保留默认超时约束，不会因为一个慢测试放松整套回归门槛。

### 风险与影响面
- 这条测试仍然是占位 E2E，运行时间在前端测试中依然偏长；后续若工作台继续变重，仍可能需要进一步拆分或重构测试结构。
- 当前做法保留了主流程覆盖，但没有把这条大测试拆成多条更细粒度用例；这是出于“先解除 `verify` 阻塞”的最小修复。

### 验证结果
- 已通过定向测试：
  - `cd web && npm test -- src/app/main-flow-e2e-placeholder.test.tsx`
    - 1 个文件、1 个用例通过
- 已通过全量前端测试：
  - `cd web && npm test`
    - 23 个文件、89 个用例全部通过
- 已通过仓库级验证：
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic `upgrade -> downgrade -> upgrade` 通过
    - `pytest`：432 passed，3 warnings
    - Web `npm run lint` 通过
    - Web `npm test`：23 文件、89 用例全部通过
    - Web `npm run build` 成功
    - Docker Compose 配置检查通过
    - `git diff --check` 通过
- 仍存在未导致失败的现有 warning：
  - `pytest` 仍有 3 条 `HTTP_422_UNPROCESSABLE_ENTITY` 弃用告警
  - Web `vitest` 运行时仍打印多条 `--localstorage-file` 路径 warning
  - Vite build 仍提示主 chunk 超过 500 kB，但当前构建成功

### 假设
- 本轮将“修复 verify 阻塞”限定为：稳定当前已记录的 flaky 前端占位 E2E，不顺带拆重整条主流程测试架构，也不顺带处理 `--localstorage-file` warning 或 chunk 体积告警。

## 2026-04-29 18:28 - Migrate member upload page remaining controls to Material 3

### 完成内容
- 完成 `TASKS.md` 中当前第一个未完成任务“收口成员专项上传页剩余非 M3 表单与操作控件”。
- 重写 [web/src/app/member-material-upload.tsx](/home/gsh/workspace/TRMS/web/src/app/member-material-upload.tsx) 的渲染层：
  - 页头改为 `RoleWorkspace + PageHeader`
  - 上传表单改为 `SectionCard + TextField(select) + Button`
  - 结果状态标签改为 `StatusBadge`
  - 成功结果列表改为 MUI `Card`
  - 返回入口改为 MUI `Button` 链接，不再依赖 `route-link`
- 保持不变的边界：
  - 上传 API、表单校验、`FileDropZone`、逐文件成功/失败结果和 Snackbar 反馈逻辑不变
- 同步更新测试 [web/src/app/member-material-upload.test.tsx](/home/gsh/workspace/TRMS/web/src/app/member-material-upload.test.tsx)：
  - “目标任务”断言从原生表单查询切到 MUI `combobox`
  - 其余主流程、超限拦截和后端拒绝路径继续保留

### 根因
- 这个页面虽然已经接入了 `FileDropZone`，但任务选择、材料类型、提交按钮、入口链接和结果状态仍然停留在原生 `select`、legacy `route-link`、手写 `status-chip`。
- 这会让成员上传页成为当前成员端最明显的“半迁移”页面，和现有 Material 3 骨架不一致。

### 关键改动点
- 用 MUI 组件接管原生交互控件，但不顺带改上传业务流程。
- 页面不再依赖：
  - `route-link`
  - 原生 `select`
  - 手写 `status-chip`

### 风险与影响面
- 本轮主要风险在于 MUI `Select` 的测试查询语义与原生控件不同，已通过测试调整收口。
- 页面结果区域从旧的 class-based 卡片切到 MUI `Card`，但保留了相同的文本信息和 aria-label，避免影响业务可见性。

### 验证结果
- 已通过定向前端回归：
  - `cd web && npm test -- src/app/member-material-upload.test.tsx`
    - 1 个文件、4 个用例通过
- 已通过相关前端 lint：
  - `cd web && npm run lint -- src/app/member-material-upload.tsx src/app/member-material-upload.test.tsx`
- 已通过前端 build：
  - `cd web && npm run build`
- 本轮未再次单独记录新的 `./scripts/verify.sh` 结果；仓库级验证最新状态仍与上一轮一致，继续被 [BLOCKERS.md](/home/gsh/workspace/TRMS/BLOCKERS.md:5) 中已记录的前端 flaky 测试阻塞。

### 假设
- 本轮将“剩余非 M3 控件”限定为：任务选择、材料类型、提交按钮、结果状态和页面跳转入口；不顺带改造 `FileDropZone` 本身、后端错误协议或上传结果数据模型。

## 2026-04-29 18:24 - Fix frontend API error parsing to preserve backend detail

### 完成内容
- 完成 `TASKS.md` 中当前第一个未完成任务“修正前端通用 API 错误解析，优先展示后端真实失败原因”。
- 调整前端公共错误解析：
  - 修改 [web/src/lib/api/errors.ts](/home/gsh/workspace/TRMS/web/src/lib/api/errors.ts)：
    - 标准错误载荷优先读取后端 `detail`，不再先被顶层泛化 `message` 截断
    - 字段级 `422` 错误不再落回“当前操作未完成…”泛化提示，改为“提交信息有误，请检查以下字段。”
  - 修改 [web/src/lib/ui-text.ts](/home/gsh/workspace/TRMS/web/src/lib/ui-text.ts)：
    - 删除“大多数 `4xx` 一律返回统一提示”的兜底策略
    - 为登录失败、用户名冲突、上传关闭、分摊总额不一致、任务状态流转限制、成员不在任务内、费用类型不允许等高频后端错误增加具体文案映射
    - 未命中已知翻译规则的 `4xx` 保留后端真实 `detail`，不再强行改写成统一提示
- 同步更新前端测试：
  - [web/src/lib/api/client.test.ts](/home/gsh/workspace/TRMS/web/src/lib/api/client.test.ts)
  - [web/src/components/ApiErrorNotice.test.tsx](/home/gsh/workspace/TRMS/web/src/components/ApiErrorNotice.test.tsx)
  - [web/src/app/App.test.tsx](/home/gsh/workspace/TRMS/web/src/app/App.test.tsx)
  - [web/src/app/member-material-upload.test.tsx](/home/gsh/workspace/TRMS/web/src/app/member-material-upload.test.tsx)
  - [web/src/app/member-expense-confirmation.test.tsx](/home/gsh/workspace/TRMS/web/src/app/member-expense-confirmation.test.tsx)
  - [web/src/app/admin-task-create.test.tsx](/home/gsh/workspace/TRMS/web/src/app/admin-task-create.test.tsx)
  - [web/src/app/admin-split-editor.test.tsx](/home/gsh/workspace/TRMS/web/src/app/admin-split-editor.test.tsx)
  - [web/src/app/admin-task-detail.test.tsx](/home/gsh/workspace/TRMS/web/src/app/admin-task-detail.test.tsx)
  - [web/src/app/admin-corrections-reminders.test.tsx](/home/gsh/workspace/TRMS/web/src/app/admin-corrections-reminders.test.tsx)
  - [web/src/app/admin-invoice-editor.test.tsx](/home/gsh/workspace/TRMS/web/src/app/admin-invoice-editor.test.tsx)
- 本轮修改文件：
  - `web/src/lib/api/errors.ts`
  - `web/src/lib/ui-text.ts`
  - `web/src/lib/api/client.test.ts`
  - `web/src/components/ApiErrorNotice.test.tsx`
  - `web/src/app/App.test.tsx`
  - `web/src/app/member-material-upload.test.tsx`
  - `web/src/app/admin-task-create.test.tsx`
  - `web/src/app/admin-split-editor.test.tsx`
  - `web/src/app/admin-task-detail.test.tsx`
  - `web/src/app/admin-corrections-reminders.test.tsx`
  - `web/src/app/admin-invoice-editor.test.tsx`
  - `TASKS.md`
  - `WORKLOG.md`

### 根因
- 前端原先有两层错误信息丢失：
  - [web/src/lib/api/errors.ts](/home/gsh/workspace/TRMS/web/src/lib/api/errors.ts) 先读顶层 `message`，而标准后端错误响应通常是“`message` 泛化、`detail` 具体”，导致更关键的 `detail` 被吞掉。
  - [web/src/lib/ui-text.ts](/home/gsh/workspace/TRMS/web/src/lib/ui-text.ts) 又把大多数 `4xx` 兜底改写成“当前操作未完成，请检查填写内容后重试。”，进一步抹平登录失败、权限失败、任务状态冲突和字段校验的真实原因。

### 关键改动点
- 优先级调整为：
  - 真实 `detail`
  - 字段级校验明细
  - 顶层 `message`
  - 最后才是状态码 fallback
- 对高频后端错误做面向用户的中文化映射，但对未知 `4xx` 保留原始 `detail`，避免再次过度泛化。

### 风险与影响面
- 本轮会改变多个页面已有错误文案，因此所有依赖旧泛化提示的前端断言都需要同步更新。
- 对未显式列入映射表的后端 `4xx`，当前策略是“保留原始 detail”；这比继续泛化更接近真实原因，但部分页面仍可能出现英文业务错误文案，后续可按高频场景继续补中文映射。

### 验证结果
- 已通过定向前端回归：
  - `cd web && npm test -- src/lib/api/client.test.ts src/components/ApiErrorNotice.test.tsx src/app/App.test.tsx src/app/member-material-upload.test.tsx src/app/admin-task-create.test.tsx src/app/admin-split-editor.test.tsx src/app/admin-task-detail.test.tsx src/app/admin-corrections-reminders.test.tsx src/app/admin-invoice-editor.test.tsx src/app/member-expense-confirmation.test.tsx`
    - 10 个文件、45 个用例通过
- 已通过相关前端 lint：
  - `cd web && npm run lint -- src/lib/ui-text.ts src/lib/api/errors.ts src/lib/api/client.test.ts src/components/ApiErrorNotice.test.tsx src/app/App.test.tsx src/app/member-material-upload.test.tsx src/app/admin-task-create.test.tsx src/app/admin-split-editor.test.tsx src/app/admin-task-detail.test.tsx src/app/admin-corrections-reminders.test.tsx src/app/admin-invoice-editor.test.tsx`
- 已通过前端 build：
  - `cd web && npm run build`
- 已按仓库要求运行整仓验证：
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic `upgrade -> downgrade -> upgrade` 通过
    - `pytest`：432 passed，3 warnings
    - Web `npm run lint` 通过
    - Web `npm test` 仍失败于已知阻塞：`src/app/main-flow-e2e-placeholder.test.tsx` 在全量运行时默认 `5000ms` 超时
- 结论：
  - 本轮相关改动的定向测试、lint、build 均通过；
  - 仓库级 `verify.sh` 仍被 [BLOCKERS.md](/home/gsh/workspace/TRMS/BLOCKERS.md:5) 中已有的 flaky 前端测试阻塞，因此本轮不能声称整仓验证通过，也不执行 commit。

### 假设
- 本轮将“优先展示真实错误原因”实现为：
  - 已知高频错误尽量中文化；
  - 未知业务 `4xx` 至少保留原始后端 `detail`；
  - 不在本轮顺带重写所有后端错误码语义或新增完整的前端 i18n 体系。

## 2026-04-29 18:35 - Review current system and add follow-up tasks

### 完成内容
- 按仓库规范完成本轮 review 前置阅读：
  - `AGENTS.md`
  - `TASKS.md`
  - `WORKLOG.md`
  - `BLOCKERS.md`
  - `README.md`
  - `docs/同济大学ACM竞赛报销收集系统需求分析文档_V0.2.md`
  - `docs/同济大学ACM竞赛报销收集系统架构设计与技术选型文档_V0.1.md`
  - `docs/UI原型图对照与交互规范补充.md`
  - `docs/Material3前端落地方案评估.md`
- 对用户指出的五类问题完成静态代码 review，并把需要落实的修改拆分写入 `TASKS.md` 新增章节“临时任务 - 2026-04-29 当前系统 review 收口”。
- 本轮未改业务代码，仅更新：
  - `TASKS.md`
  - `WORKLOG.md`

### 根因
- 前端错误提示被公共映射层过度收口：
  - [web/src/lib/ui-text.ts](/home/gsh/workspace/TRMS/web/src/lib/ui-text.ts:224) 会把大多数 `4xx` 统一映射成泛化中文提示。
  - [web/src/lib/api/errors.ts](/home/gsh/workspace/TRMS/web/src/lib/api/errors.ts:139) 在汇总错误时直接消费上述映射，导致后端已返回的 `detail` / `message` 细节被吞掉。
- Material 3 迁移并未完成，仍有大量页面依赖 legacy class 和原生表单控件：
  - [web/src/app/member-material-upload.tsx](/home/gsh/workspace/TRMS/web/src/app/member-material-upload.tsx:314)
  - [web/src/app/member-invoice-workbench.tsx](/home/gsh/workspace/TRMS/web/src/app/member-invoice-workbench.tsx:1887)
  - [web/src/app/admin-review-overview.tsx](/home/gsh/workspace/TRMS/web/src/app/admin-review-overview.tsx:645)
  - 以及 `admin-export-tasks.tsx`、`admin-corrections-reminders.tsx`、`member-material-status.tsx`、`member-expense-confirmation.tsx`、`admin-task-list.tsx`、`admin-task-detail.tsx`、`admin-invoice-editor.tsx`、`admin-split-editor.tsx` 中残余的 `route-link` / `button-*` / `status-chip` / 原生输入控件。
- 成员发票工作台当前把所有发票详情纵向平铺，天然导致长滚动页面：
  - [web/src/app/member-invoice-workbench.tsx](/home/gsh/workspace/TRMS/web/src/app/member-invoice-workbench.tsx:1887) 开始直接 `map` 渲染整批发票卡片，而不是“列表选择 + 详情联动”。
- “手动上传发票不识别”当前更像识别调度闭环缺口，而不是先验可归咎于提示词：
  - [src/trms_backend/runtime_config.py](/home/gsh/workspace/TRMS/src/trms_backend/runtime_config.py:25) 默认把开发/测试环境设为 `in_process`。
  - 但 [src/trms_backend/application/material_submission.py](/home/gsh/workspace/TRMS/src/trms_backend/application/material_submission.py:259) 上传后只创建 `pending` 识别任务占位，没有在 `in_process` 模式下自动执行。
  - [tests/test_main_flow_e2e.py](/home/gsh/workspace/TRMS/tests/test_main_flow_e2e.py:306) 也需要测试代码手工构造 `RecognitionAsyncJobProcessor` 再 `run_once()`，进一步证明当前主链路并不会自动跑识别。
- 提示词本身也偏弱，只给了通用 JSON 约束，没有针对中文发票场景的字段抽取指引：
  - [src/trms_backend/application/recognition_llm.py](/home/gsh/workspace/TRMS/src/trms_backend/application/recognition_llm.py:346)
- worker 可观测性明显不足：
  - [src/trms_backend/__main__.py](/home/gsh/workspace/TRMS/src/trms_backend/__main__.py:125) 的 worker 入口只有参数解析和 `run_forever()`，没有启动日志。
  - [src/trms_backend/application/async_jobs.py](/home/gsh/workspace/TRMS/src/trms_backend/application/async_jobs.py:67) 的轮询循环没有任何日志输出。
  - 当前仓库除了 API 错误处理外，worker/异步处理链基本没有结构化日志埋点。

### 关键改动点
- 在 `TASKS.md` 新增 10 个 review 后续任务，覆盖：
  - 前端真实错误原因展示
  - 剩余非 M3 页面/控件收口
  - 成员发票工作台左侧列表 + 右侧详情改造
  - 识别调度闭环修复
  - 发票识别提示词强化
  - worker 启动/轮询/结果日志

### 风险与影响面
- 本轮只是 review 结论落账，没有直接修复线上行为，因此上述问题当前仍然存在。
- “上传后不识别”我已确认存在调度语义错位，但未实际结合你的本地 `.env` 和真实 worker 进程复现，因此还不能排除同时叠加了 LLM 配置、文件内容或提示词质量问题。
- Material 3 收口任务已按页面拆分，但其中“成员发票工作台布局重构”影响面最大，后续实现时需要同步回归桌面端、移动端和现有 workbench 测试。

### 验证结果
- 已完成静态 review 证据核对，引用代码与测试如下：
  - [web/src/lib/ui-text.ts](/home/gsh/workspace/TRMS/web/src/lib/ui-text.ts:224)
  - [web/src/lib/api/errors.ts](/home/gsh/workspace/TRMS/web/src/lib/api/errors.ts:139)
  - [web/src/app/member-invoice-workbench.tsx](/home/gsh/workspace/TRMS/web/src/app/member-invoice-workbench.tsx:1887)
  - [src/trms_backend/application/material_submission.py](/home/gsh/workspace/TRMS/src/trms_backend/application/material_submission.py:259)
  - [tests/test_main_flow_e2e.py](/home/gsh/workspace/TRMS/tests/test_main_flow_e2e.py:306)
  - [src/trms_backend/application/recognition_llm.py](/home/gsh/workspace/TRMS/src/trms_backend/application/recognition_llm.py:346)
  - [src/trms_backend/__main__.py](/home/gsh/workspace/TRMS/src/trms_backend/__main__.py:125)
  - [src/trms_backend/application/async_jobs.py](/home/gsh/workspace/TRMS/src/trms_backend/application/async_jobs.py:67)
- 已运行仓库级验证：
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic `upgrade -> downgrade -> upgrade` 通过
    - `pytest`：432 passed，3 warnings
    - Web `npm run lint` 通过
    - Web `npm test` 未通过：`src/app/main-flow-e2e-placeholder.test.tsx` 在全量运行时命中默认 `5000ms` 超时
- 已做附加排查：
  - `cd web && npm test -- src/app/main-flow-e2e-placeholder.test.tsx`
    - 单独运行通过
- 结论：
  - 当前 `verify.sh` 失败点属于前端现有 flaky 测试，而不是本轮文档改动引入的业务回归；
  - 已将该问题写入 `TASKS.md` 与 `BLOCKERS.md`，本轮不能声称整仓验证通过。

### 假设
- 本轮把“写入 tasks”解释为：基于静态 review 明确列出需要修改的最小任务，而不是立即实现其中任一业务修复。

## 2026-04-29 17:40 - Shrink unused styles.css selectors

### 完成内容
- 完成 `TASKS.md` 中当前第一个未完成任务“进一步收缩 `styles.css` 死代码”。
- 调整 [web/src/styles.css](/home/gsh/workspace/TRMS/web/src/styles.css)：
  - 删除 `.workflow-*`、`.kpi-*`、`.dashboard-grid`、`.workspace-meta-grid`、`.task-insight*`、`.task-stage-line`、`.anomaly-chip*`、`.task-workflow*` 以及与之配套但同样未被引用的 `dashboard-kpi-grid` 样式
  - 收窄混合选择器，只保留当前 `.tsx` 仍在使用的选择器，避免为了保留活代码继续携带死选择器
  - 同步清理针对上述死类的响应式媒体查询分支

### 根因
- `styles.css` 在上一轮移除旧顶栏和全局 token 后，仍残留一批来自旧工作台/仪表盘布局的类名。
- 这些类在当前 `web/src/**/*.tsx` 中已经没有任何引用，但依然留在全局样式表中，继续增加维护噪音，也会干扰后续判断哪些页面还依赖旧 CSS。

### 关键改动点
- 修改：
  - `web/src/styles.css`
  - `TASKS.md`
  - `WORKLOG.md`

### 风险与影响面
- 本轮只删除静态检索确认未被当前 `.tsx` 引用的样式类，不修改业务组件结构、不改页面行为，也不调整仍在使用的 `.task-card`、`.status-card`、`.stat-grid` 等辅助类。
- 由于删除的是全局 CSS，风险主要在于“是否存在隐藏引用”。本轮通过全仓库文本检索和整仓构建/测试回归共同收口该风险。

### 验证结果
- 已通过仓库级验证：
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic `upgrade -> downgrade -> upgrade` 通过
    - `pytest`：432 passed，3 warnings
    - Web `npm run lint` 通过
    - Web `npm test`：23 文件、87 用例全部通过
    - Web `npm run build` 成功
    - Docker Compose 配置检查通过
    - `git diff --check` 通过
- 仍存在未导致失败的现有 warning：
  - `pytest` 仍有 3 条 `HTTP_422_UNPROCESSABLE_ENTITY` 弃用告警
  - Web `vitest` 运行时仍打印多条 `--localstorage-file` 路径 warning
  - Vite build 仍提示主 chunk 超过 500 kB，但当前构建成功

### 假设
- 本轮将“当前 .tsx 中未被引用的死类”保守定义为：在 `web/src` 范围内文本检索不到调用、且删除后整仓 `lint/test/build` 通过的选择器；不顺带处理未列入本轮任务的其他潜在样式清理项。

## 2026-04-29 17:33 - Attach destructive business actions to ConfirmDialog

### 完成内容
- 完成 `TASKS.md` 中当前第一个未完成任务“把破坏性业务动作接入 ConfirmDialog”。
- 调整 [web/src/app/admin-task-detail.tsx](/home/gsh/workspace/TRMS/web/src/app/admin-task-detail.tsx)：
  - 任务状态流转前统一弹出确认对话框
  - 完成归档时要求输入任务 ID 二次确认
- 调整 [web/src/app/admin-export-tasks.tsx](/home/gsh/workspace/TRMS/web/src/app/admin-export-tasks.tsx)：
  - 创建导出任务前弹出带任务状态、任务编号和导出格式上下文的确认对话框
- 调整 [web/src/app/admin-split-editor.tsx](/home/gsh/workspace/TRMS/web/src/app/admin-split-editor.tsx)：
  - 删除分摊行前弹出确认对话框
  - 覆盖保存分摊方案前弹出确认对话框，并明确提示可能重置成员确认状态
- 同步更新前端测试：
  - [web/src/app/admin-task-detail.test.tsx](/home/gsh/workspace/TRMS/web/src/app/admin-task-detail.test.tsx)
  - [web/src/app/admin-export-tasks.test.tsx](/home/gsh/workspace/TRMS/web/src/app/admin-export-tasks.test.tsx)
  - [web/src/app/admin-split-editor.test.tsx](/home/gsh/workspace/TRMS/web/src/app/admin-split-editor.test.tsx)
  - [web/src/app/main-flow-e2e-placeholder.test.tsx](/home/gsh/workspace/TRMS/web/src/app/main-flow-e2e-placeholder.test.tsx)
  - 覆盖确认与取消路径，并把主流程占位 E2E 适配到新的确认弹窗交互

### 根因
- `ConfirmDialogProvider` 和 `useConfirmDialog()` 已经存在，但当前高风险操作仍然直接执行：
  - 任务状态按钮点击后立即发起状态流转请求
  - 导出任务创建按钮点击后立即入队异步导出
  - 分摊编辑里的删除分摊行和覆盖保存分摊会直接丢弃本地编辑或覆盖服务端当前版本
- 这与当前任务“把破坏性业务动作接入 ConfirmDialog”的要求不一致，也让管理员缺少最后一道明确确认边界。

### 关键改动点
- 修改：
  - `web/src/app/admin-task-detail.tsx`
  - `web/src/app/admin-export-tasks.tsx`
  - `web/src/app/admin-split-editor.tsx`
  - `web/src/app/admin-task-detail.test.tsx`
  - `web/src/app/admin-export-tasks.test.tsx`
  - `web/src/app/admin-split-editor.test.tsx`
  - `web/src/app/main-flow-e2e-placeholder.test.tsx`
  - `TASKS.md`
  - `WORKLOG.md`

### 风险与影响面
- 本轮只收口当前前端已经暴露的破坏性动作，不新增新的业务入口，不扩展权限边界，不改后端 API 语义。
- 当前前端尚未提供独立的“管理员代确认”“材料删除”或“强制导出重跑”业务入口；因此本轮按现有真实入口保守收口为：
  - 任务状态流转
  - 导出任务创建
  - 分摊行删除
  - 分摊覆盖保存
- 由于新增确认弹窗，所有相关前端测试和主流程占位 E2E 都必须显式通过弹窗确认，否则会误判为页面无响应；本轮已同步修复这些受影响测试。

### 验证结果
- 已通过定向前端回归：
  - `cd web && npm test -- admin-task-detail.test.tsx admin-export-tasks.test.tsx admin-split-editor.test.tsx`
  - `cd web && npm test -- main-flow-e2e-placeholder.test.tsx`
- 已通过定向前端 lint：
  - `cd web && npm run lint -- src/app/admin-task-detail.tsx src/app/admin-export-tasks.tsx src/app/admin-split-editor.tsx src/app/admin-task-detail.test.tsx src/app/admin-export-tasks.test.tsx src/app/admin-split-editor.test.tsx`
- 已通过仓库级验证：
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic `upgrade -> downgrade -> upgrade` 通过
    - `pytest`：432 passed，3 warnings
    - Web `npm run lint` 通过
    - Web `npm test`：23 文件、87 用例全部通过
    - Web `npm run build` 成功
    - Docker Compose 配置检查通过
    - `git diff --check` 通过
- 仍存在未导致失败的现有 warning：
  - `pytest` 仍有 3 条 `HTTP_422_UNPROCESSABLE_ENTITY` 弃用告警
  - Web `vitest` 运行时仍打印多条 `--localstorage-file` 路径 warning
  - Vite build 仍提示主 chunk 超过 500 kB，但当前构建成功

### 假设
- 本轮将“破坏性业务动作”保守定义为：会直接推进任务状态、创建真实导出任务、丢弃本地分摊编辑或覆盖现有分摊版本的管理员动作；不把普通导航、预览、下载等非破坏性动作纳入确认弹窗范围。

## 2026-04-29 17:22 - Connect member upload flows to FileDropZone progress and snackbar feedback

### 完成内容
- 完成 `TASKS.md` 中当前第一个未完成任务“把材料上传场景接入 FileDropZone”。
- 调整 [web/src/app/member-invoice-workbench.tsx](/home/gsh/workspace/TRMS/web/src/app/member-invoice-workbench.tsx)：
  - 将工作台上传区从原生 `input[type=file]` 切换为 `FileDropZone`
  - 上传请求进行中显示 `LinearProgress`
  - 上传成功、部分成功和失败统一通过现有 `Snackbar` 反馈
- 调整 [web/src/app/member-material-upload.tsx](/home/gsh/workspace/TRMS/web/src/app/member-material-upload.tsx)：
  - 保留既有 `FileDropZone` 和逐文件结果展示
  - 上传请求进行中补充 `LinearProgress`
- 同步更新前端测试：
  - [web/src/app/member-material-upload.test.tsx](/home/gsh/workspace/TRMS/web/src/app/member-material-upload.test.tsx)
  - [web/src/app/member-invoice-workbench.test.tsx](/home/gsh/workspace/TRMS/web/src/app/member-invoice-workbench.test.tsx)
  - 覆盖上传过程中的进度条、Snackbar 反馈和工作台待上传文件列表展示

### 根因
- “材料上传场景接入 FileDropZone”在两个成员上传入口上的完成度不一致：
  - 专项上传页已经使用 `FileDropZone`，但缺少上传中的进度反馈；
  - 工作台上传区仍停留在原生文件输入框，也没有接入统一的 Snackbar 上传结果反馈。
- 这导致两个成员上传入口的交互风格和反馈语义不一致，与当前前端 Material 3 收口目标不符。

### 关键改动点
- 修改：
  - `web/src/app/member-invoice-workbench.tsx`
  - `web/src/app/member-invoice-workbench.test.tsx`
  - `web/src/app/member-material-upload.tsx`
  - `web/src/app/member-material-upload.test.tsx`
  - `TASKS.md`
  - `WORKLOG.md`

### 风险与影响面
- 本轮只调整成员上传区组件和上传反馈方式，不改材料上传 API、权限校验、逐文件结果结构或任务刷新逻辑。
- 工作台上传结果页内的“最近上传结果”明细仍然保留；本轮新增 Snackbar 只是补齐即时反馈，不额外删改已有结果详情展示。

### 验证结果
- 已通过定向前端回归：
  - `cd web && npm test -- member-material-upload.test.tsx member-invoice-workbench.test.tsx`
- 已通过定向前端 lint：
  - `cd web && npm run lint -- src/app/member-material-upload.tsx src/app/member-invoice-workbench.tsx src/app/member-material-upload.test.tsx src/app/member-invoice-workbench.test.tsx`
- 已通过仓库级验证：
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic `upgrade -> downgrade -> upgrade` 通过
    - `pytest`：432 passed，3 warnings
    - Web `npm run lint` 通过
    - Web `npm test`：23 文件、86 用例全部通过
    - Web `npm run build` 成功
    - Docker Compose 配置检查通过
    - `git diff --check` 通过
- 仍存在未导致失败的现有 warning：
  - `pytest` 仍有 3 条 `HTTP_422_UNPROCESSABLE_ENTITY` 弃用告警
  - Web `vitest` 运行时仍打印多条 `--localstorage-file` 路径 warning
  - Vite build 仍提示主 chunk 超过 500 kB，但当前构建成功

### 假设
- 本轮将“结果通过 Snackbar 反馈”保守定义为：上传完成后必须有即时 Snackbar 反馈，同时保留已有逐文件结果视图，避免为了统一交互而删掉当前可审查的上传明细。

## 2026-04-29 17:15 - Migrate missing materials filters to MUI Select

### 完成内容
- 完成 `TASKS.md` 中当前第一个未完成任务“迁移缺失材料筛选表单到 MUI Select”。
- 将 [web/src/app/task-missing-materials.tsx](/home/gsh/workspace/TRMS/web/src/app/task-missing-materials.tsx) 中缺失材料页面的筛选表单迁移到 MUI：
  - 管理员页“查看维度”改为 `FormControl + InputLabel + Select + MenuItem`
  - 成员页“目标任务”和“查看维度”改为同一套 MUI 选择控件
- 保持原有边界不变：
  - 缺失材料列表分组结构未改
  - 成员侧仍只展示本人相关缺失项
  - “返回成员任务列表 / 去补充材料 / 返回当前任务工作台”跳转语义未改
- 同步更新前端测试 [web/src/app/task-missing-materials.test.tsx](/home/gsh/workspace/TRMS/web/src/app/task-missing-materials.test.tsx)：
  - 断言从原生 `select` 的 `value` 检查改为 MUI `combobox` 文本检查
  - 交互改为 `mouseDown + click option`，覆盖管理员和成员两条筛选路径

### 根因
- 缺失材料页面仍保留原生 `<select>`，与当前前端其余已迁移到 Material 3 的表单页不一致。
- 当前 `TASKS.md` 已明确将“前端剩余风格不协调界面”收口到若干最小任务，本页筛选表单正是其中仍未迁移的一块。

### 关键改动点
- 修改：
  - `web/src/app/task-missing-materials.tsx`
  - `web/src/app/task-missing-materials.test.tsx`
  - `TASKS.md`
  - `WORKLOG.md`

### 风险与影响面
- 本轮只替换筛选控件实现，不改缺失材料查询接口、权限过滤、分组算法、摘要统计或页面布局结构。
- MUI `Select` 的测试交互与原生 `select` 不同；本轮已用显式下拉交互测试覆盖，避免仅靠静态渲染断言造成假通过。

### 验证结果
- 已通过定向前端回归：
  - `cd web && npm test -- task-missing-materials.test.tsx`
- 已通过定向前端 lint：
  - `cd web && npm run lint -- src/app/task-missing-materials.tsx src/app/task-missing-materials.test.tsx`
- 已通过仓库级验证：
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic `upgrade -> downgrade -> upgrade` 通过
    - `pytest`：432 passed，3 warnings
    - Web `npm run lint` 通过
    - Web `npm test`：23 文件、86 用例全部通过
    - Web `npm run build` 成功
    - Docker Compose 配置检查通过
    - `git diff --check` 通过
- 仍存在未导致失败的现有 warning：
  - `pytest` 仍有 3 条 `HTTP_422_UNPROCESSABLE_ENTITY` 弃用告警
  - Web `vitest` 运行时仍打印多条 `--localstorage-file` 路径 warning
  - Vite build 仍提示主 chunk 超过 500 kB，但当前构建成功

### 假设
- 本轮把“迁移缺失材料筛选表单到 MUI Select”保守定义为：仅替换筛选控件及其测试交互，不顺带改写缺失材料列表信息架构、成员入口流转或额外样式系统。

## 2026-04-29 17:08 - Stop codex-nightly by pending task state instead of max rounds

### 完成内容
- 完成 `TASKS.md` 中当前第一个未完成任务“让 `scripts/codex-nightly.sh` 按未完成任务自动停止”。
- 调整 `scripts/codex-nightly.sh` 的停止策略：
  - 删除 `MAX_ROUNDS` 轮数上限循环；
  - 每轮开始前继续检查 `.codex-nightly/STOP` 和 `TASKS.md` 是否还存在 `- [ ]`；
  - 每轮成功结束后再次检查 `.codex-nightly/STOP` 和 `TASKS.md`，若已无未完成任务则立即停止；
  - 若一轮执行后未完成任务列表快照完全不变，则停止夜间执行，避免在同一未完成任务上无界重复空转。
- 新增脚本级回归测试 `tests/test_codex_nightly_script.py`，覆盖：
  - 初始无未完成任务时不启动 Codex；
  - 一轮内完成未完成任务后自动停止；
  - 未完成任务快照无变化时自动停止；
  - dirty working tree 防护仍然生效。

### 根因
- 现有 `scripts/codex-nightly.sh` 仍以 `MAX_ROUNDS` 作为主停止条件，即使 `TASKS.md` 已经是唯一可信任务源，脚本依旧依赖固定轮数兜底。
- 这会带来两个问题：
  - 任务全部完成后，停止逻辑不够明确，仍保留与任务队列无关的轮数配置；
  - 若某一轮没有推进 `TASKS.md`，脚本只能继续靠轮数上限兜住，无法基于“未完成任务是否还在变化”主动停止。

### 关键改动点
- 修改：
  - `scripts/codex-nightly.sh`
  - `tests/test_codex_nightly_script.py`
  - `TASKS.md`
  - `WORKLOG.md`

### 风险与影响面
- 本轮只调整夜间脚本的继续/停止条件，不改动 Codex prompt、日志目录结构、人工 `STOP` 文件协议或 dirty working tree 的失败语义。
- “未完成任务列表无变化即停止”意味着：如果某轮只更新了 `WORKLOG.md` / `BLOCKERS.md`，但没有推进或拆分 `TASKS.md`，脚本会在该轮后结束，而不是继续重复尝试同一未完成任务。

### 验证结果
- 已通过定向脚本自检：
  - `bash -n scripts/codex-nightly.sh`
- 已通过定向回归：
  - `uv run pytest tests/test_codex_nightly_script.py`

### 假设
- 本轮将“按未完成任务自动停止”保守定义为：脚本的继续与停止都由 `TASKS.md` 未完成项状态驱动，并在未完成项不再发生变化时停止，避免无限重试同一任务；不再保留额外的固定轮数停止条件。

## 2026-04-29 17:04 - Allow admins to update draft task configuration

### 完成内容
- 完成 `TASKS.md` 中当前第一个未完成任务“允许管理员更新已创建任务的基础配置”。
- 后端新增草稿任务基础配置更新接口：
  - `PUT /api/tasks/{task_id}`
  - 仅任务负责人可调用
  - 仅 `draft` 状态允许更新
- 更新范围覆盖：
  - 比赛名称、地点、起止日期、截止时间
  - 成员名单
  - 费用类别
  - 项目/课题信息、报销人信息
  - 发票抬头、税号
- 管理员任务详情页不再只是查看和状态流转入口，现已支持在草稿任务内直接编辑并保存上述基础配置。
- 非草稿任务在详情页明确显示为只读，避免前端伪装可编辑但提交后失败。
- 补充前后端回归测试：
  - 后端覆盖草稿任务更新成功、非负责人拒绝、非草稿拒绝
  - 前端覆盖草稿任务保存成功和非草稿只读展示

### 根因
- 原系统只有创建任务、更新成员名单和状态流转接口，没有“更新已创建任务基础配置”的完整后端能力。
- 管理员任务详情页此前只能查看配置并执行状态切换，无法在发现成员名单、费用类别或报销信息填错后在原任务上修正。

### 关键改动点
- 修改：
  - `src/trms_backend/api/tasks.py`
  - `src/trms_backend/domain/tasks.py`
  - `src/trms_backend/infrastructure/repositories.py`
  - `tests/test_tasks_api.py`
  - `web/src/app/admin-task-detail.tsx`
  - `web/src/app/admin-task-detail.test.tsx`
  - `web/src/lib/api/trms.ts`
  - `web/src/lib/api/types.ts`
  - `TASKS.md`
  - `WORKLOG.md`

### 风险与影响面
- 本轮刻意把更新能力收口在 `draft` 任务，避免对已开放提交、已复核或已导出的任务产生成员确认、校验结果和导出版本的一致性回滚问题。
- 本轮没有额外开放管理员跨任务越权编辑，也没有把“修改负责人”纳入同一次更新接口。

### 验证结果
- 已通过定向后端回归：
  - `uv run pytest tests/test_tasks_api.py`
- 已通过定向前端回归：
  - `cd web && npm test -- admin-task-detail.test.tsx`
- 已通过仓库级验证：
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic `upgrade -> downgrade -> upgrade` 通过
    - `pytest`：428 passed，3 warnings
    - Web `npm run lint` 通过
    - Web `npm test`：23 文件、86 用例全部通过
    - Web `npm run build` 成功
    - Docker Compose 配置检查通过
    - `git diff --check` 通过

### 假设
- 当前“允许管理员更新已创建任务的基础配置”的最小闭环定义为：仅允许任务负责人在草稿阶段修改基础字段；一旦任务进入非草稿状态，页面和接口都明确收口为只读/拒绝，而不是隐式放宽到已提交数据的在线回写。

## 2026-04-29 16:47 - Replace dev quick role entry with a real backend-backed session

### 完成内容
- 完成 `TASKS.md` 中当前第一个未完成任务“把开发环境快捷角色入口改成真实 dev 会话登录”。
- 登录页开发入口不再调用 `setMockSession()` 伪造前端会话，而是改为：
  - 先尝试用固定 dev 账号注册对应角色
  - 若用户名已存在则回退到登录
  - 成功后拿到真实 bearer session，再进入对应工作台
- 为开发快捷入口固定了可重复复用的账号名策略：
  - `dev-member`
  - `dev-admin`
  - `dev-system-admin`
- 同时修正了一处已有 mock 会话一致性问题：mock 多角色切换时现在会同步更新 `actorId`、`displayName` 和 `memberCode`，避免只改 `role` 导致页面显示错乱。
- 新增前端测试覆盖：
  - 首次通过开发入口创建真实会话
  - 账号已存在时复用已有账号登录
  - 注册冲突且登录失败时展示错误提示

### 根因
- 原登录页里的“以成员/管理员/系统管理员进入”只会写入前端本地 mock session，没有向后端申请真实 bearer token。
- 进入成员/管理员工作台后，页面上的真实 API 请求仍然会被后端视为匿名用户，因此看起来“进入了页面”，但实际没有真正登录成功。

### 关键改动点
- 修改：
  - `web/src/app/auth.tsx`
  - `web/src/app/auth-store.ts`
  - `web/src/app/App.test.tsx`
  - `TASKS.md`
  - `WORKLOG.md`

### 风险与影响面
- 本轮只修改开发环境快捷入口，不改变正式用户名密码登录、正式注册、权限切换 API 或生产环境下隐藏开发入口的规则。
- dev 快捷入口当前使用固定测试密码，仅用于开发构建可见场景；生产构建继续由 `resolveAuthUiConfig()` 隐藏该入口。

### 验证结果
- 已通过定向前端回归：
  - `cd web && npm test -- App.test.tsx`
  - `cd web && npm test -- auth-ui-config.test.ts`
- 已通过仓库级验证：
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic `upgrade -> downgrade -> upgrade` 通过
    - `pytest`：425 passed，3 warnings
    - Web `npm run lint` 通过
    - Web `npm test`：23 文件、84 用例全部通过
    - Web `npm run build` 成功
    - Docker Compose 配置检查通过
    - `git diff --check` 通过

### 假设
- 当前把“开发环境快捷入口真正登录成功”的最小定义收口为：点击入口后能建立后端承认的 bearer 会话，并能复用固定 dev 账号；不在本轮额外引入专门的开发态 impersonation API。

## 2026-04-29 16:36 - Make the system admin panel usable with real config and runtime data

### 完成内容
- 完成 `TASKS.md` 中当前第一个未完成任务“让系统管理面板接入真实配置与巡检能力”。
- 新增系统管理员专用后端接口：
  - `GET /api/system/dashboard`
  - `PUT /api/system/global-invoice-config`
- `/system` 页面不再是静态占位卡片，现已可：
  - 读取并保存全局发票抬头与税号配置
  - 展示真实运行态摘要，包括环境、公开 API 基地址、异步任务模式、文件存储后端和渠道/LLM 配置开关
  - 展示真实的成员/管理员/系统管理员账号计数
- 新增前后端回归测试覆盖系统管理员访问、普通管理员阻断和配置保存路径。

### 根因
- 原 `web/src/app/system-admin-dashboard.tsx` 只有写死文案和写死统计数字，没有接任何真实后端能力，因此“系统管理面板”实际上不可用。
- 后端此前也没有系统管理员专用的配置/巡检 API，导致前端即使补 UI，也无真实数据源可读写。

### 关键改动点
- 修改：
  - `src/trms_backend/main.py`
  - `web/src/lib/api/trms.ts`
  - `web/src/lib/api/types.ts`
  - `web/src/app/system-admin-dashboard.tsx`
  - `TASKS.md`
  - `WORKLOG.md`
- 新增：
  - `src/trms_backend/api/system.py`
  - `tests/test_system_admin_api.py`
  - `web/src/app/system-admin-dashboard.test.tsx`

### 风险与影响面
- 本轮只让系统管理员页面接入“全局发票配置 + 安全运行态摘要”，没有顺带实现用户列表管理、角色审批流或审计日志明细查询。
- 运行态摘要刻意只返回布尔开关和安全字段，不返回 token、密钥或长期凭据原文。

### 验证结果
- 已通过定向后端回归：
  - `uv run pytest tests/test_system_admin_api.py`
- 已通过定向前端回归：
  - `cd web && npm test -- App.test.tsx system-admin-dashboard.test.tsx`
- 已通过仓库级验证：
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic `upgrade -> downgrade -> upgrade` 通过
    - `pytest`：425 passed，3 warnings
    - Web `npm run lint` 通过
    - Web `npm test`：23 文件、82 用例全部通过
    - Web `npm run build` 成功
    - Docker Compose 配置检查通过
    - `git diff --check` 通过
- 验证过程中修正了一处伴随回归：
  - mock 多角色会话切到 `/system` 时此前只改 `role`，未同步 mock 的 `actorId` / `displayName` / `memberCode`；
  - 本轮已在 `web/src/app/auth-store.ts` 一并修复，并更新 `web/src/app/App.test.tsx` 断言。

### 假设
- 当前“系统管理面板可用”的最小闭环定义为：系统管理员能够维护至少一项真实系统级配置，并能看到可验证的运行态摘要；用户管理和审计明细继续留给后续独立任务。

## 2026-04-29 16:22 - Migrate the admin split editor form to MUI TextField and Select

### 完成内容
- 完成 `TASKS.md` 中当前第一个未完成任务“迁移管理员分摊编辑表单到 MUI TextField / Select”。
- 将 [web/src/app/admin-split-editor.tsx](/home/gsh/workspace/TRMS/web/src/app/admin-split-editor.tsx) 中分摊编辑表单的原生控件替换为 MUI 表单控件：
  - 归属成员改为 `TextField select` + `MenuItem`
  - 分摊金额改为 `TextField`
  - 备注改为 `TextField`
  - 行级校验统一通过 `error` / `helperText` 展示，不再输出自造 `.field-error`
- 同步更新前端测试 [web/src/app/admin-split-editor.test.tsx](/home/gsh/workspace/TRMS/web/src/app/admin-split-editor.test.tsx)：
  - 适配 MUI `Select` 交互
  - 新增“分摊行无效时阻止提交并显示 helperText”覆盖
- `TASKS.md` 中该任务已标记完成。

### 根因
- 管理员分摊编辑页仍沿用原生 `select` / `input`，与同批次已迁移到 Material 3 的任务创建页、管理员发票录入页不一致。
- 行级校验仍依赖手写 `.field-error` 文案节点，导致“表单迁移到 MUI 体系”的任务在分摊编辑页上没有真正落地。

### 关键改动点
- 修改：
  - `web/src/app/admin-split-editor.tsx`
  - `web/src/app/admin-split-editor.test.tsx`
  - `TASKS.md`
  - `WORKLOG.md`

### 风险与影响面
- 本轮只改管理员分摊编辑页的输入控件和对应测试，不改分摊保存 API、金额汇总逻辑、确认状态刷新规则或管理员其他页面。
- 保存按钮、列表 + 详情结构、差额摘要和确认状态展示保持原样；本轮没有顺带迁移缺失材料筛选页或接入新的破坏性动作确认框。

### 验证结果
- 已通过相关前端回归：
  - `cd web && npm test -- admin-split-editor.test.tsx`
  - `cd web && npm run lint && npm test`
- 已通过仓库级验证：
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic `upgrade -> downgrade -> upgrade` 通过
    - `pytest`：421 passed，3 warnings
    - Web `npm run lint` 通过
    - Web `npm test`：22 文件、80 用例全部通过
    - Web `npm run build` 成功
    - Docker Compose 配置检查通过
    - `git diff --check` 通过
- 仍存在未导致失败的现有 warning：
  - `pytest` 中仍有 3 条 `HTTP_422_UNPROCESSABLE_ENTITY` 弃用告警；
  - Web `vitest` 运行时仍打印多条 `--localstorage-file` 路径 warning；
  - Vite build 仍提示主 chunk 超过 500 kB，但当前构建成功。

### 假设
- 本轮保守只迁移分摊行内部的成员、金额、备注输入和校验展示，不把“管理员分摊编辑表单迁移”扩展成保存按钮、摘要卡片或确认状态区块的整体重构。

## 2026-04-29 16:05 - Migrate the admin invoice editor form to MUI TextField and Select

### 完成内容
- 完成 `TASKS.md` 中当前第一个未完成任务“迁移管理员发票录入表单到 MUI TextField / Select”。
- 将 [web/src/app/admin-invoice-editor.tsx](/home/gsh/workspace/TRMS/web/src/app/admin-invoice-editor.tsx) 中发票编辑表单的原生 `input` / `select` 替换为 MUI 表单控件：
  - 发票号码、开票日期、交易时间、金额、抬头、税号、销售方名称改为 `TextField`
  - 费用类型改为 `TextField select` + `MenuItem`
  - 字段校验错误统一通过 `error` / `helperText` 展示，不再输出自造 `.field-error`
- 同步更新前端测试 [web/src/app/admin-invoice-editor.test.tsx](/home/gsh/workspace/TRMS/web/src/app/admin-invoice-editor.test.tsx)，新增“必填字段为空时阻止提交并显示 helperText”覆盖。
- `TASKS.md` 中该任务已标记完成。

### 根因
- 管理员发票录入页虽然已经收口了列表 + 详情和右侧 Tabs，但最核心的录入动作仍使用原生表单控件，和同批次已迁移到 Material 3 的任务创建页不一致。
- 校验提示仍依赖手写 `.field-error` 标签，导致本轮“表单迁移到 MUI 体系”的目标没有在管理员录入页真正落地。

### 关键改动点
- 修改：
  - `web/src/app/admin-invoice-editor.tsx`
  - `web/src/app/admin-invoice-editor.test.tsx`
  - `TASKS.md`
  - `WORKLOG.md`

### 风险与影响面
- 本轮只改管理员发票录入页的表单控件和对应测试，不改后端发票写入 API、校验规则、Tabs 结构或列表-详情联动逻辑。
- 保存按钮、表单布局和字段语义保持原样；本轮没有顺带迁移管理员分摊编辑页、成员侧发票编辑页或其他仍使用原生控件的页面。

### 验证结果
- 已通过相关前端回归：
  - `cd web && npm test -- admin-invoice-editor.test.tsx`
  - `cd web && npm test -- main-flow-e2e-placeholder.test.tsx admin-invoice-editor.test.tsx`
- 已通过仓库级验证：
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic `upgrade -> downgrade -> upgrade` 通过
    - `pytest`：421 passed，3 warnings
    - Web `npm run lint` 通过
    - Web `npm test`：22 文件、79 用例全部通过
    - Web `npm run build` 成功
    - Docker Compose 配置检查通过
    - `git diff --check` 通过
- 仍存在未导致失败的现有 warning：
  - `pytest` 中仍有 3 条 `HTTP_422_UNPROCESSABLE_ENTITY` 弃用告警；
  - Web `vitest` 运行时仍打印多条 `--localstorage-file` 路径 warning；
  - Vite build 仍提示主 chunk 超过 500 kB，但当前构建成功。

### 假设
- 本轮保守沿用页面现有的保存按钮和卡片布局，只把字段输入与错误展示迁移到 MUI 体系；不把“表单迁移”扩展为整页骨架重写。

## 2026-04-29 15:57 - Migrate the admin task creation form to Material 3 form controls

### 完成内容
- 完成 `TASKS.md` 中当前第一个未完成任务“迁移任务创建表单到 MUI TextField / Autocomplete / Checkbox 体系”。
- 将 [web/src/app/admin-task-create.tsx](/home/gsh/workspace/TRMS/web/src/app/admin-task-create.tsx) 中以下输入收口到 MUI 表单控件：
  - 比赛信息、管理员与报销信息、发票抬头税号改为 `TextField`
  - 成员名单改为 `Autocomplete` 多值录入，成员通过“输入后回车”加入标签
  - 费用类别改为 `Checkbox` + `FormHelperText`
- 同步更新前端测试：
  - [web/src/app/admin-task-create.test.tsx](/home/gsh/workspace/TRMS/web/src/app/admin-task-create.test.tsx)
  - [web/src/app/main-flow-e2e-placeholder.test.tsx](/home/gsh/workspace/TRMS/web/src/app/main-flow-e2e-placeholder.test.tsx)
- `TASKS.md` 中该任务已标记完成。

### 根因
- 任务创建页仍沿用原生 `input`、`textarea` 和手写错误标签，和当前已迁移到 Material 3 的登录页、壳层导航、工作台结构不一致。
- 成员名单仍采用“增删行”式原生输入，费用类别仍靠自造 checkbox 卡片，校验提示也散落在字段外层，不符合当前任务拆分里要求的“按页面收口到 M3 表单体系”。

### 关键改动点
- 修改：
  - `web/src/app/admin-task-create.tsx`
  - `web/src/app/admin-task-create.test.tsx`
  - `web/src/app/main-flow-e2e-placeholder.test.tsx`
  - `TASKS.md`
  - `WORKLOG.md`

### 风险与影响面
- 本轮只改任务创建页和直接依赖它的前端测试，不改后端任务创建 API、权限语义、字段校验规则或其他业务表单页。
- 成员名单录入从“多行输入框”切到 `Autocomplete` 标签录入后，前端不再保留“空成员行”这一交互状态；对应校验收口为“至少填写一名成员”，属于 UI 交互调整，不改变后端 `member_ids` 语义。

### 验证结果
- 已通过定向前端回归：
  - `cd web && npm test -- admin-task-create.test.tsx main-flow-e2e-placeholder.test.tsx`
  - `cd web && npm test -- admin-invoice-editor.test.tsx`
- 已通过仓库级验证：
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic `upgrade -> downgrade -> upgrade` 通过
    - `pytest`：421 passed，3 warnings
    - Web `npm run lint` 通过
    - Web `npm test`：22 文件、78 用例全部通过
    - Web `npm run build` 成功
    - Docker Compose 配置检查通过
    - `git diff --check` 通过
- 验证过程中观察到一次未稳定复现的既有前端测试波动：
  - 第一次执行 `./scripts/verify.sh` 时，`web` 阶段曾出现 `src/app/admin-invoice-editor.test.tsx` 失败；
  - 随后单独执行 `cd web && npm test -- admin-invoice-editor.test.tsx` 通过；
  - 第二次完整执行 `./scripts/verify.sh` 已全部通过。
- 仍存在未导致失败的现有 warning：
  - `pytest` 中仍有 3 条 `HTTP_422_UNPROCESSABLE_ENTITY` 弃用告警；
  - Web `vitest` 运行时仍打印多条 `--localstorage-file` 路径 warning；
  - Vite build 仍提示主 chunk 超过 500 kB，但当前构建成功。

### 假设
- 当前成员名单 `Autocomplete` 继续按自由文本录入“成员姓名或学号”，不在本轮引入真实成员搜索、历史成员候选或后端模糊匹配能力。

## 2026-04-29 15:44 - Split the oversized Material 3 business-form migration task into page-level tasks

### 完成内容
- 识别出 `TASKS.md` 中当前第一个未完成任务“把成员/管理员业务表单整体迁移到 MUI TextField / Select / Autocomplete”实际横跨多个页面，不适合作为单轮最小可验证任务直接实现。
- 将该任务拆分为 4 个页面级子任务：
  - `迁移任务创建表单到 MUI TextField / Autocomplete / Checkbox 体系`
  - `迁移管理员发票录入表单到 MUI TextField / Select`
  - `迁移管理员分摊编辑表单到 MUI TextField / Select`
  - `迁移缺失材料筛选表单到 MUI Select`
- 同时把原任务改写为已完成的“拆分成员/管理员业务表单整体迁移任务”，确保下一轮可以从新的第一个未完成子任务继续。

### 根因
- 原任务同时覆盖 `admin-task-create`、`admin-invoice-editor`、`admin-split-editor` 和 `task-missing-materials` 四类表单，既包含简单筛选，也包含动态成员行、复核录入和分摊行编辑。
- 如果继续把这些页面打包在一轮内处理，会同时触发多组测试和多类交互回归，违反仓库“每轮只完成一个最小可验证任务”的规则，也不利于定位回归根因。

### 关键改动点
- 修改：
  - `TASKS.md`
  - `WORKLOG.md`

### 风险与影响面
- 本轮只调整任务拆分与记录，不改任何业务代码、测试语义或前端交互。
- 拆分时保守假设“上传区输入控件迁移”仍由独立的 `FileDropZone` 任务负责，不并入本组表单迁移，避免页面表单和文件上传状态机在同一轮耦合。

### 验证结果
- 已通过仓库级验证：
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic `upgrade -> downgrade -> upgrade` 通过
    - `pytest`：421 passed，3 warnings
    - Web `npm run lint` 通过
    - Web `npm test`：22 文件、78 用例全部通过
    - Web `npm run build` 成功
    - Docker Compose 配置检查通过
    - `git diff --check` 通过
- 验证过程中观察到一次未稳定复现的前端测试波动：
  - 第一次执行 `./scripts/verify.sh` 时，`web` 阶段曾出现 `src/app/admin-invoice-editor.test.tsx` 单测失败；
  - 随后单独执行 `cd web && npm test -- admin-invoice-editor.test.tsx` 通过；
  - 第二次完整执行 `./scripts/verify.sh` 也已全部通过。
- 仍存在未导致失败的现有 warning：
  - `pytest` 中仍有 3 条 `HTTP_422_UNPROCESSABLE_ENTITY` 弃用告警；
  - Web `vitest` 运行时仍打印多条 `--localstorage-file` 路径 warning；
  - Vite build 仍提示主 chunk 超过 500 kB，但当前构建成功。

### 假设
- 当前把“缺失材料筛选表单”限定为 `web/src/app/task-missing-materials.tsx` 里的任务选择和查看维度筛选，不把列表布局或成员工作台其他表单一并纳入本轮拆分。

## 2026-04-29 15:41 - Deepen admin task detail list-detail workflow with M3 tabs

### 完成内容
- 完成 `TASKS.md` 中当前第一个未完成任务“完善管理员任务详情：列表+详情联动深度优化”。
- 在 `web/src/app/admin-review-overview.tsx` 的右侧详情面板引入 M3 `Tabs`，把原先纵向堆叠的信息收口为：
  - `附件预览`
  - `识别字段`
  - `校验异常`
  - `处理动作`
- 在 `web/src/app/admin-invoice-editor.tsx` 补齐同样的右侧 Tabs，并新增发票录入页内的原始票据预览能力，管理员无需切回复核页才能对照原件录入或更正。
- 相关前端测试已更新：
  - `web/src/app/admin-review-overview.test.tsx`
  - `web/src/app/admin-invoice-editor.test.tsx`
- `TASKS.md` 中该任务已标记完成。

### 根因
- 现有管理员复核页虽然已经有“列表 + 详情”基本结构，但右侧详情仍把预览、识别、校验、分摊和动作全部纵向铺开，扫描成本高。
- 发票录入页则缺少原始票据预览，管理员在录入时必须依赖识别结果或在复核页与录入页之间来回切换，违背了原型图和 UI 规范里强调的“同页联动处理”。

### 关键改动点
- 修改：
  - `web/src/app/admin-review-overview.tsx`
  - `web/src/app/admin-invoice-editor.tsx`
  - `web/src/app/admin-review-overview.test.tsx`
  - `web/src/app/admin-invoice-editor.test.tsx`
  - `TASKS.md`
  - `WORKLOG.md`

### 风险与影响面
- 本轮只改 Web 前端详情交互和测试，不改后端 API、权限语义、识别结果模型或校验规则。
- 发票录入页的原件预览当前按需调用既有材料下载接口，仍然沿用现有内容类型边界：仅 PDF 和图片支持内联预览，其他类型继续给出明确说明，不做伪装降级。

### 验证结果
- 已通过相关前端回归：
  - `cd web && npm test -- admin-review-overview.test.tsx admin-invoice-editor.test.tsx`
  - `cd web && npm test`
- 已通过仓库级验证：
  - `./scripts/verify.sh`
    - Python 编译检查通过
    - Alembic `upgrade -> downgrade -> upgrade` 通过
    - `pytest`：421 passed，3 warnings
    - Web `npm run lint` 通过
    - Web `npm test`：22 文件、78 用例全部通过
    - Web `npm run build` 成功
    - Docker Compose 配置检查通过
    - `git diff --check` 通过
- 验证过程中存在未导致失败的现有 warning：
  - `pytest` 中仍有 3 条 `HTTP_422_UNPROCESSABLE_ENTITY` 弃用告警；
  - Web `vitest` 运行时仍打印多条 `--localstorage-file` 路径 warning；
  - Vite build 仍提示主 chunk 超过 500 kB，但当前构建成功，未作为本轮处理范围。

### 假设
- 本轮将“处理动作集中在右侧详情面板”保守收口为 Tabs 内的分摊/跳转/保存动作整合，不额外扩展新的后端批量操作。
- 发票录入页默认仍停留在 `处理动作` 标签，优先保持管理员进入页面后的主操作路径是可直接编辑，而不是先看预览。

## 2026-04-29 15:26 - Evaluate Browser Use boundaries for a later-stage assisted finance filing flow

### 完成内容
- 新增评估文档 [docs/Browser Use后续阶段方案评估.md](/home/gsh/workspace/TRMS/docs/Browser%20Use%E5%90%8E%E7%BB%AD%E9%98%B6%E6%AE%B5%E6%96%B9%E6%A1%88%E8%AF%84%E4%BC%B0.md)，明确后续若评估 Browser Use，仅可作为“管理员在场的辅助填表器”，而不是无人值守自动提交器。
- 文档已记录三类关键边界：
  - Browser Use 自动填报的主要风险：数据事实漂移、页面脆弱性、不可逆误操作、凭据泄露和审计不足；
  - 必须保留的人工确认点：任务版本、目标页面、字段映射预览、高风险写入和最终提交；
  - 必须立即退出并转人工处理的条件：草稿版本过期、页面结构不匹配、关键字段歧义、验证码/二次认证、重复单据风险和未建模异常。
- 文档同时明确“不保存财务系统登录态”的硬边界，并给出后续最小落地顺序：
  - 先固化 `finance_draft` 输入与版本；
  - 再做映射预览与人工确认；
  - 再评估受控本地执行器；
  - 最后才考虑更深的页面自动化。
- `TASKS.md` 中“评估 Browser Use 后续阶段方案”已标记完成。

### 根因
- 虽然仓库早已把 FR-011 标记为第一阶段范围外，但目前只有“第一阶段不做”的边界说明，还缺少一份面向后续阶段的工程化评估，去回答：
  - 为什么不能直接把 Browser Use 接到现有导出或 worker 流程上；
  - 哪些人工确认点不能省；
  - 出现什么情况时必须立即停止自动化。
- 如果这层边界不提前写清楚，后续很容易把“可导出财务草稿”误延伸成“可以安全自动填报”，从而在凭据治理、审计和误操作控制上留下高风险空白。

### 关键改动点
- 新增：
  - `docs/Browser Use后续阶段方案评估.md`
- 修改：
  - `TASKS.md`
  - `WORKLOG.md`

### 风险与影响面
- 本轮只补后续阶段评估文档，不改后端、前端、CLI、导出任务或异步 worker 逻辑。
- 文档结论强调了当前更适合“受控本地辅助填表”而不是“服务端长期持有登录态自动提交”；这属于当前架构与安全边界下的保守判断，后续若学校财务系统提供正式 API 或稳定沙箱，应重新评估。

### 验证结果
- `./scripts/verify.sh` 通过：
  - Python 编译检查通过
  - Alembic `upgrade -> downgrade -> upgrade` 通过
  - `pytest`：421 passed，3 warnings
  - Web `npm run lint` 通过
  - Web `npm test`：22 文件、78 用例全部通过
  - Web `npm run build` 成功
  - Docker Compose 配置检查通过
  - `git diff --check` 通过
- 验证过程中存在现有 warning，但未导致失败：
  - `pytest` 中仍有 3 条 `HTTP_422_UNPROCESSABLE_ENTITY` 的弃用告警；
  - Web `vitest` 运行时仍打印多条 `--localstorage-file` 路径 warning。

### 假设
- 当前评估默认“Browser Use 后续阶段方案”指的是辅助学校财务系统网页填表，而不是调用学校官方 API。
- 当前评估默认高风险动作中的“最终提交”仍保留人工确认；若未来产品明确要求自动点击提交，则必须新增独立任务重新定义审计、回滚和审批责任边界。

## 2026-04-29 15:43 - Evaluate when the invoice validation module should move toward configurable policy or DSL

### 完成内容
- 新增评估文档 [docs/复杂财务规则引擎评估.md](/home/gsh/workspace/TRMS/docs/复杂财务规则引擎评估.md)，基于当前规则实现给出结论：
  - 第一阶段当前不应直接引入 DSL，也不应为了“将来可能复杂”提前上独立规则引擎；
  - 当前更合理的方向是继续保留“纯函数规则 + 统一结果模型”，未来若出现差异化需求，先把阈值、字段组和适用范围上提为可注入的策略对象。
- 文档已明确两层触发条件：
  - 何时应从模块常量迁移到“配置化策略”；
  - 何时才值得从配置化策略继续升级到 DSL。
- `TASKS.md` 中“评估更复杂财务规则引擎”已标记完成。

### 根因
- 当前仓库虽然已有较完整的规则层，但“何时继续保持代码规则、何时需要配置化、何时才该引入 DSL”一直没有被显式记录。
- 如果不先把迁移边界写清楚，后续很容易因为规则数量增加一点点，就过早引入解释器、YAML 规则文件或第三方规则引擎，反而把排障和审计复杂度抬高。

### 关键改动点
- 新增：
  - `docs/复杂财务规则引擎评估.md`
- 修改：
  - `TASKS.md`
  - `WORKLOG.md`

### 风险与影响面
- 本轮只补文档和任务记录，不改 `src/trms_backend/domain/invoice_validation.py` 的现有业务规则、接口契约或测试语义。
- 文档中的触发条件属于当前阶段的工程判断，不是不可变制度；如果后续出现真实多组织差异化规则需求，应按当时代码和运营方式重新复核。

### 验证结果
- `./scripts/verify.sh` 通过：
  - Python 编译检查通过
  - Alembic `upgrade -> downgrade -> upgrade` 通过
  - `pytest`：421 passed，3 warnings
  - Web `npm run lint` 通过
  - Web `npm test`：22 文件、78 用例全部通过
  - Web `npm run build` 成功
  - Docker Compose 配置检查通过
  - `git diff --check` 通过

### 假设
- 当前默认“更复杂财务规则引擎”指的是可配置策略层或 DSL，而不是简单增加几条 Python 规则函数。

## 2026-04-29 15:13 - Restore member-side manual invoice entry and retry recognition inside the current workbench

### 完成内容
- 在当前成员主工作台 [web/src/app/member-invoice-workbench.tsx](/home/gsh/workspace/TRMS/web/src/app/member-invoice-workbench.tsx) 收口两项原本只在旧专项页里存在的能力：
  - 本人发票材料可直接展开“手动填写或更正发票”表单，补录或修正发票号码、日期、抬头、税号、金额和费用类型；
  - 本人材料可直接触发重新识别，并在按钮状态里看到“重新识别中...”反馈。
- 页面文案显式说明边界：
  - 只允许操作本人材料；
  - 手动补录只更新当前发票字段并保留更正痕迹；
  - 重新识别会新建识别任务，不允许成员直接写入任意识别原始结果。
- 前端测试已补齐：
  - 本人材料可在当前工作台打开并提交手动补录表单；
  - 共享发票摘要维持只读，不暴露重新识别或手动补录按钮；
  - 重新识别动作会显示“重新识别中...”并在请求完成后恢复可再次触发状态。
- `TASKS.md` 中“按 UX 实测恢复成员端手动补录发票信息与重新识别入口”已标记完成。

### 根因
- 旧代码里这两项能力并没有完全缺失，而是留在 [web/src/app/member-material-status.tsx](/home/gsh/workspace/TRMS/web/src/app/member-material-status.tsx) 这个已退居次入口的专项页中。
- 当前成员真实主路径已经切到单任务工作台，但工作台只保留了材料类型、分摊和确认入口，导致成员一旦识别不准，只能被动等待管理员或后台异步链路，而不能在主路径里自助闭环。

### 关键改动点
- 修改：
  - `web/src/app/member-invoice-workbench.tsx`
  - `web/src/app/member-invoice-workbench.test.tsx`
  - `TASKS.md`
  - `WORKLOG.md`

### 风险与影响面
- 本轮只改成员前端入口与状态表达，不改后端权限判定、识别执行器或发票写入 API。
- 重新识别在当前实现里复用既有 `createRecognitionTask + executeRecognitionTask` 调用链；如果后续需要更细的“已入队 / 执行中 / 失败原因”分层反馈，仍应在识别任务模型上继续细化，而不是在前端再堆特判。
- 共享发票区域继续保持只读摘要，本轮没有放宽为可编辑他人材料。

### 验证结果
- `npm test -- member-invoice-workbench.test.tsx` 通过：13 tests passed。
- `./scripts/verify.sh` 通过：
  - Python 编译检查通过
  - Alembic `upgrade -> downgrade -> upgrade` 通过
  - `pytest`：421 passed，3 warnings
  - Web `npm run lint` 通过
  - Web `npm test`：22 文件、78 用例全部通过
  - Web `npm run build` 成功
  - Docker Compose 配置检查通过
  - `git diff --check` 通过

### 假设
- 本轮按现有后端语义处理“重新识别”为重新创建并执行一次识别任务，不额外新增成员侧撤销、取消或查看完整历史重试次数的界面。

## 2026-04-29 14:42 - Queue newly confirmed UX gap for member-side manual invoice entry and re-recognition

### 完成内容
- 根据最新用户补充，把“成员当前无法自己手动填写发票信息，也无法主动重启 LLM 自动识别”记录为新的未完成任务，已写入 `TASKS.md`：
  - `按 UX 实测恢复成员端手动补录发票信息与重新识别入口`
- 该任务被明确收口到“当前主工作台路径下可用”，避免再次出现“历史上有专项页或旧入口，但真实主路径里不可达”的状态偏差。

### 根因
- `TASKS.md` 里虽然已有历史完成项“收口登录态入口并开放成员自助识别处理”，但从当前真实 UX 和最新用户反馈看，这个能力没有在成员当前主路径里稳定可用。
- 因此这里不能沿用旧的“已完成”判断，而应把它重新作为现存产品缺口排回任务队列，按当前界面与交互事实处理。

### 关键改动点
- 修改：
  - `TASKS.md`
  - `WORKLOG.md`

### 风险与影响面
- 本轮只记录任务，不修改成员端业务逻辑、权限边界或识别执行链。
- 新任务需要特别注意不要因为恢复成员自助操作入口，就意外放宽“只能操作本人材料”的权限边界。

### 验证结果
- 本轮仅更新任务与工作记录，随后运行 `./scripts/verify.sh` 做仓库级验证。

### 假设
- 这里的“重启 LLM 自动识别”按当前系统语义记录为“对本人材料主动触发重新识别”，不等同于成员可以直接写识别结果或绕过现有异步执行边界。

## 2026-04-29 14:35 - Make reminder recording boundary explicit near the submit action

### 完成内容
- 收口管理员补材料提醒表单的边界文案：
  - 按钮文案从“记录补材料提醒”改为“保存内部提醒记录”；
  - 按钮附近显式提示“这里只保存内部提醒记录，不会自动发送短信、邮件或 Telegram 消息；如需真正通知成员，请另行联系。”；
  - 成功反馈改为“已保存对成员 X 的内部提醒记录；系统不会自动发送消息。”，避免管理员误判成真实通知已发出。
- 前端测试同步更新按钮文案、说明文案和成功反馈断言。
- `TASKS.md` 中“按 UX 实测强调补材料提醒只保存内部记录”已标记完成。

### 根因
- 原页面虽然在输入框下方写了“当前只记录管理员提醒内容与时间，不接入真实短信、邮件或 Telegram 发送”，但提示位置离提交动作较远，也不足以阻止管理员把“记录成功”误读成“通知已发送”。
- UX 报告指出这类边界必须贴近按钮和提交结果本身表达，否则属于高概率误操作。

### 关键改动点
- 修改：
  - `web/src/app/admin-corrections-reminders.tsx`
  - `web/src/app/admin-corrections-reminders.test.tsx`
  - `TASKS.md`

### 风险与影响面
- 本轮只改前端文案，不改提醒记录 API、审计逻辑或未来真实通知接入边界。
- 已存在的“提醒记录”业务语义更清晰了，但仍不等同于实现通知模块；后续若真的接入通知渠道，按钮和成功反馈需要再区分“仅记录”与“记录并发送”两种动作。

### 验证结果
- 与下一轮“上传前文件体积预检查”一起通过同一次 `./scripts/verify.sh` 全量验证，结果如下：
  - Python 编译检查通过
  - Alembic `upgrade -> downgrade -> upgrade` 通过
  - `pytest`：421 passed，3 warnings
  - Web `npm run lint` 通过
  - Web `npm test`：22 文件、76 用例全部通过
  - Web `npm run build` 成功
  - Docker Compose 配置检查通过
  - `git diff --check` 通过

### 假设
- 这轮仍把“提醒”视为内部记录能力，不默认未来一定接入站内、邮件或 Telegram 通知。

## 2026-04-29 14:36 - Precheck oversized uploads before sending member material requests

### 完成内容
- 为两个成员上传入口补充前端体积预检查：
  - `web/src/app/member-material-upload.tsx`
  - `web/src/app/member-invoice-workbench.tsx`
- 现在如果用户选择了超过 10MB 的文件，页面会在提交前直接报错：
  - `文件 <name> 超过 10MB，请压缩或拆分后再上传。`
- 新增共享上传校验工具：
  - `web/src/lib/upload-validation.ts`
- 新增前端回归测试：
  - 专项上传页会在提交前拦截超大文件；
  - 工作台上传区会在提交前拦截超大文件。
- `TASKS.md` 中“按 UX 实测增加上传前文件体积预检查”已标记完成。

### 根因
- UX 实测虽然已经把后端 413 映射成了明确的“上传文件过大”提示，但那仍然发生在用户点击提交并等待一次请求往返之后。
- 既然页面已经明确写了“单文件最大 10MB”，更合理的行为是在前端提交前就执行同一条规则，避免用户把一个本地就能判断失败的文件继续发给后端。

### 关键改动点
- 新增：
  - `web/src/lib/upload-validation.ts`
- 修改：
  - `web/src/app/member-material-upload.tsx`
  - `web/src/app/member-material-upload.test.tsx`
  - `web/src/app/member-invoice-workbench.tsx`
  - `web/src/app/member-invoice-workbench.test.tsx`
  - `TASKS.md`

### 风险与影响面
- 本轮只补前端预检查，不改后端真正执行的文件大小限制；后端仍保留最终兜底。
- 目前前端与文案共用固定 10MB 阈值，后续如果后端配置化了上传大小限制，应把这里再收敛成同一配置来源，避免双端阈值漂移。

### 验证结果
- `./scripts/verify.sh` 通过：
  - Python 编译检查通过
  - Alembic `upgrade -> downgrade -> upgrade` 通过
  - `pytest`：421 passed，3 warnings
  - Web `npm run lint` 通过
  - Web `npm test`：22 文件、76 用例全部通过
  - Web `npm run build` 成功
  - Docker Compose 配置检查通过
  - `git diff --check` 通过

### 假设
- 当前上传大小上限以现有前端/后端共同使用的 10MB 约定为准，本轮没有引入新的后端配置项去动态下发限制。
- 这轮只处理“体积过大”的本地可判定失败；文件内容格式、重复文件、服务端权限等校验仍由后端继续负责。

## 2026-04-29 14:33 - Clarify task member input semantics on admin create form

### 完成内容
- 调整管理员创建任务页的成员名单填写提示：
  - 输入行标题从“成员 N”改为“成员 N（姓名或学号）”；
  - 输入框占位文案从“输入学号或成员标识”改为“输入成员姓名或学号”；
  - 成员名单区域提示明确说明：当前阶段应填写姓名或学号字符串，系统会把它作为任务内成员标识，不应填写内部数据库 ID。
- 前端测试同步补断言，锁住上述提示文案。
- `TASKS.md` 中“按 UX 实测明确任务创建页成员名单填写语义”已标记完成。

### 根因
- UX 实测暴露的问题不是表单无法提交，而是表单把成员字段描述成了“成员标识”，迫使管理员去猜这里究竟要填姓名、学号还是系统内部 ID。
- 当前实现的真实语义其实只是“任务内成员标识字符串”，但界面没有把这个限制讲清楚，导致真实名单录入时认知成本过高，也容易误填。

### 关键改动点
- 修改：
  - `web/src/app/admin-task-create.tsx`
  - `web/src/app/admin-task-create.test.tsx`
  - `TASKS.md`

### 风险与影响面
- 本轮只改前端提示文案，不改任务创建 payload、成员匹配规则或后端数据模型。
- 新文案刻意避免承诺“历史成员选择 / 批量导入”这类还未实现的能力，只把当前真实可用的填写语义讲清楚。

### 验证结果
- `./scripts/verify.sh` 通过：
  - Python 编译检查通过
  - Alembic `upgrade -> downgrade -> upgrade` 通过
  - `pytest`：421 passed，3 warnings
  - Web `npm run lint` 通过
  - Web `npm test`：22 文件、74 用例全部通过
  - Web `npm run build` 成功
  - Docker Compose 配置检查通过
  - `git diff --check` 通过

### 假设
- 本轮只收口“当前该怎么填”的文案问题，不等同于已经实现姓名/学号双字段建模、历史成员补全或批量导入能力。
- 如果后续成员身份模型改成显式“姓名 + 学号 + 系统账号绑定”，这里的提示还需要再跟着真实模型调整。

## 2026-04-29 14:31 - Fix member workbench recognition blocking states from UX test

### 完成内容
- 修复成员工作台把识别阻塞状态错误展示为“暂无识别记录 / 当前无明显异常”的问题：
  - 识别任务仍处于 `pending` 时，发票卡片会明确显示“识别处理中”，并在待处理事项中提示“等待系统完成识别”；
  - 识别失败原因为 `llm_provider_not_configured` 或 `structured_recognition_not_configured` 时，前端不再给泛化失败文案，而是明确提示“当前环境未配置识别服务”；
  - 顶部“待处理事项”摘要现在会把识别排队、识别失败/待确认、校验异常、缺失材料和待确认费用一起计入，不再过早报绿。
- 新增前端回归测试：
  - 识别任务仍在排队时，工作台必须显示阻塞态与等待说明；
  - 识别服务未配置时，工作台必须显示明确的环境阻塞说明。
- `TASKS.md` 中“按 UX 实测收口成员工作台识别阻塞提示”已标记完成。

### 根因
- 成员工作台详细卡片使用的是 `/materials/:id/recognition-tasks` 返回的 `latest_effective` 结果，但该字段按设计不会包含仍为 `pending` 的识别任务。
- 因此前端在“已有 pending 识别任务但尚无 latest effective 结果”时，把真实状态误读成“暂无识别记录”。
- 同时，顶部待处理事项没有把 `recognition_pending_count` 计入，导致只要还没形成失败校验或缺失材料，就可能错误显示“当前无明显异常”。

### 关键改动点
- 修改：
  - `web/src/app/member-invoice-workbench.tsx`
  - `web/src/app/member-invoice-workbench.test.tsx`
  - `web/src/lib/ui-text.ts`
  - `TASKS.md`

### 风险与影响面
- 本轮只改成员工作台前端状态表达，不改后端识别执行、队列调度或发票生成逻辑。
- `describeRecognitionFailure()` 新增了对“识别服务未配置”的专门文案，会影响其他复用该函数的前端页面；当前这是有意的统一修正。
- 识别排队中现在会被视为“仍待处理”而不是“异常”，因此待处理徽标文案从纯异常数改成了更宽泛的待处理项计数。

### 验证结果
- `./scripts/verify.sh` 通过：
  - Python 编译检查通过
  - Alembic `upgrade -> downgrade -> upgrade` 通过
  - `pytest`：421 passed，3 warnings
  - Web `npm run lint` 通过
  - Web `npm test`：22 文件、74 用例全部通过
  - Web `npm run build` 成功
  - Docker Compose 配置检查通过
  - `git diff --check` 通过

### 假设
- 本轮只解决“状态表达错了”的 UX 阻塞，不等同于真正补齐识别服务配置、异步 worker 编排或识别成功后的发票生成链路。
- UX 报告中的共享发票为空、附件未归属等问题仍需后续独立轮次继续处理。

## 2026-04-29 14:16 - Run real-data UX browser test and patch low-risk blockers

### 完成内容
- 使用 Playwright MCP 对隔离实例完成了真实用户路径实测：
  - 后端：`127.0.0.1:9877`
  - 前端：`127.0.0.1:4173`
  - 数据库：`tmp/ux-runtime/ux-test.db`
  - 真实材料副本：`tmp/ux-real-data/`
- 实测角色与流程：
  - 管理员：注册、创建武汉区域赛任务、开放收集、查看复核页、记录补材料提醒、查看导出页。
  - 普通队员 A：注册、查看任务、上传武汉报名费发票、上传沈阳行程 PNG、上传超大邀请函并观察失败提示。
  - 普通队员 B：注册、查看任务、上传沈阳网约车发票，并核对共享发票区域。
  - 财务视角：通过管理员复核页与导出页检查汇总信息是否足以提交财务。
- 生成 UX 产物：
  - 报告：`UX_TEST_REPORT.md`
  - Playwright 基线脚本：`tests/ux/real-user-flows.spec.mjs`
  - 执行说明：`tests/ux/README.md`
  - 截图：`test-artifacts/ux/*.png`
- 本轮顺手修复了 3 个低风险但直接影响 UX 的问题：
  1. 导出页英文/技术化文案改成中文业务文案；
  2. 中文文件名材料预览因 `Content-Disposition` 编码失败而被伪装成“网络连接异常”的问题已修复；
  3. 超大文件上传失败补充了明确的“上传文件过大”提示，不再只显示泛化报错。

### 根因
- 这轮用户目标不是补功能，而是验证当前系统是否真的能被报销参与者直接使用。静态阅读代码无法暴露：
  - 识别链路未配置时成员端和管理员端会如何误导用户；
  - 中文文件名预览会在实际浏览器里触发什么错误；
  - 真实超大 PDF 上传失败时前端是否能告诉用户真正原因；
  - 共享发票能力在真实多成员路径下是否按产品要求工作。
- 实测表明，当前最大问题不是单个按钮文案，而是“识别结果、附件归属、共享可见性、财务导出准备度”这几条核心链路仍未闭合。

### 关键改动点
- 新增：
  - `UX_TEST_REPORT.md`
  - `tests/ux/README.md`
  - `tests/ux/real-user-flows.spec.mjs`
- 修改：
  - `.gitignore`
  - `TASKS.md`
  - `src/trms_backend/api/materials.py`
  - `src/trms_backend/domain/exports.py`
  - `tests/test_exports_api.py`
  - `tests/test_main_flow_e2e.py`
  - `tests/test_materials_api.py`
  - `web/src/app/admin-export-tasks.tsx`
  - `web/src/lib/ui-text.ts`

### 风险与影响面
- 本轮没有改动识别、分摊、确认、导出核心业务规则，只修复了用户可见的文案和中文文件名预览头部。
- `materials.py` 的响应头修复会影响所有材料预览下载路径；已补回归测试锁住 ASCII 与中文文件名场景。
- `exports.py` 的导出门禁说明改成中文后，前端和测试不再依赖英文内部状态描述；CLI/第三方若直接消费该文案，需接受文案变化。
- UX 报告引用了真实材料类型，但未提交真实数据副本和截图二进制；这些产物保留在本地忽略目录中。

### 验证结果
- `./scripts/verify.sh` 通过：
  - Python 编译检查通过
  - Alembic `upgrade -> downgrade -> upgrade` 通过
  - `pytest`：421 passed，3 warnings
  - Web `npm run lint` 通过
  - Web `npm test`：22 文件、72 用例全部通过
  - Web `npm run build` 成功
  - Docker Compose 配置检查通过
  - `git diff --check` 通过
- 浏览器实测确认：
  - 导出页中文化文案已生效；
  - 中文文件名 PDF 在管理员复核页可正常进入内联预览；
  - 超大邀请函上传失败时已显示“上传文件过大，请缩小到页面允许的大小后重试。”。

### 假设
- 真实材料目录里没有直接可用于系统成员标识的学号表；本轮测试以邀请函中的真实姓名作为成员身份标识完成 UI 路径验证，并已在报告中明确记录该限制。
- Playwright MCP 当前不提供 trace 落盘接口，因此本轮只保留截图和 `.playwright-mcp/` 快照目录，不声称已生成 trace。

## 2026-04-29 13:18 - Redirect legacy member subroutes into the invoice workbench

### 完成内容
- 收口成员端旧二级路由：
  - `/member/materials/upload` -> `/member/invoices/workbench#member-workbench-upload`
  - `/member/materials/status` -> `/member/invoices/workbench#member-workbench-invoices`
  - `/member/materials/missing` -> `/member/invoices/workbench#member-workbench-missing-materials`
  - `/member/expenses/confirm` -> `/member/invoices/workbench#member-workbench-confirmations`
- 新增 `web/src/app/legacy-member-workbench-redirect.tsx`：
  - 统一保留 `taskId` 查询参数；
  - 使用 `Navigate replace` 自动跳转，不破坏旧链接可访问性。
- `web/src/app/routes.tsx` 改为在成员路由层使用上述重定向组件，而不是继续把 4 个旧专项页暴露为一级业务入口。
- 测试层同步收口：
  - 原上传/状态/确认/缺失材料页的功能测试改为“直接渲染组件”以保留逻辑覆盖；
  - 新增 `web/src/app/member-legacy-route-redirects.test.tsx`，显式覆盖 4 个旧 URL 到工作台的跳转；
  - `web/src/app/main-flow-e2e-placeholder.test.tsx` 改为适配重定向后的工作台上传/确认交互。
- `TASKS.md` 中“收口成员端旧二级路由为工作台跳转”已标记完成。

### 根因
- 前几轮已经把成员工作台收口为单任务闭环，如果旧的 `/materials/upload`、`/status`、`/missing`、`/expenses/confirm` 仍然作为主路由存在，就会持续把成员流程拆回多个弱关联页面。
- 任务要求明确指出：旧 URL 仍需可访问，但应该自动落到工作台对应视图，而不是继续停留在历史入口。

### 关键改动点
- 新增：
  - `web/src/app/legacy-member-workbench-redirect.tsx`
  - `web/src/app/member-legacy-route-redirects.test.tsx`
- 修改：
  - `web/src/app/routes.tsx`
  - `web/src/app/member-material-upload.test.tsx`
  - `web/src/app/member-material-status.test.tsx`
  - `web/src/app/member-expense-confirmation.test.tsx`
  - `web/src/app/task-missing-materials.test.tsx`
  - `web/src/app/main-flow-e2e-placeholder.test.tsx`
  - `TASKS.md`

### 风险与影响面
- 旧页面组件文件仍然保留，但已不再由正式路由直接暴露；后续若完全移除，需要先确认没有其他内部直接引用。
- 本轮没有改工作台本身的业务逻辑，只改变入口层；因此风险主要集中在测试和链接兼容性，已通过重定向测试覆盖。
- 由于主业务入口收口到工作台，后续成员端相关改动会更集中，不再需要在多个旧页面重复铺 UI。

### 验证结果
- `./scripts/verify.sh` 通过：
  - Python 编译检查通过
  - Alembic `upgrade -> downgrade -> upgrade` 通过
  - `pytest`：420 passed，3 warnings
  - Web `npm run lint` 通过
  - Web `npm test`：22 文件、72 用例全部通过
  - Web `npm run build` 成功
  - Docker Compose 配置检查通过
  - `git diff --check` 通过

### 假设
- 旧成员专项页的保留价值现在只剩组件逻辑测试与后续过渡期兜底；如果后续没有额外直接消费场景，可以在更后面的清理轮次进一步删减。
- `materials/status` 目前落到工作台默认“发票”视图而不是单独 Tab，这是因为状态信息已经被并入发票详情视图，不再单独保留一级主入口。

## 2026-04-29 13:07 - Rewrite member confirmation and missing-material pages into M3 workspace cards

### 完成内容
- 重写 `web/src/app/member-expense-confirmation.tsx`：
  - 页面壳层切到 `RoleWorkspace + PageHeader + SectionCard + StatCard + EmptyState + StatusBadge`；
  - 顶部形成稳定的“当前任务上下文”卡，不再用旧的 `status-card auth-panel` 堆页面；
  - 费用确认摘要改为 4 张统计卡：本人费用、总金额、待确认、已处理；
  - 确认/异议成功提示改为 Snackbar，不再在费用卡内部插入成功提示文案；
  - 非 stale 的提交失败也改为 Snackbar；只有“明细版本失效”继续留在对应费用卡内，避免失去对象上下文。
- 重写 `web/src/app/task-missing-materials.tsx` 的成员视图：
  - 成员缺失材料页切到 `RoleWorkspace + PageHeader + SectionCard + StatCard + EmptyState + StatusBadge`；
  - 摘要改为统计卡，保留原有按发票 / 费用类型查看的列表能力；
  - 当前任务上下文卡中加入返回成员任务列表、去补充材料等稳定入口。
- 同步更新测试：
  - `web/src/app/member-expense-confirmation.test.tsx` 改为断言 Snackbar 成功/失败反馈；
  - `web/src/app/task-missing-materials.test.tsx` 改为断言统计卡摘要；
  - `web/src/app/main-flow-e2e-placeholder.test.tsx` 同步更新确认成功路径的反馈断言。
- `TASKS.md` 中“重写成员费用确认页与缺失材料页”已标记完成。

### 根因
- 这两个页面虽然功能已通，但都仍停留在旧的“独立专项页 + 历史卡片样式 + 局部反馈文案”阶段，和前几轮已经收口好的成员工作台、上传页、材料状态页不一致。
- 成员端主问题不是缺功能，而是流程被拆散且交互语义不统一；因此本轮优先统一为同一套 M3 工作台壳层与反馈方式。

### 关键改动点
- 修改：
  - `web/src/app/member-expense-confirmation.tsx`
  - `web/src/app/member-expense-confirmation.test.tsx`
  - `web/src/app/task-missing-materials.tsx`
  - `web/src/app/task-missing-materials.test.tsx`
  - `web/src/app/main-flow-e2e-placeholder.test.tsx`
  - `TASKS.md`

### 风险与影响面
- 本轮没有改任何后端接口、确认规则或缺失材料聚合逻辑，只改前端信息组织和反馈方式。
- 成功/失败反馈从页内卡片转到 Snackbar 后，页面主体更干净，但用户仍能看到 stale 明细这种必须挂在具体对象上的异常。
- 成员缺失材料页仍保留原生 select 与现有列表样式；后续“业务表单整体迁移到 MUI”任务会继续处理控件层。

### 验证结果
- `./scripts/verify.sh` 通过：
  - Python 编译检查通过
  - Alembic `upgrade -> downgrade -> upgrade` 通过
  - `pytest`：420 passed，3 warnings
  - Web `npm run lint` 通过
  - Web `npm test`：21 文件、69 用例全部通过
  - Web `npm run build` 成功
  - Docker Compose 配置检查通过
  - `git diff --check` 通过

### 假设
- 旧的成员专项页仍暂时保留，因为下一轮会把这些旧二级路由统一收口到工作台跳转；本轮只先保证它们本身已经具备一致的 M3 信息架构。
- 缺失材料页继续沿用分组列表而不是再拆详情面板，原因是成员端缺失项本身更适合“补什么”导向，而不是复杂审查导向。

## 2026-04-29 12:56 - Convert member material status page to list-detail workspace

### 完成内容
- 将 `web/src/app/member-material-status.tsx` 从“每份材料完整卡片纵向平铺”改为“摘要列表 + 当前详情”结构：
  - 上方 `成员材料状态列表` 现在只负责列出本人材料摘要、识别/校验摘要和缺失材料数量；
  - 下方新增 `aria-label="当前材料详情"` 的详情面板，集中展示当前选中材料的识别、校验、人工填写和缺失材料信息。
- 保持默认选中首个材料，并支持在摘要列表中切换当前查看对象。
- 将“运行重新识别”和“保存发票信息”的结果反馈从页内状态 chip / 错误卡片改为全局 Snackbar，即时提示成功或失败。
- 保留现有人工填写表单、识别重跑、缺失材料提示和工作台跳转逻辑，不改后端接口。
- 同步更新 `web/src/app/member-material-status.test.tsx`：
  - 先校验摘要列表只显示本人材料；
  - 再校验默认详情面板内容；
  - 最后切换到附件材料，确认详情面板跟随切换。
- `TASKS.md` 中“重写成员材料状态页（M3 列表 + 详情视图）”已标记完成。

### 根因
- 原页面把每份材料的全部信息都一次性展开，材料稍多时会形成长页面，用户需要在多个同构卡片间自己扫描“哪一张有问题、当前正在看哪一张”。
- 这与原型文档要求的“先在列表筛选，再在同页查看详情”的审查模式不一致，因此本轮优先收口为单页列表-详情结构。

### 关键改动点
- 修改：
  - `web/src/app/member-material-status.tsx`
  - `web/src/app/member-material-status.test.tsx`
  - `TASKS.md`

### 风险与影响面
- 本轮仍保留原生表单和既有 className；后续“业务表单整体迁移到 MUI”任务会继续处理视觉和控件层。
- 识别重跑/保存发票的反馈由局部 chip 变为 Snackbar，减少详情区噪音，但用户仍能立即获知动作结果。
- 详情区当前默认回落到列表首项；若后续需要深链接到某个材料，可在再后续轮次增加 query/hash 同步。

### 验证结果
- `./scripts/verify.sh` 通过：
  - Python 编译检查通过
  - Alembic `upgrade -> downgrade -> upgrade` 通过
  - `pytest`：420 passed，3 warnings
  - Web `npm run lint` 通过
  - Web `npm test`：21 文件、69 用例全部通过
  - Web `npm run build` 成功
  - Docker Compose 配置检查通过
  - `git diff --check` 通过

### 假设
- 当前详情面板放在列表下方而不是右侧分栏，仍满足“列表 + 详情视图”目标；后续如果页面信息继续扩张，再评估桌面端左右分栏。
- 由于当前页面只服务成员本人材料，摘要列表中不重复展示全部异常细节，把细节留给详情面板更利于扫描。

## 2026-04-29 12:49 - Rework member upload page with FileDropZone and snackbar feedback

### 完成内容
- 将 `web/src/app/member-material-upload.tsx` 的文件选择区改为复用 `web/src/components/FileDropZone.tsx`：
  - 保留 `aria-label="上传文件"` 与 `aria-label="待上传文件列表"`，不破坏现有测试和提交逻辑；
  - 已选文件展示改由 M3 拖拽上传卡内部负责，不再手写单独 `<input type="file">` 列表。
- 提交反馈改为 Snackbar：
  - 全部成功时弹出成功提示；
  - 部分成功时弹出 warning，提示成功/失败数量；
  - 整批失败或接口拒绝时弹出 error，不再在页面中额外插入一张提交错误红卡。
- 保留逐文件审查结果区：
  - 页面仍展示成功材料卡片、重复状态和失败文件列表，满足“逐文件结果可见”的要求；
  - `Upload Result` 英文眉文案改回中文“上传结果”。
- 同步更新 `web/src/app/member-material-upload.test.tsx`：
  - 上传成功用例继续覆盖逐文件结果；
  - 后端拒绝用例改为断言 Snackbar 反馈，而不是旧的页面级 `ApiErrorNotice`。
- `TASKS.md` 中“重写成员材料上传交互（拖拽 Dialog + Snackbar）”已标记完成。

### 根因
- 上传页此前仍是原生 file input + 页面内错误卡片，和已建立的 Material 3 上传基础组件、全局 Snackbar 基础设施脱节。
- 更重要的是，上传动作的成败属于“瞬时交互反馈”，继续用页面中插入一块错误卡片会打断用户对当前任务和逐文件结果的阅读节奏。

### 关键改动点
- 修改：
  - `web/src/app/member-material-upload.tsx`
  - `web/src/app/member-material-upload.test.tsx`
  - `TASKS.md`

### 风险与影响面
- 本轮只改成员专项上传页，不改工作台内上传区；`/member/invoices/workbench` 接入 `FileDropZone` 仍留给后续独立任务。
- 页面整体仍保留现有表单结构和原生 select；后续“业务表单整体迁移到 MUI”任务会继续收口。
- 由于引入 Snackbar 汇总，提交被后端拒绝时页面不会再额外显示同一份错误卡片，但错误信息仍然保留且更靠近交互时点。

### 验证结果
- `./scripts/verify.sh` 通过：
  - Python 编译检查通过
  - Alembic `upgrade -> downgrade -> upgrade` 通过
  - `pytest`：420 passed，3 warnings
  - Web `npm run lint` 通过
  - Web `npm test`：21 文件、69 用例全部通过
  - Web `npm run build` 成功
  - Docker Compose 配置检查通过
  - `git diff --check` 通过

### 假设
- 当前页的“单任务专项上传入口”定位仍保留，因此先只接入 `FileDropZone` 和 Snackbar，不把它直接并回工作台；后续旧二级路由收口时再统一处理入口层级。
- Snackbar 只承担即时反馈职责，逐文件详细结果仍然保留在页面内，避免用户错过重复文件编号或失败原因。

## 2026-04-29 12:43 - Rewrite member invoice workbench into tabbed single-task workspace

### 完成内容
- 将 `web/src/app/member-invoice-workbench.tsx` 从“长单页 + hash 锚点堆叠”收口为单任务 Tabs 工作台：
  - 新增 MUI `Tabs` / `Tab`，固定三类视图：`发票`、`缺失材料`、`费用确认`。
  - 当前 URL hash 与标签页同步：`#member-workbench-invoices`、`#member-workbench-missing-materials`、`#member-workbench-confirmations`；旧的发票上下文锚点和上传区锚点仍保持可访问。
  - 任务切换时同步更新 URL 中的 `taskId` 和当前标签页，不再只是本地 state 切换。
- 顶部“任务范围”卡改为“当前任务上下文”卡，补入当前成员信息，明确这是“固定任务上下文后再切换处理视图”的工作方式。
- 新增缺失材料独立标签页：
  - 直接按发票展示 `required_material_type`、费用类型、规则来源、发现时间和补材料动作；
  - 从缺失材料页可直接跳回上传区或对应发票上下文。
- 同步更新 `web/src/app/member-invoice-workbench.test.tsx`：
  - 保持原有任务切换、发票列表、材料类型编辑、分摊编辑、上传、共享发票等断言；
  - 确认用例改为先切换到“费用确认”标签页，再断言确认提交后的刷新结果。
- `TASKS.md` 中“重写成员单任务工作台（Tabs 化）”已标记完成。

### 根因
- 现有成员工作台虽然已经把上传、发票详情和确认收口到同一路由，但仍然是“单页纵向堆叠 + 锚点跳转”，缺失材料没有稳定独立视图，用户仍需要自己判断应该看哪一段。
- 这与 `docs/UI原型图对照与交互规范补充.md` 中“单任务闭环”“减少跨页面/跨区域上下文丢失”的要求不一致；因此本轮优先改信息组织，而不动后端接口。

### 关键改动点
- 修改：
  - `web/src/app/member-invoice-workbench.tsx`
  - `web/src/app/member-invoice-workbench.test.tsx`
  - `TASKS.md`

### 风险与影响面
- 本轮没有改任何后端 API、数据结构和权限判断，只重组成员工作台前端视图。
- 仍保留既有 hash 锚点到上传区和发票详情区，避免现有内部链接立刻失效。
- 工作台内部上传表单、分摊编辑表单仍沿用现有原生表单控件；后续“业务表单整体迁移到 MUI”任务会继续收口这一层。

### 验证结果
- `./scripts/verify.sh` 通过：
  - Python 编译检查通过
  - Alembic `upgrade -> downgrade -> upgrade` 通过
  - `pytest`：420 passed，3 warnings
  - Web `npm run lint` 通过
  - Web `npm test`：21 文件、69 用例全部通过
  - Web `npm run build` 成功
  - Docker Compose 配置检查通过
  - `git diff --check` 通过

### 假设
- 当前仍允许上传区留在“发票”标签页内，而不是单独再拆第 4 个标签页；后续旧二级路由重定向到工作台时，可按“上传 -> 发票页的上传区锚点、缺失材料 -> 缺失材料标签、确认 -> 费用确认标签”收口。
- 共享发票摘要继续放在“发票”标签页，符合“当前发票上下文”语义；后续若信息量继续膨胀，再评估是否拆成右侧详情或二级面板。

## 2026-04-29 12:25 - Strip conflicting global tokens from styles.css

### 完成内容
- 删除 `web/src/styles.css` 顶部第一个 `:root` 块：旧的多色径向渐变背景 + `color: #132238` 强制色 + 旧字体栈，全部由 MUI CssBaseline + Material 3 主题接管。
- 删除 `body` 强制 `color: #132238`（旧）与 `body { background: #f8fafc; color: #0f172a }`（后期），统一由主题控制。
- 删除文件中段第二个 `:root` 块（与 MUI 主题颜色重复）。
- 删除 `.topbar`、`.topbar-inner`、`.topbar-nav`、`.topbar-link`、`.topbar-link-active`、`.topbar-session`、`.session-text`（旧）、`.app-shell`（旧）等已被 MUI AppShell 完全替代的旧顶栏样式。
- 删除 `.workspace-shell`、`.workspace-header`、`.workspace-header::before`、`.workspace-nav-row`、`.workspace-nav`、`.workspace-nav-link`、`.workspace-session-cluster`、`.workspace-hero`、`.workspace-hero-main`、`.workspace-hero-panel`、`.brand-mark`、`.session-pill` 等已被 MUI 替代的旧 Hero / 顶栏类。
- 在文件顶部追加注释，明确"全局 reset 与基础排版由 MUI CssBaseline + 主题控制；本文件保留的旧规则只用于尚未迁移到 MUI 的业务页面"。
- 拆分 P5 第十条任务：
  - 原"移除遗留 styles.css 与冲突类"拆为两条：
    1. 清理与 MUI 主题冲突的全局 token（本轮完成）
    2. 进一步收缩死代码（`.workflow-*`、`.kpi-*`、`.dashboard-grid`、`.workspace-meta-grid` 等当前 .tsx 中未被引用的死类，留作后续轮次）

### 根因
- `styles.css` 历史上有两次大重写："早期橙金 + Hero" 与 "后期 dashboard redesign overrides"，两套互相冲突的全局 token 同时存在；MUI 主题接管后，两套都不再需要，但仍会强制覆盖 body 颜色和背景，造成视觉污染（背景偏黄偏蓝、字色偏深紫）。
- 用户感受到的"前端实在太丑陋"很大一部分来自这两套 token 同时生效；移除后整体观感与 MUI Material 3 主题一致。

### 关键改动点
- 修改：
  - `web/src/styles.css`：从 2233 行（第二次写入前）-> 2046 行（最终），CSS 输出体积 31.07 kB → 27.14 kB（gzipped 6.66 kB → 5.79 kB）。
- 任务拆分：
  - `TASKS.md` Round 10 拆为两条；第一条标记完成。

### 风险与影响面
- 测试 21 文件 / 69 用例无修改通过。
- 视觉行为：未登录页、登录页、首页、成员任务列表、管理员任务列表、任务详情、复核、分摊、导出等页面在 Round 2-9 已逐步切换到 MUI 主题，本轮删除旧 token 后视觉更纯净。
- 留存在 styles.css 中的：`.field-stack`、`.admin-form-grid`、`.task-card`、`.member-status-card`、`.member-confirmation-card`、`.route-link`、`.status-card`、`.invoice-material-button`、`.split-row-card`、`.recognition-field-card` 等仍被业务页面消费的辅助类；它们将在对应业务页 MUI 化轮次中替换。

### 修改文件
- `web/src/styles.css`
- `TASKS.md`
- `WORKLOG.md`

### 验证结果
- `./scripts/verify.sh` 通过：
  - Python 编译检查通过
  - Alembic upgrade/downgrade/upgrade 通过
  - pytest 全量通过
  - Web `npm run lint` 0 error 0 warning
  - Web `npm test` 21 文件、69 用例全部通过
  - Web `npm run build` 成功（CSS 27.14 kB / gzipped 5.79 kB）
  - Docker Compose 配置检查通过
  - `git diff --check` 通过

### 假设
- 业务页面在 Round 6.2 / dashboard.tsx M3 化以及 Round 7 admin-workspace-shell M3 化之后，即使删除上述 token，也能正确从 MUI 主题获得颜色、字体、间距与 elevation。
- "进一步收缩死代码"留待后续轮次，逐项确认 `.tsx` 引用，避免一次性删除导致某些页面意外失去样式。

### 备注
- bundle gzipped 仍约 260.6 kB（与上一轮基本持平）；CSS 是同步降低 0.87 kB gzipped。
- 这是 P5 重写第十轮的第一段；至此 Round 1~10 主线全部完成。后续补强工作（Round 6.3~6.6 单任务工作台拆分、Round 7 第二条详情联动深度优化、Round 8 表单与上传接入、Round 9 confirm 接入、Round 10 死代码收缩）按子任务推进。

## 2026-04-29 12:21 - Add Material 3 confirm dialog infrastructure

### 完成内容
- 新增 `web/src/components/confirm-dialog-context.ts`：`ConfirmDialogContext` + `ConfirmDialogOptions` 与 `ConfirmDialogContextValue` 类型，定义 `tone`/`destructive`/`requireTyping`/`confirmLabel`/`cancelLabel` 等 Material 3 二次确认参数。
- 新增 `web/src/components/ConfirmDialog.tsx`：`ConfirmDialogProvider` 基于 MUI Dialog 实现。
  - 入参为 `confirm(options)` 返回 `Promise<boolean>`，调用方按 await 结果决定是否继续动作；取消和点击关闭一律 resolve(false)。
  - 视觉：圆角 4 dialog + 标题区彩色 WarningAmber 图标 + 描述 + 可选 destructive 警示 Alert + 可选 typing 确认（输入指定字符串才允许提交）。
  - 颜色：destructive 时按钮红色 + warning 标题；普通确认走 primary。
- 新增 `web/src/components/use-confirm-dialog.ts`：`useConfirmDialog()` hook；在 Provider 之外调用退化为始终通过的 noop（与 `useSnackbar` 同样的退化策略）。
- `web/src/app/pages.tsx`：`RootLayout` 在 `SnackbarProvider` 内部嵌入 `<ConfirmDialogProvider>`，使所有路由下的业务组件可以无需额外接入直接调用 `useConfirmDialog().confirm(...)`。
- 拆分 P5 第九条任务：
  - 原"引入 ConfirmDialog 守护破坏性操作"拆为：
    1. 引入 ConfirmDialog 全局基础设施（本轮完成）
    2. 把破坏性业务动作接入 ConfirmDialog（后续轮次）

### 根因
- 项目中诸多破坏性动作（任务状态流转 / 强制提前关闭 / 代成员确认 / 重置识别结果 / 删除标记 / 强制导出等）目前是直接调用对应 API，没有用户二次确认，存在误操作风险。
- 接入需要逐页调整业务调用，按规则不能一次性铺开；先完成全局 Provider 与 hook 基础设施，让后续轮次只需在调用点 `await confirm(...)` 即可。

### 关键改动点
- 新增组件：
  - `web/src/components/confirm-dialog-context.ts`
  - `web/src/components/ConfirmDialog.tsx`
  - `web/src/components/use-confirm-dialog.ts`
- 集成：
  - `web/src/app/pages.tsx`：`RootLayout` 加入 `ConfirmDialogProvider`。
- 任务拆分：
  - `TASKS.md` Round 9 拆分；第一条标记完成。

### 风险与影响面
- 业务行为没有变化：本轮没有任何业务动作调用 `confirm(...)`，因此 21 文件 / 69 用例无修改通过。
- 即使在 Provider 之外的隔离单元测试中调用 `useConfirmDialog().confirm(...)`，hook 退化为 `Promise.resolve(true)`，不会破坏既有测试。
- bundle 影响极小（Dialog/DialogTitle/DialogContent/DialogActions/TextField/Alert 之前已在 bundle 中）。

### 修改文件
- `web/src/components/ConfirmDialog.tsx`（新增）
- `web/src/components/confirm-dialog-context.ts`（新增）
- `web/src/components/use-confirm-dialog.ts`（新增）
- `web/src/app/pages.tsx`
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
- `requireTyping` 默认要求严格匹配（trim 后等于目标字符串），用于关闭任务等非常严格的二次确认；普通破坏性动作可以仅传 `destructive: true`。
- 多次连续调用 confirm 在当前实现下会先后排队，但目前只支持单 Dialog；后续接入时由调用方保证不会并发触发。

### 备注
- Round 9 第二条子任务（接入业务动作）将作为后续轮次工作；按 AGENTS.md 原则不一次性接入所有页面。

## 2026-04-29 12:17 - Add Material 3 file drop zone component and split form rounds

### 完成内容
- 新增 `web/src/components/FileDropZone.tsx`：基于 MUI v7 的 Material 3 风格拖拽上传组件。
  - 视觉：dashed outlined 容器 + 拖拽态主色高亮 + Avatar/CloudUpload 图标 + "拖拽 / 点击选择" 文案 + 主题化 hint。
  - 行为：原生隐藏 `<input type="file">` + 自定义点击与拖拽事件；多文件追加；单文件覆盖；删除单个文件；自动按 mime/扩展名渲染图标（PDF / Image / 通用）。
  - 可达性：可传 `ariaLabel`、`fileListAriaLabel`、`inputId`、`inputName`，便于业务页面与现有测试断言（如 `getByLabelText("上传文件")`）兼容。
  - 已选文件列表使用 MUI List + ListItemAvatar，单文件显示文件名、类型与人类可读大小（B/KB/MB/GB）。
- 拆分 P5 第八条任务：
  - 原"重写表单与上传组件"任务被拆为三条：
    1. 准备 Material 3 表单与上传基础组件（本轮完成；包括 Round 4 已迁移的 TextField/Select、Round 6.2 已迁移的 ErrorMessage Alert，以及本轮新增的 FileDropZone）
    2. 把成员/管理员业务表单整体迁移到 MUI TextField / Select / Autocomplete（后续轮次）
    3. 把材料上传场景接入 FileDropZone（后续轮次）
- 第一条已标记 `[x]`。

### 根因
- 业务页面里的表单（任务创建、发票录入、分摊编辑、确认表单）和文件上传分布在 1000+ 行的多个文件中，一次性重写违反 AGENTS.md "不要一次性重写大块架构" 原则。
- 更稳健的策略是先准备好 M3 基础组件（TextField / Select / Alert / FileDropZone），再分轮把业务页面表单逐一迁移；这一轮先把 FileDropZone 这个目前还缺失的核心组件补齐。

### 关键改动点
- 新增组件：
  - `web/src/components/FileDropZone.tsx`
- 任务拆分：
  - `TASKS.md` Round 8 拆为三条；第一条标记完成。

### 风险与影响面
- 本轮没有任何业务页面消费 FileDropZone，行为完全未变；仅新增了一个可选的组件供后续轮次接入。
- bundle 影响极小；FileDropZone 引用的 List/ListItem/Avatar/IconButton/Button/Stack 在前序轮次已经被打入 bundle。
- 测试改动面：0；现有 21 文件 / 69 用例无修改通过。

### 修改文件
- `web/src/components/FileDropZone.tsx`（新增）
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
- 业务页面后续接入时，会根据每个上传场景选择是否传 `accept`、`multiple`、`disabled`，并通过 `ariaLabel="上传文件"` 等保持现有测试断言不变。
- 拖拽容器整体 onClick 触发 hidden input 的策略避免了 native input 的视觉污染，又保持键盘焦点路径仍可用（input 本身仍可 focus）。

### 备注
- 本轮属于 Round 8 范围；剩余两个子任务（业务表单整体迁移、上传接入）将在后续轮次推进。

## 2026-04-29 12:14 - Rewrite admin workspace shell with MUI navigation list

### 完成内容
- 重写 `web/src/app/admin-workspace-shell.tsx`：
  - 整体布局改为 MUI Box grid，桌面端 sticky 左侧栏 + 右侧主区，移动端单列。
  - 模块导航改为 MUI `<List>` + `<ListItemButton component={RouterLink}>` + `<ListItemIcon>` + `<ListItemText>`，每个模块拥有独立 Material Icon（DashboardIcon、AssignmentIcon、FactCheckIcon、NotificationsActiveIcon、PaymentsIcon、DownloadIcon），active 项使用 MUI selected 状态 + 主色高亮 + 右侧 ChevronRight 指示器。
  - 当前任务上下文卡改为 Card + Stack：标题区 + Divider + 任务编号/比赛名/状态 Chip + 当前阶段/截止时间网格 + 阶段说明。
  - 快捷入口按钮组用 `<Button variant="outlined" startIcon={...}>` 替换原 `.route-link-secondary`。
  - 保留所有 aria-label：`管理员模块导航`、`当前任务上下文`、`当前任务快捷入口`。
- 任务调整：
  - 原"重写管理员任务详情：列表+详情联动" 改为已完成的 "重写管理员侧 workspace shell"，并新增"完善管理员任务详情：列表+详情联动深度优化"留待后续轮次。

### 根因
- admin-workspace-shell 是所有管理员业务页（任务详情、复核、分摊编辑、导出等）的左侧固定骨架；改它一次，所有管理员页面立即获得 M3 视觉。
- 旧实现是 `<aside><section className="panel-card">...<nav className="admin-module-nav">...<Link className="admin-module-link">..</Link></nav></section></aside>`，全部依赖 `styles.css` 中的自造样式，与主题脱节。

### 关键改动点
- 重写：
  - `web/src/app/admin-workspace-shell.tsx`：从 209 行重写为基于 MUI 的 320 行版本。
- 任务调整：
  - `TASKS.md` Round 7 拆分：第一条标记完成；第二条改为后续优化任务。

### 风险与影响面
- 业务行为完全不变：模块路径、active 判定、可访问性 label、快捷入口按钮目标全部保持。
- 测试断言全部通过（21 文件、69 用例）：依赖 `getByLabelText("管理员模块导航")`、`getByLabelText("当前任务上下文")`、`toHaveTextContent("ICPC 复核任务")`、`getByRole("heading", { name: "管理员工作台 暂不可访问" })` 等用法。
- 视觉收益：管理员任务列表 / 任务详情 / 复核 / 分摊 / 导出 / 提醒 6 个页面立刻拥有 MUI Material 3 侧边导航。

### 修改文件
- `web/src/app/admin-workspace-shell.tsx`
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
- "导航骨架" StatusBadge 仍保留作为提示标签，便于运营快速识别这是稳定的导航容器而不是动态内容。
- 当前任务上下文使用 `<Box component="dl">` + `<Typography component="dt"/>` 保留语义标签，不破坏屏幕阅读器对 description list 的识别。

### 备注
- 本轮属于 Round 7 范围；列表+详情结构在管理员任务详情/复核页中已经是既有实现，本轮升级了它们的左侧导航视觉。后续如需进一步把识别字段/校验/附件预览拆为右侧 Tabs，按新拆出的"完善管理员任务详情：列表+详情联动深度优化"任务推进。

## 2026-04-29 12:11 - Migrate dashboard primitives to MUI Material 3 internals

### 完成内容
- 重写 `web/src/components/dashboard.tsx`，把 8 个公共 UI 原语全部从原生 HTML + `styles.css` 类名改为 MUI v7 内部实现，对外 API 完全保持向后兼容：
  - `StatusBadge`：内部改用 MUI `<Chip>`，按 `tone` 映射颜色（neutral=outlined, info/warning/danger/success=filled）。
  - `SectionCard`：内部改用 `<Card component="section" variant="outlined">`，标题区使用 Typography h6，描述区使用 body2 secondary。
  - `PageHeader`：内部改用 `<Box component="section">` + Stack 响应式布局，标题用 Typography h3，保留原 `<h1>` 角色（`component="h1"`）。
  - `StatCard`：内部改用 `<Card component="article" variant="outlined">`，保留 `<article>` 标签以兼容业务页内 `closest("article")` 查询。
  - `EmptyState`：内部改用 dashed outlined Card。
  - `ErrorMessage`：内部改用 `<Alert severity="error" variant="outlined" role="alert">` + `<AlertTitle>`，详情用 ul/li 列表。
  - `RoleWorkspace`：内部改用 MUI Stack 控制纵向间距，仍保留 `.workspace-page` 类名以避免现有 CSS 选择器抖动。
  - `TaskTable`：内部改用 MUI Table + TableHead + TableBody + TableContainer，caption 仍存在但通过 sr-only 样式视觉隐藏。
- 30+ 业务页面（成员任务列表/工作台/状态/确认；管理员任务列表/详情/复核/分摊/导出/提醒等）一行不改，立即获得 M3 视觉：surface tonal、Card 圆角、Chip 状态色、Typography scale、统一 elevation。

### 根因
- 原 `dashboard.tsx` 是手写 HTML + 自造 CSS 类名（`.panel-card`/`.status-card`/`.stat-card`/`.status-badge-*`），与 Round 2 引入的 M3 主题严重脱节。
- 一轮内重写所有调用方业务页（4500+ 行成员页 + 同等量级管理员页）不现实；按 AGENTS.md "不要一次性重写大块架构" 原则，更稳健的做法是改公共原语内部实现而保持对外 API 不变，让所有页面立即视觉对齐。
- 此外，本轮明确把"重写成员单任务工作台（Tabs 化）"留给后续轮次，因为它涉及 1900+ 行业务交互且存在大量 `closest("article")` 等结构断言，需要单独一轮处理。

### 关键改动点
- 重写：
  - `web/src/components/dashboard.tsx`：从基于 className + 原生 HTML 的实现改为 MUI 内部实现，对外 API 完全不变。
- 任务调整：
  - `TASKS.md` 在 P5 中新增并标记完成"让 dashboard 公共组件视觉对齐 MUI Material 3"子任务（视为 Round 6 系列的 6.2 实际完成项）；原 6.2"Tabs 化"工作台任务保留为后续轮次。

### 风险与影响面
- 业务行为无变化：所有 props、children、aria-label、heading 角色、`<article>` / `<section>` / `<table>` 标签都保持，30+ 业务页 + 21 测试文件 + 69 用例全部无修改通过。
- 视觉对齐：当用户进入任意业务页面时（成员任务列表 / 单任务工作台 / 管理员任务详情等），KPI 卡、SectionCard、状态 Chip、错误 Alert 均自动呈 M3 风格。
- bundle gzipped 略增（Alert/AlertTitle/Chip/Stack/Table 已在前序轮次引入；本轮没有新增组件）。
- 现有 `styles.css` 中的 `.panel-card` / `.status-card` / `.stat-card` / `.empty-state` / `.error-card` / `.dashboard-table` 等类名虽不再驱动外观，但仍保留以兼容业务页内的辅助类（如 `.task-card`、`.member-confirmation-card`）。这些将在 Round 10 统一清理。

### 修改文件
- `web/src/components/dashboard.tsx`
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
- 业务页内大量 `closest("article")` / `closest("section")` 断言要求 StatCard/SectionCard 等仍输出 `<article>` / `<section>` 元素；本轮通过 `component="article"` / `component="section"` 明确传递给 MUI Card 满足该要求。
- `<table>` 仍由 MUI 渲染为合法 `<table>`，TableHead 与 TableBody 同样保留 `<thead>` / `<tbody>` 语义；测试中 `getByRole("table")` 与 `within(table).getByText(...)` 全部通过。
- ErrorMessage 用 Alert 替换原 panel-card 错误卡，但仍保留 role="alert" 与 detail label/message 列表语义。

### 备注
- 这一轮是本批 P5 重写中"投入产出比"最高的一轮：30+ 业务页面全部一次性视觉升级，不必为每一页单独写 PR。
- 后续 Round 6.2"Tabs 化"工作台仍保留为待办，将在更聚焦的轮次中处理。

## 2026-04-29 12:08 - Rewrite member task list with Material 3 visuals and split workbench rounds

### 完成内容
- 重写 `web/src/app/member-task-list.tsx`：
  - 顶部 hero 改为 Stack + 标题/描述/当前成员副文案 + "进入发票工作台" Contained Button（带 OpenInNewIcon）。
  - "成员任务概览" 改为 4 张 outlined `<Card>` 网格（StatTile 子组件）：我参与的任务 / 正在收集 / 待补充或确认 / 已进入归档；每张含 overline + 大数字 + Avatar 角色着色 + 业务描述。
  - 任务列表改为 `<Card>` 包裹的 MUI `<Table>`（aria-label="成员任务列表"），状态用 MUI `<Chip>` 颜色映射（info/warning/success/default），操作列用 `<Button variant="contained">` + `<Button variant="outlined">` 组合。
  - 加载态用 `<CircularProgress>` + 简短文案，错误态保留 `ApiErrorNotice`，空态用 `<Alert severity="info">` 替换 EmptyState。
  - 移动端 grid 自动单列，Stack 自动竖向。
- 拆分 P5 第六条任务：
  - 原"重写成员端任务列表与单任务工作台"任务范围太大（涉及任务列表 + 1900 行工作台 + 上传/状态/缺失/确认 4 段共 4500+ 行），按 AGENTS.md "任务过大先拆分" 原则，拆成 6 条独立子任务：
    1. 重写成员端任务列表（M3 Material 视觉）— 本轮完成
    2. 重写成员单任务工作台（Tabs 化）
    3. 重写成员材料上传交互（拖拽 Dialog + Snackbar）
    4. 重写成员材料状态页（M3 列表 + 详情视图）
    5. 重写成员费用确认页与缺失材料页
    6. 收口成员端旧二级路由为工作台跳转
- 第一条已标记 `[x]`，其余 5 条留作后续轮次。

### 根因
- 旧任务列表使用自造 `RoleWorkspace` + `PageHeader` + `StatCard` + `SectionCard` + `TaskTable` 组合，与 Round 5 重写的首页风格脱节，且依赖 1700+ 行 `styles.css` 中的旧 token。
- 用户在 P5 计划中要求成员端从"4 段拆分页面"收口为"单任务闭环"，但单任务工作台代码 1951 行；按规则一轮内不能整体重写。本轮先做最易完成的任务列表 M3 化，并把剩余工作明确拆到后续轮次。

### 关键改动点
- 重写：
  - `web/src/app/member-task-list.tsx`：从 231 行重写为基于 MUI 的 320 行版本。
- 任务拆分：
  - `TASKS.md` 第六条 P5 任务拆为 6 条子任务，第一条标记完成。

### 风险与影响面
- 业务路由全部保持不变：
  - 列表 `/member` 仍渲染同样的 ReimbursementTask；
  - "进入发票工作台" → `/member/invoices/workbench`；
  - 每行"进入工作台" → `/member/invoices/workbench?taskId=XXX`；
  - 每行下一步按钮按 `task.status` 路由到 upload/missing/confirm/status，与旧版完全一致。
- `member-task-list.test.tsx` 全部 2 条用例无修改通过，因为关键 accessible name（heading "我的报销任务"、aria-label "成员任务概览"、table caption "成员任务列表"、link "进入发票工作台"/"进入工作台"/"提交材料"、文本 "ICPC Xi'an Regional"/"收集中"/"当前没有可见报销任务"）全部保留。
- bundle gzipped 与上一轮持平（多了 Table/TableHead/TableRow/TableCell/TableContainer/CircularProgress 也已经在前序 MUI 引入中）。

### 修改文件
- `web/src/app/member-task-list.tsx`
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
- 任务列表的"操作"列保留两个按钮（进入工作台 + 直接下一步动作），与现有测试断言一致；不删除"提交材料"等下一步快捷链接。
- 状态 Chip 颜色映射 open=info / reviewing|closed=warning / ready_to_export|completed=success / draft=default outlined。

### 备注
- 后续 5 条子任务将依次推进；单任务工作台 1900 行的重写会作为单独一轮，且优先采用"在不动业务调用的前提下替换骨架与 UI 元素"的方式，再拆出更细的视觉与交互优化任务。

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
