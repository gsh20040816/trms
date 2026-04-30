import { type FormEvent, type SyntheticEvent, useEffect, useMemo, useState } from "react";
import { Link, useLocation, useNavigate, useSearchParams } from "react-router-dom";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import LinearProgress from "@mui/material/LinearProgress";
import MenuItem from "@mui/material/MenuItem";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";

import { ApiErrorNotice } from "../components/ApiErrorNotice";
import { FileDropZone } from "../components/FileDropZone";
import { ApiError } from "../lib/api/client";
import {
  EmptyState,
  PageHeader,
  RoleWorkspace,
  SectionCard,
  StatCard,
  StatusBadge,
} from "../components/dashboard";
import { useSnackbar } from "../components/use-snackbar";
import { trmsApi } from "../lib/api/trms";
import type {
  ConfirmationStatus,
  ConfirmationRecord,
  ExpenseType,
  ExpenseDetailItem,
  ExpenseSplitRecord,
  InvoiceMemberSubmissionBatchFailure,
  InvoiceMemberSubmissionBatchResponse,
  InvoiceMemberSubmissionStatus,
  InvoiceRecord,
  MaterialBatchUploadResponse,
  MaterialRecord,
  MaterialType,
  PendingSupportingMaterialLinkageItem,
  RecognitionFailureDetail,
  RecognitionFieldResult,
  RecognitionTaskRecord,
  RecognitionTaskStatus,
  ReimbursementTask,
  TaskMemberWorkbenchItem as TaskMemberWorkbenchSummaryItem,
  TaskMemberWorkbenchQueueGroup,
  TaskMemberMaterialStatusItem,
  TaskMemberStatusReport,
  TaskSharedInvoiceItem,
  ValidationResult,
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
import { findOversizedFile, MAX_UPLOAD_FILE_BYTES } from "../lib/upload-validation";
import { useAuthSession } from "./auth-store";

type VisibleTaskState =
  | { status: "loading" }
  | { status: "error"; error: unknown }
  | { status: "ready"; visibleTasks: ReimbursementTask[] };

type SelectedTaskWorkbenchState =
  | { status: "idle" }
  | { status: "loading"; task: ReimbursementTask }
  | { status: "error"; task: ReimbursementTask; error: unknown }
  | {
    status: "ready";
    task: ReimbursementTask;
    report: TaskMemberStatusReport;
    items: WorkbenchInvoiceItem[];
    pendingSupportingMaterialLinkageItems: PendingSupportingMaterialLinkageItem[];
    sharedInvoices: TaskSharedInvoiceItem[];
  };

type PendingAction = {
  id: string;
  title: string;
  detail: string;
  to: string;
  tone: "info" | "warning" | "danger";
  label: string;
};

type InvoiceQueueGroupKey =
  | "ready"
  | "recognition_pending"
  | "recognition_review"
  | "supporting_material_linkage"
  | "missing_materials"
  | "split_incomplete"
  | "confirmation_incomplete";

type InvoiceQueueGroup = {
  key: InvoiceQueueGroupKey;
  title: string;
  description: string;
  tone: "info" | "warning" | "success";
  items: WorkbenchInvoiceItem[];
};

type WorkbenchTab = "invoices" | "missing-materials" | "confirmations";

type WorkbenchInvoiceItem = {
  material: TaskMemberMaterialStatusItem;
  invoice: InvoiceRecord | null;
  recognition: WorkbenchRecognition | null;
  validations: ValidationResult[];
  supportingMaterials: MaterialRecord[];
  splits: ExpenseSplitRecord[];
  confirmations: ConfirmationRecord[];
  relatedExpenseDetails: ExpenseDetailItem[];
  missingMaterials: TaskMemberStatusReport["missing_materials"];
  queueGroup?: TaskMemberWorkbenchQueueGroup;
  blockingReasons?: Array<Exclude<TaskMemberWorkbenchQueueGroup, "ready">>;
  readyForSubmission?: boolean;
};

type WorkbenchRecognition = Pick<
  RecognitionTaskRecord,
  "id" | "material_id" | "status" | "failure" | "recognized_fields" | "manual_corrections" | "created_at" | "updated_at"
>;

type SplitDraftRow = {
  key: string;
  member_id: string;
  amount_yuan: string;
  note: string;
};

type WorkbenchUploadFormState = {
  files: File[];
};

type WorkbenchUploadValidationErrors = Partial<Record<keyof WorkbenchUploadFormState, string>>;

type WorkbenchConfirmationItem = {
  detail: ExpenseDetailItem;
  supportingMaterials: MaterialRecord[];
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

type ManualInvoiceFormErrors = Partial<Record<keyof ManualInvoiceFormState, string>>;

type ConfirmationFeedback = {
  splitId: string;
  status: Extract<ConfirmationStatus, "confirmed" | "disputed">;
};

type ManualInvoiceSaveFeedback = {
  materialId: string;
  invoiceNumber: string;
  validationCount: number;
  failedValidationCount: number;
  pendingValidationCount: number;
};

type MaterialActionFeedback = {
  materialId: string;
  tone: "success" | "warning" | "error";
  message: string;
};

type InvoiceBatchAction = "submit" | "withdraw";

type InvoiceBatchActionFeedback = InvoiceMemberSubmissionBatchResponse & {
  action: InvoiceBatchAction;
};

type InvoiceWorkbenchSelection =
  | { kind: "own"; materialId: string }
  | { kind: "shared"; invoiceId: string };

type PendingSupportingMaterialLinkageAction = {
  materialId: string;
  invoiceId: string;
};

type UploadProcessingStageKey =
  | "received"
  | "recognition_pending"
  | "recognized"
  | "linked"
  | "action_required";

type UploadProcessingStageTone = "neutral" | "info" | "warning" | "danger" | "success";

type UploadProcessingSnapshot = {
  stage: UploadProcessingStageKey;
  tone: UploadProcessingStageTone;
  label: string;
  detail: string;
  steps: UploadProcessingStageKey[];
  transitioning: boolean;
  actionLabel: string | null;
  actionHref: string | null;
};

type ReimbursementMaterialUiStatus =
  | "uploaded"
  | "processing"
  | "recognized"
  | "needs_confirmation"
  | "missing_info"
  | "suspicious"
  | "confirmed"
  | "excluded";

type MaterialResultGroupKey =
  | "needs_confirmation"
  | "recognized"
  | "missing_info"
  | "suspicious";

type MaterialResultGroup = {
  key: MaterialResultGroupKey;
  title: string;
  description: string;
  tone: "info" | "warning" | "success";
  items: WorkbenchInvoiceItem[];
};

type DraftSummary = {
  recognizedAmountCents: number;
  pendingConfirmationAmountCents: number;
  memberAmountsCents: Map<string, number>;
  missingMaterialCount: number;
  riskItemCount: number;
};

const MATERIAL_TYPE_OPTIONS: Array<{ value: MaterialType; label: string }> = [
  { value: "invoice", label: "发票" },
  { value: "payment_record", label: "支付记录" },
  { value: "competition_notice", label: "比赛通知" },
  { value: "itinerary", label: "行程单" },
  { value: "order_screenshot", label: "订单截图" },
  { value: "other_attachment", label: "其他材料" },
];

const MATERIAL_FILE_ACCEPT = ".pdf,.zip,.jpg,.jpeg,.png,.webp";
const RECENT_UPLOAD_AUTO_REFRESH_INTERVAL_MS = 2000;
const RECENT_UPLOAD_AUTO_REFRESH_MAX_ATTEMPTS = 10;

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

const WORKBENCH_TAB_HASHES: Record<WorkbenchTab, string> = {
  invoices: "#member-workbench-invoices",
  "missing-materials": "#member-workbench-missing-materials",
  confirmations: "#member-workbench-confirmations",
};

const INVOICE_QUEUE_GROUP_METADATA: Record<Exclude<InvoiceQueueGroupKey, "ready">, Omit<InvoiceQueueGroup, "items" | "key">> = {
  recognition_pending: {
    title: "识别中",
    description: "这些材料仍在排队或执行识别，系统还没有形成稳定可提交的发票上下文。",
    tone: "info",
  },
  recognition_review: {
    title: "识别失败或待确认",
    description: "这些材料需要先补录或确认关键字段，否则后续校验、分摊和确认都不稳定。",
    tone: "warning",
  },
  supporting_material_linkage: {
    title: "附件待关联",
    description: "这些发票还有辅助材料没安全归票，附件不完整前不应直接交给管理员。",
    tone: "warning",
  },
  missing_materials: {
    title: "缺失材料",
    description: "系统已经明确指出缺什么材料，先补齐这些内容再进入提交阶段。",
    tone: "warning",
  },
  split_incomplete: {
    title: "分摊未完成",
    description: "这些发票的分摊记录还没闭合，当前金额合计还不能稳定支撑后续确认。",
    tone: "warning",
  },
  confirmation_incomplete: {
    title: "确认未完成",
    description: "这些发票已经形成分摊，但相关成员确认还没全部完成，不能视为真正闭环。",
    tone: "warning",
  },
};

const UPLOAD_PROCESSING_STAGE_LABELS: Record<UploadProcessingStageKey, string> = {
  received: "已接收",
  recognition_pending: "识别排队中",
  recognized: "识别完成",
  linked: "已归票",
  action_required: "需要处理",
};

const MATERIAL_UI_STATUS_LABELS: Record<ReimbursementMaterialUiStatus, string> = {
  uploaded: "正在识别",
  processing: "正在识别",
  recognized: "已自动识别",
  needs_confirmation: "需要你确认",
  missing_info: "缺少信息",
  suspicious: "可能有问题",
  confirmed: "已确认",
  excluded: "不报销",
};

const MATERIAL_RESULT_GROUP_METADATA: Record<MaterialResultGroupKey, Omit<MaterialResultGroup, "items" | "key">> = {
  needs_confirmation: {
    title: "需要你确认",
    description: "这些材料存在系统无法替你决定的事项，请先处理。",
    tone: "warning",
  },
  recognized: {
    title: "已自动识别",
    description: "这些材料已形成报销草稿，默认折叠查看，需要时再修改。",
    tone: "success",
  },
  missing_info: {
    title: "缺少材料",
    description: "这些材料还缺必要凭证或关键信息，补齐后才能提交。",
    tone: "warning",
  },
  suspicious: {
    title: "可能有问题",
    description: "这些材料存在金额、日期、抬头、税号或分摊风险，请核对原因。",
    tone: "warning",
  },
};

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

function pickSelectedTaskId(
  tasks: ReimbursementTask[],
  preferredTaskId: string | null,
  currentTaskId: string,
) {
  const visibleTaskIds = new Set(tasks.map((task) => task.id));
  if (currentTaskId.length > 0 && visibleTaskIds.has(currentTaskId)) {
    return currentTaskId;
  }
  if (preferredTaskId && visibleTaskIds.has(preferredTaskId)) {
    return preferredTaskId;
  }
  return tasks[0]?.id ?? "";
}

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function formatCurrencyFromCents(cents: number) {
  return `￥${(cents / 100).toFixed(2)}`;
}

function formatCurrencyInputFromCents(cents: number) {
  return (cents / 100).toFixed(2);
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

function parseCurrencyInputToCents(value: string) {
  const normalized = value.trim();
  if (!/^\d+(?:\.\d{1,2})?$/.test(normalized)) {
    return null;
  }
  const [integerPart, decimalPart = ""] = normalized.split(".");
  return Number(integerPart) * 100 + Number(`${decimalPart}00`.slice(0, 2));
}

function normalizeSplitNote(note: string) {
  const normalized = note.trim();
  return normalized.length > 0 ? normalized : null;
}

function buildSplitDraftKey(invoiceId: string, suffix: string) {
  return `${invoiceId}:${suffix}`;
}

function pickDefaultSplitMemberId(taskMemberIds: string[], drafts: SplitDraftRow[], fallbackMemberId: string) {
  return taskMemberIds.find((memberId) => drafts.every((draft) => draft.member_id !== memberId)) ?? fallbackMemberId;
}

function buildWorkbenchTaskAnchor(taskId: string, hash: string) {
  return `/member/invoices/workbench?taskId=${encodeURIComponent(taskId)}${hash}`;
}

function resolveWorkbenchTab(hash: string): WorkbenchTab {
  if (hash === WORKBENCH_TAB_HASHES.confirmations) {
    return "confirmations";
  }
  if (hash === WORKBENCH_TAB_HASHES["missing-materials"]) {
    return "missing-materials";
  }
  return "invoices";
}

function buildWorkbenchTabAnchor(taskId: string, tab: WorkbenchTab) {
  return buildWorkbenchTaskAnchor(taskId, WORKBENCH_TAB_HASHES[tab]);
}

function buildInitialUploadFormState(): WorkbenchUploadFormState {
  return {
    files: [],
  };
}

function buildSplitDraftRows(
  item: WorkbenchInvoiceItem,
  defaultMemberId: string,
): SplitDraftRow[] {
  const invoice = item.invoice;
  if (!invoice) {
    return [];
  }
  if (item.splits.length === 0) {
    return [
      {
        key: buildSplitDraftKey(invoice.id, "default"),
        member_id: defaultMemberId,
        amount_yuan: formatCurrencyInputFromCents(invoice.amount_cents),
        note: "",
      },
    ];
  }
  return item.splits.map((split, index) => ({
    key: split.id || buildSplitDraftKey(invoice.id, `existing-${index}`),
    member_id: split.member_id,
    amount_yuan: formatCurrencyInputFromCents(split.amount_cents),
    note: split.note ?? "",
  }));
}

function buildInitialSplitDrafts(
  items: WorkbenchInvoiceItem[],
  defaultMemberId: string,
) {
  return Object.fromEntries(
    items
      .filter((item) => item.invoice !== null)
      .map((item) => [item.invoice!.id, buildSplitDraftRows(item, defaultMemberId)] as const),
  );
}

function haveSplitDraftsChanged(
  item: WorkbenchInvoiceItem,
  drafts: SplitDraftRow[],
  defaultMemberId: string,
) {
  const baseline = buildSplitDraftRows(item, defaultMemberId);
  if (drafts.length !== baseline.length) {
    return true;
  }
  return drafts.some((draft, index) => {
    const previous = baseline[index];
    if (!previous) {
      return true;
    }
    return (
      draft.member_id !== previous.member_id
      || draft.amount_yuan !== previous.amount_yuan
      || normalizeSplitNote(draft.note) !== normalizeSplitNote(previous.note)
    );
  });
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

function formatFieldValue(
  fieldName: (typeof FIELD_ORDER)[number],
  value: unknown,
) {
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

function getInvoiceFieldValue(
  invoice: InvoiceRecord | null,
  fieldName: (typeof FIELD_ORDER)[number],
) {
  if (!invoice) {
    return null;
  }
  return invoice[fieldName];
}

function getRecognitionFieldValue(
  recognition: WorkbenchRecognition | null,
  fieldName: (typeof FIELD_ORDER)[number],
) {
  return recognition?.recognized_fields[fieldName] ?? null;
}

function getRecognitionFieldTextValue(
  recognition: WorkbenchRecognition | null,
  fieldName: (typeof FIELD_ORDER)[number],
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

function getRecognitionAmountInput(recognition: WorkbenchRecognition | null) {
  const field = getRecognitionFieldValue(recognition, "amount_cents");
  if (!field || typeof field.value !== "number") {
    return "";
  }
  return formatCurrencyInputFromCents(field.value);
}

function getRecognitionExpenseType(
  recognition: WorkbenchRecognition | null,
  allowedExpenseTypes: ExpenseType[],
) {
  const rawValue = getRecognitionFieldTextValue(recognition, "expense_type");
  if (isExpenseType(rawValue) && allowedExpenseTypes.includes(rawValue)) {
    return rawValue;
  }
  return allowedExpenseTypes[0] ?? "other";
}

function renderRecognitionSource(field: RecognitionFieldResult | null) {
  if (!field) {
    return "暂无识别值";
  }
  if (field.source === "manual") {
    return "人工填写";
  }
  return "系统识别";
}

function getRecognitionStatus(item: WorkbenchInvoiceItem): RecognitionTaskStatus | null {
  return item.recognition?.status ?? item.material.recognition_status ?? null;
}

function getRecognitionFailure(item: WorkbenchInvoiceItem): RecognitionFailureDetail | null {
  if (item.recognition?.failure) {
    return item.recognition.failure;
  }
  if (item.material.recognition_failure_stage && item.material.recognition_failure_reason) {
    return {
      stage: item.material.recognition_failure_stage,
      reason: item.material.recognition_failure_reason,
    };
  }
  return null;
}

function summarizePendingActions(task: ReimbursementTask, report: TaskMemberStatusReport): PendingAction[] {
  const actions: PendingAction[] = [];

  if (report.counts.recognition_pending_count > 0) {
    actions.push({
      id: "recognition-pending",
      title: "等待系统完成识别",
      detail: `当前有 ${report.counts.recognition_pending_count} 份材料仍在识别排队或尚未执行；在结果出来前，分摊与确认不会自然闭合。`,
      to: buildWorkbenchTaskAnchor(task.id, "#member-workbench-invoices"),
      tone: "info",
      label: "查看当前状态",
    });
  }

  if (report.counts.recognition_failed_count > 0 || report.counts.recognition_needs_confirmation_count > 0) {
    actions.push({
      id: "recognition",
      title: "先核对识别结果",
      detail: `当前有 ${report.counts.recognition_failed_count + report.counts.recognition_needs_confirmation_count} 份材料仍需人工确认或补录。`,
      to: buildWorkbenchTaskAnchor(task.id, "#member-workbench-invoices"),
      tone: "warning",
      label: "定位到对应发票",
    });
  }

  if (report.counts.missing_material_count > 0) {
    actions.push({
      id: "missing-materials",
      title: "补齐必传材料",
      detail: `当前有 ${report.counts.missing_material_count} 条缺失材料提示，会影响后续复核。`,
      to: buildWorkbenchTaskAnchor(task.id, "#member-workbench-upload"),
      tone: "danger",
      label: "去上传区补材料",
    });
  }

  if (report.counts.validation_failed_count > 0 || report.counts.validation_pending_count > 0) {
    actions.push({
      id: "validations",
      title: "处理异常校验",
      detail: `当前有 ${report.counts.validation_failed_count} 条失败校验、${report.counts.validation_pending_count} 条待确认校验。`,
      to: buildWorkbenchTaskAnchor(task.id, "#member-workbench-invoices"),
      tone: "warning",
      label: "查看异常原因",
    });
  }

  if (report.counts.pending_confirmation_count > 0 || report.counts.missing_confirmation_count > 0) {
    actions.push({
      id: "confirmations",
      title: "确认本人费用",
      detail: `当前有 ${report.counts.pending_confirmation_count + report.counts.missing_confirmation_count} 条费用还未完成确认。`,
      to: buildWorkbenchTaskAnchor(task.id, "#member-workbench-confirmations"),
      tone: "info",
      label: "去确认区处理",
    });
  }

  if (actions.length === 0) {
    actions.push({
      id: "done",
      title: "当前任务已无明显待处理项",
      detail: "可以继续回看发票记录，或等待管理员进入下一阶段处理。",
      to: buildWorkbenchTaskAnchor(task.id, "#member-workbench-invoices"),
      tone: "info",
      label: "回看当前发票",
    });
  }

  return actions;
}

function summarizePendingActionsWithLinkage(
  task: ReimbursementTask,
  report: TaskMemberStatusReport,
  pendingSupportingMaterialLinkageItems: PendingSupportingMaterialLinkageItem[],
) {
  const actions = summarizePendingActions(task, report);
  if (pendingSupportingMaterialLinkageItems.length > 0) {
    actions.unshift({
      id: "supporting-material-linkage",
      title: "处理待关联辅助材料",
      detail: `当前有 ${pendingSupportingMaterialLinkageItems.length} 份辅助材料还没归到发票；这些材料不会自动算作已补齐附件。`,
      to: buildWorkbenchTaskAnchor(task.id, "#member-workbench-pending-linkage"),
      tone: "warning",
      label: "查看待关联列表",
    });
  }
  return actions;
}

function collectAbnormalReasons(item: WorkbenchInvoiceItem) {
  const reasons: string[] = [];
  const recognitionStatus = getRecognitionStatus(item);
  const recognitionFailure = getRecognitionFailure(item);

  if (recognitionStatus === "pending") {
    reasons.push("系统正在处理该材料识别；识别完成前，暂时还不能生成完整发票字段、分摊与确认上下文。");
  }
  if (recognitionStatus === "failed") {
    reasons.push(describeRecognitionFailure(recognitionFailure));
  }
  if (recognitionStatus === "needs_confirmation") {
    reasons.push("识别结果里仍有待确认字段，请优先核对关键发票信息。");
  }
  for (const validation of item.validations) {
    if (validation.status === "failed" || validation.status === "pending") {
      reasons.push(`${formatValidationRule(validation.rule_code)}：${validation.message}`);
    }
  }
  for (const missingMaterial of item.missingMaterials) {
    reasons.push(`${formatMaterialType(missingMaterial.required_material_type)}：${missingMaterial.message}`);
  }
  for (const confirmation of item.confirmations) {
    if (confirmation.status === "disputed" && confirmation.dispute_reason) {
      reasons.push(`${formatMemberLabel(confirmation.member_id)}提出异议：${confirmation.dispute_reason}`);
    }
  }

  return reasons;
}

function mapWorkbenchSummaryItem(item: TaskMemberWorkbenchSummaryItem): WorkbenchInvoiceItem {
  return {
    material: item.material,
    invoice: item.invoice,
    recognition: item.recognition,
    validations: item.validations,
    supportingMaterials: item.supporting_materials,
    splits: item.splits,
    confirmations: item.confirmations,
    relatedExpenseDetails: item.related_expense_details,
    missingMaterials: item.missing_materials,
    queueGroup: item.queue_group,
    blockingReasons: item.blocking_reasons,
    readyForSubmission: item.ready_for_submission,
  };
}

function buildWorkbenchItems(
  report: TaskMemberStatusReport,
  invoices: InvoiceRecord[],
  recognitionsByMaterialId: Map<string, WorkbenchRecognition | null>,
  validationsByInvoiceId: Map<string, ValidationResult[]>,
  supportingMaterialsByInvoiceId: Map<string, MaterialRecord[]>,
  splitsByInvoiceId: Map<string, ExpenseSplitRecord[]>,
  confirmationsByInvoiceId: Map<string, ConfirmationRecord[]>,
) {
  const invoicesByMaterialId = new Map(invoices.map((invoice) => [invoice.material_id, invoice] as const));

  return [...report.materials]
    .sort((left, right) => right.created_at.localeCompare(left.created_at))
    .map((material) => {
      const invoice = invoicesByMaterialId.get(material.material_id) ?? null;
      return {
        material,
        invoice,
        recognition: recognitionsByMaterialId.get(material.material_id) ?? null,
        validations: invoice ? (validationsByInvoiceId.get(invoice.id) ?? []) : [],
        supportingMaterials: invoice ? (supportingMaterialsByInvoiceId.get(invoice.id) ?? []) : [],
        splits: invoice ? (splitsByInvoiceId.get(invoice.id) ?? []) : [],
        confirmations: invoice ? (confirmationsByInvoiceId.get(invoice.id) ?? []) : [],
        relatedExpenseDetails: report.expense_details.filter(
          (detail) => detail.invoice.material_id === material.material_id,
        ),
        missingMaterials: invoice
          ? report.missing_materials.filter((entry) => entry.invoice_id === invoice.id)
          : [],
        queueGroup: undefined,
        blockingReasons: undefined,
        readyForSubmission: undefined,
      };
    });
}

function buildSummaryStats(task: ReimbursementTask, report: TaskMemberStatusReport) {
  return [
    {
      label: "本人材料",
      value: report.counts.material_count,
      description: `当前任务状态：${formatTaskStatus(task.status)}。`,
    },
    {
      label: "待处理事项",
      value: (
        report.counts.recognition_pending_count
        + report.counts.recognition_failed_count
        + report.counts.recognition_needs_confirmation_count
        + report.counts.validation_failed_count
        + report.counts.validation_pending_count
        + report.counts.missing_material_count
        + report.counts.pending_confirmation_count
        + report.counts.missing_confirmation_count
      ),
      description: "包括识别排队、人工确认、校验异常、缺失材料和待确认费用。",
    },
    {
      label: "本人费用",
      value: formatCurrencyFromCents(report.total_expense_amount_cents),
      description: "来自当前任务下与你相关的分摊金额。",
    },
    {
      label: "确认进度",
      value: `${report.counts.confirmed_expense_count}/${report.counts.expense_detail_count}`,
      description: "已确认条数 / 当前与你相关的费用条数。",
    },
  ];
}

function buildConfirmationItems(items: WorkbenchInvoiceItem[]) {
  return items.flatMap((item) =>
    item.relatedExpenseDetails.map((detail) => ({
      detail,
      supportingMaterials: item.supportingMaterials,
    })),
  );
}

function formatSupportingMaterialSummary(item: TaskSharedInvoiceItem) {
  if (item.supporting_materials.length === 0) {
    return "当前还没有已关联的必要附件摘要。";
  }
  return item.supporting_materials
    .map((material) => `${formatMaterialType(material.material_type)} ${material.count} 份`)
    .join(" / ");
}

function formatPendingSupportingMaterialLinkageReason(
  reason: PendingSupportingMaterialLinkageItem["pending_reason"],
) {
  if (reason === "no_candidate") {
    return "当前没有可安全匹配的候选发票";
  }
  return "当前存在多张候选发票，系统不会自动绑定";
}

function formatInvoiceMemberSubmissionStatus(status: InvoiceMemberSubmissionStatus) {
  return status === "submitted" ? "已提交管理员" : "未提交管理员";
}

function formatTaskDateRange(task: ReimbursementTask) {
  if (task.competition_start_date === task.competition_end_date) {
    return task.competition_start_date;
  }
  return `${task.competition_start_date} 至 ${task.competition_end_date}`;
}

function getMaterialUiStatus(item: WorkbenchInvoiceItem): ReimbursementMaterialUiStatus {
  const recognitionStatus = getRecognitionStatus(item);
  if (recognitionStatus === "pending") {
    return "processing";
  }
  if (recognitionStatus === "failed" || recognitionStatus === "needs_confirmation" || !item.invoice) {
    return "needs_confirmation";
  }
  if (item.missingMaterials.length > 0) {
    return "missing_info";
  }
  if (item.validations.some((validation) => validation.status === "failed" || validation.status === "pending")) {
    return "suspicious";
  }
  if (item.invoice.member_submission_status === "submitted") {
    return "confirmed";
  }
  return "recognized";
}

function getMaterialUiTone(status: ReimbursementMaterialUiStatus) {
  if (status === "recognized" || status === "confirmed") {
    return "success" as const;
  }
  if (status === "uploaded" || status === "processing") {
    return "info" as const;
  }
  if (status === "excluded") {
    return "neutral" as const;
  }
  return "warning" as const;
}

function getMaterialResultGroupKey(item: WorkbenchInvoiceItem): MaterialResultGroupKey {
  const status = getMaterialUiStatus(item);
  if (status === "missing_info") {
    return "missing_info";
  }
  if (status === "suspicious") {
    return "suspicious";
  }
  if (status === "recognized" || status === "confirmed") {
    return "recognized";
  }
  return "needs_confirmation";
}

function buildMaterialResultGroups(items: WorkbenchInvoiceItem[]) {
  const groups = new Map<MaterialResultGroupKey, WorkbenchInvoiceItem[]>();
  (Object.keys(MATERIAL_RESULT_GROUP_METADATA) as MaterialResultGroupKey[]).forEach((key) => {
    groups.set(key, []);
  });

  items.forEach((item) => {
    groups.get(getMaterialResultGroupKey(item))?.push(item);
  });

  return (Object.entries(MATERIAL_RESULT_GROUP_METADATA) as Array<
    [MaterialResultGroupKey, Omit<MaterialResultGroup, "items" | "key">]
  >)
    .map(([key, metadata]) => ({
      key,
      ...metadata,
      items: groups.get(key) ?? [],
    }));
}

function buildDraftSummary(items: WorkbenchInvoiceItem[], report: TaskMemberStatusReport): DraftSummary {
  const memberAmountsCents = new Map<string, number>();
  for (const item of items) {
    for (const split of item.splits) {
      memberAmountsCents.set(
        split.member_id,
        (memberAmountsCents.get(split.member_id) ?? 0) + split.amount_cents,
      );
    }
  }

  return {
    recognizedAmountCents: items.reduce((sum, item) => sum + (item.invoice?.amount_cents ?? 0), 0),
    pendingConfirmationAmountCents: items.reduce((sum, item) => {
      const status = getMaterialUiStatus(item);
      return status === "needs_confirmation" || status === "missing_info" || status === "suspicious"
        ? sum + (item.invoice?.amount_cents ?? 0)
        : sum;
    }, 0),
    memberAmountsCents,
    missingMaterialCount: report.counts.missing_material_count,
    riskItemCount: items.filter((item) => getMaterialUiStatus(item) === "suspicious").length,
  };
}

function buildSubmitBlockers(
  task: ReimbursementTask,
  pendingActionCount: number,
  problemInvoiceCount: number,
  pendingSupportingMaterialLinkageItems: PendingSupportingMaterialLinkageItem[],
  confirmationItems: WorkbenchConfirmationItem[],
) {
  const blockers: string[] = [];
  if (task.status !== "open") {
    blockers.push(`当前任务为${formatTaskStatus(task.status)}，暂不能提交新的确认。`);
  }
  if (pendingActionCount > 0) {
    blockers.push(`还有 ${pendingActionCount} 项需要处理。`);
  }
  if (problemInvoiceCount > 0) {
    blockers.push(`还有 ${problemInvoiceCount} 份材料存在待确认、缺少信息或风险提示。`);
  }
  if (pendingSupportingMaterialLinkageItems.length > 0) {
    blockers.push(`还有 ${pendingSupportingMaterialLinkageItems.length} 份辅助材料需要指定归属。`);
  }
  const pendingConfirmations = confirmationItems.filter((item) => getCurrentConfirmationStatus(item.detail) === "pending").length;
  if (pendingConfirmations > 0) {
    blockers.push(`还有 ${pendingConfirmations} 笔分到你名下的费用需要确认。`);
  }
  return blockers;
}

function formatInvoiceBatchActionLabel(action: InvoiceBatchAction) {
  return action === "submit" ? "批量提交" : "批量撤回";
}

function describeWorkbenchInvoice(item: WorkbenchInvoiceItem) {
  return item.invoice?.invoice_number ?? item.material.original_filename;
}

function buildInvoiceBatchFeedbackMessage(feedback: InvoiceBatchActionFeedback) {
  const succeededCount = feedback.items.length;
  const failedCount = feedback.failures.length;
  const actionLabel = formatInvoiceBatchActionLabel(feedback.action);
  if (feedback.status === "success") {
    return `${actionLabel}成功：共处理 ${succeededCount} 张发票。`;
  }
  if (feedback.status === "partial_success") {
    return `${actionLabel}部分成功：已处理 ${succeededCount} 张，另有 ${failedCount} 张失败。`;
  }
  return `${actionLabel}失败：选中的 ${failedCount} 张发票都没有处理成功。`;
}

function buildInvoiceBatchFailureMessage(
  failure: InvoiceMemberSubmissionBatchFailure,
  items: WorkbenchInvoiceItem[],
) {
  const matchedItem = items.find((item) => item.invoice?.id === failure.invoice_id);
  const invoiceLabel = matchedItem ? describeWorkbenchInvoice(matchedItem) : failure.invoice_id;
  return `${invoiceLabel}：${failure.detail}`;
}

function formatRecognitionDispatchMessage(dispatch: MaterialBatchUploadResponse["recognition_dispatch"]) {
  if (!dispatch) {
    return null;
  }
  if (dispatch.status === "queued") {
    return "材料已接收，正在排队识别；识别完成后会自动刷新识别结果。";
  }
  return "材料已接收，系统正在整理识别结果和待处理事项。";
}

function buildAllowedExpenseTypes(task: ReimbursementTask): ExpenseType[] {
  const taskExpenseTypes = task.fee_categories.filter(isExpenseType);
  return taskExpenseTypes.length > 0 ? taskExpenseTypes : ["other"];
}

function buildManualInvoiceFormState(
  item: WorkbenchInvoiceItem,
  allowedExpenseTypes: ExpenseType[],
): ManualInvoiceFormState {
  return {
    invoiceNumber: item.invoice?.invoice_number ?? getRecognitionFieldTextValue(item.recognition, "invoice_number"),
    issueDate: item.invoice?.issue_date ?? getRecognitionFieldTextValue(item.recognition, "issue_date"),
    transactionTime: item.invoice?.transaction_time
      ? formatDateTimeLocalInput(item.invoice.transaction_time)
      : formatDateTimeLocalInput(getRecognitionFieldTextValue(item.recognition, "transaction_time")),
    buyerName: item.invoice?.buyer_name ?? getRecognitionFieldTextValue(item.recognition, "buyer_name"),
    taxNumber: item.invoice?.tax_number ?? getRecognitionFieldTextValue(item.recognition, "tax_number"),
    sellerName: item.invoice?.seller_name ?? getRecognitionFieldTextValue(item.recognition, "seller_name"),
    amountYuan: item.invoice ? formatCurrencyInputFromCents(item.invoice.amount_cents) : getRecognitionAmountInput(item.recognition),
    expenseType: item.invoice?.expense_type ?? getRecognitionExpenseType(item.recognition, allowedExpenseTypes),
  };
}

function validateManualInvoiceForm(
  formState: ManualInvoiceFormState,
  allowedExpenseTypes: ExpenseType[],
) {
  const errors: ManualInvoiceFormErrors = {};
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
  if (parseCurrencyInputToCents(formState.amountYuan) === null) {
    errors.amountYuan = "请输入大于 0 的金额，单位为元。";
  }
  return errors;
}

function validateWorkbenchUploadForm(
  task: ReimbursementTask | null,
  formState: WorkbenchUploadFormState,
) {
  const errors: WorkbenchUploadValidationErrors = {};

  if (!task || task.status !== "open") {
    errors.files = "当前任务不在开放提交阶段，成员不能直接补交材料。";
  }
  if (formState.files.length === 0) {
    errors.files = "至少选择一个要上传的文件。";
  } else {
    const oversizedFile = findOversizedFile(formState.files);
    if (oversizedFile) {
      errors.files = `文件 ${oversizedFile.name} 超过 ${Math.floor(MAX_UPLOAD_FILE_BYTES / 1024 / 1024)}MB，请压缩或拆分后再上传。`;
    }
  }

  return errors;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isUploadFailureList(value: unknown): value is Array<{
  original_filename: string | null;
  error_code: string;
  detail: string;
}> {
  return Array.isArray(value) && value.every((item) => {
    if (!isRecord(item)) {
      return false;
    }
    return (
      (item.original_filename === null || typeof item.original_filename === "string")
      && typeof item.error_code === "string"
      && typeof item.detail === "string"
    );
  });
}

function isMaterialRecord(value: unknown): value is MaterialRecord {
  if (!isRecord(value)) {
    return false;
  }
  return (
    typeof value.id === "string"
    && typeof value.original_filename === "string"
    && typeof value.material_type === "string"
    && typeof value.channel === "string"
  );
}

function extractFailedBatchUploadResponse(error: unknown): MaterialBatchUploadResponse | null {
  if (!(error instanceof ApiError) || !isRecord(error.payload)) {
    return null;
  }

  const payload = error.payload;
  if (payload.status !== "failed" || !Array.isArray(payload.items) || !isUploadFailureList(payload.failures)) {
    return null;
  }

  if (!payload.items.every(isMaterialRecord)) {
    return null;
  }

  return {
    status: "failed",
    items: payload.items,
    failures: payload.failures,
  };
}

function getCurrentConfirmationStatus(detail: ExpenseDetailItem): ConfirmationStatus {
  return detail.confirmation?.status ?? "pending";
}

function isSplitStaleError(error: unknown) {
  return error instanceof ApiError && error.status === 404 && error.message === "split not found";
}

function buildInvoiceWorkbenchSelectionKey(selection: InvoiceWorkbenchSelection) {
  return selection.kind === "own"
    ? `own:${selection.materialId}`
    : `shared:${selection.invoiceId}`;
}

function buildPendingSupportingMaterialLinkageActionKey(action: PendingSupportingMaterialLinkageAction) {
  return `${action.materialId}:${action.invoiceId}`;
}

function findPendingSupportingMaterialLinkageMatches(
  invoiceId: string,
  pendingSupportingMaterialLinkageItems: PendingSupportingMaterialLinkageItem[],
) {
  return pendingSupportingMaterialLinkageItems.filter((item) => (
    item.candidate_invoices.some((candidate) => candidate.invoice_id === invoiceId)
  ));
}

function isRecognitionProviderNotConfiguredFailure(
  failure: RecognitionFailureDetail | null,
) {
  if (!failure || failure.stage !== "ai") {
    return false;
  }
  return (
    failure.reason === "llm_provider_not_configured"
    || failure.reason === "text_llm_provider_not_configured"
    || failure.reason === "vlm_provider_not_configured"
    || failure.reason === "structured_recognition_not_configured"
  );
}

function hasSplitCoverageGap(item: WorkbenchInvoiceItem) {
  if (!item.invoice) {
    return false;
  }
  if (item.splits.length === 0) {
    return false;
  }
  const totalSplitAmountCents = item.splits.reduce((sum, split) => sum + split.amount_cents, 0);
  return totalSplitAmountCents !== item.invoice.amount_cents;
}

function hasConfirmationGap(item: WorkbenchInvoiceItem) {
  if (!item.invoice || item.splits.length === 0) {
    return false;
  }
  const currentConfirmationsBySplitId = new Map(
    item.confirmations
      .filter((confirmation) => confirmation.is_current)
      .map((confirmation) => [confirmation.split_id, confirmation] as const),
  );
  return item.splits.some((split) => {
    const confirmation = currentConfirmationsBySplitId.get(split.id);
    return !confirmation || confirmation.status !== "confirmed";
  });
}

function buildInvoiceQueueStatusSummary(
  item: WorkbenchInvoiceItem,
  pendingSupportingMaterialLinkageItems: PendingSupportingMaterialLinkageItem[],
) {
  const messages: string[] = [];
  const recognitionStatus = getRecognitionStatus(item);
  const pendingLinkageMatches = item.invoice
    ? findPendingSupportingMaterialLinkageMatches(item.invoice.id, pendingSupportingMaterialLinkageItems)
    : [];

  if (recognitionStatus === "pending") {
    messages.push("系统仍在识别这份材料，当前先不要把它当成稳定发票。");
  }
  if (recognitionStatus === "failed") {
    messages.push("识别失败，请先补录关键字段或重新触发识别。");
  }
  if (recognitionStatus === "needs_confirmation") {
    messages.push("识别结果仍有待确认字段，请先核对关键发票信息。");
  }
  if (!item.invoice) {
    messages.push("系统还没有形成可提交发票，请先补录或更正发票字段。");
  }
  if (pendingLinkageMatches.length > 0) {
    messages.push(`还有 ${pendingLinkageMatches.length} 份辅助材料待关联到这张发票。`);
  }
  if (item.missingMaterials.length > 0) {
    messages.push(`当前仍缺少 ${item.missingMaterials.length} 类必传材料。`);
  }
  if (hasSplitCoverageGap(item)) {
    messages.push("分摊记录还没有闭合到发票总额。");
  }
  if (hasConfirmationGap(item)) {
    messages.push("相关成员费用确认还没有全部完成。");
  }

  return [...new Set(messages)];
}

function deriveInvoiceQueueGroupKey(
  item: WorkbenchInvoiceItem,
  pendingSupportingMaterialLinkageItems: PendingSupportingMaterialLinkageItem[],
): InvoiceQueueGroupKey {
  if (item.queueGroup) {
    return item.queueGroup;
  }
  const recognitionStatus = getRecognitionStatus(item);
  if (recognitionStatus === "pending") {
    return "recognition_pending";
  }
  if (recognitionStatus === "failed" || recognitionStatus === "needs_confirmation" || !item.invoice) {
    return "recognition_review";
  }
  if (findPendingSupportingMaterialLinkageMatches(item.invoice.id, pendingSupportingMaterialLinkageItems).length > 0) {
    return "supporting_material_linkage";
  }
  if (item.missingMaterials.length > 0) {
    return "missing_materials";
  }
  if (hasSplitCoverageGap(item)) {
    return "split_incomplete";
  }
  if (hasConfirmationGap(item)) {
    return "confirmation_incomplete";
  }
  return "ready";
}

function buildInvoiceQueueGroups(
  items: WorkbenchInvoiceItem[],
  pendingSupportingMaterialLinkageItems: PendingSupportingMaterialLinkageItem[],
) {
  const readyItems: WorkbenchInvoiceItem[] = items.filter((item) => item.readyForSubmission ?? false);
  const problemGroups = new Map<Exclude<InvoiceQueueGroupKey, "ready">, WorkbenchInvoiceItem[]>();

  (Object.keys(INVOICE_QUEUE_GROUP_METADATA) as Array<Exclude<InvoiceQueueGroupKey, "ready">>).forEach((key) => {
    problemGroups.set(key, []);
  });

  items.forEach((item) => {
    const groupKey = deriveInvoiceQueueGroupKey(item, pendingSupportingMaterialLinkageItems);
    if (groupKey === "ready") {
      if (!readyItems.includes(item)) {
        readyItems.push(item);
      }
      return;
    }
    problemGroups.get(groupKey)?.push(item);
  });

  return {
    readyItems,
    problemSections: (Object.entries(INVOICE_QUEUE_GROUP_METADATA) as Array<
      [Exclude<InvoiceQueueGroupKey, "ready">, Omit<InvoiceQueueGroup, "items" | "key">]
    >)
      .map(([key, metadata]) => ({
        key,
        ...metadata,
        items: problemGroups.get(key) ?? [],
      }))
      .filter((section) => section.items.length > 0),
  };
}

function parseInvoiceWorkbenchAnchorTarget(hash: string) {
  const prefix = "#workbench-invoice-";
  if (!hash.startsWith(prefix)) {
    return null;
  }
  return decodeURIComponent(hash.slice(prefix.length));
}

function pickInvoiceWorkbenchSelection(
  items: WorkbenchInvoiceItem[],
  sharedInvoices: TaskSharedInvoiceItem[],
  anchorTarget: string | null,
  currentSelectionKey: string | null,
): InvoiceWorkbenchSelection | null {
  if (anchorTarget) {
    const ownMatch = items.find((item) => item.invoice?.id === anchorTarget || item.material.material_id === anchorTarget);
    if (ownMatch) {
      return {
        kind: "own",
        materialId: ownMatch.material.material_id,
      };
    }
    const sharedMatch = sharedInvoices.find((item) => item.invoice_id === anchorTarget);
    if (sharedMatch) {
      return {
        kind: "shared",
        invoiceId: sharedMatch.invoice_id,
      };
    }
  }

  if (currentSelectionKey) {
    if (currentSelectionKey.startsWith("own:")) {
      const materialId = currentSelectionKey.slice("own:".length);
      if (items.some((item) => item.material.material_id === materialId)) {
        return {
          kind: "own",
          materialId,
        };
      }
    }
    if (currentSelectionKey.startsWith("shared:")) {
      const invoiceId = currentSelectionKey.slice("shared:".length);
      if (sharedInvoices.some((item) => item.invoice_id === invoiceId)) {
        return {
          kind: "shared",
          invoiceId,
        };
      }
    }
  }

  const firstOwnItem = items[0];
  if (firstOwnItem) {
    return {
      kind: "own",
      materialId: firstOwnItem.material.material_id,
    };
  }

  const firstSharedInvoice = sharedInvoices[0];
  if (firstSharedInvoice) {
    return {
      kind: "shared",
      invoiceId: firstSharedInvoice.invoice_id,
    };
  }

  return null;
}

function findWorkbenchItemBySupportingMaterialId(
  materialId: string,
  items: WorkbenchInvoiceItem[],
) {
  return items.find((item) => item.supportingMaterials.some((material) => material.id === materialId)) ?? null;
}

function buildUploadProcessingSnapshot(
  uploadedItem: MaterialBatchUploadResponse["items"][number],
  taskId: string,
  workbenchState: SelectedTaskWorkbenchState,
  recognitionDispatch: MaterialBatchUploadResponse["recognition_dispatch"],
): UploadProcessingSnapshot {
  const fallbackRecognitionStatus = uploadedItem.recognition_status ?? null;
  if (workbenchState.status !== "ready" || workbenchState.task.id !== taskId) {
    if (fallbackRecognitionStatus === "pending") {
      return {
        stage: "recognition_pending",
        tone: "info",
        label: UPLOAD_PROCESSING_STAGE_LABELS.recognition_pending,
        detail: recognitionDispatch?.status === "queued"
          ? "材料已接收，正在排队识别；页面会继续自动刷新。"
          : "材料已接收，系统正在刷新识别状态。",
        steps: ["received", "recognition_pending"],
        transitioning: true,
        actionLabel: null,
        actionHref: null,
      };
    }
    return {
      stage: "received",
      tone: "info",
      label: UPLOAD_PROCESSING_STAGE_LABELS.received,
      detail: "材料已接收，工作台正在同步这份材料的识别、归票和待办状态。",
      steps: ["received"],
      transitioning: true,
      actionLabel: null,
      actionHref: null,
    };
  }

  const directWorkbenchItem = workbenchState.items.find(
    (item) => item.material.material_id === uploadedItem.id,
  ) ?? null;
  const linkedWorkbenchItem = findWorkbenchItemBySupportingMaterialId(uploadedItem.id, workbenchState.items);
  const pendingLinkageItem = workbenchState.pendingSupportingMaterialLinkageItems.find(
    (item) => item.material_id === uploadedItem.id,
  ) ?? null;
  const recognitionStatus = directWorkbenchItem
    ? (getRecognitionStatus(directWorkbenchItem) ?? fallbackRecognitionStatus)
    : fallbackRecognitionStatus;
  const recognitionFailure = directWorkbenchItem ? getRecognitionFailure(directWorkbenchItem) : null;
  const linkedInvoice = directWorkbenchItem?.invoice ?? linkedWorkbenchItem?.invoice ?? null;
  const queueGroup = directWorkbenchItem?.queueGroup;

  if (recognitionStatus === "pending") {
    return {
      stage: "recognition_pending",
      tone: "info",
      label: UPLOAD_PROCESSING_STAGE_LABELS.recognition_pending,
      detail: recognitionDispatch?.status === "queued"
        ? "材料已进入识别队列；系统会继续刷新下面的待处理事项。"
        : "系统正在识别这份材料，识别完成后会继续刷新归票和待办结果。",
      steps: ["received", "recognition_pending"],
      transitioning: true,
      actionLabel: null,
      actionHref: null,
    };
  }

  if (recognitionStatus === "failed") {
    return {
      stage: "action_required",
      tone: isRecognitionProviderNotConfiguredFailure(recognitionFailure) ? "warning" : "danger",
      label: UPLOAD_PROCESSING_STAGE_LABELS.action_required,
      detail: isRecognitionProviderNotConfiguredFailure(recognitionFailure)
        ? "当前环境未配置识别服务；请联系管理员配置自动识别服务，或直接在下面手动补录发票字段。"
        : describeRecognitionFailure(recognitionFailure),
      steps: ["received", "action_required"],
      transitioning: false,
      actionLabel: "去工作台处理",
      actionHref: buildWorkbenchTaskAnchor(taskId, "#member-workbench-invoices"),
    };
  }

  if (recognitionStatus === "needs_confirmation") {
    return {
      stage: "action_required",
      tone: "warning",
      label: UPLOAD_PROCESSING_STAGE_LABELS.action_required,
      detail: "识别结果已经生成，但仍有关键字段待确认；系统已把相关待办刷新到下面发票区。",
      steps: ["received", "recognized", "action_required"],
      transitioning: false,
      actionLabel: "去核对字段",
      actionHref: buildWorkbenchTaskAnchor(taskId, "#member-workbench-invoices"),
    };
  }

  if (pendingLinkageItem) {
    return {
      stage: "action_required",
      tone: "warning",
      label: UPLOAD_PROCESSING_STAGE_LABELS.action_required,
      detail: pendingLinkageItem.pending_reason === "multiple_candidates"
        ? "系统已经识别出这份辅助材料，但存在多张候选发票，需要你在下面选择归属发票。"
        : "系统已经识别出这份辅助材料，但当前还没有安全候选发票；请先补传或补录发票。",
      steps: ["received", "recognized", "action_required"],
      transitioning: false,
      actionLabel: pendingLinkageItem.pending_reason === "multiple_candidates"
        ? "去选择候选发票"
        : "去上传区补发票",
      actionHref: buildWorkbenchTaskAnchor(
        taskId,
        pendingLinkageItem.pending_reason === "multiple_candidates"
          ? "#member-workbench-pending-linkage"
          : "#member-workbench-upload",
      ),
    };
  }

  if (directWorkbenchItem && queueGroup && queueGroup !== "ready") {
    if (queueGroup === "missing_materials") {
      return {
        stage: "action_required",
        tone: "warning",
        label: UPLOAD_PROCESSING_STAGE_LABELS.action_required,
        detail: "系统已经识别并生成发票，但当前还缺少必传附件；待处理事项已刷新到下面列表。",
        steps: ["received", "recognized", "linked", "action_required"],
        transitioning: false,
        actionLabel: "去上传区补材料",
        actionHref: buildWorkbenchTaskAnchor(taskId, "#member-workbench-upload"),
      };
    }
    if (queueGroup === "split_incomplete") {
      return {
        stage: "action_required",
        tone: "warning",
        label: UPLOAD_PROCESSING_STAGE_LABELS.action_required,
        detail: "系统已经识别并形成发票，但分摊金额还没有闭合；请在下面继续处理分摊。",
        steps: ["received", "recognized", "linked", "action_required"],
        transitioning: false,
        actionLabel: "去处理分摊",
        actionHref: buildWorkbenchTaskAnchor(taskId, "#member-workbench-invoices"),
      };
    }
    if (queueGroup === "confirmation_incomplete") {
      return {
        stage: "action_required",
        tone: "warning",
        label: UPLOAD_PROCESSING_STAGE_LABELS.action_required,
        detail: "系统已经识别并形成发票，但相关费用确认还没有完成；确认区已同步刷新。",
        steps: ["received", "recognized", "linked", "action_required"],
        transitioning: false,
        actionLabel: "去确认区处理",
        actionHref: buildWorkbenchTaskAnchor(taskId, "#member-workbench-confirmations"),
      };
    }
  }

  if (linkedInvoice) {
    return {
      stage: "linked",
      tone: "success",
      label: UPLOAD_PROCESSING_STAGE_LABELS.linked,
      detail: directWorkbenchItem?.invoice
        ? "系统已形成对应发票并把待办同步到当前工作台，可继续查看是否已进入可提交队列。"
        : `系统已把这份辅助材料归到发票 ${linkedInvoice.invoice_number}。`,
      steps: ["received", "recognized", "linked"],
      transitioning: false,
      actionLabel: "查看当前发票",
      actionHref: buildWorkbenchTaskAnchor(taskId, "#member-workbench-invoices"),
    };
  }

  if (recognitionStatus === "succeeded") {
    return {
      stage: "recognized",
      tone: "success",
      label: UPLOAD_PROCESSING_STAGE_LABELS.recognized,
      detail: "识别已经完成，系统正在把归票结果和待处理事项收口到当前工作台。",
      steps: ["received", "recognized"],
      transitioning: true,
      actionLabel: null,
      actionHref: null,
    };
  }

  return {
    stage: "received",
    tone: "info",
    label: UPLOAD_PROCESSING_STAGE_LABELS.received,
    detail: "材料已接收，系统正在合并最新状态。",
    steps: ["received"],
    transitioning: true,
    actionLabel: null,
    actionHref: null,
  };
}

export function MemberInvoiceWorkbenchPage() {
  const session = useAuthSession();
  const { showError, showSuccess, showWarning } = useSnackbar();
  const actorId = session?.actorId ?? "";
  const [searchParams] = useSearchParams();
  const location = useLocation();
  const navigate = useNavigate();
  const preferredTaskId = searchParams.get("taskId");
  const activeTab = resolveWorkbenchTab(location.hash);
  const preferredInvoiceAnchorTarget = activeTab === "invoices"
    ? parseInvoiceWorkbenchAnchorTarget(location.hash)
    : null;
  const [taskState, setTaskState] = useState<VisibleTaskState>({ status: "loading" });
  const [selectedTaskId, setSelectedTaskId] = useState("");
  const [selectedInvoiceWorkbenchKey, setSelectedInvoiceWorkbenchKey] = useState<string | null>(null);
  const [selectedBatchInvoiceIds, setSelectedBatchInvoiceIds] = useState<string[]>([]);
  const [workbenchState, setWorkbenchState] = useState<SelectedTaskWorkbenchState>({ status: "idle" });
  const [materialTypeDrafts, setMaterialTypeDrafts] = useState<Record<string, MaterialType>>({});
  const [materialTypeErrors, setMaterialTypeErrors] = useState<Record<string, string>>({});
  const [updatingMaterialId, setUpdatingMaterialId] = useState<string | null>(null);
  const [activeManualEditorMaterialId, setActiveManualEditorMaterialId] = useState<string | null>(null);
  const [manualInvoiceFormState, setManualInvoiceFormState] = useState<ManualInvoiceFormState | null>(null);
  const [manualInvoiceErrors, setManualInvoiceErrors] = useState<ManualInvoiceFormErrors>({});
  const [manualInvoiceSubmitError, setManualInvoiceSubmitError] = useState<string | null>(null);
  const [manualInvoiceSaveFeedback, setManualInvoiceSaveFeedback] = useState<ManualInvoiceSaveFeedback | null>(null);
  const [savingManualInvoiceMaterialId, setSavingManualInvoiceMaterialId] = useState<string | null>(null);
  const [retryingRecognitionMaterialId, setRetryingRecognitionMaterialId] = useState<string | null>(null);
  const [recognitionRetryFeedback, setRecognitionRetryFeedback] = useState<MaterialActionFeedback | null>(null);
  const [splitDrafts, setSplitDrafts] = useState<Record<string, SplitDraftRow[]>>({});
  const [splitErrors, setSplitErrors] = useState<Record<string, string>>({});
  const [updatingSplitInvoiceId, setUpdatingSplitInvoiceId] = useState<string | null>(null);
  const [uploadFormState, setUploadFormState] = useState<WorkbenchUploadFormState>(() => buildInitialUploadFormState());
  const [uploadValidationErrors, setUploadValidationErrors] = useState<WorkbenchUploadValidationErrors>({});
  const [uploadSubmitError, setUploadSubmitError] = useState<unknown>(null);
  const [uploadResult, setUploadResult] = useState<MaterialBatchUploadResponse | null>(null);
  const [uploadProcessingRefreshAttempts, setUploadProcessingRefreshAttempts] = useState(0);
  const [isUploading, setIsUploading] = useState(false);
  const [viewingOriginalMaterialId, setViewingOriginalMaterialId] = useState<string | null>(null);
  const [confirmationSubmitError, setConfirmationSubmitError] = useState<unknown>(null);
  const [confirmationFeedback, setConfirmationFeedback] = useState<ConfirmationFeedback | null>(null);
  const [submittingConfirmationSplitId, setSubmittingConfirmationSplitId] = useState<string | null>(null);
  const [staleConfirmationSplitId, setStaleConfirmationSplitId] = useState<string | null>(null);
  const [disputeReasons, setDisputeReasons] = useState<Record<string, string>>({});
  const [disputeErrors, setDisputeErrors] = useState<Record<string, string>>({});
  const [invoiceBatchActionError, setInvoiceBatchActionError] = useState<unknown>(null);
  const [invoiceBatchActionFeedback, setInvoiceBatchActionFeedback] = useState<InvoiceBatchActionFeedback | null>(null);
  const [runningInvoiceBatchAction, setRunningInvoiceBatchAction] = useState<InvoiceBatchAction | null>(null);
  const [runningPendingSupportingMaterialLinkageActionKey, setRunningPendingSupportingMaterialLinkageActionKey] = useState<string | null>(null);
  const [pendingSupportingMaterialLinkageErrors, setPendingSupportingMaterialLinkageErrors] = useState<Record<string, string>>({});
  const [workbenchReloadVersion, setWorkbenchReloadVersion] = useState(0);

  function resetTaskScopedUiState() {
    setActiveManualEditorMaterialId(null);
    setManualInvoiceFormState(null);
    setManualInvoiceErrors({});
    setManualInvoiceSubmitError(null);
    setManualInvoiceSaveFeedback(null);
    setSavingManualInvoiceMaterialId(null);
    setRetryingRecognitionMaterialId(null);
    setRecognitionRetryFeedback(null);
    setUploadValidationErrors({});
    setUploadSubmitError(null);
    setUploadResult(null);
    setUploadProcessingRefreshAttempts(0);
    setUploadFormState(buildInitialUploadFormState());
    setViewingOriginalMaterialId(null);
    setConfirmationSubmitError(null);
    setConfirmationFeedback(null);
    setSubmittingConfirmationSplitId(null);
    setStaleConfirmationSplitId(null);
    setDisputeReasons({});
    setDisputeErrors({});
    setSelectedInvoiceWorkbenchKey(null);
    setSelectedBatchInvoiceIds([]);
    setInvoiceBatchActionError(null);
    setInvoiceBatchActionFeedback(null);
    setRunningInvoiceBatchAction(null);
    setRunningPendingSupportingMaterialLinkageActionKey(null);
    setPendingSupportingMaterialLinkageErrors({});
  }

  useEffect(() => {
    let cancelled = false;

    async function loadVisibleTasks() {
      if (!session || session.role !== "member") {
        return;
      }

      setTaskState({ status: "loading" });

      try {
        const allTasks = await trmsApi.listTasks();
        const visibleTasks = allTasks.filter((task) => task.member_ids.includes(session.actorId));

        if (cancelled) {
          return;
        }

        setTaskState({ status: "ready", visibleTasks });
        resetTaskScopedUiState();
        setSelectedTaskId((currentTaskId) => pickSelectedTaskId(visibleTasks, preferredTaskId, currentTaskId));
      } catch (error) {
        if (cancelled) {
          return;
        }
        setTaskState({ status: "error", error });
      }
    }

    void loadVisibleTasks();

    return () => {
      cancelled = true;
    };
  }, [preferredTaskId, session]);

  useEffect(() => {
    let cancelled = false;

    function applyLoadedWorkbenchState(
      task: ReimbursementTask,
      report: TaskMemberStatusReport,
      items: WorkbenchInvoiceItem[],
      pendingSupportingMaterialLinkageItems: PendingSupportingMaterialLinkageItem[],
      sharedInvoices: TaskSharedInvoiceItem[],
    ) {
      if (cancelled) {
        return;
      }

      setWorkbenchState({
        status: "ready",
        task,
        report,
        items,
        pendingSupportingMaterialLinkageItems,
        sharedInvoices: [...sharedInvoices].sort(
          (left, right) => right.updated_at.localeCompare(left.updated_at),
        ),
      });
      setMaterialTypeDrafts(
        Object.fromEntries(
          report.materials.map((material) => [material.material_id, material.material_type] as const),
        ),
      );
      setSplitDrafts(buildInitialSplitDrafts(items, session!.actorId));
      setMaterialTypeErrors({});
      setSplitErrors({});
    }

    async function loadWorkbenchLegacy(task: ReimbursementTask) {
      const [report, sharedInvoicesReport, pendingSupportingMaterialLinkageReport, invoicesResponse] = await Promise.all([
        trmsApi.getTaskMemberStatus(task.id, session!.actorId),
        trmsApi.getTaskSharedInvoices(task.id, session!.actorId),
        trmsApi.getTaskSupportingMaterialLinkage(task.id, session!.actorId),
        trmsApi.listTaskInvoices(task.id),
      ]);
      const invoices = invoicesResponse.items;
      const recognitionEntries = await Promise.all(
        report.materials.map(async (material) => [
          material.material_id,
          (await trmsApi.listMaterialRecognitionTasks(material.material_id)).latest_effective,
        ] as const),
      );
      const validationEntries = await Promise.all(
        invoices.map(async (invoice) => [
          invoice.id,
          (await trmsApi.listInvoiceValidations(invoice.id)).items,
        ] as const),
      );
      const supportingEntries = await Promise.all(
        invoices.map(async (invoice) => [
          invoice.id,
          (await trmsApi.listInvoiceSupportingMaterials(invoice.id)).items,
        ] as const),
      );
      const splitEntries = await Promise.all(
        invoices.map(async (invoice) => [
          invoice.id,
          (await trmsApi.listInvoiceSplits(invoice.id)).items,
        ] as const),
      );
      const confirmationEntries = await Promise.all(
        invoices.map(async (invoice) => [
          invoice.id,
          (await trmsApi.listInvoiceConfirmations(invoice.id)).items,
        ] as const),
      );
      applyLoadedWorkbenchState(
        task,
        report,
        buildWorkbenchItems(
          report,
          invoices,
          new Map(recognitionEntries),
          new Map(validationEntries),
          new Map(supportingEntries),
          new Map(splitEntries),
          new Map(confirmationEntries),
        ),
        pendingSupportingMaterialLinkageReport.items,
        sharedInvoicesReport.items,
      );
    }

    async function loadWorkbench(task: ReimbursementTask) {
      setWorkbenchState({ status: "loading", task });

      try {
        const summary = await trmsApi.getTaskMemberWorkbench(task.id, session!.actorId);
        applyLoadedWorkbenchState(
          task,
          summary.report,
          summary.items.map(mapWorkbenchSummaryItem),
          summary.pending_supporting_material_linkage_items,
          summary.shared_invoices,
        );
      } catch (error) {
        try {
          await loadWorkbenchLegacy(task);
        } catch (legacyError) {
          if (cancelled) {
            return;
          }
          setWorkbenchState({ status: "error", task, error: legacyError ?? error });
        }
      }
    }

    if (!session || session.role !== "member" || taskState.status !== "ready") {
      return () => {
        cancelled = true;
      };
    }

    const selectedTask = taskState.visibleTasks.find((task) => task.id === selectedTaskId) ?? null;
    if (!selectedTask) {
      return () => {
        cancelled = true;
      };
    }

    void loadWorkbench(selectedTask);

    return () => {
      cancelled = true;
    };
  }, [selectedTaskId, session, taskState, workbenchReloadVersion]);

  const visibleTasks = taskState.status === "ready" ? taskState.visibleTasks : [];
  const selectedTask = visibleTasks.find((task) => task.id === selectedTaskId) ?? null;
  const summaryStats = workbenchState.status === "ready" ? buildSummaryStats(workbenchState.task, workbenchState.report) : [];
  const pendingActions = workbenchState.status === "ready"
    ? summarizePendingActionsWithLinkage(
      workbenchState.task,
      workbenchState.report,
      workbenchState.pendingSupportingMaterialLinkageItems,
    )
    : [];
  const missingMaterials = workbenchState.status === "ready" ? workbenchState.report.missing_materials : [];
  const pendingSupportingMaterialLinkageItems = useMemo(
    () => (
      workbenchState.status === "ready"
        ? workbenchState.pendingSupportingMaterialLinkageItems
        : []
    ),
    [workbenchState],
  );
  const sharedInvoices = useMemo(() => (
    workbenchState.status === "ready"
      ? workbenchState.sharedInvoices.filter((item) => item.submitter_id !== actorId)
      : []
  ), [actorId, workbenchState]);
  const resolvedInvoiceWorkbenchSelection = workbenchState.status === "ready" && activeTab === "invoices"
    ? pickInvoiceWorkbenchSelection(
      workbenchState.items,
      sharedInvoices,
      preferredInvoiceAnchorTarget,
      selectedInvoiceWorkbenchKey,
    )
    : null;
  const resolvedInvoiceWorkbenchKey = resolvedInvoiceWorkbenchSelection
    ? buildInvoiceWorkbenchSelectionKey(resolvedInvoiceWorkbenchSelection)
    : null;
  const selectedOwnWorkbenchItem = workbenchState.status === "ready" && resolvedInvoiceWorkbenchSelection?.kind === "own"
    ? workbenchState.items.find((item) => item.material.material_id === resolvedInvoiceWorkbenchSelection.materialId) ?? null
    : null;
  const selectedSharedWorkbenchInvoice = resolvedInvoiceWorkbenchSelection?.kind === "shared"
    ? sharedInvoices.find((item) => item.invoice_id === resolvedInvoiceWorkbenchSelection.invoiceId) ?? null
    : null;
  const selectedInvoiceDetailAnchorId = selectedOwnWorkbenchItem?.invoice?.id
    ? `workbench-invoice-${selectedOwnWorkbenchItem.invoice.id}`
    : selectedSharedWorkbenchInvoice
      ? `workbench-invoice-${selectedSharedWorkbenchInvoice.invoice_id}`
      : undefined;
  const taskAllowedExpenseTypes = workbenchState.status === "ready"
    ? buildAllowedExpenseTypes(workbenchState.task)
    : [];
  const confirmationItems = useMemo(
    () => (workbenchState.status === "ready" ? buildConfirmationItems(workbenchState.items) : []),
    [workbenchState],
  );
  const abnormalCount = useMemo(() => {
    if (workbenchState.status !== "ready") {
      return 0;
    }
    return workbenchState.items.reduce((count, item) => count + collectAbnormalReasons(item).length, 0);
  }, [workbenchState]);
  const pendingActionCount = pendingActions.filter((action) => action.id !== "done").length;
  const ownInvoiceItems = useMemo(
    () => (
      workbenchState.status === "ready"
        ? workbenchState.items.filter((item) => item.invoice !== null)
        : []
    ),
    [workbenchState],
  );
  const invoiceQueueGroups = useMemo(
    () => (
      workbenchState.status === "ready"
        ? buildInvoiceQueueGroups(workbenchState.items, pendingSupportingMaterialLinkageItems)
        : { readyItems: [], problemSections: [] as InvoiceQueueGroup[] }
    ),
    [pendingSupportingMaterialLinkageItems, workbenchState],
  );
  const readyInvoiceItems = invoiceQueueGroups.readyItems;
  const problemInvoiceSections = invoiceQueueGroups.problemSections;
  const problemInvoiceCount = problemInvoiceSections.reduce((count, section) => count + section.items.length, 0);
  const materialResultGroups = useMemo(
    () => (
      workbenchState.status === "ready"
        ? buildMaterialResultGroups(workbenchState.items)
        : []
    ),
    [workbenchState],
  );
  const draftSummary = useMemo(
    () => (
      workbenchState.status === "ready"
        ? buildDraftSummary(workbenchState.items, workbenchState.report)
        : null
    ),
    [workbenchState],
  );
  const selectedBatchInvoiceIdSet = useMemo(
    () => new Set(selectedBatchInvoiceIds),
    [selectedBatchInvoiceIds],
  );
  const selectedBatchInvoiceItems = useMemo(
    () => ownInvoiceItems.filter((item) => item.invoice && selectedBatchInvoiceIdSet.has(item.invoice.id)),
    [ownInvoiceItems, selectedBatchInvoiceIdSet],
  );
  const selectedSubmittedInvoiceCount = selectedBatchInvoiceItems.filter(
    (item) => item.invoice?.member_submission_status === "submitted",
  ).length;
  const selectedUnsubmittedInvoiceCount = selectedBatchInvoiceItems.length - selectedSubmittedInvoiceCount;
  const allOwnInvoiceIds = ownInvoiceItems.map((item) => item.invoice!.id);
  const allOwnInvoicesSelected = allOwnInvoiceIds.length > 0 && allOwnInvoiceIds.every(
    (invoiceId) => selectedBatchInvoiceIdSet.has(invoiceId),
  );
  const recentUploadProcessingSnapshots = useMemo(
    () => (
      uploadResult && selectedTask
        ? uploadResult.items.map((item) => buildUploadProcessingSnapshot(
          item,
          selectedTask.id,
          workbenchState,
          uploadResult.recognition_dispatch,
        ))
        : []
    ),
    [selectedTask, uploadResult, workbenchState],
  );
  const hasRecentUploadTransitioningItems = recentUploadProcessingSnapshots.some((item) => item.transitioning);
  const canAutoRefreshRecentUploadStatus = (
    activeTab === "invoices"
    && uploadResult !== null
    && hasRecentUploadTransitioningItems
    && uploadProcessingRefreshAttempts < RECENT_UPLOAD_AUTO_REFRESH_MAX_ATTEMPTS
  );
  const submitBlockers = workbenchState.status === "ready"
    ? buildSubmitBlockers(
      workbenchState.task,
      pendingActionCount,
      problemInvoiceCount,
      pendingSupportingMaterialLinkageItems,
      confirmationItems,
    )
    : [];
  const canSubmitReimbursementConfirmation = submitBlockers.length === 0 && readyInvoiceItems.length > 0;

  useEffect(() => {
    if (!canAutoRefreshRecentUploadStatus) {
      return undefined;
    }

    const timerId = window.setTimeout(() => {
      setUploadProcessingRefreshAttempts((current) => current + 1);
      setWorkbenchReloadVersion((current) => current + 1);
    }, RECENT_UPLOAD_AUTO_REFRESH_INTERVAL_MS);

    return () => {
      window.clearTimeout(timerId);
    };
  }, [canAutoRefreshRecentUploadStatus]);

  function handlePendingSupportingMaterialCandidateSelect(invoiceId: string) {
    if (workbenchState.status !== "ready") {
      return;
    }
    const ownMatch = workbenchState.items.find((item) => item.invoice?.id === invoiceId);
    if (ownMatch) {
      setSelectedInvoiceWorkbenchKey(buildInvoiceWorkbenchSelectionKey({
        kind: "own",
        materialId: ownMatch.material.material_id,
      }));
      void navigate(buildWorkbenchTaskAnchor(workbenchState.task.id, "#member-workbench-invoices"));
      return;
    }
    const sharedMatch = sharedInvoices.find((item) => item.invoice_id === invoiceId);
    if (sharedMatch) {
      setSelectedInvoiceWorkbenchKey(buildInvoiceWorkbenchSelectionKey({
        kind: "shared",
        invoiceId: sharedMatch.invoice_id,
      }));
      void navigate(buildWorkbenchTaskAnchor(workbenchState.task.id, "#member-workbench-invoices"));
    }
  }

  async function handlePendingSupportingMaterialAttach(
    item: PendingSupportingMaterialLinkageItem,
    candidateInvoiceId: string,
    candidateInvoiceNumber: string,
  ) {
    if (!session || workbenchState.status !== "ready") {
      return;
    }

    const actionKey = buildPendingSupportingMaterialLinkageActionKey({
      materialId: item.material_id,
      invoiceId: candidateInvoiceId,
    });
    setPendingSupportingMaterialLinkageErrors((current) => {
      const next = { ...current };
      delete next[item.material_id];
      return next;
    });
    setRunningPendingSupportingMaterialLinkageActionKey(actionKey);

    try {
      await trmsApi.attachInvoiceSupportingMaterial(candidateInvoiceId, item.material_id);
      handlePendingSupportingMaterialCandidateSelect(candidateInvoiceId);
      setWorkbenchReloadVersion((current) => current + 1);
      showSuccess(`已将 ${item.original_filename} 关联到发票 ${candidateInvoiceNumber}，页面已刷新最新附件状态。`);
    } catch (error) {
      const message = error instanceof ApiError ? error.summary.message : "关联辅助材料失败，请稍后重试。";
      setPendingSupportingMaterialLinkageErrors((current) => ({
        ...current,
        [item.material_id]: message,
      }));
      showError(message);
    } finally {
      setRunningPendingSupportingMaterialLinkageActionKey(null);
    }
  }

  function handleBatchInvoiceSelectionChange(invoiceId: string, checked: boolean) {
    setSelectedBatchInvoiceIds((current) => {
      if (checked) {
        if (current.includes(invoiceId)) {
          return current;
        }
        return [...current, invoiceId];
      }
      return current.filter((currentInvoiceId) => currentInvoiceId !== invoiceId);
    });
  }

  function handleBatchSelectAllInvoices() {
    setSelectedBatchInvoiceIds(allOwnInvoiceIds);
  }

  function handleBatchClearInvoiceSelection() {
    setSelectedBatchInvoiceIds([]);
  }

  function handleSubmitReimbursementConfirmation() {
    if (readyInvoiceItems.length === 0) {
      return;
    }
    const invoiceIds = readyInvoiceItems.flatMap((item) => (item.invoice ? [item.invoice.id] : []));
    setSelectedBatchInvoiceIds(invoiceIds);
    void handleInvoiceBatchAction("submit", invoiceIds);
  }

  async function handleInvoiceBatchAction(action: InvoiceBatchAction, invoiceIds = selectedBatchInvoiceIds) {
    if (!session || !selectedTask || invoiceIds.length === 0) {
      return;
    }

    setInvoiceBatchActionError(null);
    setInvoiceBatchActionFeedback(null);
    setRunningInvoiceBatchAction(action);

    try {
      const response = action === "submit"
        ? await trmsApi.submitTaskInvoices(selectedTask.id, {
          actor_id: session.actorId,
          invoice_ids: invoiceIds,
        })
        : await trmsApi.withdrawTaskInvoiceSubmissions(selectedTask.id, {
          actor_id: session.actorId,
          invoice_ids: invoiceIds,
        });
      const feedback = {
        action,
        ...response,
      } satisfies InvoiceBatchActionFeedback;
      setInvoiceBatchActionFeedback(feedback);
      if (response.items.length > 0) {
        setWorkbenchReloadVersion((current) => current + 1);
      }
      const feedbackMessage = buildInvoiceBatchFeedbackMessage(feedback);
      if (response.status === "success") {
        showSuccess(feedbackMessage);
      } else {
        showWarning(feedbackMessage);
      }
    } catch (error) {
      setInvoiceBatchActionError(error);
      const message = error instanceof ApiError ? error.summary.message : "批量提交状态更新失败，请稍后重试。";
      showError(message);
    } finally {
      setRunningInvoiceBatchAction(null);
    }
  }

  async function handleMaterialTypeSave(materialId: string) {
    if (!session) {
      return;
    }
    const materialType = materialTypeDrafts[materialId];
    if (!materialType) {
      return;
    }

    setUpdatingMaterialId(materialId);
    setMaterialTypeErrors((current) => {
      const next = { ...current };
      delete next[materialId];
      return next;
    });

    try {
      await trmsApi.updateMaterialType(materialId, {
        actor_id: session.actorId,
        material_type: materialType,
      });
      setWorkbenchReloadVersion((current) => current + 1);
    } catch (error) {
      const message = error instanceof ApiError ? error.message : "材料类型更新失败，请稍后重试。";
      setMaterialTypeErrors((current) => ({
        ...current,
        [materialId]: message,
      }));
    } finally {
      setUpdatingMaterialId((current) => (current === materialId ? null : current));
    }
  }

  function handleManualEditorToggle(item: WorkbenchInvoiceItem, task: ReimbursementTask) {
    if (item.material.material_type !== "invoice") {
      return;
    }
    if (activeManualEditorMaterialId === item.material.material_id) {
      setActiveManualEditorMaterialId(null);
      setManualInvoiceFormState(null);
      setManualInvoiceErrors({});
      setManualInvoiceSubmitError(null);
      return;
    }

    setActiveManualEditorMaterialId(item.material.material_id);
    setManualInvoiceFormState(buildManualInvoiceFormState(item, buildAllowedExpenseTypes(task)));
    setManualInvoiceErrors({});
    setManualInvoiceSubmitError(null);
    setManualInvoiceSaveFeedback(null);
  }

  function updateManualInvoiceField<Key extends keyof ManualInvoiceFormState>(
    key: Key,
    value: ManualInvoiceFormState[Key],
  ) {
    setManualInvoiceFormState((current) => {
      if (!current) {
        return current;
      }
      return {
        ...current,
        [key]: value,
      };
    });
    setManualInvoiceErrors((current) => {
      if (!(key in current)) {
        return current;
      }
      const next = { ...current };
      delete next[key];
      return next;
    });
  }

  async function handleManualInvoiceSubmit(
    event: FormEvent<HTMLFormElement>,
    item: WorkbenchInvoiceItem,
    task: ReimbursementTask,
  ) {
    event.preventDefault();
    if (!session || !manualInvoiceFormState) {
      return;
    }

    const allowedExpenseTypes = buildAllowedExpenseTypes(task);
    const errors = validateManualInvoiceForm(manualInvoiceFormState, allowedExpenseTypes);
    setManualInvoiceErrors(errors);
    setManualInvoiceSubmitError(null);
    if (Object.keys(errors).length > 0) {
      return;
    }

    const amountCents = parseCurrencyInputToCents(manualInvoiceFormState.amountYuan);
    if (amountCents === null) {
      return;
    }

    setSavingManualInvoiceMaterialId(item.material.material_id);
    try {
      const response = await trmsApi.createOrUpdateInvoice(item.material.material_id, {
        actor_id: session.actorId,
        invoice_number: manualInvoiceFormState.invoiceNumber.trim(),
        issue_date: manualInvoiceFormState.issueDate.trim() || null,
        transaction_time: toApiDateTime(manualInvoiceFormState.transactionTime),
        buyer_name: manualInvoiceFormState.buyerName.trim(),
        tax_number: manualInvoiceFormState.taxNumber.trim(),
        seller_name: manualInvoiceFormState.sellerName.trim() || null,
        amount_cents: amountCents,
        expense_type: manualInvoiceFormState.expenseType,
      });
      setManualInvoiceSaveFeedback({
        materialId: item.material.material_id,
        invoiceNumber: response.invoice.invoice_number,
        validationCount: response.validations.length,
        failedValidationCount: response.validations.filter((validation) => validation.status === "failed").length,
        pendingValidationCount: response.validations.filter((validation) => validation.status === "pending").length,
      });
      setActiveManualEditorMaterialId(null);
      setManualInvoiceFormState(null);
      setManualInvoiceErrors({});
      setManualInvoiceSubmitError(null);
      setWorkbenchReloadVersion((current) => current + 1);
    } catch (error) {
      setManualInvoiceSubmitError(error instanceof ApiError ? error.message : "保存发票字段失败，请稍后重试。");
    } finally {
      setSavingManualInvoiceMaterialId((current) => (
        current === item.material.material_id ? null : current
      ));
    }
  }

  async function handleRecognitionRetry(item: WorkbenchInvoiceItem) {
    setRetryingRecognitionMaterialId(item.material.material_id);
    setRecognitionRetryFeedback(null);
    try {
      const created = await trmsApi.createRecognitionTask(item.material.material_id);
      const executed = await trmsApi.executeRecognitionTask(created.item.id);
      setRecognitionRetryFeedback({
        materialId: item.material.material_id,
        tone: executed.dispatch?.status === "queued" ? "warning" : "success",
        message: executed.dispatch?.message ?? "已发起重新识别，工作台正在刷新最新状态。",
      });
      setWorkbenchReloadVersion((current) => current + 1);
    } catch (error) {
      setRecognitionRetryFeedback({
        materialId: item.material.material_id,
        tone: "error",
        message: error instanceof ApiError ? error.message : "重新识别失败，请稍后重试。",
      });
    } finally {
      setRetryingRecognitionMaterialId((current) => (
        current === item.material.material_id ? null : current
      ));
    }
  }

  function updateUploadField<Key extends keyof WorkbenchUploadFormState>(
    key: Key,
    value: WorkbenchUploadFormState[Key],
  ) {
    setUploadFormState((current) => ({
      ...current,
      [key]: value,
    }));
    setUploadValidationErrors((current) => {
      if (!(key in current)) {
        return current;
      }
      const next = { ...current };
      delete next[key];
      return next;
    });
  }

  function resetUploadSelectedFiles() {
    setUploadFormState((current) => ({
      ...current,
      files: [],
    }));
  }

  async function handleUploadSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!session) {
      return;
    }

    setUploadSubmitError(null);
    setUploadResult(null);
    setUploadProcessingRefreshAttempts(0);

    const errors = validateWorkbenchUploadForm(selectedTask, uploadFormState);
    setUploadValidationErrors(errors);
    if (Object.keys(errors).length > 0 || !selectedTask) {
      return;
    }

    const requestBody = new FormData();
    requestBody.set("submitter_id", session.actorId);
    requestBody.set("channel", "web");
    uploadFormState.files.forEach((file) => {
      requestBody.append("files", file);
    });

    setIsUploading(true);
    try {
      const response = await trmsApi.submitTaskMaterials(selectedTask.id, requestBody);
      setUploadResult(response);
      setUploadProcessingRefreshAttempts(0);
      resetUploadSelectedFiles();
      if (response.items.length > 0) {
        setWorkbenchReloadVersion((current) => current + 1);
      }
      const dispatchMessage = formatRecognitionDispatchMessage(response.recognition_dispatch);
      if (response.status === "success") {
        showSuccess(dispatchMessage
          ? `上传成功：${response.items.length} 个文件已归档到当前任务。${dispatchMessage}`
          : `上传成功：${response.items.length} 个文件已归档到当前任务。`);
      } else {
        const failureCount = response.failures?.length ?? 0;
        showWarning(dispatchMessage
          ? `上传完成：${response.items.length} 个成功，${failureCount} 个失败。${dispatchMessage}`
          : `上传完成：${response.items.length} 个成功，${failureCount} 个失败。`);
      }
    } catch (error) {
      const failedBatch = extractFailedBatchUploadResponse(error);
      if (failedBatch) {
        setUploadResult(failedBatch);
        setUploadProcessingRefreshAttempts(0);
        resetUploadSelectedFiles();
        if (failedBatch.items.length > 0) {
          setWorkbenchReloadVersion((current) => current + 1);
        }
        const failureCount = failedBatch.failures?.length ?? 0;
        showError(`上传失败：${failureCount} 个文件未通过，请查看逐文件原因。`);
      } else {
        setUploadSubmitError(error);
        const message = error instanceof ApiError ? error.summary.message : "材料上传失败，请稍后重试。";
        showError(message);
      }
    } finally {
      setIsUploading(false);
    }
  }

  async function handleViewOriginalMaterial(item: WorkbenchInvoiceItem) {
    setViewingOriginalMaterialId(item.material.material_id);
    try {
      const file = await trmsApi.downloadMaterialContent(item.material.material_id);
      const objectUrl = URL.createObjectURL(file.blob);
      window.open(objectUrl, "_blank", "noopener,noreferrer");
      window.setTimeout(() => {
        URL.revokeObjectURL(objectUrl);
      }, 60_000);
    } catch (error) {
      const message = error instanceof ApiError ? error.summary.message : "原文件暂时无法打开，请稍后重试。";
      showError(message);
    } finally {
      setViewingOriginalMaterialId((current) => (
        current === item.material.material_id ? null : current
      ));
    }
  }

  function updateSplitDraft(invoiceId: string, rowKey: string, patch: Partial<SplitDraftRow>) {
    setSplitDrafts((current) => ({
      ...current,
      [invoiceId]: (current[invoiceId] ?? []).map((draft) => (
        draft.key === rowKey
          ? {
            ...draft,
            ...patch,
          }
          : draft
      )),
    }));
    setSplitErrors((current) => {
      const next = { ...current };
      delete next[invoiceId];
      return next;
    });
  }

  function addSplitDraft(invoiceId: string, taskMemberIds: string[]) {
    if (!session) {
      return;
    }
    setSplitDrafts((current) => {
      const currentDrafts = current[invoiceId] ?? [];
      const defaultMemberId = pickDefaultSplitMemberId(
        taskMemberIds,
        currentDrafts,
        session.actorId,
      );
      return {
        ...current,
        [invoiceId]: [
          ...currentDrafts,
          {
            key: buildSplitDraftKey(invoiceId, `new-${currentDrafts.length + 1}`),
            member_id: defaultMemberId,
            amount_yuan: "0.00",
            note: "",
          },
        ],
      };
    });
    setSplitErrors((current) => {
      const next = { ...current };
      delete next[invoiceId];
      return next;
    });
  }

  function removeSplitDraft(invoiceId: string, rowKey: string) {
    setSplitDrafts((current) => ({
      ...current,
      [invoiceId]: (current[invoiceId] ?? []).filter((draft) => draft.key !== rowKey),
    }));
    setSplitErrors((current) => {
      const next = { ...current };
      delete next[invoiceId];
      return next;
    });
  }

  async function handleSplitSave(item: WorkbenchInvoiceItem) {
    if (!session || !item.invoice) {
      return;
    }
    const invoiceId = item.invoice.id;
    const drafts = splitDrafts[invoiceId] ?? buildSplitDraftRows(item, session.actorId);
    if (drafts.length === 0) {
      setSplitErrors((current) => ({
        ...current,
        [invoiceId]: "至少保留一条分摊记录。",
      }));
      return;
    }

    const normalizedItems = [];
    for (const draft of drafts) {
      const amountCents = parseCurrencyInputToCents(draft.amount_yuan);
      if (amountCents === null || amountCents <= 0) {
        setSplitErrors((current) => ({
          ...current,
          [invoiceId]: "请为每条分摊填写有效金额，格式示例为 123.45。",
        }));
        return;
      }
      normalizedItems.push({
        member_id: draft.member_id,
        amount_cents: amountCents,
        note: normalizeSplitNote(draft.note),
      });
    }

    setUpdatingSplitInvoiceId(invoiceId);
    setSplitErrors((current) => {
      const next = { ...current };
      delete next[invoiceId];
      return next;
    });

    try {
      await trmsApi.replaceInvoiceSplits(invoiceId, {
        actor_id: session.actorId,
        items: normalizedItems,
      });
      setWorkbenchReloadVersion((current) => current + 1);
    } catch (error) {
      const message = error instanceof ApiError ? error.message : "分摊方案更新失败，请稍后重试。";
      setSplitErrors((current) => ({
        ...current,
        [invoiceId]: message,
      }));
    } finally {
      setUpdatingSplitInvoiceId((current) => (current === invoiceId ? null : current));
    }
  }

  async function handleConfirmationSubmit(
    item: WorkbenchConfirmationItem,
    status: Extract<ConfirmationStatus, "confirmed" | "disputed">,
  ) {
    if (!session) {
      return;
    }

    const disputeReason = disputeReasons[item.detail.split_id]?.trim() ?? "";
    if (status === "disputed" && !disputeReason) {
      setDisputeErrors((current) => ({
        ...current,
        [item.detail.split_id]: "提交异议时必须填写原因。",
      }));
      return;
    }

    setConfirmationSubmitError(null);
    setConfirmationFeedback(null);
    setStaleConfirmationSplitId(null);
    setDisputeErrors((current) => {
      if (!(item.detail.split_id in current)) {
        return current;
      }
      const next = { ...current };
      delete next[item.detail.split_id];
      return next;
    });
    setSubmittingConfirmationSplitId(item.detail.split_id);

    try {
      await trmsApi.submitSplitConfirmation(item.detail.split_id, {
        actor_id: session.actorId,
        member_id: session.actorId,
        status,
        dispute_reason: status === "disputed" ? disputeReason : null,
      });
      setConfirmationFeedback({
        splitId: item.detail.split_id,
        status,
      });
      if (status === "disputed") {
        setDisputeReasons((current) => ({
          ...current,
          [item.detail.split_id]: "",
        }));
      }
      setWorkbenchReloadVersion((current) => current + 1);
    } catch (error) {
      if (isSplitStaleError(error)) {
        setStaleConfirmationSplitId(item.detail.split_id);
        return;
      }
      setConfirmationSubmitError(error);
    } finally {
      setSubmittingConfirmationSplitId(null);
    }
  }

  function handleTaskChange(nextTaskId: string) {
    resetTaskScopedUiState();
    setSelectedTaskId(nextTaskId);
    void navigate(buildWorkbenchTabAnchor(nextTaskId, activeTab));
  }

  function handleTabChange(_event: SyntheticEvent, nextTab: WorkbenchTab) {
    if (!selectedTaskId) {
      return;
    }
    void navigate(buildWorkbenchTabAnchor(selectedTaskId, nextTab));
  }

  function renderOwnWorkbenchQueueCard(item: WorkbenchInvoiceItem, contextLabel: string) {
    const isSelected = resolvedInvoiceWorkbenchKey === buildInvoiceWorkbenchSelectionKey({
      kind: "own",
      materialId: item.material.material_id,
    });
    const abnormalReasons = collectAbnormalReasons(item);
    const canBatchSelect = item.invoice !== null;
    const isBatchSelected = item.invoice ? selectedBatchInvoiceIdSet.has(item.invoice.id) : false;
    const statusSummary = buildInvoiceQueueStatusSummary(item, pendingSupportingMaterialLinkageItems);

    return (
      <li key={item.material.material_id}>
        <div className="page-stack">
          <div className="inline-actions">
            <label>
              <input
                type="checkbox"
                aria-label={`批量选择发票 ${describeWorkbenchInvoice(item)}`}
                checked={isBatchSelected}
                disabled={!canBatchSelect}
                onChange={(event) => {
                  if (!item.invoice) {
                    return;
                  }
                  handleBatchInvoiceSelectionChange(item.invoice.id, event.target.checked);
                }}
              />
              <span> 纳入批量区</span>
            </label>
            {item.invoice ? (
              <StatusBadge tone={item.invoice.member_submission_status === "submitted" ? "success" : "neutral"}>
                {formatInvoiceMemberSubmissionStatus(item.invoice.member_submission_status)}
              </StatusBadge>
            ) : (
              <StatusBadge tone="warning">尚未形成发票</StatusBadge>
            )}
          </div>
          <button
            type="button"
            className={`invoice-material-button ${isSelected ? "invoice-material-button-selected" : ""}`}
            aria-pressed={isSelected}
            onClick={() => {
              setSelectedInvoiceWorkbenchKey(buildInvoiceWorkbenchSelectionKey({
                kind: "own",
                materialId: item.material.material_id,
              }));
            }}
          >
            <div className="task-card-header">
              <div>
                <p className="task-card-id">{contextLabel} / {item.material.material_id}</p>
                <h3>{item.invoice?.invoice_number ?? item.material.original_filename}</h3>
              </div>
              <StatusBadge tone={abnormalReasons.length > 0 ? "warning" : "success"}>
                {abnormalReasons.length > 0 ? `${abnormalReasons.length} 条待处理` : "状态稳定"}
              </StatusBadge>
            </div>
            <dl className="task-meta-grid invoice-editor-summary-grid">
              <div>
                <dt>识别状态</dt>
                <dd>{getRecognitionStatus(item) ? formatRecognitionStatus(getRecognitionStatus(item)!) : "暂无识别"}</dd>
              </div>
              <div>
                <dt>校验状态</dt>
                <dd>{formatValidationStatus(item.material.validation_status)}</dd>
              </div>
              <div>
                <dt>分摊记录</dt>
                <dd>{item.splits.length > 0 ? `${item.splits.length} 条` : "待分摊"}</dd>
              </div>
              <div>
                <dt>提交状态</dt>
                <dd>{item.invoice ? formatInvoiceMemberSubmissionStatus(item.invoice.member_submission_status) : "未形成发票"}</dd>
              </div>
              <div>
                <dt>附件 / 缺失</dt>
                <dd>{item.supportingMaterials.length} / {item.missingMaterials.length}</dd>
              </div>
            </dl>
            {statusSummary.length > 0 ? (
              <ul className="member-status-detail-list" aria-label={`${describeWorkbenchInvoice(item)} 状态摘要`}>
                {statusSummary.map((summary) => (
                  <li key={summary}>{summary}</li>
                ))}
              </ul>
            ) : null}
            <p className="field-hint">点击展开处理详情，继续更正字段、处理附件、分摊和确认。</p>
          </button>
        </div>
      </li>
    );
  }

  function renderMaterialResultCard(item: WorkbenchInvoiceItem, group: MaterialResultGroup) {
    const status = getMaterialUiStatus(item);
    const abnormalReasons = collectAbnormalReasons(item);
    const pendingLinkageMatches = item.invoice
      ? findPendingSupportingMaterialLinkageMatches(item.invoice.id, pendingSupportingMaterialLinkageItems)
      : [];
    const shouldExpand = group.key !== "recognized";
    const isSelected = resolvedInvoiceWorkbenchKey === buildInvoiceWorkbenchSelectionKey({
      kind: "own",
      materialId: item.material.material_id,
    });

    return (
      <li key={`${group.key}:${item.material.material_id}`}>
        <article className={`status-card member-status-card ${shouldExpand ? "" : "status-card-muted"}`}>
          <div className="member-status-section-header">
            <div>
              <p className="task-card-id">{item.material.original_filename}</p>
              <h3>{item.invoice?.invoice_number ?? formatMaterialType(item.material.material_type)}</h3>
            </div>
            <StatusBadge tone={getMaterialUiTone(status)}>
              {MATERIAL_UI_STATUS_LABELS[status]}
            </StatusBadge>
          </div>

          <dl className="task-meta-grid member-status-meta-grid">
            <div>
              <dt>材料类型</dt>
              <dd>{formatMaterialType(item.material.material_type)}</dd>
            </div>
            <div>
              <dt>金额</dt>
              <dd>{item.invoice ? formatCurrencyFromCents(item.invoice.amount_cents) : "待识别"}</dd>
            </div>
            <div>
              <dt>日期</dt>
              <dd>{item.invoice?.issue_date ?? (item.invoice?.transaction_time ? formatDateTime(item.invoice.transaction_time) : "待识别")}</dd>
            </div>
            <div>
              <dt>费用类别</dt>
              <dd>{item.invoice ? formatExpenseType(item.invoice.expense_type) : "待识别"}</dd>
            </div>
            <div>
              <dt>归属成员</dt>
              <dd>{item.splits.length > 0 ? item.splits.map((split) => formatMemberLabel(split.member_id)).join("、") : "待确认"}</dd>
            </div>
            <div>
              <dt>当前状态</dt>
              <dd>{MATERIAL_UI_STATUS_LABELS[status]}</dd>
            </div>
          </dl>

          {shouldExpand ? (
            <div className="member-status-section">
              <div className="member-status-section-header">
                <h4>为什么需要处理</h4>
                <StatusBadge tone="warning">
                  {abnormalReasons.length + pendingLinkageMatches.length} 项
                </StatusBadge>
              </div>
              {abnormalReasons.length > 0 || pendingLinkageMatches.length > 0 ? (
                <ul className="member-status-message-list" aria-label={`${item.material.material_id} 需要处理原因`}>
                  {abnormalReasons.map((reason) => (
                    <li key={reason}>{reason}</li>
                  ))}
                  {pendingLinkageMatches.map((linkage) => (
                    <li key={linkage.material_id}>
                      辅助材料 {linkage.original_filename} 存在多个可能归属，需要你指定对应发票。
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="field-hint">系统还在整理这份材料，完成后会刷新可处理事项。</p>
              )}
            </div>
          ) : (
            <p className="field-hint">系统已生成草稿，默认不要求逐项填写；需要核对时可打开详情。</p>
          )}

          <div className="inline-actions">
            {item.invoice && status !== "confirmed" ? (
              <Button
                type="button"
                variant={status === "recognized" ? "contained" : "outlined"}
                size="small"
                disabled={runningInvoiceBatchAction !== null || workbenchState.status !== "ready" || workbenchState.task.status !== "open"}
                onClick={() => {
                  const invoiceIds = [item.invoice!.id];
                  setSelectedBatchInvoiceIds(invoiceIds);
                  void handleInvoiceBatchAction("submit", invoiceIds);
                }}
              >
                确认
              </Button>
            ) : null}
            <Button
              type="button"
              variant="outlined"
              size="small"
              onClick={() => {
                setSelectedInvoiceWorkbenchKey(buildInvoiceWorkbenchSelectionKey({
                  kind: "own",
                  materialId: item.material.material_id,
                }));
              }}
              aria-pressed={isSelected}
            >
              修改
            </Button>
            <Button
              type="button"
              variant="outlined"
              size="small"
              onClick={() => {
                setSelectedInvoiceWorkbenchKey(buildInvoiceWorkbenchSelectionKey({
                  kind: "own",
                  materialId: item.material.material_id,
                }));
              }}
            >
              指定归属
            </Button>
            <Button type="button" variant="outlined" size="small" disabled>
              标记为不报销
            </Button>
            <Button
              type="button"
              variant="outlined"
              size="small"
              disabled={viewingOriginalMaterialId === item.material.material_id}
              onClick={() => {
                void handleViewOriginalMaterial(item);
              }}
            >
              {viewingOriginalMaterialId === item.material.material_id ? "正在打开..." : "查看原文件"}
            </Button>
          </div>
          {status === "confirmed" ? (
            <p className="field-hint">这份材料已提交给管理员；如需调整，请先在批量区撤回。</p>
          ) : null}
          {status !== "recognized" && status !== "confirmed" ? (
            <p className="field-hint">请先处理上方原因，再提交确认。</p>
          ) : null}
        </article>
      </li>
    );
  }

  function renderSelectedOwnWorkbenchItem(item: WorkbenchInvoiceItem) {
    const abnormalReasons = collectAbnormalReasons(item);
    const invoice = item.invoice;
    const task = workbenchState.status === "ready" ? workbenchState.task : null;
    const splitDraftRows = invoice && session
      ? (splitDrafts[invoice.id] ?? buildSplitDraftRows(item, session.actorId))
      : [];
    const isManualEditorOpen = activeManualEditorMaterialId === item.material.material_id;
    const isSavingManualInvoice = savingManualInvoiceMaterialId === item.material.material_id;
    const scopedRecognitionRetryFeedback = recognitionRetryFeedback?.materialId === item.material.material_id
      ? recognitionRetryFeedback
      : null;
    const scopedManualInvoiceSaveFeedback = manualInvoiceSaveFeedback?.materialId === item.material.material_id
      ? manualInvoiceSaveFeedback
      : null;
    const recognitionActionLabel = getRecognitionStatus(item) ? "运行重新识别" : "开始识别";

    return (
      <>
        <div className="member-status-section-header">
          <div>
            <p className="task-card-id">
              {formatMaterialType(item.material.material_type)} / {item.material.material_id}
            </p>
            <h2>{item.invoice?.invoice_number ?? item.material.original_filename}</h2>
          </div>
          <StatusBadge tone={abnormalReasons.length > 0 ? "warning" : "success"}>
            {abnormalReasons.length > 0 ? "需处理" : "状态稳定"}
          </StatusBadge>
        </div>

        <dl className="task-meta-grid member-status-meta-grid">
          <div>
            <dt>原始文件</dt>
            <dd>{item.material.original_filename}</dd>
          </div>
          <div>
            <dt>上传时间</dt>
            <dd>{formatDateTime(item.material.created_at)}</dd>
          </div>
          <div>
            <dt>识别状态</dt>
            <dd>{getRecognitionStatus(item) ? formatRecognitionStatus(getRecognitionStatus(item)!) : "暂无识别记录"}</dd>
          </div>
          <div>
            <dt>校验状态</dt>
            <dd>{formatValidationStatus(item.material.validation_status)}</dd>
          </div>
        </dl>

        <section className="member-status-section">
          <div className="member-status-section-header">
            <h4>材料类型</h4>
            <StatusBadge tone="info">可自助更正</StatusBadge>
          </div>
          <div className="admin-form-grid">
            <TextField
              select
              label="当前材料类型"
              aria-label={`${item.material.material_id} 材料类型`}
              value={materialTypeDrafts[item.material.material_id] ?? item.material.material_type}
              onChange={(event) => {
                const nextMaterialType = event.target.value as MaterialType;
                setMaterialTypeDrafts((current) => ({
                  ...current,
                  [item.material.material_id]: nextMaterialType,
                }));
              }}
              disabled={updatingMaterialId === item.material.material_id}
            >
              {MATERIAL_TYPE_OPTIONS.map((option) => (
                <MenuItem key={option.value} value={option.value}>
                  {option.label}
                </MenuItem>
              ))}
            </TextField>
            <Box sx={{ display: "flex", alignItems: "center" }}>
              <Button
                type="button"
                variant="outlined"
                onClick={() => {
                  void handleMaterialTypeSave(item.material.material_id);
                }}
                disabled={
                  updatingMaterialId === item.material.material_id
                  || (materialTypeDrafts[item.material.material_id] ?? item.material.material_type)
                    === item.material.material_type
                }
              >
                {updatingMaterialId === item.material.material_id ? "保存中..." : "保存材料类型"}
              </Button>
            </Box>
          </div>
          <p className="field-hint">
            仅收集中任务允许成员修改本人材料类型；若该材料已经形成发票主记录或存在不兼容关联，系统会明确拒绝。
          </p>
          {materialTypeErrors[item.material.material_id] ? (
            <p className="field-error field-error-block">{materialTypeErrors[item.material.material_id]}</p>
          ) : null}
        </section>

        <section className="member-status-section">
          <div className="member-status-section-header">
            <h4>待处理事项</h4>
            <StatusBadge tone={abnormalReasons.length > 0 ? "warning" : "success"}>{abnormalReasons.length} 条</StatusBadge>
          </div>
          {abnormalReasons.length > 0 ? (
            <ul className="member-status-message-list" aria-label={`${item.material.material_id} 异常原因列表`}>
              {abnormalReasons.map((reason) => (
                <li key={reason}>{reason}</li>
              ))}
            </ul>
          ) : (
            <p className="field-hint">当前发票没有新的识别、校验或确认异常。</p>
          )}
        </section>

        <section className="member-status-section">
          <div className="member-status-section-header">
            <h4>识别字段与当前值</h4>
            <StatusBadge tone="info">
              {item.recognition ? renderRecognitionSource(getRecognitionFieldValue(item.recognition, "invoice_number")) : "暂无识别"}
            </StatusBadge>
          </div>
          <ul className="member-status-message-list" aria-label={`${item.material.material_id} 发票字段列表`}>
            {FIELD_ORDER.map((fieldName) => {
              const recognitionField = getRecognitionFieldValue(item.recognition, fieldName);
              const manualValue = getInvoiceFieldValue(item.invoice, fieldName);
              const recognitionText = formatFieldValue(fieldName, recognitionField?.value ?? null);
              const manualText = formatFieldValue(fieldName, manualValue);
              const isCorrected = recognitionField !== null && manualText !== recognitionText;
              return (
                <li key={fieldName}>
                  <strong>{FIELD_LABELS[fieldName]}</strong>
                  <span>识别值：{recognitionText}</span>
                  <span>当前值：{manualText}</span>
                  <span>
                    {recognitionField
                      ? `${renderRecognitionSource(recognitionField)} / ${recognitionField.status === "needs_confirmation" ? "待确认" : "已识别"}`
                      : "暂无识别结果"}
                  </span>
                  {isCorrected ? <span>状态：已人工更正</span> : null}
                </li>
              );
            })}
          </ul>
        </section>

        <section className="member-status-section">
          <div className="member-status-section-header">
            <h4>手动补录与重新识别</h4>
            <StatusBadge tone="info">仅本人材料可操作</StatusBadge>
          </div>
          <p className="field-hint">
            这里用于修正系统识别不准的字段；重新识别会再次读取原文件，不会覆盖你已经确认的内容。
          </p>
          <div className="inline-actions">
            <Button
              type="button"
              variant="outlined"
              disabled={retryingRecognitionMaterialId === item.material.material_id}
              onClick={() => {
                void handleRecognitionRetry(item);
              }}
            >
              {retryingRecognitionMaterialId === item.material.material_id ? "重新识别中..." : recognitionActionLabel}
            </Button>
            {item.material.material_type === "invoice" ? (
              <Button
                type="button"
                variant="outlined"
                onClick={() => {
                  if (task) {
                    handleManualEditorToggle(item, task);
                  }
                }}
              >
                {isManualEditorOpen ? "收起手动补录" : "手动填写或更正发票"}
              </Button>
            ) : null}
          </div>
          {scopedRecognitionRetryFeedback ? (
            scopedRecognitionRetryFeedback.tone === "error" ? (
              <p className="field-error field-error-block">{scopedRecognitionRetryFeedback.message}</p>
            ) : (
              <p className="field-hint">{scopedRecognitionRetryFeedback.message}</p>
            )
          ) : null}
          {item.material.material_type !== "invoice" ? (
            <p className="field-hint">
              当前材料不是发票类型，因此这里只提供重新识别入口；如需补录发票字段，请先确认材料类型是否应更正为发票。
            </p>
          ) : null}
          {scopedManualInvoiceSaveFeedback ? (
            <p className="field-hint">
              已保存发票 {scopedManualInvoiceSaveFeedback.invoiceNumber}；当前共有 {scopedManualInvoiceSaveFeedback.validationCount} 条校验结果，其中失败 {scopedManualInvoiceSaveFeedback.failedValidationCount} 条、待确认 {scopedManualInvoiceSaveFeedback.pendingValidationCount} 条。
            </p>
          ) : null}
          {isManualEditorOpen && manualInvoiceFormState && item.material.material_type === "invoice" && task ? (
            <form
              className="page-stack"
              aria-label={`${item.material.material_id} 发票手动补录表单`}
              onSubmit={(event) => {
                void handleManualInvoiceSubmit(event, item, task);
              }}
            >
              <div className="admin-form-grid">
                <TextField
                  label="发票号码"
                  value={manualInvoiceFormState.invoiceNumber}
                  onChange={(event) => {
                    updateManualInvoiceField("invoiceNumber", event.target.value);
                  }}
                  error={Boolean(manualInvoiceErrors.invoiceNumber)}
                  helperText={manualInvoiceErrors.invoiceNumber}
                  slotProps={{ htmlInput: { "aria-label": `${item.material.material_id} 发票号码` } }}
                />
                <TextField
                  label="开票日期"
                  type="date"
                  value={manualInvoiceFormState.issueDate}
                  onChange={(event) => {
                    updateManualInvoiceField("issueDate", event.target.value);
                  }}
                  slotProps={{ inputLabel: { shrink: true } }}
                />
                <TextField
                  label="交易时间"
                  type="datetime-local"
                  value={manualInvoiceFormState.transactionTime}
                  onChange={(event) => {
                    updateManualInvoiceField("transactionTime", event.target.value);
                  }}
                  slotProps={{
                    inputLabel: { shrink: true },
                    htmlInput: { "aria-label": `${item.material.material_id} 交易时间` },
                  }}
                />
                <TextField
                  label="金额（元）"
                  type="text"
                  inputMode="decimal"
                  placeholder="例如 123.45"
                  value={manualInvoiceFormState.amountYuan}
                  onChange={(event) => {
                    updateManualInvoiceField("amountYuan", event.target.value);
                  }}
                  error={Boolean(manualInvoiceErrors.amountYuan)}
                  helperText={manualInvoiceErrors.amountYuan}
                  slotProps={{ htmlInput: { "aria-label": `${item.material.material_id} 金额` } }}
                />
                <TextField
                  label="发票抬头"
                  value={manualInvoiceFormState.buyerName}
                  onChange={(event) => {
                    updateManualInvoiceField("buyerName", event.target.value);
                  }}
                  error={Boolean(manualInvoiceErrors.buyerName)}
                  helperText={manualInvoiceErrors.buyerName}
                  slotProps={{ htmlInput: { "aria-label": `${item.material.material_id} 发票抬头` } }}
                />
                <TextField
                  label="税号"
                  value={manualInvoiceFormState.taxNumber}
                  onChange={(event) => {
                    updateManualInvoiceField("taxNumber", event.target.value);
                  }}
                  error={Boolean(manualInvoiceErrors.taxNumber)}
                  helperText={manualInvoiceErrors.taxNumber}
                  slotProps={{ htmlInput: { "aria-label": `${item.material.material_id} 税号` } }}
                />
                <TextField
                  label="销售方名称"
                  value={manualInvoiceFormState.sellerName}
                  onChange={(event) => {
                    updateManualInvoiceField("sellerName", event.target.value);
                  }}
                  slotProps={{ htmlInput: { "aria-label": `${item.material.material_id} 销售方名称` } }}
                />
                <TextField
                  select
                  label="费用类型"
                  aria-label={`${item.material.material_id} 费用类型`}
                  value={manualInvoiceFormState.expenseType}
                  onChange={(event) => {
                    updateManualInvoiceField("expenseType", event.target.value as ExpenseType);
                  }}
                  error={Boolean(manualInvoiceErrors.expenseType)}
                  helperText={manualInvoiceErrors.expenseType}
                  >
                    {taskAllowedExpenseTypes.map((expenseType) => (
                      <MenuItem key={expenseType} value={expenseType}>
                        {formatExpenseType(expenseType)}
                    </MenuItem>
                  ))}
                </TextField>
              </div>
              {manualInvoiceSubmitError ? (
                <p className="field-error field-error-block">{manualInvoiceSubmitError}</p>
              ) : null}
              <div className="inline-actions">
                <Button variant="outlined" type="submit" disabled={isSavingManualInvoice}>
                  {isSavingManualInvoice ? "保存中..." : "保存发票字段"}
                </Button>
              </div>
            </form>
          ) : null}
        </section>

        <section className="member-status-section">
          <div className="member-status-section-header">
            <h4>当前分摊方案与确认状态</h4>
            <StatusBadge tone="info">{item.splits.length} 条分摊</StatusBadge>
          </div>
          {invoice && task ? (
            <>
              <div className="member-status-section-header">
                <h5>调整分配对象与备注</h5>
                <StatusBadge tone={task.status === "open" ? "info" : "neutral"}>
                  {task.status === "open" ? "当前可编辑" : `当前${formatTaskStatus(task.status)}，不可编辑`}
                </StatusBadge>
              </div>
              {splitDraftRows.map((draft, index) => (
                <div key={draft.key} className="admin-form-grid">
                  <TextField
                    select
                    label={`分配对象 ${index + 1}`}
                    aria-label={`${invoice.id} 分摊行 ${index + 1} 成员`}
                    value={draft.member_id}
                    onChange={(event) => {
                      updateSplitDraft(invoice.id, draft.key, {
                        member_id: event.target.value,
                      });
                    }}
                    disabled={
                      task.status !== "open"
                      || updatingSplitInvoiceId === invoice.id
                    }
                  >
                    {task.member_ids.map((memberId) => (
                      <MenuItem key={memberId} value={memberId}>
                        {formatMemberLabel(memberId)}
                      </MenuItem>
                    ))}
                  </TextField>
                  <TextField
                    label="金额（元）"
                    type="text"
                    inputMode="decimal"
                    value={draft.amount_yuan}
                    onChange={(event) => {
                      updateSplitDraft(invoice.id, draft.key, {
                        amount_yuan: event.target.value,
                      });
                    }}
                    disabled={
                      task.status !== "open"
                      || updatingSplitInvoiceId === invoice.id
                    }
                    slotProps={{ htmlInput: { "aria-label": `${invoice.id} 分摊行 ${index + 1} 金额` } }}
                  />
                  <TextField
                    label="备注"
                    type="text"
                    value={draft.note}
                    onChange={(event) => {
                      updateSplitDraft(invoice.id, draft.key, {
                        note: event.target.value,
                      });
                    }}
                    disabled={
                      task.status !== "open"
                      || updatingSplitInvoiceId === invoice.id
                    }
                    slotProps={{ htmlInput: { "aria-label": `${invoice.id} 分摊行 ${index + 1} 备注` } }}
                  />
                  <Box sx={{ display: "flex", alignItems: "center" }}>
                    <Button
                      type="button"
                      variant="outlined"
                      onClick={() => {
                        removeSplitDraft(invoice.id, draft.key);
                      }}
                      disabled={
                        task.status !== "open"
                        || updatingSplitInvoiceId === invoice.id
                        || splitDraftRows.length <= 1
                      }
                    >
                      移除
                    </Button>
                  </Box>
                </div>
              ))}
              <div className="inline-actions">
                <Button
                  type="button"
                  variant="outlined"
                  onClick={() => {
                    addSplitDraft(invoice.id, task.member_ids);
                  }}
                  disabled={
                    task.status !== "open"
                    || updatingSplitInvoiceId === invoice.id
                  }
                >
                  新增分摊对象
                </Button>
                <Button
                  type="button"
                  variant="outlined"
                  onClick={() => {
                    void handleSplitSave(item);
                  }}
                  disabled={
                    task.status !== "open"
                    || updatingSplitInvoiceId === invoice.id
                    || (
                      item.splits.length > 0
                      && session !== null
                      && !haveSplitDraftsChanged(
                        item,
                        splitDraftRows,
                        session.actorId,
                      )
                    )
                  }
                >
                  {updatingSplitInvoiceId === invoice.id ? "保存中..." : "保存分摊方案"}
                </Button>
              </div>
              <p className="field-hint">
                {(() => {
                  const summary = summarizeSplitDrafts(splitDraftRows);
                  if (summary.hasInvalidAmount) {
                    return "请使用最多两位小数的金额格式；保存后，受影响成员需要重新确认费用。";
                  }
                  return `当前分摊合计 ${formatCurrencyFromCents(summary.totalCents)}，发票金额 ${formatCurrencyFromCents(invoice.amount_cents)}。保存后，受影响成员需要重新确认费用。`;
                })()}
              </p>
              {splitErrors[invoice.id] ? (
                <p className="field-error field-error-block">{splitErrors[invoice.id]}</p>
              ) : null}
            </>
          ) : (
            <p className="field-hint">当前材料还没有形成发票主记录，暂时无法调整金额分配对象。</p>
          )}
          {item.splits.length > 0 ? (
            <>
              <p className="field-hint">以下为当前已保存的分摊与确认状态。</p>
              <ul className="member-status-message-list" aria-label={`${item.material.material_id} 分摊列表`}>
                {item.splits.map((split) => {
                  const confirmation = item.confirmations.find((entry) => entry.split_id === split.id) ?? null;
                  return (
                    <li key={split.id}>
                      <strong>{formatMemberLabel(split.member_id)}</strong>
                      <span>分摊金额：{formatCurrencyFromCents(split.amount_cents)}</span>
                      <span>备注：{split.note ?? "无"}</span>
                      <span>确认状态：{confirmation ? formatConfirmationStatus(confirmation.status) : "待确认"}</span>
                    </li>
                  );
                })}
              </ul>
            </>
          ) : invoice ? (
            <p className="field-hint">当前还没有已保存的分摊记录，保存后会在这里显示最新确认状态。</p>
          ) : null}
          {item.relatedExpenseDetails.length > 0 && task ? (
            <p className="field-hint">
              当前发票已有 {item.relatedExpenseDetails.length} 条与你相关的费用明细，可直接在本页的
              <Button
                component={Link}
                variant="text"
                size="small"
                to={buildWorkbenchTaskAnchor(task.id, "#member-workbench-confirmations")}
                sx={{ minWidth: "auto", px: 0.75, verticalAlign: "baseline" }}
              >
                费用确认区
              </Button>
              提交确认或异议。
            </p>
          ) : null}
        </section>

        <section className="member-status-section">
          <div className="member-status-section-header">
            <h4>关联附件与缺失项</h4>
            <StatusBadge tone="info">
              附件 {item.supportingMaterials.length} 份 / 缺失 {item.missingMaterials.length} 项
            </StatusBadge>
          </div>
          {item.supportingMaterials.length > 0 ? (
            <ul className="member-status-message-list">
              {item.supportingMaterials.map((material) => (
                <li key={material.id}>
                  <strong>{formatMaterialType(material.material_type)} / {material.original_filename}</strong>
                  <span>上传时间：{formatDateTime(material.created_at)}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="field-hint">当前这张发票还没有已关联的辅助材料。</p>
          )}
          {item.missingMaterials.length > 0 ? (
            <ul className="member-status-message-list" aria-label={`${item.material.material_id} 缺失材料列表`}>
              {item.missingMaterials.map((missingMaterial) => (
                <li key={`${missingMaterial.invoice_id}:${missingMaterial.required_material_type}:${missingMaterial.source_rule_code}`}>
                  <strong>{formatMaterialType(missingMaterial.required_material_type)}</strong>
                  <span>{missingMaterial.message}</span>
                </li>
              ))}
            </ul>
          ) : null}
        </section>

        <section className="member-status-section">
          <div className="member-status-section-header">
            <h4>下一步动作</h4>
            <StatusBadge tone="info">优先留在当前工作台</StatusBadge>
          </div>
          <div className="inline-actions">
            {task ? (
              <>
                <Button component={Link} variant="outlined" size="small" to={buildWorkbenchTaskAnchor(task.id, "#member-workbench-upload")}>
                  去上传区补材料
                </Button>
                <Button component={Link} variant="outlined" size="small" to={buildWorkbenchTaskAnchor(task.id, "#member-workbench-confirmations")}>
                  去确认区处理
                </Button>
                <Button component={Link} variant="outlined" size="small" to={buildWorkbenchTaskAnchor(task.id, "#member-workbench-invoices")}>
                  回到当前发票列表
                </Button>
              </>
            ) : null}
          </div>
        </section>
      </>
    );
  }

  function renderSelectedSharedWorkbenchInvoice(item: TaskSharedInvoiceItem) {
    return (
      <>
        <div className="member-status-section-header">
          <div>
            <p className="task-card-id">共享摘要 / {item.invoice_id}</p>
            <h2>{item.invoice_number}</h2>
          </div>
          <StatusBadge tone="info">{formatExpenseType(item.expense_type)}</StatusBadge>
        </div>

        <dl className="task-meta-grid member-status-meta-grid">
          <div>
            <dt>上传成员</dt>
            <dd>{item.submitter_id ? formatMemberLabel(item.submitter_id) : "未记录"}</dd>
          </div>
          <div>
            <dt>发票金额</dt>
            <dd>{formatCurrencyFromCents(item.amount_cents)}</dd>
          </div>
          <div>
            <dt>开票日期</dt>
            <dd>{item.issue_date ?? "未填写"}</dd>
          </div>
          <div>
            <dt>最近更新</dt>
            <dd>{formatDateTime(item.updated_at)}</dd>
          </div>
        </dl>

        <section className="member-status-section">
          <div className="member-status-section-header">
            <h4>基础元数据</h4>
            <StatusBadge tone="info">只读摘要</StatusBadge>
          </div>
          <ul className="member-status-message-list">
            <li>
              <strong>发票抬头</strong>
              <span>{item.buyer_name}</span>
            </li>
            <li>
              <strong>销售方</strong>
              <span>{item.seller_name ?? "未填写"}</span>
            </li>
          </ul>
        </section>

        <section className="member-status-section">
          <div className="member-status-section-header">
            <h4>当前分摊去向</h4>
            <StatusBadge tone="info">{item.splits.length} 条</StatusBadge>
          </div>
          {item.splits.length > 0 ? (
            <ul className="member-status-message-list">
              {item.splits.map((split) => (
                <li key={`${item.invoice_id}:${split.member_id}`}>
                  <strong>{formatMemberLabel(split.member_id)}</strong>
                  <span>{formatCurrencyFromCents(split.amount_cents)}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="field-hint">当前还没有已保存的分摊方案。</p>
          )}
        </section>

        <section className="member-status-section">
          <div className="member-status-section-header">
            <h4>必要附件摘要</h4>
            <StatusBadge tone="info">{item.supporting_materials.length} 类</StatusBadge>
          </div>
          <p className="field-hint">{formatSupportingMaterialSummary(item)}</p>
        </section>
      </>
    );
  }

  if (!session || session.role !== "member") {
    return null;
  }

  return (
    <RoleWorkspace
      header={(
        <PageHeader
          eyebrow="成员材料提交"
          title="比赛报销材料提交"
          description="先批量上传发票、车票、住宿凭证、支付截图和比赛通知；系统生成报销草稿后，你只处理需要确认的事项。"
          meta={`当前成员：${session.displayName}${session.memberCode ? `（${session.memberCode}）` : ""}`}
          actions={(
            <div className="page-actions">
              <Button component={Link} variant="outlined" to="/member">
                返回任务列表
              </Button>
            </div>
          )}
        />
      )}
      summary={summaryStats.length > 0 ? (
        <section className="stat-grid" aria-label="成员发票工作台摘要">
          {summaryStats.map((item) => (
            <StatCard
              key={item.label}
              label={item.label}
              value={item.value}
              description={item.description}
            />
          ))}
        </section>
      ) : undefined}
    >
      {taskState.status === "loading" ? (
        <SectionCard title="正在加载成员任务" description="正在读取你参与的报销任务，请稍候。" />
      ) : null}

      {taskState.status === "error" ? <ApiErrorNotice error={taskState.error} /> : null}
      {workbenchState.status === "error" ? <ApiErrorNotice error={workbenchState.error} /> : null}

      {taskState.status === "ready" && visibleTasks.length === 0 ? (
        <EmptyState
          title="当前没有可处理的报销任务"
          description="管理员创建并发布包含你的报销任务后，会在这里显示。"
        />
      ) : null}

      {taskState.status === "ready" && visibleTasks.length > 0 ? (
        <SectionCard
          title="比赛报销项目"
          description="确认当前处理的是哪场比赛；发票抬头和税号会用于系统自动核对。"
          action={selectedTask ? <StatusBadge tone="info">{formatTaskStatus(selectedTask.status)}</StatusBadge> : null}
        >
          <div className="admin-form-grid">
            <TextField
              select
              label="目标任务"
              aria-label="目标任务"
              value={selectedTaskId}
              onChange={(event) => {
                handleTaskChange(event.target.value);
              }}
            >
              {visibleTasks.map((task) => (
                <MenuItem key={task.id} value={task.id}>
                  {task.competition_name}（{task.id}）
                </MenuItem>
              ))}
            </TextField>
            {selectedTask ? (
              <dl className="task-meta-grid member-status-meta-grid">
                <div>
                  <dt>比赛名称</dt>
                  <dd>{selectedTask.competition_name}</dd>
                </div>
                <div>
                  <dt>比赛时间</dt>
                  <dd>{formatTaskDateRange(selectedTask)}</dd>
                </div>
                <div>
                  <dt>比赛地点</dt>
                  <dd>{selectedTask.competition_location}</dd>
                </div>
                <div>
                  <dt>报销截止时间</dt>
                  <dd>{formatDateTime(selectedTask.deadline)}</dd>
                </div>
                <div>
                  <dt>参赛成员</dt>
                  <dd>{selectedTask.member_ids.map((memberId) => formatMemberLabel(memberId)).join("、")}</dd>
                </div>
                <div>
                  <dt>发票抬头</dt>
                  <dd>{selectedTask.invoice_title}</dd>
                </div>
                <div>
                  <dt>税号</dt>
                  <dd>{selectedTask.tax_number}</dd>
                </div>
              </dl>
            ) : null}
          </div>
        </SectionCard>
      ) : null}

      {selectedTask && workbenchState.status === "loading" ? (
        <SectionCard title="正在汇总当前任务" description="正在整理你的材料、识别结果、金额分配和确认状态。" />
      ) : null}

      {workbenchState.status === "ready" ? (
        <SectionCard
          title="需要你处理的事项"
          description="系统只把无法自动判断、材料缺失或存在冲突的事项列出来。"
          action={(
            <StatusBadge tone={pendingActionCount > 0 ? (abnormalCount > 0 ? "warning" : "info") : "success"}>
              {pendingActionCount > 0 ? `${pendingActionCount} 项仍待处理` : "当前无明显异常"}
            </StatusBadge>
          )}
        >
          <ul className="error-detail-list" aria-label="待处理事项列表">
            {pendingActions.map((action) => (
              <li key={action.id}>
                <strong>{action.title}</strong>
                <span>{action.detail}</span>
                <Button component={Link} variant="text" size="small" to={action.to} sx={{ justifyContent: "flex-start", width: "fit-content", px: 0 }}>
                  {action.label}
                </Button>
              </li>
            ))}
          </ul>
        </SectionCard>
      ) : null}

      {selectedTask && activeTab === "invoices" ? (
        <div id="member-workbench-upload">
          <SectionCard
            title="上传报销材料"
            description="将发票、车票、住宿凭证、支付截图拖到这里。上传后系统会自动识别类型、金额、日期、费用类别和归属建议。"
            action={(
              <StatusBadge tone={selectedTask.status === "open" ? "info" : "neutral"}>
                {selectedTask.status === "open" ? "当前可补交" : `当前${formatTaskStatus(selectedTask.status)}，不可补交`}
              </StatusBadge>
            )}
          >
            {selectedTask.status === "open" ? (
              <form
                className="page-stack"
                onSubmit={(event) => {
                  void handleUploadSubmit(event);
                }}
                noValidate
              >
                <div className="page-stack">
                  <Box>
                    <FileDropZone
                      files={uploadFormState.files}
                      onChange={(files) => {
                        updateUploadField("files", files);
                      }}
                      accept={MATERIAL_FILE_ACCEPT}
                      disabled={isUploading}
                      ariaLabel="工作台上传文件"
                      fileListAriaLabel="工作台待上传文件列表"
                      hint="将发票、车票、住宿凭证、支付截图拖到这里；支持一次选择多个文件，单文件最大 10MB。"
                    />
                    {uploadValidationErrors.files ? (
                      <Typography color="error" variant="body2" sx={{ mt: 1 }}>
                        {uploadValidationErrors.files}
                      </Typography>
                    ) : null}
                  </Box>
                </div>

                {isUploading ? <LinearProgress aria-label="工作台上传进度" /> : null}

                <div className="admin-form-footer">
                  <p className="field-hint">
                    上传后无需先填写完整报销表单；系统会先生成草稿，再把需要你确认的地方列出来。
                  </p>
                  <Button variant="contained" type="submit" disabled={isUploading}>
                    {isUploading ? "正在上传..." : "选择文件并上传"}
                  </Button>
                </div>
              </form>
            ) : (
              <p className="field-hint">
                当前任务已不在开放提交阶段。若仍需补材料，请根据下面的异常提示联系管理员重新开放任务，或使用专项页面查看历史记录。
              </p>
            )}
          </SectionCard>
        </div>
      ) : null}

      {activeTab === "invoices" && uploadSubmitError ? <ApiErrorNotice error={uploadSubmitError} /> : null}

      {activeTab === "invoices" && uploadResult ? (
        <SectionCard
          title="最近上传处理状态"
          description="这里不仅保留逐文件上传结果，还会继续展示系统对这批材料的识别、归票和后续待办状态。"
          action={(
            <div className="inline-actions">
              <StatusBadge tone={uploadResult.status === "failed" ? "warning" : "success"}>
                {uploadResult.status === "success"
                  ? "全部成功"
                  : uploadResult.status === "partial_success"
                    ? "部分成功"
                    : "全部失败"}
              </StatusBadge>
              <Button
                type="button"
                variant="outlined"
                size="small"
                onClick={() => {
                  setWorkbenchReloadVersion((current) => current + 1);
                }}
              >
                刷新处理状态
              </Button>
            </div>
          )}
        >
          {formatRecognitionDispatchMessage(uploadResult.recognition_dispatch) ? (
            <p className="field-hint">{formatRecognitionDispatchMessage(uploadResult.recognition_dispatch)}</p>
          ) : null}
          {canAutoRefreshRecentUploadStatus ? (
            <>
              <LinearProgress aria-label="工作台上传处理状态刷新中" sx={{ mb: 1.5 }} />
              <p className="field-hint">
                系统正在自动刷新这批材料的识别和归票状态；下面的待处理事项会随状态变化同步更新。
              </p>
            </>
          ) : null}
          {!canAutoRefreshRecentUploadStatus
          && hasRecentUploadTransitioningItems
          && uploadProcessingRefreshAttempts >= RECENT_UPLOAD_AUTO_REFRESH_MAX_ATTEMPTS ? (
            <p className="field-hint">
              这批材料仍在自动处理中；可稍后手动刷新查看最新状态。
            </p>
          ) : null}
          {uploadResult.items.length > 0 ? (
            <ul className="member-status-message-list" aria-label="工作台上传成功列表">
              {uploadResult.items.map((item, index) => {
                const snapshot = recentUploadProcessingSnapshots[index];
                return (
                <li key={item.id}>
                  <strong>{item.original_filename}</strong>
                  <span>材料类型：{formatMaterialType(item.material_type)}</span>
                  <span>{item.duplicate_of ? `重复文件：${item.duplicate_of}` : "已归档到当前任务"}</span>
                  {snapshot ? (
                    <>
                      <span>当前阶段：{snapshot.label}</span>
                      <span>处理轨迹：{snapshot.steps.map((step) => UPLOAD_PROCESSING_STAGE_LABELS[step]).join(" -> ")}</span>
                      <span>{snapshot.detail}</span>
                      {snapshot.actionLabel && snapshot.actionHref ? (
                        <Button
                          component={Link}
                          variant="outlined"
                          size="small"
                          to={snapshot.actionHref}
                        >
                          {snapshot.actionLabel}
                        </Button>
                      ) : null}
                    </>
                  ) : null}
                </li>
                );
              })}
            </ul>
          ) : (
            <p className="field-hint">本次没有成功归档的新材料。</p>
          )}

          {uploadResult.failures && uploadResult.failures.length > 0 ? (
            <ul className="member-status-message-list" aria-label="工作台上传失败列表">
              {uploadResult.failures.map((failure) => (
                <li key={`${failure.original_filename ?? "unknown"}:${failure.error_code}`}>
                  <strong>{failure.original_filename ?? "未命名文件"}</strong>
                  <span>{failure.error_code}</span>
                  <span>{failure.detail}</span>
                </li>
              ))}
            </ul>
          ) : null}
        </SectionCard>
      ) : null}

      {workbenchState.status === "ready" && activeTab === "invoices" ? (
        <SectionCard
          title="识别结果"
          description="系统已按状态整理材料，优先展示需要你确认的内容；正常材料默认只显示摘要。"
          action={<StatusBadge tone="info">{workbenchState.items.length} 份材料</StatusBadge>}
        >
          <div className="page-stack">
            {materialResultGroups.map((group) => (
              <section key={group.key} className="member-status-section" aria-label={`${group.title} 材料列表`}>
                <div className="member-status-section-header">
                  <div>
                    <h4>{group.title}</h4>
                    <p className="field-hint">{group.description}</p>
                  </div>
                  <StatusBadge tone={group.items.length > 0 ? group.tone : "neutral"}>{group.items.length} 份</StatusBadge>
                </div>
                {group.items.length > 0 ? (
                  <ul className="invoice-material-list" aria-label={`${group.title} 材料卡片`}>
                    {group.items.map((item) => renderMaterialResultCard(item, group))}
                  </ul>
                ) : (
                  <p className="field-hint">当前没有这一类材料。</p>
                )}
              </section>
            ))}
          </div>
        </SectionCard>
      ) : null}

      {workbenchState.status === "ready" && activeTab === "invoices" && draftSummary ? (
        <SectionCard
          title="报销草稿汇总"
          description="金额会随识别结果、分摊和确认状态自动更新。"
        >
          <dl className="task-meta-grid member-status-meta-grid">
            <div>
              <dt>当前已识别总金额</dt>
              <dd>{formatCurrencyFromCents(draftSummary.recognizedAmountCents)}</dd>
            </div>
            <div>
              <dt>待确认金额</dt>
              <dd>{formatCurrencyFromCents(draftSummary.pendingConfirmationAmountCents)}</dd>
            </div>
            <div>
              <dt>缺失材料数量</dt>
              <dd>{draftSummary.missingMaterialCount}</dd>
            </div>
            <div>
              <dt>风险项数量</dt>
              <dd>{draftSummary.riskItemCount}</dd>
            </div>
          </dl>
          <section className="member-status-section">
            <div className="member-status-section-header">
              <h4>每位成员金额</h4>
              <StatusBadge tone={draftSummary.memberAmountsCents.size > 0 ? "info" : "neutral"}>
                {draftSummary.memberAmountsCents.size} 人
              </StatusBadge>
            </div>
            {draftSummary.memberAmountsCents.size > 0 ? (
              <ul className="member-status-message-list" aria-label="每位成员金额">
                {[...draftSummary.memberAmountsCents.entries()].map(([memberId, amountCents]) => (
                  <li key={memberId}>
                    <strong>{formatMemberLabel(memberId)}</strong>
                    <span>{formatCurrencyFromCents(amountCents)}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="field-hint">系统还没有形成成员金额分配。</p>
            )}
          </section>
        </SectionCard>
      ) : null}

      {workbenchState.status === "ready" && activeTab === "invoices" ? (
        <SectionCard
          title="提交确认"
          description="所有必要项确认后，再把报销草稿提交给管理员审核。"
          action={(
            <StatusBadge tone={canSubmitReimbursementConfirmation ? "success" : "warning"}>
              {canSubmitReimbursementConfirmation ? "可以提交" : "暂不能提交"}
            </StatusBadge>
          )}
        >
          {submitBlockers.length > 0 ? (
            <>
              <p className="field-hint">还需要处理以下事项后才能提交：</p>
              <ul className="member-status-message-list" aria-label="提交阻塞原因">
                {submitBlockers.map((blocker) => (
                  <li key={blocker}>{blocker}</li>
                ))}
              </ul>
            </>
          ) : (
            <p className="field-hint">当前没有阻塞项，可以提交给管理员审核。</p>
          )}
          <div className="inline-actions">
            <Button
              type="button"
              variant="contained"
              disabled={!canSubmitReimbursementConfirmation || runningInvoiceBatchAction !== null}
              onClick={handleSubmitReimbursementConfirmation}
            >
              {runningInvoiceBatchAction === "submit" ? "正在提交..." : "提交报销确认"}
            </Button>
          </div>
          {invoiceBatchActionError ? <ApiErrorNotice error={invoiceBatchActionError} /> : null}
          {invoiceBatchActionFeedback ? (
            <p className="field-hint">{buildInvoiceBatchFeedbackMessage(invoiceBatchActionFeedback)}</p>
          ) : null}
        </SectionCard>
      ) : null}

      {workbenchState.status === "ready" ? (
        <SectionCard
          title="高级处理"
          description="低频操作集中在这里：查看发票详情、补充缺失材料或确认个人费用。"
        >
          <Tabs
            value={activeTab}
            onChange={handleTabChange}
            aria-label="成员单任务工作台标签页"
            sx={{ borderBottom: 1, borderColor: "divider" }}
          >
            <Tab value="invoices" label="材料详情" id="member-workbench-tab-invoices" />
            <Tab value="missing-materials" label="缺失材料" id="member-workbench-tab-missing-materials" />
            <Tab value="confirmations" label="费用确认" id="member-workbench-tab-confirmations" />
          </Tabs>
        </SectionCard>
      ) : null}

      {workbenchState.status === "ready" && activeTab === "confirmations" ? (
        <div id="member-workbench-confirmations">
          <SectionCard
            title="确认当前分到本人名下的费用"
            description="确认动作现在直接留在当前任务工作台中；先看下面的识别和分摊上下文，再在这里提交确认或异议。"
            action={(
              <StatusBadge tone={confirmationItems.some((item) => getCurrentConfirmationStatus(item.detail) === "pending") ? "warning" : "success"}>
                待确认 {confirmationItems.filter((item) => getCurrentConfirmationStatus(item.detail) === "pending").length} 条
              </StatusBadge>
            )}
          >
            {confirmationSubmitError ? <ApiErrorNotice error={confirmationSubmitError} /> : null}

            {confirmationItems.length === 0 ? (
              <p className="field-hint">当前任务下还没有分配到你名下、需要你处理的费用确认项。</p>
            ) : (
              <section className="member-confirmation-list" aria-label="工作台费用确认列表">
                {confirmationItems.map((item) => {
                  const currentStatus = getCurrentConfirmationStatus(item.detail);
                  const disputeReason = disputeReasons[item.detail.split_id] ?? "";
                  const disputeError = disputeErrors[item.detail.split_id];
                  const isSubmitting = submittingConfirmationSplitId === item.detail.split_id;
                  const isStale = staleConfirmationSplitId === item.detail.split_id;
                  const hasFeedback = confirmationFeedback?.splitId === item.detail.split_id;

                  return (
                    <article key={item.detail.split_id} className="status-card member-confirmation-card">
                      <div className="member-status-section-header">
                        <div>
                          <p className="task-card-id">费用明细 {item.detail.split_id}</p>
                          <h2>{item.detail.invoice.invoice_number}</h2>
                        </div>
                        <StatusBadge tone={currentStatus === "confirmed" ? "success" : currentStatus === "disputed" ? "danger" : "warning"}>
                          {formatConfirmationStatus(currentStatus)}
                        </StatusBadge>
                      </div>

                      <dl className="task-meta-grid member-status-meta-grid">
                        <div>
                          <dt>归属金额</dt>
                          <dd>{formatCurrencyFromCents(item.detail.amount_cents)}</dd>
                        </div>
                        <div>
                          <dt>发票总额</dt>
                          <dd>{formatCurrencyFromCents(item.detail.invoice.amount_cents)}</dd>
                        </div>
                        <div>
                          <dt>费用类型</dt>
                          <dd>{formatExpenseType(item.detail.invoice.expense_type)}</dd>
                        </div>
                        <div>
                          <dt>确认状态</dt>
                          <dd>{formatConfirmationStatus(currentStatus)}</dd>
                        </div>
                        <div>
                          <dt>关联附件</dt>
                          <dd>{item.supportingMaterials.length} 份</dd>
                        </div>
                        <div>
                          <dt>成员备注</dt>
                          <dd>{item.detail.note ?? "无"}</dd>
                        </div>
                      </dl>

                      <TextField
                        label="异议原因"
                        aria-label={`工作台异议原因 ${item.detail.split_id}`}
                        value={disputeReason}
                        placeholder="如果金额、归属或附件关联不正确，请写明原因。"
                        onChange={(event) => {
                          const nextValue = event.target.value;
                          setDisputeReasons((current) => ({
                            ...current,
                            [item.detail.split_id]: nextValue,
                          }));
                          setDisputeErrors((current) => {
                            if (!(item.detail.split_id in current)) {
                              return current;
                            }
                            const next = { ...current };
                            delete next[item.detail.split_id];
                            return next;
                          });
                        }}
                        error={Boolean(disputeError)}
                        helperText={disputeError}
                        multiline
                        minRows={3}
                        fullWidth
                      />

                      <div className="inline-actions">
                        <Button
                          type="button"
                          variant="contained"
                          disabled={isSubmitting}
                          onClick={() => {
                            void handleConfirmationSubmit(item, "confirmed");
                          }}
                        >
                          {isSubmitting ? "提交中..." : "确认这笔费用"}
                        </Button>
                        <Button
                          type="button"
                          variant="outlined"
                          disabled={isSubmitting}
                          onClick={() => {
                            void handleConfirmationSubmit(item, "disputed");
                          }}
                        >
                          {isSubmitting ? "提交中..." : "提交异议"}
                        </Button>
                        <Button
                          component={Link}
                          variant="outlined"
                          to={buildWorkbenchTaskAnchor(workbenchState.task.id, `#workbench-invoice-${item.detail.invoice.id}`)}
                        >
                          查看对应发票上下文
                        </Button>
                        {isStale ? (
                          <Button
                            type="button"
                            variant="outlined"
                            onClick={() => {
                              setStaleConfirmationSplitId(null);
                              setWorkbenchReloadVersion((current) => current + 1);
                            }}
                          >
                            重新加载明细
                          </Button>
                        ) : null}
                      </div>

                      {hasFeedback ? (
                        <p className="confirmation-feedback">
                          {confirmationFeedback.status === "confirmed" ? "已提交确认，工作台已刷新最新确认状态。" : "已提交异议，工作台已刷新最新确认状态。"}
                        </p>
                      ) : null}
                      {isStale ? (
                        <p className="field-error-block">
                          当前费用明细版本已失效，通常是管理员刚修改了分摊金额或成员归属；请刷新后再确认。
                        </p>
                      ) : null}
                    </article>
                  );
                })}
              </section>
            )}
          </SectionCard>
        </div>
      ) : null}

      {workbenchState.status === "ready" && activeTab === "invoices" && workbenchState.items.length === 0 && sharedInvoices.length === 0 && pendingSupportingMaterialLinkageItems.length === 0 ? (
        <EmptyState
          title="当前任务下还没有可查看的发票"
          description="先上传本人发票材料，或者等待任务内其他成员产生可共享查看的发票摘要。"
          action={(
            <Button component={Link} variant="contained" to={buildWorkbenchTaskAnchor(workbenchState.task.id, "#member-workbench-upload")}>
              去上传区
            </Button>
          )}
        />
      ) : null}

      {workbenchState.status === "ready" && activeTab === "invoices" && (workbenchState.items.length > 0 || sharedInvoices.length > 0 || pendingSupportingMaterialLinkageItems.length > 0) ? (
        <section id="member-workbench-invoices" className="page-stack">
          <SectionCard
            title="成员提交队列"
            description="第一屏先看哪些发票已经可以提交、哪些仍被具体问题阻塞；只有在需要修正时再展开详情。"
            action={(
              <StatusBadge tone={problemInvoiceCount > 0 ? "warning" : "success"}>
                {problemInvoiceCount > 0 ? `${problemInvoiceCount} 张仍待处理` : "当前可提交结构稳定"}
              </StatusBadge>
            )}
          >
            <div className="admin-form-header">
              <div>
                <p className="eyebrow">Invoice Queue</p>
                <h2>可提交与问题发票分组</h2>
              </div>
              <StatusBadge tone="info">
                本人 {workbenchState.items.length} 张 / 共享 {sharedInvoices.length} 张
              </StatusBadge>
            </div>
            <p className="field-hint">
              默认不再要求你先钻进某一张票的完整详情；先看下面的分组，再决定要展开处理哪一张。
            </p>

            <section
              id="member-workbench-batch-submission"
              className="member-status-section"
              aria-label="批量提交与撤回区"
            >
              <div className="member-status-section-header">
                <div>
                  <h4>批量提交与撤回</h4>
                  <p className="field-hint">
                    这里专门处理“把哪些发票正式交给管理员”和“在管理员进入后续阶段前撤回自己刚提交的发票”。
                  </p>
                </div>
                <StatusBadge tone={selectedBatchInvoiceItems.length > 0 ? "info" : "neutral"}>
                  已选 {selectedBatchInvoiceItems.length} 张
                </StatusBadge>
              </div>
              <dl className="task-meta-grid member-status-meta-grid">
                <div>
                  <dt>本人发票</dt>
                  <dd>{ownInvoiceItems.length} 张</dd>
                </div>
                <div>
                  <dt>已选发票</dt>
                  <dd>{selectedBatchInvoiceItems.length} 张</dd>
                </div>
                <div>
                  <dt>已提交</dt>
                  <dd>{selectedSubmittedInvoiceCount} 张</dd>
                </div>
                <div>
                  <dt>未提交</dt>
                  <dd>{selectedUnsubmittedInvoiceCount} 张</dd>
                </div>
                <div>
                  <dt>任务状态</dt>
                  <dd>{formatTaskStatus(workbenchState.task.status)}</dd>
                </div>
              </dl>
              <div className="inline-actions">
                <Button
                  type="button"
                  variant="outlined"
                  size="small"
                  disabled={ownInvoiceItems.length === 0 || allOwnInvoicesSelected}
                  onClick={handleBatchSelectAllInvoices}
                >
                  选择全部本人发票
                </Button>
                <Button
                  type="button"
                  variant="outlined"
                  size="small"
                  disabled={selectedBatchInvoiceItems.length === 0}
                  onClick={handleBatchClearInvoiceSelection}
                >
                  清空选择
                </Button>
              </div>
              <div className="inline-actions">
                <Button
                  type="button"
                  variant="contained"
                  disabled={selectedBatchInvoiceItems.length === 0 || runningInvoiceBatchAction !== null || workbenchState.task.status !== "open"}
                  onClick={() => {
                    void handleInvoiceBatchAction("submit");
                  }}
                >
                  {runningInvoiceBatchAction === "submit" ? "批量提交中..." : "批量提交选中发票"}
                </Button>
                <Button
                  type="button"
                  variant="outlined"
                  disabled={selectedBatchInvoiceItems.length === 0 || runningInvoiceBatchAction !== null || workbenchState.task.status !== "open"}
                  onClick={() => {
                    void handleInvoiceBatchAction("withdraw");
                  }}
                >
                  {runningInvoiceBatchAction === "withdraw" ? "批量撤回中..." : "批量撤回选中发票"}
                </Button>
              </div>
              {workbenchState.task.status !== "open" ? (
                <p className="field-hint">
                  当前任务已不在开放提交阶段，因此成员不能再批量提交或撤回；如需调整，请联系管理员重新开放任务。
                </p>
              ) : null}
              {invoiceBatchActionError ? <ApiErrorNotice error={invoiceBatchActionError} /> : null}
              {invoiceBatchActionFeedback ? (
                <div className="page-stack">
                  <p className="field-hint">{buildInvoiceBatchFeedbackMessage(invoiceBatchActionFeedback)}</p>
                  {invoiceBatchActionFeedback.failures.length > 0 ? (
                    <ul className="member-status-message-list" aria-label="批量提交与撤回失败原因列表">
                      {invoiceBatchActionFeedback.failures.map((failure) => (
                        <li key={`${invoiceBatchActionFeedback.action}:${failure.invoice_id}:${failure.error_code}`}>
                          {buildInvoiceBatchFailureMessage(failure, workbenchState.items)}
                        </li>
                      ))}
                    </ul>
                  ) : null}
                </div>
              ) : null}
            </section>

            <section className="member-status-section" aria-label="可提交发票列表">
              <div className="member-status-section-header">
                <div>
                  <h4>可提交发票</h4>
                  <p className="field-hint">
                    {workbenchState.task.status === "open"
                      ? "这些发票当前没有识别、附件、分摊或确认问题，可以直接纳入批量提交。"
                      : "这些发票的结构已经闭合，但当前任务状态不允许成员继续提交或撤回。"}
                  </p>
                </div>
                <StatusBadge tone={readyInvoiceItems.length > 0 ? "success" : "neutral"}>
                  {readyInvoiceItems.length} 张
                </StatusBadge>
              </div>
              {readyInvoiceItems.length > 0 ? (
                <ul className="invoice-material-list" aria-label="可提交发票卡片列表">
                  {readyInvoiceItems.map((item) => renderOwnWorkbenchQueueCard(item, "可提交发票"))}
                </ul>
              ) : (
                <p className="field-hint">当前还没有可直接提交的发票；先处理下面的问题分组。</p>
              )}
            </section>

            <section className="member-status-section" aria-label="问题发票分组">
              <div className="member-status-section-header">
                <div>
                  <h4>问题发票</h4>
                  <p className="field-hint">
                    这里按当前最主要的阻塞原因分组，避免继续在长列表里自己判断哪张票为什么不能提交。
                  </p>
                </div>
                <StatusBadge tone={problemInvoiceCount > 0 ? "warning" : "success"}>
                  {problemInvoiceCount > 0 ? `${problemInvoiceCount} 张` : "当前无问题发票"}
                </StatusBadge>
              </div>
              {problemInvoiceSections.length > 0 ? (
                <div className="page-stack">
                  {problemInvoiceSections.map((section) => (
                    <section
                      key={section.key}
                      className="member-status-section member-workbench-subsection"
                      aria-label={`${section.title} 分组`}
                    >
                      <div className="member-status-section-header">
                        <div>
                          <h4>{section.title}</h4>
                          <p className="field-hint">{section.description}</p>
                        </div>
                        <StatusBadge tone={section.tone}>{section.items.length} 张</StatusBadge>
                      </div>
                      <ul className="invoice-material-list" aria-label={`${section.title} 发票列表`}>
                        {section.items.map((item) => renderOwnWorkbenchQueueCard(item, section.title))}
                      </ul>
                    </section>
                  ))}
                </div>
              ) : (
                <p className="field-hint">当前没有识别或校验阻塞的发票；可以直接从上面的可提交区处理。</p>
              )}
            </section>

            {pendingSupportingMaterialLinkageItems.length > 0 ? (
              <section
                id="member-workbench-pending-linkage"
                className="member-status-section"
                aria-label="待关联辅助材料列表"
              >
                <div className="member-status-section-header">
                  <div>
                    <h4>待关联辅助材料</h4>
                    <p className="field-hint">
                      这些材料还没有安全归到某张发票，因此不会算作已补齐附件；这里会明确告诉你为什么没自动关联，以及下一步该看哪张票。
                    </p>
                  </div>
                  <StatusBadge tone="warning">{pendingSupportingMaterialLinkageItems.length} 份</StatusBadge>
                </div>
                <ul className="member-status-message-list">
                  {pendingSupportingMaterialLinkageItems.map((item) => (
                    <li key={item.material_id}>
                      {(() => {
                        const hasRunningAction = runningPendingSupportingMaterialLinkageActionKey?.startsWith(`${item.material_id}:`) ?? false;
                        return (
                          <>
                            <strong>{formatMaterialType(item.material_type)} / {item.original_filename}</strong>
                            <span>{formatPendingSupportingMaterialLinkageReason(item.pending_reason)}</span>
                            {item.candidate_invoices.length > 0 ? (
                              <span>
                                候选发票：
                                {item.candidate_invoices.map((candidate) => (
                                  `${candidate.invoice_number}（${formatExpenseType(candidate.expense_type)} / ${formatCurrencyFromCents(candidate.amount_cents)}）`
                                )).join("；")}
                              </span>
                            ) : (
                              <span>当前没有候选发票；通常意味着你还没有创建对应发票，或材料提交人与现有发票不匹配。</span>
                            )}
                            <span>上传时间：{formatDateTime(item.created_at)}</span>
                            <div className="inline-actions">
                              {item.pending_reason === "no_candidate" ? (
                                <Button
                                  component={Link}
                                  variant="outlined"
                                  size="small"
                                  to={buildWorkbenchTaskAnchor(workbenchState.task.id, "#member-workbench-upload")}
                                >
                                  去上传区补录或补传发票
                                </Button>
                              ) : null}
                              {item.candidate_invoices.map((candidate) => {
                                const actionKey = buildPendingSupportingMaterialLinkageActionKey({
                                  materialId: item.material_id,
                                  invoiceId: candidate.invoice_id,
                                });
                                const isRunning = runningPendingSupportingMaterialLinkageActionKey === actionKey;
                                return (
                                  <Button
                                    key={`attach:${item.material_id}:${candidate.invoice_id}`}
                                    type="button"
                                    variant="contained"
                                    size="small"
                                    disabled={hasRunningAction}
                                    onClick={() => {
                                      void handlePendingSupportingMaterialAttach(
                                        item,
                                        candidate.invoice_id,
                                        candidate.invoice_number,
                                      );
                                    }}
                                  >
                                    {isRunning ? `关联中 ${candidate.invoice_number}...` : `关联到发票 ${candidate.invoice_number}`}
                                  </Button>
                                );
                              })}
                              {item.candidate_invoices.map((candidate) => (
                                <Button
                                  key={`view:${item.material_id}:${candidate.invoice_id}`}
                                  type="button"
                                  variant="outlined"
                                  size="small"
                                  disabled={hasRunningAction}
                                  onClick={() => {
                                    handlePendingSupportingMaterialCandidateSelect(candidate.invoice_id);
                                  }}
                                >
                                  查看候选发票 {candidate.invoice_number}
                                </Button>
                              ))}
                            </div>
                            {pendingSupportingMaterialLinkageErrors[item.material_id] ? (
                              <p className="field-error field-error-block">
                                {pendingSupportingMaterialLinkageErrors[item.material_id]}
                              </p>
                            ) : null}
                          </>
                        );
                      })()}
                    </li>
                  ))}
                </ul>
              </section>
            ) : null}

            {sharedInvoices.length > 0 ? (
              <>
                <div className="member-status-section-header">
                  <h4>任务内其他成员已上传发票</h4>
                  <StatusBadge tone="info">{sharedInvoices.length} 张</StatusBadge>
                </div>
                <p className="field-hint">
                  这里仅共享发票基础信息、当前分摊去向和必要附件摘要；不提供原始文件下载或支付截图全文。
                </p>
                <ul className="invoice-material-list" aria-label="共享发票选择列表">
                  {sharedInvoices.map((item) => {
                    const isSelected = resolvedInvoiceWorkbenchKey === buildInvoiceWorkbenchSelectionKey({
                      kind: "shared",
                      invoiceId: item.invoice_id,
                    });
                    return (
                      <li key={item.invoice_id}>
                        <button
                          type="button"
                          className={`invoice-material-button ${isSelected ? "invoice-material-button-selected" : ""}`}
                          aria-pressed={isSelected}
                          onClick={() => {
                            setSelectedInvoiceWorkbenchKey(buildInvoiceWorkbenchSelectionKey({
                              kind: "shared",
                              invoiceId: item.invoice_id,
                            }));
                          }}
                        >
                          <div className="task-card-header">
                            <div>
                              <p className="task-card-id">共享摘要 / {item.invoice_id}</p>
                              <h3>{item.invoice_number}</h3>
                            </div>
                            <StatusBadge tone="info">{formatExpenseType(item.expense_type)}</StatusBadge>
                          </div>
                          <dl className="task-meta-grid invoice-editor-summary-grid">
                            <div>
                              <dt>上传成员</dt>
                              <dd>{item.submitter_id ? formatMemberLabel(item.submitter_id) : "未记录"}</dd>
                            </div>
                            <div>
                              <dt>发票金额</dt>
                              <dd>{formatCurrencyFromCents(item.amount_cents)}</dd>
                            </div>
                            <div>
                              <dt>分摊记录</dt>
                              <dd>{item.splits.length} 条</dd>
                            </div>
                            <div>
                              <dt>附件摘要</dt>
                              <dd>{formatSupportingMaterialSummary(item)}</dd>
                            </div>
                          </dl>
                        </button>
                      </li>
                    );
                  })}
                </ul>
              </>
            ) : null}
          </SectionCard>

          <SectionCard
            title="展开的发票详情"
            description="只有在需要更正字段、处理附件、调整分摊或确认时，才继续查看这一层完整上下文。"
          >
            <article
              className="status-card admin-form-card admin-review-detail-panel"
              id={selectedInvoiceDetailAnchorId}
              aria-label="成员发票工作台列表"
            >
              {selectedOwnWorkbenchItem ? (
                renderSelectedOwnWorkbenchItem(selectedOwnWorkbenchItem)
              ) : selectedSharedWorkbenchInvoice ? (
                renderSelectedSharedWorkbenchInvoice(selectedSharedWorkbenchInvoice)
              ) : (
                <p className="field-hint">当前任务下还没有可展示的发票详情。</p>
              )}
            </article>
          </SectionCard>
        </section>
      ) : null}

      {workbenchState.status === "ready" && activeTab === "missing-materials" ? (
        <section id="member-workbench-missing-materials" className="member-status-list" aria-label="工作台缺失材料列表">
          {missingMaterials.length > 0 ? (
            missingMaterials.map((missingMaterial) => (
              <article
                key={`${missingMaterial.invoice_id}:${missingMaterial.required_material_type}:${missingMaterial.source_rule_code}`}
                className="task-card member-status-card"
              >
                <div className="member-status-section-header">
                  <div>
                    <p className="task-card-id">缺失材料</p>
                    <h2>{missingMaterial.invoice_number}</h2>
                  </div>
                  <StatusBadge tone="warning">{formatMaterialType(missingMaterial.required_material_type)}</StatusBadge>
                </div>

                <dl className="task-meta-grid member-status-meta-grid">
                  <div>
                    <dt>费用类型</dt>
                    <dd>{formatExpenseType(missingMaterial.expense_type)}</dd>
                  </div>
                  <div>
                    <dt>发现时间</dt>
                    <dd>{formatDateTime(missingMaterial.detected_at)}</dd>
                  </div>
                  <div>
                    <dt>为什么需要</dt>
                    <dd>{formatValidationRule(missingMaterial.source_rule_code)}</dd>
                  </div>
                </dl>

                <p className="field-hint">{missingMaterial.message}</p>

                <div className="inline-actions">
                  <Button component={Link} variant="outlined" size="small" to={buildWorkbenchTaskAnchor(workbenchState.task.id, "#member-workbench-upload")}>
                    去上传区补材料
                  </Button>
                  <Button
                    component={Link}
                    variant="outlined"
                    size="small"
                    to={buildWorkbenchTaskAnchor(workbenchState.task.id, `#workbench-invoice-${missingMaterial.invoice_id}`)}
                  >
                    查看对应发票上下文
                  </Button>
                </div>
              </article>
            ))
          ) : (
            <EmptyState
              title="当前任务没有待补的缺失材料"
              description="至少在当前聚合结果里，系统没有发现仍阻塞复核的缺失项。"
            />
          )}
        </section>
      ) : null}

    </RoleWorkspace>
  );
}
