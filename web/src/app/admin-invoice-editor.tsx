import { useEffect, useRef, useState } from "react";
import { Link as RouterLink, useParams, useSearchParams } from "react-router-dom";
import Accordion from "@mui/material/Accordion";
import AccordionDetails from "@mui/material/AccordionDetails";
import AccordionSummary from "@mui/material/AccordionSummary";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import MenuItem from "@mui/material/MenuItem";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import TextField from "@mui/material/TextField";

import { ApiErrorNotice } from "../components/ApiErrorNotice";
import { InvoiceSummaryRow } from "../components/invoice-summary-row";
import { StatusBadge } from "../components/dashboard";
import { trmsApi } from "../lib/api/trms";
import type {
  ExpenseType,
  RecognitionFieldResult,
  RecognitionTaskRecord,
  ReimbursementTask,
  TaskReviewSummary,
  TaskReviewSummaryInvoiceItem,
  TaskReviewSummaryMaterialItem,
  ValidationResult,
} from "../lib/api/types";
import { formatInvoiceAmountFromCents } from "../lib/currency";
import {
  describeRecognitionFailure,
  formatMaterialType,
  formatMemberLabel,
  formatValidationRule,
} from "../lib/ui-text";
import { useAuthSession } from "./auth-store";

type InvoiceEditorPageState =
  | { status: "loading" }
  | { status: "error"; error: unknown }
  | { status: "ready"; task: ReimbursementTask; summary: TaskReviewSummary };

type InvoicePreviewState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "unsupported"; contentType: string | null }
  | { status: "error"; error: unknown }
  | { status: "ready"; url: string; contentType: string };

type InvoiceEditorFormState = {
  invoiceNumber: string;
  issueDate: string;
  transactionTime: string;
  buyerName: string;
  taxNumber: string;
  sellerName: string;
  amountYuan: string;
  expenseType: ExpenseType;
};

type InvoiceEditorFormErrors = Partial<Record<keyof InvoiceEditorFormState, string>>;

type InvoiceMaterialItem = {
  materialItem: TaskReviewSummaryMaterialItem;
  invoiceItem: TaskReviewSummaryInvoiceItem | null;
};

type SaveFeedback = {
  materialId: string;
  invoiceNumber: string;
  validationCount: number;
  failedValidationCount: number;
  pendingValidationCount: number;
};

type InvoiceFieldConfig = {
  key: keyof InvoiceEditorFormState;
  label: string;
  recognitionField: string;
  required: boolean;
};

type InvoiceDetailTab = "preview" | "recognition" | "validation" | "actions";

const EXPENSE_TYPE_LABELS: Record<ExpenseType, string> = {
  registration: "参赛费",
  railway: "火车票",
  airfare: "航空费",
  local_transport: "市内交通",
  hotel: "住宿费",
  other: "其他",
};

const RECOGNITION_STATUS_LABELS: Record<string, string> = {
  pending: "识别排队中",
  succeeded: "识别完成",
  failed: "识别失败",
  needs_confirmation: "识别待确认",
};

const RECOGNITION_SOURCE_LABELS: Record<string, string> = {
  ai: "系统识别",
  ocr: "图片识别",
  pdf_text: "文档识别",
  manual: "人工更正",
};

const RECOGNITION_FIELD_STATUS_LABELS: Record<string, string> = {
  recognized: "已识别",
  needs_confirmation: "待确认",
};

const REVALIDATION_STATUS_LABELS: Record<string, string> = {
  triggered: "已触发重新校验",
  not_required: "无需重新校验",
};

const VALIDATION_STATUS_LABELS: Record<string, string> = {
  passed: "通过",
  failed: "失败",
  pending: "待确认",
  not_applicable: "不适用",
};

const VALIDATION_SEVERITY_LABELS: Record<string, string> = {
  blocker: "需要立即处理",
  warning: "需要关注",
  info: "已记录",
};

