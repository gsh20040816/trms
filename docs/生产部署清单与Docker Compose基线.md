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
7. `reverse-proxy`：统一入口，负责 `/api` 反向代理和前端静态页面转发。
8. `migrate`：一次性 Alembic 迁移容器，用于启动前把数据库迁移到 `head`。
9. `minio-init`：一次性初始化 MinIO bucket。

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
   - `TRMS_LLM_API_KEY`
4. 若正式域名不是 `localhost`，同步更新：
   - `TRMS_PUBLIC_HTTP_PORT`
   - `TRMS_CORS_ALLOWED_ORIGINS`
   - `TRMS_PUBLIC_API_BASE_URL`
5. 若对象存储 bucket、region 或 key prefix 有定制需求，更新：
   - `TRMS_STORAGE_S3_BUCKET`
   - `TRMS_STORAGE_S3_REGION`
   - `TRMS_STORAGE_S3_KEY_PREFIX`

## 启动步骤

首次部署建议按以下顺序执行：

```bash
docker compose --env-file .env -f deploy/docker-compose.yml up -d postgres redis minio
docker compose --env-file .env -f deploy/docker-compose.yml up minio-init
docker compose --env-file .env -f deploy/docker-compose.yml run --rm migrate
docker compose --env-file .env -f deploy/docker-compose.yml up -d api worker web reverse-proxy
```

如果只是重复执行迁移，也可以单独运行：

```bash
docker compose --env-file .env -f deploy/docker-compose.yml run --rm migrate
```

## 健康检查

部署完成后，至少检查以下内容：

1. 统一入口健康检查：

```bash
curl http://127.0.0.1:${TRMS_PUBLIC_HTTP_PORT:-8080}/health
```

2. Compose 服务状态：

```bash
docker compose --env-file .env -f deploy/docker-compose.yml ps
```

3. 关键容器健康状态应满足：
   - `postgres` 为 `healthy`
   - `redis` 为 `healthy`
   - `minio` 为 `healthy`
   - `api` 为 `healthy`
   - `web` 为 `healthy`
   - `reverse-proxy` 为 `healthy`
4. MinIO 管理控制台默认仅暴露到宿主机 `127.0.0.1:9001`，应通过本机或受控隧道访问，不应直接公开到公网。

## 日志位置

当前部署基线默认把日志输出到容器 stdout/stderr，不在仓库内额外写磁盘日志文件。排障入口如下：

```bash
docker compose --env-file .env -f deploy/docker-compose.yml logs -f api worker
docker compose --env-file .env -f deploy/docker-compose.yml logs -f reverse-proxy
docker compose --env-file .env -f deploy/docker-compose.yml logs -f postgres
docker compose --env-file .env -f deploy/docker-compose.yml logs -f minio
```

补充说明：

1. `reverse-proxy` 和 `web` 容器内部仍使用 Nginx 默认日志路径 `/var/log/nginx/access.log` 与 `/var/log/nginx/error.log`，但在当前基线下推荐统一通过 `docker compose logs` 查看。
2. PostgreSQL 数据目录位于命名卷 `postgres-data`。
3. Redis 数据目录位于命名卷 `redis-data`。
4. MinIO 对象数据位于命名卷 `minio-data`。

## 运行边界

1. `TRMS_ENV=production` 时，后端不会自动建表；必须先运行 `migrate`。
2. 前端默认通过 `VITE_API_BASE_URL=/api` 走同源反向代理，不在构建产物里暴露后端内网地址。
3. 当前 worker 仍使用数据库轮询模型，`redis` 只作为第一阶段部署基线预留，不代表仓库已经切换到 Redis Broker。
4. 当前对象存储后端固定为 S3 兼容模式，Compose 基线里默认指向内部 `minio:9000`。
5. 当前导出下载仍经后端接口鉴权读取，不暴露长期公开对象 URL。

## 初始管理员创建

部署完成且 `api` 健康后，可用 bootstrap token 创建首个高权限账号：

```bash
curl -X POST http://127.0.0.1:${TRMS_PUBLIC_HTTP_PORT:-8080}/api/auth/bootstrap-admin \
  -H "Content-Type: application/json" \
  -H "X-TRMS-Bootstrap-Token: ${TRMS_AUTH_BOOTSTRAP_ADMIN_TOKEN}" \
  -d '{
    "username": "admin",
    "password": "replace-with-admin-password",
    "role": "system_admin"
  }'
```

约束如下：

1. 该入口只允许创建首个 `admin` 或 `system_admin`。
2. 一旦库中已经存在任一高权限账号，该接口会显式拒绝再次使用。
3. `TRMS_AUTH_ALLOW_ADMIN_SELF_REGISTER` 在生产模板中默认是 `false`，不要改成 `true` 作为长期方案。

## 回滚与重建

仅在确认可接受停机和数据影响时执行：

```bash
docker compose --env-file .env -f deploy/docker-compose.yml down
```

如果要连同数据卷一起销毁：

```bash
docker compose --env-file .env -f deploy/docker-compose.yml down -v
```

这会删除 `postgres-data`、`redis-data` 和 `minio-data`，只能在已经完成备份或明确允许丢数据时执行。
