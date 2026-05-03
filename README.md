# TRMS

同济大学 ACM 竞赛报销收集系统。

当前开发切片已具备后端、CLI 与 Web 前端的第一阶段主链路骨架，并提供基础用户名密码注册登录能力。

生产部署基线已补齐到 `deploy/` 目录，包含 `Docker Compose`、后端/前端镜像构建文件、反向代理示例配置和 `.env.example`。当前 Compose 基线默认假设由宿主机上的 Caddy、Nginx 或其他外部反向代理统一接入；仓库同时提供 `./scripts/trms-prod.sh` 作为生产环境统一启停入口。具体启动顺序、迁移命令、健康检查、日志位置和首个管理员初始化步骤见 [docs/生产部署清单与Docker Compose基线.md](docs/生产部署清单与Docker%20Compose基线.md)。
数据库、对象存储、原始材料的备份与恢复策略建议见 [docs/备份与恢复策略说明.md](docs/%E5%A4%87%E4%BB%BD%E4%B8%8E%E6%81%A2%E5%A4%8D%E7%AD%96%E7%95%A5%E8%AF%B4%E6%98%8E.md)；当前仓库仅完成策略说明，恢复演练仍是后续独立任务。

## 统一配置文件

仓库统一使用根目录 `.env` 作为运行配置文件：

- 部署 / 生产基线模板：根目录 `.env.example`
- 本地开发模板：根目录 `.env.development.example`

```bash
cp .env.development.example .env
```

配置生效边界如下：

- `uv run python -m trms_backend`、`uv run python -m trms_backend worker` 会默认读取根目录 `.env`；
- `cd web && npm run dev`、`npm run build` 会从仓库根目录而不是 `web/` 子目录读取 `.env` 中的 `TRMS_WEB_*` 与 `VITE_*` 变量；
- `docker compose --env-file .env -f deploy/docker-compose.yml ...` 使用同一份根目录 `.env`；
- `deploy/docker-compose.yml` 中的 `migrate`、`api`、`worker` 也会默认通过 `env_file` 继承这同一份根目录 `.env`；若需要覆盖，必须同时覆盖 Compose CLI 的 `--env-file` 与 `TRMS_RUNTIME_ENV_FILE`；
- 若 shell 中显式传入同名环境变量，则显式环境变量优先于 `.env`。

生产环境若沿用仓库基线，推荐直接使用：

```bash
./scripts/trms-prod.sh build
./scripts/trms-prod.sh deploy
./scripts/trms-prod.sh start
./scripts/trms-prod.sh status
./scripts/trms-prod.sh stop
```

说明：

- `build` 只重建 `migrate`、`api`、`worker`、`web` 镜像，不启动容器。
- `deploy` 会先执行 `build`，再执行当前 `start` 流程，适合服务器上 `git pull` 之后更新代码。
- `start` 不会主动重建镜像；如果源码、`Dockerfile` 或前端构建产物依赖发生变化，仅执行 `start` 可能继续复用旧镜像。

## 本地验证

```bash
uv sync
uv run pytest
uv run python -m trms_backend --reload
```

## 第一阶段本地运行闭环

当前仓库适合验证“本地 API + 本地/假外部依赖 + Web 前端 + 占位 CLI”的第一阶段闭环，不应把它理解为真实 Telegram、真实邮件、真实财务系统或完整生产凭据流程已经联通。

推荐的本地最小启动顺序：

```bash
cp .env.development.example .env
uv sync
uv run alembic upgrade head
uv run python -m trms_backend --reload
```

如果要验证独立 worker 模式，而不是请求内同步处理异步任务，再开一个终端运行：

```bash
TRMS_ASYNC_JOB_MODE=worker uv run python -m trms_backend worker
```

如果要联调 Web 前端：

```bash
cd web
npm install
npm run dev
```

本地回归验证统一使用：

```bash
./scripts/verify.sh
```

该脚本当前会执行 Python 编译检查、Alembic `upgrade -> downgrade -> upgrade` 验证、`pytest`、Web `lint/test/build`、Docker Compose 配置检查和 `git diff --check`。

## CLI 当前状态

第一阶段 CLI 目前已实现这些命令：

- `login`
- `health`
- `tasks`
- `task`
- `submit`
- `status`
- `missing-materials`
- `split`
- `confirm-expense`

当前仓库还没有安装型 `trms-cli` console script，实际调用方式是：

