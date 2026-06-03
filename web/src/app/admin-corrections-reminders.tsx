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
  TaskMemberSummary,
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
  memberIds?: string;
  content?: string;
  emailSubject?: string;
  emailBody?: string;
};

type TaskMemberSummaryMap = ReturnType<typeof buildTaskMemberSummaryMap>;

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function sortRemindersByCreatedAtDesc(items: MaterialReminderRecord[]) {
  return items.slice().sort((left, right) => right.created_at.localeCompare(left.created_at));
}

function buildDefaultReminderSubject(task: ReimbursementTask) {
  return `TRMS 报销任务提醒：${task.competition_name}`.slice(0, 255);
}

function formatSelectedMembers(
  memberIds: string[],
  memberSummaryMap: TaskMemberSummaryMap,
) {
  if (memberIds.length === 0) {
    return "尚未选择成员";
  }
  if (memberIds.length <= 3) {
    return memberIds.map((memberId) => formatTaskMemberLabel(memberId, memberSummaryMap)).join("、");
  }
  const visibleLabels = memberIds
    .slice(0, 3)
    .map((memberId) => formatTaskMemberLabel(memberId, memberSummaryMap))
    .join("、");
  return `${visibleLabels} 等 ${memberIds.length} 名成员`;
}

function buildDefaultReminderBody(
  task: ReimbursementTask,
  memberIds: string[],
  memberSummaryMap: TaskMemberSummaryMap,
  content: string,
) {
  const reminderContent = content.trim() || "请根据管理员要求补充材料或确认费用。";
  return [
    "这是一封 TRMS 自动化提醒邮件，无需直接回复本邮件。",
    "",
    `任务：${task.competition_name}`,
    `任务编号：${task.id}`,
    `提醒对象：${formatSelectedMembers(memberIds, memberSummaryMap)}`,
    "",
    "提醒内容：",
    reminderContent,
    "",
    "请登录 TRMS 查看任务详情，并按提醒补充材料或确认费用。",
    "如果你已经完成相关操作，请忽略这封邮件。",
  ].join("\n");
}

function getReminderDeliveryTone(reminder: MaterialReminderRecord) {
  if (reminder.email_delivery_status === "sent") {
    return "success" as const;
  }
  if (reminder.email_delivery_status === "failed") {
    return "danger" as const;
  }
  if (reminder.email_delivery_status === "pending") {
    return "warning" as const;
  }
  return "info" as const;
}

function getReminderDeliveryText(reminder: MaterialReminderRecord) {
  if (reminder.email_delivery_status === "sent") {
    return "邮件已发送";
  }
  if (reminder.email_delivery_status === "failed") {
    return "邮件发送失败";
  }
  if (reminder.email_delivery_status === "pending") {
    return "邮件待发送";
  }
  return "仅记录";
}

