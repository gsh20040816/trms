#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="$ROOT_DIR/deploy/docker-compose.yml"
PROJECT_NAME="${TRMS_DRILL_PROJECT_NAME:-trms-backup-drill}"
PUBLIC_HTTP_PORT="${TRMS_DRILL_HTTP_PORT:-18080}"
API_BASE_URL="http://127.0.0.1:${PUBLIC_HTTP_PORT}/api"
WORK_DIR="${TRMS_DRILL_WORK_DIR:-$(mktemp -d "${TMPDIR:-/tmp}/trms-backup-drill.XXXXXX")}"
ENV_FILE="$WORK_DIR/.env"
BACKUP_DIR="$WORK_DIR/backups"
DB_BACKUP_FILE="$BACKUP_DIR/postgres/trms.dump"
OBJECT_BACKUP_DIR="$BACKUP_DIR/object-storage"
SAMPLE_FILE="$WORK_DIR/sample-invoice.pdf"
START_TS="$(date +%s)"
HOST_UID="$(id -u)"
HOST_GID="$(id -g)"

POSTGRES_DB="trms"
POSTGRES_USER="trms"
POSTGRES_PASSWORD="trms-backup-drill-password"
MINIO_ROOT_USER="trms-backup-drill-root"
MINIO_ROOT_PASSWORD="trms-backup-drill-root-password"
S3_ACCESS_KEY_ID="$MINIO_ROOT_USER"
S3_SECRET_ACCESS_KEY="$MINIO_ROOT_PASSWORD"
S3_BUCKET="trms-backup-drill"
BOOTSTRAP_ADMIN_TOKEN="trms-backup-drill-bootstrap-token"
MINIO_ENDPOINT="http://minio:9000"
MINIO_NETWORK_ENDPOINT="http://minio:9000"
LLM_BASE_URL="http://127.0.0.1:9"
LLM_API_KEY="sk-backup-drill-placeholder"
LLM_MODEL="gpt-4.1-mini"

log() {
  printf '[backup-drill] %s\n' "$*"
}

fail() {
  log "失败：$*"
  exit 1
}

have_cmd() {
  command -v "$1" >/dev/null 2>&1
}

compose() {
  docker compose \
    --project-name "$PROJECT_NAME" \
    --env-file "$ENV_FILE" \
    -f "$COMPOSE_FILE" \
    "$@"
}

json_get() {
  local expression="$1"
  python3 -c 'import json, sys; data = json.load(sys.stdin); value = eval(sys.argv[1], {"__builtins__": {}}, {"data": data}); print("" if value is None else value)' "$expression"
}

http_get() {
  local url="$1"
  shift
  curl -fsS "$@" "$url"
}

http_post_json() {
  local url="$1"
  local payload="$2"
  shift 2
  curl -fsS "$@" \
    -H 'Content-Type: application/json' \
    -d "$payload" \
    "$url"
}

http_patch_json() {
  local url="$1"
  local payload="$2"
  shift 2
  curl -fsS -X PATCH "$@" \
    -H 'Content-Type: application/json' \
    -d "$payload" \
    "$url"
}

wait_for_http() {
  local url="$1"
  local attempts="${2:-120}"
  local sleep_seconds="${3:-2}"
  local attempt=1

  while (( attempt <= attempts )); do
    if curl -fsS "$url" >/dev/null 2>&1; then
      return 0
    fi
    sleep "$sleep_seconds"
    attempt=$((attempt + 1))
  done

  return 1
}

wait_for_postgres() {
  local attempts=60
  local attempt=1

  while (( attempt <= attempts )); do
    if compose exec -T postgres pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null 2>&1; then
      return 0
    fi
    sleep 2
    attempt=$((attempt + 1))
  done

  return 1
}

