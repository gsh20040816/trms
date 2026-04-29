# UX Playwright 基线

本目录保存一份最小 Playwright 重放脚本，用于复现本轮真实用户路径。

说明：

- 本轮实际浏览器操作由 Playwright MCP 完成。
- 这里的脚本用于后续本地重复执行，不代表本轮所有断言都已自动化。
- 默认依赖已经复制好的真实数据副本：
  - `tmp/ux-real-data/武汉/报名费/ICPC武汉_同济大学_于离别之朝束起约定之花.pdf`
  - `tmp/ux-real-data/武汉/50thICPC邀请函（武汉）.pdf`
  - `tmp/ux-real-data/沈阳/【享道出行-49.34元-1个行程】高德打车电子发票.pdf`
  - `tmp/ux-real-data/沈阳/沈阳-上海1079.png`

## 启动

后端：

```bash
TRMS_ENV=development \
DATABASE_URL=sqlite:///./tmp/ux-runtime/ux-test.db \
TRMS_STORAGE_BACKEND=local \
MATERIAL_STORAGE_DIR=./tmp/ux-runtime/materials \
TRMS_CORS_ALLOWED_ORIGINS=http://127.0.0.1:4173,http://localhost:4173 \
TRMS_PUBLIC_API_BASE_URL=http://127.0.0.1:9877/api \
TRMS_API_HOST=127.0.0.1 \
TRMS_API_PORT=9877 \
TRMS_ASYNC_JOB_MODE=in_process \
TRMS_AUTH_ALLOW_ADMIN_SELF_REGISTER=true \
uv run python -m trms_backend --host 127.0.0.1 --port 9877
```

前端：

```bash
cd web
VITE_API_BASE_URL=http://127.0.0.1:9877/api npm run dev -- --host 127.0.0.1 --port 4173
```

## 执行

```bash
npx -y playwright@1.59.1 test tests/ux/real-user-flows.spec.mjs
```

