# TRMS

同济大学 ACM 竞赛报销收集系统。

当前开发切片已具备后端、CLI 与 Web 前端的第一阶段主链路骨架，并提供基础用户名密码注册登录能力。

## 本地验证

```bash
uv sync
uv run pytest
uv run uvicorn trms_backend.main:app --reload
```

默认使用本地 SQLite 文件 `trms.db`。如需连接 PostgreSQL，可设置 `DATABASE_URL`。

```bash
DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/trms uv run uvicorn trms_backend.main:app --reload
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
