# 生产部署清单与 Docker Compose 基线

更新时间：2026-04-28

本文档为第一阶段提供最小可运行的部署基线，对应 `deploy/docker-compose.yml`、`deploy/Dockerfile.api`、`deploy/Dockerfile.web` 和根目录 `.env.example`。本地开发环境建议改用根目录 `.env.development.example` 复制为 `.env`。

根目录 `.env` 也是当前仓库统一的运行配置文件：后端 `uv run python -m trms_backend`、worker 和 `web` 前端开发/构建流程都会默认读取这同一份文件；若 shell 中显式传入同名环境变量，则以显式环境变量为准。

## 当前范围

当前部署基线包含以下服务：

1. `api`：FastAPI 后端。
2. `worker`：异步识别与导出 worker。
3. `web`：Vite 构建后的静态前端。
4. `postgres`：主数据库。
5. `redis`：为架构建议中的 Broker / 缓存预留，本轮只纳入部署基线，不接入当前后端主链路。
6. `minio`：S3 兼容对象存储。
7. `migrate`：一次性 Alembic 迁移容器，用于启动前把数据库迁移到 `head`。
8. `minio-init`：一次性初始化 MinIO bucket。

## 部署前检查清单

1. 安装 Docker Engine 与 Docker Compose v2。
2. 复制环境变量模板：

```bash
cp .env.example .env
```

3. 在 `.env` 中替换以下占位值：
   - `TRMS_POSTGRES_PASSWORD`
   - `TRMS_MINIO_ROOT_USER`
   - `TRMS_MINIO_ROOT_PASSWORD`
   - `TRMS_STORAGE_S3_ACCESS_KEY_ID`
   - `TRMS_STORAGE_S3_SECRET_ACCESS_KEY`
   - `TRMS_AUTH_BOOTSTRAP_ADMIN_TOKEN`
   - `TRMS_TEXT_LLM_API_KEY`
   - `TRMS_VLM_API_KEY`
4. 同步更新对外正式地址：
   - `TRMS_CORS_ALLOWED_ORIGINS`
   - `TRMS_PUBLIC_API_BASE_URL`
   - `TRMS_PUBLIC_WEB_BASE_URL`
5. 若对象存储 bucket、region 或 key prefix 有定制需求，更新：
   - `TRMS_STORAGE_S3_BUCKET`
   - `TRMS_STORAGE_S3_REGION`
   - `TRMS_STORAGE_S3_KEY_PREFIX`

## 启动步骤

首次部署建议按以下顺序执行：

优先使用仓库提供的统一脚本：

```bash
./scripts/trms-prod.sh start
```

该脚本会依次执行：

- 启动 `postgres`、`redis`、`minio`
- 运行 `minio-init`
- 执行 `migrate`
- 启动 `api`、`worker`、`web`

如需查看状态、日志或停止服务，可使用：

```bash
./scripts/trms-prod.sh status
./scripts/trms-prod.sh logs
./scripts/trms-prod.sh stop
./scripts/trms-prod.sh down
```

补充约束：

- 脚本默认读取仓库根目录 `.env` 与 `deploy/docker-compose.yml`
- 脚本会校验 `TRMS_ENV=production`，避免误把开发配置当成生产基线执行
- 若需覆盖路径，可设置 `TRMS_PROD_ENV_FILE` 或 `TRMS_PROD_COMPOSE_FILE`

若需要手工分步执行，等价命令如下：

```bash
docker compose --env-file .env -f deploy/docker-compose.yml up -d postgres redis minio
docker compose --env-file .env -f deploy/docker-compose.yml up minio-init
docker compose --env-file .env -f deploy/docker-compose.yml run --rm migrate
docker compose --env-file .env -f deploy/docker-compose.yml up -d api worker web
```

如果只是重复执行迁移，也可以单独运行：

```bash
docker compose --env-file .env -f deploy/docker-compose.yml run --rm migrate
```

## 健康检查

部署完成后，至少检查以下内容：

1. 后端健康检查：

```bash
curl http://127.0.0.1:${TRMS_API_PORT:-9876}/health
```

2. 前端健康检查：

```bash
curl http://127.0.0.1:8081/healthz
```

3. Compose 服务状态：

```bash
docker compose --env-file .env -f deploy/docker-compose.yml ps
```

4. 关键容器健康状态应满足：
   - `postgres` 为 `healthy`
   - `redis` 为 `healthy`
   - `minio` 为 `healthy`
   - `api` 为 `healthy`
   - `web` 为 `healthy`
