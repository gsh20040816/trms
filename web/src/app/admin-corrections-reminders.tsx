import { useEffect, useMemo, useState } from "react";
import { Link as RouterLink, useParams } from "react-router-dom";

import Button from "@mui/material/Button";
import TextField from "@mui/material/TextField";

import { ApiErrorNotice } from "../components/ApiErrorNotice";
import { TaskMemberAutocomplete } from "../components/task-member-autocomplete";
import { MetadataChip, PageHeader, StatusBadge, SurfaceCard } from "../components/dashboard";
import { trmsApi } from "../lib/api/trms";
import type {
  MaterialReminderRecord,
  ReimbursementTask,
} from "../lib/api/types";
import { buildTaskMemberSummaryMap, formatTaskMemberLabel } from "../lib/ui-text";
import { isTaskVisibleToAdministrator } from "../lib/task-administrators";
import { AdminWorkspaceShell } from "./admin-workspace-shell";
import { useAuthSession } from "./auth-store";

type CorrectionReminderPageState =
  | { status: "loading" }
  | { status: "error"; error: unknown }
  | {
      status: "ready";
      task: ReimbursementTask;
      reminders: MaterialReminderRecord[];
    };

type ReminderFormErrors = {
  memberId?: string;
  content?: string;
};

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function sortRemindersByCreatedAtDesc(items: MaterialReminderRecord[]) {
  return items.slice().sort((left, right) => right.created_at.localeCompare(left.created_at));
}