```bash
uv run python -m trms_cli.cli --help
```

CLI 与 Telegram 现在共用一套“任务列表 / 当前任务切换 / 文件提交”语义，但认证方式不同：

- CLI 通过 bearer token 会话访问 API；
- Telegram 通过绑定后的账号身份访问同一套任务与上传主链路。

CLI `login` 目前仍只是“本地 token 会话保存占位”，不是完整 OAuth 登录闭环：

- 它会读取预先提供的 `TRMS_CLI_ACCESS_TOKEN` 和 `TRMS_CLI_REFRESH_TOKEN`，并安全写入本地 session 文件；
- 默认 session 文件路径是 `~/.config/trms/session.json`，也可用 `TRMS_CLI_CONFIG_DIR` 覆盖；
- 目前尚未对接 CLI 专用 token 签发 / 刷新流程，也不等同于 Web 登录已经自动可复用到 CLI。

因此，README 当前只把 CLI 视为“已有命令和本地会话边界的开发入口”，不把它表述为已具备完整终端登录发布流程。

默认使用本地 SQLite 文件 `trms.db`。如需连接 PostgreSQL，可设置 `DATABASE_URL`。

```bash
DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/trms uv run python -m trms_backend --reload
```

数据库迁移边界：

- 仓库已引入 Alembic 基线迁移，迁移入口为 `uv run alembic upgrade head`。
- 开发和测试环境仍保留 `create_all` 自举能力，便于临时 SQLite 和 pytest 临时库快速启动。
- `TRMS_ENV=production` 时，API 和 worker 启动不会再自动建表或自动演进 schema；必须先执行迁移，否则启动会显式失败。
- 需要回滚时使用 `uv run alembic downgrade base` 或目标 revision；共享环境执行前应先备份数据库。
- 旧的本地 `trms.db` 如果仍是历史 `create_all` 生成且不需要保留数据，优先删除后重新执行 `uv run alembic upgrade head`；若必须保留数据，应先人工确认 schema 与当前基线一致，再决定是否 `alembic stamp head`，不要在未核对结构时直接盖章。

后端运行配置已统一收敛到环境变量：

- `TRMS_ENV`：`development`、`test` 或 `production`，默认 `development`
- `DATABASE_URL`
- `TRMS_STORAGE_BACKEND`
- `MATERIAL_STORAGE_DIR`：仅 `TRMS_STORAGE_BACKEND=local` 时使用
- `TRMS_STORAGE_S3_ENDPOINT`
- `TRMS_STORAGE_S3_BUCKET`
- `TRMS_STORAGE_S3_ACCESS_KEY_ID`
- `TRMS_STORAGE_S3_SECRET_ACCESS_KEY`
- `TRMS_STORAGE_S3_REGION`
- `TRMS_STORAGE_S3_KEY_PREFIX`
- `TRMS_CORS_ALLOWED_ORIGINS`：逗号分隔的 `http(s)://host[:port]` 列表
- `TRMS_PUBLIC_API_BASE_URL`
- `TRMS_PUBLIC_WEB_BASE_URL`
- `TZ`：系统时区，默认 `UTC`；建议使用 IANA 时区名，例如 `Asia/Shanghai`
- `TRMS_API_HOST`
- `TRMS_API_PORT`
- `TRMS_ASYNC_JOB_MODE`
- `TRMS_ASYNC_JOB_POLL_INTERVAL_SECONDS`
- `TRMS_ASYNC_JOB_WORKER_CONCURRENCY`
- `TRMS_AUTH_ALLOW_ADMIN_SELF_REGISTER`
- `TRMS_AUTH_BOOTSTRAP_ADMIN_TOKEN`
- `TRMS_AUTH_TELEGRAM_INBOUND_TOKEN`
- `TRMS_AUTH_EMAIL_INBOUND_TOKEN`
- `TRMS_TELEGRAM_BOT_TOKEN`
- `TRMS_TELEGRAM_WEBHOOK_SECRET`
- `TRMS_SMTP_HOST`
- `TRMS_SMTP_PORT`
- `TRMS_SMTP_USERNAME`
- `TRMS_SMTP_PASSWORD`
- `TRMS_SMTP_FROM_ADDRESS`
- `TRMS_SMTP_STARTTLS`
- `TRMS_SMTP_USE_SSL`
- `TRMS_SMTP_TIMEOUT_SECONDS`
- `TRMS_IMAP_HOST`
- `TRMS_IMAP_PORT`
- `TRMS_IMAP_USERNAME`
- `TRMS_IMAP_PASSWORD`
- `TRMS_IMAP_MAILBOX`
- `TRMS_IMAP_POLL_INTERVAL_SECONDS`
- `TRMS_IMAP_USE_SSL`
- `TRMS_IMAP_STARTTLS`
- `TRMS_TEXT_LLM_API_KEY`
- `TRMS_TEXT_LLM_BASE_URL`
- `TRMS_TEXT_LLM_MODEL`
- `TRMS_TEXT_LLM_TIMEOUT_SECONDS`
- `TRMS_TEXT_LLM_MAX_RETRIES`
- `TRMS_VLM_API_KEY`
- `TRMS_VLM_BASE_URL`
- `TRMS_VLM_MODEL`
- `TRMS_VLM_TIMEOUT_SECONDS`
- `TRMS_VLM_MAX_RETRIES`
- 兼容旧配置：
  - `TRMS_LLM_API_KEY`
  - `TRMS_LLM_BASE_URL`
  - `TRMS_LLM_MODEL`
  - `TRMS_LLM_TIMEOUT_SECONDS`
  - `TRMS_LLM_MAX_RETRIES`

