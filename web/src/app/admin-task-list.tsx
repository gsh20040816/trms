import { useDeferredValue, useEffect, useState } from "react";
import { Link as RouterLink } from "react-router-dom";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";

import { EmptyState, PageHeader, SectionCard, StatusBadge, TaskTable } from "../components/dashboard";
import { ApiErrorNotice } from "../components/ApiErrorNotice";
import { trmsApi } from "../lib/api/trms";
import type {
  OverdueConfirmationList,
  ReimbursementTask,
  TaskReviewSummary,
  TaskStatus,
} from "../lib/api/types";
import { formatTaskStatus } from "../lib/ui-text";
import { formatTaskAdministratorCountLabel, isTaskVisibleToAdministrator } from "../lib/task-administrators";
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

function buildAnomalyCount(reviewSummary: TaskReviewSummary, overdueSummary: OverdueConfirmationList) {
  const materialGapCount = buildMaterialGapCount(reviewSummary);
  const outstandingCount = buildOutstandingConfirmationCount(reviewSummary);
  const overdueCount = Number(overdueSummary.total_overdue_members ?? 0);
  return materialGapCount
    + outstandingCount
    + overdueCount
    + reviewSummary.counts.disputed_confirmation_count
    + reviewSummary.counts.failed_recognition_count
    + reviewSummary.counts.needs_confirmation_recognition_count;
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
    return `/admin/tasks/${task.id}/review`;
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

function buildPriorityHighlights(reviewSummary: TaskReviewSummary, overdueSummary: OverdueConfirmationList) {
  const items: string[] = [];
  const materialGapCount = buildMaterialGapCount(reviewSummary);
  const overdueCount = Number(overdueSummary.total_overdue_members ?? 0);
  if (materialGapCount > 0) {
    items.push(`${materialGapCount} 项材料或校验待补齐`);
  }
  if (reviewSummary.counts.failed_recognition_count > 0) {
    items.push(`${reviewSummary.counts.failed_recognition_count} 份材料识别失败`);
  }
  if (reviewSummary.counts.needs_confirmation_recognition_count > 0) {
    items.push(`${reviewSummary.counts.needs_confirmation_recognition_count} 份材料待人工确认`);
  }
  if (reviewSummary.counts.disputed_confirmation_count > 0) {
    items.push(`${reviewSummary.counts.disputed_confirmation_count} 条费用存在成员异议`);
  }
  if (buildOutstandingConfirmationCount(reviewSummary) > 0) {
    items.push(`${buildOutstandingConfirmationCount(reviewSummary)} 条费用待成员确认`);
  }
  if (overdueCount > 0) {
    items.push(`${overdueCount} 名成员已逾期未确认`);
  }
  return items.slice(0, 3);
}

function buildMetricCards(allItems: AdminTaskDigest[]) {
  return [
    {
      key: "draft",
      label: "草稿待完善",
      value: allItems.filter(({ task }) => task.status === "draft").length,
      hint: "补齐成员与费用后再发布",
      tone: "neutral" as const,
    },
    {
      key: "collecting",
      label: "收集中",
      value: allItems.filter(({ task }) => task.status === "open").length,
      hint: "成员仍可继续上传材料",
      tone: "info" as const,
    },
    {
      key: "reviewing",
      label: "待复核",
      value: allItems.filter(({ task }) => task.status === "closed" || task.status === "reviewing").length,
      hint: "优先清理异常与待确认",
      tone: "warning" as const,
    },
    {
      key: "attention",
      label: "需催办",
      value: allItems.filter(({ reviewSummary, overdueSummary }) =>
        buildPriorityScore(reviewSummary, overdueSummary) > 0,
      ).length,
      hint: "存在缺件、异议或逾期",
      tone: "danger" as const,
    },
    {
      key: "ready",
      label: "可导出",
      value: allItems.filter(({ task }) => task.status === "ready_to_export").length,
      hint: "可直接进入导出整理",
      tone: "success" as const,
    },
  ];
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
        const ownedTasks = allTasks.filter((task) => isTaskVisibleToAdministrator(task, session.actorId));
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

  const metricCards = buildMetricCards(allItems);
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
          title="任务管理"
          description="先看哪一个任务最该推进，再顺着首页把缺件、确认和导出准备度处理完。"
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
      <section className="admin-dashboard-metric-grid" aria-label="管理员任务概览">
        {metricCards.map((metric) => (
          <Card key={metric.key} component="article" variant="outlined" className="admin-dashboard-metric-card">
            <CardContent>
              <Stack direction="row" alignItems="flex-start" justifyContent="space-between" spacing={1}>
                <Box sx={{ minWidth: 0 }}>
                  <Typography variant="overline" color="text.secondary">
                    {metric.label}
                  </Typography>
                  <Typography component="strong" variant="h5" sx={{ display: "block", fontWeight: 700, lineHeight: 1.1 }}>
                    {metric.value}
                  </Typography>
                </Box>
                <StatusBadge tone={metric.tone}>{metric.hint}</StatusBadge>
              </Stack>
            </CardContent>
          </Card>
        ))}
      </section>

      {highlightedItem ? (
        <SectionCard
          title="建议优先处理的任务"
          description="先把这一项推进到下一个稳定阶段，再回头处理其他任务。"
          action={(
            <StatusBadge tone={buildStatusTone(highlightedItem.task, highlightedItem.reviewSummary, highlightedItem.overdueSummary)}>
              {describeAdminTaskStage(highlightedItem.task.status).label}
            </StatusBadge>
          )}
        >
          <div className="admin-dashboard-priority-layout">
            <div className="admin-dashboard-priority-main">
              <p className="eyebrow">下一步建议</p>
              <h3>{highlightedItem.task.competition_name}</h3>
              <p className="admin-dashboard-priority-summary">
                {highlightedItem.task.competition_location} · {formatTaskAdministratorCountLabel(highlightedItem.task)}
                · 截止 {formatDateTime(highlightedItem.task.deadline)}
              </p>
              <p className="admin-dashboard-priority-description">
                {buildTaskAction(highlightedItem.task, highlightedItem.reviewSummary, highlightedItem.overdueSummary)}
                前，先处理当前最明显的阻塞项。
              </p>
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
            </div>
            <div className="priority-task-grid">
              <div>
                <dt>当前阶段</dt>
                <dd>{describeAdminTaskStage(highlightedItem.task.status).label}</dd>
              </div>
              <div>
                <dt>待处理数量</dt>
                <dd>{buildAnomalyCount(highlightedItem.reviewSummary, highlightedItem.overdueSummary)}</dd>
              </div>
              <div>
                <dt>下一步动作</dt>
                <dd>{buildTaskAction(highlightedItem.task, highlightedItem.reviewSummary, highlightedItem.overdueSummary)}</dd>
              </div>
            </div>
            <ul className="admin-dashboard-priority-list" aria-label="当前优先任务提醒">
              {buildPriorityHighlights(highlightedItem.reviewSummary, highlightedItem.overdueSummary).map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>
        </SectionCard>
      ) : null}

      <SectionCard
        title="筛选任务"
        description="先搜任务名，再按状态缩小范围。"
        action={<StatusBadge tone="info">共 {sortedFilteredItems.length} 条</StatusBadge>}
      >
        <div className="admin-task-toolbar">
          <TextField
            label="搜索任务"
            aria-label="基础搜索"
            type="search"
            value={searchQuery}
            placeholder="输入任务名称"
            size="small"
            onChange={(event) => {
              setSearchQuery(event.target.value);
            }}
          />
          <TextField
            select
            label="任务状态"
            aria-label="状态筛选"
            value={statusFilter}
            size="small"
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
          description="先处理临近截止、卡点最多的任务；不需要来回跳多个页面。"
        >
          <TaskTable
            caption="管理员待处理任务"
            header={(
              <tr>
                <th>任务</th>
                <th>当前卡点</th>
                <th>截止时间</th>
                <th>处理动作</th>
              </tr>
            )}
          >
            {sortedFilteredItems.map(({ task, reviewSummary, overdueSummary }) => {
              const overdueCount = Number(overdueSummary.total_overdue_members ?? 0);
              const stage = describeAdminTaskStage(task.status);
              const anomalyCount = buildAnomalyCount(reviewSummary, overdueSummary);
              return (
                <tr key={task.id} className="admin-task-list-row">
                  <td>
                    <div className="table-primary">
                      <strong>{task.competition_name}</strong>
                      <span>
                        {task.competition_location} · {formatTaskAdministratorCountLabel(task)}
                      </span>
                      <div className="admin-task-row-badges">
                        <StatusBadge tone={buildStatusTone(task, reviewSummary, overdueSummary)}>
                          {formatTaskStatus(task.status)}
                        </StatusBadge>
                        <StatusBadge tone="info">{stage.label}</StatusBadge>
                      </div>
                    </div>
                  </td>
                  <td>
                    <div className="table-primary">
                      <strong>{anomalyCount} 项待处理</strong>
                      <span>{buildPriorityHighlights(reviewSummary, overdueSummary)[0] ?? "当前没有突出阻塞项"}</span>
                      {overdueCount > 0 ? <span className="table-subnote">其中逾期 {overdueCount} 人</span> : null}
                    </div>
                  </td>
                  <td>{formatDateTime(task.deadline)}</td>
                  <td>
                    <div className="table-actions admin-task-row-actions">
                      <Button
                        component={RouterLink}
                        variant="contained"
                        size="small"
                        to={buildTaskActionPath(task, reviewSummary, overdueSummary)}
                      >
                        {buildTaskAction(task, reviewSummary, overdueSummary)}
                      </Button>
                      <Button component={RouterLink} variant="text" size="small" to={`/admin/tasks/${task.id}`}>
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
