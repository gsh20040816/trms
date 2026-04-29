import { type FormEvent, type SyntheticEvent, useEffect, useMemo, useState } from "react";
import { Link, useLocation, useNavigate, useSearchParams } from "react-router-dom";

import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";

import { ApiErrorNotice } from "../components/ApiErrorNotice";
import { ApiError } from "../lib/api/client";
import {
  EmptyState,
  PageHeader,
  RoleWorkspace,
  SectionCard,
  StatCard,
  StatusBadge,
} from "../components/dashboard";
import { trmsApi } from "../lib/api/trms";
import type {
  ConfirmationStatus,
  ConfirmationRecord,
  ExpenseDetailItem,
  ExpenseSplitRecord,
  InvoiceRecord,
  MaterialBatchUploadResponse,
  MaterialRecord,
  MaterialType,
  RecognitionFailureDetail,
  RecognitionFieldResult,
  RecognitionTaskRecord,
  RecognitionTaskStatus,
  ReimbursementTask,
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

type WorkbenchTab = "invoices" | "missing-materials" | "confirmations";

type WorkbenchInvoiceItem = {
  material: TaskMemberMaterialStatusItem;
  invoice: InvoiceRecord | null;
  recognition: RecognitionTaskRecord | null;
  validations: ValidationResult[];
  supportingMaterials: MaterialRecord[];
  splits: ExpenseSplitRecord[];
  confirmations: ConfirmationRecord[];
  relatedExpenseDetails: ExpenseDetailItem[];
  missingMaterials: TaskMemberStatusReport["missing_materials"];
};

type SplitDraftRow = {
  key: string;
  member_id: string;
  amount_yuan: string;
  note: string;
};

type WorkbenchUploadFormState = {
  materialType: MaterialType;
  files: File[];
};

type WorkbenchUploadValidationErrors = Partial<Record<keyof WorkbenchUploadFormState, string>>;

type WorkbenchConfirmationItem = {
  detail: ExpenseDetailItem;
  supportingMaterials: MaterialRecord[];
};

type ConfirmationFeedback = {
  splitId: string;
  status: Extract<ConfirmationStatus, "confirmed" | "disputed">;
};

const MATERIAL_TYPE_OPTIONS: Array<{ value: MaterialType; label: string }> = [
  { value: "invoice", label: "发票" },
  { value: "payment_record", label: "支付记录" },
  { value: "competition_notice", label: "比赛通知" },
  { value: "itinerary", label: "行程单" },
  { value: "order_screenshot", label: "订单截图" },
  { value: "other_attachment", label: "其他材料" },
];

const DEFAULT_UPLOAD_MATERIAL_TYPE: MaterialType = "invoice";
const MATERIAL_FILE_ACCEPT = ".pdf,.zip,.jpg,.jpeg,.png,.webp";

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
    materialType: DEFAULT_UPLOAD_MATERIAL_TYPE,
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
  recognition: RecognitionTaskRecord | null,
  fieldName: (typeof FIELD_ORDER)[number],
) {
  return recognition?.recognized_fields[fieldName] ?? null;
}