开发环境默认值：

- `DATABASE_URL=sqlite:///./trms.db`
- `TRMS_STORAGE_BACKEND=local`
- `MATERIAL_STORAGE_DIR=./data/materials`
- `TRMS_CORS_ALLOWED_ORIGINS=http://127.0.0.1:5173,http://localhost:5173`
- `TRMS_PUBLIC_API_BASE_URL=http://127.0.0.1:9876/api`
- `TRMS_API_HOST=127.0.0.1`
- `TRMS_API_PORT=9876`

本地跨端口联调示例：

```bash
TRMS_API_HOST=127.0.0.1 \
TRMS_API_PORT=8100 \
TRMS_PUBLIC_API_BASE_URL=http://127.0.0.1:8100/api \
TRMS_CORS_ALLOWED_ORIGINS=http://127.0.0.1:5173,http://localhost:5173 \
uv run python -m trms_backend --reload
```

文件存储边界：

- `TRMS_STORAGE_BACKEND` 支持 `local` 和 `s3`。
- 开发和测试环境默认使用 `local`，并从 `MATERIAL_STORAGE_DIR` 读取本地根目录。
- 单个上传材料默认大小上限为 64MiB；后端上传校验、CLI 本地预检和前端上传预检共用同一阈值。
- `TRMS_ENV=production` 时必须显式配置 `TRMS_STORAGE_BACKEND`；当前支持 `local` 和 `s3`，其中 `local` 适合单机部署，`s3` 更适合容器化和多实例部署。
- 当前 `deploy/docker-compose.yml` 中 `migrate`、`api`、`worker` 会统一通过 `env_file` 继承运行环境文件，并在 `TRMS_STORAGE_BACKEND=local` 时把宿主机 `MATERIAL_STORAGE_DIR` bind mount 到容器内同一路径，例如 `MATERIAL_STORAGE_DIR=/srv/trms/materials` 时，宿主机 `/srv/trms/materials` 会成为原始材料与导出产物的持久化目录。
- `TRMS_STORAGE_S3_ENDPOINT`、`TRMS_STORAGE_S3_BUCKET`、`TRMS_STORAGE_S3_ACCESS_KEY_ID`、`TRMS_STORAGE_S3_SECRET_ACCESS_KEY` 为 `s3` 后端必填项；`TRMS_STORAGE_S3_REGION` 和 `TRMS_STORAGE_S3_KEY_PREFIX` 为可选项。
- 对象存储凭据只允许通过后端环境变量或密钥管理注入，不入库、不返回前端，也不应写入日志。
- 当前导出产物下载继续走后端接口读取存储内容，不暴露长期公开 URL；更细粒度的 bearer 下载鉴权仍待后续权限任务收口。
- 当前仓库已补入 `psycopg[binary]` 依赖，`postgresql+psycopg://...` 连接串可直接用于 Compose 基线和共享环境。

邮箱验证码发送边界：

