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

type MemberActionHint = {
  title: string;
  summary: string;
  actions: string[];
};

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

function getTaskSortPriority(status: TaskStatus) {
  switch (status) {
    case "open":
      return 0;
    case "reviewing":
      return 1;
    case "closed":
      return 2;
    case "ready_to_export":
      return 3;
    case "completed":
      return 4;
    case "draft":
    default:
      return 5;
  }
}

function buildActionHint(task: ReimbursementTask): MemberActionHint {
  if (task.status === "open") {
    return {
      title: "先上传或补齐材料",
      summary: "这是当前最重要的动作。开放提交阶段不需要先理解所有规则，先把相关发票和附件交上来。",
      actions: ["上传材料", "查看材料状态", "查看缺失材料"],
    };
  }
  if (task.status === "closed" || task.status === "reviewing") {
    return {
      title: "先看缺失项和费用确认",
      summary: "提交阶段已结束，接下来应查看识别结果、缺失材料和个人费用明细是否需要补充或确认。",
      actions: ["查看材料状态", "查看缺失材料", "确认费用明细"],
    };
  }
  if (task.status === "ready_to_export") {
    return {
      title: "等待管理员导出",
      summary: "当前任务已满足导出前条件，你主要需要保留查询入口，必要时再回看材料和费用明细。",
      actions: ["查看材料状态", "确认费用明细"],
    };
  }
  if (task.status === "completed") {
    return {
      title: "任务已归档",
      summary: "当前任务已完成归档，后续主要用于追溯和核对，不再继续补交材料。",
      actions: ["查看材料状态", "确认费用明细"],
    };
  }
  return {
    title: "等待管理员发布",
    summary: "草稿态任务暂未开放成员操作，先等待管理员补齐配置并发布。",
    actions: ["查看材料状态"],
  };
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

  const visibleTasks = state.status === "ready" ? state.items : [];
  const sortedVisibleTasks = [...visibleTasks].sort((left, right) => {
    const priorityDifference = getTaskSortPriority(left.status) - getTaskSortPriority(right.status);
    if (priorityDifference !== 0) {
      return priorityDifference;
    }
    return left.deadline.localeCompare(right.deadline);
  });
  const dashboardStats = {
    total: visibleTasks.length,
    openCount: visibleTasks.filter((task) => task.status === "open").length,
    reviewCount: visibleTasks.filter((task) => task.status === "closed" || task.status === "reviewing").length,
    archivedCount: visibleTasks.filter((task) => task.status === "ready_to_export" || task.status === "completed").length,
  };

  if (!session || session.role !== "member") {
    return null;
  }

  return (
    <div className="page-stack">
      <section className="status-card dashboard-panel">
        <div className="task-card-top">
          <div>
            <p className="eyebrow">Member Tasks</p>
            <h2>成员可提交任务</h2>
          </div>
          {state.status === "ready" ? (
            <span className="status-chip">当前任务 {dashboardStats.total}</span>
          ) : null}
        </div>
        <p>
          当前页改成成员任务工作台：先看自己现在该做什么，再决定上传材料、补缺失项还是确认费用，不再把页面当成静态说明页。
        </p>
        <div className="dashboard-kpi-grid" aria-label="成员任务概览">
          <div className="kpi-card">
            <strong className="kpi-value">{dashboardStats.openCount}</strong>
            <span className="kpi-label">正在开放提交</span>
            <p>优先处理这类任务，避免错过截止时间。</p>
          </div>
          <div className="kpi-card">
            <strong className="kpi-value">{dashboardStats.reviewCount}</strong>
            <span className="kpi-label">等待补充或确认</span>
            <p>重点查看识别状态、缺失材料和费用确认入口。</p>
          </div>
          <div className="kpi-card">
            <strong className="kpi-value">{dashboardStats.archivedCount}</strong>
            <span className="kpi-label">进入归档阶段</span>
            <p>这类任务以查询和回看记录为主。</p>
          </div>
        </div>
      </section>

      {state.status === "loading" ? (
        <section className="status-card">
          <p className="eyebrow">Loading</p>
          <h2>正在加载成员可见任务</h2>
          <p>正在读取当前成员可参与的比赛报销任务，请稍候。</p>
        </section>
      ) : null}

      {state.status === "error" ? <ApiErrorNotice error={state.error} /> : null}

      {state.status === "ready" && sortedVisibleTasks.length === 0 ? (
        <section className="status-card">
          <p className="eyebrow">Empty</p>
          <h2>当前没有可见报销任务</h2>
          <p>
            当前 mock 成员身份尚未匹配到任何 `member_ids` 包含 {session.actorId}
            的任务；后续如果管理员创建并发布包含你的比赛任务，会在这里显示。
          </p>
        </section>
      ) : null}

      {state.status === "ready" && sortedVisibleTasks.length > 0 ? (
        <section className="task-card-grid" aria-label="成员可见任务列表">
          {sortedVisibleTasks.map((task) => {
            const actionHint = buildActionHint(task);

            return (
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

                <p className="task-stage-line">当前阶段：{formatTaskStatus(task.status)}</p>

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

                <div className="task-insight-grid">
                  <section className="task-insight">
                    <span className="task-insight-label">推荐动作</span>
                    <strong>{actionHint.title}</strong>
                    <p>{actionHint.summary}</p>
                  </section>
                  <section className="task-insight">
                    <span className="task-insight-label">本页用途</span>
                    <strong>先确定下一步，再进入具体操作页</strong>
                    <p>成员工作台只做一件事：把当前任务按优先级摆出来，避免你在不同页面之间猜流程。</p>
                  </section>
                </div>

                <ul className="task-workflow-list" aria-label={`${task.id} 建议动作`}>
                  {actionHint.actions.map((action) => (
                    <li key={`${task.id}:${action}`} className="task-workflow-item">
                      {action}
                    </li>
                  ))}
                </ul>

                <div className="inline-actions">
                  <Link
                    className="route-link route-link-secondary"
                    to={`/member/materials/status?taskId=${encodeURIComponent(task.id)}`}
                  >
                    查看材料状态
                  </Link>
                  <Link
                    className="route-link route-link-secondary"
                    to={`/member/materials/missing?taskId=${encodeURIComponent(task.id)}`}
                  >
                    查看缺失材料
                  </Link>
                  <Link
                    className="route-link route-link-secondary"
                    to={`/member/expenses/confirm?taskId=${encodeURIComponent(task.id)}`}
                  >
                    确认费用明细
                  </Link>
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
            );
          })}
        </section>
      ) : null}
    </div>
  );
}
