# TRMS

同济大学 ACM 竞赛报销收集系统。

当前开发切片已具备后端、CLI 与 Web 前端的第一阶段主链路骨架，并提供基础用户名密码注册登录能力。

## 本地验证

```bash
uv sync
uv run pytest
uv run python -m trms_backend --reload
```

默认使用本地 SQLite 文件 `trms.db`。如需连接 PostgreSQL，可设置 `DATABASE_URL`。

```bash
DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/trms uv run python -m trms_backend --reload
```

后端运行配置已统一收敛到环境变量：

- `TRMS_ENV`：`development`、`test` 或 `production`，默认 `development`
- `DATABASE_URL`
- `MATERIAL_STORAGE_DIR`
- `TRMS_CORS_ALLOWED_ORIGINS`：逗号分隔的 `http(s)://host[:port]` 列表
- `TRMS_PUBLIC_API_BASE_URL`
- `TRMS_API_HOST`
- `TRMS_API_PORT`
- `TRMS_ASYNC_JOB_MODE`
- `TRMS_ASYNC_JOB_POLL_INTERVAL_SECONDS`
- `TRMS_LLM_API_KEY`
- `TRMS_LLM_BASE_URL`
- `TRMS_LLM_MODEL`
- `TRMS_LLM_TIMEOUT_SECONDS`
- `TRMS_LLM_MAX_RETRIES`

开发环境默认值：

- `DATABASE_URL=sqlite:///./trms.db`
- `MATERIAL_STORAGE_DIR=./data/materials`
- `TRMS_CORS_ALLOWED_ORIGINS=http://127.0.0.1:5173,http://localhost:5173`
- `TRMS_PUBLIC_API_BASE_URL=http://127.0.0.1:8000/api`
- `TRMS_API_HOST=127.0.0.1`
- `TRMS_API_PORT=8000`

本地跨端口联调示例：

```bash
TRMS_API_HOST=127.0.0.1 \
TRMS_API_PORT=8100 \
TRMS_PUBLIC_API_BASE_URL=http://127.0.0.1:8100/api \
TRMS_CORS_ALLOWED_ORIGINS=http://127.0.0.1:5173,http://localhost:5173 \
uv run python -m trms_backend --reload
```

生产环境不会静默回退到开发默认值；当 `TRMS_ENV=production` 时，以上变量都必须显式提供，否则服务会在启动时直接报错。启动参数 `--host`、`--port` 可覆盖对应环境变量，例如：

```bash
TRMS_ENV=production \
DATABASE_URL=postgresql+psycopg://user:password@db:5432/trms \
MATERIAL_STORAGE_DIR=/var/lib/trms/materials \
TRMS_CORS_ALLOWED_ORIGINS=https://trms.example.edu \
TRMS_PUBLIC_API_BASE_URL=https://trms.example.edu/api \
TRMS_API_HOST=0.0.0.0 \
TRMS_API_PORT=8000 \
uv run python -m trms_backend --host 0.0.0.0 --port 8000
```

OpenAI 兼容 LLM Provider 配置边界：

- 只有在至少配置了一个 `TRMS_LLM_*` 变量时，后端才会尝试启用 LLM Provider 配置块。
- 一旦开始配置 `TRMS_LLM_*`，`TRMS_LLM_API_KEY` 和 `TRMS_LLM_MODEL` 必填；缺失时服务会在启动阶段直接报错。
- `TRMS_LLM_BASE_URL` 默认为 `https://api.openai.com/v1`，可替换为任何 OpenAI 兼容接口地址；尾部 `/` 会被规范化去掉。
- `TRMS_LLM_TIMEOUT_SECONDS` 默认 `30`，`TRMS_LLM_MAX_RETRIES` 默认 `2`。
- 当前仓库已接入“文本 PDF 提取 -> OpenAI 兼容 LLM 结构化识别”的最小同步执行链；扫描 PDF / 图片 OCR 和完整异步 worker 消费链仍待后续任务补齐。
- 未配置 LLM Provider 时，识别执行链会将任务显式视为 `disabled`，而不是伪造识别成功。

