import { type FormEvent, useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import MenuItem from "@mui/material/MenuItem";
import TextField from "@mui/material/TextField";

import { ApiErrorNotice } from "../components/ApiErrorNotice";
import {
  EmptyState,
  PageHeader,
  RoleWorkspace,
  SectionCard,
  StatusBadge,
} from "../components/dashboard";
import { useSnackbar } from "../components/use-snackbar";
import { ApiError } from "../lib/api/client";
import { trmsApi } from "../lib/api/trms";
import type {
  ExpenseSplitRecord,
  ExpenseType,
  InvoiceRecord,
  ManualInvoiceEntry,
  MaterialRecord,
  MaterialType,
  ReimbursementTask,
  TaskMemberWorkbenchItem,
  TaskMemberWorkbenchSummary,
  TaskSharedInvoiceItem,
} from "../lib/api/types";
import {
  describeRecognitionFailure,
  formatConfirmationStatus,
  formatExpenseType,
  formatMaterialType,
  formatMemberLabel,
  formatRecognitionStatus,
  formatTaskStatus,
  formatValidationRule,
  formatValidationStatus,
} from "../lib/ui-text";
import { useAuthSession } from "./auth-store";
import { buildInvoiceDetailPath } from "./member-invoice-paths";

type DetailState =
  | { status: "loading" }
  | { status: "error"; error: unknown }
  | {
    status: "ready";
    task: ReimbursementTask;
    summary: TaskMemberWorkbenchSummary;
    item: TaskMemberWorkbenchItem | null;
    sharedInvoice: TaskSharedInvoiceItem | null;
  };

type ManualInvoiceFormState = {
  invoiceNumber: string;
  issueDate: string;
  transactionTime: string;
  buyerName: string;
  taxNumber: string;
  sellerName: string;
  amountYuan: string;
  expenseType: ExpenseType;
};

type SplitDraftRow = {
  key: string;
  member_id: string;
  amount_yuan: string;
  note: string;
};

const MATERIAL_TYPE_OPTIONS: Array<{ value: MaterialType; label: string }> = [
  { value: "invoice", label: "发票" },
  { value: "payment_record", label: "支付记录" },
  { value: "competition_notice", label: "比赛通知" },
  { value: "itinerary", label: "行程单" },
  { value: "order_screenshot", label: "订单截图" },
  { value: "other_attachment", label: "其他材料" },
];

const FIELD_ORDER = [
  "invoice_number",
  "issue_date",
  "transaction_time",
  "buyer_name",
  "tax_number",
  "seller_name",
  "amount_cents",
  "expense_type",
] as const;

const FIELD_LABELS: Record<(typeof FIELD_ORDER)[number], string> = {
  invoice_number: "发票号码",
  issue_date: "开票日期",
  transaction_time: "交易时间",
  buyer_name: "发票抬头",
  tax_number: "税号",
  seller_name: "销售方",
  amount_cents: "金额",
  expense_type: "费用类型",
};

function formatCurrencyFromCents(cents: number) {
  return `￥${(cents / 100).toFixed(2)}`;
}

function formatCurrencyInputFromCents(cents: number) {
  return (cents / 100).toFixed(2);
}

function parseCurrencyInputToCents(value: string) {
  const normalized = value.trim();
  if (!/^\d+(?:\.\d{1,2})?$/.test(normalized)) {
    return null;
  }
  const [integerPart, decimalPart = ""] = normalized.split(".");
  return Number(integerPart) * 100 + Number(`${decimalPart}00`.slice(0, 2));
}

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function formatDateTimeLocalInput(value: string | null) {
  if (!value) {
    return "";
  }
  const date = new Date(value);
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  const hours = String(date.getHours()).padStart(2, "0");
  const minutes = String(date.getMinutes()).padStart(2, "0");
  return `${year}-${month}-${day}T${hours}:${minutes}`;
}

function toApiDateTime(value: string) {
  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }
  const localDate = new Date(trimmed);
  const year = localDate.getFullYear();
  const month = String(localDate.getMonth() + 1).padStart(2, "0");
  const day = String(localDate.getDate()).padStart(2, "0");
  const hours = String(localDate.getHours()).padStart(2, "0");
  const minutes = String(localDate.getMinutes()).padStart(2, "0");
  const offsetMinutes = -localDate.getTimezoneOffset();
  const sign = offsetMinutes >= 0 ? "+" : "-";
  const absoluteOffsetMinutes = Math.abs(offsetMinutes);
  const offsetHours = String(Math.floor(absoluteOffsetMinutes / 60)).padStart(2, "0");
  const offsetRemainderMinutes = String(absoluteOffsetMinutes % 60).padStart(2, "0");
  return `${year}-${month}-${day}T${hours}:${minutes}:00${sign}${offsetHours}:${offsetRemainderMinutes}`;
}

