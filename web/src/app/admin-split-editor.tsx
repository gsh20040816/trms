import { useEffect, useRef, useState } from "react";
import { Link as RouterLink, useParams, useSearchParams } from "react-router-dom";
import Button from "@mui/material/Button";
import TextField from "@mui/material/TextField";

import { ApiErrorNotice } from "../components/ApiErrorNotice";
import { InvoiceSummaryRow } from "../components/invoice-summary-row";
import { TaskMemberAutocomplete } from "../components/task-member-autocomplete";
import { useConfirmDialog } from "../components/use-confirm-dialog";
import { PageHeader, StatusBadge } from "../components/dashboard";
import { trmsApi } from "../lib/api/trms";
import type {
  ConfirmationStatus,
  ReimbursementTask,
  TaskReviewSummary,
  TaskReviewSummaryInvoiceItem,
  TaskReviewSummaryMaterialItem,
} from "../lib/api/types";
import { buildTaskMemberSummaryMap, formatTaskMemberLabel } from "../lib/ui-text";
import { AdminWorkspaceShell } from "./admin-workspace-shell";
import { useAuthSession } from "./auth-store";

type SplitEditorPageState =
  | { status: "loading" }
  | { status: "error"; error: unknown }
  | { status: "ready"; task: ReimbursementTask; summary: TaskReviewSummary };

type SplitInvoiceItem = {
  invoiceItem: TaskReviewSummaryInvoiceItem;
  materialItem: TaskReviewSummaryMaterialItem | null;
};

type SplitFormRow = {
  rowId: string;
  memberId: string;
  amountYuan: string;
  note: string;
};

type SplitFormRowError = {
  memberId?: string;
  amountYuan?: string;
};

type SplitFormErrors = Record<string, SplitFormRowError>;

type SaveFeedback = {
  invoiceId: string;
  splitCount: number;
  totalAmountCents: number;
};

const CONFIRMATION_STATUS_LABELS: Record<ConfirmationStatus, string> = {
  pending: "待确认",
  confirmed: "已确认",
  disputed: "有异议",
};

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function formatCurrencyFromCents(cents: number) {
  return `￥${(cents / 100).toFixed(2)}`;
}

function formatAmountInputFromCents(cents: number) {
  return (cents / 100).toFixed(2);
}

function parseAmountYuanToCents(value: string) {
  const normalizedValue = value.trim();
  if (!normalizedValue) {
    return null;
  }

  const amount = Number(normalizedValue);
  if (!Number.isFinite(amount) || amount <= 0) {
    return null;
  }
  return Math.round(amount * 100);
}

function buildSplitInvoiceItems(summary: TaskReviewSummary): SplitInvoiceItem[] {
  const materialItemsById = new Map(
    summary.materials.map((item) => [item.material.id, item] as const),
  );

  return summary.invoices
    .map((invoiceItem) => ({
      invoiceItem,
      materialItem: materialItemsById.get(invoiceItem.invoice.material_id) ?? null,
    }))
    .sort((left, right) => {
      const leftTime = left.materialItem
        ? new Date(left.materialItem.material.created_at).getTime()
        : new Date(left.invoiceItem.invoice.updated_at).getTime();
      const rightTime = right.materialItem
        ? new Date(right.materialItem.material.created_at).getTime()
        : new Date(right.invoiceItem.invoice.updated_at).getTime();
      return rightTime - leftTime;
    });
}

function pickSelectedInvoiceId(
  items: SplitInvoiceItem[],
  preferredInvoiceId: string | null,
  currentInvoiceId: string,
) {
  const visibleInvoiceIds = new Set(items.map((item) => item.invoiceItem.invoice.id));
  if (currentInvoiceId && visibleInvoiceIds.has(currentInvoiceId)) {
    return currentInvoiceId;
  }
  if (preferredInvoiceId && visibleInvoiceIds.has(preferredInvoiceId)) {
    return preferredInvoiceId;
  }
  return items[0]?.invoiceItem.invoice.id ?? "";
}

