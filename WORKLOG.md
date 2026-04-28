# WORKLOG

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