5. `api` 当前仅暴露到宿主机 `127.0.0.1:${TRMS_API_PORT:-9876}`，`web` 仅暴露到宿主机 `127.0.0.1:8081`；应由宿主机上的 Caddy、Nginx 或其他外部反向代理统一提供 HTTPS 与公网入口，不应把这两个回环端口直接映射到公网。
6. MinIO 管理控制台默认仅暴露到宿主机 `127.0.0.1:9001`，应通过本机或受控隧道访问，不应直接公开到公网。

## 日志位置

当前部署基线默认把日志输出到容器 stdout/stderr，不在仓库内额外写磁盘日志文件。排障入口如下：

```bash
docker compose --env-file .env -f deploy/docker-compose.yml logs -f api worker
docker compose --env-file .env -f deploy/docker-compose.yml logs -f web
docker compose --env-file .env -f deploy/docker-compose.yml logs -f postgres
docker compose --env-file .env -f deploy/docker-compose.yml logs -f minio
```

补充说明：

1. `web` 容器内部仍使用 Nginx 默认日志路径 `/var/log/nginx/access.log` 与 `/var/log/nginx/error.log`，但在当前基线下推荐统一通过 `docker compose logs` 查看；若宿主机再通过 Caddy 或 Nginx 反代，对外入口日志应到对应宿主机代理中查看。
2. PostgreSQL 数据目录位于命名卷 `postgres-data`。
3. Redis 数据目录位于命名卷 `redis-data`。
4. MinIO 对象数据位于命名卷 `minio-data`。

## 运行边界

1. `TRMS_ENV=production` 时，后端不会自动建表；必须先运行 `migrate`。
2. 前端默认通过 `VITE_API_BASE_URL=/api` 走同源反向代理，不在构建产物里暴露后端内网地址；当前 Compose 基线默认假设宿主机上的 Caddy、Nginx 或其他外部反向代理负责把 `/api` 路由到 `127.0.0.1:${TRMS_API_PORT:-9876}`，并把其他路径路由到 `127.0.0.1:8081`。
3. 当前 worker 仍使用数据库轮询模型，`redis` 只作为第一阶段部署基线预留，不代表仓库已经切换到 Redis Broker；`TRMS_ASYNC_JOB_WORKER_CONCURRENCY` 控制单个 worker 进程内的识别并发线程数。
4. 当前 Compose 基线默认使用 S3 兼容对象存储，并指向内部 `minio:9000`；若改为 `TRMS_STORAGE_BACKEND=local`，Compose 已会把 `MATERIAL_STORAGE_DIR` 透传给 `migrate`、`api`、`worker`，并将宿主机同一路径 bind mount 到 `api` 与 `worker` 容器内，例如 `MATERIAL_STORAGE_DIR=/srv/trms/materials` 时，宿主机 `/srv/trms/materials` 就是材料与导出产物的持久化目录。
5. 当前导出下载仍经后端接口鉴权读取，不暴露长期公开对象 URL。

## 初始管理员创建

部署完成且 `api` 健康后，可用 bootstrap token 创建首个高权限账号。若外部反向代理已就绪，优先走正式 HTTPS 域名；若仍在宿主机本地调试，也可直接访问回环端口：

```bash
curl -X POST http://127.0.0.1:${TRMS_API_PORT:-9876}/api/auth/bootstrap-admin \
  -H "Content-Type: application/json" \
  -H "X-TRMS-Bootstrap-Token: ${TRMS_AUTH_BOOTSTRAP_ADMIN_TOKEN}" \
  -d '{
    "username": "admin",
    "password": "replace-with-admin-password",
    "role": "system_admin"
  }'
```

约束如下：

1. 该入口只允许创建首个 `system_admin`。
2. 一旦库中已经存在任一高权限账号，该接口会显式拒绝再次使用。
3. `TRMS_AUTH_ALLOW_ADMIN_SELF_REGISTER` 在生产模板中默认是 `false`，不要改成 `true` 作为长期方案。

## 回滚与重建

仅在确认可接受停机和数据影响时执行：

```bash
./scripts/trms-prod.sh down
```

等价手工命令：

```bash
docker compose --env-file .env -f deploy/docker-compose.yml down
```

如果要连同数据卷一起销毁：

```bash
docker compose --env-file .env -f deploy/docker-compose.yml down -v
```

这会删除 `postgres-data`、`redis-data` 和 `minio-data`，只能在已经完成备份或明确允许丢数据时执行。
