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

## Web 前端

```bash
cd web
npm install
npm run dev
```

前端工程使用 React + TypeScript + Vite。仓库根目录执行 `./scripts/verify.sh` 时，如存在 `web/package.json`，会自动进入 `web/` 执行 `npm run lint`、`npm test` 和 `npm run build`。

默认前端 API 地址为 `/api`。本地联调时可通过 Vite 代理或设置 `VITE_API_BASE_URL` 指向后端服务，例如：

```bash
VITE_API_BASE_URL=http://127.0.0.1:8000/api npm run dev
```

## 基础账号登录

后端提供最小账号 API：

- `POST /api/auth/register`
- `POST /api/auth/login`
- `GET /api/auth/me`
- `POST /api/auth/logout`

密码使用 PBKDF2-SHA256 加盐哈希保存，不保存明文密码。登录成功后返回 bearer token，Web 前端会保存 token 和用户身份，用于恢复页面会话。

当前限制：既有业务 API 仍有部分路径通过 `actor_id`、`submitter_id` 或 `member_id` 参数表达操作者身份；后续任务会继续把这些路径迁移到 bearer 身份上下文并补齐强权限控制。
