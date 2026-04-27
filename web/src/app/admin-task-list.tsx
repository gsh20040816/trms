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
    });
  }
  if (reviewSummary.counts.failed_recognition_count > 0) {
    items.push({
      label: "识别失败",
      count: reviewSummary.counts.failed_recognition_count,
    });
  }
  if (reviewSummary.counts.needs_confirmation_recognition_count > 0) {
    items.push({
      label: "识别待人工确认",
      count: reviewSummary.counts.needs_confirmation_recognition_count,
    });
  }
  if (reviewSummary.counts.disputed_confirmation_count > 0) {
    items.push({
      label: "成员异议",
      count: reviewSummary.counts.disputed_confirmation_count,
    });
  }

  const unresolvedConfirmationCount =
    reviewSummary.counts.pending_confirmation_count
    + reviewSummary.counts.missing_confirmation_count;
  if (unresolvedConfirmationCount > 0) {
    items.push({
      label: "待确认费用明细",
      count: unresolvedConfirmationCount,
    });
  }
  if (overdueSummary.is_overdue && overdueSummary.total_overdue_members > 0) {
    items.push({
      label: "逾期未确认成员",
      count: overdueSummary.total_overdue_members,
    });
  }

  return items;
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

  if (!session || session.role !== "admin") {
    return null;
  }

  const allItems = state.status === "ready" ? state.items : [];
  const filteredItems = allItems.filter(({ task }) => {
    const matchesStatus = statusFilter === "all" || task.status === statusFilter;
    const matchesSearch =
      deferredSearchQuery.length === 0
      || task.id.toLowerCase().includes(deferredSearchQuery)
      || task.competition_name.toLowerCase().includes(deferredSearchQuery);
    return matchesStatus && matchesSearch;
  });

  return (
    <div className="page-stack">
      <section className="status-card admin-page-hero">
        <p className="eyebrow">Admin Tasks</p>
        <h2>管理员任务列表</h2>
        <p>
          当前页已接入真实任务列表、复核摘要和逾期确认摘要接口，优先服务管理员快速判断哪些任务可继续推进、哪些任务仍有异常待处理。
        </p>
        <p className="status-note">
          当前仍使用 mock 管理员身份 {session.displayName}（{session.actorId}），并保守地只展示
          `administrator_id` 与当前身份一致的任务，避免在真实鉴权未接入前误展示其他管理员任务。
        </p>
        <div className="inline-actions">
          <Link className="route-link" to="/admin/tasks/new">
            创建新任务
          </Link>
        </div>
      </section>

      <section className="status-card admin-filter-panel">
        <div className="admin-filter-header">
          <div>
            <p className="eyebrow">筛选与搜索</p>
            <h2>按状态筛选或按任务编号/比赛名称搜索</h2>
          </div>
          {state.status === "ready" ? (
            <span className="status-chip">当前任务 {filteredItems.length} / {allItems.length}</span>
          ) : null}
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
            当前 mock 管理员身份尚未匹配到任何 `administrator_id = {session.actorId}` 的任务；后续接入任务创建页后，可从这里继续进入详情与复核链路。
          </p>
        </section>
      ) : null}

      {state.status === "ready" && allItems.length > 0 && filteredItems.length === 0 ? (
        <section className="status-card">
          <p className="eyebrow">No Match</p>
          <h2>没有匹配当前筛选条件的任务</h2>
          <p>请放宽状态筛选或清空搜索词，再重新查看管理员任务列表。</p>
        </section>
      ) : null}

      {state.status === "ready" && filteredItems.length > 0 ? (
        <section className="task-card-grid" aria-label="管理员任务列表">
          {filteredItems.map(({ task, reviewSummary, overdueSummary }) => {
            const anomalies = buildTaskAnomalies(reviewSummary, overdueSummary);

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

                <section className="task-anomaly-panel" aria-label={`${task.id} 异常摘要`}>
                  <div className="task-anomaly-header">
                    <h4>异常摘要</h4>
                    <span className="status-chip">
                      {anomalies.length > 0 ? `${anomalies.length} 类异常` : "当前无异常"}
                    </span>
                  </div>
                  {anomalies.length > 0 ? (
                    <ul className="task-anomaly-list">
                      {anomalies.map((anomaly) => (
                        <li key={`${task.id}:${anomaly.label}`}>
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
                  <Link className="route-link route-link-secondary" to={`/admin/tasks/${task.id}`}>
                    查看详情与状态操作
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
