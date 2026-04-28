import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { useAuthSession } from "./auth-store";
import { ApiErrorNotice } from "../components/ApiErrorNotice";
import { trmsApi } from "../lib/api/trms";
import type { ReimbursementTask, TaskStatus } from "../lib/api/types";

type MemberTaskListState =
  | { status: "loading" }
  | { status: "error"; error: unknown }
  | { status: "ready"; items: ReimbursementTask[] };

const TASK_STATUS_LABELS: Record<TaskStatus, string> = {
  draft: "草稿",
  open: "开放提交",
  closed: "已关闭",
  reviewing: "复核中",
  ready_to_export: "可导出",
  completed: "已归档",
};

function formatTaskStatus(status: TaskStatus) {
  return TASK_STATUS_LABELS[status];
}

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function formatDateRange(task: ReimbursementTask) {
  return `${task.competition_start_date} 至 ${task.competition_end_date}`;
}

export function MemberTaskListPage() {
  const session = useAuthSession();
  const [state, setState] = useState<MemberTaskListState>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;

    async function loadVisibleTasks() {
      if (!session || session.role !== "member") {
        return;
      }

      setState({ status: "loading" });

      try {
        const allTasks = await trmsApi.listTasks();
        const visibleTasks = allTasks.filter((task) => task.member_ids.includes(session.actorId));

        if (cancelled) {
          return;
        }

        setState({
          status: "ready",
          items: visibleTasks,
        });
      } catch (error) {
        if (cancelled) {
          return;
        }

        setState({
          status: "error",
          error,
        });
      }
    }

    void loadVisibleTasks();

    return () => {
      cancelled = true;
    };
  }, [session]);

  if (!session || session.role !== "member") {
    return null;
  }

  const visibleTasks = state.status === "ready" ? state.items : [];

  return (
    <div className="page-stack">
      <section className="status-card auth-panel">
        <p className="eyebrow">Member Tasks</p>
        <h2>成员可提交任务</h2>
        <p>
          当前页先承接成员侧最小闭环入口，只展示当前 mock 成员可参与的报销任务，帮助成员先定位自己应向哪个比赛任务提交材料。
        </p>
        <p className="status-note">
          在真实鉴权和“已参与任务”聚合接口接入前，前端先按 `task.member_ids` 是否包含当前成员
          `{session.actorId}` 做保守过滤，不额外暴露无关任务。
        </p>
      </section>

      {state.status === "loading" ? (
        <section className="status-card">
          <p className="eyebrow">Loading</p>
          <h2>正在加载成员可见任务</h2>
          <p>正在读取当前成员可参与的比赛报销任务，请稍候。</p>
        </section>
      ) : null}

      {state.status === "error" ? <ApiErrorNotice error={state.error} /> : null}

      {state.status === "ready" && visibleTasks.length === 0 ? (
        <section className="status-card">
          <p className="eyebrow">Empty</p>
          <h2>当前没有可见报销任务</h2>
          <p>
            当前 mock 成员身份尚未匹配到任何 `member_ids` 包含 {session.actorId}
            的任务；后续如果管理员创建并发布包含你的比赛任务，会在这里显示。
          </p>
        </section>
      ) : null}

      {state.status === "ready" && visibleTasks.length > 0 ? (
        <section className="task-card-grid" aria-label="成员可见任务列表">
          {visibleTasks.map((task) => (
            <article key={task.id} className="task-card">
              <div className="task-card-header">
                <div>
                  <p className="task-card-id">任务编号 {task.id}</p>
                  <h3>{task.competition_name}</h3>
                </div>
                <span className={`status-chip task-status-chip task-status-${task.status}`}>
                  {formatTaskStatus(task.status)}
                </span>
              </div>
              <dl className="task-meta-grid">
                <div>
                  <dt>比赛时间</dt>
                  <dd>{formatDateRange(task)}</dd>
                </div>
                <div>
                  <dt>截止时间</dt>
                  <dd>{formatDateTime(task.deadline)}</dd>
                </div>
                <div>
                  <dt>任务状态</dt>
                  <dd>{formatTaskStatus(task.status)}</dd>
                </div>
                <div>
                  <dt>当前成员</dt>
                  <dd>{session.displayName}</dd>
                </div>
              </dl>
              <div className="inline-actions">
                {task.status === "open" ? (
                  <Link
                    className="route-link"
                    to={`/member/materials/upload?taskId=${encodeURIComponent(task.id)}`}
                  >
                    上传材料
                  </Link>
                ) : (
                  <span className="status-note">当前任务未处于开放提交状态，暂不能从成员端继续上传材料。</span>
                )}
              </div>
            </article>
          ))}
        </section>
      ) : null}
    </div>
  );
}