- 成员自助绑定邮箱时，后端会通过 SMTP 发送 6 位验证码邮件；当前验证码默认有效期为 10 分钟。
- 只有配置了 `TRMS_SMTP_HOST`、`TRMS_SMTP_PORT` 和 `TRMS_SMTP_FROM_ADDRESS` 后，`/api/email-bindings/verification-code` 才可用。
- `TRMS_SMTP_USERNAME` 与 `TRMS_SMTP_PASSWORD` 必须成对出现；若留空，则按“无需 SMTP 登录”的本地中继模式发送。
- `TRMS_SMTP_STARTTLS` 默认 `true`，`TRMS_SMTP_USE_SSL` 默认 `false`；若使用 SMTPS 465 端口，可设置 `TRMS_SMTP_USE_SSL=true` 并按服务端要求关闭 `STARTTLS`。
- SMTP 凭据只允许通过后端环境变量注入，不入库、不返回前端，也不应写入日志。

IMAP 收件轮询边界：

- 当前 worker 已支持可选的 IMAP 邮箱轮询；仅当配置了 `TRMS_IMAP_HOST`、`TRMS_IMAP_PORT`、`TRMS_IMAP_USERNAME` 和 `TRMS_IMAP_PASSWORD` 后才会启用。
- `TRMS_IMAP_MAILBOX` 默认 `INBOX`；`TRMS_IMAP_POLL_INTERVAL_SECONDS` 默认 `30`；`TRMS_IMAP_USE_SSL` 默认 `true`，`TRMS_IMAP_STARTTLS` 默认 `false`。
- worker 会按邮箱 `UID` 去重记录已轮询邮件，并把原始 `.eml` 存入统一存储后端的 `_email_inbox/` 命名空间。
- 发件人邮箱未绑定成员身份时，邮件会被显式记录为 `ignored_unbound_sender`，不会进入成员主链路。
- 发件人已绑定但主题任务标识不存在或邮件格式不满足规范时，邮件会记录为稳定忽略原因，而不是静默丢弃。
- 对于 `ready_for_import` 的收件记录，worker 会继续提取邮件附件并复用统一材料上传链路写入目标任务。
- 若已配置 SMTP，系统会自动回复“已收到 / 部分成功 / 失败原因”这三类处理结果摘要。

生产环境不会静默回退到开发默认值；当 `TRMS_ENV=production` 时，以上变量都必须显式提供，否则服务会在启动时直接报错。启动参数 `--host`、`--port` 可覆盖对应环境变量，例如：

```bash
TRMS_ENV=production \
DATABASE_URL=postgresql+psycopg://user:password@db:5432/trms \
TRMS_STORAGE_BACKEND=local \
MATERIAL_STORAGE_DIR=/srv/trms/materials \
TRMS_CORS_ALLOWED_ORIGINS=https://trms.example.edu \
TRMS_PUBLIC_API_BASE_URL=https://trms.example.edu/api \
TRMS_API_HOST=0.0.0.0 \
TRMS_API_PORT=9876 \
uv run alembic upgrade head && \
uv run python -m trms_backend --host 0.0.0.0 --port 9876
```

生产环境若改用 S3 兼容对象存储，则需要：

```bash
TRMS_ENV=production \
DATABASE_URL=postgresql+psycopg://user:password@db:5432/trms \
TRMS_STORAGE_BACKEND=s3 \
TRMS_STORAGE_S3_ENDPOINT=https://minio.example.edu \
TRMS_STORAGE_S3_BUCKET=trms-prod \
TRMS_STORAGE_S3_ACCESS_KEY_ID=replace-me \
TRMS_STORAGE_S3_SECRET_ACCESS_KEY=replace-me \
TRMS_STORAGE_S3_REGION=cn-east-1 \
TRMS_STORAGE_S3_KEY_PREFIX=prod \
TRMS_CORS_ALLOWED_ORIGINS=https://trms.example.edu \
TRMS_PUBLIC_API_BASE_URL=https://trms.example.edu/api \
TRMS_API_HOST=0.0.0.0 \
TRMS_API_PORT=9876 \
uv run alembic upgrade head && \
uv run python -m trms_backend --host 0.0.0.0 --port 9876
```

OpenAI 兼容文本 LLM / VLM Provider 配置边界：

- 当前仓库区分两类 provider：
  - `TRMS_TEXT_LLM_*`：用于纯文本材料和可抽取文本的 PDF
  - `TRMS_VLM_*`：用于扫描 PDF、图片和截图
