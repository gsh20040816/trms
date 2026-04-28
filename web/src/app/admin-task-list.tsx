import { useDeferredValue, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { EmptyState, PageHeader, RoleWorkspace, SectionCard, StatCard, StatusBadge, TaskTable } from "../components/dashboard";
import { ApiErrorNotice } from "../components/ApiErrorNotice";
import { trmsApi } from "../lib/api/trms";
import type {
  OverdueConfirmationList,
  ReimbursementTask,
  TaskReviewSummary,
  TaskStatus,
} from "../lib/api/types";
import { formatTaskStatus } from "../lib/ui-text";
import { useAuthSession } from "./auth-store";

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

const TASK_STATUS_OPTIONS: Array<{ value: TaskStatusFilter; label: string }> = [
  { value: "all", label: "全部状态" },
  { value: "draft", label: "草稿" },
  { value: "open", label: "收集中" },
  { value: "closed", label: "已截止" },
  { value: "reviewing", label: "待复核" },
  { value: "ready_to_export", label: "可导出" },
  { value: "completed", label: "已完成" },
];

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function buildOutstandingConfirmationCount(reviewSummary: TaskReviewSummary) {
  return reviewSummary.counts.pending_confirmation_count + reviewSummary.counts.missing_confirmation_count;
}

function buildMaterialGapCount(reviewSummary: TaskReviewSummary) {
  return Number(reviewSummary.counts.pending_assignment_material_count ?? 0)
    + Number(reviewSummary.counts.blocker_failed_validation_count ?? 0);
}

function buildPriorityScore(reviewSummary: TaskReviewSummary, overdueSummary: OverdueConfirmationList) {
  const overdueMemberCount = Number(overdueSummary.total_overdue_members ?? 0);
  return reviewSummary.counts.blocker_failed_validation_count * 100
    + reviewSummary.counts.disputed_confirmation_count * 70
    + reviewSummary.counts.failed_recognition_count * 50
    + reviewSummary.counts.needs_confirmation_recognition_count * 30
    + buildOutstandingConfirmationCount(reviewSummary) * 10
    + (overdueSummary.is_overdue ? overdueMemberCount * 20 : 0);
}

function buildTaskAction(task: ReimbursementTask, reviewSummary: TaskReviewSummary, overdueSummary: OverdueConfirmationList) {
  if (buildMaterialGapCount(reviewSummary) > 0) {
    return "补材料";
  }
  if (buildOutstandingConfirmationCount(reviewSummary) > 0 || overdueSummary.total_overdue_members > 0) {
    return "催确认";
  }
  if (task.status === "ready_to_export") {
    return "导出材料";
  }
  if (task.status === "draft") {
    return "完善任务";
  }
  return "进入处理";
}

function buildStatusTone(task: ReimbursementTask, reviewSummary: TaskReviewSummary, overdueSummary: OverdueConfirmationList) {
  if (buildPriorityScore(reviewSummary, overdueSummary) > 0) {
    return "warning" as const;
  }
  if (task.status === "ready_to_export" || task.status === "completed") {
    return "success" as const;
  }
  return "info" as const;
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

  return (
    <RoleWorkspace
      header={(
        <PageHeader
          eyebrow="管理员工作台"
          title="待处理任务"
          description="先看我负责的任务、材料风险和待确认情况，再进入复核、提醒或导出。"
          meta={`当前身份：${session.displayName}`}
          actions={(
            <div className="page-actions">
              <Link className="button button-primary" to="/admin/tasks/new">
                创建任务
              </Link>
            </div>
          )}
        />
      )}
      summary={(
        <section className="stat-grid" aria-label="管理员任务概览">
          <StatCard label="我负责的任务" value={dashboardStats.total} description="当前归你负责的全部报销任务。" />
          <StatCard label="推进中的任务" value={dashboardStats.activeCount} description="仍在收集、截止后待处理或待复核的任务。" />
          <StatCard label="需要优先处理" value={dashboardStats.attentionCount} description="存在缺失材料、待确认费用或逾期事项。" />
          <StatCard label="可导出任务" value={dashboardStats.readyToExportCount} description="条件已满足，可直接整理导出材料。" />
        </section>
      )}
    >
      <SectionCard title="筛选任务" description="通过任务名称和状态快速定位要处理的事项。">
        <div className="filter-grid">
          <label className="field-stack">
            <span>搜索任务</span>
            <input
              aria-label="基础搜索"
              type="search"
              value={searchQuery}
              placeholder="输入任务名称"
              onChange={(event) => {
                setSearchQuery(event.target.value);
              }}
            />
          </label>
          <label className="field-stack">
            <span>任务状态</span>
            <select
              aria-label="状态筛选"
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
      </SectionCard>

      {state.status === "loading" ? (
        <SectionCard title="正在加载任务列表" description="正在读取任务概览，请稍候。" />
      ) : null}

      {state.status === "error" ? <ApiErrorNotice error={state.error} /> : null}

      {state.status === "ready" && allItems.length === 0 ? (
        <EmptyState
          title="当前管理员名下还没有任务"
          description="可以先创建一个新的报销任务，随后回到这里查看收集、复核和导出进度。"
          action={(
            <Link className="button button-primary" to="/admin/tasks/new">
              创建新任务
            </Link>
          )}
        />
      ) : null}

      {state.status === "ready" && allItems.length > 0 && sortedFilteredItems.length === 0 ? (
        <EmptyState
          title="没有匹配当前筛选条件的任务"
          description="可以清空搜索条件或切换状态筛选后重新查看。"
        />
      ) : null}

      {state.status === "ready" && sortedFilteredItems.length > 0 ? (
        <SectionCard
          title="任务列表"
          description="任务列表是当前页面的主工作区，优先处理临近截止且存在风险的任务。"
          action={<StatusBadge tone="info">共 {sortedFilteredItems.length} 条</StatusBadge>}
        >
          <TaskTable
            caption="管理员待处理任务"
            header={(
              <tr>
                <th>任务名称</th>
                <th>状态</th>
                <th>负责人</th>
                <th>截止时间</th>
                <th>待补材料</th>
                <th>待确认费用</th>
                <th>操作</th>
              </tr>
            )}
          >
            {sortedFilteredItems.map(({ task, reviewSummary, overdueSummary }) => {
              const materialGapCount = buildMaterialGapCount(reviewSummary);
              const outstandingCount = buildOutstandingConfirmationCount(reviewSummary);
              const overdueCount = Number(overdueSummary.total_overdue_members ?? 0);
              return (
                <tr key={task.id}>
                  <td>
                    <div className="table-primary">
                      <strong>{task.competition_name}</strong>
                      <span>
                        {task.competition_location} · {formatTaskStatus(task.status)}
                      </span>
                    </div>
                  </td>
                  <td>
                    <StatusBadge tone={buildStatusTone(task, reviewSummary, overdueSummary)}>
                      {formatTaskStatus(task.status)}
                    </StatusBadge>
                  </td>
                  <td>{session.displayName}</td>
                  <td>{formatDateTime(task.deadline)}</td>
                  <td>{materialGapCount}</td>
                  <td>
                    {outstandingCount}
                    {overdueCount > 0 ? <span className="table-subnote">，逾期 {overdueCount}</span> : null}
                  </td>
                  <td>
                    <div className="table-actions">
                      <Link className="button button-primary button-small" to={`/admin/tasks/${task.id}/review`}>
                        {buildTaskAction(task, reviewSummary, overdueSummary)}
                      </Link>
                      <Link className="button button-secondary button-small" to={`/admin/tasks/${task.id}`}>
                        查看详情
                      </Link>
                    </div>
                  </td>
                </tr>
              );
            })}
          </TaskTable>
        </SectionCard>
      ) : null}
    </RoleWorkspace>
  );
}
