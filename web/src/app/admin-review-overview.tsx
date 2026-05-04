import { useEffect, useMemo, useRef, useState } from "react";
import { Link as RouterLink, useParams } from "react-router-dom";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import TextField from "@mui/material/TextField";

import { ApiErrorNotice } from "../components/ApiErrorNotice";
import { TaskMemberAutocomplete } from "../components/task-member-autocomplete";
import { useConfirmDialog } from "../components/use-confirm-dialog";
import { InvoiceSummaryRow } from "../components/invoice-summary-row";
import { MetadataChip, PageHeader, StatusBadge, SurfaceCard } from "../components/dashboard";
import { trmsApi } from "../lib/api/trms";
import type {
  ConfirmationRecord,
  ExpenseType,
  ExpenseSplitRecord,
  RecognitionTaskRecord,
  ReimbursementTask,
  TaskMemberSummary,
  TaskReviewSummary,
  TaskReviewSummaryInvoiceItem,
  TaskReviewSummaryMaterialItem,
  ValidationResult,
} from "../lib/api/types";
import { formatCurrencyFromCents, formatInvoiceAmountFromCents } from "../lib/currency";
import {
  buildTaskMemberSummaryMap,
  describeRecognitionFailure,
  formatConfirmationStatus,
  formatExpenseType,
  formatFieldLabel,
  formatMaterialType,
  formatTaskMemberLabel,
  formatRecognitionStatus,
  formatSubmissionChannel,
  formatTaskStatus,
  formatValidationRule,
  formatValidationSeverity,
  formatValidationStatus,
} from "../lib/ui-text";
import { isTaskVisibleToAdministrator } from "../lib/task-administrators";
import { AdminWorkspaceShell } from "./admin-workspace-shell";
import { useAuthSession } from "./auth-store";

type ReviewPageState =
  | { status: "loading" }
  | { status: "error"; error: unknown }
  | {
      status: "ready";
      task: ReimbursementTask;
      reviewSummary: TaskReviewSummary;
      overdueSummary: ReviewOverdueSummary;
    };

type ReviewPreviewState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "unsupported"; contentType: string | null }
  | { status: "error"; error: unknown }
  | { status: "ready"; url: string; contentType: string };

type ReviewOverdueSummary = {
  is_overdue: boolean;
  total_overdue_members: number;
  overdue_member_ids: string[];
};

type ReviewAnomalyItem = {
  label: string;
  count: number;
  tone: "failed" | "pending";
};

type ReviewDetailTab = "preview" | "recognition" | "validation" | "actions";

type ReviewMaterialDetailItem = {
  materialItem: TaskReviewSummaryMaterialItem;
  primaryInvoice: TaskReviewSummaryInvoiceItem | null;
  relatedInvoices: TaskReviewSummaryInvoiceItem[];
};

type ReviewInvoiceEditorFormState = {
  invoiceNumber: string;
  issueDate: string;
  transactionTime: string;
  buyerName: string;
  taxNumber: string;
  sellerName: string;
  corporateTransferReference: string;
  amountYuan: string;
  expenseType: ExpenseType;
};

type ReviewInvoiceEditorFormErrors = Partial<Record<keyof ReviewInvoiceEditorFormState, string>>;

type ReviewSplitFormRow = {
  rowId: string;
  memberId: string;
  amountYuan: string;
  note: string;
};

type ReviewSplitFormRowError = {
  memberId?: string;
  amountYuan?: string;
};

type ReviewSplitFormErrors = Record<string, ReviewSplitFormRowError>;

type ReviewActionFeedback = {
  invoiceId: string | null;
  kind: "invoice" | "split" | "paper_receipt";
  message: string;
};

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
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

function formatAmountInputFromCents(cents: number | null) {
  if (cents === null) {
    return "";
  }
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
  return (
    `${year}-${month}-${day}T${hours}:${minutes}:00`
    + `${sign}${offsetHours}:${offsetRemainderMinutes}`
  );
}

function getRecognitionFieldValue(
  recognition: RecognitionTaskRecord | null,
  fieldName: string,
) {
  return recognition?.recognized_fields[fieldName] ?? null;
}

function getRecognitionFieldTextValue(
  recognition: RecognitionTaskRecord | null,
  fieldName: string,
) {
  const field = getRecognitionFieldValue(recognition, fieldName);
  if (!field) {
    return "";
  }
  if (typeof field.value === "string") {
    return field.value;
  }
  if (typeof field.value === "number" || typeof field.value === "boolean") {
    return String(field.value);
  }
  return "";
}

function getRecognitionAmountInput(recognition: RecognitionTaskRecord | null) {
  const field = getRecognitionFieldValue(recognition, "amount_cents");
  if (!field || typeof field.value !== "number") {
    return "";
  }
  return formatAmountInputFromCents(field.value);
}

function getRecognitionExpenseType(
  recognition: RecognitionTaskRecord | null,
  allowedExpenseTypes: ExpenseType[],
) {
  const rawValue = getRecognitionFieldTextValue(recognition, "expense_type");
  if (isExpenseType(rawValue) && allowedExpenseTypes.includes(rawValue)) {
    return rawValue;
  }
  return allowedExpenseTypes[0] ?? "other";
}

function buildInitialInvoiceFormState(
  materialItem: TaskReviewSummaryMaterialItem,
  invoiceItem: TaskReviewSummaryInvoiceItem | null,
  task: ReimbursementTask,
): ReviewInvoiceEditorFormState {
  const allowedExpenseTypes = task.fee_categories.filter(isExpenseType);
  const recognition = materialItem.latest_recognition;
  const invoice = invoiceItem?.invoice ?? null;
  const defaultExpenseType = invoice?.expense_type
    ?? getRecognitionExpenseType(recognition, allowedExpenseTypes)
    ?? "other";

  return {
    invoiceNumber: invoice?.invoice_number ?? getRecognitionFieldTextValue(recognition, "invoice_number"),
    issueDate: invoice?.issue_date ?? getRecognitionFieldTextValue(recognition, "issue_date"),
    transactionTime: invoice?.transaction_time
      ? formatDateTimeLocalInput(invoice.transaction_time)
      : formatDateTimeLocalInput(getRecognitionFieldTextValue(recognition, "transaction_time")),
    buyerName: invoice?.buyer_name ?? getRecognitionFieldTextValue(recognition, "buyer_name"),
    taxNumber: invoice?.tax_number ?? getRecognitionFieldTextValue(recognition, "tax_number"),
    sellerName: invoice?.seller_name ?? getRecognitionFieldTextValue(recognition, "seller_name"),
    corporateTransferReference: invoice?.corporate_transfer_reference ?? getRecognitionFieldTextValue(recognition, "corporate_transfer_reference"),
    amountYuan: invoice ? formatAmountInputFromCents(invoice.amount_cents) : getRecognitionAmountInput(recognition),
    expenseType: defaultExpenseType,
  };
}

function validateInvoiceForm(
  formState: ReviewInvoiceEditorFormState,
  allowedExpenseTypes: ExpenseType[],
): ReviewInvoiceEditorFormErrors {
  const errors: ReviewInvoiceEditorFormErrors = {};
  if (!formState.invoiceNumber.trim()) {
    errors.invoiceNumber = "发票号码不能为空。";
  }
  if (!formState.buyerName.trim()) {
    errors.buyerName = "发票抬头不能为空。";
  }
  if (!formState.taxNumber.trim()) {
    errors.taxNumber = "税号不能为空。";
  }
  if (!allowedExpenseTypes.includes(formState.expenseType)) {
    errors.expenseType = "请选择当前任务允许的费用类型。";
  }
  if (parseAmountYuanToCents(formState.amountYuan) === null) {
    errors.amountYuan = "请输入大于 0 的金额，单位为元。";
  }
  return errors;
}

function pickDefaultSplitMemberId(
  invoiceItem: TaskReviewSummaryInvoiceItem,
  materialItem: TaskReviewSummaryMaterialItem,
  task: ReimbursementTask,
) {
  const submitterId = materialItem.material.submitter_id;
  if (submitterId && task.member_ids.includes(submitterId)) {
    return submitterId;
  }

  const existingMemberId = invoiceItem.splits[0]?.split.member_id;
  if (existingMemberId && task.member_ids.includes(existingMemberId)) {
    return existingMemberId;
  }

  return task.member_ids[0] ?? "";
}

function buildInitialSplitRows(
  invoiceItem: TaskReviewSummaryInvoiceItem,
  materialItem: TaskReviewSummaryMaterialItem,
  task: ReimbursementTask,
  createRowId: () => string,
): ReviewSplitFormRow[] {
  if (invoiceItem.splits.length > 0) {
    return invoiceItem.splits.map(({ split }) => ({
      rowId: createRowId(),
      memberId: split.member_id,
      amountYuan: formatAmountInputFromCents(split.amount_cents),
      note: split.note ?? "",
    }));
  }

  return [
    {
      rowId: createRowId(),
      memberId: pickDefaultSplitMemberId(invoiceItem, materialItem, task),
      amountYuan: formatAmountInputFromCents(invoiceItem.invoice.amount_cents),
      note: "",
    },
  ];
}

