import type { ReactNode } from "react";
import { Link } from "react-router-dom";

import { StatusBadge } from "../components/dashboard";
import type { ReimbursementTask } from "../lib/api/types";
import { formatTaskStatus } from "../lib/ui-text";
import { describeAdminTaskStage } from "./admin-task-stage";

export type AdminModuleKey =
  | "overview"
  | "tasks"
  | "review"
  | "corrections"
  | "splits"
  | "exports";

type AdminWorkspaceShellProps = {
  activeModule: AdminModuleKey;
  taskId?: string | null;
  task?: ReimbursementTask | null;
  header: ReactNode;
  children: ReactNode;
};

type AdminModuleDefinition = {
  key: AdminModuleKey;
  title: string;
  description: string;
};

const ADMIN_MODULES: AdminModuleDefinition[] = [
  {
    key: "overview",
    title: "首页总览",
    description: "按任务推进查看当前最紧急的处理事项。",
  },
  {
    key: "tasks",
    title: "任务管理",
    description: "查看任务配置、成员范围和状态流转。",
  },
  {
    key: "review",
    title: "材料审核",
    description: "集中处理识别异常、缺失材料和复核问题。",
  },
  {
    key: "corrections",
    title: "成员提醒",
    description: "统一跟进成员补材料、更正和异议处理。",
  },
  {
    key: "splits",
    title: "分摊确认",
    description: "调整费用归属并跟踪成员确认状态。",
  },
  {
    key: "exports",
    title: "导出打印",
    description: "查看导出准备度并生成最终材料包。",
  },
];

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function buildModulePath(moduleKey: AdminModuleKey, taskId?: string | null) {
  switch (moduleKey) {
    case "overview":
      return "/admin";
    case "tasks":
      return taskId ? `/admin/tasks/${taskId}` : "/admin/tasks/new";
    case "review":
      return taskId ? `/admin/tasks/${taskId}/review` : null;
    case "corrections":
      return taskId ? `/admin/tasks/${taskId}/corrections` : null;
    case "splits":
      return taskId ? `/admin/tasks/${taskId}/splits` : null;
    case "exports":
      return taskId ? `/admin/tasks/${taskId}/exports` : null;
    default:
      return null;
  }
}

export function AdminWorkspaceShell({
  activeModule,
  taskId,
  task,
  header,
  children,
}: AdminWorkspaceShellProps) {
  const taskStage = task ? describeAdminTaskStage(task.status) : null;

  return (
    <div className="admin-workspace-shell">
      <aside className="admin-workspace-sidebar">
        <section className="panel-card admin-sidebar-panel">
          <div className="panel-card-header">
            <div>
              <p className="page-header-eyebrow">管理员工作台</p>
              <h2>任务推进导航</h2>
              <p>固定模块和当前任务上下文保持在同一位置，不再依赖页面内部跳转按钮。</p>
            </div>
            <StatusBadge tone="info">导航骨架</StatusBadge>
          </div>

          <nav className="admin-module-nav" aria-label="管理员模块导航">
            {ADMIN_MODULES.map((module) => {
              const path = buildModulePath(module.key, taskId);
              const isActive = module.key === activeModule;
              if (!path) {
                return (
                  <div
                    key={module.key}
                    className="admin-module-link admin-module-link-disabled"
                    aria-disabled="true"
                  >
                    <strong>{module.title}</strong>
                    <span>{module.description}</span>
                  </div>
                );
              }

              return (
                <Link
                  key={module.key}
                  className={`admin-module-link${isActive ? " admin-module-link-active" : ""}`}
                  to={path}
                  aria-current={isActive ? "page" : undefined}
                >
                  <strong>{module.title}</strong>
                  <span>{module.description}</span>
                </Link>
              );
            })}
          </nav>
        </section>

        <section className="panel-card admin-sidebar-panel" aria-label="当前任务上下文">
          <div className="panel-card-header">
            <div>
              <h2>当前任务上下文</h2>
              <p>把当前任务阶段、状态和快捷入口固定下来，避免处理过程中丢失上下文。</p>
            </div>
          </div>

          {task ? (
            <div className="admin-task-context">
              <div className="admin-task-context-header">
                <div>
                  <p className="task-card-id">任务编号 {task.id}</p>
                  <h3>{task.competition_name}</h3>
                </div>
                <StatusBadge tone={task.status === "ready_to_export" || task.status === "completed" ? "success" : "warning"}>
                  {formatTaskStatus(task.status)}
                </StatusBadge>
              </div>
              <dl className="admin-task-context-grid">
                <div>
                  <dt>当前阶段</dt>
                  <dd>{taskStage?.label}</dd>
                </div>
                <div>
                  <dt>截止时间</dt>
                  <dd>{formatDateTime(task.deadline)}</dd>
                </div>
              </dl>
              <p className="admin-task-context-summary">{taskStage?.summary}</p>
            </div>
          ) : (
            <div className="admin-task-context admin-task-context-empty">
              <h3>{taskId ? `任务 ${taskId}` : "尚未选中任务"}</h3>
              <p>{taskId ? "正在读取当前任务上下文或当前账号无权访问该任务。" : "先从首页选择任务，右侧模块就会自动带入当前任务上下文。"}</p>
            </div>
          )}

          {taskId ? (
            <div className="admin-context-actions" aria-label="当前任务快捷入口">
              <Link className="route-link route-link-secondary" to={`/admin/tasks/${taskId}`}>
                任务详情
              </Link>
              <Link className="route-link route-link-secondary" to={`/admin/tasks/${taskId}/review`}>
                材料审核
              </Link>
              <Link className="route-link route-link-secondary" to={`/admin/tasks/${taskId}/splits`}>
                分摊确认
              </Link>
              <Link className="route-link route-link-secondary" to={`/admin/tasks/${taskId}/exports`}>
                导出打印
              </Link>
            </div>
          ) : null}
        </section>
      </aside>

      <div className="admin-workspace-main">
        <div className="workspace-page">
          {header}
          {children}
        </div>
      </div>
    </div>
  );
}
