import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { ApiErrorNotice } from "../components/ApiErrorNotice";
import { trmsApi } from "../lib/api/trms";
import type { ReimbursementTask, TaskStatus } from "../lib/api/types";
import { formatMemberLabel, formatTaskStatus } from "../lib/ui-text";
import { useAuthSession } from "./auth-store";

type TaskDetailState =
  | { status: "loading" }
  | { status: "error"; error: unknown }
  | { status: "ready"; task: ReimbursementTask };

const TASK_STATUS_TRANSITIONS: Record<TaskStatus, TaskStatus[]> = {
  draft: ["open"],
  open: ["draft", "closed"],
  closed: ["open", "reviewing"],
  reviewing: ["open", "ready_to_export"],
  ready_to_export: ["completed"],
  completed: [],
};

const FEE_CATEGORY_LABELS: Record<string, string> = {
  registration: "参赛费",
  railway: "火车票",
  airfare: "航空费",
  local_transport: "市内交通",
  hotel: "住宿费",
  other: "其他",
};

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function formatFeeCategory(category: string) {
  return FEE_CATEGORY_LABELS[category] ?? category;
}

function buildStatusActionLabel(targetStatus: TaskStatus) {
  return `切换为${formatTaskStatus(targetStatus)}`;
}

export function AdminTaskDetailPage() {
  const session = useAuthSession();
  const { taskId } = useParams<{ taskId: string }>();
  const [state, setState] = useState<TaskDetailState>({ status: "loading" });
  const [statusUpdateError, setStatusUpdateError] = useState<unknown>(null);
  const [isUpdatingStatus, setIsUpdatingStatus] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function loadTask() {
      if (!session || session.role !== "admin" || !taskId) {
        return;
      }

      setState({ status: "loading" });
      setStatusUpdateError(null);

      try {
        const task = await trmsApi.getTask(taskId);
        if (cancelled) {
          return;
        }
        setState({
          status: "ready",
          task,
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

    void loadTask();

    return () => {
      cancelled = true;
    };
  }, [session, taskId]);

  if (!session || session.role !== "admin") {
    return null;
  }

  if (!taskId) {
    return (
      <div className="page-stack">
        <section className="status-card">
          <p className="eyebrow">任务详情</p>
          <h2>任务标识缺失</h2>
          <p>暂时无法读取该任务，请从任务列表重新进入。</p>
        </section>
      </div>
    );
  }

  const task = state.status === "ready" ? state.task : null;
  const allowedTransitions = task ? TASK_STATUS_TRANSITIONS[task.status] : [];
  const isForeignTask = task ? task.administrator_id !== session.actorId : false;
  const visibleTask = state.status === "ready" && !isForeignTask ? state.task : null;

  async function handleStatusUpdate(targetStatus: TaskStatus) {
    if (!task) {
      return;
    }

    setStatusUpdateError(null);
    setIsUpdatingStatus(true);
    try {
      const updatedTask = await trmsApi.updateTaskStatus(task.id, {
        target_status: targetStatus,
      });
      setState({
        status: "ready",
        task: updatedTask,
      });
    } catch (error) {
      setStatusUpdateError(error);
    } finally {
      setIsUpdatingStatus(false);
    }
  }

  return (
    <div className="page-stack">
      <section className="status-card admin-task-detail-hero">
        <p className="eyebrow">任务详情</p>
        <h2>任务详情与状态操作</h2>
        <p>
          这里集中查看任务信息、成员范围、费用类别和当前可执行的下一步操作。
        </p>
        <div className="inline-actions">
          <Link className="route-link route-link-secondary" to="/admin">
            返回任务列表
          </Link>
          {taskId ? (
            <>
              <Link className="route-link" to={`/admin/tasks/${taskId}/invoices`}>
                录入或更正发票
              </Link>
              <Link className="route-link route-link-secondary" to={`/admin/tasks/${taskId}/missing-materials`}>
                查看缺失材料
              </Link>
              <Link className="route-link route-link-secondary" to={`/admin/tasks/${taskId}/review`}>
                进入复核总览
              </Link>
              <Link className="route-link route-link-secondary" to={`/admin/tasks/${taskId}/exports`}>
                进入导出管理
              </Link>
              <Link className="route-link route-link-secondary" to={`/admin/tasks/${taskId}/splits`}>
                编辑费用分摊
              </Link>
            </>
          ) : null}
        </div>
      </section>

      {state.status === "loading" ? (
        <section className="status-card admin-task-detail-panel">
          <p className="eyebrow">Loading</p>
          <h2>正在加载任务详情</h2>
          <p>正在读取任务基础配置和当前状态，请稍候。</p>
        </section>
      ) : null}

      {state.status === "error" ? <ApiErrorNotice error={state.error} /> : null}
      {statusUpdateError ? <ApiErrorNotice error={statusUpdateError} /> : null}

      {state.status === "ready" && isForeignTask ? (
        <section className="status-card admin-task-detail-panel">
          <p className="eyebrow">访问范围</p>
          <h2>当前任务不属于此管理员</h2>
          <p>
            你当前没有处理该任务的权限，如需访问请联系对应负责人。
          </p>
        </section>
      ) : null}

      {visibleTask ? (
        <section className="task-detail-layout">
          <article className="status-card admin-task-detail-panel">
            <div className="task-card-header">
              <div>
                <p className="task-card-id">任务编号 {visibleTask.id}</p>
                <h2>{visibleTask.competition_name}</h2>
              </div>
              <span className={`status-chip task-status-chip task-status-${visibleTask.status}`}>
                {formatTaskStatus(visibleTask.status)}
              </span>
            </div>

            <dl className="task-detail-grid">
              <div>
                <dt>比赛地点</dt>
                <dd>{visibleTask.competition_location}</dd>
              </div>
              <div>
                <dt>比赛时间</dt>
                <dd>
                  {visibleTask.competition_start_date} 至 {visibleTask.competition_end_date}
                </dd>
              </div>
              <div>
                <dt>提交截止时间</dt>
                <dd>{formatDateTime(visibleTask.deadline)}</dd>
              </div>
              <div>
                <dt>任务负责人</dt>
                <dd>{session.displayName}</dd>
              </div>
              <div>
                <dt>项目/课题信息</dt>
                <dd>{visibleTask.project_info}</dd>
              </div>
              <div>
                <dt>报销人信息</dt>
                <dd>{visibleTask.reimburser_info}</dd>
              </div>
              <div>
                <dt>发票抬头</dt>
                <dd>{visibleTask.invoice_title}</dd>
              </div>
              <div>
                <dt>税号</dt>
                <dd>{visibleTask.tax_number}</dd>
              </div>
            </dl>
          </article>

          <article className="status-card admin-task-detail-panel">
            <div className="admin-form-header">
              <div>
                <p className="eyebrow">Members</p>
                <h2>成员名单</h2>
              </div>
              <span className="status-chip">{visibleTask.member_ids.length} 名成员</span>
            </div>
            <ul className="token-list" aria-label="任务成员名单">
              {visibleTask.member_ids.map((memberId) => (
                <li key={memberId} className="token-chip">
                  {formatMemberLabel(memberId)}
                </li>
              ))}
            </ul>
          </article>

          <article className="status-card admin-task-detail-panel">
            <div className="admin-form-header">
              <div>
                <p className="eyebrow">Fee Categories</p>
                <h2>允许费用类别</h2>
              </div>
              <span className="status-chip">{visibleTask.fee_categories.length} 类费用</span>
            </div>
            <ul className="token-list" aria-label="任务费用类别">
              {visibleTask.fee_categories.map((category) => (
                <li key={category} className="token-chip">
                  {formatFeeCategory(category)}
                </li>
              ))}
            </ul>
          </article>

          <article className="status-card admin-task-detail-panel">
            <div className="admin-form-header">
              <div>
                <p className="eyebrow">Status Actions</p>
                <h2>状态流转操作</h2>
              </div>
              <span className={`status-chip task-status-chip task-status-${visibleTask.status}`}>
                当前状态：{formatTaskStatus(visibleTask.status)}
              </span>
            </div>
            {allowedTransitions.length > 0 ? (
              <>
                <p className="field-hint">
                  只显示当前可执行的下一步操作。如果条件未满足，页面会给出可执行提示。
                </p>
                <div className="status-action-grid">
                  {allowedTransitions.map((targetStatus) => (
                    <button
                      key={targetStatus}
                      type="button"
                      className="route-link"
                      disabled={isUpdatingStatus}
                      onClick={() => {
                        void handleStatusUpdate(targetStatus);
                      }}
                    >
                      {isUpdatingStatus ? "正在提交状态更新..." : buildStatusActionLabel(targetStatus)}
                    </button>
                  ))}
                </div>
              </>
            ) : (
              <p className="field-hint">
                当前任务已经没有可继续推进的下一步操作，可返回任务列表查看其他事项。
              </p>
            )}
          </article>
        </section>
      ) : null}
    </div>
  );
}
