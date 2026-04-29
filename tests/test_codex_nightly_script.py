from __future__ import annotations

import os
import subprocess
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "codex-nightly.sh"


def _write_executable(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    path.chmod(0o755)


def _init_test_repo(tmp_path: Path, tasks_content: str) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "TASKS.md").write_text(tasks_content, encoding="utf-8")
    (repo / ".gitignore").write_text(".codex-nightly/\n", encoding="utf-8")

    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True, text=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "add", "TASKS.md", ".gitignore"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "test: init repo"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return repo


def _install_fake_codex(tmp_path: Path) -> tuple[Path, Path]:
    bin_dir = tmp_path / "bin"
    state_dir = tmp_path / "state"
    bin_dir.mkdir()
    state_dir.mkdir()

    fake_codex = """#!/usr/bin/env python3
import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    args = sys.argv[1:]
    final_path = None
    for index, arg in enumerate(args):
        if arg == "--output-last-message" and index + 1 < len(args):
            final_path = Path(args[index + 1])
            break

    if final_path is not None:
        final_path.write_text("fake final message\\n", encoding="utf-8")

    state_dir = Path(os.environ["FAKE_CODEX_STATE_DIR"])
    count_path = state_dir / "count.txt"
    count = int(count_path.read_text(encoding="utf-8")) + 1 if count_path.exists() else 1
    count_path.write_text(str(count), encoding="utf-8")

    mode = os.environ["FAKE_CODEX_MODE"]
    repo = Path.cwd()
    tasks_path = repo / "TASKS.md"

    if mode == "complete_first_task":
        tasks_text = tasks_path.read_text(encoding="utf-8")
        tasks_path.write_text(tasks_text.replace("- [ ]", "- [x]", 1), encoding="utf-8")
        subprocess.run(["git", "add", "TASKS.md"], cwd=repo, check=True)
        subprocess.run(
            ["git", "commit", "-m", "test: complete pending task"],
            cwd=repo,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    elif mode == "dirty_change":
        (repo / "DIRTY.txt").write_text("dirty\\n", encoding="utf-8")
    elif mode == "leave_pending":
        pass
    else:
        raise SystemExit(f"unsupported mode: {mode}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
"""
    _write_executable(bin_dir / "codex", fake_codex)
    return bin_dir, state_dir


def _run_script(repo: Path, tmp_path: Path, mode: str) -> subprocess.CompletedProcess[str]:
    bin_dir, state_dir = _install_fake_codex(tmp_path)
    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    env["FAKE_CODEX_MODE"] = mode
    env["FAKE_CODEX_STATE_DIR"] = str(state_dir)
    return subprocess.run(
        ["bash", str(SCRIPT_PATH), str(repo)],
        cwd=repo,
        env=env,
        capture_output=True,
        text=True,
    )


def _combined_output(result: subprocess.CompletedProcess[str]) -> str:
    return f"{result.stdout}{result.stderr}"


def test_stops_immediately_when_no_pending_tasks(tmp_path: Path) -> None:
    repo = _init_test_repo(tmp_path, "# TASKS\n\n- [x] done\n")

    result = _run_script(repo, tmp_path, "leave_pending")

    assert result.returncode == 0
    output = _combined_output(result)
    assert "TASKS.md 中没有未完成任务，停止夜间执行" in output
    assert "开始第 1 轮" not in output
    assert not (tmp_path / "state" / "count.txt").exists()


def test_stops_after_round_when_pending_tasks_are_completed(tmp_path: Path) -> None:
    repo = _init_test_repo(tmp_path, "# TASKS\n\n- [ ] pending\n")

    result = _run_script(repo, tmp_path, "complete_first_task")

    assert result.returncode == 0
    output = _combined_output(result)
    assert "开始第 1 轮" in output
    assert "第 1 轮完成" in output
    assert "第 1 轮后 TASKS.md 中已无未完成任务，停止夜间执行" in output
    assert (tmp_path / "state" / "count.txt").read_text(encoding="utf-8") == "1"
    assert "- [ ]" not in (repo / "TASKS.md").read_text(encoding="utf-8")


def test_stops_when_pending_task_snapshot_does_not_change(tmp_path: Path) -> None:
    repo = _init_test_repo(tmp_path, "# TASKS\n\n- [ ] pending\n")

    result = _run_script(repo, tmp_path, "leave_pending")

    assert result.returncode == 0
    output = _combined_output(result)
    assert "第 1 轮完成" in output
    assert "第 1 轮后未完成任务列表无变化，停止夜间执行" in output
    assert (tmp_path / "state" / "count.txt").read_text(encoding="utf-8") == "1"


def test_keeps_dirty_worktree_guard(tmp_path: Path) -> None:
    repo = _init_test_repo(tmp_path, "# TASKS\n\n- [ ] pending\n")

    result = _run_script(repo, tmp_path, "dirty_change")

    assert result.returncode == 1
    output = _combined_output(result)
    assert "第 1 轮结束后仍存在未提交改动，请查看 git status" in output
    assert "DIRTY.txt" in output
