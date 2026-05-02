#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

FORCE_FULL_VERIFY=0
declare -a EXPLICIT_CHANGED_FILES=()
declare -a CHANGED_SHELL_FILES=()

log() {
  printf '[verify] %s\n' "$*"
}

have_cmd() {
  command -v "$1" >/dev/null 2>&1
}

resolve_cpu_count() {
  if [[ -n "${TRMS_VERIFY_CPU_COUNT:-}" ]]; then
    printf '%s\n' "$TRMS_VERIFY_CPU_COUNT"
    return
  fi

  if have_cmd nproc; then
    nproc
    return
  fi

  if have_cmd getconf; then
    getconf _NPROCESSORS_ONLN
    return
  fi

  printf '1\n'
}

resolve_test_worker_count() {
  local cpu_count=1
  local worker_count=1

  if [[ -n "${TRMS_VERIFY_TEST_WORKERS:-}" ]]; then
    printf '%s\n' "$TRMS_VERIFY_TEST_WORKERS"
    return
  fi

  cpu_count="$(resolve_cpu_count)"
  if [[ "$cpu_count" -le 1 ]]; then
    printf '1\n'
    return
  fi

  worker_count=$(((cpu_count + 1) / 2))
  if [[ "$worker_count" -lt 2 ]]; then
    worker_count=2
  fi

  printf '%s\n' "$worker_count"
}

usage() {
  cat <<'EOF'
用法：
  ./scripts/verify.sh [--all] [--files <path>...]

选项：
  --all            忽略改动范围探测，执行完整验证
  --files <path>   使用显式文件列表推导需要运行的校验集
EOF
}

parse_args() {
  while [[ "$#" -gt 0 ]]; do
    case "$1" in
      --all)
        FORCE_FULL_VERIFY=1
        shift
        ;;
      --files)
        shift
        while [[ "$#" -gt 0 && "$1" != --* ]]; do
          EXPLICIT_CHANGED_FILES+=("$1")
          shift
        done
        ;;
      --help|-h)
        usage
        exit 0
        ;;
      *)
        log "未知参数：$1"
        usage
        exit 2
        ;;
    esac
  done
}