const INVOICE_FIELD_CONFIGS: InvoiceFieldConfig[] = [
  {
    key: "invoiceNumber",
    label: "发票号码",
    recognitionField: "invoice_number",
    required: true,
  },
  {
    key: "issueDate",
    label: "开票日期",
    recognitionField: "issue_date",
    required: false,
  },
  {
    key: "transactionTime",
    label: "交易时间",
    recognitionField: "transaction_time",
    required: false,
  },
  {
    key: "buyerName",
    label: "发票抬头",
    recognitionField: "buyer_name",
    required: true,
  },
  {
    key: "taxNumber",
    label: "税号",
    recognitionField: "tax_number",
    required: true,
  },
  {
    key: "sellerName",
    label: "销售方名称",
    recognitionField: "seller_name",
    required: false,
  },
  {
    key: "amountYuan",
    label: "金额",
    recognitionField: "amount_cents",
    required: true,
  },
  {
    key: "expenseType",
    label: "费用类型",
    recognitionField: "expense_type",
    required: true,
  },
];

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

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function formatExpenseType(value: string) {
  return isExpenseType(value) ? EXPENSE_TYPE_LABELS[value] : value;
}

function formatRecognitionSource(source: string) {
  return RECOGNITION_SOURCE_LABELS[source] ?? source;
}

function formatRecognitionStatus(status: string) {
  return RECOGNITION_STATUS_LABELS[status] ?? status;
}

function formatRecognitionFieldStatus(status: string) {
  return RECOGNITION_FIELD_STATUS_LABELS[status] ?? status;
}

function formatValidationStatus(status: string) {
  return VALIDATION_STATUS_LABELS[status] ?? status;
}

function formatValidationSeverity(severity: string) {
  return VALIDATION_SEVERITY_LABELS[severity] ?? severity;
}