export function AdminCorrectionsRemindersPage() {
  const session = useAuthSession();
  const { taskId } = useParams<{ taskId: string }>();
  const [pageState, setPageState] = useState<CorrectionReminderPageState>({ status: "loading" });
  const [memberId, setMemberId] = useState("");
  const [content, setContent] = useState("");
  const [formErrors, setFormErrors] = useState<ReminderFormErrors>({});
  const [submitError, setSubmitError] = useState<unknown>(null);
  const [submitFeedback, setSubmitFeedback] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function loadPage() {
      if (!session || session.role !== "admin" || !taskId) {
        return;
      }

      setPageState({ status: "loading" });
      setSubmitError(null);

      try {
        const [task, reminderResponse] = await Promise.all([
          trmsApi.getTask(taskId),
          trmsApi.listTaskMaterialReminders(taskId, session.actorId),
        ]);

        if (cancelled) {
          return;
        }

        setPageState({
          status: "ready",
          task,
          reminders: sortRemindersByCreatedAtDesc(reminderResponse.items),
        });
        setMemberId((current) => {
          if (task.member_ids.includes(current)) {
            return current;
          }
          return task.member_ids[0] ?? "";
        });
      } catch (error) {
        if (cancelled) {
          return;
        }
        setPageState({
          status: "error",
          error,
        });
      }
    }

    void loadPage();

    return () => {
      cancelled = true;
    };
  }, [session, taskId]);

  const memberSummaryMap = useMemo(
    () => (
      pageState.status === "ready"
        ? buildTaskMemberSummaryMap(pageState.task.member_summaries)
        : new Map()
    ),
    [pageState],
  );

  if (!session || session.role !== "admin") {
    return null;
  }

  if (!taskId) {
    return (
      <div className="page-stack">
        <SurfaceCard component="section" className="status-card">
          <p className="eyebrow">任务缺失</p>
          <h2>任务标识缺失</h2>
          <p>当前路由未提供任务编号，无法进入人工更正与提醒页。</p>
        </SurfaceCard>
      </div>
    );
  }

  const task = pageState.status === "ready" ? pageState.task : null;
  const isForeignTask = task ? !isTaskVisibleToAdministrator(task, session.actorId) : false;
  const visibleTask = pageState.status === "ready" && !isForeignTask ? pageState.task : null;
  const visibleReminders = pageState.status === "ready" && !isForeignTask ? pageState.reminders : [];

  function handleReminderSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void submitReminder();
  }

  async function submitReminder() {
    if (!session || !taskId || !visibleTask) {
      return;
    }

    const nextErrors: ReminderFormErrors = {};
    if (!memberId.trim()) {
      nextErrors.memberId = "请选择提醒对象。";
    }
    if (!content.trim()) {
      nextErrors.content = "请输入提醒内容。";
    }
    setFormErrors(nextErrors);
    setSubmitError(null);
    setSubmitFeedback(null);
    if (nextErrors.memberId || nextErrors.content) {
      return;
    }

    setIsSubmitting(true);
    try {
      const reminder = await trmsApi.createTaskMaterialReminder(taskId, {
        administrator_id: session.actorId,
        member_id: memberId.trim(),
        content: content.trim(),
      });

      setPageState((current) => {
        if (current.status !== "ready") {
          return current;
        }
        return {
          ...current,
          reminders: sortRemindersByCreatedAtDesc([reminder, ...current.reminders]),
        };
      });
      setContent("");
      setFormErrors({});
      setSubmitFeedback(`已保存对${formatTaskMemberLabel(reminder.member_id, memberSummaryMap)}的内部提醒记录；系统不会自动发送消息。`);
    } catch (error) {
      setSubmitError(error);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <AdminWorkspaceShell
      activeModule="corrections"
      taskId={taskId}
      task={visibleTask}
      header={(
        <PageHeader
          eyebrow="成员提醒"
          title="管理员补材料提醒"
          description="在这里记录对成员的补材料提醒和确认说明，发票审核仍在材料审核页处理。"
          actions={(
            <div className="page-actions">
              <Button component={RouterLink} variant="outlined" to={`/admin/tasks/${taskId}/review`}>
                返回复核总览
              </Button>
              <Button component={RouterLink} variant="outlined" to={`/admin/tasks/${taskId}`}>
                返回任务详情
              </Button>
            </div>
          )}
        />
      )}
    >
      {pageState.status === "loading" ? (
        <SurfaceCard component="section" className="status-card admin-review-panel">
          <p className="eyebrow">成员提醒</p>
          <h2>正在加载成员提醒上下文</h2>
          <p>正在读取任务详情和补材料提醒记录，请稍候。</p>
        </SurfaceCard>
      ) : null}

      {pageState.status === "error" ? <ApiErrorNotice error={pageState.error} /> : null}
      {submitError ? <ApiErrorNotice error={submitError} /> : null}

      {pageState.status === "ready" && isForeignTask ? (
        <SurfaceCard component="section" className="status-card admin-review-panel">
          <p className="eyebrow">访问范围</p>
          <h2>当前任务不属于此管理员</h2>
          <p>你当前没有处理该任务的权限，如需访问请联系对应负责人。</p>
        </SurfaceCard>
      ) : null}

      {visibleTask ? (
        <SurfaceCard component="section" className="status-card admin-form-card">
            <div className="admin-form-header">
              <div>
                <p className="eyebrow">成员提醒</p>
                <h2>选择成员并记录提醒</h2>
              </div>
              <StatusBadge tone="info">{visibleReminders.length} 条已记录提醒</StatusBadge>
            </div>

            <p className="field-hint">
              先选择成员并记录提醒内容；发票审核、字段更正和分摊调整统一回到材料审核页处理。
            </p>

            <form onSubmit={handleReminderSubmit}>
              <div className="admin-form-grid">
                <TaskMemberAutocomplete
                  label="提醒对象成员"
                  value={memberId}
                  options={visibleTask.member_ids}
                  memberSummaries={visibleTask.member_summaries}
                  error={Boolean(formErrors.memberId)}
                  helperText={formErrors.memberId ?? undefined}
                  placeholder="输入成员姓名、用户名或学号筛选"
                  onChange={(nextValue) => {
                    setMemberId(nextValue);
                    setFormErrors((current) => ({ ...current, memberId: undefined }));
                  }}
                  disabled={visibleTask.member_ids.length === 0}
                />

                <TextField
                  className="admin-form-field-full"
                  label="提醒内容"
                  multiline
                  minRows={4}
                  value={content}
                  placeholder="例如：请补充支付记录和比赛通知，并在补交后重新确认金额。"
                  error={Boolean(formErrors.content)}
                  helperText={formErrors.content ?? "这里会记录提醒内容和时间，但不会自动代发短信、邮件或 Telegram 消息。"}
                  onChange={(event) => {
                    setContent(event.target.value);
                    setFormErrors((current) => ({ ...current, content: undefined }));
                  }}
                />
              </div>

              <div className="admin-form-footer">
                <p className="field-hint">系统只保存内部提醒记录，不会自动发送短信、邮件或 Telegram 消息；如需真正通知成员，请另行联系。</p>
                <Button variant="contained" type="submit" disabled={isSubmitting || visibleTask.member_ids.length === 0}>
                  {isSubmitting ? "保存中..." : "保存内部提醒记录"}
                </Button>
              </div>
            </form>

            {submitFeedback ? <p className="confirmation-feedback">{submitFeedback}</p> : null}

            <div className="admin-review-subsection">
              <h4>已记录提醒</h4>
              {visibleReminders.length > 0 ? (
                <ul className="admin-review-record-list" aria-label="补材料提醒列表">
                  {visibleReminders.map((reminder) => (
                    <SurfaceCard key={reminder.id} component="li" className="admin-review-record-card">
                      <div className="task-card-header">
                        <div>
                          <p className="task-card-id">补材料提醒</p>
                          <h3>{formatTaskMemberLabel(reminder.member_id, memberSummaryMap)}</h3>
                        </div>
                        <StatusBadge tone="info">已记录</StatusBadge>
                      </div>
                      <p>{reminder.content}</p>
                      <div className="admin-review-inline-metadata">
                        <MetadataChip component="span" className="token-chip" label={`记录时间 ${formatDateTime(reminder.created_at)}`} />
                      </div>
                    </SurfaceCard>
                  ))}
                </ul>
              ) : (
                <p className="field-hint">当前任务还没有已记录的补材料提醒。</p>
              )}
            </div>
        </SurfaceCard>
      ) : null}
    </AdminWorkspaceShell>
  );
}