function buildSplitSummaryRows(rows: ReviewSplitFormRow[]) {
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

function validateSplitRows(rows: ReviewSplitFormRow[]) {
  const errors: ReviewSplitFormErrors = {};

  for (const row of rows) {
    const rowErrors: ReviewSplitFormRowError = {};
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

function countCurrentConfirmationStatus(
  item: TaskReviewSummaryInvoiceItem,
  targetStatus: ConfirmationRecord["status"],
) {
  return item.splits.filter(({ confirmation }) => confirmation?.is_current && confirmation.status === targetStatus)
    .length;
}

function pickActionInvoiceId(
  items: TaskReviewSummaryInvoiceItem[],
  currentInvoiceId: string,
) {
  const visibleInvoiceIds = new Set(items.map((item) => item.invoice.id));
  if (currentInvoiceId && visibleInvoiceIds.has(currentInvoiceId)) {
    return currentInvoiceId;
  }
  return items[0]?.invoice.id ?? "";
}

function formatActorDisplay(value: string | null | undefined) {
  return value && value.trim().length > 0 ? value : "尚未确认";
}

function buildEditableInvoiceCandidates(
  detailItem: ReviewMaterialDetailItem | null,
): TaskReviewSummaryInvoiceItem[] {
  if (!detailItem) {
    return [];
  }
  if (detailItem.materialItem.material.material_type === "invoice") {
    return detailItem.primaryInvoice ? [detailItem.primaryInvoice] : [];
  }
  return detailItem.relatedInvoices;
}

function buildReviewAnomalies(
  reviewSummary: TaskReviewSummary,
  overdueSummary: ReviewOverdueSummary,
) {
  const items: ReviewAnomalyItem[] = [];

  if (reviewSummary.counts.blocker_failed_validation_count > 0) {
    items.push({
      label: "需要立即处理",
      count: reviewSummary.counts.blocker_failed_validation_count,
      tone: "failed",
    });
  }
  if (reviewSummary.counts.pending_assignment_material_count > 0) {
    items.push({
      label: "待归属材料",
      count: reviewSummary.counts.pending_assignment_material_count,
      tone: "failed",
    });
  }
  if (reviewSummary.counts.failed_recognition_count > 0) {
    items.push({
      label: "识别失败",
      count: reviewSummary.counts.failed_recognition_count,
      tone: "failed",
    });
  }
  if (reviewSummary.counts.needs_confirmation_recognition_count > 0) {
    items.push({
      label: "识别待人工确认",
      count: reviewSummary.counts.needs_confirmation_recognition_count,
      tone: "pending",
    });
  }

  const unresolvedConfirmationCount =
    reviewSummary.counts.pending_confirmation_count
    + reviewSummary.counts.missing_confirmation_count;
  if (unresolvedConfirmationCount > 0) {
    items.push({
      label: "待成员确认",
      count: unresolvedConfirmationCount,
      tone: "pending",
    });
  }
  if (reviewSummary.counts.disputed_confirmation_count > 0) {
    items.push({
      label: "成员异议",
      count: reviewSummary.counts.disputed_confirmation_count,
      tone: "failed",
    });
  }
  if (overdueSummary.is_overdue && overdueSummary.total_overdue_members > 0) {
    items.push({
      label: "逾期未确认成员",
      count: overdueSummary.total_overdue_members,
      tone: "failed",
    });
  }

  return items;
}

function buildOutstandingMemberIds(summary: TaskReviewSummary) {
  const memberIds = new Set<string>();

  for (const invoiceItem of summary.invoices) {
    for (const { split, confirmation } of invoiceItem.splits) {
      if (confirmation === null || confirmation.status === "pending") {
        memberIds.add(split.member_id);
      }
    }
  }

  return [...memberIds].sort();
}

function buildDisputedConfirmationItems(summary: TaskReviewSummary) {
  const items: Array<{
    invoiceNumber: string;
    split: ExpenseSplitRecord;
    confirmation: ConfirmationRecord;
  }> = [];

  for (const invoiceItem of summary.invoices) {
    for (const splitItem of invoiceItem.splits) {
      if (splitItem.confirmation?.status !== "disputed") {
        continue;
      }
      items.push({
        invoiceNumber: invoiceItem.invoice.invoice_number,
        split: splitItem.split,
        confirmation: splitItem.confirmation,
      });
    }
  }

  return items.sort((left, right) => right.confirmation.updated_at.localeCompare(left.confirmation.updated_at));
}

function buildReviewDetailItems(summary: TaskReviewSummary) {
  const invoiceItemsById = new Map(summary.invoices.map((item) => [item.invoice.id, item] as const));

  return [...summary.materials]
    .sort((left, right) => right.material.created_at.localeCompare(left.material.created_at))
    .map((materialItem) => {
      const relatedInvoiceIds = [
        ...(materialItem.invoice_id ? [materialItem.invoice_id] : []),
        ...materialItem.supporting_invoice_ids,
      ];
      const relatedInvoices = relatedInvoiceIds
        .map((invoiceId) => invoiceItemsById.get(invoiceId) ?? null)
        .filter((item): item is TaskReviewSummaryInvoiceItem => item !== null);

      return {
        materialItem,
        primaryInvoice: materialItem.invoice_id ? (invoiceItemsById.get(materialItem.invoice_id) ?? null) : null,
        relatedInvoices,
      } satisfies ReviewMaterialDetailItem;
    });
}

function describeInvoiceReference(invoiceItem: TaskReviewSummaryInvoiceItem | null) {
  if (invoiceItem === null) {
    return "未录入";
  }
  return invoiceItem.invoice.invoice_number;
}

function describeSupportingInvoiceReferences(invoices: TaskReviewSummaryInvoiceItem[]) {
  if (invoices.length === 0) {
    return "无";
  }
  return invoices.map((item) => item.invoice.invoice_number).join("、");
}

function pickSelectedMaterialId(
  items: ReviewMaterialDetailItem[],
  currentMaterialId: string,
) {
  const visibleMaterialIds = new Set(items.map((item) => item.materialItem.material.id));
  if (currentMaterialId && visibleMaterialIds.has(currentMaterialId)) {
    return currentMaterialId;
  }
  const firstInvoiceMaterial = items.find((item) => item.materialItem.material.material_type === "invoice");
  return firstInvoiceMaterial?.materialItem.material.id ?? items[0]?.materialItem.material.id ?? "";
}

function buildRecognitionBadgeTone(recognition: RecognitionTaskRecord | null) {
  if (recognition === null) {
    return "warning" as const;
  }
  if (recognition.status === "succeeded") {
    return "success" as const;
  }
  if (recognition.status === "failed") {
    return "danger" as const;
  }
  return "warning" as const;
}

function buildInvoiceSummaryValidationLabel(invoiceItem: TaskReviewSummaryInvoiceItem) {
  if (invoiceItem.validations.some((validation) => validation.status === "failed")) {
    return {
      label: "校验失败",
      tone: "warning" as const,
    };
  }
  if (invoiceItem.validations.some((validation) => validation.status === "pending")) {
    return {
      label: "校验待确认",
      tone: "warning" as const,
    };
  }
  return {
    label: "校验通过",
    tone: "success" as const,
  };
}

function buildInvoiceSummaryValidationStatus(invoiceItem: TaskReviewSummaryInvoiceItem) {
  return buildInvoiceSummaryValidationLabel(invoiceItem);
}

function buildValidationBadgeTone(validation: ValidationResult) {
  if (validation.status === "failed") {
    return "danger" as const;
  }
  if (validation.status === "pending") {
    return "warning" as const;
  }
  return "success" as const;
}

function buildConfirmationBadgeTone(confirmation: ConfirmationRecord | null) {
  if (confirmation === null || confirmation.status === "pending") {
    return "warning" as const;
  }
  if (confirmation.status === "disputed") {
    return "danger" as const;
  }
  return "success" as const;
}

function isPreviewableContentType(contentType: string | null) {
  return contentType === "application/pdf" || Boolean(contentType?.startsWith("image/"));
}

function describeRecognitionFieldValue(
  value: unknown,
  fieldName?: string,
  materialType?: TaskReviewSummaryMaterialItem["material"]["material_type"],
) {
  if (fieldName === "amount_cents") {
    return typeof value === "number"
      ? formatInvoiceAmountFromCents(value)
      : formatInvoiceAmountFromCents(null, materialType === "invoice" ? "未识别金额/待补录" : "未识别金额");
  }
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  if (value === null || value === undefined) {
    return "未识别";
  }
  return "复杂结构";
}

function buildMaterialSummaryValidationLabel(
  item: ReviewMaterialDetailItem,
  recognition: RecognitionTaskRecord | null,
) {
  const failedValidationCount = item.primaryInvoice?.validations.filter(
    (validation) => validation.status === "failed",
  ).length ?? 0;
  if (failedValidationCount > 0) {
    return "校验失败";
  }
  if (recognition?.status === "failed") {
    return "识别失败";
  }
  if (recognition?.status === "needs_confirmation") {
    return "待人工确认";
  }
  return "已归档";
}

function getReviewDetailItemSelectorStatus(
  item: ReviewMaterialDetailItem,
  recognition: RecognitionTaskRecord | null,
) {
  const label = buildMaterialSummaryValidationLabel(item, recognition);
  if (label === "已归档") {
    return { label: "是", tone: "success" as const };
  }
  if (label === "待人工确认") {
    return { label: "待确认", tone: "warning" as const };
  }
  return { label: "否", tone: "warning" as const };
}

function getReviewDetailItemSelectorNumber(item: ReviewMaterialDetailItem) {
  return item.primaryInvoice?.invoice.invoice_number ?? "未形成主发票";
}

function getReviewDetailItemSelectorAmount(item: ReviewMaterialDetailItem) {
  return item.primaryInvoice
    ? formatInvoiceAmountFromCents(item.primaryInvoice.invoice.amount_cents)
    : "未形成主发票";
}

function getReviewDetailItemSelectorType(item: ReviewMaterialDetailItem) {
  return formatMaterialType(item.materialItem.material.material_type);
}

function getReviewDetailItemSelectorHint(
  item: ReviewMaterialDetailItem,
  memberSummaryMap: Map<string, TaskMemberSummary>,
) {
  const recognition = item.materialItem.latest_recognition;
  return `提交人 ${formatTaskMemberLabel(item.materialItem.material.submitter_id, memberSummaryMap)}；${recognition ? formatRecognitionStatus(recognition.status) : "未触发识别"}`;
}

function syncActionEditorState(params: {
  task: ReimbursementTask | null;
  detailItem: ReviewMaterialDetailItem | null;
  actionInvoiceId: string;
  createSplitRowId: () => string;
}) {
  const { task, detailItem, actionInvoiceId, createSplitRowId } = params;
  const editableInvoiceCandidates = buildEditableInvoiceCandidates(detailItem);
  const nextActionInvoiceId = pickActionInvoiceId(editableInvoiceCandidates, actionInvoiceId);
  const selectedActionInvoice = editableInvoiceCandidates.find(
    (invoiceItem) => invoiceItem.invoice.id === nextActionInvoiceId,
  ) ?? null;

  return {
    invoiceFormState: task && detailItem
      ? buildInitialInvoiceFormState(detailItem.materialItem, detailItem.primaryInvoice, task)
      : null,
    invoiceFormErrors: {} as ReviewInvoiceEditorFormErrors,
    selectedActionInvoiceId: nextActionInvoiceId,
    splitRows: task && detailItem && selectedActionInvoice
      ? buildInitialSplitRows(selectedActionInvoice, detailItem.materialItem, task, createSplitRowId)
      : [],
    splitErrors: {} as ReviewSplitFormErrors,
    actionError: null as unknown,
    actionFeedback: null as ReviewActionFeedback | null,
  };
}

export function AdminReviewOverviewPage() {
  const session = useAuthSession();
  const { confirm } = useConfirmDialog();
  const { taskId } = useParams<{ taskId: string }>();
  const [state, setState] = useState<ReviewPageState>({ status: "loading" });
  const [selectedMaterialId, setSelectedMaterialId] = useState("");
  const [previewState, setPreviewState] = useState<ReviewPreviewState>({ status: "idle" });
  const [detailTab, setDetailTab] = useState<ReviewDetailTab>("preview");
  const [refreshNonce, setRefreshNonce] = useState(0);
  const [actionError, setActionError] = useState<unknown>(null);
  const [invoiceFormState, setInvoiceFormState] = useState<ReviewInvoiceEditorFormState | null>(null);
  const [invoiceFormErrors, setInvoiceFormErrors] = useState<ReviewInvoiceEditorFormErrors>({});
  const [isSavingInvoice, setIsSavingInvoice] = useState(false);
  const [isConfirmingPaperReceipt, setIsConfirmingPaperReceipt] = useState(false);
  const [selectedActionInvoiceId, setSelectedActionInvoiceId] = useState("");
  const [splitRows, setSplitRows] = useState<ReviewSplitFormRow[]>([]);
  const [splitErrors, setSplitErrors] = useState<ReviewSplitFormErrors>({});
  const [isSavingSplits, setIsSavingSplits] = useState(false);
  const [actionFeedback, setActionFeedback] = useState<ReviewActionFeedback | null>(null);
  const selectedMaterialIdRef = useRef(selectedMaterialId);
  const selectedActionInvoiceIdRef = useRef(selectedActionInvoiceId);
  const nextSplitRowSequenceRef = useRef(0);

  function createSplitRowId() {
    const rowId = `review-split-row-${nextSplitRowSequenceRef.current}`;
    nextSplitRowSequenceRef.current += 1;
    return rowId;
  }

  useEffect(() => {
    selectedMaterialIdRef.current = selectedMaterialId;
  }, [selectedMaterialId]);

  useEffect(() => {
    selectedActionInvoiceIdRef.current = selectedActionInvoiceId;
  }, [selectedActionInvoiceId]);

  useEffect(() => {
    let cancelled = false;

    async function loadReviewPage() {
      if (!session || session.role !== "admin" || !taskId) {
        return;
      }

      setState({ status: "loading" });

      try {
        const [task, reviewSummary, overdueSummary] = await Promise.all([
          trmsApi.getTask(taskId),
          trmsApi.getTaskReviewSummary(taskId, session.actorId),
          trmsApi.listTaskOverdueConfirmations(taskId, session.actorId),
        ]);

        if (cancelled) {
          return;
        }

        const detailItems = buildReviewDetailItems(reviewSummary);
        const nextSelectedMaterialId = pickSelectedMaterialId(detailItems, selectedMaterialIdRef.current);
        const nextSelectedDetailItem = detailItems.find(
          (item) => item.materialItem.material.id === nextSelectedMaterialId,
        ) ?? null;
        const nextEditorState = syncActionEditorState({
          task,
          detailItem: nextSelectedDetailItem,
          actionInvoiceId: selectedActionInvoiceIdRef.current,
          createSplitRowId,
        });

        setSelectedMaterialId(nextSelectedMaterialId);
        setInvoiceFormState(nextEditorState.invoiceFormState);
        setInvoiceFormErrors(nextEditorState.invoiceFormErrors);
        setSelectedActionInvoiceId(nextEditorState.selectedActionInvoiceId);
        setSplitRows(nextEditorState.splitRows);
        setSplitErrors(nextEditorState.splitErrors);
        setActionError(nextEditorState.actionError);
        setActionFeedback(nextEditorState.actionFeedback);
        setState({
          status: "ready",
          task,
          reviewSummary,
          overdueSummary,
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

    void loadReviewPage();

    return () => {
      cancelled = true;
    };
  }, [refreshNonce, session, taskId]);

  const detailItems = useMemo(
    () => (state.status === "ready" ? buildReviewDetailItems(state.reviewSummary) : []),
    [state],
  );

  const task = state.status === "ready" ? state.task : null;
  const isForeignTask = task && session ? !isTaskVisibleToAdministrator(task, session.actorId) : false;
  const visibleTask = state.status === "ready" && !isForeignTask ? state.task : null;
  const visibleSummary = state.status === "ready" && !isForeignTask ? state.reviewSummary : null;
  const visibleOverdueSummary = state.status === "ready" && !isForeignTask ? state.overdueSummary : null;
  const pendingPaperReceiptInvoiceItems = useMemo(
    () => (
      visibleSummary
        ? visibleSummary.invoices.filter(
            (item) => item.invoice.is_paper_invoice && !item.invoice.paper_invoice_received,
          )
        : []
    ),
    [visibleSummary],
  );
  const memberSummaryMap: Map<string, TaskMemberSummary> = visibleTask
    ? buildTaskMemberSummaryMap(visibleTask.member_summaries)
    : new Map<string, TaskMemberSummary>();
  const selectedDetailItem = visibleSummary
    ? detailItems.find((item) => item.materialItem.material.id === selectedMaterialId) ?? null
    : null;

  useEffect(() => {
    let cancelled = false;
    let objectUrl: string | null = null;

    async function loadPreview() {
      const material = selectedDetailItem?.materialItem.material ?? null;
      if (!material) {
        setPreviewState({ status: "idle" });
        return;
      }
      if (!isPreviewableContentType(material.content_type)) {
        setPreviewState({
          status: "unsupported",
          contentType: material.content_type,
        });
        return;
      }

      setPreviewState({ status: "loading" });

      try {
        const previewFile = await trmsApi.downloadMaterialContent(material.id);
        if (cancelled) {
          return;
        }

        objectUrl = URL.createObjectURL(previewFile.blob);
        setPreviewState({
          status: "ready",
          url: objectUrl,
          contentType: previewFile.contentType ?? material.content_type ?? "application/octet-stream",
        });
      } catch (error) {
        if (cancelled) {
          return;
        }
        setPreviewState({
          status: "error",
          error,
        });
      }
    }

    void loadPreview();

    return () => {
      cancelled = true;
      if (objectUrl) {
        URL.revokeObjectURL(objectUrl);
      }
    };
  }, [selectedDetailItem]);

  if (!session || session.role !== "admin") {
    return null;
  }

  if (!taskId) {
    return (
      <AdminWorkspaceShell
        activeModule="review"
        header={(
          <PageHeader
            eyebrow="材料审核"
            title="管理员复核总览"
            description="集中查看任务材料风险、成员确认和导出准备度。"
          />
        )}
      >
        <SurfaceCard component="section" className="status-card">
          <p className="eyebrow">复核总览</p>
          <h2>任务标识缺失</h2>
          <p>暂时无法读取该任务，请从任务列表重新进入。</p>
        </SurfaceCard>
      </AdminWorkspaceShell>
    );
  }

  const anomalyItems = visibleSummary && visibleOverdueSummary
    ? buildReviewAnomalies(visibleSummary, visibleOverdueSummary)
    : [];
  const outstandingMemberIds = visibleSummary
    ? buildOutstandingMemberIds(visibleSummary)
    : [];
  const disputedItems = visibleSummary
    ? buildDisputedConfirmationItems(visibleSummary)
    : [];
  const selectedMaterial = selectedDetailItem?.materialItem.material ?? null;
  const selectedRecognition = selectedDetailItem?.materialItem.latest_recognition ?? null;
  const selectedInvoice = selectedDetailItem?.primaryInvoice ?? null;
  const relatedInvoices = selectedDetailItem?.relatedInvoices ?? [];
  const selectedValidations = selectedInvoice?.validations.filter(
    (validation) => validation.status !== "passed" && validation.status !== "not_applicable",
  ) ?? [];
  const recognitionEntries = selectedRecognition
    ? Object.entries(selectedRecognition.recognized_fields)
    : [];
  const editableInvoiceCandidates = buildEditableInvoiceCandidates(selectedDetailItem);
  const selectedActionInvoice = editableInvoiceCandidates.find(
    (invoiceItem) => invoiceItem.invoice.id === selectedActionInvoiceId,
  ) ?? editableInvoiceCandidates[0] ?? null;
  const splitSummary = buildSplitSummaryRows(splitRows);
  const splitAmountDifferenceCents = selectedActionInvoice
    ? splitSummary.totalAmountCents - selectedActionInvoice.invoice.amount_cents
    : 0;

  function updateInvoiceField<Key extends keyof ReviewInvoiceEditorFormState>(
    key: Key,
    value: ReviewInvoiceEditorFormState[Key],
  ) {
    setInvoiceFormState((current) => {
      if (!current) {
        return current;
      }
      return {
        ...current,
        [key]: value,
      };
    });
    setInvoiceFormErrors((current) => {
      if (!(key in current)) {
        return current;
      }
      const next = { ...current };
      delete next[key];
      return next;
    });
  }

  function updateSplitRow(
    rowId: string,
    field: keyof Omit<ReviewSplitFormRow, "rowId">,
    value: string,
  ) {
    setSplitRows((current) => current.map((row) => (row.rowId === rowId ? { ...row, [field]: value } : row)));
    setSplitErrors((current) => {
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

  function handleAddSplitRow() {
    if (!visibleTask || !selectedDetailItem || !selectedActionInvoice) {
      return;
    }

    setSplitRows((current) => [
      ...current,
      {
        rowId: createSplitRowId(),
        memberId: pickDefaultSplitMemberId(selectedActionInvoice, selectedDetailItem.materialItem, visibleTask),
        amountYuan: "",
        note: "",
      },
    ]);
  }

  async function handleRemoveSplitRow(rowId: string, rowIndex: number) {
    if (splitRows.length <= 1 || !visibleTask || !selectedActionInvoice) {
      return;
    }

    const confirmed = await confirm({
      title: `确认删除分摊行 ${rowIndex}？`,
      description: `当前正在编辑任务 ${visibleTask.competition_name} 下发票 ${selectedActionInvoice.invoice.invoice_number} 的分摊方案。删除后，这一行尚未保存的成员、金额和备注会直接丢失。`,
      confirmLabel: "删除分摊行",
      cancelLabel: "继续编辑",
      destructive: true,
    });
    if (!confirmed) {
      return;
    }

    setSplitRows((current) => current.filter((row) => row.rowId !== rowId));
    setSplitErrors((current) => {
      if (!(rowId in current)) {
        return current;
      }
      const next = { ...current };
      delete next[rowId];
      return next;
    });
  }

  async function handleSaveInvoice(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!session || !visibleTask || !selectedDetailItem || !invoiceFormState) {
      return;
    }

    const allowedExpenseTypes = visibleTask.fee_categories.filter(isExpenseType);
    const nextErrors = validateInvoiceForm(invoiceFormState, allowedExpenseTypes);
    setInvoiceFormErrors(nextErrors);
    setActionError(null);
    if (Object.keys(nextErrors).length > 0) {
      return;
    }

    const amountCents = parseAmountYuanToCents(invoiceFormState.amountYuan);
    if (amountCents === null) {
      return;
    }

    setIsSavingInvoice(true);
    try {
      const response = await trmsApi.createOrUpdateInvoice(selectedDetailItem.materialItem.material.id, {
        actor_id: session.actorId,
        invoice_number: invoiceFormState.invoiceNumber.trim(),
        issue_date: invoiceFormState.issueDate.trim() || null,
        transaction_time: toApiDateTime(invoiceFormState.transactionTime),
        buyer_name: invoiceFormState.buyerName.trim(),
        tax_number: invoiceFormState.taxNumber.trim(),
        seller_name: invoiceFormState.sellerName.trim() || null,
        corporate_transfer_reference: invoiceFormState.corporateTransferReference.trim() || null,
        amount_cents: amountCents,
        expense_type: invoiceFormState.expenseType,
      });

      setActionFeedback({
        invoiceId: response.invoice.id,
        kind: "invoice",
        message: `已保存发票 ${response.invoice.invoice_number} 的字段更正，并刷新当前材料摘要。`,
      });
      setRefreshNonce((current) => current + 1);
    } catch (error) {
      setActionError(error);
    } finally {
      setIsSavingInvoice(false);
    }
  }

  async function handleConfirmPaperReceipt() {
    if (!session || !selectedActionInvoice) {
      return;
    }

    setActionError(null);
    setIsConfirmingPaperReceipt(true);
    try {
      const response = await trmsApi.confirmPaperInvoiceReceipt(selectedActionInvoice.invoice.id, {
        actor_id: session.actorId,
      });
      setActionFeedback({
        invoiceId: response.invoice.id,
        kind: "paper_receipt",
        message: `已确认收到纸质发票 ${response.invoice.invoice_number}，相关校验已刷新。`,
      });
      setRefreshNonce((current) => current + 1);
    } catch (error) {
      setActionError(error);
    } finally {
      setIsConfirmingPaperReceipt(false);
    }
  }

  async function handleConfirmPendingPaperReceipts() {
    if (!session || pendingPaperReceiptInvoiceItems.length === 0) {
      return;
    }

    setActionError(null);
    setIsConfirmingPaperReceipt(true);
    try {
      const response = await trmsApi.confirmPaperInvoiceReceipts({
        actor_id: session.actorId,
        invoice_ids: pendingPaperReceiptInvoiceItems.map((item) => item.invoice.id),
      });
      const confirmedCount = response.items?.length ?? 1;
      setActionFeedback({
        invoiceId: null,
        kind: "paper_receipt",
        message: `已批量确认 ${confirmedCount} 张纸质发票收票，相关校验已刷新。`,
      });
      setRefreshNonce((current) => current + 1);
    } catch (error) {
      setActionError(error);
    } finally {
      setIsConfirmingPaperReceipt(false);
    }
  }

  async function handleSaveSplits(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!session || !visibleTask || !selectedActionInvoice || splitRows.length === 0) {
      return;
    }

    const nextErrors = validateSplitRows(splitRows);
    setSplitErrors(nextErrors);
    setActionError(null);
    if (Object.keys(nextErrors).length > 0) {
      return;
    }

    const confirmed = await confirm({
      title: splitAmountDifferenceCents === 0 ? "确认覆盖保存当前分摊方案？" : "确认保存未闭合的分摊方案？",
      description: splitAmountDifferenceCents === 0
        ? `发票 ${selectedActionInvoice.invoice.invoice_number} 将按当前表单覆盖保存 ${splitRows.length} 条分摊。服务端可能把受影响成员的确认状态重置为待确认，请确认金额和归属成员已核对无误。`
        : splitAmountDifferenceCents > 0
          ? `发票 ${selectedActionInvoice.invoice.invoice_number} 当前分摊合计比票面金额多出 ${formatCurrencyFromCents(splitAmountDifferenceCents)}。确认后仍会保存，但该发票会继续保留“分摊未完成”门禁。`
          : `发票 ${selectedActionInvoice.invoice.invoice_number} 当前分摊合计比票面金额少了 ${formatCurrencyFromCents(Math.abs(splitAmountDifferenceCents))}。确认后仍会保存，但该发票会继续保留“分摊未完成”门禁。`,
      confirmLabel: "确认保存分摊",
      cancelLabel: "继续编辑",
      destructive: true,
    });
    if (!confirmed) {
      return;
    }

    setIsSavingSplits(true);
    try {
      await trmsApi.replaceInvoiceSplits(selectedActionInvoice.invoice.id, {
        actor_id: session.actorId,
        items: splitRows.map((row) => ({
          member_id: row.memberId.trim(),
          amount_cents: parseAmountYuanToCents(row.amountYuan) ?? 0,
          note: row.note.trim() || null,
        })),
      });

      setActionFeedback({
        invoiceId: selectedActionInvoice.invoice.id,
        kind: "split",
        message: `已保存发票 ${selectedActionInvoice.invoice.invoice_number} 的分摊方案，并刷新确认状态。`,
      });
      setRefreshNonce((current) => current + 1);
    } catch (error) {
      setActionError(error);
    } finally {
      setIsSavingSplits(false);
    }
  }

  return (
    <AdminWorkspaceShell
      activeModule="review"
      taskId={taskId}
      task={visibleTask}
      header={(
        <PageHeader
          eyebrow="材料审核"
          title="管理员复核总览"
          description="在同一任务上下文里筛选当前材料、查看原件与识别结果，并决定下一步更正或分摊处理动作。"
          actions={(
            <div className="page-actions">
              <Button component={RouterLink} variant="contained" to={`/admin/tasks/${taskId}/corrections`}>
                处理更正与提醒
              </Button>
              <Button component={RouterLink} variant="outlined" to={`/admin/tasks/${taskId}/invoices`}>
                打开发票录入页
              </Button>
            </div>
          )}
        />
      )}
    >
      {state.status === "loading" ? (
        <SurfaceCard component="section" className="status-card admin-review-panel">
          <p className="eyebrow">加载中</p>
          <h2>正在加载复核总览</h2>
          <p>正在读取任务详情、复核摘要和逾期确认信息，请稍候。</p>
        </SurfaceCard>
      ) : null}

      {state.status === "error" ? <ApiErrorNotice error={state.error} /> : null}

      {state.status === "ready" && isForeignTask ? (
        <SurfaceCard component="section" className="status-card admin-review-panel">
          <p className="eyebrow">访问范围</p>
          <h2>当前任务不属于此管理员</h2>
          <p>你当前没有查看该任务的权限，如需访问请联系对应负责人。</p>
        </SurfaceCard>
      ) : null}

      {visibleTask && visibleSummary && visibleOverdueSummary ? (
        <>
          <SurfaceCard component="section" className="status-card admin-review-panel">
            <div className="task-card-header">
              <div>
                <p className="task-card-id">材料审核</p>
                <h2>{visibleTask.competition_name}</h2>
              </div>
              <StatusBadge tone="info">{formatTaskStatus(visibleTask.status)}</StatusBadge>
            </div>
            <div className="admin-review-summary-grid">
              <div>
                <dt>比赛地点</dt>
                <dd>{visibleTask.competition_location}</dd>
              </div>
              <div>
                <dt>提交截止</dt>
                <dd>{formatDateTime(visibleTask.deadline)}</dd>
              </div>
              <div>
                <dt>材料 / 待归属</dt>
                <dd>
                  {visibleSummary.counts.material_count} / {visibleSummary.counts.pending_assignment_material_count}
                </dd>
              </div>
              <div>
                <dt>发票 / 校验</dt>
                <dd>
                  {visibleSummary.counts.invoice_count} / {visibleSummary.counts.validation_count}
                </dd>
              </div>
              <div>
                <dt>分摊确认进度</dt>
                <dd>
                  {visibleSummary.counts.confirmed_split_count} / {visibleSummary.counts.split_count}
                </dd>
              </div>
              <div>
                <dt>逾期未确认成员</dt>
                <dd>{visibleOverdueSummary.total_overdue_members}</dd>
              </div>
            </div>
          </SurfaceCard>

          <SurfaceCard component="section" className="status-card admin-review-panel">
            <div className="admin-form-header">
              <div>
                <p className="eyebrow">审核风险</p>
                <h2>本任务待处理风险</h2>
              </div>
              <StatusBadge tone="info">{anomalyItems.length} 类重点项</StatusBadge>
            </div>
            {anomalyItems.length > 0 ? (
              <ul className="task-anomaly-list" aria-label="复核风险摘要">
                {anomalyItems.map((item) => (
                  <li key={item.label}>
                    <strong>{item.label}</strong>
                    <StatusBadge tone={item.tone === "failed" ? "danger" : "warning"}>
                      {item.count}
                    </StatusBadge>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="task-healthy-note">当前复核摘要下没有待突出显示的异常项。</p>
            )}
            {outstandingMemberIds.length > 0 ? (
              <div className="admin-review-subsection">
                <h4>当前未完成确认成员</h4>
                <ul className="token-list" aria-label="未完成确认成员">
                  {outstandingMemberIds.map((memberId) => (
                    <MetadataChip
                      key={memberId}
                      component="li"
                      className="token-chip"
                      label={formatTaskMemberLabel(memberId, memberSummaryMap)}
                    />
                  ))}
                </ul>
              </div>
            ) : null}
            {visibleOverdueSummary.overdue_member_ids.length > 0 ? (
              <div className="admin-review-subsection">
                <h4>已逾期未确认成员</h4>
                <ul className="token-list" aria-label="逾期未确认成员">
                  {visibleOverdueSummary.overdue_member_ids.map((memberId) => (
                    <MetadataChip
                      key={memberId}
                      component="li"
                      className="token-chip"
                      label={formatTaskMemberLabel(memberId, memberSummaryMap)}
                    />
                  ))}
                </ul>
              </div>
            ) : null}
            {disputedItems.length > 0 ? (
              <div className="admin-review-subsection">
                <h4>当前成员异议</h4>
                <ul className="admin-review-list" aria-label="成员异议列表">
                  {disputedItems.map(({ invoiceNumber, split, confirmation }) => (
                    <li key={split.id}>
                      <strong>
                        {formatTaskMemberLabel(split.member_id, memberSummaryMap)} / {invoiceNumber} / {formatCurrencyFromCents(split.amount_cents)}
                      </strong>
                      <span>{confirmation.dispute_reason ?? "未填写异议原因"}</span>
                      <span>提交时间：{formatDateTime(confirmation.updated_at)}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
            {pendingPaperReceiptInvoiceItems.length > 0 ? (
              <div className="admin-review-subsection">
                <h4>待确认纸票</h4>
                <p className="field-hint">
                  当前有 {pendingPaperReceiptInvoiceItems.length} 张纸质发票尚未确认收票；确认后会逐张刷新纸票收票校验。
                </p>
                {actionError ? <ApiErrorNotice error={actionError} /> : null}
                <div className="admin-form-footer">
                  <Button
                    type="button"
                    variant="contained"
                    disabled={isConfirmingPaperReceipt}
                    onClick={() => {
                      void handleConfirmPendingPaperReceipts();
                    }}
                  >
                    {isConfirmingPaperReceipt ? "正在批量确认收票..." : `批量确认 ${pendingPaperReceiptInvoiceItems.length} 张纸票`}
                  </Button>
                </div>
                {actionFeedback?.kind === "paper_receipt" ? (
                  <p className="field-hint">{actionFeedback.message}</p>
                ) : null}
              </div>
            ) : null}
          </SurfaceCard>

          <SurfaceCard component="section" className="status-card admin-review-panel">
            <div className="admin-form-header">
              <div>
                <p className="eyebrow">待归属</p>
                <h2>待归属材料</h2>
              </div>
              <StatusBadge tone={visibleSummary.pending_assignment_materials.length > 0 ? "danger" : "success"}>
                {visibleSummary.pending_assignment_materials.length} 份
              </StatusBadge>
            </div>
            {visibleSummary.pending_assignment_materials.length > 0 ? (
              <ul className="admin-review-record-list" aria-label="待归属材料列表">
                {visibleSummary.pending_assignment_materials.map((material) => (
                    <li key={material.id} className="admin-review-record-card">
                    <InvoiceSummaryRow
                      filename={material.original_filename}
                      invoiceNumber={null}
                      primaryLabel="待归属材料"
                      amountLabel={formatMaterialType(material.material_type)}
                      validationLabel="待归属"
                      validationTone="warning"
                      supportingMaterialCount={0}
                      statusHint={material.submitter_id_hint ? formatTaskMemberLabel(material.submitter_id_hint, memberSummaryMap) : "未提供成员提示"}
                      trailingContent={<StatusBadge tone="danger">待归属</StatusBadge>}
                    />
                    <div className="admin-review-inline-metadata">
                      <MetadataChip component="span" className="token-chip" label={formatMaterialType(material.material_type)} />
                      <MetadataChip component="span" className="token-chip" label={formatSubmissionChannel(material.channel)} />
                    </div>
                    <div className="task-meta-grid admin-review-meta-grid">
                      <div>
                        <dt>上传时间</dt>
                        <dd>{formatDateTime(material.created_at)}</dd>
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="field-hint">当前任务提示下没有待归属材料。</p>
            )}
          </SurfaceCard>

          <section className="admin-review-workspace">
            <SurfaceCard component="article" className="status-card admin-task-detail-panel admin-review-list-panel">
              <div className="admin-form-header">
                <div>
                  <p className="eyebrow">材料列表</p>
                  <h2>材料审核列表</h2>
                </div>
                <StatusBadge tone="info">{detailItems.length} 份材料</StatusBadge>
              </div>
              <p className="field-hint">
                先在左侧选中要处理的材料，再在右侧查看原件、识别字段、校验异常和分摊去向。
              </p>
              {detailItems.length > 0 ? (
                <div className="invoice-editor-select-panel">
                  <FormControl fullWidth>
                    <InputLabel id="admin-review-material-select-label">目标材料</InputLabel>
                    <Select
                      labelId="admin-review-material-select-label"
                      label="目标材料"
                      aria-label="目标材料"
                      value={selectedMaterialId}
                      onChange={(event) => {
                        const nextMaterialId = String(event.target.value);
                        const nextSelectedDetailItem = detailItems.find(
                          (item) => item.materialItem.material.id === nextMaterialId,
                        ) ?? null;
                        const nextEditorState = syncActionEditorState({
                          task: visibleTask,
                          detailItem: nextSelectedDetailItem,
                          actionInvoiceId: "",
                          createSplitRowId,
                        });

                        setSelectedMaterialId(nextMaterialId);
                        setInvoiceFormState(nextEditorState.invoiceFormState);
                        setInvoiceFormErrors(nextEditorState.invoiceFormErrors);
                        setSelectedActionInvoiceId(nextEditorState.selectedActionInvoiceId);
                        setSplitRows(nextEditorState.splitRows);
                        setSplitErrors(nextEditorState.splitErrors);
                        setActionError(nextEditorState.actionError);
                        setActionFeedback(nextEditorState.actionFeedback);
                      }}
                      renderValue={(value) => {
                        const currentItem = detailItems.find(
                          (item) => item.materialItem.material.id === String(value),
                        );
                        if (!currentItem) {
                          return "请选择材料";
                        }
                        const material = currentItem.materialItem.material;
                        const selectorStatus = getReviewDetailItemSelectorStatus(
                          currentItem,
                          currentItem.materialItem.latest_recognition,
                        );
                        return (
                          <span className="invoice-editor-select-value">
                            <span className="invoice-editor-select-value-title">
                              <strong title={getReviewDetailItemSelectorNumber(currentItem)}>
                                发票号：{getReviewDetailItemSelectorNumber(currentItem)}
                              </strong>
                              <span className={`invoice-editor-select-value-status invoice-editor-select-value-status-${selectorStatus.tone}`}>
                                校验通过：{selectorStatus.label}
                              </span>
                            </span>
                            <span title={material.original_filename}>文件：{material.original_filename}</span>
                            <span>
                              类型：{getReviewDetailItemSelectorType(currentItem)}；金额：{getReviewDetailItemSelectorAmount(currentItem)}
                            </span>
                          </span>
                        );
                      }}
                      MenuProps={{
                        PaperProps: {
                          sx: {
                            maxHeight: 420,
                            width: "min(560px, calc(100vw - 32px))",
                          },
                        },
                        MenuListProps: {
                          "aria-label": "材料下拉选项",
                        },
                      }}
                    >
                      {detailItems.map((item) => {
                        const material = item.materialItem.material;
                        const selectorStatus = getReviewDetailItemSelectorStatus(
                          item,
                          item.materialItem.latest_recognition,
                        );
                        return (
                          <MenuItem key={material.id} value={material.id} className="invoice-editor-select-option">
                            <span className="invoice-editor-select-option-content">
                              <span className="invoice-editor-select-option-title">
                                <strong title={getReviewDetailItemSelectorNumber(item)}>
                                  发票号：{getReviewDetailItemSelectorNumber(item)}
                                </strong>
                                <span className={`invoice-editor-select-value-status invoice-editor-select-value-status-${selectorStatus.tone}`}>
                                  校验通过：{selectorStatus.label}
                                </span>
                              </span>
                              <span className="invoice-editor-select-option-grid">
                                <span title={material.original_filename}>原始文件名：{material.original_filename}</span>
                                <span>类型：{getReviewDetailItemSelectorType(item)}</span>
                                <span>金额：{getReviewDetailItemSelectorAmount(item)}</span>
                                <span title={getReviewDetailItemSelectorHint(item, memberSummaryMap)}>
                                  {getReviewDetailItemSelectorHint(item, memberSummaryMap)}
                                </span>
                              </span>
                            </span>
                          </MenuItem>
                        );
                      })}
                    </Select>
                  </FormControl>
                  <p className="field-hint">候选材料会在展开层中滚动显示，方便你持续对照右侧详情处理。</p>
                </div>
              ) : (
                <p className="field-hint">当前任务还没有已归档材料。</p>
              )}
            </SurfaceCard>

            <SurfaceCard component="article" className="status-card admin-form-card admin-review-detail-panel" aria-label="当前材料详情">
              {selectedMaterial ? (
                <>
                  <div className="admin-form-header">
                    <div>
                      <p className="eyebrow">当前材料</p>
                      <h2>当前材料详情</h2>
                    </div>
                    <StatusBadge tone={buildRecognitionBadgeTone(selectedRecognition)}>
                      {selectedRecognition ? formatRecognitionStatus(selectedRecognition.status) : "未触发识别"}
                    </StatusBadge>
                  </div>

                  <div className="task-card-header">
                    <div>
                      <p className="task-card-id">当前材料</p>
                      <h3>{selectedMaterial.original_filename}</h3>
                    </div>
                    <StatusBadge tone="info">
                      {selectedInvoice ? `当前发票 ${selectedInvoice.invoice.invoice_number}` : "尚未形成主发票"}
                    </StatusBadge>
                  </div>

                  <div className="admin-review-inline-metadata">
                    <MetadataChip component="span" className="token-chip" label={formatMaterialType(selectedMaterial.material_type)} />
                    <MetadataChip component="span" className="token-chip" label={formatSubmissionChannel(selectedMaterial.channel)} />
                    <MetadataChip component="span" className="token-chip" label={formatTaskMemberLabel(selectedMaterial.submitter_id, memberSummaryMap)} />
                    {selectedInvoice ? (
                      <MetadataChip component="span" className="token-chip" label={formatExpenseType(selectedInvoice.invoice.expense_type)} />
                    ) : null}
                  </div>

                  <div className="task-meta-grid admin-review-meta-grid admin-review-detail-grid">
                    <div>
                      <dt>上传时间</dt>
                      <dd>{formatDateTime(selectedMaterial.created_at)}</dd>
                    </div>
                    <div>
                      <dt>内容类型</dt>
                      <dd>{selectedMaterial.content_type ?? "未知"}</dd>
                    </div>
                    <div>
                      <dt>主发票</dt>
                      <dd>{describeInvoiceReference(selectedInvoice)}</dd>
                    </div>
                    <div>
                      <dt>辅助归属到</dt>
                      <dd>{describeSupportingInvoiceReferences(relatedInvoices.filter((item) => item.invoice.id !== selectedInvoice?.invoice.id))}</dd>
                    </div>
                  </div>

                  <Box sx={{ mt: 3, borderBottom: 1, borderColor: "divider" }}>
                    <Tabs
                      value={detailTab}
                      onChange={(_, value: ReviewDetailTab) => {
                        setDetailTab(value);
                      }}
                      aria-label="当前材料详情标签页"
                      variant="scrollable"
                      allowScrollButtonsMobile
                    >
                      <Tab label="附件预览" value="preview" />
                      <Tab label="识别字段" value="recognition" />
                      <Tab label="校验异常" value="validation" />
                      <Tab label="处理动作" value="actions" />
                    </Tabs>
                  </Box>

                  {detailTab === "preview" ? (
                    <section className="admin-review-subsection">
                      <h4>原始票据预览</h4>
                      {previewState.status === "loading" ? (
                        <p className="field-hint">正在拉取原始材料内容，请稍候。</p>
                      ) : null}
                      {previewState.status === "unsupported" ? (
                        <p className="field-hint">
                          当前材料类型为 {previewState.contentType ?? "未知"}，暂不支持内联预览，请通过材料列表继续判断是否需要更正归属或附件类型。
                        </p>
                      ) : null}
                      {previewState.status === "error" ? <ApiErrorNotice error={previewState.error} /> : null}
                      {previewState.status === "ready" ? (
                        <div className="admin-review-preview-shell">
                          {previewState.contentType.startsWith("image/") ? (
                            <img
                              className="admin-review-preview-image"
                              src={previewState.url}
                              alt={`${selectedMaterial.original_filename} 预览`}
                            />
                          ) : (
                            <object
                              className="admin-review-preview-frame"
                              data={previewState.url}
                              type={previewState.contentType}
                              aria-label="原始票据 PDF 预览"
                            >
                              <p className="field-hint">当前环境暂时无法直接显示 PDF，但材料内容已经成功加载。</p>
                            </object>
                          )}
                        </div>
                      ) : null}
                    </section>
                  ) : null}

                  {detailTab === "recognition" ? (
                    <section className="admin-review-subsection">
                      <h4>识别字段与来源</h4>
                      {selectedRecognition ? (
                        <>
                          <ul className="admin-review-list">
                            <li>
                              <strong>最近识别状态</strong>
                              <span>{formatRecognitionStatus(selectedRecognition.status)}</span>
                            </li>
                            {selectedRecognition.failure ? (
                              <li>
                                <strong>识别提示</strong>
                                <span>{describeRecognitionFailure(selectedRecognition.failure)}</span>
                              </li>
                            ) : null}
                            <li>
                              <strong>低置信度字段数</strong>
                              <span>
                                {
                                  recognitionEntries.filter(([, field]) => field.status === "needs_confirmation").length
                                }
                              </span>
                            </li>
                          </ul>
                          {recognitionEntries.length > 0 ? (
                            <div className="recognition-field-grid">
                              {recognitionEntries.map(([fieldName, field]) => (
                                <article key={fieldName} className="recognition-field-card">
                                  <h4>{formatFieldLabel(fieldName)}</h4>
                                  <p className="recognition-field-value">
                                    {describeRecognitionFieldValue(
                                      field.value,
                                      fieldName,
                                      selectedMaterial.material_type,
                                    )}
                                  </p>
                                  <dl className="task-meta-grid admin-review-detail-field-grid">
                                    <div>
                                      <dt>置信度</dt>
                                      <dd>{Math.round(field.confidence * 100)}%</dd>
                                    </div>
                                    <div>
                                      <dt>状态</dt>
                                      <dd>{field.status === "needs_confirmation" ? "待人工确认" : "可直接采用"}</dd>
                                    </div>
                                  </dl>
                                </article>
                              ))}
                            </div>
                          ) : (
                            <p className="field-hint">当前识别结果还没有可展示的结构化字段。</p>
                          )}
                        </>
                      ) : (
                        <p className="field-hint">当前材料尚无识别任务结果。</p>
                      )}
                    </section>
                  ) : null}

                  {detailTab === "validation" ? (
                    <section className="admin-review-subsection">
                      <h4>当前票据与校验异常</h4>
                      {selectedInvoice ? (
                        <>
                          <div className="task-meta-grid admin-review-meta-grid admin-review-detail-grid">
                            <div>
                              <dt>发票号码</dt>
                              <dd>{selectedInvoice.invoice.invoice_number}</dd>
                            </div>
                            <div>
                              <dt>金额</dt>
                              <dd>{formatCurrencyFromCents(selectedInvoice.invoice.amount_cents)}</dd>
                            </div>
                            <div>
                              <dt>抬头 / 税号</dt>
                              <dd>{selectedInvoice.invoice.buyer_name} / {selectedInvoice.invoice.tax_number}</dd>
                            </div>
                            <div>
                              <dt>交易时间</dt>
                              <dd>
                                {selectedInvoice.invoice.transaction_time
                                  ? formatDateTime(selectedInvoice.invoice.transaction_time)
                                  : selectedInvoice.invoice.issue_date ?? "未录入"}
                              </dd>
                            </div>
                            <div>
                              <dt>支持附件数</dt>
                              <dd>{selectedInvoice.supporting_material_ids.length}</dd>
                            </div>
                            <div>
                              <dt>异常校验数</dt>
                              <dd>{selectedValidations.length}</dd>
                            </div>
                          </div>
                          {selectedInvoice.validations.length > 0 ? (
                            <ul className="admin-review-list" aria-label="当前材料校验列表">
                              {selectedValidations.length > 0
                                ? selectedValidations.map((validation) => (
                                    <li key={validation.id}>
                                      <strong>
                                        {formatValidationSeverity(validation.severity)} / {formatValidationRule(validation.rule_code)}
                                      </strong>
                                      <StatusBadge tone={buildValidationBadgeTone(validation)}>
                                        {formatValidationStatus(validation.status)}
                                      </StatusBadge>
                                      <span>{validation.message}</span>
                                    </li>
                                  ))
                                : (
                                  <li>
                                    <strong>当前发票暂无异常校验</strong>
                                    <span>所有已生成规则结果均为通过或不适用。</span>
                                  </li>
                                )}
                            </ul>
                          ) : (
                            <p className="field-hint">当前发票还没有校验结果。</p>
                          )}
                        </>
                      ) : selectedMaterial.material_type === "invoice" ? (
                        <p className="field-hint">
                          这份发票材料还没有人工确认后的发票记录。先检查左侧预览和识别字段，再进入发票录入页补录或更正金额、抬头和税号。
                        </p>
                      ) : relatedInvoices.length > 0 ? (
                        <ul className="admin-review-list" aria-label="关联发票摘要列表">
                          {relatedInvoices.map((invoiceItem) => (
                            <li key={invoiceItem.invoice.id}>
                              {(() => {
                                const invoiceMaterial = detailItems.find(
                                  (item) => item.materialItem.material.id === invoiceItem.invoice.material_id,
                                )?.materialItem.material ?? null;
                                const summaryValidation = buildInvoiceSummaryValidationStatus(invoiceItem);
                                const filename = invoiceMaterial?.original_filename ?? invoiceItem.invoice.invoice_number;
                                const abnormalValidationCount = invoiceItem.validations.filter(
                                  (item) => item.status === "failed" || item.status === "pending",
                                ).length;
                                return (
                                  <InvoiceSummaryRow
                                    filename={filename}
                                    invoiceNumber={invoiceItem.invoice.invoice_number}
                                    amountLabel={formatCurrencyFromCents(invoiceItem.invoice.amount_cents)}
                                    validationLabel={summaryValidation.label}
                                    validationTone={summaryValidation.tone}
                                    supportingMaterialCount={invoiceItem.supporting_material_ids.length}
                                    statusHint={`当前异常校验 ${abnormalValidationCount} 条`}
                                    trailingContent={(
                                      <StatusBadge tone="info">
                                        {formatExpenseType(invoiceItem.invoice.expense_type)}
                                      </StatusBadge>
                                    )}
                                    action={{
                                      ariaLabel: `关联发票 ${filename} ${invoiceItem.invoice.invoice_number}`,
                                      onClick: () => {
                                        setSelectedMaterialId(invoiceItem.invoice.material_id);
                                      },
                                    }}
                                  />
                                );
                              })()}
                            </li>
                          ))}
                        </ul>
                      ) : (
                        <p className="field-hint">
                          当前材料还没有关联到任何发票记录。若它应作为支付记录、比赛通知或行程单参与校验，请先确认归属关系。
                        </p>
                      )}
                    </section>
                  ) : null}

                  {detailTab === "actions" ? (
                    <>
                      {actionError ? <ApiErrorNotice error={actionError} /> : null}

                      {actionFeedback ? (
                        <section className="member-status-section">
                          <div className="member-status-section-header">
                            <div>
                              <h4>处理动作已保存</h4>
                              <p className="field-hint">{actionFeedback.message}</p>
                            </div>
                            <StatusBadge tone="success">已刷新摘要</StatusBadge>
                          </div>
                        </section>
                      ) : null}

                      {editableInvoiceCandidates.length > 1 ? (
                        <section className="member-status-section">
                          <div className="member-status-section-header">
                            <div>
                              <h4>选择当前要处理的关联发票</h4>
                              <p className="field-hint">
                                当前材料关联了多张发票；先选中目标发票，再在下方继续字段更正、分摊调整或纸票收票确认。
                              </p>
                            </div>
                          </div>
                          <FormControl fullWidth>
                            <InputLabel id="admin-review-action-invoice-select-label">处理目标发票</InputLabel>
                            <Select
                              labelId="admin-review-action-invoice-select-label"
                              label="处理目标发票"
                              aria-label="处理目标发票"
                              value={selectedActionInvoice?.invoice.id ?? ""}
                              onChange={(event) => {
                                const nextActionInvoiceId = String(event.target.value);
                                const nextSelectedActionInvoice = editableInvoiceCandidates.find(
                                  (invoiceItem) => invoiceItem.invoice.id === nextActionInvoiceId,
                                ) ?? null;
                                setSelectedActionInvoiceId(nextActionInvoiceId);
                                setSplitRows(
                                  visibleTask && selectedDetailItem && nextSelectedActionInvoice
                                    ? buildInitialSplitRows(
                                      nextSelectedActionInvoice,
                                      selectedDetailItem.materialItem,
                                      visibleTask,
                                      createSplitRowId,
                                    )
                                    : [],
                                );
                                setSplitErrors({});
                                setActionError(null);
                                setActionFeedback(null);
                              }}
                            >
                              {editableInvoiceCandidates.map((invoiceItem) => (
                                <MenuItem key={invoiceItem.invoice.id} value={invoiceItem.invoice.id}>
                                  {invoiceItem.invoice.invoice_number} / {formatExpenseType(invoiceItem.invoice.expense_type)} / {formatCurrencyFromCents(invoiceItem.invoice.amount_cents)}
                                </MenuItem>
                              ))}
                            </Select>
                          </FormControl>
                        </section>
                      ) : null}

                      {selectedMaterial.material_type === "invoice" && invoiceFormState ? (
                        <form
                          className="page-stack"
                          onSubmit={(event) => {
                            void handleSaveInvoice(event);
                          }}
                        >
                          <section className="member-status-section">
                            <div className="member-status-section-header">
                              <div>
                                <h4>发票字段更正</h4>
                                <p className="field-hint">
                                  直接在材料审核页核对并保存票号、金额、抬头、税号和费用类型，不再依赖跳转到独立发票录入页。
                                </p>
                              </div>
                              <StatusBadge tone="info">
                                {selectedInvoice ? `当前发票号 ${selectedInvoice.invoice.invoice_number}` : "尚无发票记录"}
                              </StatusBadge>
                            </div>
                            <div className="admin-form-grid">
                              <TextField
                                label="发票号码"
                                name="review-invoice-number"
                                value={invoiceFormState.invoiceNumber}
                                onChange={(event) => {
                                  updateInvoiceField("invoiceNumber", event.target.value);
                                }}
                                error={Boolean(invoiceFormErrors.invoiceNumber)}
                                helperText={invoiceFormErrors.invoiceNumber}
                                fullWidth
                              />
                              <TextField
                                label="金额（元）"
                                name="review-amount-yuan"
                                value={invoiceFormState.amountYuan}
                                onChange={(event) => {
                                  updateInvoiceField("amountYuan", event.target.value);
                                }}
                                error={Boolean(invoiceFormErrors.amountYuan)}
                                helperText={invoiceFormErrors.amountYuan}
                                fullWidth
                                slotProps={{
                                  htmlInput: {
                                    inputMode: "decimal",
                                    placeholder: "例如 123.45",
                                  },
                                }}
                              />
                              <TextField
                                label="开票日期"
                                type="date"
                                name="review-issue-date"
                                value={invoiceFormState.issueDate}
                                onChange={(event) => {
                                  updateInvoiceField("issueDate", event.target.value);
                                }}
                                fullWidth
                                slotProps={{ inputLabel: { shrink: true } }}
                              />
                              <TextField
                                label="交易时间"
                                type="datetime-local"
                                name="review-transaction-time"
                                value={invoiceFormState.transactionTime}
                                onChange={(event) => {
                                  updateInvoiceField("transactionTime", event.target.value);
                                }}
                                fullWidth
                                slotProps={{ inputLabel: { shrink: true } }}
                              />
                              <TextField
                                label="发票抬头"
                                name="review-buyer-name"
                                value={invoiceFormState.buyerName}
                                onChange={(event) => {
                                  updateInvoiceField("buyerName", event.target.value);
                                }}
                                error={Boolean(invoiceFormErrors.buyerName)}
                                helperText={invoiceFormErrors.buyerName}
                                fullWidth
                              />
                              <TextField
                                label="税号"
                                name="review-tax-number"
                                value={invoiceFormState.taxNumber}
                                onChange={(event) => {
                                  updateInvoiceField("taxNumber", event.target.value);
                                }}
                                error={Boolean(invoiceFormErrors.taxNumber)}
                                helperText={invoiceFormErrors.taxNumber}
                                fullWidth
                              />
                              <TextField
                                select
                                label="费用类型"
                                name="review-expense-type"
                                value={invoiceFormState.expenseType}
                                onChange={(event) => {
                                  updateInvoiceField("expenseType", event.target.value as ExpenseType);
                                }}
                                error={Boolean(invoiceFormErrors.expenseType)}
                                helperText={invoiceFormErrors.expenseType}
                                fullWidth
                              >
                                {visibleTask.fee_categories.filter(isExpenseType).map((expenseType) => (
                                  <MenuItem key={expenseType} value={expenseType}>
                                    {formatExpenseType(expenseType)}
                                  </MenuItem>
                                ))}
                              </TextField>
                              <TextField
                                label="销售方名称"
                                name="review-seller-name"
                                value={invoiceFormState.sellerName}
                                onChange={(event) => {
                                  updateInvoiceField("sellerName", event.target.value);
                                }}
                                fullWidth
                              />
                              <TextField
                                label="公对公转账编号"
                                name="review-corporate-transfer-reference"
                                value={invoiceFormState.corporateTransferReference}
                                onChange={(event) => {
                                  updateInvoiceField("corporateTransferReference", event.target.value);
                                }}
                                fullWidth
                              />
                            </div>
                            <div className="admin-form-footer">
                              <Button variant="contained" type="submit" disabled={isSavingInvoice}>
                                {isSavingInvoice ? "正在保存并刷新摘要" : "保存发票字段"}
                              </Button>
                            </div>
                          </section>
                        </form>
                      ) : selectedMaterial.material_type === "invoice" ? (
                        <section className="member-status-section">
                          <div className="member-status-section-header">
                            <div>
                              <h4>发票字段更正</h4>
                              <p className="field-hint">当前任务上下文还没有准备好可编辑的发票字段表单。</p>
                            </div>
                          </div>
                        </section>
                      ) : null}

                      {selectedActionInvoice ? (
                        <>
                          {selectedActionInvoice.invoice.is_paper_invoice ? (
                            <section className="member-status-section">
                              <div className="member-status-section-header">
                                <div>
                                  <h4>纸票接收确认</h4>
                                  <p className="field-hint">
                                    纸质发票的收票确认已并入材料审核页；管理员可直接在这里确认已收到纸票，不再跳转独立页处理。
                                  </p>
                                </div>
                                <StatusBadge tone={selectedActionInvoice.invoice.paper_invoice_received ? "success" : "warning"}>
                                  {selectedActionInvoice.invoice.paper_invoice_received ? "已确认收票" : "待确认收票"}
                                </StatusBadge>
                              </div>
                              <dl className="task-meta-grid admin-review-detail-grid">
                                <div>
                                  <dt>收票状态</dt>
                                  <dd>{selectedActionInvoice.invoice.paper_invoice_received ? "已收到纸票" : "尚未确认"}</dd>
                                </div>
                                <div>
                                  <dt>确认人</dt>
                                  <dd>{formatActorDisplay(selectedActionInvoice.invoice.paper_invoice_received_by)}</dd>
                                </div>
                                <div>
                                  <dt>确认时间</dt>
                                  <dd>
                                    {selectedActionInvoice.invoice.paper_invoice_received_at
                                      ? formatDateTime(selectedActionInvoice.invoice.paper_invoice_received_at)
                                      : "尚未确认"}
                                  </dd>
                                </div>
                              </dl>
                              {!selectedActionInvoice.invoice.paper_invoice_received ? (
                                <div className="admin-form-footer">
                                  <Button
                                    type="button"
                                    variant="contained"
                                    disabled={isConfirmingPaperReceipt}
                                    onClick={() => {
                                      void handleConfirmPaperReceipt();
                                    }}
                                  >
                                    {isConfirmingPaperReceipt ? "正在确认收票..." : "确认已收到纸票"}
                                  </Button>
                                </div>
                              ) : null}
                            </section>
                          ) : null}

                          <form
                            className="page-stack"
                            onSubmit={(event) => {
                              void handleSaveSplits(event);
                            }}
                          >
                            <section className="member-status-section">
                              <div className="member-status-section-header">
                                <div>
                                  <h4>分摊调整</h4>
                                  <p className="field-hint">
                                    当前发票的分摊编辑已并入材料审核页；管理员可直接在这里调整成员归属、金额和备注。
                                  </p>
                                </div>
                                <Button
                                  type="button"
                                  variant="outlined"
                                  onClick={handleAddSplitRow}
                                >
                                  新增分摊行
                                </Button>
                              </div>

                              <ul className="split-row-list" aria-label="当前材料分摊编辑列表">
                                {splitRows.map((row, index) => (
                                  <li
                                    key={row.rowId}
                                    role="group"
                                    className="split-row-card admin-review-record-card"
                                    aria-label={`分摊行 ${index + 1}`}
                                  >
                                    <div className="split-row-header">
                                      <strong>分摊行 {index + 1}</strong>
                                      <Button
                                        type="button"
                                        variant="outlined"
                                        onClick={() => {
                                          void handleRemoveSplitRow(row.rowId, index + 1);
                                        }}
                                        disabled={splitRows.length <= 1}
                                      >
                                        删除
                                      </Button>
                                    </div>

                                    <div className="admin-form-grid split-editor-form-grid">
                                      <TaskMemberAutocomplete
                                        label="归属成员"
                                        value={row.memberId}
                                        name={`review-member-${row.rowId}`}
                                        options={visibleTask.member_ids}
                                        memberSummaries={visibleTask.member_summaries}
                                        includeEmptyOption
                                        emptyOptionLabel="请选择成员"
                                        placeholder="输入成员姓名、用户名或学号筛选"
                                        onChange={(nextValue) => {
                                          updateSplitRow(row.rowId, "memberId", nextValue);
                                        }}
                                        error={Boolean(splitErrors[row.rowId]?.memberId)}
                                        helperText={splitErrors[row.rowId]?.memberId}
                                      />

                                      <TextField
                                        label="分摊金额（元）"
                                        name={`review-amount-${row.rowId}`}
                                        value={row.amountYuan}
                                        onChange={(event) => {
                                          updateSplitRow(row.rowId, "amountYuan", event.target.value);
                                        }}
                                        error={Boolean(splitErrors[row.rowId]?.amountYuan)}
                                        helperText={splitErrors[row.rowId]?.amountYuan}
                                        inputProps={{ inputMode: "decimal" }}
                                        fullWidth
                                      />

                                      <TextField
                                        className="split-editor-note-field"
                                        label="备注"
                                        name={`review-note-${row.rowId}`}
                                        value={row.note}
                                        onChange={(event) => {
                                          updateSplitRow(row.rowId, "note", event.target.value);
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
                                  <dd>{formatCurrencyFromCents(selectedActionInvoice.invoice.amount_cents)}</dd>
                                </div>
                                <div>
                                  <dt>分摊合计</dt>
                                  <dd>{formatCurrencyFromCents(splitSummary.totalAmountCents)}</dd>
                                </div>
                                <div>
                                  <dt>差额</dt>
                                  <dd
                                    className={
                                      splitAmountDifferenceCents === 0
                                        ? "split-difference-balanced"
                                        : "split-difference-unbalanced"
                                    }
                                  >
                                    {splitAmountDifferenceCents >= 0 ? "+" : "-"}
                                    {formatCurrencyFromCents(Math.abs(splitAmountDifferenceCents))}
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
                                  <h4>当前分摊确认状态</h4>
                                  <p className="field-hint">
                                    保存分摊后，服务端会按最新版本刷新成员确认状态；管理员无需再跳转到独立分摊页查看结果。
                                  </p>
                                </div>
                                <StatusBadge tone="info">
                                  已确认 {countCurrentConfirmationStatus(selectedActionInvoice, "confirmed")} / {selectedActionInvoice.splits.length}
                                </StatusBadge>
                              </div>

                              {selectedActionInvoice.splits.length === 0 ? (
                                <p className="field-hint">当前发票还没有已保存的分摊记录；首次保存后，会显示每个成员的最新确认状态。</p>
                              ) : (
                                <ul className="admin-review-record-list" aria-label="当前材料分摊列表">
                                  {selectedActionInvoice.splits.map(({ split, confirmation }) => (
                                    <li key={split.id} className="admin-review-record-card">
                                      <div className="task-card-header">
                                        <strong>
                                          {formatTaskMemberLabel(split.member_id, memberSummaryMap)} / {formatCurrencyFromCents(split.amount_cents)}
                                        </strong>
                                        <StatusBadge tone={buildConfirmationBadgeTone(confirmation)}>
                                          {confirmation?.is_current
                                            ? formatConfirmationStatus(confirmation.status)
                                            : "未提交确认"}
                                        </StatusBadge>
                                      </div>
                                      <span>版本 {split.version}</span>
                                      {split.note ? <span>备注：{split.note}</span> : null}
                                      {confirmation?.dispute_reason ? <span>异议原因：{confirmation.dispute_reason}</span> : null}
                                      <span>
                                        {confirmation?.is_current
                                          ? `最新确认时间：${formatDateTime(confirmation.updated_at)}`
                                          : "当前成员尚未确认最新分摊版本"}
                                      </span>
                                    </li>
                                  ))}
                                </ul>
                              )}
                            </section>

                            <div className="admin-form-footer">
                              <Button variant="contained" type="submit" disabled={isSavingSplits}>
                                {isSavingSplits ? "正在保存并刷新摘要" : "保存费用分摊"}
                              </Button>
                            </div>
                          </form>
                        </>
                      ) : selectedMaterial.material_type !== "invoice" ? (
                        <section className="member-status-section">
                          <div className="member-status-section-header">
                            <div>
                              <h4>当前材料可操作范围</h4>
                              <p className="field-hint">
                                当前辅助材料还没有关联到可编辑发票；请先确认归属关系，或去“处理更正与提醒”页继续催办。
                              </p>
                            </div>
                          </div>
                        </section>
                      ) : null}

                      <div className="inline-actions admin-review-action-row">
                        <Button
                          component={RouterLink}
                          variant="outlined"
                          size="small"
                          to={`/admin/tasks/${taskId}/corrections`}
                        >
                          处理更正与提醒
                        </Button>
                      </div>
                    </>
                  ) : null}
                </>
              ) : (
                <>
                  <p className="eyebrow">当前材料</p>
                  <h2>当前没有可查看的材料</h2>
                  <p className="field-hint">当前任务还没有已归档材料，暂时无法进入列表-详情联动复核。</p>
                </>
              )}
            </SurfaceCard>
          </section>
        </>
      ) : null}
    </AdminWorkspaceShell>
  );
}