is_doc_only_path() {
  local path="$1"
  case "$path" in
    AGENTS.md|README.md|TASKS.md|WORKLOG.md|BLOCKERS.md|UX_TEST_REPORT.md|docs/*|*.md)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

collect_git_changed_files() {
  local -A seen=()
  local path=""

  while IFS= read -r -d '' path; do
    seen["$path"]=1
  done < <(git diff --name-only -z --cached)

  while IFS= read -r -d '' path; do
    seen["$path"]=1
  done < <(git diff --name-only -z)

  while IFS= read -r -d '' path; do
    seen["$path"]=1
  done < <(git ls-files --others --exclude-standard -z)

  for path in "${!seen[@]}"; do
    printf '%s\0' "$path"
  done
}

enable_suite() {
  local suite="$1"
  ENABLED_SUITES["$suite"]=1
}

classify_changed_files() {
  local -n files_ref="$1"
  local -n enabled_ref="$2"
  local doc_only=1
  local path=""
  local classified=0

  CHANGED_SHELL_FILES=()
  UNKNOWN_CHANGE=0
  ENABLED_SUITES=()

  for path in "${files_ref[@]}"; do
    [[ -n "$path" ]] || continue
    if is_doc_only_path "$path"; then
      continue
    fi

    doc_only=0
    case "$path" in
      scripts/*.sh|*.sh)
        enabled_ref["shell"]=1
        CHANGED_SHELL_FILES+=("$path")
        classified=1
        ;;
      pyproject.toml|uv.lock|alembic.ini|alembic/*|src/*|tests/*|scripts/*.py)
        enabled_ref["python_compile"]=1
        enabled_ref["python_pytest"]=1
        classified=1
        ;;
      web/*|web/package.json|web/package-lock.json)
        enabled_ref["web_node_lint"]=1
        enabled_ref["web_node_test"]=1
        enabled_ref["web_node_build"]=1
        classified=1
        ;;
      package.json|package-lock.json)
        enabled_ref["root_node_lint"]=1
        enabled_ref["root_node_test"]=1
        enabled_ref["root_node_build"]=1
        classified=1
        ;;
      deploy/*|.env.example|.env.development.example)
        enabled_ref["deploy"]=1
        classified=1
        ;;
      Cargo.toml|Cargo.lock|*.rs)
        enabled_ref["rust"]=1
        classified=1
        ;;
      go.mod|go.sum|*.go)
        enabled_ref["go"]=1
        classified=1
        ;;
      CMakeLists.txt|*.cmake)
        enabled_ref["cmake"]=1
        classified=1
        ;;
      Makefile|*.mk)
        enabled_ref["make"]=1
        classified=1
        ;;
      *)
        UNKNOWN_CHANGE=1
        ;;
    esac
  done

  if [[ "$doc_only" -eq 1 ]]; then
    VERIFY_SCOPE="docs_only"
    return
  fi

  if [[ "$classified" -eq 0 || "$UNKNOWN_CHANGE" -eq 1 ]]; then
    VERIFY_SCOPE="full"
    return
  fi

  VERIFY_SCOPE="scoped"
}

resolve_python_cmd() {
  local python_cmd=""

  if have_cmd uv && [[ -f uv.lock ]]; then
    python_cmd="uv run python"
  elif have_cmd python3; then
    python_cmd="python3"
  elif have_cmd python; then
    python_cmd="python"
  else
    return 1
  fi

  printf '%s\n' "$python_cmd"
}

run_python_compile_checks() {
  local python_cmd=""
  python_cmd="$(resolve_python_cmd)" || {
    log "跳过 Python 编译/迁移检查：未找到 python、python3 或 uv"
    return
  }

  log "运行 Python 语法编译检查"
  # shellcheck disable=SC2086
  $python_cmd -m compileall src tests

  if [[ -f alembic.ini ]]; then
    local -a alembic_cmd=()

    if have_cmd uv && [[ -f uv.lock ]]; then
      alembic_cmd=(uv run alembic)
    elif have_cmd python3 && python3 -m alembic --help >/dev/null 2>&1; then
      alembic_cmd=(python3 -m alembic)
    elif have_cmd python && python -m alembic --help >/dev/null 2>&1; then
      alembic_cmd=(python -m alembic)
    fi

    if [[ "${#alembic_cmd[@]}" -gt 0 ]]; then
      local migration_tmp_dir=""
      local migration_database_url=""
      migration_tmp_dir="$(mktemp -d)"
      migration_database_url="sqlite:///${migration_tmp_dir}/verify-migrations.db"

      log "运行 Alembic 迁移脚本验证"
      DATABASE_URL="$migration_database_url" "${alembic_cmd[@]}" upgrade head
      DATABASE_URL="$migration_database_url" "${alembic_cmd[@]}" downgrade base
      DATABASE_URL="$migration_database_url" "${alembic_cmd[@]}" upgrade head

      rm -rf "$migration_tmp_dir"
    else
      log "跳过 Alembic 检查：当前环境未安装 alembic"
    fi
  fi

}

run_shell_checks() {
  local -a shell_files=()
  local path=""

  if [[ "${#CHANGED_SHELL_FILES[@]}" -gt 0 ]]; then
    shell_files=("${CHANGED_SHELL_FILES[@]}")
  elif [[ -f scripts/verify.sh ]]; then
    shell_files=("scripts/verify.sh")
  fi

  if ! have_cmd bash; then
    log "跳过 Shell 检查：未找到 bash"
    return
  fi

  for path in "${shell_files[@]}"; do
    if [[ -f "$path" ]]; then
      log "运行 bash -n $path"
      bash -n "$path"
    fi
  done

  if have_cmd shellcheck && [[ "${#shell_files[@]}" -gt 0 ]]; then
    log "运行 shellcheck ${shell_files[*]}"
    shellcheck "${shell_files[@]}"
  else
    log "跳过 shellcheck：未找到 shellcheck 或无待检查脚本"
  fi
}

run_pytest_checks() {
  local python_cmd=""
  local pytest_workers=1

  if [[ ! -d tests ]]; then
    log "跳过 pytest：未找到 tests 目录"
    return
  fi

  python_cmd="$(resolve_python_cmd)" || {
    log "跳过 pytest：未找到 python、python3 或 uv"
    return
  }

  pytest_workers="$(resolve_test_worker_count)"
  if have_cmd uv && [[ -f uv.lock ]]; then
    if [[ "$pytest_workers" -gt 1 ]]; then
      log "运行 pytest（并行 worker=${pytest_workers}）"
      uv run pytest -n "$pytest_workers" --dist loadfile
    else
      log "运行 pytest（当前环境仅使用单 worker）"
      uv run pytest
    fi
  elif "$python_cmd" -m pytest --version >/dev/null 2>&1; then
    if [[ "$pytest_workers" -gt 1 ]]; then
      log "运行 pytest（并行 worker=${pytest_workers}）"
      # shellcheck disable=SC2086
      $python_cmd -m pytest -n "$pytest_workers" --dist loadfile
    else
      log "运行 pytest（当前环境仅使用单 worker）"
      # shellcheck disable=SC2086
      $python_cmd -m pytest
    fi
  else
    log "跳过 pytest：当前环境未安装 pytest"
  fi
}

run_node_script_check() {
  local target_dir="$1"
  local label="$2"
  local script_name="$3"
  local log_label="$4"
  local test_workers=1

  if ! have_cmd npm; then
    log "跳过 Node 检查：未找到 npm"
    return
  fi

  log "运行 ${label} ${log_label}"
  (
    cd "$target_dir"
    case "$script_name" in
      lint)
        npm run lint --if-present
        ;;
      test)
        test_workers="$(resolve_test_worker_count)"
        if [[ "$test_workers" -gt 1 ]]; then
          npm test --if-present -- --maxWorkers="$test_workers"
        else
          npm test --if-present
        fi
        ;;
      build)
        npm run build --if-present
        ;;
      *)
        log "内部错误：未知 Node 脚本 $script_name"
        return 2
        ;;
    esac
  )
}

run_deployment_checks() {
  if [[ ! -f deploy/docker-compose.yml || ! -f .env.example ]]; then
    return
  fi

  if ! have_cmd docker || ! docker compose version >/dev/null 2>&1; then
    log "跳过 Docker Compose 检查：未找到 docker compose"
    return
  fi

  log "运行 Docker Compose 配置检查"
  docker compose --env-file .env.example -f deploy/docker-compose.yml config >/dev/null
}

run_rust_checks() {
  if ! have_cmd cargo; then
    log "跳过 Rust 检查：未找到 cargo"
    return
  fi

  log "运行 cargo fmt --check"
  cargo fmt --check
  log "运行 cargo test"
  cargo test
}

run_go_checks() {
  if ! have_cmd go; then
    log "跳过 Go 检查：未找到 go"
    return
  fi

  log "运行 go test ./..."
  go test ./...
}

run_cmake_checks() {
  if ! have_cmd cmake; then
    log "跳过 CMake 检查：未找到 cmake"
    return
  fi

  local build_dir="build/verify"
  log "运行 CMake configure/build"
  cmake -S . -B "$build_dir"
  cmake --build "$build_dir"

  if have_cmd ctest; then
    log "运行 ctest"
    ctest --test-dir "$build_dir" --output-on-failure
  else
    log "跳过 ctest：未找到 ctest"
  fi
}

run_make_checks() {
  if ! have_cmd make; then
    log "跳过 Makefile 检查：未找到 make"
    return
  fi

  if make -n test >/dev/null 2>&1; then
    log "运行 make test"
    make test
  else
    log "运行 make"
    make
  fi
}

run_suite() {
  local suite="$1"
  case "$suite" in
    shell)
      run_shell_checks
      ;;
    python_compile)
      run_python_compile_checks
      ;;
    python_pytest)
      run_pytest_checks
      ;;
    root_node_lint)
      run_node_script_check "." "根目录" "lint" "npm run lint"
      ;;
    root_node_test)
      run_node_script_check "." "根目录" "test" "npm test"
      ;;
    root_node_build)
      run_node_script_check "." "根目录" "build" "npm run build"
      ;;
    web_node_lint)
      run_node_script_check "web" "web 前端" "lint" "npm run lint"
      ;;
    web_node_test)
      run_node_script_check "web" "web 前端" "test" "npm test"
      ;;
    web_node_build)
      run_node_script_check "web" "web 前端" "build" "npm run build"
      ;;
    deploy)
      run_deployment_checks
      ;;
    rust)
      run_rust_checks
      ;;
    go)
      run_go_checks
      ;;
    cmake)
      run_cmake_checks
      ;;
    make)
      run_make_checks
      ;;
    *)
      log "内部错误：未知校验套件 $suite"
      return 2
      ;;
  esac
}

run_selected_suites() {
  local -a suites=("$@")
  local tmp_dir=""
  local -a pids=()
  local -a names=()
  local -a logs=()
  local idx=0
  local status=0
  local failed=0

  if [[ "${#suites[@]}" -eq 0 ]]; then
    log "未识别到需要执行的构建校验，仅运行通用检查"
    return
  fi

  if [[ "${#suites[@]}" -eq 1 ]]; then
    run_suite "${suites[0]}"
    return
  fi

  tmp_dir="$(mktemp -d)"
  for idx in "${!suites[@]}"; do
    names[idx]="${suites[idx]}"
    logs[idx]="${tmp_dir}/${suites[idx]}.log"
    (
      run_suite "${suites[idx]}"
    ) >"${logs[idx]}" 2>&1 &
    pids[idx]="$!"
  done

  for idx in "${!pids[@]}"; do
    status=0
    wait "${pids[idx]}" || status="$?"
    cat "${logs[idx]}"
    if [[ "$status" -ne 0 ]]; then
      log "检查失败：${names[idx]}"
      failed=1
    fi
  done

  rm -rf "$tmp_dir"

  if [[ "$failed" -ne 0 ]]; then
    return 1
  fi
}

build_full_suite_selection() {
  [[ -f scripts/verify.sh ]] && enable_suite "shell"
  if [[ -f pyproject.toml || -f requirements.txt || -f setup.py ]]; then
    enable_suite "python_compile"
    enable_suite "python_pytest"
  fi
  if [[ -f package.json ]]; then
    enable_suite "root_node_lint"
    enable_suite "root_node_test"
    enable_suite "root_node_build"
  fi
  if [[ -f web/package.json ]]; then
    enable_suite "web_node_lint"
    enable_suite "web_node_test"
    enable_suite "web_node_build"
  fi
  [[ -f deploy/docker-compose.yml || -f .env.example ]] && enable_suite "deploy"
  [[ -f Cargo.toml ]] && enable_suite "rust"
  [[ -f go.mod ]] && enable_suite "go"
  [[ -f CMakeLists.txt ]] && enable_suite "cmake"
  [[ -f Makefile ]] && enable_suite "make"
}

build_selected_suite_list() {
  local -n enabled_ref="$1"
  local -a ordered=()
  local suite=""

  for suite in \
    shell \
    python_compile \
    python_pytest \
    root_node_lint \
    root_node_test \
    root_node_build \
    web_node_lint \
    web_node_test \
    web_node_build \
    deploy \
    rust \
    go \
    cmake \
    make; do
    if [[ -n "${enabled_ref[$suite]:-}" ]]; then
      ordered+=("$suite")
    fi
  done

  printf '%s\n' "${ordered[@]}"
}

declare -A ENABLED_SUITES=()
declare -a CHANGED_FILES=()
VERIFY_SCOPE="full"
UNKNOWN_CHANGE=0

parse_args "$@"

if [[ "$FORCE_FULL_VERIFY" -eq 1 ]]; then
  VERIFY_SCOPE="full"
elif [[ "${#EXPLICIT_CHANGED_FILES[@]}" -gt 0 ]]; then
  CHANGED_FILES=("${EXPLICIT_CHANGED_FILES[@]}")
  classify_changed_files CHANGED_FILES ENABLED_SUITES
elif have_cmd git && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  while IFS= read -r -d '' path; do
    CHANGED_FILES+=("$path")
  done < <(collect_git_changed_files)

  if [[ "${#CHANGED_FILES[@]}" -gt 0 ]]; then
    classify_changed_files CHANGED_FILES ENABLED_SUITES
  fi
fi

if [[ "$VERIFY_SCOPE" == "docs_only" ]]; then
  log "仅检测到文档改动，跳过仓库级验证"
  exit 0
fi

if [[ "$VERIFY_SCOPE" == "full" ]]; then
  ENABLED_SUITES=()
  build_full_suite_selection
else
  log "按改动范围执行相关校验"
fi

mapfile -t SELECTED_SUITES < <(build_selected_suite_list ENABLED_SUITES)
run_selected_suites "${SELECTED_SUITES[@]}"

if have_cmd git && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  log "运行 git diff --check"
  git diff --check
else
  log "跳过 git diff --check：当前目录不是 git 仓库或未找到 git"
fi

log "验证完成"
