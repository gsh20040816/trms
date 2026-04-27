#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="${1:-$(pwd)}"
MAX_ROUNDS="${MAX_ROUNDS:-30}"

log() {
  printf '[codex-nightly] %s\n' "$*"
}

die() {
  printf '[codex-nightly] ERROR: %s\n' "$*" >&2
  exit 1
}

have_cmd() {
  command -v "$1" >/dev/null 2>&1
}

cd "$REPO_DIR"

if ! have_cmd git; then
  die "未找到 git，无法检查工作区状态"
fi

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  die "当前路径不是 git 仓库：$REPO_DIR"
fi

if ! have_cmd codex; then
  die "未找到 codex 命令，请先在运行环境中安装或配置 Codex CLI"
fi

if [[ ! -f TASKS.md ]]; then
  die "缺少 TASKS.md，无法读取任务队列"
fi

mkdir -p .codex-nightly/logs

round=1
while [[ "$round" -le "$MAX_ROUNDS" ]]; do
  if [[ -f .codex-nightly/STOP ]]; then
    log "检测到 .codex-nightly/STOP，停止夜间执行"
    exit 0
  fi

  if ! grep -q '^- \[ \]' TASKS.md; then
    log "TASKS.md 中没有未完成任务，停止夜间执行"
    exit 0
  fi

  timestamp="$(date '+%Y%m%d-%H%M%S')"
  log_file=".codex-nightly/logs/round-${round}-${timestamp}.log"
  final_file=".codex-nightly/logs/round-${round}-${timestamp}.final.md"

  log "开始第 $round 轮，日志：$log_file"

  prompt="$(cat <<'PROMPT'
你是本仓库的 Codex 夜间工作代理。请严格按以下规则执行本轮工作：

1. 先阅读 AGENTS.md、TASKS.md、WORKLOG.md、BLOCKERS.md、README.md 和 docs/ 下的需求/架构文档。
2. 选择 TASKS.md 中第一个未完成且未被 BLOCKERS.md 阻塞的任务。
3. 本轮只完成这一个最小可验证任务；不要实现其他业务功能，不要做无关重构。
4. 如果任务过大，先拆分 TASKS.md，并只提交拆分任务这一项工作。
5. 如果遇到不明确但不阻塞的问题，做保守假设并写入 WORKLOG.md。
6. 如果遇到阻塞，写入 BLOCKERS.md，更新 WORKLOG.md，然后结束本轮。
7. 修改后运行 ./scripts/verify.sh。
8. 验证失败时优先修复；如果无法修复，把失败原因写入 WORKLOG.md 和 BLOCKERS.md。
9. 验证通过后更新 TASKS.md 和 WORKLOG.md，执行 git add 和 git commit。
10. commit message 使用英文，格式为 <type>: <message>。
11. 最终输出本轮摘要、验证结果、commit 哈希；如果没有 commit，说明原因。
PROMPT
)"

  set +e
  codex --ask-for-approval never exec \
    --sandbox workspace-write \
    --output-last-message "$final_file" \
    "$prompt" >"$log_file" 2>&1
  codex_status=$?
  set -e

  if [[ "$codex_status" -ne 0 ]]; then
    log "第 $round 轮 Codex 执行失败，退出码：$codex_status"
    log "请查看日志：$log_file"
    exit "$codex_status"
  fi

  if [[ -n "$(git status --porcelain)" ]]; then
    log "第 $round 轮结束后仍存在未提交改动，请查看 git status"
    git status --short | tee -a "$log_file"
    exit 1
  fi

  log "第 $round 轮完成"
  round=$((round + 1))
done

log "达到最大轮数 MAX_ROUNDS=$MAX_ROUNDS，停止夜间执行"