function renderRecognitionSource(field: RecognitionFieldResult | null) {
  if (!field) {
    return "暂无识别值";
  }
  if (field.source === "manual") {
    return "人工填写";
  }
  if (field.source === "ai") {
    return "AI 识别";
  }
  if (field.source === "pdf_text") {
    return "PDF 文本提取";
  }
  return "OCR 识别";
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
      detail: `当前有 ${report.counts.missing_material_count} 条缺失材料提示，会阻塞后续复核。`,
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

function buildWorkbenchItems(
  report: TaskMemberStatusReport,
  invoices: InvoiceRecord[],
  recognitionsByMaterialId: Map<string, RecognitionTaskRecord | null>,
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

function validateWorkbenchUploadForm(
  task: ReimbursementTask | null,
  formState: WorkbenchUploadFormState,
) {
  const errors: WorkbenchUploadValidationErrors = {};

  if (!task || task.status !== "open") {
    errors.files = "当前任务不在开放提交阶段，成员不能直接补交材料。";
  }
  if (!MATERIAL_TYPE_OPTIONS.some((option) => option.value === formState.materialType)) {
    errors.materialType = "请选择受支持的材料类型。";
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

export function MemberInvoiceWorkbenchPage() {
  const session = useAuthSession();
  const actorId = session?.actorId ?? "";
  const [searchParams] = useSearchParams();
  const location = useLocation();
  const navigate = useNavigate();
  const preferredTaskId = searchParams.get("taskId");
  const activeTab = resolveWorkbenchTab(location.hash);
  const [taskState, setTaskState] = useState<VisibleTaskState>({ status: "loading" });
  const [selectedTaskId, setSelectedTaskId] = useState("");
  const [workbenchState, setWorkbenchState] = useState<SelectedTaskWorkbenchState>({ status: "idle" });
  const [materialTypeDrafts, setMaterialTypeDrafts] = useState<Record<string, MaterialType>>({});
  const [materialTypeErrors, setMaterialTypeErrors] = useState<Record<string, string>>({});
  const [updatingMaterialId, setUpdatingMaterialId] = useState<string | null>(null);
  const [splitDrafts, setSplitDrafts] = useState<Record<string, SplitDraftRow[]>>({});
  const [splitErrors, setSplitErrors] = useState<Record<string, string>>({});
  const [updatingSplitInvoiceId, setUpdatingSplitInvoiceId] = useState<string | null>(null);
  const [uploadFormState, setUploadFormState] = useState<WorkbenchUploadFormState>(() => buildInitialUploadFormState());
  const [uploadValidationErrors, setUploadValidationErrors] = useState<WorkbenchUploadValidationErrors>({});
  const [uploadSubmitError, setUploadSubmitError] = useState<unknown>(null);
  const [uploadResult, setUploadResult] = useState<MaterialBatchUploadResponse | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadFileInputKey, setUploadFileInputKey] = useState(0);
  const [confirmationSubmitError, setConfirmationSubmitError] = useState<unknown>(null);
  const [confirmationFeedback, setConfirmationFeedback] = useState<ConfirmationFeedback | null>(null);
  const [submittingConfirmationSplitId, setSubmittingConfirmationSplitId] = useState<string | null>(null);
  const [staleConfirmationSplitId, setStaleConfirmationSplitId] = useState<string | null>(null);
  const [disputeReasons, setDisputeReasons] = useState<Record<string, string>>({});
  const [disputeErrors, setDisputeErrors] = useState<Record<string, string>>({});
  const [workbenchReloadVersion, setWorkbenchReloadVersion] = useState(0);

  function resetTaskScopedUiState() {
    setUploadValidationErrors({});
    setUploadSubmitError(null);
    setUploadResult(null);
    setUploadFormState(buildInitialUploadFormState());
    setUploadFileInputKey((current) => current + 1);
    setConfirmationSubmitError(null);
    setConfirmationFeedback(null);
    setSubmittingConfirmationSplitId(null);
    setStaleConfirmationSplitId(null);
    setDisputeReasons({});
    setDisputeErrors({});
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

    async function loadWorkbench(task: ReimbursementTask) {
      setWorkbenchState({ status: "loading", task });

      try {
        const [report, sharedInvoicesReport, invoicesResponse] = await Promise.all([
          trmsApi.getTaskMemberStatus(task.id, session!.actorId),
          trmsApi.getTaskSharedInvoices(task.id, session!.actorId),
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
        const items = buildWorkbenchItems(
          report,
          invoices,
          new Map(recognitionEntries),
          new Map(validationEntries),
          new Map(supportingEntries),
          new Map(splitEntries),
          new Map(confirmationEntries),
        );

        if (cancelled) {
          return;
        }

        setWorkbenchState({
          status: "ready",
          task,
          report,
          items,
          sharedInvoices: [...sharedInvoicesReport.items].sort(
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
      } catch (error) {
        if (cancelled) {
          return;
        }
        setWorkbenchState({ status: "error", task, error });
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
    ? summarizePendingActions(workbenchState.task, workbenchState.report)
    : [];
  const missingMaterials = workbenchState.status === "ready" ? workbenchState.report.missing_materials : [];
  const sharedInvoices = workbenchState.status === "ready"
    ? workbenchState.sharedInvoices.filter((item) => item.submitter_id !== actorId)
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
    setUploadFileInputKey((current) => current + 1);
  }

  async function handleUploadSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!session) {
      return;
    }

    setUploadSubmitError(null);
    setUploadResult(null);

    const errors = validateWorkbenchUploadForm(selectedTask, uploadFormState);
    setUploadValidationErrors(errors);
    if (Object.keys(errors).length > 0 || !selectedTask) {
      return;
    }

    const requestBody = new FormData();
    requestBody.set("submitter_id", session.actorId);
    requestBody.set("channel", "web");
    requestBody.set("material_type", uploadFormState.materialType);
    uploadFormState.files.forEach((file) => {
      requestBody.append("files", file);
    });

    setIsUploading(true);
    try {
      const response = await trmsApi.submitTaskMaterials(selectedTask.id, requestBody);
      setUploadResult(response);
      resetUploadSelectedFiles();
      if (response.items.length > 0) {
        setWorkbenchReloadVersion((current) => current + 1);
      }
    } catch (error) {
      const failedBatch = extractFailedBatchUploadResponse(error);
      if (failedBatch) {
        setUploadResult(failedBatch);
        resetUploadSelectedFiles();
        if (failedBatch.items.length > 0) {
          setWorkbenchReloadVersion((current) => current + 1);
        }
      } else {
        setUploadSubmitError(error);
      }
    } finally {
      setIsUploading(false);
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

  if (!session || session.role !== "member") {
    return null;
  }

  return (
    <RoleWorkspace
      header={(
        <PageHeader
          eyebrow="成员发票工作台"
          title="按任务查看我的发票与费用"
          description="在单一任务上下文里查看识别字段、人工更正值、关联附件、当前分摊去向和确认状态。"
          meta={`当前成员：${session.displayName}${session.memberCode ? `（${session.memberCode}）` : ""}`}
          actions={(
            <div className="page-actions">
              <Link className="button button-secondary" to="/member">
                返回任务列表
              </Link>
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
          title="当前任务上下文"
          description="先固定在一个任务内处理发票，再在缺失材料和费用确认之间切换，减少上下文丢失。"
          action={selectedTask ? <StatusBadge tone="info">{formatTaskStatus(selectedTask.status)}</StatusBadge> : null}
        >
          <div className="admin-form-grid">
            <label className="field-stack">
              <span>目标任务</span>
              <select
                aria-label="目标任务"
                value={selectedTaskId}
                onChange={(event) => {
                  handleTaskChange(event.target.value);
                }}
              >
                {visibleTasks.map((task) => (
                  <option key={task.id} value={task.id}>
                    {task.competition_name}（{task.id}）
                  </option>
                ))}
              </select>
            </label>
            {selectedTask ? (
              <dl className="task-meta-grid member-status-meta-grid">
                <div>
                  <dt>比赛地点</dt>
                  <dd>{selectedTask.competition_location}</dd>
                </div>
                <div>
                  <dt>截止时间</dt>
                  <dd>{formatDateTime(selectedTask.deadline)}</dd>
                </div>
                <div>
                  <dt>当前成员</dt>
                  <dd>{session.displayName}{session.memberCode ? `（${session.memberCode}）` : ""}</dd>
                </div>
              </dl>
            ) : null}
          </div>
        </SectionCard>
      ) : null}

      {selectedTask && workbenchState.status === "loading" ? (
        <SectionCard title="正在汇总当前任务" description="正在聚合你的发票、识别结果、分摊和确认状态。" />
      ) : null}

      {workbenchState.status === "ready" ? (
        <SectionCard
          title="待处理事项"
          description="先处理最会阻塞后续复核的事项，再回看发票细节。"
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
                <Link className="route-link route-link-secondary" to={action.to}>
                  {action.label}
                </Link>
              </li>
            ))}
          </ul>
        </SectionCard>
      ) : null}

      {workbenchState.status === "ready" ? (
        <SectionCard
          title="单任务处理视图"
          description="在发票、缺失材料和费用确认三类视图之间切换，不再要求你自己在多个页面之间拼接上下文。"
        >
          <Tabs
            value={activeTab}
            onChange={handleTabChange}
            aria-label="成员单任务工作台标签页"
            sx={{ borderBottom: 1, borderColor: "divider" }}
          >
            <Tab value="invoices" label="发票" id="member-workbench-tab-invoices" />
            <Tab value="missing-materials" label="缺失材料" id="member-workbench-tab-missing-materials" />
            <Tab value="confirmations" label="费用确认" id="member-workbench-tab-confirmations" />
          </Tabs>
        </SectionCard>
      ) : null}

      {selectedTask && activeTab === "invoices" ? (
        <div id="member-workbench-upload">
          <SectionCard
            title="上传材料与附件"
            description="在当前任务下直接补充发票、支付记录、行程单等材料；上传完成后，下面的识别、缺失项和分摊视图会自动刷新。"
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
                <div className="admin-form-grid">
                  <label className="field-stack">
                    <span>材料类型</span>
                    <select
                      aria-label="工作台上传材料类型"
                      value={uploadFormState.materialType}
                      onChange={(event) => {
                        updateUploadField("materialType", event.target.value as MaterialType);
                      }}
                    >
                      {MATERIAL_TYPE_OPTIONS.map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                    {uploadValidationErrors.materialType ? (
                      <span className="field-error">{uploadValidationErrors.materialType}</span>
                    ) : (
                      <span className="field-hint">请选择最接近的材料类型，便于识别、缺失项检查和后续复核。</span>
                    )}
                  </label>

                  <label className="field-stack">
                    <span>上传文件</span>
                    <input
                      aria-label="工作台上传文件"
                      key={uploadFileInputKey}
                      type="file"
                      multiple
                      accept={MATERIAL_FILE_ACCEPT}
                      onChange={(event) => {
                        updateUploadField("files", Array.from(event.target.files ?? []));
                      }}
                    />
                    {uploadValidationErrors.files ? (
                      <span className="field-error">{uploadValidationErrors.files}</span>
                    ) : (
                      <span className="field-hint">
                        支持 PDF、ZIP、JPG、PNG、WEBP；单文件最大 10MB。批量上传时会逐文件返回成功或失败结果。
                      </span>
                    )}
                  </label>
                </div>

                {uploadFormState.files.length > 0 ? (
                  <ul className="upload-file-list" aria-label="工作台待上传文件列表">
                    {uploadFormState.files.map((file) => (
                      <li key={`${file.name}:${file.size}:${file.lastModified}`}>
                        <strong>{file.name}</strong>
                        <span>{file.type || "未知类型"}</span>
                        <span>{file.size} bytes</span>
                      </li>
                    ))}
                  </ul>
                ) : null}

                <div className="admin-form-footer">
                  <p className="field-hint">
                    上传成功后会保留原始文件并刷新当前任务视图；如存在部分失败，页面会显式列出每个失败文件的真实原因。
                  </p>
                  <button className="route-link" type="submit" disabled={isUploading}>
                    {isUploading ? "正在上传..." : "上传到当前任务"}
                  </button>
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
          title="最近上传结果"
          description="当前工作台直接展示最近一次上传的逐文件结果，不把部分失败伪装成全部成功。"
          action={(
            <StatusBadge tone={uploadResult.status === "failed" ? "warning" : "success"}>
              {uploadResult.status === "success"
                ? "全部成功"
                : uploadResult.status === "partial_success"
                  ? "部分成功"
                  : "全部失败"}
            </StatusBadge>
          )}
        >
          {uploadResult.items.length > 0 ? (
            <ul className="member-status-message-list" aria-label="工作台上传成功列表">
              {uploadResult.items.map((item) => (
                <li key={item.id}>
                  <strong>{item.original_filename}</strong>
                  <span>材料编号：{item.id}</span>
                  <span>材料类型：{formatMaterialType(item.material_type)}</span>
                  <span>{item.duplicate_of ? `重复文件：${item.duplicate_of}` : "已归档到当前任务"}</span>
                </li>
              ))}
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
                        <span className={`status-chip member-status-chip-${currentStatus}`}>
                          {formatConfirmationStatus(currentStatus)}
                        </span>
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
                          <dt>当前版本</dt>
                          <dd>v{item.detail.split_version}</dd>
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

                      <label className="field-stack confirmation-reason-field">
                        <span>异议原因</span>
                        <textarea
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
                        />
                        {disputeError ? <span className="field-error">{disputeError}</span> : null}
                      </label>

                      <div className="inline-actions">
                        <button
                          className="route-link"
                          type="button"
                          disabled={isSubmitting}
                          onClick={() => {
                            void handleConfirmationSubmit(item, "confirmed");
                          }}
                        >
                          {isSubmitting ? "提交中..." : "确认这笔费用"}
                        </button>
                        <button
                          className="route-link route-link-secondary"
                          type="button"
                          disabled={isSubmitting}
                          onClick={() => {
                            void handleConfirmationSubmit(item, "disputed");
                          }}
                        >
                          {isSubmitting ? "提交中..." : "提交异议"}
                        </button>
                        <Link
                          className="route-link route-link-secondary"
                          to={buildWorkbenchTaskAnchor(workbenchState.task.id, `#workbench-invoice-${item.detail.invoice.id}`)}
                        >
                          查看对应发票上下文
                        </Link>
                        {isStale ? (
                          <button
                            className="route-link route-link-secondary"
                            type="button"
                            onClick={() => {
                              setStaleConfirmationSplitId(null);
                              setWorkbenchReloadVersion((current) => current + 1);
                            }}
                          >
                            重新加载明细
                          </button>
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

      {workbenchState.status === "ready" && activeTab === "invoices" && workbenchState.items.length === 0 ? (
        <EmptyState
          title="当前任务下还没有本人已上传发票"
          description="先上传发票材料，系统识别和费用确认才会在这里形成完整工作台。"
          action={(
            <Link className="button button-primary" to={buildWorkbenchTaskAnchor(workbenchState.task.id, "#member-workbench-upload")}>
              去上传区
            </Link>
          )}
        />
      ) : null}

      {workbenchState.status === "ready" && activeTab === "invoices" && workbenchState.items.length > 0 ? (
        <section id="member-workbench-invoices" className="member-status-list" aria-label="成员发票工作台列表">
          {workbenchState.items.map((item) => {
            const abnormalReasons = collectAbnormalReasons(item);
            const invoice = item.invoice;
            const splitDraftRows = invoice
              ? (splitDrafts[invoice.id] ?? buildSplitDraftRows(item, session.actorId))
              : [];

            return (
              <article
                key={item.material.material_id}
                id={invoice ? `workbench-invoice-${invoice.id}` : undefined}
                className="task-card member-status-card"
              >
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
                    <span className="status-chip">可自助更正</span>
                  </div>
                  <div className="admin-form-grid">
                    <label className="field-stack">
                      <span>当前材料类型</span>
                      <select
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
                          <option key={option.value} value={option.value}>
                            {option.label}
                          </option>
                        ))}
                      </select>
                    </label>
                    <div className="field-stack">
                      <span>操作</span>
                      <button
                        type="button"
                        className="button button-secondary"
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
                      </button>
                    </div>
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
                    <span className="status-chip">{abnormalReasons.length} 条</span>
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
                    <span className="status-chip">
                      {item.recognition ? renderRecognitionSource(getRecognitionFieldValue(item.recognition, "invoice_number")) : "暂无识别"}
                    </span>
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
                    <h4>当前分摊方案与确认状态</h4>
                    <span className="status-chip">{item.splits.length} 条分摊</span>
                  </div>
                  {invoice ? (
                    <>
                      <div className="member-status-section-header">
                        <h5>调整分配对象与备注</h5>
                        <span className="status-chip">
                          {workbenchState.task.status === "open" ? "当前可编辑" : `当前${formatTaskStatus(workbenchState.task.status)}，不可编辑`}
                        </span>
                      </div>
                      {splitDraftRows.map((draft, index) => (
                        <div key={draft.key} className="admin-form-grid">
                          <label className="field-stack">
                            <span>分配对象 {index + 1}</span>
                            <select
                              aria-label={`${invoice.id} 分摊行 ${index + 1} 成员`}
                              value={draft.member_id}
                              onChange={(event) => {
                                updateSplitDraft(invoice.id, draft.key, {
                                  member_id: event.target.value,
                                });
                              }}
                              disabled={
                                workbenchState.task.status !== "open"
                                || updatingSplitInvoiceId === invoice.id
                              }
                            >
                              {workbenchState.task.member_ids.map((memberId) => (
                                <option key={memberId} value={memberId}>
                                  {formatMemberLabel(memberId)}
                                </option>
                              ))}
                            </select>
                          </label>
                          <label className="field-stack">
                            <span>金额（元）</span>
                            <input
                              aria-label={`${invoice.id} 分摊行 ${index + 1} 金额`}
                              type="text"
                              inputMode="decimal"
                              value={draft.amount_yuan}
                              onChange={(event) => {
                                updateSplitDraft(invoice.id, draft.key, {
                                  amount_yuan: event.target.value,
                                });
                              }}
                              disabled={
                                workbenchState.task.status !== "open"
                                || updatingSplitInvoiceId === invoice.id
                              }
                            />
                          </label>
                          <label className="field-stack">
                            <span>备注</span>
                            <input
                              aria-label={`${invoice.id} 分摊行 ${index + 1} 备注`}
                              type="text"
                              value={draft.note}
                              onChange={(event) => {
                                updateSplitDraft(invoice.id, draft.key, {
                                  note: event.target.value,
                                });
                              }}
                              disabled={
                                workbenchState.task.status !== "open"
                                || updatingSplitInvoiceId === invoice.id
                              }
                            />
                          </label>
                          <div className="field-stack">
                            <span>操作</span>
                            <button
                              type="button"
                              className="button button-secondary"
                              onClick={() => {
                                removeSplitDraft(invoice.id, draft.key);
                              }}
                              disabled={
                                workbenchState.task.status !== "open"
                                || updatingSplitInvoiceId === invoice.id
                                || splitDraftRows.length <= 1
                              }
                            >
                              移除
                            </button>
                          </div>
                        </div>
                      ))}
                      <div className="inline-actions">
                        <button
                          type="button"
                          className="button button-secondary"
                          onClick={() => {
                            addSplitDraft(invoice.id, workbenchState.task.member_ids);
                          }}
                          disabled={
                            workbenchState.task.status !== "open"
                            || updatingSplitInvoiceId === invoice.id
                          }
                        >
                          新增分摊对象
                        </button>
                        <button
                          type="button"
                          className="button button-secondary"
                          onClick={() => {
                            void handleSplitSave(item);
                          }}
                          disabled={
                            workbenchState.task.status !== "open"
                            || updatingSplitInvoiceId === invoice.id
                            || (
                              item.splits.length > 0
                              && !haveSplitDraftsChanged(
                                item,
                                splitDraftRows,
                                session.actorId,
                              )
                            )
                          }
                        >
                          {updatingSplitInvoiceId === invoice.id ? "保存中..." : "保存分摊方案"}
                        </button>
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
                  {item.relatedExpenseDetails.length > 0 ? (
                    <p className="field-hint">
                      当前发票已有 {item.relatedExpenseDetails.length} 条与你相关的费用明细，可直接在本页的
                      <Link
                        className="route-link route-link-secondary"
                        to={buildWorkbenchTaskAnchor(workbenchState.task.id, "#member-workbench-confirmations")}
                      >
                        费用确认区
                      </Link>
                      提交确认或异议。
                    </p>
                  ) : null}
                </section>

                <section className="member-status-section">
                  <div className="member-status-section-header">
                    <h4>关联附件与缺失项</h4>
                    <span className="status-chip">
                      附件 {item.supportingMaterials.length} 份 / 缺失 {item.missingMaterials.length} 项
                    </span>
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
                    <span className="status-chip">优先留在当前工作台</span>
                  </div>
                  <div className="inline-actions">
                    <Link className="route-link route-link-secondary" to={buildWorkbenchTaskAnchor(workbenchState.task.id, "#member-workbench-upload")}>
                      跳到上传区
                    </Link>
                    <Link className="route-link route-link-secondary" to={buildWorkbenchTaskAnchor(workbenchState.task.id, "#member-workbench-invoices")}>
                      回到发票详情
                    </Link>
                    <Link className="route-link route-link-secondary" to={buildWorkbenchTaskAnchor(workbenchState.task.id, "#member-workbench-confirmations")}>
                      跳到确认区
                    </Link>
                  </div>
                </section>
              </article>
            );
          })}
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
                    <p className="task-card-id">缺失材料 / {missingMaterial.invoice_id}</p>
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
                    <dt>规则来源</dt>
                    <dd>{formatValidationRule(missingMaterial.source_rule_code)}</dd>
                  </div>
                </dl>

                <p className="field-hint">{missingMaterial.message}</p>

                <div className="inline-actions">
                  <Link className="route-link route-link-secondary" to={buildWorkbenchTaskAnchor(workbenchState.task.id, "#member-workbench-upload")}>
                    去上传区补材料
                  </Link>
                  <Link
                    className="route-link route-link-secondary"
                    to={buildWorkbenchTaskAnchor(workbenchState.task.id, `#workbench-invoice-${missingMaterial.invoice_id}`)}
                  >
                    查看对应发票上下文
                  </Link>
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

      {workbenchState.status === "ready" && activeTab === "invoices" ? (
        <SectionCard
          title="任务内其他成员已上传发票"
          description="这里仅共享发票基础元数据、当前分摊去向和必要附件摘要；不提供原始文件下载、支付截图全文或识别原始响应。"
          action={(
            <StatusBadge tone="info">
              {sharedInvoices.length} 张
            </StatusBadge>
          )}
        >
          {sharedInvoices.length > 0 ? (
            <section className="member-status-list" aria-label="任务内共享发票摘要列表">
              {sharedInvoices.map((item) => (
                <article key={item.invoice_id} className="task-card member-status-card">
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
                      <span className="status-chip">只读摘要</span>
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
                      <span className="status-chip">{item.splits.length} 条</span>
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
                      <span className="status-chip">{item.supporting_materials.length} 类</span>
                    </div>
                    <p className="field-hint">{formatSupportingMaterialSummary(item)}</p>
                  </section>
                </article>
              ))}
            </section>
          ) : (
            <p className="field-hint">当前任务里还没有其他成员上传可共享查看的发票摘要。</p>
          )}
        </SectionCard>
      ) : null}
    </RoleWorkspace>
  );
}
