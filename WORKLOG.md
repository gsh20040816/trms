# WORKLOG

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