- 兼容旧单一路径配置：
  - 若未配置 `TRMS_TEXT_LLM_*` 或 `TRMS_VLM_*`，系统会分别回退到旧的 `TRMS_LLM_*`
  - 这样旧部署不需要立刻改环境变量，仍保持“文本 PDF + 扫描 PDF/图片共用一套 provider”的旧行为
- 一旦开始配置某一类 provider 的 `*_BASE_URL` / `*_MODEL` 等字段，该类 provider 的 `*_API_KEY` 和 `*_MODEL` 必填；缺失时服务会在启动阶段直接报错。
- `TRMS_TEXT_LLM_BASE_URL` 与 `TRMS_VLM_BASE_URL` 默认都是 `https://api.openai.com/v1`，可替换为任何兼容接口地址；尾部 `/` 会被规范化去掉。
- `TRMS_TEXT_LLM_TIMEOUT_SECONDS`、`TRMS_VLM_TIMEOUT_SECONDS` 默认 `30`，`TRMS_TEXT_LLM_MAX_RETRIES`、`TRMS_VLM_MAX_RETRIES` 默认 `2`。
- 当前仓库已接入“文本 PDF 提取 + PDF 页面渲染成图片 + 图片直送 OpenAI 兼容 VLM -> 结构化识别”的执行链；文本 PDF 会优先走本地可抽取文本，扫描 PDF 会先渲染为图片再交给多模态模型，图片会以 base64 data URL 形式直送多模态模型；若文本 PDF 的首次 text LLM 识别失败，系统会再把该 PDF 渲染为图片并回退走一次 VLM。
- 系统管理员现在可以在系统管理页保存识别 provider 的系统级覆盖项；运行时优先读取系统配置，缺失字段再回退到环境变量，不回显 API key 原文。
- 未配置对应 provider 时，识别会按材料类型分别显式停在：
  - `text_llm_provider_not_configured`
  - `vlm_provider_not_configured`
  而不是伪造识别成功。

Telegram Bot 与入站可信边界：

- `PUT /api/telegram-bindings/*` 与 Telegram 绑定查询接口现在都要求 bearer 身份，且仅 `admin` / `system_admin` 可管理。
- 成员现在可在 Telegram 中发送 `/bind` 获取一次性网页绑定链接；登录 Web 后确认，即可把当前 Telegram 账号绑定到当前成员身份。
- 真实 Telegram bot webhook 入口为 `/api/telegram/bot/webhook`；配置 `TRMS_TELEGRAM_BOT_TOKEN` 后可处理 `/bind`、`/tasks`、`/task <submission_key>` 和直接发送文件上传。
- 任务对外统一暴露 `submission_key` 作为跨 Telegram / CLI / 邮件的稳定任务提交标识；旧字段名 `email_submission_key` 继续兼容已有 API / 数据。
- 只有在后端配置了 `TRMS_AUTH_TELEGRAM_INBOUND_TOKEN`，且请求头 `X-TRMS-Telegram-Inbound-Token` 与之匹配时，`/api/telegram/materials` 才会把表单中的 `telegram_user_id` 当作可信身份来源。
- 未配置该 token，或请求未携带该 token 时，Telegram 材料仍会被接收，但只进入待归属流程，不会直接归档到成员主链路。
- 该 token 只允许保留在后端环境变量或渠道入站器密钥管理中，不入库、不返回前端，也不应写入日志。

格式化邮件入站可信边界：

- `/api/email/materials` 不再信任匿名调用方表单里的 `resolved_member_id`。
- 只有在后端配置了 `TRMS_AUTH_EMAIL_INBOUND_TOKEN`，且请求头 `X-TRMS-Email-Inbound-Token` 与之匹配时，邮件入站器提供的 `resolved_member_id` 才会被当作可信成员身份直接写入成员主链路。
- 未配置该 token，或请求未携带该 token 时，格式合法的邮件材料仍会被接收，但即使表单里带了 `resolved_member_id`，也只会进入待归属流程。
- 该 token 只允许保留在后端环境变量或渠道入站器密钥管理中，不入库、不返回前端，也不应写入日志。

异步任务运行模式边界：