function isExpenseType(value: string): value is ExpenseType {
  return (
    value === "registration"
    || value === "railway"
    || value === "airfare"
    || value === "local_transport"
    || value === "hotel"
    || value === "other"
  );
}

function buildAllowedExpenseTypes(task: ReimbursementTask): ExpenseType[] {
  const taskExpenseTypes = task.fee_categories.filter(isExpenseType);
  return taskExpenseTypes.length > 0 ? taskExpenseTypes : ["other"];
}

function getRecognitionText(item: TaskMemberWorkbenchItem | null, fieldName: (typeof FIELD_ORDER)[number]) {
  const value = item?.recognition?.recognized_fields[fieldName]?.value;
  if (typeof value === "string") {
    return value;
  }
  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  return "";
}

function getRecognitionAmountInput(item: TaskMemberWorkbenchItem | null) {
  const value = item?.recognition?.recognized_fields.amount_cents?.value;
  return typeof value === "number" ? formatCurrencyInputFromCents(value) : "";
}

function getRecognitionExpenseType(item: TaskMemberWorkbenchItem | null, allowedExpenseTypes: ExpenseType[]) {
  const rawValue = getRecognitionText(item, "expense_type");
  if (isExpenseType(rawValue) && allowedExpenseTypes.includes(rawValue)) {
    return rawValue;
  }
  return allowedExpenseTypes[0] ?? "other";
}

function formatFieldValue(fieldName: (typeof FIELD_ORDER)[number], value: unknown) {
  if (value === null || value === undefined || value === "") {
    return "未填写";
  }
  if (fieldName === "amount_cents" && typeof value === "number") {
    return formatCurrencyFromCents(value);
  }
  if (fieldName === "expense_type" && typeof value === "string") {
    return formatExpenseType(value);
  }
  if (fieldName === "transaction_time" && typeof value === "string") {
    return formatDateTime(value);
  }
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  return JSON.stringify(value);
}

function buildManualInvoiceFormState(
  item: TaskMemberWorkbenchItem,
  allowedExpenseTypes: ExpenseType[],
): ManualInvoiceFormState {
  return {
    invoiceNumber: item.invoice?.invoice_number ?? getRecognitionText(item, "invoice_number"),
    issueDate: item.invoice?.issue_date ?? getRecognitionText(item, "issue_date"),
    transactionTime: item.invoice?.transaction_time
      ? formatDateTimeLocalInput(item.invoice.transaction_time)
      : formatDateTimeLocalInput(getRecognitionText(item, "transaction_time")),
    buyerName: item.invoice?.buyer_name ?? getRecognitionText(item, "buyer_name"),
    taxNumber: item.invoice?.tax_number ?? getRecognitionText(item, "tax_number"),
    sellerName: item.invoice?.seller_name ?? getRecognitionText(item, "seller_name"),
    amountYuan: item.invoice ? formatCurrencyInputFromCents(item.invoice.amount_cents) : getRecognitionAmountInput(item),
    expenseType: item.invoice?.expense_type ?? getRecognitionExpenseType(item, allowedExpenseTypes),
  };
}

function buildSplitDraftRows(item: TaskMemberWorkbenchItem, defaultMemberId: string): SplitDraftRow[] {
  const invoice = item.invoice;
  if (!invoice) {
    return [];
  }
  if (item.splits.length === 0) {
    return [{
      key: `${invoice.id}:default`,
      member_id: defaultMemberId,
      amount_yuan: formatCurrencyInputFromCents(invoice.amount_cents),
      note: "",
    }];
  }
  return item.splits.map((split, index) => ({
    key: split.id || `${invoice.id}:existing-${index}`,
    member_id: split.member_id,
    amount_yuan: formatCurrencyInputFromCents(split.amount_cents),
    note: split.note ?? "",
  }));
}

function summarizeSplitDrafts(drafts: SplitDraftRow[]) {
  let totalCents = 0;
  let hasInvalidAmount = false;
  for (const draft of drafts) {
    const amountCents = parseCurrencyInputToCents(draft.amount_yuan);
    if (amountCents === null || amountCents <= 0) {
      hasInvalidAmount = true;
      continue;
    }
    totalCents += amountCents;
  }
  return { totalCents, hasInvalidAmount };
}