异步任务运行模式边界：

- `TRMS_ASYNC_JOB_MODE` 支持 `in_process` 和 `worker` 两种模式。
- 开发和测试环境默认使用 `in_process`，便于当前同步接口和本地排障。
- `TRMS_ENV=production` 时默认切换为 `worker`，并拒绝 `TRMS_ASYNC_JOB_MODE=in_process`，避免把耗时任务长期留在请求线程。
- `TRMS_ASYNC_JOB_POLL_INTERVAL_SECONDS` 默认 `5`，用于 worker 空闲轮询间隔。
- 当前 worker 已可消费待执行的识别任务，并沿用现有识别状态、失败原因和重试历史查询接口。
- 导出任务的真正异步消费逻辑仍待后续任务接入；当前 `export` processor 仍是占位。

示例：

```bash
TRMS_LLM_API_KEY=sk-example \
TRMS_LLM_BASE_URL=https://llm.example.com/v1 \
TRMS_LLM_MODEL=gpt-4.1-mini \
TRMS_LLM_TIMEOUT_SECONDS=20 \
TRMS_LLM_MAX_RETRIES=1 \
uv run python -m trms_backend --reload
```

启动异步 worker 入口：

```bash
TRMS_ASYNC_JOB_MODE=worker uv run python -m trms_backend worker
```

本地仅做入口自检时可运行一次轮询后退出：

```bash
TRMS_ASYNC_JOB_MODE=worker uv run python -m trms_backend worker --once
```

## Web 前端

```bash
cd web
npm install
npm run dev
```

前端工程使用 React + TypeScript + Vite。仓库根目录执行 `./scripts/verify.sh` 时，如存在 `web/package.json`，会自动进入 `web/` 执行 `npm run lint`、`npm test` 和 `npm run build`。

Vite 开发服务的监听 host/port 可通过环境变量配置，只影响 `npm run dev`，不会写入生产构建产物：

```bash
TRMS_WEB_HOST=0.0.0.0 TRMS_WEB_PORT=4173 npm run dev
```

前端 API 地址边界如下：

1. 同源 `/api`

默认前端 API 地址为 `/api`。适用于本地 Vite 代理或生产环境下由反向代理把 `/api` 转发到后端，无需额外公开后端地址。

2. 本地跨端口联调

本地联调时可通过设置 `VITE_API_BASE_URL` 指向后端服务，例如：

```bash
TRMS_WEB_HOST=127.0.0.1 \
TRMS_WEB_PORT=5173 \
VITE_API_BASE_URL=http://127.0.0.1:8100/api \
npm run dev
```

3. 生产反向代理

生产部署优先保持前端构建产物中的 API 地址为默认 `/api`，并由 Nginx、Caddy 或其他反向代理把 `/api` 路由到后端服务。只有在前后端必须跨域部署时，才应在构建时设置公开可见的 `VITE_API_BASE_URL`。

安全边界：

- 所有 `VITE_*` 变量都会进入前端构建产物，只能保存公开配置。
- 不要把 OpenAI 兼容 LLM `api_key`、后端 secret、数据库凭据或长期 token 写入 `VITE_*` 变量。
- 前端页面和测试不应展示上述 secret；相关敏感配置只能保留在后端环境变量或专用密钥管理中。
- `TRMS_LLM_API_KEY` 只允许从后端环境变量或密钥管理读取，不入库、不返回前端，也不应写入日志。

## 基础账号登录

后端提供最小账号 API：

- `POST /api/auth/register`
- `POST /api/auth/login`
- `GET /api/auth/me`
- `POST /api/auth/logout`

密码使用 PBKDF2-SHA256 加盐哈希保存，不保存明文密码。登录成功后返回 bearer token，Web 前端会保存 token 和用户身份，用于恢复页面会话。

当前限制：既有业务 API 仍有部分路径通过 `actor_id`、`submitter_id` 或 `member_id` 参数表达操作者身份；后续任务会继续把这些路径迁移到 bearer 身份上下文并补齐强权限控制。