- `TRMS_ASYNC_JOB_MODE` 支持 `in_process` 和 `worker` 两种模式。
- 开发和测试环境默认使用 `in_process`，便于当前同步接口和本地排障。
- `TRMS_ENV=production` 时默认切换为 `worker`，并拒绝 `TRMS_ASYNC_JOB_MODE=in_process`，避免把耗时任务长期留在请求线程。
- `TRMS_ASYNC_JOB_POLL_INTERVAL_SECONDS` 默认 `5`，用于 worker 空闲轮询间隔。
- `TRMS_ASYNC_JOB_WORKER_CONCURRENCY` 默认 `4`，用于 worker 模式下并发处理待识别材料，支持成员批量上传发票后同时消费多条识别任务。
- 当前 worker 已可消费待执行的识别任务，并沿用现有识别状态、失败原因和重试历史查询接口。
- 当前 worker 已可消费待执行的导出任务，并为已实现的 CSV / JSON / merged PDF 导出落盘产物、更新状态、失败原因和重试历史查询。
- 当前 worker 也可在配置 IMAP 后轮询邮箱，记录邮件去重结果和忽略原因。
- 导出产物需通过导出任务下载接口访问；当前真实合并 PDF 已实现，XLSX 导出仍未实现。

示例：

```bash
TRMS_TEXT_LLM_API_KEY=sk-example \
TRMS_TEXT_LLM_BASE_URL=https://llm.example.com/v1 \
TRMS_TEXT_LLM_MODEL=gpt-4.1-mini \
TRMS_VLM_API_KEY=sk-example \
TRMS_VLM_BASE_URL=https://llm.example.com/v1 \
TRMS_VLM_MODEL=gpt-4.1-mini \
uv run python -m trms_backend --reload
```

启动异步 worker 入口：

```bash
TRMS_ASYNC_JOB_MODE=worker uv run python -m trms_backend worker
```

启动 Telegram 开发轮询入口：

```bash
uv run python -m trms_backend telegram-bot --drop-pending-updates
```

说明：

- 该入口面向开发环境，使用 Telegram long polling，不依赖公网 webhook；
- 仍要求已配置 `TRMS_TELEGRAM_BOT_TOKEN`；
- 若同时配置过 webhook，启动轮询前会先删除 webhook。

本地仅做入口自检时可运行一次轮询后退出：

```bash
TRMS_ASYNC_JOB_MODE=worker uv run python -m trms_backend worker --once
```

## 当前未实现或未联通的外部依赖

以下能力不要按“README 已写到就等于可直接使用”理解：

- Telegram 渠道现在已补真实 Bot / Webhook 接入口，但生产环境仍需自行向 Telegram 注册 webhook，并通过 `TRMS_TELEGRAM_WEBHOOK_SECRET` 收口入口可信性。
- 格式化邮件渠道目前已完成格式规范、受信任入站边界、邮箱绑定、IMAP 轮询去重、附件写入统一材料主链路和 SMTP 结果回执。
- OpenAI 兼容文本 LLM / VLM Provider 只有在环境变量或系统管理员系统配置中至少配置了一类后才会启用；未配置对应 provider 时识别会显式失败，不会伪装为识别成功。
- Browser Use / 财务系统自动录入明确属于第一阶段范围外，不应被当作现成功能。
- XLSX 导出仍未实现；当前可落盘并下载的是 CSV / JSON / `merged_pdf`。

## Web 前端

```bash
cd web
npm install
npm run dev
```

前端工程使用 React + TypeScript + Vite。仓库根目录执行 `./scripts/verify.sh` 时，如存在 `web/package.json`，会自动进入 `web/` 执行 `npm run lint`、`npm test` 和 `npm run build`。

Vite 开发服务的监听 host/port 可通过环境变量配置，只影响 `npm run dev`，不会写入生产构建产物：

```bash
npm run dev
```

以上配置默认从仓库根目录 `.env` 读取；若只想临时覆盖当前进程，也可以继续用 shell 环境变量，例如 `TRMS_WEB_HOST=0.0.0.0 TRMS_WEB_PORT=4173 npm run dev`。

前端 API 地址边界如下：

1. 同源 `/api`

默认前端 API 地址为 `/api`。适用于本地 Vite 代理或生产环境下由反向代理把 `/api` 转发到后端，无需额外公开后端地址。

2. 本地跨端口联调

本地联调时可通过设置 `VITE_API_BASE_URL` 指向后端服务，例如：

```bash
npm run dev
```

推荐直接把以下值写入根目录 `.env`：