function collectAbnormalReasons(item: TaskMemberWorkbenchItem) {
  const reasons: string[] = [];
  const recognitionStatus = item.recognition?.status ?? item.material.recognition_status;
  if (recognitionStatus === "pending") {
    reasons.push("系统正在处理该材料识别；识别完成前暂时不能形成完整发票上下文。");
  }
  if (recognitionStatus === "failed") {
    reasons.push(describeRecognitionFailure(item.recognition?.failure ?? (
      item.material.recognition_failure_stage && item.material.recognition_failure_reason
        ? {
          stage: item.material.recognition_failure_stage,
          reason: item.material.recognition_failure_reason,
        }
        : null
    )));
  }
  if (recognitionStatus === "needs_confirmation") {
    reasons.push("识别结果里仍有待确认字段，请优先核对关键发票信息。");
  }
  for (const validation of item.validations) {
    if (validation.status === "failed" || validation.status === "pending") {
      reasons.push(`${formatValidationRule(validation.rule_code)}：${validation.message}`);
    }
  }
  for (const missingMaterial of item.missing_materials) {
    reasons.push(`${formatMaterialType(missingMaterial.required_material_type)}：${missingMaterial.message}`);
  }
  return reasons;
}

function pickItemByRoute(
  summary: TaskMemberWorkbenchSummary,
  invoiceId: string | undefined,
  materialId: string | undefined,
) {
  if (invoiceId) {
    return summary.items.find((item) => item.invoice?.id === invoiceId) ?? null;
  }
  if (materialId) {
    return summary.items.find((item) => item.material.material_id === materialId) ?? null;
  }
  return null;
}

function pickSharedInvoiceByRoute(summary: TaskMemberWorkbenchSummary, invoiceId: string | undefined) {
  if (!invoiceId) {
    return null;
  }
  return summary.shared_invoices.find((item) => item.invoice_id === invoiceId) ?? null;
}

function findPrimaryInvoice(item: TaskMemberWorkbenchItem | null, sharedInvoice: TaskSharedInvoiceItem | null) {
  if (item?.invoice) {
    return item.invoice;
  }
  if (!sharedInvoice) {
    return null;
  }
  return {
    id: sharedInvoice.invoice_id,
    task_id: "",
    material_id: "",
    invoice_number: sharedInvoice.invoice_number,
    issue_date: sharedInvoice.issue_date,
    transaction_time: null,
    buyer_name: sharedInvoice.buyer_name,
    tax_number: "",
    seller_name: sharedInvoice.seller_name,
    amount_cents: sharedInvoice.amount_cents,
    expense_type: sharedInvoice.expense_type,
    member_submission_status: "unsubmitted",
    submitted_by_member_id: null,
    submitted_at: null,
    created_at: sharedInvoice.updated_at,
    updated_at: sharedInvoice.updated_at,
  } satisfies InvoiceRecord;
}

