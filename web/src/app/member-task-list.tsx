import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { EmptyState, PageHeader, RoleWorkspace, SectionCard, StatCard, StatusBadge, TaskTable } from "../components/dashboard";
import { ApiErrorNotice } from "../components/ApiErrorNotice";
import { trmsApi } from "../lib/api/trms";
import type { ReimbursementTask, TaskStatus } from "../lib/api/types";
import { formatTaskStatus } from "../lib/ui-text";
import { useAuthSession } from "./auth-store";

type MemberTaskListState =
  | { status: "loading" }
  | { status: "error"; error: unknown }
  | { status: "ready"; items: ReimbursementTask[] };

const NEXT_ACTIONS: Record<TaskStatus, string> = {
  draft: "等待开放",
  open: "提交材料",
  closed: "查看待补项",
  reviewing: "确认费用",
  ready_to_export: "查看结果",
  completed: "查看归档",
};

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
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

function buildStatusTone(status: TaskStatus) {
  if (status === "open") {
    return "info" as const;
  }
  if (status === "reviewing" || status === "closed") {
    return "warning" as const;
  }
  if (status === "ready_to_export" || status === "completed") {
    return "success" as const;
  }
  return "neutral" as const;
}

function buildWorkbenchLink(task: ReimbursementTask) {
  return `/member/invoices/workbench?taskId=${encodeURIComponent(task.id)}`;
}

function buildDirectActionLink(task: ReimbursementTask) {
  if (task.status === "open") {
    return `/member/materials/upload?taskId=${encodeURIComponent(task.id)}`;
  }
  if (task.status === "closed") {
    return `/member/materials/missing?taskId=${encodeURIComponent(task.id)}`;
  }
  if (task.status === "reviewing") {
    return `/member/expenses/confirm?taskId=${encodeURIComponent(task.id)}`;
  }
  return `/member/materials/status?taskId=${encodeURIComponent(task.id)}`;
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

  return (
    <RoleWorkspace
      header={(
        <PageHeader
          eyebrow="成员工作台"
          title="我的报销任务"
          description="先看我参与的任务，再优先进入单任务发票工作台处理上传、补材料和费用确认。"
          meta={`当前成员：${session.displayName}${session.memberCode ? `（${session.memberCode}）` : ""}`}
          actions={(
            <div className="page-actions">
              <Link className="button button-primary" to="/member/invoices/workbench">
                进入发票工作台
              </Link>
            </div>
          )}
        />
      )}
      summary={(
        <section className="stat-grid" aria-label="成员任务概览">
          <StatCard label="我参与的任务" value={dashboardStats.total} description="当前你可以查看或处理的全部报销任务。" />
          <StatCard label="正在收集" value={dashboardStats.openCount} description="优先在截止前提交或补充材料。" />
          <StatCard label="待补充或确认" value={dashboardStats.reviewCount} description="需要查看材料状态或确认费用的任务。" />
          <StatCard label="已进入归档" value={dashboardStats.archivedCount} description="主要用于查询结果和回看记录。" />
        </section>
      )}
    >
      {state.status === "loading" ? (
        <SectionCard title="正在加载成员可见任务" description="正在读取你参与的报销任务，请稍候。" />
      ) : null}

      {state.status === "error" ? <ApiErrorNotice error={state.error} /> : null}

      {state.status === "ready" && sortedVisibleTasks.length === 0 ? (
        <EmptyState
          title="当前没有可见报销任务"
          description="管理员创建并发布包含你的报销任务后，会在这里显示。"
        />
      ) : null}

      {state.status === "ready" && sortedVisibleTasks.length > 0 ? (
        <SectionCard
          title="任务列表"
          description="优先从这里进入单任务发票工作台；如需跳过汇总页，也可以直接执行当前下一步。"
          action={<StatusBadge tone="info">共 {sortedVisibleTasks.length} 条</StatusBadge>}
        >
          <TaskTable
            caption="成员任务列表"
            header={(
              <tr>
                <th>任务名称</th>
                <th>当前状态</th>
                <th>截止时间</th>
                <th>下一步</th>
                <th>操作</th>
              </tr>
            )}
          >
            {sortedVisibleTasks.map((task) => (
              <tr key={task.id}>
                <td>
                  <div className="table-primary">
                    <strong>{task.competition_name}</strong>
                    <span>{task.competition_location}</span>
                  </div>
                </td>
                <td>
                  <StatusBadge tone={buildStatusTone(task.status)}>{formatTaskStatus(task.status)}</StatusBadge>
                </td>
                <td>{formatDateTime(task.deadline)}</td>
                <td>{NEXT_ACTIONS[task.status]}</td>
                <td>
                  <div className="table-actions">
                    <Link className="button button-primary button-small" to={buildWorkbenchLink(task)}>
                      进入工作台
                    </Link>
                    <Link className="button button-secondary button-small" to={buildDirectActionLink(task)}>
                      {NEXT_ACTIONS[task.status]}
                    </Link>
                  </div>
                </td>
              </tr>
            ))}
          </TaskTable>
        </SectionCard>
      ) : null}
    </RoleWorkspace>
  );
}
