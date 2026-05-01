import { useEffect, useMemo, useState } from "react";
import { Link as RouterLink, useParams } from "react-router-dom";

import Button from "@mui/material/Button";
import TextField from "@mui/material/TextField";

import { ApiErrorNotice } from "../components/ApiErrorNotice";
import { InvoiceSummaryRow } from "../components/invoice-summary-row";
import { TaskMemberAutocomplete } from "../components/task-member-autocomplete";
import { PageHeader, StatusBadge } from "../components/dashboard";
import { trmsApi } from "../lib/api/trms";
import { formatCurrencyFromCents } from "../lib/currency";
import type {
  ExpenseType,
  MaterialReminderRecord,
  RecognitionTaskStatus,
  ReimbursementTask,
  TaskReviewSummary,
  ValidationResult,
} from "../lib/api/types";
import { buildTaskMemberSummaryMap, formatTaskMemberLabel } from "../lib/ui-text";
import { AdminWorkspaceShell } from "./admin-workspace-shell";
import { useAuthSession } from "./auth-store";

type CorrectionReminderPageState =
  | { status: "loading" }
  | { status: "error"; error: unknown }
  | {
      status: "ready";
      task: ReimbursementTask;
      summary: TaskReviewSummary;
      reminders: MaterialReminderRecord[];
    };

type ReminderFormErrors = {
  memberId?: string;
  content?: string;
};

type RecognitionCorrectionAction = {
  materialId: string;
  invoiceId: string | null;
  invoiceNumber: string | null;
  filename: string;
  submitterId: string | null;
  recognitionStatus: RecognitionTaskStatus | null;
  lowConfidenceFieldNames: string[];
  failureReason: string | null;
  createdAt: string;
};

type InvoiceCorrectionAction = {
  invoiceId: string;
  materialId: string;
  filename: string;
  invoiceNumber: string;
  amountCents: number;
  expenseType: ExpenseType;
  abnormalValidations: ValidationResult[];
  disputedSplitCount: number;
  pendingSplitCount: number;
  updatedAt: string;
};

const EXPENSE_TYPE_LABELS: Record<ExpenseType, string> = {
  registration: "参赛费",
  railway: "火车票",
  airfare: "航空费",
  local_transport: "市内交通",
  hotel: "住宿费",
  other: "其他",
};

const RECOGNITION_STATUS_LABELS: Record<RecognitionTaskStatus, string> = {
  pending: "识别中",
  succeeded: "识别成功",
  failed: "识别失败",
  needs_confirmation: "待人工确认",
};

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function formatExpenseType(expenseType: ExpenseType) {
  return EXPENSE_TYPE_LABELS[expenseType] ?? expenseType;
}

function formatRecognitionStatus(status: RecognitionTaskStatus | null) {
  if (status === null) {
    return "未触发识别";
  }
  return RECOGNITION_STATUS_LABELS[status];
}

function sortRemindersByCreatedAtDesc(items: MaterialReminderRecord[]) {
  return items.slice().sort((left, right) => right.created_at.localeCompare(left.created_at));
}

function buildRecognitionCorrectionActions(summary: TaskReviewSummary): RecognitionCorrectionAction[] {
  const invoiceItemsById = new Map(summary.invoices.map((item) => [item.invoice.id, item] as const));
  return summary.materials
    .filter((item) => item.material.material_type === "invoice")
    .map((item) => {
      const recognition = item.latest_recognition;
      const invoiceItem = item.invoice_id ? (invoiceItemsById.get(item.invoice_id) ?? null) : null;
      const lowConfidenceFieldNames = recognition
        ? Object.entries(recognition.recognized_fields)
          .filter(([, field]) => field.status === "needs_confirmation")
          .map(([fieldName]) => fieldName)
        : [];

      return {
        materialId: item.material.id,
        invoiceId: item.invoice_id,
        invoiceNumber: invoiceItem?.invoice.invoice_number ?? null,
        filename: item.material.original_filename,
        submitterId: item.material.submitter_id,
        recognitionStatus: recognition?.status ?? null,
        lowConfidenceFieldNames,
        failureReason: recognition?.failure
          ? `${recognition.failure.stage} / ${recognition.failure.reason}`
          : null,
        createdAt: item.material.created_at,
      };
    })
    .filter((item) => {
      return (
        item.invoiceId === null
        || item.recognitionStatus === "failed"
        || item.recognitionStatus === "needs_confirmation"
        || item.lowConfidenceFieldNames.length > 0
      );
    })
    .sort((left, right) => right.createdAt.localeCompare(left.createdAt));
}

