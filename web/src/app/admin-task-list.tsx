import { useDeferredValue, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { useAuthSession } from "./auth-store";
import { ApiErrorNotice } from "../components/ApiErrorNotice";
import { trmsApi } from "../lib/api/trms";
import type {
  OverdueConfirmationList,
  ReimbursementTask,
  TaskReviewSummary,
  TaskStatus,
} from "../lib/api/types";

type AdminTaskDigest = {
  task: ReimbursementTask;
  reviewSummary: TaskReviewSummary;
  overdueSummary: OverdueConfirmationList;
};

type TaskListState =
  | { status: "loading" }
  | { status: "error"; error: unknown }
  | { status: "ready"; items: AdminTaskDigest[] };

type TaskStatusFilter = "all" | TaskStatus;

type TaskAnomalyItem = {
  label: string;
  count: number;
  tone: "failed" | "pending";
};

type TaskActionHint = {
  title: string;
  summary: string;
};

const TASK_STATUS_OPTIONS: Array<{ value: TaskStatusFilter; label: string }> = [
  { value: "all", label: "全部状态" },
  { value: "draft", label: "草稿" },
  { value: "open", label: "开放提交" },
  { value: "closed", label: "已关闭" },
  { value: "reviewing", label: "复核中" },
  { value: "ready_to_export", label: "可导出" },
  { value: "completed", label: "已归档" },
];

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

function buildTaskAnomalies(
  reviewSummary: TaskReviewSummary,
  overdueSummary: OverdueConfirmationList,
): TaskAnomalyItem[] {
  const items: TaskAnomalyItem[] = [];

  if (reviewSummary.counts.blocker_failed_validation_count > 0) {
    items.push({
      label: "Must 级失败校验",
      count: reviewSummary.counts.blocker_failed_validation_count,
      tone: "failed",
    });
  }
  if (reviewSummary.counts.failed_recognition_count > 0) {
    items.push({
      label: "识别失败",
      count: reviewSummary.counts.failed_recognition_count,
      tone: "failed",
    });
  }
  if (reviewSummary.counts.needs_confirmation_recognition_count > 0) {
    items.push({
      label: "识别待人工确认",
      count: reviewSummary.counts.needs_confirmation_recognition_count,
      tone: "pending",
    });
  }
  if (reviewSummary.counts.disputed_confirmation_count > 0) {
    items.push({
      label: "成员异议",
      count: reviewSummary.counts.disputed_confirmation_count,
      tone: "failed",
    });
  }

  const unresolvedConfirmationCount =
    reviewSummary.counts.pending_confirmation_count
    + reviewSummary.counts.missing_confirmation_count;
  if (unresolvedConfirmationCount > 0) {
    items.push({
      label: "待确认费用明细",
      count: unresolvedConfirmationCount,
      tone: "pending",
    });
  }
  if (overdueSummary.is_overdue && overdueSummary.total_overdue_members > 0) {
    items.push({
      label: "逾期未确认成员",
      count: overdueSummary.total_overdue_members,
      tone: "failed",
    });
  }

  return items;
}

function buildPriorityScore(reviewSummary: TaskReviewSummary, overdueSummary: OverdueConfirmationList) {
  return reviewSummary.counts.blocker_failed_validation_count * 100
    + reviewSummary.counts.disputed_confirmation_count * 70
    + reviewSummary.counts.failed_recognition_count * 50
    + reviewSummary.counts.needs_confirmation_recognition_count * 30
    + (reviewSummary.counts.pending_confirmation_count + reviewSummary.counts.missing_confirmation_count) * 10
    + (overdueSummary.is_overdue ? overdueSummary.total_overdue_members * 20 : 0);
}

function buildTaskActionHint(
  task: ReimbursementTask,
  reviewSummary: TaskReviewSummary,
  overdueSummary: OverdueConfirmationList,
): TaskActionHint {
  if (reviewSummary.counts.blocker_failed_validation_count > 0) {
    return {
      title: "先处理 Must 级失败校验",
      summary: "当前任务还不能顺利推进到导出阶段，应优先修复关键校验异常。",
    };
  }
  if (reviewSummary.counts.disputed_confirmation_count > 0 || overdueSummary.total_overdue_members > 0) {
    return {
      title: "催办成员确认或处理异议",
      summary: "先把成员异议和逾期确认清掉，再继续推进复核与导出。",
    };
  }
  if (reviewSummary.counts.failed_recognition_count > 0 || reviewSummary.counts.needs_confirmation_recognition_count > 0) {
    return {
      title: "补人工更正与识别确认",
      summary: "识别失败和低置信度字段会拖慢后续复核，建议先回到发票更正页处理。",
    };
  }
  if (task.status === "draft") {
    return {
      title: "补齐配置后发布任务",
      summary: "草稿态任务应先确认成员名单、截止时间和费用类别，再开放提交。",
    };
  }
  if (task.status === "open") {
    return {
      title: "继续收集材料",
      summary: "当前仍在开放提交阶段，建议盯住截止时间并提前处理高风险任务。",
    };
  }
  if (task.status === "closed" || task.status === "reviewing") {
    return {
      title: "进入复核总览推进清单",
      summary: "任务已接近复核阶段，应把缺失材料、确认和异常项尽快清零。",
    };
  }
  if (task.status === "ready_to_export") {
    return {
      title: "创建导出任务",
      summary: "当前已达到可导出状态，可直接进入导出工作台生成所需材料。",
    };
  }
  return {
    title: "保持归档记录可追溯",
    summary: "当前任务已完成归档，后续主要用于查询和追溯，不再继续推进。",
  };
}

export function AdminTaskListPage() {
  const session = useAuthSession();
  const [state, setState] = useState<TaskListState>({ status: "loading" });
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<TaskStatusFilter>("all");
  const deferredSearchQuery = useDeferredValue(searchQuery.trim().toLowerCase());

  useEffect(() => {
    let cancelled = false;

    async function loadTaskDigests() {
      if (!session || session.role !== "admin") {
        return;
      }

      setState({ status: "loading" });

      try {
        const allTasks = await trmsApi.listTasks();
        const ownedTasks = allTasks.filter((task) => task.administrator_id === session.actorId);
        const items = await Promise.all(
          ownedTasks.map(async (task) => {
            const [reviewSummary, overdueSummary] = await Promise.all([
              trmsApi.getTaskReviewSummary(task.id, session.actorId),
              trmsApi.listTaskOverdueConfirmations(task.id, session.actorId),
            ]);
            return {
              task,
              reviewSummary,
              overdueSummary,
            };
          }),
        );

        if (cancelled) {
          return;
        }

        setState({
          status: "ready",
          items,
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

    void loadTaskDigests();

    return () => {
      cancelled = true;
    };
  }, [session]);

  const allItems = state.status === "ready" ? state.items : [];
  const filteredItems = allItems.filter(({ task }) => {
    const matchesStatus = statusFilter === "all" || task.status === statusFilter;
    const matchesSearch =
      deferredSearchQuery.length === 0
      || task.id.toLowerCase().includes(deferredSearchQuery)
      || task.competition_name.toLowerCase().includes(deferredSearchQuery);
    return matchesStatus && matchesSearch;
  });

  const sortedFilteredItems = [...filteredItems].sort((left, right) => {
    const rightScore = buildPriorityScore(right.reviewSummary, right.overdueSummary);
    const leftScore = buildPriorityScore(left.reviewSummary, left.overdueSummary);
    if (rightScore !== leftScore) {
      return rightScore - leftScore;
    }
    return left.task.deadline.localeCompare(right.task.deadline);
  });

  const dashboardStats = {
    total: allItems.length,
    activeCount: allItems.filter(({ task }) =>
      task.status === "open" || task.status === "closed" || task.status === "reviewing",
    ).length,
    attentionCount: allItems.filter(({ reviewSummary, overdueSummary }) =>
      buildPriorityScore(reviewSummary, overdueSummary) > 0,
    ).length,
    readyToExportCount: allItems.filter(({ task }) => task.status === "ready_to_export").length,
  };

  if (!session || session.role !== "admin") {
    return null;
  }

  return (
    <div className="page-stack">
      <section className="status-card dashboard-panel">
        <div className="task-card-top">
          <div>
            <p className="eyebrow">Admin Tasks</p>
            <h2>管理员任务列表</h2>
          </div>
          {state.status === "ready" ? (
            <span className="status-chip">当前任务 {filteredItems.length} / {dashboardStats.total}</span>
          ) : null}
        </div>
        <p>
          当前页改成管理员工作台入口：先看哪些任务需要处理，再决定进入详情、复核还是导出，而不是先读大段说明文本。
        </p>
        <div className="inline-actions">
          <Link className="route-link" to="/admin/tasks/new">
            创建新任务
          </Link>
        </div>
        <div className="dashboard-kpi-grid" aria-label="管理员任务概览">
          <div className="kpi-card">
            <strong className="kpi-value">{dashboardStats.total}</strong>
            <span className="kpi-label">我负责的任务</span>
            <p>只统计 `administrator_id` 与当前身份一致的任务。</p>
          </div>
          <div className="kpi-card">
            <strong className="kpi-value">{dashboardStats.activeCount}</strong>
            <span className="kpi-label">推进中的任务</span>
            <p>包含开放提交、已关闭和复核中的任务。</p>
          </div>
          <div className="kpi-card">
            <strong className="kpi-value">{dashboardStats.attentionCount}</strong>
            <span className="kpi-label">需要优先处理</span>
            <p>含 Must 级失败、识别异常、异议或逾期确认的任务。</p>
          </div>
          <div className="kpi-card">
            <strong className="kpi-value">{dashboardStats.readyToExportCount}</strong>
            <span className="kpi-label">可直接导出</span>
            <p>这类任务可以直接进入导出工作台生成材料。</p>
          </div>
        </div>
      </section>

      <section className="status-card admin-filter-panel">
        <div className="admin-filter-header">
          <div>
            <p className="eyebrow">筛选与搜索</p>
            <h2>先筛任务，再处理异常</h2>
          </div>
        </div>
        <div className="admin-filter-grid">
          <label className="field-stack">
            <span>基础搜索</span>
            <input
              type="search"
              name="task-search"
              value={searchQuery}
              placeholder="输入任务编号或比赛名称"
              onChange={(event) => {
                setSearchQuery(event.target.value);
              }}
            />
          </label>
          <label className="field-stack">
            <span>状态筛选</span>
            <select
              name="task-status-filter"
              value={statusFilter}
              onChange={(event) => {
                setStatusFilter(event.target.value as TaskStatusFilter);
              }}
            >
              {TASK_STATUS_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
        </div>
      </section>

      {state.status === "loading" ? (
        <section className="status-card">
          <p className="eyebrow">Loading</p>
          <h2>正在加载任务列表</h2>
          <p>正在读取管理员任务、复核摘要和逾期确认摘要，请稍候。</p>
        </section>
      ) : null}

      {state.status === "error" ? <ApiErrorNotice error={state.error} /> : null}

      {state.status === "ready" && allItems.length === 0 ? (
        <section className="status-card">
          <p className="eyebrow">Empty</p>
          <h2>当前管理员名下还没有任务</h2>
          <p>
            当前 mock 管理员身份尚未匹配到任何 `administrator_id = {session.actorId}` 的任务；可先创建任务，再回到这里继续推进复核工作流。
          </p>
        </section>
      ) : null}

      {state.status === "ready" && allItems.length > 0 && sortedFilteredItems.length === 0 ? (
        <section className="status-card">
          <p className="eyebrow">No Match</p>
          <h2>没有匹配当前筛选条件的任务</h2>
          <p>请放宽状态筛选或清空搜索词，再重新查看管理员任务列表。</p>
        </section>
      ) : null}

      {state.status === "ready" && sortedFilteredItems.length > 0 ? (
        <section className="task-card-grid" aria-label="管理员任务列表">
          {sortedFilteredItems.map(({ task, reviewSummary, overdueSummary }) => {
            const anomalies = buildTaskAnomalies(reviewSummary, overdueSummary);
            const nextAction = buildTaskActionHint(task, reviewSummary, overdueSummary);

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
                    <dt>材料 / 发票</dt>
                    <dd>
                      {reviewSummary.counts.material_count} / {reviewSummary.counts.invoice_count}
                    </dd>
                  </div>
                  <div>
                    <dt>确认进度</dt>
                    <dd>
                      {reviewSummary.counts.confirmed_split_count} / {reviewSummary.counts.split_count}
                    </dd>
                  </div>
                </dl>

                <div className="task-insight-grid">
                  <section className="task-insight">
                    <span className="task-insight-label">推荐动作</span>
                    <strong>{nextAction.title}</strong>
                    <p>{nextAction.summary}</p>
                  </section>
                  <section className="task-insight">
                    <span className="task-insight-label">异常视图</span>
                    <strong>{anomalies.length > 0 ? `${anomalies.length} 类待处理问题` : "当前无异常"}</strong>
                    <p>
                      {anomalies.length > 0
                        ? "优先清掉 Must 级失败、成员异议和逾期确认，再进入下一阶段。"
                        : "当前没有阻断性问题，可按任务状态继续推进。"}
                    </p>
                  </section>
                </div>

                <section className="task-anomaly-panel" aria-label={`${task.id} 异常摘要`}>
                  <div className="task-anomaly-header">
                    <h4>异常摘要</h4>
                    <span className="status-chip">
                      {anomalies.length > 0 ? `${anomalies.length} 类异常` : "当前无异常"}
                    </span>
                  </div>
                  {anomalies.length > 0 ? (
                    <ul className="anomaly-chip-list">
                      {anomalies.map((anomaly) => (
                        <li
                          key={`${task.id}:${anomaly.label}`}
                          className={`anomaly-chip anomaly-chip-${anomaly.tone}`}
                        >
                          <span>{anomaly.label}</span>
                          <strong>{anomaly.count}</strong>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="task-healthy-note">
                      当前未发现 Must 级失败校验、识别异常、成员异议或逾期未确认成员。
                    </p>
                  )}
                </section>

                <div className="inline-actions">
                  <Link className="route-link" to={`/admin/tasks/${task.id}`}>
                    查看详情与状态操作
                  </Link>
                  <Link className="route-link route-link-secondary" to={`/admin/tasks/${task.id}/review`}>
                    进入复核总览
                  </Link>
                </div>
              </article>
            );
          })}
        </section>
      ) : null}
    </div>
  );
}
