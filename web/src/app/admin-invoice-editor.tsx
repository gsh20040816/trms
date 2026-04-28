import { useEffect, useRef, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";

import { ApiErrorNotice } from "../components/ApiErrorNotice";
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
import {
  describeRecognitionFailure,
  formatMemberLabel,
  formatValidationRule,
} from "../lib/ui-text";
import { useAuthSession } from "./auth-store";

type InvoiceEditorPageState =
  | { status: "loading" }
  | { status: "error"; error: unknown }
  | { status: "ready"; task: ReimbursementTask; summary: TaskReviewSummary };

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

function formatCurrencyFromCents(cents: number) {
  return `￥${(cents / 100).toFixed(2)}`;
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
    return formatCurrencyFromCents(field.value);
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

  const task = pageState.status === "ready" ? pageState.task : null;
  const isForeignTask = task ? task.administrator_id !== session.actorId : false;
  const visibleTask = pageState.status === "ready" && !isForeignTask ? pageState.task : null;
  const visibleSummary = pageState.status === "ready" && !isForeignTask ? pageState.summary : null;
  const selectedItem = visibleSummary ? findSelectedItem(invoiceMaterialItems, selectedMaterialId) : null;
  const selectedRecognition = selectedItem?.materialItem.latest_recognition ?? null;
  const selectedInvoice = selectedItem?.invoiceItem?.invoice ?? null;
  const selectedValidations = selectedItem?.invoiceItem?.validations ?? [];
  const allowedExpenseTypes = visibleTask
    ? visibleTask.fee_categories.filter(isExpenseType)
    : [];

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
          <Link className="route-link route-link-secondary" to={`/admin/tasks/${taskId}`}>
            返回任务详情
          </Link>
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
                <span className="status-chip">{invoiceMaterialItems.length} 份发票材料</span>
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
                        <button
                          type="button"
                          className={`invoice-material-button ${isSelected ? "invoice-material-button-selected" : ""}`}
                          onClick={() => {
                            setSelectedMaterialId(material.id);
                            setFormState(buildInitialFormState(item, visibleTask));
                            setFormErrors({});
                            setSubmitError(null);
                            setSaveFeedback(null);
                          }}
                        >
                          <div className="task-card-header">
                            <div>
                              <p className="task-card-id">材料编号 {material.id}</p>
                              <h3>{material.original_filename}</h3>
                            </div>
                            <span className="status-chip">
                              {invoice ? "已存在发票记录" : "待录入"}
                            </span>
                          </div>
                          <dl className="task-meta-grid invoice-editor-summary-grid">
                            <div>
                              <dt>提交人</dt>
                              <dd>{formatMemberLabel(material.submitter_id)}</dd>
                            </div>
                            <div>
                              <dt>识别状态</dt>
                              <dd>{formatRecognitionStatus(item.materialItem.latest_recognition?.status ?? "pending")}</dd>
                            </div>
                            <div>
                              <dt>当前发票号</dt>
                              <dd>{invoice?.invoice_number ?? "尚未录入"}</dd>
                            </div>
                            <div>
                              <dt>异常校验</dt>
                              <dd>
                                失败 {countFailedValidations(validations)} 条，待确认 {countPendingValidations(validations)} 条
                              </dd>
                            </div>
                          </dl>
                        </button>
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
                  <span className="status-chip">
                    {selectedInvoice ? `当前发票号 ${selectedInvoice.invoice_number}` : "尚无发票记录"}
                  </span>
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
                    <dd>{formatDateTime(selectedItem.materialItem.material.created_at)}</dd>
                  </div>
                  <div>
                    <dt>支持的费用类型</dt>
                    <dd>{allowedExpenseTypes.map((item) => formatExpenseType(item)).join("、")}</dd>
                  </div>
                </dl>

                {saveFeedback && saveFeedback.materialId === selectedItem.materialItem.material.id ? (
                  <section className="member-status-section">
                    <div className="member-status-section-header">
                      <div>
                        <h4>保存完成并已刷新校验结果</h4>
                        <p className="field-hint">
                          发票 {saveFeedback.invoiceNumber} 当前共有 {saveFeedback.validationCount} 条校验结果，其中失败 {saveFeedback.failedValidationCount} 条、待确认 {saveFeedback.pendingValidationCount} 条。
                        </p>
                      </div>
                      <span className="status-chip member-status-chip-pending">已重新加载摘要</span>
                    </div>
                  </section>
                ) : null}

                <form
                  className="page-stack"
                  onSubmit={(event) => {
                    void handleSubmit(event);
                  }}
                >
                  <div className="admin-form-grid">
                    <label className="field-stack">
                      <span>发票号码</span>
                      <input
                        name="invoice-number"
                        value={formState.invoiceNumber}
                        onChange={(event) => {
                          updateField("invoiceNumber", event.target.value);
                        }}
                      />
                      {formErrors.invoiceNumber ? <span className="field-error">{formErrors.invoiceNumber}</span> : null}
                    </label>

                    <label className="field-stack">
                      <span>开票日期</span>
                      <input
                        type="date"
                        name="issue-date"
                        value={formState.issueDate}
                        onChange={(event) => {
                          updateField("issueDate", event.target.value);
                        }}
                      />
                    </label>

                    <label className="field-stack">
                      <span>交易时间</span>
                      <input
                        type="datetime-local"
                        name="transaction-time"
                        value={formState.transactionTime}
                        onChange={(event) => {
                          updateField("transactionTime", event.target.value);
                        }}
                      />
                    </label>

                    <label className="field-stack">
                      <span>金额（元）</span>
                      <input
                        name="amount-yuan"
                        inputMode="decimal"
                        placeholder="例如 123.45"
                        value={formState.amountYuan}
                        onChange={(event) => {
                          updateField("amountYuan", event.target.value);
                        }}
                      />
                      {formErrors.amountYuan ? <span className="field-error">{formErrors.amountYuan}</span> : null}
                    </label>

                    <label className="field-stack">
                      <span>发票抬头</span>
                      <input
                        name="buyer-name"
                        value={formState.buyerName}
                        onChange={(event) => {
                          updateField("buyerName", event.target.value);
                        }}
                      />
                      {formErrors.buyerName ? <span className="field-error">{formErrors.buyerName}</span> : null}
                    </label>

                    <label className="field-stack">
                      <span>税号</span>
                      <input
                        name="tax-number"
                        value={formState.taxNumber}
                        onChange={(event) => {
                          updateField("taxNumber", event.target.value);
                        }}
                      />
                      {formErrors.taxNumber ? <span className="field-error">{formErrors.taxNumber}</span> : null}
                    </label>

                    <label className="field-stack">
                      <span>销售方名称</span>
                      <input
                        name="seller-name"
                        value={formState.sellerName}
                        onChange={(event) => {
                          updateField("sellerName", event.target.value);
                        }}
                      />
                    </label>

                    <label className="field-stack">
                      <span>费用类型</span>
                      <select
                        name="expense-type"
                        value={formState.expenseType}
                        onChange={(event) => {
                          updateField("expenseType", event.target.value as ExpenseType);
                        }}
                      >
                        {allowedExpenseTypes.map((expenseType) => (
                          <option key={expenseType} value={expenseType}>
                            {formatExpenseType(expenseType)}
                          </option>
                        ))}
                      </select>
                      {formErrors.expenseType ? <span className="field-error">{formErrors.expenseType}</span> : null}
                    </label>
                  </div>

                  <section className="member-status-section">
                    <div className="member-status-section-header">
                      <div>
                        <h4>识别状态与字段来源</h4>
                        <p className="field-hint">
                          当前服务端会把人工更正写回最新有效识别记录，因此这里直接展示字段来源、置信度和待确认提示，而不是只显示最终发票值。
                        </p>
                      </div>
                      <span className={`status-chip member-status-chip-${selectedRecognition?.status ?? "pending"}`}>
                        {formatRecognitionStatus(selectedRecognition?.status ?? "pending")}
                      </span>
                    </div>

                    {selectedRecognition?.status === "failed" && selectedRecognition.failure ? (
                      <p className="field-hint">
                        {describeRecognitionFailure(selectedRecognition.failure)}
                      </p>
                    ) : null}

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
                            aria-label={`${fieldConfig.label}识别信息`}
                          >
                            <div className="member-status-section-header">
                              <div>
                                <h4>{fieldConfig.label}</h4>
                                <p className="field-hint">
                                  {recognizedField
                                    ? `来源：${formatRecognitionSource(recognizedField.source)}，置信度 ${formatConfidence(recognizedField.confidence)}`
                                    : fieldConfig.required
                                      ? "当前没有可直接复用的识别建议，请人工录入。"
                                      : "该字段暂无识别建议，可按需补录。"}
                                </p>
                              </div>
                              <span className={`status-chip member-status-chip-${recognizedField?.status ?? "not_ready"}`}>
                                {recognizedField
                                  ? formatRecognitionFieldStatus(recognizedField.status)
                                  : "暂无识别建议"}
                              </span>
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
                  </section>

                  <section className="member-status-section">
                    <div className="member-status-section-header">
                      <div>
                        <h4>当前校验结果</h4>
                        <p className="field-hint">
                          保存后这里会根据服务端返回和任务摘要刷新结果更新，不把“应该已重新校验”当作结论。
                        </p>
                      </div>
                      <span className="status-chip">
                        共 {selectedValidations.length} 条
                      </span>
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
                              <span className={`status-chip member-status-chip-${validation.status}`}>
                                {formatValidationStatus(validation.status)}
                              </span>
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

                  <div className="admin-form-footer">
                    <p className="field-hint">
                      保存后请继续根据校验结果补充材料或回到复核页处理剩余问题。
                    </p>
                    <button className="route-link" type="submit" disabled={isSubmitting}>
                      {isSubmitting ? "正在保存并刷新摘要" : "保存发票字段"}
                    </button>
                  </div>
                </form>
              </article>
            ) : null}
          </section>
        </>
      ) : null}
    </div>
  );
}