function formatRevalidationStatus(status: string) {
  return REVALIDATION_STATUS_LABELS[status] ?? status;
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

function formatConfidence(confidence: number) {
  return `${Math.round(confidence * 100)}%`;
}

function formatRecognitionAuditText(field: RecognitionFieldResult) {
  return `来源：${formatRecognitionSource(field.source)}，置信度 ${formatConfidence(field.confidence)}`;
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

function buildInvoiceMaterialItems(summary: TaskReviewSummary): InvoiceMaterialItem[] {
  const invoiceItemsById = new Map(summary.invoices.map((item) => [item.invoice.id, item]));
  return summary.materials
    .filter((item) => item.material.material_type === "invoice")
    .map((materialItem) => ({
      materialItem,
      invoiceItem: materialItem.invoice_id ? (invoiceItemsById.get(materialItem.invoice_id) ?? null) : null,
    }))
    .sort((left, right) => {
      return (
        new Date(right.materialItem.material.created_at).getTime()
        - new Date(left.materialItem.material.created_at).getTime()
      );
    });
}

function pickSelectedMaterialId(
  items: InvoiceMaterialItem[],
  preferredMaterialId: string | null,
  currentMaterialId: string,
) {
  const visibleMaterialIds = new Set(items.map((item) => item.materialItem.material.id));
  if (currentMaterialId && visibleMaterialIds.has(currentMaterialId)) {
    return currentMaterialId;
  }
  if (preferredMaterialId && visibleMaterialIds.has(preferredMaterialId)) {
    return preferredMaterialId;
  }
  return items[0]?.materialItem.material.id ?? "";
}

function buildInitialFormState(
  item: InvoiceMaterialItem | null,
  task: ReimbursementTask,
): InvoiceEditorFormState {
  const allowedExpenseTypes = task.fee_categories.filter(isExpenseType);
  const recognition = item?.materialItem.latest_recognition ?? null;
  const invoice = item?.invoiceItem?.invoice ?? null;
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
    amountYuan: invoice
      ? formatAmountInputFromCents(invoice.amount_cents)
      : getRecognitionAmountInput(recognition),
    expenseType: defaultExpenseType,
  };
}

function validateForm(
  formState: InvoiceEditorFormState,
  allowedExpenseTypes: ExpenseType[],
): InvoiceEditorFormErrors {
  const errors: InvoiceEditorFormErrors = {};
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

function countFailedValidations(validations: ValidationResult[]) {
  return validations.filter((item) => item.status === "failed").length;
}

function countPendingValidations(validations: ValidationResult[]) {
  return validations.filter((item) => item.status === "pending").length;
}

function buildInvoiceSummaryValidation(validations: ValidationResult[], hasInvoice: boolean) {
  if (!hasInvoice) {
    return { label: "待补录校验", tone: "warning" as const };
  }
  if (countFailedValidations(validations) > 0) {
    return { label: "校验失败", tone: "warning" as const };
  }
  if (countPendingValidations(validations) > 0) {
    return { label: "校验待确认", tone: "warning" as const };
  }
  return { label: "校验通过", tone: "success" as const };
}

function findSelectedItem(items: InvoiceMaterialItem[], materialId: string) {
  return items.find((item) => item.materialItem.material.id === materialId) ?? null;
}

function getFieldCorrections(
  recognition: RecognitionTaskRecord | null,
  fieldName: string,
) {
  if (!recognition) {
    return [];
  }
  return recognition.manual_corrections
    .filter((item) => item.field_name === fieldName)
    .slice()
    .reverse();
}

function describeRecognitionFieldValue(field: RecognitionFieldResult, fieldName: string) {
  if (fieldName === "amount_cents" && typeof field.value === "number") {
    return formatInvoiceAmountFromCents(field.value);
  }
  if (fieldName === "amount_cents") {
    return formatInvoiceAmountFromCents(null);
  }
  if (fieldName === "expense_type" && typeof field.value === "string") {
    return formatExpenseType(field.value);
  }
  if (fieldName === "transaction_time" && typeof field.value === "string") {
    return field.value;
  }
  if (fieldName === "issue_date" && typeof field.value === "string") {
    return field.value;
  }
  if (typeof field.value === "string" || typeof field.value === "number") {
    return String(field.value);
  }
  return "无法直接展示";
}

function isPreviewableContentType(contentType: string | null) {
  return contentType === "application/pdf" || Boolean(contentType?.startsWith("image/"));
}

export function AdminInvoiceEditorPage() {
  const session = useAuthSession();
  const { taskId } = useParams<{ taskId: string }>();
  const [searchParams] = useSearchParams();
  const preferredMaterialId = searchParams.get("materialId");
  const [pageState, setPageState] = useState<InvoiceEditorPageState>({ status: "loading" });
  const [selectedMaterialId, setSelectedMaterialId] = useState("");
  const [formState, setFormState] = useState<InvoiceEditorFormState | null>(null);
  const [formErrors, setFormErrors] = useState<InvoiceEditorFormErrors>({});
  const [submitError, setSubmitError] = useState<unknown>(null);
  const [saveFeedback, setSaveFeedback] = useState<SaveFeedback | null>(null);
  const [refreshNonce, setRefreshNonce] = useState(0);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [detailTab, setDetailTab] = useState<InvoiceDetailTab>("actions");
  const [previewState, setPreviewState] = useState<InvoicePreviewState>({ status: "idle" });
  const latestSelectedMaterialIdRef = useRef(selectedMaterialId);

  useEffect(() => {
    latestSelectedMaterialIdRef.current = selectedMaterialId;
  }, [selectedMaterialId]);

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

        const nextInvoiceMaterialItems = buildInvoiceMaterialItems(summary);
        const nextSelectedMaterialId = pickSelectedMaterialId(
          nextInvoiceMaterialItems,
          preferredMaterialId,
          latestSelectedMaterialIdRef.current,
        );
        const nextSelectedItem = findSelectedItem(
          nextInvoiceMaterialItems,
          nextSelectedMaterialId,
        );

        setPageState({
          status: "ready",
          task,
          summary,
        });
        setSelectedMaterialId(nextSelectedMaterialId);
        setFormState(nextSelectedItem ? buildInitialFormState(nextSelectedItem, task) : null);
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
  }, [preferredMaterialId, refreshNonce, session, taskId]);

  const invoiceMaterialItems = pageState.status === "ready"
    ? buildInvoiceMaterialItems(pageState.summary)
    : [];
  const task = pageState.status === "ready" ? pageState.task : null;
  const isForeignTask = task ? task.administrator_id !== session?.actorId : false;
  const visibleTask = pageState.status === "ready" && !isForeignTask ? pageState.task : null;
  const visibleSummary = pageState.status === "ready" && !isForeignTask ? pageState.summary : null;
  const selectedItem = visibleSummary ? findSelectedItem(invoiceMaterialItems, selectedMaterialId) : null;
  const selectedMaterial = selectedItem?.materialItem.material ?? null;
  const selectedMaterialIdForPreview = selectedMaterial?.id ?? "";
  const selectedMaterialContentType = selectedMaterial?.content_type ?? null;
  const selectedRecognition = selectedItem?.materialItem.latest_recognition ?? null;
  const selectedInvoice = selectedItem?.invoiceItem?.invoice ?? null;
  const selectedValidations = selectedItem?.invoiceItem?.validations ?? [];
  const allowedExpenseTypes = visibleTask
    ? visibleTask.fee_categories.filter(isExpenseType)
    : [];

  useEffect(() => {
    let cancelled = false;
    let objectUrl: string | null = null;

    async function loadPreview() {
      if (detailTab !== "preview") {
        setPreviewState({ status: "idle" });
        return;
      }
      if (!selectedMaterialIdForPreview) {
        setPreviewState({ status: "idle" });
        return;
      }
      if (!isPreviewableContentType(selectedMaterialContentType)) {
        setPreviewState({
          status: "unsupported",
          contentType: selectedMaterialContentType,
        });
        return;
      }

      setPreviewState({ status: "loading" });

      try {
        const previewFile = await trmsApi.downloadMaterialContent(selectedMaterialIdForPreview);
        if (cancelled) {
          return;
        }

        objectUrl = URL.createObjectURL(previewFile.blob);
        setPreviewState({
          status: "ready",
          url: objectUrl,
          contentType: previewFile.contentType ?? selectedMaterialContentType ?? "application/octet-stream",
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
  }, [detailTab, selectedMaterialContentType, selectedMaterialIdForPreview]);

  if (!session || session.role !== "admin") {
    return null;
  }

  if (!taskId) {
    return (
      <div className="page-stack">
        <section className="status-card">
          <p className="eyebrow">发票补录</p>
          <h2>任务标识缺失</h2>
          <p>暂时无法读取该任务，请从任务列表重新进入。</p>
        </section>
      </div>
    );
  }

  function updateField<Key extends keyof InvoiceEditorFormState>(
    key: Key,
    value: InvoiceEditorFormState[Key],
  ) {
    setFormState((current) => {
      if (!current) {
        return current;
      }
      return {
        ...current,
        [key]: value,
      };
    });
    setFormErrors((current) => {
      if (!(key in current)) {
        return current;
      }
      const next = { ...current };
      delete next[key];
      return next;
    });
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!session || !formState || !selectedItem || !visibleTask) {
      return;
    }

    const nextErrors = validateForm(formState, allowedExpenseTypes);
    setFormErrors(nextErrors);
    setSubmitError(null);
    if (Object.keys(nextErrors).length > 0) {
      return;
    }

    const amountCents = parseAmountYuanToCents(formState.amountYuan);
    if (amountCents === null) {
      return;
    }

    setIsSubmitting(true);
    try {
      const response = await trmsApi.createOrUpdateInvoice(selectedItem.materialItem.material.id, {
        actor_id: session.actorId,
        invoice_number: formState.invoiceNumber.trim(),
        issue_date: formState.issueDate.trim() || null,
        transaction_time: toApiDateTime(formState.transactionTime),
        buyer_name: formState.buyerName.trim(),
        tax_number: formState.taxNumber.trim(),
        seller_name: formState.sellerName.trim() || null,
        amount_cents: amountCents,
        expense_type: formState.expenseType,
      });

      setSaveFeedback({
        materialId: selectedItem.materialItem.material.id,
        invoiceNumber: response.invoice.invoice_number,
        validationCount: response.validations.length,
        failedValidationCount: countFailedValidations(response.validations),
        pendingValidationCount: countPendingValidations(response.validations),
      });
      setRefreshNonce((current) => current + 1);
    } catch (error) {
      setSubmitError(error);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="page-stack">
      <section className="status-card admin-task-detail-hero">
        <p className="eyebrow">发票补录与更正</p>
        <h2>发票人工录入与更正</h2>
        <p>
          在这里根据已有识别结果补录或修正发票信息，并查看保存后的校验反馈。
        </p>
        <div className="inline-actions">
          <Button component={RouterLink} variant="outlined" to={`/admin/tasks/${taskId}`}>
            返回任务详情
          </Button>
        </div>
      </section>

      {pageState.status === "loading" ? (
        <section className="status-card admin-task-detail-panel">
          <p className="eyebrow">发票补录</p>
          <h2>正在加载发票录入上下文</h2>
          <p>正在读取任务信息、发票材料和识别/校验摘要，请稍候。</p>
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
        <>
          <section className="invoice-editor-layout">
            <article className="status-card admin-task-detail-panel invoice-editor-list-panel">
              <div className="admin-form-header">
                <div>
                  <p className="eyebrow">Invoice Materials</p>
                  <h2>待录入或可更正的发票材料</h2>
                </div>
                <StatusBadge tone="info">{invoiceMaterialItems.length} 份发票材料</StatusBadge>
              </div>

              {invoiceMaterialItems.length === 0 ? (
                <p className="field-hint invoice-editor-empty">
                  当前任务还没有 `invoice` 类型材料，暂时没有可录入的发票。
                </p>
              ) : (
                <ul className="invoice-material-list" aria-label="发票材料列表">
                  {invoiceMaterialItems.map((item) => {
                    const material = item.materialItem.material;
                    const invoice = item.invoiceItem?.invoice ?? null;
                    const validations = item.invoiceItem?.validations ?? [];
                    const isSelected = material.id === selectedMaterialId;
                    return (
                      <li key={material.id}>
                        <InvoiceSummaryRow
                          filename={material.original_filename}
                          invoiceNumber={invoice?.invoice_number ?? null}
                          amountLabel={formatInvoiceAmountFromCents(invoice?.amount_cents ?? null)}
                          validationLabel={buildInvoiceSummaryValidation(validations, invoice !== null).label}
                          validationTone={buildInvoiceSummaryValidation(validations, invoice !== null).tone}
                          supportingMaterialCount={item.invoiceItem?.supporting_material_ids.length ?? 0}
                          statusHint={`提交人 ${formatMemberLabel(material.submitter_id)}；${formatRecognitionStatus(item.materialItem.latest_recognition?.status ?? "pending")}`}
                          trailingContent={(
                            <StatusBadge tone={invoice ? "success" : "warning"}>
                              {invoice ? "已存在发票记录" : "待录入"}
                            </StatusBadge>
                          )}
                          selected={isSelected}
                          action={{
                            ariaLabel: `发票材料 ${material.original_filename} ${invoice?.invoice_number ?? "待补录票号"}`,
                            onClick: () => {
                              setSelectedMaterialId(material.id);
                              setFormState(buildInitialFormState(item, visibleTask));
                              setFormErrors({});
                              setSubmitError(null);
                              setSaveFeedback(null);
                            },
                          }}
                        />
                      </li>
                    );
                  })}
                </ul>
              )}
            </article>

            {selectedItem && formState ? (
              <article className="status-card admin-form-card invoice-editor-form-panel">
                <div className="admin-form-header">
                  <div>
                    <p className="eyebrow">Selected Material</p>
                    <h2>录入或更正发票字段</h2>
                  </div>
                  <StatusBadge tone="info">
                    {selectedInvoice ? `当前发票号 ${selectedInvoice.invoice_number}` : "尚无发票记录"}
                  </StatusBadge>
                </div>

                <dl className="task-meta-grid invoice-editor-summary-grid">
                  <div>
                    <dt>提交成员</dt>
                    <dd>{formatMemberLabel(selectedItem.materialItem.material.submitter_id)}</dd>
                  </div>
                  <div>
                    <dt>比赛名称</dt>
                    <dd>{visibleTask.competition_name}</dd>
                  </div>
                  <div>
                    <dt>材料类型</dt>
                    <dd>{formatMaterialType(selectedItem.materialItem.material.material_type)}</dd>
                  </div>
                  <div>
                    <dt>材料上传时间</dt>
                    <dd>{formatDateTime(selectedItem.materialItem.material.created_at)}</dd>
                  </div>
                  <div>
                    <dt>支持的费用类型</dt>
                    <dd>{allowedExpenseTypes.map((item) => formatExpenseType(item)).join("、")}</dd>
                  </div>
                </dl>

                <Box sx={{ mt: 3, borderBottom: 1, borderColor: "divider" }}>
                  <Tabs
                    value={detailTab}
                    onChange={(_, value: InvoiceDetailTab) => {
                      setDetailTab(value);
                    }}
                    aria-label="发票详情标签页"
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
                  <section className="member-status-section">
                    <div className="member-status-section-header">
                      <div>
                        <h4>原始票据预览</h4>
                        <p className="field-hint">
                          先在这里核对原始票据，再决定是否需要进入人工更正。
                        </p>
                      </div>
                      <StatusBadge tone="info">{selectedItem.materialItem.material.content_type ?? "未知类型"}</StatusBadge>
                    </div>
                    {previewState.status === "loading" ? (
                      <p className="field-hint">正在拉取原始材料内容，请稍候。</p>
                    ) : null}
                    {previewState.status === "unsupported" ? (
                      <p className="field-hint">
                        当前材料类型为 {previewState.contentType ?? "未知"}，暂不支持内联预览，请结合识别字段和原文件名判断下一步处理。
                      </p>
                    ) : null}
                    {previewState.status === "error" ? <ApiErrorNotice error={previewState.error} /> : null}
                    {previewState.status === "ready" ? (
                      <div className="admin-review-preview-shell">
                        {previewState.contentType.startsWith("image/") ? (
                          <img
                            className="admin-review-preview-image"
                            src={previewState.url}
                            alt={`${selectedItem.materialItem.material.original_filename} 预览`}
                          />
                        ) : (
                          <object
                            className="admin-review-preview-frame"
                            data={previewState.url}
                            type={previewState.contentType}
                            aria-label="原始票据 PDF 预览"
                          >
                            <p className="field-hint">当前环境无法直接显示 PDF 预览，但材料内容已成功加载。</p>
                          </object>
                        )}
                      </div>
                    ) : null}
                  </section>
                ) : null}

                {detailTab === "recognition" ? (
                  <section className="member-status-section">
                    <div className="member-status-section-header">
                      <div>
                        <h4>业务字段审核参考</h4>
                        <p className="field-hint">
                          默认只展示管理员审核需要的业务字段建议。来源、置信度和人工更正轨迹已收进下方折叠审计区，避免默认界面暴露内部识别细节。
                        </p>
                      </div>
                      <StatusBadge tone={selectedRecognition?.status === "failed" ? "danger" : selectedRecognition?.status === "succeeded" ? "success" : "warning"}>
                        {formatRecognitionStatus(selectedRecognition?.status ?? "pending")}
                      </StatusBadge>
                    </div>

                    {selectedRecognition?.status === "failed" && selectedRecognition.failure ? (
                      <p className="field-hint">
                        {describeRecognitionFailure(selectedRecognition.failure)}
                      </p>
                    ) : null}

                    <dl className="task-meta-grid invoice-editor-summary-grid">
                      <div>
                        <dt>材料类型</dt>
                        <dd>{formatMaterialType(selectedItem.materialItem.material.material_type)}</dd>
                      </div>
                      <div>
                        <dt>待人工确认字段</dt>
                        <dd>
                          {selectedRecognition
                            ? INVOICE_FIELD_CONFIGS.filter((fieldConfig) => {
                              const field = getRecognitionFieldValue(
                                selectedRecognition,
                                fieldConfig.recognitionField,
                              );
                              return field?.status === "needs_confirmation";
                            }).length
                            : 0}
                        </dd>
                      </div>
                      <div>
                        <dt>人工更正记录</dt>
                        <dd>{selectedRecognition?.manual_corrections.length ?? 0}</dd>
                      </div>
                      <div>
                        <dt>当前识别状态</dt>
                        <dd>{formatRecognitionStatus(selectedRecognition?.status ?? "pending")}</dd>
                      </div>
                    </dl>

                    <div className="admin-form-grid" style={{ marginTop: "18px" }}>
                      {INVOICE_FIELD_CONFIGS.map((fieldConfig) => {
                        const recognizedField = getRecognitionFieldValue(
                          selectedRecognition,
                          fieldConfig.recognitionField,
                        );
                        return (
                          <TextField
                            key={fieldConfig.key}
                            label={`${fieldConfig.label}识别建议`}
                            value={recognizedField
                              ? describeRecognitionFieldValue(recognizedField, fieldConfig.recognitionField)
                              : ""}
                            fullWidth
                            slotProps={{
                              input: {
                                readOnly: true,
                              },
                            }}
                            helperText={
                              recognizedField
                                ? recognizedField.status === "needs_confirmation"
                                  ? "系统已给出建议，但该字段仍需管理员人工确认或更正。"
                                  : "系统已识别到该字段，可直接对照原件核对。"
                                : fieldConfig.required
                                  ? "当前没有可直接复用的识别建议，需要管理员补录。"
                                  : "该字段暂无识别建议，可按需补录。"
                            }
                          />
                        );
                      })}
                    </div>

                    <Accordion
                      disableGutters
                      sx={{ mt: 2 }}
                      slotProps={{ transition: { unmountOnExit: true } }}
                    >
                      <AccordionSummary aria-controls="recognition-audit-panel" id="recognition-audit-header">
                        展开调试与审计信息
                      </AccordionSummary>
                      <AccordionDetails id="recognition-audit-panel">
                        {selectedRecognition ? (
                          <div className="page-stack">
                            <ul className="member-status-message-list">
                              <li>
                                <strong>最近识别状态</strong>
                                <span>{formatRecognitionStatus(selectedRecognition.status)}</span>
                              </li>
                              <li>
                                <strong>最近识别更新时间</strong>
                                <span>{formatDateTime(selectedRecognition.updated_at)}</span>
                              </li>
                            </ul>
                            <div className="recognition-field-grid">
                              {INVOICE_FIELD_CONFIGS.map((fieldConfig) => {
                                const recognizedField = getRecognitionFieldValue(
                                  selectedRecognition,
                                  fieldConfig.recognitionField,
                                );
                                const corrections = getFieldCorrections(
                                  selectedRecognition,
                                  fieldConfig.recognitionField,
                                );
                                return (
                                  <section
                                    key={fieldConfig.key}
                                    className="recognition-field-card"
                                    aria-label={`${fieldConfig.label}审计信息`}
                                  >
                                    <div className="member-status-section-header">
                                      <div>
                                        <h4>{fieldConfig.label}</h4>
                                        <p className="field-hint">
                                          {recognizedField
                                            ? formatRecognitionAuditText(recognizedField)
                                            : "当前没有识别结果可供审计。"}
                                        </p>
                                      </div>
                                      <StatusBadge tone={recognizedField?.status === "recognized" ? "success" : "warning"}>
                                        {recognizedField
                                          ? formatRecognitionFieldStatus(recognizedField.status)
                                          : "暂无识别建议"}
                                      </StatusBadge>
                                    </div>

                                    {recognizedField ? (
                                      <ul className="member-status-message-list">
                                        <li>
                                          <strong>当前识别值</strong>
                                          <span>
                                            {describeRecognitionFieldValue(recognizedField, fieldConfig.recognitionField)}
                                          </span>
                                        </li>
                                        <li>
                                          <strong>最近更新时间</strong>
                                          <span>
                                            {recognizedField.updated_at
                                              ? formatDateTime(recognizedField.updated_at)
                                              : "当前字段暂无单独更新时间"}
                                          </span>
                                        </li>
                                      </ul>
                                    ) : null}

                                    {corrections.length > 0 ? (
                                      <ul className="manual-correction-list">
                                        {corrections.map((correction) => (
                                          <li key={correction.id}>
                                            <strong>人工更正</strong>
                                            <span>
                                              {correction.before
                                                ? `${describeRecognitionFieldValue(correction.before, fieldConfig.recognitionField)} -> `
                                                : "无原始识别值 -> "}
                                              {describeRecognitionFieldValue(correction.after, fieldConfig.recognitionField)}
                                            </span>
                                            <span>
                                              {formatDateTime(correction.corrected_at)}，{formatRevalidationStatus(correction.revalidation_status)}
                                            </span>
                                          </li>
                                        ))}
                                      </ul>
                                    ) : null}
                                  </section>
                                );
                              })}
                            </div>
                          </div>
                        ) : (
                          <p className="field-hint">当前材料还没有可展开的识别审计信息。</p>
                        )}
                      </AccordionDetails>
                    </Accordion>
                  </section>
                ) : null}

                {detailTab === "validation" ? (
                  <section className="member-status-section">
                    <div className="member-status-section-header">
                      <div>
                        <h4>当前校验结果</h4>
                        <p className="field-hint">
                          保存后这里会根据服务端返回和任务摘要刷新结果更新，不把“应该已重新校验”当作结论。
                        </p>
                      </div>
                      <StatusBadge tone="info">
                        共 {selectedValidations.length} 条
                      </StatusBadge>
                    </div>

                    {selectedValidations.length === 0 ? (
                      <p className="field-hint">
                        当前材料还没有对应发票校验结果；若这是首次录入，保存后会生成新的校验结果。
                      </p>
                    ) : (
                      <ul className="validation-result-list" aria-label="发票校验结果列表">
                        {selectedValidations.map((validation) => (
                          <li key={validation.id}>
                            <div className="task-card-header">
                              <strong>{formatValidationRule(validation.rule_code)}</strong>
                              <StatusBadge tone={validation.status === "failed" ? "danger" : validation.status === "pending" ? "warning" : "success"}>
                                {formatValidationStatus(validation.status)}
                              </StatusBadge>
                            </div>
                            <span>
                              严重级别：{formatValidationSeverity(validation.severity)}
                            </span>
                            <span>{validation.message}</span>
                          </li>
                        ))}
                      </ul>
                    )}
                  </section>
                ) : null}

                {detailTab === "actions" ? (
                  <>
                    {saveFeedback && saveFeedback.materialId === selectedItem.materialItem.material.id ? (
                      <section className="member-status-section">
                        <div className="member-status-section-header">
                          <div>
                            <h4>保存完成并已刷新校验结果</h4>
                            <p className="field-hint">
                              发票 {saveFeedback.invoiceNumber} 当前共有 {saveFeedback.validationCount} 条校验结果，其中失败 {saveFeedback.failedValidationCount} 条、待确认 {saveFeedback.pendingValidationCount} 条。
                            </p>
                          </div>
                          <StatusBadge tone="success">已重新加载摘要</StatusBadge>
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
                            <h4>票据核心字段</h4>
                            <p className="field-hint">
                              先核对票号、金额和日期，再处理后续抬头与费用归类，避免在多个标签页之间来回切换。
                            </p>
                          </div>
                        </div>
                        <div className="admin-form-grid">
                          <TextField
                            label="发票号码"
                            name="invoice-number"
                            value={formState.invoiceNumber}
                            onChange={(event) => {
                              updateField("invoiceNumber", event.target.value);
                            }}
                            error={Boolean(formErrors.invoiceNumber)}
                            helperText={formErrors.invoiceNumber}
                            fullWidth
                          />
                          <TextField
                            label="金额（元）"
                            name="amount-yuan"
                            value={formState.amountYuan}
                            onChange={(event) => {
                              updateField("amountYuan", event.target.value);
                            }}
                            error={Boolean(formErrors.amountYuan)}
                            helperText={formErrors.amountYuan}
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
                            name="issue-date"
                            value={formState.issueDate}
                            onChange={(event) => {
                              updateField("issueDate", event.target.value);
                            }}
                            fullWidth
                            slotProps={{ inputLabel: { shrink: true } }}
                          />
                          <TextField
                            label="交易时间"
                            type="datetime-local"
                            name="transaction-time"
                            value={formState.transactionTime}
                            onChange={(event) => {
                              updateField("transactionTime", event.target.value);
                            }}
                            fullWidth
                            slotProps={{ inputLabel: { shrink: true } }}
                          />
                        </div>
                      </section>

                      <section className="member-status-section">
                        <div className="member-status-section-header">
                          <div>
                            <h4>抬头与税号</h4>
                            <p className="field-hint">
                              这组字段会直接影响抬头和税号校验，应优先按原件与任务配置复核。
                            </p>
                          </div>
                        </div>
                        <div className="admin-form-grid">
                          <TextField
                            label="发票抬头"
                            name="buyer-name"
                            value={formState.buyerName}
                            onChange={(event) => {
                              updateField("buyerName", event.target.value);
                            }}
                            error={Boolean(formErrors.buyerName)}
                            helperText={formErrors.buyerName}
                            fullWidth
                          />
                          <TextField
                            label="税号"
                            name="tax-number"
                            value={formState.taxNumber}
                            onChange={(event) => {
                              updateField("taxNumber", event.target.value);
                            }}
                            error={Boolean(formErrors.taxNumber)}
                            helperText={formErrors.taxNumber}
                            fullWidth
                          />
                        </div>
                      </section>

                      <section className="member-status-section">
                        <div className="member-status-section-header">
                          <div>
                            <h4>报销归类与补充信息</h4>
                            <p className="field-hint">
                              最后确认费用类型和销售方名称，确保这张发票能进入正确的报销规则路径。
                            </p>
                          </div>
                        </div>
                        <div className="admin-form-grid">
                          <TextField
                            select
                            label="费用类型"
                            name="expense-type"
                            value={formState.expenseType}
                            onChange={(event) => {
                              updateField("expenseType", event.target.value as ExpenseType);
                            }}
                            error={Boolean(formErrors.expenseType)}
                            helperText={formErrors.expenseType}
                            fullWidth
                          >
                            {allowedExpenseTypes.map((expenseType) => (
                              <MenuItem key={expenseType} value={expenseType}>
                                {formatExpenseType(expenseType)}
                              </MenuItem>
                            ))}
                          </TextField>
                          <TextField
                            label="销售方名称"
                            name="seller-name"
                            value={formState.sellerName}
                            onChange={(event) => {
                              updateField("sellerName", event.target.value);
                            }}
                            fullWidth
                          />
                        </div>
                      </section>

                      <div className="admin-form-footer">
                        <p className="field-hint">
                          保存后请继续根据校验结果补充材料或回到复核页处理剩余问题。
                        </p>
                        <Button variant="contained" type="submit" disabled={isSubmitting}>
                          {isSubmitting ? "正在保存并刷新摘要" : "保存发票字段"}
                        </Button>
                      </div>
                    </form>
                  </>
                ) : null}
              </article>
            ) : null}
          </section>
        </>
      ) : null}
    </div>
  );
}
