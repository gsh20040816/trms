#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="${TRMS_PROD_COMPOSE_FILE:-$ROOT_DIR/deploy/docker-compose.yml}"
ENV_FILE="${TRMS_PROD_ENV_FILE:-$ROOT_DIR/.env}"

log() {
  printf '[trms-prod] %s\n' "$*"
}

fail() {
  log "失败：$*"
  exit 1
}

have_cmd() {
  command -v "$1" >/dev/null 2>&1
}

usage() {
  cat <<'EOF'
用法：
  ./scripts/trms-prod.sh <command> [args...]

命令：
  start           按生产基线启动依赖、执行迁移并拉起 api/worker/web
  stop            停止当前 Compose 项目中的全部服务，但保留容器和卷
  down            停止并移除当前 Compose 项目的容器与网络
  status          查看当前 Compose 服务状态
  logs [service]  查看日志；不传 service 时默认跟随 api worker web postgres minio

可选环境变量：
  TRMS_PROD_ENV_FILE       覆盖默认环境文件路径，默认 ./.env
  TRMS_PROD_COMPOSE_FILE   覆盖默认 Compose 文件路径，默认 ./deploy/docker-compose.yml
EOF
}

compose() {
  docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"
}

trim() {
  local value="$1"
  value="${value#"${value%%[![:space:]]*}"}"
  value="${value%"${value##*[![:space:]]}"}"
  printf '%s\n' "$value"
}

strip_wrapping_quotes() {
  local value="$1"
  if [[ "$value" == \"*\" && "$value" == *\" ]]; then
    value="${value:1:${#value}-2}"
  elif [[ "$value" == \'*\' && "$value" == *\' ]]; then
    value="${value:1:${#value}-2}"
  fi
  printf '%s\n' "$value"
}

read_env_file_value() {
  local key="$1"
  awk -F= -v wanted_key="$key" '
    /^[[:space:]]*#/ { next }
    /^[[:space:]]*$/ { next }
    {
      raw_key=$1
      gsub(/^[[:space:]]+|[[:space:]]+$/, "", raw_key)
      if (raw_key != wanted_key) {
        next
      }
      value=substr($0, index($0, "=") + 1)
      print value
    }
  ' "$ENV_FILE" | tail -n 1
}

resolve_config_value() {
  local key="$1"
  local value="${!key:-}"

  if [[ -n "$value" ]]; then
    trim "$value"
    return
  fi

  value="$(read_env_file_value "$key")"
  value="$(trim "$value")"
  value="$(strip_wrapping_quotes "$value")"
  printf '%s\n' "$value"
}

ensure_prerequisites() {
  [[ -f "$COMPOSE_FILE" ]] || fail "未找到 Compose 文件：$COMPOSE_FILE"
  [[ -f "$ENV_FILE" ]] || fail "未找到环境文件：$ENV_FILE"

  have_cmd docker || fail "未找到 docker 命令"
  docker compose version >/dev/null 2>&1 || fail "当前环境不可用 docker compose"
}

ensure_production_env() {
  local trms_env=""

  trms_env="$(resolve_config_value "TRMS_ENV")"
  [[ -n "$trms_env" ]] || fail "未在 $ENV_FILE 或当前环境中找到 TRMS_ENV"
  [[ "$trms_env" == "production" ]] || fail "TRMS_ENV=$trms_env；生产脚本只允许用于 production"
}

start_stack() {
  ensure_prerequisites
  ensure_production_env

  log "启动基础依赖：postgres redis minio"
  compose up -d postgres redis minio

  log "初始化 MinIO bucket"
  compose up minio-init

  log "执行数据库迁移"
  compose run --rm migrate

  log "启动应用服务：api worker web"
  compose up -d api worker web

  log "当前服务状态"
  compose ps
}

stop_stack() {
  ensure_prerequisites
  ensure_production_env

  log "停止当前 Compose 项目中的服务"
  compose stop
}

down_stack() {
  ensure_prerequisites
  ensure_production_env

  log "停止并移除当前 Compose 项目中的容器与网络"
  compose down
}

show_status() {
  ensure_prerequisites
  ensure_production_env

  compose ps
}

show_logs() {
  ensure_prerequisites
  ensure_production_env

  if [[ "$#" -gt 0 ]]; then
    compose logs -f "$@"
    return
  fi

  compose logs -f api worker web postgres minio
}

main() {
  local command="${1:-}"

  case "$command" in
    start)
      shift
      [[ "$#" -eq 0 ]] || fail "start 不接受额外参数"
      start_stack
      ;;
    stop)
      shift
      [[ "$#" -eq 0 ]] || fail "stop 不接受额外参数"
      stop_stack
      ;;
    down)
      shift
      [[ "$#" -eq 0 ]] || fail "down 不接受额外参数"
      down_stack
      ;;
    status)
      shift
      [[ "$#" -eq 0 ]] || fail "status 不接受额外参数"
      show_status
      ;;
    logs)
      shift
      show_logs "$@"
      ;;
    --help|-h|help)
      usage
      ;;
    "")
      usage
      exit 2
      ;;
    *)
      fail "未知命令：$command"
      ;;
  esac
}

main "$@"