cleanup() {
  if [[ "${TRMS_DRILL_SKIP_CLEANUP:-0}" == "1" ]]; then
    log "跳过清理，保留 Compose 环境供人工检查"
    return
  fi

  if [[ -f "$ENV_FILE" ]]; then
    compose down -v >/dev/null 2>&1 || true
  fi

  if [[ "${TRMS_DRILL_KEEP_WORK_DIR:-0}" != "1" ]]; then
    rm -rf "$WORK_DIR" 2>/dev/null || true
    if [[ -d "$WORK_DIR" ]]; then
      docker run --rm \
        -v "$WORK_DIR:/workdir" \
        --entrypoint /bin/sh \
        minio/mc:latest \
        -ec 'rm -rf /workdir/* /workdir/.[!.]* /workdir/..?* 2>/dev/null || true' \
        >/dev/null 2>&1 || true
      rmdir "$WORK_DIR" 2>/dev/null || true
    fi
  fi
}

create_env_file() {
  mkdir -p "$BACKUP_DIR/postgres" "$OBJECT_BACKUP_DIR"
  cat >"$ENV_FILE" <<EOF
TRMS_PUBLIC_HTTP_PORT=${PUBLIC_HTTP_PORT}

TRMS_POSTGRES_DB=${POSTGRES_DB}
TRMS_POSTGRES_USER=${POSTGRES_USER}
TRMS_POSTGRES_PASSWORD=${POSTGRES_PASSWORD}

TRMS_MINIO_ROOT_USER=${MINIO_ROOT_USER}
TRMS_MINIO_ROOT_PASSWORD=${MINIO_ROOT_PASSWORD}

DATABASE_URL=postgresql+psycopg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}

TRMS_ENV=production
TRMS_STORAGE_BACKEND=s3
TRMS_STORAGE_S3_ENDPOINT=${MINIO_ENDPOINT}
TRMS_STORAGE_S3_BUCKET=${S3_BUCKET}
TRMS_STORAGE_S3_ACCESS_KEY_ID=${S3_ACCESS_KEY_ID}
TRMS_STORAGE_S3_SECRET_ACCESS_KEY=${S3_SECRET_ACCESS_KEY}
TRMS_STORAGE_S3_REGION=us-east-1
TRMS_STORAGE_S3_KEY_PREFIX=prod

TRMS_CORS_ALLOWED_ORIGINS=http://127.0.0.1:${PUBLIC_HTTP_PORT},http://localhost:${PUBLIC_HTTP_PORT}
TRMS_PUBLIC_API_BASE_URL=http://127.0.0.1:${PUBLIC_HTTP_PORT}/api
TRMS_API_HOST=0.0.0.0
TRMS_API_PORT=8000

TRMS_ASYNC_JOB_MODE=worker
TRMS_ASYNC_JOB_POLL_INTERVAL_SECONDS=5

TRMS_AUTH_ALLOW_ADMIN_SELF_REGISTER=false
TRMS_AUTH_BOOTSTRAP_ADMIN_TOKEN=${BOOTSTRAP_ADMIN_TOKEN}

TRMS_LLM_BASE_URL=${LLM_BASE_URL}
TRMS_LLM_API_KEY=${LLM_API_KEY}
TRMS_LLM_MODEL=${LLM_MODEL}
TRMS_LLM_TIMEOUT_SECONDS=1
TRMS_LLM_MAX_RETRIES=0

VITE_API_BASE_URL=/api
EOF
}

write_sample_file() {
  cat >"$SAMPLE_FILE" <<'EOF'
%PDF-1.4
1 0 obj
<< /Type /Catalog >>
endobj
trms-backup-restore-drill
EOF
}

mirror_bucket_to_dir() {
  docker run --rm \
    --network "${PROJECT_NAME}_default" \
    -v "$OBJECT_BACKUP_DIR:/backup" \
    --user "${HOST_UID}:${HOST_GID}" \
    -e HOME=/tmp \
    -e MC_CONFIG_DIR=/tmp/.mc \
    --entrypoint /bin/sh \
    minio/mc:latest \
    -ec "
      mc alias set trms ${MINIO_NETWORK_ENDPOINT} ${S3_ACCESS_KEY_ID} ${S3_SECRET_ACCESS_KEY}
      mc mirror --overwrite trms/${S3_BUCKET} /backup
    "
}