export function AdminCorrectionsRemindersPage() {
  const session = useAuthSession();
  const { taskId } = useParams<{ taskId: string }>();
  const [pageState, setPageState] = useState<CorrectionReminderPageState>({ status: "loading" });
  const [memberIds, setMemberIds] = useState<string[]>([]);
  const [memberPickerValue, setMemberPickerValue] = useState("");
  const [content, setContent] = useState("");
  const [emailSubject, setEmailSubject] = useState("");
  const [emailBody, setEmailBody] = useState("");
  const [emailSubjectEdited, setEmailSubjectEdited] = useState(false);
  const [emailBodyEdited, setEmailBodyEdited] = useState(false);
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
        setMemberIds((current) => current.filter((memberId) => task.member_ids.includes(memberId)));
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
        : new Map<string, TaskMemberSummary>()
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
  const currentEmailSubject = visibleTask && !emailSubjectEdited
    ? buildDefaultReminderSubject(visibleTask)
    : emailSubject;
  const currentEmailBody = visibleTask && !emailBodyEdited
    ? buildDefaultReminderBody(visibleTask, memberIds, memberSummaryMap, content)
    : emailBody;

  function handleReminderSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void submitReminder();
  }

  async function submitReminder() {
    if (!session || !taskId || !visibleTask) {
      return;
    }

    const nextErrors: ReminderFormErrors = {};
    if (memberIds.length === 0) {
      nextErrors.memberIds = "请选择至少一名提醒对象。";
    }
    if (!content.trim()) {
      nextErrors.content = "请输入提醒内容。";
    }
    if (!currentEmailSubject.trim()) {
      nextErrors.emailSubject = "请输入邮件主题。";
    }
    if (!currentEmailBody.trim()) {
      nextErrors.emailBody = "请输入邮件正文。";
    }
    setFormErrors(nextErrors);
    setSubmitError(null);
    setSubmitFeedback(null);
    if (nextErrors.memberIds || nextErrors.content || nextErrors.emailSubject || nextErrors.emailBody) {
      return;
    }

    setIsSubmitting(true);
    try {
      const response = await trmsApi.createTaskMaterialReminder(taskId, {
        administrator_id: session.actorId,
        member_ids: memberIds,
        content: content.trim(),
        email_subject: currentEmailSubject.trim(),
        email_body: currentEmailBody.trim(),
      });
      const reminders = response.items;

      setPageState((current) => {
        if (current.status !== "ready") {
          return current;
        }
        return {
          ...current,
          reminders: sortRemindersByCreatedAtDesc([...reminders, ...current.reminders]),
        };
      });
      const sentCount = reminders.filter((reminder) => reminder.email_delivery_status === "sent").length;
      const failedCount = reminders.filter((reminder) => reminder.email_delivery_status === "failed").length;
      setMemberIds([]);
      setContent("");
      setEmailSubjectEdited(false);
      setEmailBodyEdited(false);
      setFormErrors({});
      setSubmitFeedback(`已记录 ${reminders.length} 条提醒；邮件发送成功 ${sentCount} 封，失败 ${failedCount} 封。`);
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
          description="在这里选择一个或多个成员，编辑提醒邮件内容，并发送到成员的 primary 邮箱。"
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
              系统会使用成员最早绑定的邮箱作为 primary 邮箱；没有 primary 邮箱或邮件配置异常时，会记录失败原因。
            </p>

            <form onSubmit={handleReminderSubmit}>
              <div className="admin-form-grid">
                <TaskMemberAutocomplete
                  label="提醒对象成员"
                  value={memberPickerValue}
                  options={visibleTask.member_ids.filter((candidateId) => !memberIds.includes(candidateId))}
                  memberSummaries={visibleTask.member_summaries}
                  error={Boolean(formErrors.memberIds)}
                  helperText={formErrors.memberIds ?? `已选择 ${memberIds.length} 名成员，可继续搜索并追加。`}
                  placeholder="输入成员姓名、用户名或学号筛选"
                  includeEmptyOption
                  emptyOptionLabel="继续选择成员"
                  onChange={(nextValue) => {
                    if (!nextValue) {
                      setMemberPickerValue("");
                      return;
                    }
                    setMemberIds((current) => (
                      current.includes(nextValue) ? current : [...current, nextValue]
                    ));
                    setMemberPickerValue("");
                    setFormErrors((current) => ({ ...current, memberIds: undefined }));
                  }}
                  disabled={visibleTask.member_ids.length === 0}
                />
                <div className="admin-review-inline-metadata admin-form-field-full" aria-label="已选提醒对象">
                  {memberIds.length > 0 ? (
                    memberIds.map((selectedMemberId) => (
                      <MetadataChip
                        key={selectedMemberId}
                        component="span"
                        className="token-chip"
                        label={formatTaskMemberLabel(selectedMemberId, memberSummaryMap)}
                        onDelete={() => {
                          setMemberIds((current) => current.filter((item) => item !== selectedMemberId));
                        }}
                      />
                    ))
                  ) : (
                    <p className="field-hint">当前还没有选择提醒对象。</p>
                  )}
                </div>

                <TextField
                  className="admin-form-field-full"
                  label="提醒内容"
                  multiline
                  minRows={4}
                  value={content}
                  placeholder="例如：请补充支付记录和比赛通知，并在补交后重新确认金额。"
                  error={Boolean(formErrors.content)}
                  helperText={formErrors.content ?? "提醒内容会进入内部记录，并默认写入邮件正文。"}
                  onChange={(event) => {
                    setContent(event.target.value);
                    setFormErrors((current) => ({ ...current, content: undefined }));
                  }}
                />

                <TextField
                  className="admin-form-field-full"
                  label="邮件主题"
                  value={currentEmailSubject}
                  error={Boolean(formErrors.emailSubject)}
                  helperText={formErrors.emailSubject ?? "管理员可编辑发送给成员的邮件主题。"}
                  onChange={(event) => {
                    setEmailSubject(event.target.value);
                    setEmailSubjectEdited(true);
                    setFormErrors((current) => ({ ...current, emailSubject: undefined }));
                  }}
                />

                <TextField
                  className="admin-form-field-full"
                  label="邮件正文"
                  multiline
                  minRows={8}
                  value={currentEmailBody}
                  error={Boolean(formErrors.emailBody)}
                  helperText={formErrors.emailBody ?? "默认包含自动化邮件、无需回复、任务、提醒对象和处理指引；发送前可编辑。"}
                  onChange={(event) => {
                    setEmailBody(event.target.value);
                    setEmailBodyEdited(true);
                    setFormErrors((current) => ({ ...current, emailBody: undefined }));
                  }}
                />
              </div>

              <div className="admin-form-footer">
                <p className="field-hint">提交后会创建提醒记录并尝试发送邮件；每名成员的发送结果会保存在下方列表。</p>
                <Button variant="contained" type="submit" disabled={isSubmitting || visibleTask.member_ids.length === 0}>
                  {isSubmitting ? "发送中..." : "发送提醒邮件"}
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
                        <StatusBadge tone={getReminderDeliveryTone(reminder)}>
                          {getReminderDeliveryText(reminder)}
                        </StatusBadge>
                      </div>
                      <p>{reminder.content}</p>
                      <div className="admin-review-inline-metadata">
                        <MetadataChip component="span" className="token-chip" label={`记录时间 ${formatDateTime(reminder.created_at)}`} />
                        {reminder.email_recipient ? (
                          <MetadataChip component="span" className="token-chip" label={`primary 邮箱 ${reminder.email_recipient}`} />
                        ) : null}
                        {reminder.email_sent_at ? (
                          <MetadataChip component="span" className="token-chip" label={`发送时间 ${formatDateTime(reminder.email_sent_at)}`} />
                        ) : null}
                        {reminder.email_failure_reason ? (
                          <MetadataChip component="span" className="token-chip" color="error" label={`失败原因 ${reminder.email_failure_reason}`} />
                        ) : null}
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