export function MemberInvoiceDetailPage() {
  const session = useAuthSession();
  const navigate = useNavigate();
  const { invoiceId, materialId } = useParams();
  const [searchParams] = useSearchParams();
  const taskId = searchParams.get("taskId") ?? "";
  const { showError, showSuccess, showWarning } = useSnackbar();
  const [detailState, setDetailState] = useState<DetailState>({ status: "loading" });
  const [reloadVersion, setReloadVersion] = useState(0);
  const [materialTypeDraft, setMaterialTypeDraft] = useState<MaterialType | null>(null);
  const [manualForm, setManualForm] = useState<ManualInvoiceFormState | null>(null);
  const [manualError, setManualError] = useState<string | null>(null);
  const [savingManual, setSavingManual] = useState(false);
  const [savingMaterialType, setSavingMaterialType] = useState(false);
  const [retryingRecognition, setRetryingRecognition] = useState(false);
  const [splitDrafts, setSplitDrafts] = useState<SplitDraftRow[]>([]);
  const [splitError, setSplitError] = useState<string | null>(null);
  const [savingSplits, setSavingSplits] = useState(false);
  const [openingOriginal, setOpeningOriginal] = useState(false);
  const [confirmingSplitId, setConfirmingSplitId] = useState<string | null>(null);
  const [disputeReasons, setDisputeReasons] = useState<Record<string, string>>({});
  const [confirmationError, setConfirmationError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadDetail() {
      if (!session || session.role !== "member" || !taskId) {
        return;
      }
      setDetailState({ status: "loading" });
      try {
        const [task, summary] = await Promise.all([
          trmsApi.getTask(taskId),
          trmsApi.getTaskMemberWorkbench(taskId, session.actorId),
        ]);
        const item = pickItemByRoute(summary, invoiceId, materialId);
        const sharedInvoice = item ? null : pickSharedInvoiceByRoute(summary, invoiceId);
        if (cancelled) {
          return;
        }
        setDetailState({ status: "ready", task, summary, item, sharedInvoice });
        if (item) {
          setMaterialTypeDraft(item.material.material_type);
          setManualForm(buildManualInvoiceFormState(item, buildAllowedExpenseTypes(task)));
          setSplitDrafts(buildSplitDraftRows(item, session.actorId));
        }
      } catch (error) {
        if (!cancelled) {
          setDetailState({ status: "error", error });
        }
      }
    }

    void loadDetail();

    return () => {
      cancelled = true;
    };
  }, [invoiceId, materialId, reloadVersion, session, taskId]);

  const item = detailState.status === "ready" ? detailState.item : null;
  const sharedInvoice = detailState.status === "ready" ? detailState.sharedInvoice : null;
  const invoice = findPrimaryInvoice(item, sharedInvoice);
  const task = detailState.status === "ready" ? detailState.task : null;
  const abnormalReasons = useMemo(() => (item ? collectAbnormalReasons(item) : []), [item]);
  const allowedExpenseTypes = task ? buildAllowedExpenseTypes(task) : [];
  const splitSummary = summarizeSplitDrafts(splitDrafts);
  const relatedExpenseDetails = item?.related_expense_details ?? [];
  const pendingExpenseConfirmationCount = relatedExpenseDetails.filter((detail) => (
    detail.confirmation?.status !== "confirmed"
  )).length;

  function updateManualField<Key extends keyof ManualInvoiceFormState>(
    key: Key,
    value: ManualInvoiceFormState[Key],
  ) {
    setManualForm((current) => (current ? { ...current, [key]: value } : current));
    setManualError(null);
  }

  async function handleMaterialTypeSave() {
    if (!item || !session || !materialTypeDraft) {
      return;
    }
    setSavingMaterialType(true);
    try {
      await trmsApi.updateMaterialType(item.material.material_id, {
        actor_id: session.actorId,
        material_type: materialTypeDraft,
      });
      showSuccess("材料类型已保存。");
      setReloadVersion((current) => current + 1);
    } catch (error) {
      showError(error instanceof ApiError ? error.summary.message : "材料类型保存失败。");
    } finally {
      setSavingMaterialType(false);
    }
  }

  async function handleManualSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!item || !session || !manualForm) {
      return;
    }
    const amountCents = parseCurrencyInputToCents(manualForm.amountYuan);
    if (
      !manualForm.invoiceNumber.trim()
      || !manualForm.buyerName.trim()
      || !manualForm.taxNumber.trim()
      || amountCents === null
      || amountCents <= 0
      || !allowedExpenseTypes.includes(manualForm.expenseType)
    ) {
      setManualError("请补齐发票号码、发票抬头、税号、金额和任务允许的费用类型。");
      return;
    }
    const payload: ManualInvoiceEntry = {
      actor_id: session.actorId,
      invoice_number: manualForm.invoiceNumber.trim(),
      issue_date: manualForm.issueDate.trim() || null,
      transaction_time: toApiDateTime(manualForm.transactionTime),
      buyer_name: manualForm.buyerName.trim(),
      tax_number: manualForm.taxNumber.trim(),
      seller_name: manualForm.sellerName.trim() || null,
      amount_cents: amountCents,
      expense_type: manualForm.expenseType,
    };
    setSavingManual(true);
    setManualError(null);
    try {
      const response = await trmsApi.createOrUpdateInvoice(item.material.material_id, payload);
      showSuccess(`已保存发票 ${response.invoice.invoice_number}，并刷新 ${response.validations.length} 条校验结果。`);
      if (!invoiceId && task) {
        void navigate(buildInvoiceDetailPath(task.id, response.invoice.id), { replace: true });
      }
      setReloadVersion((current) => current + 1);
    } catch (error) {
      setManualError(error instanceof ApiError ? error.summary.message : "保存发票字段失败。");
    } finally {
      setSavingManual(false);
    }
  }

  function updateSplitDraft(rowKey: string, patch: Partial<SplitDraftRow>) {
    setSplitDrafts((current) => current.map((draft) => (
      draft.key === rowKey ? { ...draft, ...patch } : draft
    )));
    setSplitError(null);
  }

  function addSplitDraft() {
    if (!task || !session || !invoice) {
      return;
    }
    const fallbackMemberId = task.member_ids.find((memberId) => (
      splitDrafts.every((draft) => draft.member_id !== memberId)
    )) ?? session.actorId;
    setSplitDrafts((current) => [
      ...current,
      {
        key: `${invoice.id}:new-${current.length + 1}`,
        member_id: fallbackMemberId,
        amount_yuan: "0.00",
        note: "",
      },
    ]);
  }

  async function handleSplitSave() {
    if (!invoice || !session) {
      return;
    }
    const normalizedItems = [];
    for (const draft of splitDrafts) {
      const amountCents = parseCurrencyInputToCents(draft.amount_yuan);
      if (amountCents === null || amountCents <= 0) {
        setSplitError("请为每条分摊填写有效金额，格式示例为 123.45。");
        return;
      }
      normalizedItems.push({
        member_id: draft.member_id,
        amount_cents: amountCents,
        note: draft.note.trim() || null,
      });
    }
    if (normalizedItems.length === 0) {
      setSplitError("至少保留一条分摊记录。");
      return;
    }
    setSavingSplits(true);
    setSplitError(null);
    try {
      await trmsApi.replaceInvoiceSplits(invoice.id, {
        actor_id: session.actorId,
        items: normalizedItems,
      });
      showSuccess("分摊方案已保存，相关成员需要重新确认费用。");
      setReloadVersion((current) => current + 1);
    } catch (error) {
      setSplitError(error instanceof ApiError ? error.summary.message : "分摊方案保存失败。");
    } finally {
      setSavingSplits(false);
    }
  }

  async function handleRecognitionRetry() {
    if (!item) {
      return;
    }
    setRetryingRecognition(true);
    try {
      const created = await trmsApi.createRecognitionTask(item.material.material_id);
      const executed = await trmsApi.executeRecognitionTask(created.item.id);
      if (executed.dispatch?.status === "queued") {
        showWarning(executed.dispatch.message);
      } else {
        showSuccess(executed.dispatch?.message ?? "已完成重新识别。");
      }
      setReloadVersion((current) => current + 1);
    } catch (error) {
      showError(error instanceof ApiError ? error.summary.message : "重新识别失败。");
    } finally {
      setRetryingRecognition(false);
    }
  }

  async function handleViewOriginal(material: MaterialRecord) {
    setOpeningOriginal(true);
    try {
      const file = await trmsApi.downloadMaterialContent(material.id);
      const objectUrl = URL.createObjectURL(file.blob);
      window.open(objectUrl, "_blank", "noopener,noreferrer");
      window.setTimeout(() => {
        URL.revokeObjectURL(objectUrl);
      }, 60_000);
    } catch (error) {
      showError(error instanceof ApiError ? error.summary.message : "原文件暂时无法打开。");
    } finally {
      setOpeningOriginal(false);
    }
  }

  async function handleExpenseConfirmationSubmit(
    splitId: string,
    status: "confirmed" | "disputed",
  ) {
    if (!session) {
      return;
    }
    const disputeReason = disputeReasons[splitId]?.trim() ?? "";
    if (status === "disputed" && !disputeReason) {
      setConfirmationError("提交异议时必须填写原因。");
      return;
    }

    setConfirmingSplitId(splitId);
    setConfirmationError(null);
    try {
      await trmsApi.submitSplitConfirmation(splitId, {
        actor_id: session.actorId,
        member_id: session.actorId,
        status,
        dispute_reason: status === "disputed" ? disputeReason : null,
      });
      showSuccess(status === "confirmed" ? "已确认这笔费用。" : "已提交费用异议。");
      setDisputeReasons((current) => ({ ...current, [splitId]: "" }));
      setReloadVersion((current) => current + 1);
    } catch (error) {
      setConfirmationError(error instanceof ApiError ? error.summary.message : "费用确认提交失败。");
    } finally {
      setConfirmingSplitId(null);
    }
  }

  if (!session || session.role !== "member") {
    return null;
  }

  return (
    <RoleWorkspace
      header={(
        <PageHeader
          eyebrow="单张发票处理"
          title={invoice?.invoice_number ?? item?.material.original_filename ?? "发票处理"}
          description="在这个页面补齐字段、修改材料类型、调整分摊金额，并查看校验与附件状态。"
          meta={task ? `${task.competition_name} / ${formatTaskStatus(task.status)}` : `当前成员：${session.displayName}`}
          actions={(
            <div className="page-actions">
              <Button component={Link} variant="outlined" to={taskId ? `/member/invoices/workbench?taskId=${encodeURIComponent(taskId)}` : "/member/invoices/workbench"}>
                返回工作台
              </Button>
            </div>
          )}
        />
      )}
    >
      {detailState.status === "loading" ? (
        <SectionCard title="正在加载发票" description="正在读取当前发票、识别、校验、附件和分摊状态。" />
      ) : null}

      {detailState.status === "error" ? <ApiErrorNotice error={detailState.error} /> : null}

      {detailState.status === "ready" && !item && !sharedInvoice ? (
        <EmptyState
          title="没有找到这张发票"
          description="它可能不属于当前任务，或者当前账号没有查看权限。"
          action={<Button component={Link} variant="contained" to={`/member/invoices/workbench?taskId=${encodeURIComponent(taskId)}`}>返回工作台</Button>}
        />
      ) : null}

      {detailState.status === "ready" && sharedInvoice ? (
        <SectionCard
          title="共享发票摘要"
          description="这是任务内其他成员上传的发票，只展示可共享摘要，不提供原始附件和编辑入口。"
          action={<StatusBadge tone="info">只读</StatusBadge>}
        >
          <dl className="task-meta-grid member-status-meta-grid">
            <div><dt>上传成员</dt><dd>{sharedInvoice.submitter_id ? formatMemberLabel(sharedInvoice.submitter_id) : "未记录"}</dd></div>
            <div><dt>发票金额</dt><dd>{formatCurrencyFromCents(sharedInvoice.amount_cents)}</dd></div>
            <div><dt>费用类型</dt><dd>{formatExpenseType(sharedInvoice.expense_type)}</dd></div>
            <div><dt>开票日期</dt><dd>{sharedInvoice.issue_date ?? "未填写"}</dd></div>
          </dl>
        </SectionCard>
      ) : null}

      {detailState.status === "ready" && item ? (
        <>
          <SectionCard
            title="当前状态"
            description="先看这张发票当前阻塞在哪里，再决定补字段、重新识别或调整分摊。"
            action={<StatusBadge tone={abnormalReasons.length > 0 ? "warning" : "success"}>{abnormalReasons.length > 0 ? `${abnormalReasons.length} 项待处理` : "状态稳定"}</StatusBadge>}
          >
            <dl className="task-meta-grid member-status-meta-grid">
              <div><dt>原始文件</dt><dd>{item.material.original_filename}</dd></div>
              <div><dt>材料类型</dt><dd>{formatMaterialType(item.material.material_type)}</dd></div>
              <div><dt>识别状态</dt><dd>{item.recognition ? formatRecognitionStatus(item.recognition.status) : "暂无识别"}</dd></div>
              <div><dt>校验状态</dt><dd>{formatValidationStatus(item.material.validation_status)}</dd></div>
              <div><dt>发票金额</dt><dd>{item.invoice ? formatCurrencyFromCents(item.invoice.amount_cents) : "未形成发票"}</dd></div>
              <div><dt>上传时间</dt><dd>{formatDateTime(item.material.created_at)}</dd></div>
            </dl>
            {abnormalReasons.length > 0 ? (
              <ul className="member-status-message-list" aria-label="单张发票待处理事项">
                {abnormalReasons.map((reason) => <li key={reason}>{reason}</li>)}
              </ul>
            ) : (
              <p className="field-hint">当前没有识别、校验或附件阻塞。</p>
            )}
            <div className="inline-actions">
              <Button type="button" variant="outlined" disabled={openingOriginal} onClick={() => { void handleViewOriginal({ id: item.material.material_id } as MaterialRecord); }}>
                {openingOriginal ? "正在打开..." : "查看原文件"}
              </Button>
              <Button type="button" variant="outlined" disabled={retryingRecognition} onClick={() => { void handleRecognitionRetry(); }}>
                {retryingRecognition ? "重新识别中..." : "运行重新识别"}
              </Button>
            </div>
          </SectionCard>

          <SectionCard title="材料类型" description="识别错类型时先在这里修正，再补录发票字段。">
            <div className="admin-form-grid">
              <TextField
                select
                label="当前材料类型"
                value={materialTypeDraft ?? item.material.material_type}
                onChange={(event) => { setMaterialTypeDraft(event.target.value as MaterialType); }}
                disabled={savingMaterialType}
              >
                {MATERIAL_TYPE_OPTIONS.map((option) => (
                  <MenuItem key={option.value} value={option.value}>{option.label}</MenuItem>
                ))}
              </TextField>
              <Box sx={{ display: "flex", alignItems: "center" }}>
                <Button
                  type="button"
                  variant="outlined"
                  disabled={savingMaterialType || !materialTypeDraft || materialTypeDraft === item.material.material_type}
                  onClick={() => { void handleMaterialTypeSave(); }}
                >
                  {savingMaterialType ? "保存中..." : "保存材料类型"}
                </Button>
              </Box>
            </div>
          </SectionCard>

          <SectionCard title="发票字段" description="识别完成且字段完整时系统会自动建票；缺失或低置信字段在这里人工补齐。">
            <ul className="member-status-message-list" aria-label="识别字段与当前值">
              {FIELD_ORDER.map((fieldName) => (
                <li key={fieldName}>
                  <strong>{FIELD_LABELS[fieldName]}</strong>
                  <span>识别值：{formatFieldValue(fieldName, item.recognition?.recognized_fields[fieldName]?.value ?? null)}</span>
                  <span>当前值：{formatFieldValue(fieldName, item.invoice?.[fieldName] ?? null)}</span>
                </li>
              ))}
            </ul>
            {manualForm ? (
              <form className="page-stack" onSubmit={(event) => { void handleManualSubmit(event); }}>
                <div className="admin-form-grid">
                  <TextField label="发票号码" value={manualForm.invoiceNumber} onChange={(event) => { updateManualField("invoiceNumber", event.target.value); }} />
                  <TextField label="开票日期" type="date" value={manualForm.issueDate} onChange={(event) => { updateManualField("issueDate", event.target.value); }} slotProps={{ inputLabel: { shrink: true } }} />
                  <TextField label="交易时间" type="datetime-local" value={manualForm.transactionTime} onChange={(event) => { updateManualField("transactionTime", event.target.value); }} slotProps={{ inputLabel: { shrink: true } }} />
                  <TextField label="金额（元）" value={manualForm.amountYuan} onChange={(event) => { updateManualField("amountYuan", event.target.value); }} />
                  <TextField label="发票抬头" value={manualForm.buyerName} onChange={(event) => { updateManualField("buyerName", event.target.value); }} />
                  <TextField label="税号" value={manualForm.taxNumber} onChange={(event) => { updateManualField("taxNumber", event.target.value); }} />
                  <TextField label="销售方名称" value={manualForm.sellerName} onChange={(event) => { updateManualField("sellerName", event.target.value); }} />
                  <TextField select label="费用类型" value={manualForm.expenseType} onChange={(event) => { updateManualField("expenseType", event.target.value as ExpenseType); }}>
                    {allowedExpenseTypes.map((expenseType) => (
                      <MenuItem key={expenseType} value={expenseType}>{formatExpenseType(expenseType)}</MenuItem>
                    ))}
                  </TextField>
                </div>
                {manualError ? <p className="field-error field-error-block">{manualError}</p> : null}
                <div className="inline-actions">
                  <Button type="submit" variant="contained" disabled={savingManual || item.material.material_type !== "invoice"}>
                    {savingManual ? "保存中..." : "保存发票字段并校验"}
                  </Button>
                </div>
              </form>
            ) : null}
          </SectionCard>

          <SectionCard title="分摊金额" description="修改分摊对象和金额后，相关成员需要重新确认。">
            {invoice && task ? (
              <>
                {splitDrafts.map((draft, index) => (
                  <div key={draft.key} className="admin-form-grid">
                    <TextField select label={`分配对象 ${index + 1}`} value={draft.member_id} onChange={(event) => { updateSplitDraft(draft.key, { member_id: event.target.value }); }}>
                      {task.member_ids.map((memberId) => (
                        <MenuItem key={memberId} value={memberId}>{formatMemberLabel(memberId)}</MenuItem>
                      ))}
                    </TextField>
                    <TextField label="金额（元）" value={draft.amount_yuan} onChange={(event) => { updateSplitDraft(draft.key, { amount_yuan: event.target.value }); }} />
                    <TextField label="备注" value={draft.note} onChange={(event) => { updateSplitDraft(draft.key, { note: event.target.value }); }} />
                    <Box sx={{ display: "flex", alignItems: "center" }}>
                      <Button type="button" variant="outlined" disabled={splitDrafts.length <= 1} onClick={() => { setSplitDrafts((current) => current.filter((row) => row.key !== draft.key)); }}>
                        移除
                      </Button>
                    </Box>
                  </div>
                ))}
                <p className="field-hint">
                  {splitSummary.hasInvalidAmount
                    ? "请使用最多两位小数的金额格式。"
                    : `当前分摊合计 ${formatCurrencyFromCents(splitSummary.totalCents)}，发票金额 ${formatCurrencyFromCents(invoice.amount_cents)}。`}
                </p>
                {splitError ? <p className="field-error field-error-block">{splitError}</p> : null}
                <div className="inline-actions">
                  <Button type="button" variant="outlined" onClick={addSplitDraft}>新增分摊对象</Button>
                  <Button type="button" variant="contained" disabled={savingSplits} onClick={() => { void handleSplitSave(); }}>
                    {savingSplits ? "保存中..." : "保存分摊方案"}
                  </Button>
                </div>
                {item.splits.length > 0 ? (
                  <ul className="member-status-message-list" aria-label="当前已保存分摊">
                    {item.splits.map((split: ExpenseSplitRecord) => {
                      const confirmation = item.confirmations.find((entry) => entry.split_id === split.id) ?? null;
                      return (
                        <li key={split.id}>
                          <strong>{formatMemberLabel(split.member_id)}</strong>
                          <span>分摊金额：{formatCurrencyFromCents(split.amount_cents)}</span>
                          <span>确认状态：{confirmation ? formatConfirmationStatus(confirmation.status) : "待确认"}</span>
                        </li>
                      );
                    })}
                  </ul>
                ) : null}
              </>
            ) : (
              <p className="field-hint">当前材料还没有形成发票主记录，先保存发票字段后再调整分摊。</p>
            )}
          </SectionCard>

          <SectionCard
            title="本人费用确认"
            description="确认或提出异议只作用于这张发票分到你名下的费用。"
            action={<StatusBadge tone={pendingExpenseConfirmationCount > 0 ? "warning" : "success"}>待确认 {pendingExpenseConfirmationCount} 条</StatusBadge>}
          >
            {confirmationError ? <p className="field-error field-error-block">{confirmationError}</p> : null}
            {relatedExpenseDetails.length > 0 ? (
              <section className="member-confirmation-list" aria-label="单张发票费用确认列表">
                {relatedExpenseDetails.map((detail) => {
                  const currentStatus = detail.confirmation?.status ?? "pending";
                  const isSubmitting = confirmingSplitId === detail.split_id;
                  return (
                    <article key={detail.split_id} className="status-card member-confirmation-card">
                      <div className="member-status-section-header">
                        <div>
                          <p className="task-card-id">费用明细 {detail.split_id}</p>
                          <h3>{detail.invoice.invoice_number}</h3>
                        </div>
                        <StatusBadge tone={currentStatus === "confirmed" ? "success" : currentStatus === "disputed" ? "danger" : "warning"}>
                          {formatConfirmationStatus(currentStatus)}
                        </StatusBadge>
                      </div>
                      <dl className="task-meta-grid member-status-meta-grid">
                        <div><dt>归属成员</dt><dd>{formatMemberLabel(detail.member_id)}</dd></div>
                        <div><dt>归属金额</dt><dd>{formatCurrencyFromCents(detail.amount_cents)}</dd></div>
                        <div><dt>发票总额</dt><dd>{formatCurrencyFromCents(detail.invoice.amount_cents)}</dd></div>
                        <div><dt>备注</dt><dd>{detail.note ?? "无"}</dd></div>
                      </dl>
                      <TextField
                        label="异议原因"
                        value={disputeReasons[detail.split_id] ?? ""}
                        onChange={(event) => {
                          setDisputeReasons((current) => ({
                            ...current,
                            [detail.split_id]: event.target.value,
                          }));
                          setConfirmationError(null);
                        }}
                        multiline
                        minRows={2}
                        fullWidth
                      />
                      <div className="inline-actions">
                        <Button
                          type="button"
                          variant="contained"
                          disabled={isSubmitting}
                          onClick={() => { void handleExpenseConfirmationSubmit(detail.split_id, "confirmed"); }}
                        >
                          {isSubmitting ? "提交中..." : "确认这笔费用"}
                        </Button>
                        <Button
                          type="button"
                          variant="outlined"
                          disabled={isSubmitting}
                          onClick={() => { void handleExpenseConfirmationSubmit(detail.split_id, "disputed"); }}
                        >
                          {isSubmitting ? "提交中..." : "提交异议"}
                        </Button>
                      </div>
                    </article>
                  );
                })}
              </section>
            ) : (
              <p className="field-hint">当前这张发票还没有分到你名下、需要你确认的费用。</p>
            )}
          </SectionCard>

          <SectionCard title="附件与缺失材料" description="确认这张票已经关联必要附件，缺失项可回工作台上传入口补齐。">
            {item.supporting_materials.length > 0 ? (
              <ul className="member-status-message-list">
                {item.supporting_materials.map((material) => (
                  <li key={material.id}>
                    <strong>{formatMaterialType(material.material_type)} / {material.original_filename}</strong>
                    <span>上传时间：{formatDateTime(material.created_at)}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="field-hint">当前这张发票还没有已关联的辅助材料。</p>
            )}
            {item.missing_materials.length > 0 ? (
              <ul className="member-status-message-list">
                {item.missing_materials.map((missingMaterial) => (
                  <li key={`${missingMaterial.invoice_id}:${missingMaterial.required_material_type}:${missingMaterial.source_rule_code}`}>
                    <strong>{formatMaterialType(missingMaterial.required_material_type)}</strong>
                    <span>{missingMaterial.message}</span>
                  </li>
                ))}
              </ul>
            ) : null}
          </SectionCard>
        </>
      ) : null}
    </RoleWorkspace>
  );
}
