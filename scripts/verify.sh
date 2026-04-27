#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

log() {
  printf '[verify] %s\n' "$*"
}

have_cmd() {
  command -v "$1" >/dev/null 2>&1
}

run_if_cmd() {
  local cmd="$1"
  shift
  if have_cmd "$cmd"; then
    "$cmd" "$@"
  else
    log "跳过：未找到命令 $cmd"
  fi
}

run_python_checks() {
  local python_cmd=""

  if have_cmd uv && [[ -f uv.lock ]]; then
    python_cmd="uv run python"
  elif have_cmd python3; then
    python_cmd="python3"
  elif have_cmd python; then
    python_cmd="python"
  else
    log "跳过 Python 检查：未找到 python、python3 或 uv"
    return
  fi

  log "运行 Python 语法编译检查"
  # shellcheck disable=SC2086
  $python_cmd -m compileall src tests

  if [[ -d tests ]]; then
    if have_cmd uv && [[ -f uv.lock ]]; then
      log "运行 pytest"
      uv run pytest
    elif "$python_cmd" -m pytest --version >/dev/null 2>&1; then
      log "运行 pytest"
      # shellcheck disable=SC2086
      $python_cmd -m pytest
    else
      log "跳过 pytest：当前环境未安装 pytest"
    fi
  fi
}

run_node_checks() {
  local target_dir="$1"
  local label="$2"

  if ! have_cmd npm; then
    log "跳过 Node 检查：未找到 npm"
    return
  fi

  log "运行 ${label} npm lint/test/build（如果存在）"
  (
    cd "$target_dir"
    npm run lint --if-present
    npm test --if-present
    npm run build --if-present
  )
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

recognized=0

if [[ -f pyproject.toml || -f requirements.txt || -f setup.py ]]; then
  recognized=1
  run_python_checks
fi

if [[ -f package.json ]]; then
  recognized=1
  run_node_checks "." "根目录"
fi

if [[ -f web/package.json ]]; then
  recognized=1
  run_node_checks "web" "web 前端"
fi

if [[ -f Cargo.toml ]]; then
  recognized=1
  run_rust_checks
fi

if [[ -f go.mod ]]; then
  recognized=1
  run_go_checks
fi

if [[ -f CMakeLists.txt ]]; then
  recognized=1
  run_cmake_checks
fi

if [[ -f Makefile ]]; then
  recognized=1
  run_make_checks
fi

if [[ "$recognized" -eq 0 ]]; then
  log "未识别到常见构建系统，仅运行通用检查"
fi

if have_cmd git && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  log "运行 git diff --check"
  git diff --check
else
  log "跳过 git diff --check：当前目录不是 git 仓库或未找到 git"
fi

log "验证完成"
