import { useDeferredValue, useEffect, useState } from "react";
import { Link as RouterLink } from "react-router-dom";

import Button from "@mui/material/Button";
import TextField from "@mui/material/TextField";

import { EmptyState, PageHeader, SectionCard, StatCard, StatusBadge, TaskTable } from "../components/dashboard";
import { ApiErrorNotice } from "../components/ApiErrorNotice";
import { trmsApi } from "../lib/api/trms";
import type {
  OverdueConfirmationList,
  ReimbursementTask,
  TaskReviewSummary,
  TaskStatus,
} from "../lib/api/types";
import { formatTaskStatus } from "../lib/ui-text";
import { describeAdminTaskStage } from "./admin-task-stage";
import { AdminWorkspaceShell } from "./admin-workspace-shell";
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

function buildTaskActionPath(task: ReimbursementTask, reviewSummary: TaskReviewSummary, overdueSummary: OverdueConfirmationList) {
  if (buildMaterialGapCount(reviewSummary) > 0) {
    return `/admin/tasks/${task.id}/missing-materials`;
  }
  if (buildOutstandingConfirmationCount(reviewSummary) > 0 || overdueSummary.total_overdue_members > 0) {
    return `/admin/tasks/${task.id}/review`;
  }
  if (task.status === "ready_to_export") {
    return `/admin/tasks/${task.id}/exports`;
  }
  return `/admin/tasks/${task.id}`;
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
    draftCount: allItems.filter(({ task }) => task.status === "draft").length,
    collectingCount: allItems.filter(({ task }) => task.status === "open").length,
    reviewingCount: allItems.filter(({ task }) => task.status === "closed" || task.status === "reviewing").length,
    attentionCount: allItems.filter(({ reviewSummary, overdueSummary }) =>
      buildPriorityScore(reviewSummary, overdueSummary) > 0,
    ).length,
    readyToExportCount: allItems.filter(({ task }) => task.status === "ready_to_export").length,
  };
  const topPriorityItem = sortedFilteredItems[0] ?? null;
  const overallTopPriorityItem = [...allItems].sort((left, right) => {
    const rightScore = buildPriorityScore(right.reviewSummary, right.overdueSummary);
    const leftScore = buildPriorityScore(left.reviewSummary, left.overdueSummary);
    if (rightScore !== leftScore) {
      return rightScore - leftScore;
    }
    return left.task.deadline.localeCompare(right.task.deadline);
  })[0] ?? null;
  const highlightedItem = topPriorityItem ?? overallTopPriorityItem;

  return (
    <AdminWorkspaceShell
      activeModule="overview"
      header={(
        <PageHeader
          eyebrow="管理员工作台"
          title="按任务推进处理当前工作"
          description="首页先展示当前任务处于哪个阶段、有多少异常，以及你下一步最该进入哪个处理入口。"
          meta={`当前身份：${session.displayName}`}
          actions={(
            <div className="page-actions">
              <Button component={RouterLink} variant="contained" to="/admin/tasks/new">
                创建任务
              </Button>
            </div>
          )}
        />
      )}
    >
      <section className="stat-grid" aria-label="管理员任务概览">
        <StatCard label="创建中任务" value={dashboardStats.draftCount} description="仍需补齐成员、费用类别或基础信息后再发布。" />
        <StatCard label="收集中任务" value={dashboardStats.collectingCount} description="成员仍可提交材料，优先盯缺失项和截止时间。" />
        <StatCard label="审核中任务" value={dashboardStats.reviewingCount} description="已截止或正在复核，适合集中处理异常与确认。" />
        <StatCard label="需要优先处理" value={dashboardStats.attentionCount} description="存在缺失材料、待确认费用或逾期事项。" />
        <StatCard label="可导出任务" value={dashboardStats.readyToExportCount} description="条件已满足，可直接整理导出材料。" />
      </section>

      {highlightedItem ? (
        <SectionCard
          title="当前优先推进任务"
          description="首页优先给出当前最紧急的任务阶段、异常数量和建议入口。"
          action={(
            <StatusBadge tone={buildStatusTone(highlightedItem.task, highlightedItem.reviewSummary, highlightedItem.overdueSummary)}>
              {describeAdminTaskStage(highlightedItem.task.status).label}
            </StatusBadge>
          )}
        >
          <div className="priority-task-grid">
            <div>
              <dt>任务</dt>
              <dd>{highlightedItem.task.competition_name}</dd>
            </div>
            <div>
              <dt>异常数量</dt>
              <dd>
                {buildMaterialGapCount(highlightedItem.reviewSummary)
                  + highlightedItem.reviewSummary.counts.disputed_confirmation_count
                  + highlightedItem.reviewSummary.counts.failed_recognition_count
                  + highlightedItem.reviewSummary.counts.needs_confirmation_recognition_count}
              </dd>
            </div>
            <div>
              <dt>下一步动作</dt>
              <dd>{buildTaskAction(highlightedItem.task, highlightedItem.reviewSummary, highlightedItem.overdueSummary)}</dd>
            </div>
          </div>
          <div className="page-actions">
            <Button
              component={RouterLink}
              variant="contained"
              to={buildTaskActionPath(highlightedItem.task, highlightedItem.reviewSummary, highlightedItem.overdueSummary)}
            >
              进入当前优先任务
            </Button>
            <Button component={RouterLink} variant="outlined" to={`/admin/tasks/${highlightedItem.task.id}`}>
              查看任务详情
            </Button>
          </div>
        </SectionCard>
      ) : null}

      <SectionCard title="筛选任务" description="通过任务名称和状态快速定位要处理的事项。">
        <div className="filter-grid">
          <TextField
            label="搜索任务"
            aria-label="基础搜索"
            type="search"
            value={searchQuery}
            placeholder="输入任务名称"
            onChange={(event) => {
              setSearchQuery(event.target.value);
            }}
          />
          <TextField
            select
            label="任务状态"
            aria-label="状态筛选"
            value={statusFilter}
            onChange={(event) => {
              setStatusFilter(event.target.value as TaskStatusFilter);
            }}
            SelectProps={{ native: true }}
          >
              {TASK_STATUS_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
          </TextField>
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
            <Button component={RouterLink} variant="contained" to="/admin/tasks/new">
              创建新任务
            </Button>
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
                <th>当前阶段</th>
                <th>状态</th>
                <th>截止时间</th>
                <th>异常数量</th>
                <th>下一步动作</th>
              </tr>
            )}
          >
            {sortedFilteredItems.map(({ task, reviewSummary, overdueSummary }) => {
              const materialGapCount = buildMaterialGapCount(reviewSummary);
              const outstandingCount = buildOutstandingConfirmationCount(reviewSummary);
              const overdueCount = Number(overdueSummary.total_overdue_members ?? 0);
              const stage = describeAdminTaskStage(task.status);
              const anomalyCount = materialGapCount
                + outstandingCount
                + overdueCount
                + reviewSummary.counts.disputed_confirmation_count
                + reviewSummary.counts.failed_recognition_count
                + reviewSummary.counts.needs_confirmation_recognition_count;
              return (
                <tr key={task.id}>
                  <td>
                    <div className="table-primary">
                      <strong>{task.competition_name}</strong>
                      <span>
                        {task.competition_location} · 负责人 {session.displayName}
                      </span>
                    </div>
                  </td>
                  <td>{stage.label}</td>
                  <td>
                    <StatusBadge tone={buildStatusTone(task, reviewSummary, overdueSummary)}>
                      {formatTaskStatus(task.status)}
                    </StatusBadge>
                  </td>
                  <td>{formatDateTime(task.deadline)}</td>
                  <td>
                    {anomalyCount}
                    {overdueCount > 0 ? <span className="table-subnote">，逾期 {overdueCount}</span> : null}
                  </td>
                  <td>
                    <div className="table-actions">
                      <Button
                        component={RouterLink}
                        variant="contained"
                        size="small"
                        to={buildTaskActionPath(task, reviewSummary, overdueSummary)}
                      >
                        {buildTaskAction(task, reviewSummary, overdueSummary)}
                      </Button>
                      <Button component={RouterLink} variant="outlined" size="small" to={`/admin/tasks/${task.id}`}>
                        查看详情
                      </Button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </TaskTable>
        </SectionCard>
      ) : null}
    </AdminWorkspaceShell>
  );
}