function findSelectedInvoiceItem(items: SplitInvoiceItem[], invoiceId: string) {
  return items.find((item) => item.invoiceItem.invoice.id === invoiceId) ?? null;
}

function pickDefaultMemberId(item: SplitInvoiceItem, task: ReimbursementTask) {
  const submitterId = item.materialItem?.material.submitter_id;
  if (submitterId && task.member_ids.includes(submitterId)) {
    return submitterId;
  }
  return task.member_ids[0] ?? "";
}

function buildInitialRows(
  item: SplitInvoiceItem,
  task: ReimbursementTask,
  createRowId: () => string,
): SplitFormRow[] {
  if (item.invoiceItem.splits.length > 0) {
    return item.invoiceItem.splits.map(({ split }) => ({
      rowId: createRowId(),
      memberId: split.member_id,
      amountYuan: formatAmountInputFromCents(split.amount_cents),
      note: split.note ?? "",
    }));
  }

  return [
    {
      rowId: createRowId(),
      memberId: pickDefaultMemberId(item, task),
      amountYuan: formatAmountInputFromCents(item.invoiceItem.invoice.amount_cents),
      note: "",
    },
  ];
}

function buildSummaryRows(rows: SplitFormRow[]) {
  let totalAmountCents = 0;
  let invalidRowCount = 0;

  for (const row of rows) {
    const amountCents = parseAmountYuanToCents(row.amountYuan);
    if (amountCents === null) {
      invalidRowCount += 1;
      continue;
    }
    totalAmountCents += amountCents;
  }

  return {
    totalAmountCents,
    invalidRowCount,
  };
}

function validateRows(rows: SplitFormRow[]): SplitFormErrors {
  const errors: SplitFormErrors = {};

  for (const row of rows) {
    const rowErrors: SplitFormRowError = {};
    if (!row.memberId.trim()) {
      rowErrors.memberId = "请选择归属成员。";
    }
    if (parseAmountYuanToCents(row.amountYuan) === null) {
      rowErrors.amountYuan = "请输入大于 0 的金额，单位为元。";
    }
    if (rowErrors.memberId || rowErrors.amountYuan) {
      errors[row.rowId] = rowErrors;
    }
  }

  return errors;
}

function countFailedValidations(item: TaskReviewSummaryInvoiceItem) {
  return item.validations.filter((validation) => validation.status === "failed").length;
}

function countPendingValidations(item: TaskReviewSummaryInvoiceItem) {
  return item.validations.filter((validation) => validation.status === "pending").length;
}

function buildInvoiceSummaryValidation(item: TaskReviewSummaryInvoiceItem) {
  if (countFailedValidations(item) > 0) {
    return { label: "校验失败", tone: "warning" as const };
  }
  if (countPendingValidations(item) > 0) {
    return { label: "校验待确认", tone: "warning" as const };
  }
  return { label: "校验通过", tone: "success" as const };
}

function formatConfirmationStatus(status: ConfirmationStatus) {
  return CONFIRMATION_STATUS_LABELS[status];
}

function countCurrentConfirmationStatus(
  item: TaskReviewSummaryInvoiceItem,
  targetStatus: ConfirmationStatus,
) {
  return item.splits.filter(({ confirmation }) => confirmation?.is_current && confirmation.status === targetStatus)
    .length;
}

