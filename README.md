# TRMS

同济大学 ACM 竞赛报销收集系统。

当前开发切片聚焦后端基础能力：报销任务创建、查询和状态管理骨架。

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
