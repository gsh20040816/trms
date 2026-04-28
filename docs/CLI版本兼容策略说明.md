# CLI 版本兼容策略说明

更新时间：2026-04-28

## 当前目标

第一阶段 CLI 已经承担登录、任务查询、材料上传、状态查询、分摊提交和费用确认等入口。随着命令和 JSON 输出逐步增多，后端需要能够区分：

1. 当前请求是否来自 CLI；
2. 当前 CLI 是否理解服务端要求的最小协议；
3. JSON 输出发生破坏性变更时，脚本调用方如何识别不兼容。

本策略只解决第一阶段的最小兼容协商，不引入独立的 CLI 发布服务或复杂版本矩阵。

## 请求协商头

当前 `trms-cli` 对每个 HTTP 请求都附带以下请求头：

| Header | 当前值 | 作用 |
|---|---|---|
| `X-TRMS-Client` | `cli` | 明确该请求来自 CLI，而不是 Web、测试脚本或未来其他渠道 |
| `X-TRMS-CLI-Version` | `1` | 表示当前 CLI/服务端协商使用的协议版本 |
| `X-TRMS-CLI-Capabilities` | `json-output-v1,material-submit-v1,task-list-v1,member-status-v1,missing-materials-v1,split-submit-v1,expense-confirmation-v1` | 声明当前 CLI 已实现的关键能力，用于后续按能力门禁排查 |

这里的 `X-TRMS-CLI-Version` 是协议版本，不等同于 Python 包版本或未来发行版本号。当前仓库尚无独立 CLI 发版流程，因此先用整数协议版本表达“是否能和当前服务端对话”。

## 服务端行为

服务端当前采用最小门禁：

1. 只有当请求显式声明 `X-TRMS-Client: cli` 时，才进入 CLI 兼容检查。
2. 当 `X-TRMS-CLI-Version` 缺失、不可解析，或小于当前最小支持版本 `1` 时，服务端返回 `426 Upgrade Required`。
3. 错误响应至少包含：
   - `code=cli_version_too_old`
   - `detail`
   - `minimum_supported_cli_version`
   - `received_cli_version`
4. 响应头 `X-TRMS-Minimum-CLI-Version` 复述当前最小支持版本，便于脚本或诊断工具读取。

当前实现是“声明式门禁”：

1. 新 CLI 会稳定发送上述请求头，因此可以得到显式错误。
2. 更早、完全不发送这些请求头的历史客户端，服务端暂时无法仅凭通用 REST 路径把它们和非 CLI 调用完全区分开来。
3. 若后续需要彻底拒绝无版本头的旧 CLI，应优先为 CLI 收敛独立入口或更明确的认证上下文，而不是在通用任务接口里猜测调用方身份。

## JSON 输出兼容规则

`--json` 输出是 CLI 对脚本调用方的稳定契约，文本输出不是。

当前规则如下：

1. 当前 JSON schema version 为 `trms-cli.v1`。
2. 仅新增可选字段、补充新命令且不改变已有字段语义时，保持 `trms-cli.v1` 不变。
3. 出现以下任一破坏性变更时，必须升级 `CLI_JSON_SCHEMA_VERSION`，例如 `trms-cli.v2`：
   - 删除字段；
   - 重命名字段；
   - 修改字段类型；
   - 修改已有字段语义，导致旧脚本按旧含义解析会出错；
   - 把原本可选字段改成调用方必须处理的新强约束。
4. 当 JSON schema 发生破坏性升级时，应同步：
   - 更新 CLI 请求头里的能力标识；
   - 在 `WORKLOG.md` 记录升级原因和影响面；
   - 由服务端在需要新能力的接口上提高最小 CLI 协议版本或增加能力门禁。

## 后续演进边界

如后续第一阶段继续扩展 CLI，优先遵循以下顺序：

1. 先判断新增能力是否只涉及新增命令或新增可选字段。
2. 只有在现有协议无法表达时，才提升 `X-TRMS-CLI-Version`。
3. 只有在现有 JSON 契约被破坏时，才提升 `CLI_JSON_SCHEMA_VERSION`。
4. 不把“命令更多了”误当作“必须升级协议版本”。