export function AdminSplitEditorPage() {
  const session = useAuthSession();
  const { confirm } = useConfirmDialog();
  const { taskId } = useParams<{ taskId: string }>();
  const [searchParams] = useSearchParams();
  const preferredInvoiceId = searchParams.get("invoiceId");
  const [pageState, setPageState] = useState<SplitEditorPageState>({ status: "loading" });
  const [selectedInvoiceId, setSelectedInvoiceId] = useState("");
  const [formRows, setFormRows] = useState<SplitFormRow[]>([]);
  const [formErrors, setFormErrors] = useState<SplitFormErrors>({});
  const [submitError, setSubmitError] = useState<unknown>(null);
  const [saveFeedback, setSaveFeedback] = useState<SaveFeedback | null>(null);
  const [refreshNonce, setRefreshNonce] = useState(0);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const selectedInvoiceIdRef = useRef(selectedInvoiceId);
  const nextRowSequenceRef = useRef(0);

  function createRowId() {
    const rowId = `split-row-${nextRowSequenceRef.current}`;
    nextRowSequenceRef.current += 1;
    return rowId;
  }

  useEffect(() => {
    selectedInvoiceIdRef.current = selectedInvoiceId;
  }, [selectedInvoiceId]);

  useEffect(() => {
    let cancelled = false;

    async function loadPage() {
      if (!session || session.role !== "admin" || !taskId) {
        return;
      }

      setPageState({ status: "loading" });
      setSubmitError(null);

      try {
        const [task, summary] = await Promise.all([
          trmsApi.getTask(taskId),
          trmsApi.getTaskReviewSummary(taskId, session.actorId),
        ]);

        if (cancelled) {
          return;
        }

        const nextItems = buildSplitInvoiceItems(summary);
        const nextSelectedInvoiceId = pickSelectedInvoiceId(
          nextItems,
          preferredInvoiceId,
          selectedInvoiceIdRef.current,
        );
        const nextSelectedItem = findSelectedInvoiceItem(nextItems, nextSelectedInvoiceId);

        setPageState({
          status: "ready",
          task,
          summary,
        });
        setSelectedInvoiceId(nextSelectedInvoiceId);
        setFormRows(nextSelectedItem ? buildInitialRows(nextSelectedItem, task, createRowId) : []);
        setFormErrors({});
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
  }, [preferredInvoiceId, refreshNonce, session, taskId]);

  const splitInvoiceItems = pageState.status === "ready"
    ? buildSplitInvoiceItems(pageState.summary)
    : [];

  if (!session || session.role !== "admin") {
    return null;
  }

  if (!taskId) {
    return (
      <AdminWorkspaceShell
        activeModule="splits"
        header={(
          <PageHeader
            eyebrow="分摊确认"
            title="费用分摊编辑"
            description="维护发票分摊对象、金额和确认状态。"
          />
        )}
      >
        <section className="status-card">
          <p className="eyebrow">Task Missing</p>
          <h2>任务标识缺失</h2>
          <p>当前路由未提供任务编号，无法进入费用分摊编辑页。</p>
        </section>
      </AdminWorkspaceShell>
    );
  }

  const task = pageState.status === "ready" ? pageState.task : null;
  const isForeignTask = task ? task.administrator_id !== session.actorId : false;
  const visibleTask = pageState.status === "ready" && !isForeignTask ? pageState.task : null;
  const visibleSummary = pageState.status === "ready" && !isForeignTask ? pageState.summary : null;
  const memberSummaryMap = visibleTask ? buildTaskMemberSummaryMap(visibleTask.member_summaries) : new Map();
  const selectedInvoiceItem = visibleSummary
    ? findSelectedInvoiceItem(splitInvoiceItems, selectedInvoiceId)
    : null;
  const splitSummary = buildSummaryRows(formRows);
  const selectedInvoice = selectedInvoiceItem?.invoiceItem.invoice ?? null;
  const selectedMaterial = selectedInvoiceItem?.materialItem?.material ?? null;
  const amountDifferenceCents = selectedInvoice
    ? splitSummary.totalAmountCents - selectedInvoice.amount_cents
    : 0;

  function updateRow(
    rowId: string,
    field: keyof Omit<SplitFormRow, "rowId">,
    value: string,
  ) {
    setFormRows((current) => current.map((row) => (row.rowId === rowId ? { ...row, [field]: value } : row)));
    setFormErrors((current) => {
      const rowErrors = current[rowId];
      if (!rowErrors) {
        return current;
      }

      const nextRowErrors = { ...rowErrors };
      if (field === "memberId") {
        delete nextRowErrors.memberId;
      }
      if (field === "amountYuan") {
        delete nextRowErrors.amountYuan;
      }

      const nextErrors = { ...current };
      if (!nextRowErrors.memberId && !nextRowErrors.amountYuan) {
        delete nextErrors[rowId];
      } else {
        nextErrors[rowId] = nextRowErrors;
      }
      return nextErrors;
    });
  }

  function handleSelectInvoice(item: SplitInvoiceItem) {
    if (!visibleTask) {
      return;
    }
    setSelectedInvoiceId(item.invoiceItem.invoice.id);
    setFormRows(buildInitialRows(item, visibleTask, createRowId));
    setFormErrors({});
    setSubmitError(null);
    setSaveFeedback(null);
  }

  function handleAddRow() {
    if (!visibleTask || !selectedInvoiceItem) {
      return;
    }

    setFormRows((current) => [
      ...current,
      {
        rowId: createRowId(),
        memberId: pickDefaultMemberId(selectedInvoiceItem, visibleTask),
        amountYuan: "",
        note: "",
      },
    ]);
  }

  async function handleRemoveRow(rowId: string, rowIndex: number) {
    if (formRows.length <= 1 || !selectedInvoice || !visibleTask) {
      return;
    }

    const confirmed = await confirm({
      title: `确认删除分摊行 ${rowIndex}？`,
      description: `当前正在编辑任务 ${visibleTask.competition_name}（${visibleTask.id}）下发票 ${selectedInvoice.invoice_number} 的分摊方案。删除后，这一行尚未保存的成员、金额和备注会直接丢失。`,
      confirmLabel: "删除分摊行",
      cancelLabel: "继续编辑",
      destructive: true,
    });
    if (!confirmed) {
      return;
    }

    setFormRows((current) => {
      if (current.length <= 1) {
        return current;
      }
      return current.filter((row) => row.rowId !== rowId);
    });
    setFormErrors((current) => {
      if (!(rowId in current)) {
        return current;
      }
      const next = { ...current };
      delete next[rowId];
      return next;
    });
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!session || !selectedInvoiceItem || formRows.length === 0 || !visibleTask || !selectedInvoice) {
      return;
    }

    const nextErrors = validateRows(formRows);
    setFormErrors(nextErrors);
    setSubmitError(null);
    if (Object.keys(nextErrors).length > 0) {
      return;
    }

    const confirmed = await confirm({
      title: amountDifferenceCents === 0 ? "确认覆盖保存当前分摊方案？" : "确认保存未闭合的分摊方案？",
      description: amountDifferenceCents === 0
        ? `任务 ${visibleTask.competition_name}（${visibleTask.id}）的发票 ${selectedInvoice.invoice_number} 将按当前表单覆盖保存 ${formRows.length} 条分摊。服务端可能把受影响成员的确认状态重置为待确认，请确认金额和归属成员已核对无误。`
        : amountDifferenceCents > 0
          ? `任务 ${visibleTask.competition_name}（${visibleTask.id}）的发票 ${selectedInvoice.invoice_number} 当前分摊合计比票面金额多出 ${formatCurrencyFromCents(amountDifferenceCents)}。这会留下超额报销风险；确认后仍会保存，但该发票会继续保留“分摊未完成”门禁。`
          : `任务 ${visibleTask.competition_name}（${visibleTask.id}）的发票 ${selectedInvoice.invoice_number} 当前分摊合计比票面金额少了 ${formatCurrencyFromCents(Math.abs(amountDifferenceCents))}。这表示仍有未报销金额；确认后仍会保存，但该发票会继续保留“分摊未完成”门禁。`,
      confirmLabel: "确认保存分摊",
      cancelLabel: "继续编辑",
      destructive: true,
    });
    if (!confirmed) {
      return;
    }

    setIsSubmitting(true);
    try {
      const response = await trmsApi.replaceInvoiceSplits(selectedInvoiceItem.invoiceItem.invoice.id, {
        actor_id: session.actorId,
        items: formRows.map((row) => ({
          member_id: row.memberId.trim(),
          amount_cents: parseAmountYuanToCents(row.amountYuan) ?? 0,
          note: row.note.trim() || null,
        })),
      });

      const totalAmountCents = response.items.reduce((sum, item) => sum + item.amount_cents, 0);
      setSaveFeedback({
        invoiceId: selectedInvoiceItem.invoiceItem.invoice.id,
        splitCount: response.items.length,
        totalAmountCents,
      });
      setRefreshNonce((current) => current + 1);
    } catch (error) {
      setSubmitError(error);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <AdminWorkspaceShell
      activeModule="splits"
      taskId={taskId}
      task={visibleTask}
      header={(
        <PageHeader
          eyebrow="分摊确认"
          title="费用分摊编辑"
          description="在这里为单张发票维护归属成员和分摊金额，并检查总额是否一致。"
          actions={(
            <div className="page-actions">
              <Button component={RouterLink} variant="outlined" to={`/admin/tasks/${taskId}`}>
                返回任务详情
              </Button>
              <Button component={RouterLink} variant="outlined" to={`/admin/tasks/${taskId}/invoices`}>
                返回发票录入
              </Button>
            </div>
          )}
        />
      )}
    >

      {pageState.status === "loading" ? (
        <section className="status-card admin-task-detail-panel">
          <p className="eyebrow">费用分摊</p>
          <h2>正在加载分摊编辑上下文</h2>
          <p>正在读取任务信息、发票列表、当前分摊和确认状态，请稍候。</p>
        </section>
      ) : null}

      {pageState.status === "error" ? <ApiErrorNotice error={pageState.error} /> : null}
      {submitError ? <ApiErrorNotice error={submitError} /> : null}

      {pageState.status === "ready" && isForeignTask ? (
        <section className="status-card admin-task-detail-panel">
          <p className="eyebrow">访问范围</p>
          <h2>当前任务不属于此管理员</h2>
          <p>你当前没有处理该任务的权限，如需访问请联系对应负责人。</p>
        </section>
      ) : null}

      {visibleTask && visibleSummary ? (
        <section className="split-editor-layout">
          <article className="status-card admin-task-detail-panel split-editor-list-panel">
            <div className="admin-form-header">
              <div>
                <p className="eyebrow">Invoices</p>
                <h2>可编辑分摊的发票</h2>
              </div>
              <StatusBadge tone="info">{splitInvoiceItems.length} 张发票</StatusBadge>
            </div>

            {splitInvoiceItems.length === 0 ? (
              <p className="field-hint split-editor-empty">
                当前任务还没有已录入发票，暂时无法编辑费用分摊。
              </p>
            ) : (
              <ul className="invoice-material-list" aria-label="任务发票列表">
                {splitInvoiceItems.map((item) => {
                  const invoice = item.invoiceItem.invoice;
                  const material = item.materialItem?.material ?? null;
                  const isSelected = invoice.id === selectedInvoiceId;
                  return (
                    <li key={invoice.id}>
                      <InvoiceSummaryRow
                        filename={material?.original_filename ?? invoice.invoice_number}
                        invoiceNumber={invoice.invoice_number}
                        amountLabel={formatCurrencyFromCents(invoice.amount_cents)}
                        validationLabel={buildInvoiceSummaryValidation(item.invoiceItem).label}
                        validationTone={buildInvoiceSummaryValidation(item.invoiceItem).tone}
                        supportingMaterialCount={item.invoiceItem.supporting_material_ids.length}
                        statusHint={`提交人 ${material?.submitter_id ?? "未知提交人"}；分摊 ${item.invoiceItem.splits.length} 条`}
                        trailingContent={(
                          <StatusBadge tone={item.invoiceItem.splits.length > 0 ? "info" : "warning"}>
                            {item.invoiceItem.splits.length > 0 ? `${item.invoiceItem.splits.length} 条分摊` : "待分摊"}
                          </StatusBadge>
                        )}
                        selected={isSelected}
                        action={{
                          ariaLabel: `任务发票 ${material?.original_filename ?? invoice.invoice_number} ${invoice.invoice_number}`,
                          onClick: () => {
                            handleSelectInvoice(item);
                          },
                        }}
                      />
                    </li>
                  );
                })}
              </ul>
            )}
          </article>

          {selectedInvoiceItem && selectedInvoice ? (
            <article className="status-card admin-form-card split-editor-form-panel">
              <div className="admin-form-header">
                <div>
                  <p className="eyebrow">Selected Invoice</p>
                  <h2>编辑当前发票的费用分摊</h2>
                </div>
                <StatusBadge tone="info">
                  当前发票号 {selectedInvoice.invoice_number}
                </StatusBadge>
              </div>

              <dl className="task-meta-grid invoice-editor-summary-grid">
                <div>
                  <dt>任务编号</dt>
                  <dd>{visibleTask.id}</dd>
                </div>
                <div>
                  <dt>比赛名称</dt>
                  <dd>{visibleTask.competition_name}</dd>
                </div>
                <div>
                  <dt>材料上传时间</dt>
                  <dd>{selectedMaterial ? formatDateTime(selectedMaterial.created_at) : "无材料时间"}</dd>
                </div>
                <div>
                  <dt>当前提交人</dt>
                  <dd>{selectedMaterial?.submitter_id ?? "未知提交人"}</dd>
                </div>
                <div>
                  <dt>发票金额</dt>
                  <dd>{formatCurrencyFromCents(selectedInvoice.amount_cents)}</dd>
                </div>
                <div>
                  <dt>当前分摊数</dt>
                  <dd>{selectedInvoiceItem.invoiceItem.splits.length} 条</dd>
                </div>
              </dl>

              {saveFeedback?.invoiceId === selectedInvoice.id ? (
                <section className="member-status-section">
                  <div className="member-status-section-header">
                    <div>
                      <h4>最近一次保存结果</h4>
                      <p className="field-hint">
                        已保存 {saveFeedback.splitCount} 条分摊，合计 {formatCurrencyFromCents(saveFeedback.totalAmountCents)}。任务摘要已重新拉取，当前确认状态以下方最新数据为准。
                      </p>
                    </div>
                    <StatusBadge tone="success">已刷新</StatusBadge>
                  </div>
                </section>
              ) : null}

              <form
                className="page-stack"
                onSubmit={(event) => {
                  void handleSubmit(event);
                }}
              >
                <section className="member-status-section">
                  <div className="member-status-section-header">
                    <div>
                      <h4>分摊明细</h4>
                      <p className="field-hint">
                        允许为一张发票配置一个或多个归属成员。前端会持续显示与发票金额的差额，但不会擅自替你修正数据。
                      </p>
                    </div>
                    <Button
                      type="button"
                      variant="outlined"
                      onClick={handleAddRow}
                    >
                      新增分摊行
                    </Button>
                  </div>

                  <ul className="split-row-list" aria-label="分摊编辑列表">
                    {formRows.map((row, index) => (
                      <li
                        key={row.rowId}
                        role="group"
                        className="split-row-card"
                        aria-label={`分摊行 ${index + 1}`}
                      >
                        <div className="split-row-header">
                          <strong>分摊行 {index + 1}</strong>
                          <Button
                            type="button"
                            variant="outlined"
                            onClick={() => {
                              void handleRemoveRow(row.rowId, index + 1);
                            }}
                            disabled={formRows.length <= 1}
                          >
                            删除
                          </Button>
                        </div>

                        <div className="admin-form-grid split-editor-form-grid">
                          <TaskMemberAutocomplete
                            label="归属成员"
                            value={row.memberId}
                            name={`member-${row.rowId}`}
                            options={visibleTask.member_ids}
                            memberSummaries={visibleTask.member_summaries}
                            includeEmptyOption
                            emptyOptionLabel="请选择成员"
                            placeholder="输入成员姓名、用户名或学号筛选"
                            onChange={(nextValue) => {
                              updateRow(row.rowId, "memberId", nextValue);
                            }}
                            error={Boolean(formErrors[row.rowId]?.memberId)}
                            helperText={formErrors[row.rowId]?.memberId}
                          />

                          <TextField
                            label="分摊金额（元）"
                            name={`amount-${row.rowId}`}
                            value={row.amountYuan}
                            onChange={(event) => {
                              updateRow(row.rowId, "amountYuan", event.target.value);
                            }}
                            error={Boolean(formErrors[row.rowId]?.amountYuan)}
                            helperText={formErrors[row.rowId]?.amountYuan}
                            inputProps={{ inputMode: "decimal" }}
                            fullWidth
                          />

                          <TextField
                            className="split-editor-note-field"
                            label="备注"
                            name={`note-${row.rowId}`}
                            value={row.note}
                            onChange={(event) => {
                              updateRow(row.rowId, "note", event.target.value);
                            }}
                            fullWidth
                          />
                        </div>
                      </li>
                    ))}
                  </ul>

                  <div className="split-summary-card" aria-label="分摊金额摘要">
                    <div>
                      <dt>发票金额</dt>
                      <dd>{formatCurrencyFromCents(selectedInvoice.amount_cents)}</dd>
                    </div>
                    <div>
                      <dt>分摊合计</dt>
                      <dd>{formatCurrencyFromCents(splitSummary.totalAmountCents)}</dd>
                    </div>
                    <div>
                      <dt>差额</dt>
                      <dd
                        className={
                          amountDifferenceCents === 0
                            ? "split-difference-balanced"
                            : "split-difference-unbalanced"
                        }
                      >
                        {amountDifferenceCents >= 0 ? "+" : "-"}
                        {formatCurrencyFromCents(Math.abs(amountDifferenceCents))}
                      </dd>
                    </div>
                    <div>
                      <dt>未完成金额行</dt>
                      <dd>{splitSummary.invalidRowCount} 行</dd>
                    </div>
                  </div>
                </section>

                <section className="member-status-section">
                  <div className="member-status-section-header">
                    <div>
                      <h4>当前确认状态</h4>
                      <p className="field-hint">
                        服务端会按最新分摊版本维护成员确认状态。若管理员修改金额或归属成员，部分成员的确认可能被重置为待确认。
                      </p>
                    </div>
                    <StatusBadge tone="info">
                      已确认 {countCurrentConfirmationStatus(selectedInvoiceItem.invoiceItem, "confirmed")} / {selectedInvoiceItem.invoiceItem.splits.length}
                    </StatusBadge>
                  </div>

                  {selectedInvoiceItem.invoiceItem.splits.length === 0 ? (
                    <p className="field-hint">
                      当前发票还没有持久化分摊记录；首次保存后，这里会显示每个成员的最新确认状态。
                    </p>
                  ) : (
                    <ul className="validation-result-list" aria-label="当前分摊确认状态">
                      {selectedInvoiceItem.invoiceItem.splits.map(({ split, confirmation }) => (
                        <li key={split.id}>
                          <div className="task-card-header">
                            <strong>
                              {formatTaskMemberLabel(split.member_id, memberSummaryMap)} · {formatCurrencyFromCents(split.amount_cents)}
                            </strong>
                            <StatusBadge tone={confirmation?.status === "confirmed" ? "success" : confirmation?.status === "disputed" ? "danger" : "warning"}>
                              {confirmation?.is_current
                                ? formatConfirmationStatus(confirmation.status)
                                : "待确认"}
                            </StatusBadge>
                          </div>
                          <span>当前版本：v{split.version}</span>
                          <span>{split.note ? `备注：${split.note}` : "无备注"}</span>
                          <span>
                            {confirmation?.is_current
                              ? `最新确认时间：${formatDateTime(confirmation.updated_at)}`
                              : "当前成员尚未确认最新分摊版本"}
                          </span>
                          {confirmation?.dispute_reason ? (
                            <span>异议原因：{confirmation.dispute_reason}</span>
                          ) : null}
                        </li>
                      ))}
                    </ul>
                  )}
                </section>

                <div className="admin-form-footer">
                  <p className="field-hint">
                    若差额不为 0，服务端会继续按真实规则拒绝保存，并返回明确错误；本页只负责把该错误原样展示出来。
                  </p>
                  <Button variant="contained" type="submit" disabled={isSubmitting}>
                    {isSubmitting ? "正在保存并刷新摘要" : "保存费用分摊"}
                  </Button>
                </div>
              </form>
            </article>
          ) : null}
        </section>
      ) : null}
    </AdminWorkspaceShell>
  );
}