mirror_dir_to_bucket() {
  docker run --rm \
    --network "${PROJECT_NAME}_default" \
    -v "$OBJECT_BACKUP_DIR:/backup" \
    --user "${HOST_UID}:${HOST_GID}" \
    -e HOME=/tmp \
    -e MC_CONFIG_DIR=/tmp/.mc \
    --entrypoint /bin/sh \
    minio/mc:latest \
    -ec "
      mc alias set trms ${MINIO_NETWORK_ENDPOINT} ${S3_ACCESS_KEY_ID} ${S3_SECRET_ACCESS_KEY}
      mc mirror --overwrite /backup trms/${S3_BUCKET}
    "
}

list_bucket_objects() {
  docker run --rm \
    --network "${PROJECT_NAME}_default" \
    -e HOME=/tmp \
    -e MC_CONFIG_DIR=/tmp/.mc \
    --entrypoint /bin/sh \
    minio/mc:latest \
    -ec "
      mc alias set trms ${MINIO_NETWORK_ENDPOINT} ${S3_ACCESS_KEY_ID} ${S3_SECRET_ACCESS_KEY} >/dev/null
      mc find trms/${S3_BUCKET} --print
    "
}

read_bucket_object() {
  local storage_key="$1"
  docker run --rm \
    --network "${PROJECT_NAME}_default" \
    -e HOME=/tmp \
    -e MC_CONFIG_DIR=/tmp/.mc \
    --entrypoint /bin/sh \
    minio/mc:latest \
    -ec "
      mc alias set trms ${MINIO_NETWORK_ENDPOINT} ${S3_ACCESS_KEY_ID} ${S3_SECRET_ACCESS_KEY} >/dev/null
      mc cat trms/${S3_BUCKET}/${storage_key}
    "
}

psql_query() {
  local sql="$1"
  compose exec -T postgres psql \
    -U "$POSTGRES_USER" \
    -d "$POSTGRES_DB" \
    -At \
    -c "$sql"
}