```dotenv
TRMS_WEB_HOST=127.0.0.1
TRMS_WEB_PORT=5173
VITE_API_BASE_URL=http://127.0.0.1:8100/api
```

3. 生产反向代理

生产部署优先保持前端构建产物中的 API 地址为默认 `/api`，并由 Nginx、Caddy 或其他反向代理把 `/api` 路由到后端服务。只有在前后端必须跨域部署时，才应在构建时设置公开可见的 `VITE_API_BASE_URL`。

安全边界：

- 所有 `VITE_*` 变量都会进入前端构建产物，只能保存公开配置。
- `VITE_ENABLE_DEV_AUTH_ROUTES` 用于控制登录页的开发调试角色入口和高权限自注册入口；默认在生产构建下隐藏，只有显式设置为 `true` 才会重新显示。
- 不要把 OpenAI 兼容 LLM `api_key`、后端 secret、数据库凭据或长期 token 写入 `VITE_*` 变量。
- 不要把对象存储 access key / secret key 写入 `VITE_*` 变量。
- 前端页面和测试不应展示上述 secret；相关敏感配置只能保留在后端环境变量或专用密钥管理中。
- `TRMS_TEXT_LLM_API_KEY`、`TRMS_VLM_API_KEY` 与兼容旧路径的 `TRMS_LLM_API_KEY` 只能保留在后端环境变量、系统管理员系统配置或专用密钥管理中，不返回前端，也不应写入日志。

## 基础账号登录

后端提供最小账号 API：

- `POST /api/auth/register`
- `POST /api/auth/registration-verification-code`
- `POST /api/auth/bootstrap-admin`
- `POST /api/auth/login`
- `GET /api/auth/me`
- `POST /api/auth/logout`

密码使用 PBKDF2-SHA256 加盐哈希保存，不保存明文密码。登录成功后返回 bearer token，Web 前端会保存 token 和用户身份，用于恢复页面会话。

生产注册策略边界：

- 默认只有 `member` 允许通过 `POST /api/auth/register` 自注册。
- `POST /api/auth/registration-verification-code` 用于发送注册邮箱验证码；生产环境下只会向系统管理员允许的邮箱 host 发送验证码。
- `POST /api/auth/register` 只接受单角色自注册；像 `roles=["member","admin"]` 这样的多角色直写仅保留给历史测试夹具，不再视为真实产品赋权路径。
- `TRMS_ENV=production` 时，`admin` 和 `system_admin` 角色的自注册默认关闭；只有显式设置 `TRMS_AUTH_ALLOW_ADMIN_SELF_REGISTER=true` 才会重新开放，主要用于受控调试环境。
- `TRMS_ENV=production` 时，自助注册必须同时满足：
  - 注册邮箱 host 已被系统管理员加入 allowlist；
  - 先通过邮箱验证码验证；
  - 注册成功后，该邮箱会自动写入系统邮箱绑定。
- 生产环境下注册邮箱 host allowlist 默认是空列表，因此系统初始化后不会有任何用户能直接自助注册；必须先由首个 `system_admin` 登录系统管理页配置 allowlist。
- 生产环境初始化首个高权限账号时，可为后端配置 `TRMS_AUTH_BOOTSTRAP_ADMIN_TOKEN`，再调用 `POST /api/auth/bootstrap-admin` 并在请求头携带 `X-TRMS-Bootstrap-Token`。
- `bootstrap-admin` 入口现在只允许创建首个 `system_admin` 账号；一旦库里已经存在任一高权限账号，该入口会显式拒绝再次使用，后续邀请/审批流程仍待单独实现。
- 首个 `system_admin` 创建完成后，应立即进入 `/system` 设置“注册邮箱 host 白名单”，再通知成员使用邮箱验证码完成自助注册。
- 需要把已有账号追加为管理员时，应由 `system_admin` 调用 `PUT /api/system/users/{user_id}/roles/admin`；多角色账号的真实来源应走该受控接口，而不是公开注册时直接提交多角色数组。
- 用户表会记录账号创建来源，区分 `self_service` 与 `bootstrap_token`，作为最小审计边界。

当前限制：既有业务 API 仍有部分路径通过 `actor_id`、`submitter_id` 或 `member_id` 参数表达操作者身份；后续任务会继续把这些路径迁移到 bearer 身份上下文并补齐强权限控制。
