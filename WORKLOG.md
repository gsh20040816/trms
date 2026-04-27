# WORKLOG

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