main() {
  trap cleanup EXIT

  have_cmd docker || fail "未找到 docker"
  have_cmd curl || fail "未找到 curl"
  have_cmd python3 || fail "未找到 python3"

  create_env_file
  write_sample_file

  log "启动备份前演练环境"
  compose up -d postgres redis minio
  wait_for_postgres || fail "PostgreSQL 未在预期时间内就绪"
  compose up minio-init
  log "构建当前工作树对应的部署镜像"
  compose build api worker web migrate
  compose run --rm migrate
  compose up -d api web reverse-proxy
  wait_for_http "http://127.0.0.1:${PUBLIC_HTTP_PORT}/health" || fail "初始环境健康检查失败"

  log "创建最小任务、成员样本和上传材料"
  http_post_json \
    "${API_BASE_URL}/auth/bootstrap-admin" \
    '{"username":"admin","password":"backup-drill-admin-password","role":"admin","display_name":"Backup Drill Admin","actor_id":"admin-1"}' \
    -H "X-TRMS-Bootstrap-Token: ${BOOTSTRAP_ADMIN_TOKEN}" \
    >/dev/null

  admin_login_response="$(
    http_post_json \
      "${API_BASE_URL}/auth/login" \
      '{"username":"admin","password":"backup-drill-admin-password"}'
  )"
  ADMIN_TOKEN="$(printf '%s' "$admin_login_response" | json_get 'data["access_token"]')"

  member_register_response="$(
    http_post_json \
      "${API_BASE_URL}/auth/register" \
      '{"username":"member1","password":"backup-drill-member-password","role":"member","display_name":"Backup Drill Member","actor_id":"2250001","member_code":"2250001"}'
  )"
  MEMBER_TOKEN="$(printf '%s' "$member_register_response" | json_get 'data["access_token"]')"

  create_task_response="$(
    http_post_json \
      "${API_BASE_URL}/tasks" \
      '{"competition_name":"ICPC Asia Regional","competition_location":"Shanghai","competition_start_date":"2026-11-01","competition_end_date":"2026-11-03","deadline":"2026-12-01T00:00:00Z","member_ids":["2250001","2250002","2250003"],"fee_categories":["registration","railway","hotel"],"administrator_id":"admin-1","project_info":"ACM competition project","reimburser_info":"Lab reimbursement owner","invoice_title":"同济大学","tax_number":"12100000425006117D"}'
  )"
  TASK_ID="$(printf '%s' "$create_task_response" | json_get 'data["id"]')"

  http_patch_json \
    "${API_BASE_URL}/tasks/${TASK_ID}/status" \
    '{"target_status":"open"}' \
    -H "Authorization: Bearer ${ADMIN_TOKEN}" \
    >/dev/null

  upload_response="$(
    curl -fsS \
      -H "Authorization: Bearer ${MEMBER_TOKEN}" \
      -F "channel=web" \
      -F "material_type=invoice" \
      -F "files=@${SAMPLE_FILE};type=application/pdf" \
      "${API_BASE_URL}/tasks/${TASK_ID}/materials"
  )"
  MATERIAL_ID="$(printf '%s' "$upload_response" | json_get 'data["items"][0]["id"]')"
  STORAGE_KEY="$(printf '%s' "$upload_response" | json_get 'data["items"][0]["storage_key"]')"

  TASK_COUNT_BEFORE="$(psql_query 'SELECT count(*) FROM reimbursement_tasks;')"
  MATERIAL_COUNT_BEFORE="$(psql_query 'SELECT count(*) FROM materials;')"
  AUDIT_COUNT_BEFORE="$(psql_query 'SELECT count(*) FROM audit_logs;')"
  MATERIAL_AUDIT_BEFORE="$(
    psql_query "SELECT action || '|' || result || '|' || COALESCE(request_id, '') FROM audit_logs WHERE object_type = 'material' AND object_id = '${MATERIAL_ID}' ORDER BY created_at ASC LIMIT 1;"
  )"
  OBJECT_COUNT_BEFORE="$(list_bucket_objects | wc -l | tr -d ' ')"
  ORIGINAL_OBJECT_CONTENT="$(read_bucket_object "$STORAGE_KEY")"
  [[ -n "$MATERIAL_AUDIT_BEFORE" ]] || fail "备份前未找到材料审计记录"
  [[ "$OBJECT_COUNT_BEFORE" -ge 1 ]] || fail "备份前对象存储中没有找到样本对象"

  log "执行数据库逻辑备份"
  compose exec -T postgres pg_dump \
    -U "$POSTGRES_USER" \
    -d "$POSTGRES_DB" \
    -Fc >"$DB_BACKUP_FILE"
  [[ -s "$DB_BACKUP_FILE" ]] || fail "数据库备份文件为空"

  log "执行对象存储镜像备份"
  mirror_bucket_to_dir

  log "销毁卷并准备恢复"
  compose down -v

  log "恢复 PostgreSQL 与对象存储"
  compose up -d postgres redis minio
  wait_for_postgres || fail "恢复阶段 PostgreSQL 未在预期时间内就绪"
  compose up minio-init
  compose exec -T postgres pg_restore \
    -U "$POSTGRES_USER" \
    -d "$POSTGRES_DB" \
    --clean \
    --if-exists \
    <"$DB_BACKUP_FILE"
  mirror_dir_to_bucket

  log "启动恢复后的应用栈并执行核对"
  compose up -d api web reverse-proxy
  wait_for_http "http://127.0.0.1:${PUBLIC_HTTP_PORT}/health" || fail "恢复后健康检查失败"

  restored_member_login_response="$(
    http_post_json \
      "${API_BASE_URL}/auth/login" \
      '{"username":"member1","password":"backup-drill-member-password"}'
  )"
  RESTORED_MEMBER_TOKEN="$(printf '%s' "$restored_member_login_response" | json_get 'data["access_token"]')"

  restored_materials_response="$(
    http_get \
      "${API_BASE_URL}/tasks/${TASK_ID}/materials" \
      -H "Authorization: Bearer ${RESTORED_MEMBER_TOKEN}"
  )"
  RESTORED_STORAGE_KEY="$(printf '%s' "$restored_materials_response" | json_get 'data["items"][0]["storage_key"]')"
  RESTORED_MATERIAL_ID="$(printf '%s' "$restored_materials_response" | json_get 'data["items"][0]["id"]')"
  RESTORED_OBJECT_CONTENT="$(read_bucket_object "$RESTORED_STORAGE_KEY")"

  TASK_COUNT_AFTER="$(psql_query 'SELECT count(*) FROM reimbursement_tasks;')"
  MATERIAL_COUNT_AFTER="$(psql_query 'SELECT count(*) FROM materials;')"
  AUDIT_COUNT_AFTER="$(psql_query 'SELECT count(*) FROM audit_logs;')"
  MATERIAL_AUDIT_AFTER="$(
    psql_query "SELECT action || '|' || result || '|' || COALESCE(request_id, '') FROM audit_logs WHERE object_type = 'material' AND object_id = '${MATERIAL_ID}' ORDER BY created_at ASC LIMIT 1;"
  )"
  OBJECT_COUNT_AFTER="$(list_bucket_objects | wc -l | tr -d ' ')"
  [[ -n "$MATERIAL_AUDIT_AFTER" ]] || fail "恢复后未找到材料审计记录"

  [[ "$TASK_COUNT_BEFORE" == "$TASK_COUNT_AFTER" ]] || fail "恢复后任务数量不匹配"
  [[ "$MATERIAL_COUNT_BEFORE" == "$MATERIAL_COUNT_AFTER" ]] || fail "恢复后材料数量不匹配"
  [[ "$AUDIT_COUNT_BEFORE" == "$AUDIT_COUNT_AFTER" ]] || fail "恢复后审计数量不匹配"
  [[ "$OBJECT_COUNT_BEFORE" == "$OBJECT_COUNT_AFTER" ]] || fail "恢复后对象数量不匹配"
  [[ "$MATERIAL_ID" == "$RESTORED_MATERIAL_ID" ]] || fail "恢复后材料 ID 不匹配"
  [[ "$STORAGE_KEY" == "$RESTORED_STORAGE_KEY" ]] || fail "恢复后 storage_key 不匹配"
  [[ "$MATERIAL_AUDIT_BEFORE" == "$MATERIAL_AUDIT_AFTER" ]] || fail "恢复后材料审计记录不匹配"
  [[ "$ORIGINAL_OBJECT_CONTENT" == "$RESTORED_OBJECT_CONTENT" ]] || fail "恢复后对象内容不匹配"

  compose up -d worker >/dev/null

  DURATION_SECONDS="$(( $(date +%s) - START_TS ))"

  log "演练完成"
  printf 'project_name=%s\n' "$PROJECT_NAME"
  printf 'work_dir=%s\n' "$WORK_DIR"
  printf 'public_http_port=%s\n' "$PUBLIC_HTTP_PORT"
  printf 'task_id=%s\n' "$TASK_ID"
  printf 'material_id=%s\n' "$MATERIAL_ID"
  printf 'storage_key=%s\n' "$STORAGE_KEY"
  printf 'db_backup_file=%s\n' "$DB_BACKUP_FILE"
  printf 'object_backup_dir=%s\n' "$OBJECT_BACKUP_DIR"
  printf 'task_count_before=%s\n' "$TASK_COUNT_BEFORE"
  printf 'task_count_after=%s\n' "$TASK_COUNT_AFTER"
  printf 'material_count_before=%s\n' "$MATERIAL_COUNT_BEFORE"
  printf 'material_count_after=%s\n' "$MATERIAL_COUNT_AFTER"
  printf 'audit_count_before=%s\n' "$AUDIT_COUNT_BEFORE"
  printf 'audit_count_after=%s\n' "$AUDIT_COUNT_AFTER"
  printf 'object_count_before=%s\n' "$OBJECT_COUNT_BEFORE"
  printf 'object_count_after=%s\n' "$OBJECT_COUNT_AFTER"
  printf 'material_audit=%s\n' "$MATERIAL_AUDIT_AFTER"
  printf 'duration_seconds=%s\n' "$DURATION_SECONDS"
}

main "$@"