function buildInvoiceCorrectionActions(summary: TaskReviewSummary): InvoiceCorrectionAction[] {
  return summary.invoices
    .map((invoiceItem) => {
      const abnormalValidations = invoiceItem.validations.filter(
        (validation) => validation.status !== "passed" && validation.status !== "not_applicable",
      );
      const disputedSplitCount = invoiceItem.splits.filter(
        ({ confirmation }) => confirmation?.status === "disputed",
      ).length;
      const pendingSplitCount = invoiceItem.splits.filter(
        ({ confirmation }) => confirmation === null || confirmation.status === "pending",
      ).length;

      return {
        invoiceId: invoiceItem.invoice.id,
        materialId: invoiceItem.invoice.material_id,
        filename: summary.materials.find((item) => item.material.id === invoiceItem.invoice.material_id)?.material.original_filename
          ?? invoiceItem.invoice.invoice_number,
        invoiceNumber: invoiceItem.invoice.invoice_number,
        amountCents: invoiceItem.invoice.amount_cents,
        expenseType: invoiceItem.invoice.expense_type,
        abnormalValidations,
        disputedSplitCount,
        pendingSplitCount,
        updatedAt: invoiceItem.invoice.updated_at,
      };
    })
    .filter((item) => {
      return item.abnormalValidations.length > 0 || item.disputedSplitCount > 0;
    })
    .sort((left, right) => right.updatedAt.localeCompare(left.updatedAt));
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
        const [task, summary, reminderResponse] = await Promise.all([
          trmsApi.getTask(taskId),
          trmsApi.getTaskReviewSummary(taskId, session.actorId),
          trmsApi.listTaskMaterialReminders(taskId, session.actorId),
        ]);

        if (cancelled) {
          return;
        }

        setPageState({
          status: "ready",
          task,
          summary,
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

  const recognitionActions = useMemo(
    () => (pageState.status === "ready" ? buildRecognitionCorrectionActions(pageState.summary) : []),
    [pageState],
  );
  const invoiceActions = useMemo(
    () => (pageState.status === "ready" ? buildInvoiceCorrectionActions(pageState.summary) : []),
    [pageState],
  );
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
        <section className="status-card">
          <p className="eyebrow">Task Missing</p>
          <h2>任务标识缺失</h2>
          <p>当前路由未提供任务编号，无法进入人工更正与提醒页。</p>
        </section>
      </div>
    );
  }

  const task = pageState.status === "ready" ? pageState.task : null;
  const isForeignTask = task ? task.administrator_id !== session.actorId : false;
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
          eyebrow="更正与提醒"
          title="管理员人工更正与补材料提醒"
          description="这里集中处理两件事：跳转到需要补录或更正的发票，以及记录对成员的补材料提醒。"
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
        <section className="status-card admin-review-panel">
          <p className="eyebrow">更正与提醒</p>
          <h2>正在加载更正与提醒上下文</h2>
          <p>正在读取任务详情、复核摘要和补材料提醒记录，请稍候。</p>
        </section>
      ) : null}

      {pageState.status === "error" ? <ApiErrorNotice error={pageState.error} /> : null}
      {submitError ? <ApiErrorNotice error={submitError} /> : null}

      {pageState.status === "ready" && isForeignTask ? (
        <section className="status-card admin-review-panel">
          <p className="eyebrow">访问范围</p>
          <h2>当前任务不属于此管理员</h2>
          <p>你当前没有处理该任务的权限，如需访问请联系对应负责人。</p>
        </section>
      ) : null}

      {visibleTask ? (
        <section className="task-detail-layout">
          <article className="status-card admin-review-panel">
            <div className="admin-form-header">
              <div>
                <p className="eyebrow">Corrections</p>
                <h2>待人工更正项</h2>
              </div>
              <StatusBadge tone="info">
                {recognitionActions.length + invoiceActions.length} 个处理入口
              </StatusBadge>
            </div>

            <div className="admin-review-subsection">
              <h4>识别字段待确认或待补录材料</h4>
              {recognitionActions.length > 0 ? (
                <ul className="admin-review-record-list" aria-label="识别字段更正列表">
                  {recognitionActions.map((item) => (
                    <li key={item.materialId} className="admin-review-record-card">
                      <div className="task-card-header">
                        <div>
                          <p className="task-card-id">待确认发票材料</p>
                          <h3>{item.filename}</h3>
                        </div>
                        <StatusBadge tone={item.recognitionStatus === "failed" ? "danger" : "warning"}>
                          {formatRecognitionStatus(item.recognitionStatus)}
                        </StatusBadge>
                      </div>
                      <div className="admin-review-inline-metadata">
                        <span className="token-chip">提交人 {item.submitterId ? formatTaskMemberLabel(item.submitterId, memberSummaryMap) : "未解析"}</span>
                        <span className="token-chip">
                          低置信度字段 {item.lowConfidenceFieldNames.length} 个
                        </span>
                      </div>
                      <div className="task-meta-grid admin-review-meta-grid">
                        <div>
                          <dt>已录入发票</dt>
                          <dd>{item.invoiceNumber ?? "未录入"}</dd>
                        </div>
                        <div>
                          <dt>上传时间</dt>
                          <dd>{formatDateTime(item.createdAt)}</dd>
                        </div>
                      </div>
                      {item.lowConfidenceFieldNames.length > 0 ? (
                        <p className="field-hint">
                          待确认字段：{item.lowConfidenceFieldNames.join("、")}
                        </p>
                      ) : null}
                      {item.failureReason ? (
                        <p className="field-hint">识别失败原因：{item.failureReason}</p>
                      ) : null}
                      <div className="inline-actions">
                        <Button
                          component={RouterLink}
                          variant="contained"
                          size="small"
                          to={`/admin/tasks/${taskId}/invoices?materialId=${encodeURIComponent(item.materialId)}`}
                        >
                          更正识别字段与金额
                        </Button>
                      </div>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="field-hint">当前复核摘要下没有需要人工确认识别字段的发票材料。</p>
              )}
            </div>

            <div className="admin-review-subsection">
              <h4>存在异常校验或异议的发票</h4>
              {invoiceActions.length > 0 ? (
                <ul className="admin-review-record-list" aria-label="金额更正列表">
                  {invoiceActions.map((item) => (
                    <li key={item.invoiceId} className="admin-review-record-card">
                      <InvoiceSummaryRow
                        filename={item.filename}
                        invoiceNumber={item.invoiceNumber}
                        amountLabel={formatCurrencyFromCents(item.amountCents)}
                        validationLabel={item.abnormalValidations.some((validation) => validation.status === "failed") ? "校验失败" : "校验待确认"}
                        validationTone="warning"
                        supportingMaterialCount={0}
                        statusHint={`待确认分摊 ${item.pendingSplitCount} 条；异议分摊 ${item.disputedSplitCount} 条`}
                        trailingContent={<StatusBadge tone="info">{formatExpenseType(item.expenseType)}</StatusBadge>}
                      />
                      <div className="admin-review-inline-metadata">
                        <span className="token-chip">{formatExpenseType(item.expenseType)}</span>
                        <span className="token-chip">异常校验 {item.abnormalValidations.length} 条</span>
                        <span className="token-chip">异议分摊 {item.disputedSplitCount} 条</span>
                      </div>
                      <div className="task-meta-grid admin-review-meta-grid">
                        <div>
                          <dt>待确认分摊</dt>
                          <dd>{item.pendingSplitCount}</dd>
                        </div>
                        <div>
                          <dt>最近更新时间</dt>
                          <dd>{formatDateTime(item.updatedAt)}</dd>
                        </div>
                      </div>
                      <ul className="admin-review-list" aria-label={`发票 ${item.invoiceNumber} 异常摘要`}>
                        {item.abnormalValidations.slice(0, 3).map((validation) => (
                          <li key={validation.id}>
                            <strong>{validation.rule_code}</strong>
                            <span>{validation.message}</span>
                          </li>
                        ))}
                        {item.abnormalValidations.length > 3 ? (
                          <li>
                            <strong>其他异常</strong>
                            <span>还有 {item.abnormalValidations.length - 3} 条异常校验未在此处展开。</span>
                          </li>
                        ) : null}
                      </ul>
                      <div className="inline-actions">
                        <Button
                          component={RouterLink}
                          variant="contained"
                          size="small"
                          to={`/admin/tasks/${taskId}/invoices?materialId=${encodeURIComponent(item.materialId)}`}
                        >
                          更正发票金额与字段
                        </Button>
                        <Button
                          component={RouterLink}
                          variant="outlined"
                          size="small"
                          to={`/admin/tasks/${taskId}/splits?invoiceId=${encodeURIComponent(item.invoiceId)}`}
                        >
                          调整当前发票分摊
                        </Button>
                      </div>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="field-hint">当前没有因异常校验或成员异议而需要优先更正的发票。</p>
              )}
            </div>
          </article>

          <article className="status-card admin-form-card">
            <div className="admin-form-header">
              <div>
                <p className="eyebrow">Reminders</p>
                <h2>记录补材料提醒</h2>
              </div>
              <StatusBadge tone="info">{visibleReminders.length} 条已记录提醒</StatusBadge>
            </div>

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
                  helperText={formErrors.content ?? "当前只记录管理员提醒内容与时间，不接入真实短信、邮件或 Telegram 发送。"}
                  onChange={(event) => {
                    setContent(event.target.value);
                    setFormErrors((current) => ({ ...current, content: undefined }));
                  }}
                />
              </div>

              <div className="admin-form-footer">
                <p className="field-hint">这里只保存内部提醒记录，不会自动发送短信、邮件或 Telegram 消息；如需真正通知成员，请另行联系。</p>
                <Button variant="contained" type="submit" disabled={isSubmitting || visibleTask.member_ids.length === 0}>
                  {isSubmitting ? "保存中..." : "保存内部提醒记录"}
                </Button>
              </div>
            </form>

            {submitFeedback ? <p className="confirmation-feedback">{submitFeedback}</p> : null}

            <div className="admin-review-subsection">
              <h4>已记录提醒</h4>
              {visibleReminders.length > 0 ? (
                <ul className="admin-review-list" aria-label="补材料提醒列表">
                  {visibleReminders.map((reminder) => (
                    <li key={reminder.id}>
                      <strong>{formatTaskMemberLabel(reminder.member_id, memberSummaryMap)}</strong>
                      <span>{reminder.content}</span>
                      <span>记录时间：{formatDateTime(reminder.created_at)}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="field-hint">当前任务还没有已记录的补材料提醒。</p>
              )}
            </div>
          </article>
        </section>
      ) : null}
    </AdminWorkspaceShell>
  );
}
