import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { ApiErrorNotice } from "../components/ApiErrorNotice";
import { trmsApi } from "../lib/api/trms";
import type { ReimbursementTask, TaskStatus } from "../lib/api/types";
import { useAuthSession } from "./auth-store";

type TaskDetailState =
  | { status: "loading" }
  | { status: "error"; error: unknown }
  | { status: "ready"; task: ReimbursementTask };

const TASK_STATUS_LABELS: Record<TaskStatus, string> = {
  draft: "草稿",
  open: "开放提交",
  closed: "已关闭",
  reviewing: "复核中",
  ready_to_export: "可导出",
  completed: "已归档",
};

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

function formatTaskStatus(status: TaskStatus) {
  return TASK_STATUS_LABELS[status];
}

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
          <p className="eyebrow">Task Missing</p>
          <h2>任务标识缺失</h2>
          <p>当前路由未提供任务编号，无法读取详情。</p>
        </section>
      </div>
    );
  }

  const task = state.status === "ready" ? state.task : null;
  const allowedTransitions = task ? TASK_STATUS_TRANSITIONS[task.status] : [];
  const isForeignTask = task ? task.administrator_id !== session.actorId : false;
  const foreignTaskAdministratorId = isForeignTask && task ? task.administrator_id : null;
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
        <p className="eyebrow">Admin Task Detail</p>
        <h2>任务详情与状态操作</h2>
        <p>
          本页聚焦管理员查看单个任务的基础配置，并直接调用现有
          `GET /api/tasks/{taskId}` 与 `PATCH /api/tasks/{taskId}/status`
          接口执行状态流转。
        </p>
        <p className="status-note">
          当前仍使用 mock 管理员身份 {session.displayName}（{session.actorId}）。若后端拒绝状态流转，本页会直接展示服务端返回的失败原因，不在前端伪装成功。
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
          <p className="eyebrow">Access Scope</p>
          <h2>当前任务不属于此管理员</h2>
          <p>
            当前任务的 `administrator_id` 为 {foreignTaskAdministratorId}，与当前 mock 管理员
            {session.actorId} 不一致。为避免在真实鉴权接入前误操作，这里不展示状态流转按钮。
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
                <dt>管理员标识</dt>
                <dd>{visibleTask.administrator_id}</dd>
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
                  {memberId}
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
                  当前页只展示后端状态机允许的下一步操作；若任务仍缺少发布条件、复核条件或导出完成记录，后端会返回明确的 `409` 错误。
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
                当前状态已经没有前端可继续触发的下一步流转。如需进入 `completed`，仍需后端先记录导出完成事实。
              </p>
            )}
          </article>
        </section>
      ) : null}
    </div>
  );
}
