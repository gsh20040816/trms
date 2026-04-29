import { useEffect, useState } from "react";
import { Link as RouterLink, useSearchParams } from "react-router-dom";

import Button from "@mui/material/Button";
import MenuItem from "@mui/material/MenuItem";
import TextField from "@mui/material/TextField";

import { ApiErrorNotice } from "../components/ApiErrorNotice";
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
  ExpenseType,
  InvoiceRecord,
  MaterialRecord,
  MaterialType,
  RecognitionTaskList,
  RecognitionTaskRecord,
  ReimbursementTask,
  ValidationResult,
} from "../lib/api/types";
import {
  describeRecognitionFailure,
  formatMaterialType,
  formatSubmissionChannel,
  formatTaskStatus,
  formatValidationRule,
} from "../lib/ui-text";
import { useAuthSession } from "./auth-store";

type VisibleTaskState =
  | { status: "loading" }
  | { status: "error"; error: unknown }
  | { status: "ready"; visibleTasks: ReimbursementTask[] };

type SelectedTaskMaterialState =
  | { status: "idle" }
  | { status: "loading"; task: ReimbursementTask }
  | { status: "error"; task: ReimbursementTask; error: unknown }
  | { status: "ready"; task: ReimbursementTask; items: MemberMaterialStatusItem[] };

type ValidationSummaryStatus = "passed" | "failed" | "pending" | "not_ready";

type MissingMaterialTip = {
  requiredMaterialType: MaterialType;
  message: string;
  ruleCode: string;
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

type MemberMaterialStatusItem = {
  material: MaterialRecord;
  recognition: RecognitionTaskRecord | null;
  invoice: InvoiceRecord | null;
  validations: ValidationResult[];
  missingMaterialTips: MissingMaterialTip[];
};

const RECOGNITION_STATUS_LABELS: Record<string, string> = {
  pending: "识别排队中",
  succeeded: "识别完成",
  failed: "识别失败",
  needs_confirmation: "识别待确认",
};

const RECOGNITION_FIELD_LABELS: Record<string, string> = {
  invoice_number: "发票号码",
  buyer_name: "购买方名称",
  tax_number: "税号",
  amount_cents: "金额",
  transaction_time: "交易时间",
  expense_type: "费用类型",
  departure_location: "出发地",
  arrival_location: "到达地",
  cabin_class: "舱位",
  seat_class: "座位等级",
};

const EXPENSE_TYPE_LABELS: Record<ExpenseType, string> = {
  registration: "参赛费",
  railway: "火车票",
  airfare: "航空费",
  local_transport: "市内交通",
  hotel: "住宿费",
  other: "其他",
};

const MISSING_MATERIAL_RULE_TO_TYPE: Partial<Record<string, MaterialType>> = {
  invoice_payment_record_required: "payment_record",
  invoice_competition_notice_required: "competition_notice",
  invoice_airfare_itinerary_required: "itinerary",
  invoice_local_transport_rideshare_trip_required: "itinerary",
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

function formatExpenseType(value: ExpenseType) {
  return EXPENSE_TYPE_LABELS[value];
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

function formatRecognitionFieldName(fieldName: string) {
  return RECOGNITION_FIELD_LABELS[fieldName] ?? fieldName;
}

function getCurrentRecognitionTask(recognitionList: RecognitionTaskList): RecognitionTaskRecord | null {
  const latestEffective = recognitionList.latest_effective;
  if (latestEffective) {
    return latestEffective;
  }
  return recognitionList.items[recognitionList.items.length - 1] ?? null;
}

function getRecognitionFieldTextValue(
  recognition: RecognitionTaskRecord | null,
  fieldName: string,
) {
  const field = recognition?.recognized_fields[fieldName];
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
  const field = recognition?.recognized_fields.amount_cents;
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

function buildManualInvoiceFormState(
  item: MemberMaterialStatusItem,
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
    amountYuan: item.invoice
      ? formatAmountInputFromCents(item.invoice.amount_cents)
      : getRecognitionAmountInput(item.recognition),
    expenseType: item.invoice?.expense_type
      ?? getRecognitionExpenseType(item.recognition, allowedExpenseTypes),
  };
}

function validateManualInvoiceForm(
  formState: ManualInvoiceFormState,
  allowedExpenseTypes: ExpenseType[],
): ManualInvoiceFormErrors {
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
  if (parseAmountYuanToCents(formState.amountYuan) === null) {
    errors.amountYuan = "请输入大于 0 的金额，单位为元。";
  }
  return errors;
}

function deriveMissingMaterialTips(validations: ValidationResult[]): MissingMaterialTip[] {
  return validations.flatMap((validation) => {
    if (validation.status !== "failed") {
      return [];
    }
    const requiredMaterialType = MISSING_MATERIAL_RULE_TO_TYPE[validation.rule_code];
    if (!requiredMaterialType) {
      return [];
    }
    return [
      {
        requiredMaterialType,
        message: validation.message,
        ruleCode: validation.rule_code,
      },
    ];
  });
}

function summarizeRecognition(recognition: RecognitionTaskRecord | null) {
  if (!recognition) {
    return {
      tone: "pending" as const,
      title: "识别任务尚未创建",
      details: ["当前材料还没有可展示的识别任务记录。"],
    };
  }

  if (recognition.status === "failed") {
    return {
      tone: "failed" as const,
      title: RECOGNITION_STATUS_LABELS[recognition.status],
      details: [describeRecognitionFailure(recognition.failure)],
    };
  }

  if (recognition.status === "needs_confirmation") {
    const pendingFieldNames = Object.entries(recognition.recognized_fields)
      .filter(([, field]) => field.status === "needs_confirmation")
      .map(([fieldName]) => formatRecognitionFieldName(fieldName));

    return {
      tone: "needs_confirmation" as const,
      title: RECOGNITION_STATUS_LABELS[recognition.status],
      details: pendingFieldNames.length > 0
        ? [`待确认字段：${pendingFieldNames.join("、")}`]
        : ["识别结果包含待确认项，请直接补充或更正关键信息。"],
    };
  }

  if (recognition.status === "succeeded") {
    const recognizedFieldCount = Object.keys(recognition.recognized_fields).length;
    return {
      tone: "succeeded" as const,
      title: RECOGNITION_STATUS_LABELS[recognition.status],
      details: [`已输出 ${recognizedFieldCount} 个识别字段。`],
    };
  }

  return {
    tone: "pending" as const,
    title: RECOGNITION_STATUS_LABELS[recognition.status],
    details: ["材料已进入统一识别流程，当前仍在排队或处理中。"],
  };
}

function summarizeValidations(
  materialType: MaterialType,
  invoice: InvoiceRecord | null,
  validations: ValidationResult[],
) {
  if (!invoice) {
    return {
      tone: "not_ready" as const,
      title: materialType === "invoice" ? "待录入发票字段" : "当前材料暂无独立发票校验",
      details: [
        materialType === "invoice"
          ? "该发票材料还没有对应的发票结构化记录，因此暂时没有可展示的校验结果。"
          : "当前校验结果只挂在发票记录上；辅助材料的影响会体现在关联发票的校验中。",
      ],
      abnormalValidations: [] as ValidationResult[],
    };
  }

  if (validations.length === 0) {
    return {
      tone: "not_ready" as const,
      title: "暂无校验结果",
      details: ["发票记录已存在，但当前还没有可展示的校验结果。"],
      abnormalValidations: [] as ValidationResult[],
    };
  }

  const failedValidations = validations.filter((validation) => validation.status === "failed");
  const pendingValidations = validations.filter((validation) => validation.status === "pending");
  const abnormalValidations = validations.filter(
    (validation) => validation.status === "failed" || validation.status === "pending",
  );

  let tone: ValidationSummaryStatus = "passed";
  let title = "全部校验通过";
  if (failedValidations.length > 0) {
    tone = "failed";
    title = `存在 ${failedValidations.length} 条失败校验`;
  } else if (pendingValidations.length > 0) {
    tone = "pending";
    title = `存在 ${pendingValidations.length} 条待确认校验`;
  }

  const details = [
    `总计 ${validations.length} 条校验结果`,
    `失败 ${failedValidations.length} 条，待确认 ${pendingValidations.length} 条`,
  ];

  return {
    tone,
    title,
    details,
    abnormalValidations,
  };
}

function buildRecognitionBadgeTone(
  tone: ReturnType<typeof summarizeRecognition>["tone"],
) {
  switch (tone) {
    case "failed":
      return "danger" as const;
    case "needs_confirmation":
      return "warning" as const;
    case "succeeded":
      return "success" as const;
    default:
      return "info" as const;
  }
}

function buildValidationBadgeTone(
  tone: ReturnType<typeof summarizeValidations>["tone"],
) {
  switch (tone) {
    case "failed":
      return "danger" as const;
    case "pending":
      return "warning" as const;
    case "passed":
      return "success" as const;
    default:
      return "neutral" as const;
  }
}

export function MemberMaterialStatusPage() {
  const session = useAuthSession();
  const { showError, showSuccess, showWarning } = useSnackbar();
  const [searchParams] = useSearchParams();
  const preferredTaskId = searchParams.get("taskId");
  const [taskState, setTaskState] = useState<VisibleTaskState>({ status: "loading" });
  const [selectedTaskId, setSelectedTaskId] = useState("");
  const [materialState, setMaterialState] = useState<SelectedTaskMaterialState>({ status: "idle" });
  const [selectedMaterialId, setSelectedMaterialId] = useState<string | null>(null);
  const [refreshNonce, setRefreshNonce] = useState(0);
  const [activeEditorMaterialId, setActiveEditorMaterialId] = useState<string | null>(null);
  const [editorFormState, setEditorFormState] = useState<ManualInvoiceFormState | null>(null);
  const [editorErrors, setEditorErrors] = useState<ManualInvoiceFormErrors>({});
  const [retryingMaterialId, setRetryingMaterialId] = useState<string | null>(null);
  const [savingMaterialId, setSavingMaterialId] = useState<string | null>(null);

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
        setSelectedTaskId((currentTaskId) => (
          pickSelectedTaskId(visibleTasks, preferredTaskId, currentTaskId)
        ));
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

    async function loadSelectedTaskStatus(task: ReimbursementTask) {
      setMaterialState({ status: "loading", task });

      try {
        const [materialsResponse, invoicesResponse] = await Promise.all([
          trmsApi.listTaskMaterials(task.id),
          trmsApi.listTaskInvoices(task.id),
        ]);

        const ownMaterials = materialsResponse.items
          .filter((material) => material.submitter_id === session?.actorId)
          .sort((left, right) => right.created_at.localeCompare(left.created_at));
        const ownMaterialIds = new Set(ownMaterials.map((material) => material.id));
        const invoicesByMaterialId = new Map(
          invoicesResponse.items
            .filter((invoice) => ownMaterialIds.has(invoice.material_id))
            .map((invoice) => [invoice.material_id, invoice] as const),
        );

        const recognitionEntries = await Promise.all(
          ownMaterials.map(async (material) => [
            material.id,
            await trmsApi.listMaterialRecognitionTasks(material.id),
          ] as const),
        );
        const recognitionsByMaterialId = new Map(
          recognitionEntries.map(([materialId, recognitionList]) => [
            materialId,
            getCurrentRecognitionTask(recognitionList),
          ] as const),
        );

        const ownInvoices = Array.from(invoicesByMaterialId.values());
        const validationEntries = await Promise.all(
          ownInvoices.map(async (invoice) => [
            invoice.id,
            (await trmsApi.listInvoiceValidations(invoice.id)).items,
          ] as const),
        );
        const validationsByInvoiceId = new Map(validationEntries);

        if (cancelled) {
          return;
        }

        const items = ownMaterials.map((material) => {
          const invoice = invoicesByMaterialId.get(material.id) ?? null;
          const validations = invoice ? (validationsByInvoiceId.get(invoice.id) ?? []) : [];
          return {
            material,
            recognition: recognitionsByMaterialId.get(material.id) ?? null,
            invoice,
            validations,
            missingMaterialTips: deriveMissingMaterialTips(validations),
          };
        });

        setMaterialState({ status: "ready", task, items });
      } catch (error) {
        if (cancelled) {
          return;
        }

        setMaterialState({ status: "error", task, error });
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

    void loadSelectedTaskStatus(selectedTask);

    return () => {
      cancelled = true;
    };
  }, [refreshNonce, selectedTaskId, session, taskState]);

  if (!session || session.role !== "member") {
    return null;
  }
  const memberSession = session;

  const visibleTasks = taskState.status === "ready" ? taskState.visibleTasks : [];
  const selectedTask = visibleTasks.find((task) => task.id === selectedTaskId) ?? null;
  const readyItems = materialState.status === "ready" ? materialState.items : [];
  const selectedItem = readyItems.find((item) => item.material.id === selectedMaterialId) ?? readyItems[0] ?? null;
  const totalMissingTips = readyItems.reduce(
    (count, item) => count + item.missingMaterialTips.length,
    0,
  );
  const needsConfirmationRecognitions = readyItems.filter(
    (item) => item.recognition?.status === "needs_confirmation",
  ).length;
  const failedValidations = readyItems.reduce(
    (count, item) => count + item.validations.filter((validation) => validation.status === "failed").length,
    0,
  );
  const summaryCards = materialState.status === "ready" ? [
    {
      label: "本人材料",
      value: readyItems.length,
      description: "当前任务下由你提交、并可在此页直接跟进的材料数。",
    },
    {
      label: "识别待确认",
      value: needsConfirmationRecognitions,
      description: "识别结果中仍需要你手动确认或补录的材料数。",
    },
    {
      label: "失败校验",
      value: failedValidations,
      description: "当前材料关联发票上已命中的失败校验条数。",
    },
    {
      label: "缺失提示",
      value: totalMissingTips,
      description: "当前任务里已识别出的缺失辅助材料提示条数。",
    },
  ] : [];
  const allowedExpenseTypes: ExpenseType[] = (() => {
    const taskExpenseTypes = selectedTask
      ? selectedTask.fee_categories.filter(isExpenseType)
      : [];
    return taskExpenseTypes.length > 0 ? taskExpenseTypes : ["other"];
  })();

  function openManualEditor(item: MemberMaterialStatusItem) {
    setActiveEditorMaterialId(item.material.id);
    setEditorFormState(buildManualInvoiceFormState(item, allowedExpenseTypes));
    setEditorErrors({});
  }

  function closeManualEditor() {
    setActiveEditorMaterialId(null);
    setEditorFormState(null);
    setEditorErrors({});
  }

  function resetLocalActionState() {
    closeManualEditor();
  }

  function updateEditorField<Key extends keyof ManualInvoiceFormState>(
    key: Key,
    value: ManualInvoiceFormState[Key],
  ) {
    setEditorFormState((current) => {
      if (!current) {
        return current;
      }
      return {
        ...current,
        [key]: value,
      };
    });
    setEditorErrors((current) => {
      if (!(key in current)) {
        return current;
      }
      const next = { ...current };
      delete next[key];
      return next;
    });
  }

  async function handleRetryRecognition(item: MemberMaterialStatusItem) {
    setRetryingMaterialId(item.material.id);
    try {
      const created = await trmsApi.createRecognitionTask(item.material.id);
      const executed = await trmsApi.executeRecognitionTask(created.item.id);
      if (executed.dispatch?.status === "queued") {
        showWarning(executed.dispatch.message);
      } else {
        showSuccess(executed.dispatch?.message ?? "已重新发起识别并刷新当前材料状态。");
      }
      setRefreshNonce((current) => current + 1);
    } catch (error) {
      showError(error instanceof Error ? error.message : "重新识别失败，请稍后重试。");
    } finally {
      setRetryingMaterialId(null);
    }
  }

  async function handleManualInvoiceSubmit(
    event: React.FormEvent<HTMLFormElement>,
    item: MemberMaterialStatusItem,
  ) {
    event.preventDefault();
    if (!editorFormState) {
      return;
    }

    const nextErrors = validateManualInvoiceForm(editorFormState, allowedExpenseTypes);
    setEditorErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) {
      return;
    }

    const amountCents = parseAmountYuanToCents(editorFormState.amountYuan);
    if (amountCents === null) {
      return;
    }

    setSavingMaterialId(item.material.id);
    try {
      const response = await trmsApi.createOrUpdateInvoice(item.material.id, {
        actor_id: memberSession.actorId,
        invoice_number: editorFormState.invoiceNumber.trim(),
        issue_date: editorFormState.issueDate.trim() || null,
        transaction_time: toApiDateTime(editorFormState.transactionTime),
        buyer_name: editorFormState.buyerName.trim(),
        tax_number: editorFormState.taxNumber.trim(),
        seller_name: editorFormState.sellerName.trim() || null,
        amount_cents: amountCents,
        expense_type: editorFormState.expenseType,
      });
      showSuccess(`已保存发票 ${response.invoice.invoice_number}，并重新刷新校验结果。`);
      closeManualEditor();
      setRefreshNonce((current) => current + 1);
    } catch (error) {
      showError(error instanceof Error ? error.message : "保存发票信息失败，请稍后重试。");
    } finally {
      setSavingMaterialId(null);
    }
  }

  return (
    <RoleWorkspace
      header={(
        <PageHeader
          eyebrow="材料状态"
          title="成员材料状态"
          description="在单任务上下文中跟进本人材料的识别进度、发票校验异常和缺失材料提示。"
          meta={`当前成员：${memberSession.displayName}${memberSession.memberCode ? `（${memberSession.memberCode}）` : ""}`}
          actions={(
            <div className="page-actions">
              <StatusBadge tone="info">当前可见任务 {visibleTasks.length} 个</StatusBadge>
              <Button
                component={RouterLink}
                variant="contained"
                to={selectedTask ? `/member/invoices/workbench?taskId=${encodeURIComponent(selectedTask.id)}` : "/member/invoices/workbench"}
              >
                返回当前任务工作台
              </Button>
              <Button component={RouterLink} variant="outlined" to="/member">
                返回成员任务列表
              </Button>
              {selectedTask?.status === "open" ? (
                <Button
                  component={RouterLink}
                  variant="outlined"
                  to={`/member/materials/upload?taskId=${encodeURIComponent(selectedTask.id)}`}
                >
                  去上传更多材料
                </Button>
              ) : null}
            </div>
          )}
        />
      )}
      summary={summaryCards.length > 0 ? (
        <section className="stat-grid" aria-label="材料状态摘要">
          {summaryCards.map((item) => (
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
        <SectionCard title="正在加载可见任务" description="正在读取当前成员可访问的报销任务，以便定位你自己的材料状态。" />
      ) : null}

      {taskState.status === "error" ? <ApiErrorNotice error={taskState.error} /> : null}

      {taskState.status === "ready" && visibleTasks.length === 0 ? (
        <EmptyState
          title="当前没有可查看状态的报销任务"
          description="管理员创建并发布相关任务后，你可以在这里查看自己的材料状态。"
        />
      ) : null}

      {taskState.status === "ready" && visibleTasks.length > 0 ? (
        <SectionCard
          title="选择要查看的任务"
          description="这里只展示你当前可访问的任务，并只聚合你本人提交的材料。"
          action={selectedTask ? <StatusBadge tone="info">{formatTaskStatus(selectedTask.status)}</StatusBadge> : null}
        >
          <div className="admin-form-grid">
            <TextField
              select
              label="目标任务"
              fullWidth
              value={selectedTaskId}
              helperText="这里只列出你可以查看的任务，并只汇总你本人提交的材料。"
              onChange={(event) => {
                resetLocalActionState();
                setSelectedTaskId(event.target.value);
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
                  <dt>截止时间</dt>
                  <dd>{formatDateTime(selectedTask.deadline)}</dd>
                </div>
              </dl>
            ) : null}
          </div>
        </SectionCard>
      ) : null}

      {selectedTask && materialState.status === "loading" ? (
        <SectionCard title="正在汇总成员材料状态" description="正在读取该任务下你本人提交的材料、识别任务和发票校验结果。" />
      ) : null}

      {selectedTask && materialState.status === "error" ? <ApiErrorNotice error={materialState.error} /> : null}

      {selectedTask && materialState.status === "ready" && materialState.items.length === 0 ? (
        <EmptyState
          title="当前任务下还没有你提交的材料"
          description="你还没有向当前任务提交材料，可以先上传发票或辅助材料。"
          action={selectedTask.status === "open" ? (
            <Button
              component={RouterLink}
              variant="contained"
              to={`/member/materials/upload?taskId=${encodeURIComponent(selectedTask.id)}`}
            >
              去上传材料
            </Button>
          ) : null}
        />
      ) : null}

      {selectedTask && materialState.status === "ready" && materialState.items.length > 0 ? (
        <section className="member-status-list" aria-label="成员材料状态列表">
          {materialState.items.map((item) => {
            const recognitionSummary = summarizeRecognition(item.recognition);
            const validationSummary = summarizeValidations(
              item.material.material_type,
              item.invoice,
              item.validations,
            );
            const isSelected = selectedItem?.material.id === item.material.id;

            return (
              <article key={item.material.id} className="task-card member-status-card">
                <div className="task-card-header">
                  <div>
                    <p className="task-card-id">材料编号 {item.material.id}</p>
                    <h3>{item.material.original_filename}</h3>
                  </div>
                  <StatusBadge tone="info">{formatMaterialType(item.material.material_type)}</StatusBadge>
                </div>

                <dl className="task-meta-grid member-status-meta-grid">
                  <div>
                    <dt>提交时间</dt>
                    <dd>{formatDateTime(item.material.created_at)}</dd>
                  </div>
                  <div>
                    <dt>提交渠道</dt>
                    <dd>{formatSubmissionChannel(item.material.channel)}</dd>
                  </div>
                  <div>
                    <dt>重复文件</dt>
                    <dd>{item.material.duplicate_of ? `与 ${item.material.duplicate_of} 重复` : "未标记重复"}</dd>
                  </div>
                  <div>
                    <dt>关联发票</dt>
                    <dd>{item.invoice ? item.invoice.invoice_number : "暂无发票记录"}</dd>
                  </div>
                </dl>

                <section className="member-status-section">
                  <div className="member-status-section-header">
                    <h4>当前摘要</h4>
                    <StatusBadge tone={isSelected ? "info" : "neutral"}>
                      {isSelected ? "当前查看" : "可查看详情"}
                    </StatusBadge>
                  </div>
                  <ul className="member-status-detail-list">
                    <li>{recognitionSummary.title}</li>
                    <li>{validationSummary.title}</li>
                    <li>{item.missingMaterialTips.length > 0 ? `缺失材料 ${item.missingMaterialTips.length} 条` : "当前无缺失材料提示"}</li>
                  </ul>
                  <div className="inline-actions">
                    <Button
                      type="button"
                      variant={isSelected ? "contained" : "outlined"}
                      onClick={() => {
                        resetLocalActionState();
                        setSelectedMaterialId(item.material.id);
                      }}
                    >
                      {isSelected ? "查看当前详情" : "查看详情"}
                    </Button>
                  </div>
                </section>
              </article>
            );
          })}
        </section>
      ) : null}

      {selectedTask && materialState.status === "ready" && selectedItem ? (
        (() => {
          const item = selectedItem;
          const recognitionSummary = summarizeRecognition(item.recognition);
          const validationSummary = summarizeValidations(
            item.material.material_type,
            item.invoice,
            item.validations,
          );

          return (
            <article className="task-card member-status-card" aria-label="当前材料详情">
              <div className="task-card-header">
                <div>
                  <p className="task-card-id">当前材料详情 / 材料编号 {item.material.id}</p>
                  <h3>{item.material.original_filename}</h3>
                </div>
                <StatusBadge tone="info">{formatMaterialType(item.material.material_type)}</StatusBadge>
              </div>

              <dl className="task-meta-grid member-status-meta-grid">
                <div>
                  <dt>提交时间</dt>
                  <dd>{formatDateTime(item.material.created_at)}</dd>
                </div>
                <div>
                  <dt>提交渠道</dt>
                  <dd>{formatSubmissionChannel(item.material.channel)}</dd>
                </div>
                <div>
                  <dt>重复文件</dt>
                  <dd>{item.material.duplicate_of ? `与 ${item.material.duplicate_of} 重复` : "未标记重复"}</dd>
                </div>
                <div>
                  <dt>关联发票</dt>
                  <dd>{item.invoice ? item.invoice.invoice_number : "暂无发票记录"}</dd>
                </div>
              </dl>

              <section className="member-status-section">
                <div className="member-status-section-header">
                  <h4>识别状态</h4>
                  <StatusBadge tone={buildRecognitionBadgeTone(recognitionSummary.tone)}>
                    {recognitionSummary.title}
                  </StatusBadge>
                </div>
                <ul className="member-status-detail-list">
                  {recognitionSummary.details.map((detail) => (
                    <li key={detail}>{detail}</li>
                  ))}
                </ul>
                <div className="inline-actions">
                  <Button
                    type="button"
                    variant="outlined"
                    disabled={retryingMaterialId === item.material.id}
                    onClick={() => {
                      void handleRetryRecognition(item);
                    }}
                  >
                    {retryingMaterialId === item.material.id
                      ? "重新识别中..."
                      : item.recognition
                        ? "运行重新识别"
                        : "开始识别"}
                  </Button>
                </div>
              </section>

              <section className="member-status-section">
                <div className="member-status-section-header">
                  <h4>校验状态</h4>
                  <StatusBadge tone={buildValidationBadgeTone(validationSummary.tone)}>
                    {validationSummary.title}
                  </StatusBadge>
                </div>
                <ul className="member-status-detail-list">
                  {validationSummary.details.map((detail) => (
                    <li key={detail}>{detail}</li>
                  ))}
                </ul>
                {validationSummary.abnormalValidations.length > 0 ? (
                  <ul className="member-status-message-list" aria-label={`${item.material.id} 校验异常列表`}>
                    {validationSummary.abnormalValidations.map((validation) => (
                      <li key={validation.id}>
                        <strong>{formatValidationRule(validation.rule_code)}</strong>
                        <span>{validation.message}</span>
                      </li>
                    ))}
                  </ul>
                ) : null}
              </section>

              {item.material.material_type === "invoice" ? (
                <section className="member-status-section">
                  <div className="member-status-section-header">
                    <h4>人工填写信息</h4>
                    <StatusBadge tone="info">
                      {item.invoice ? "可直接更正已录入发票" : "识别不准时可自行补录"}
                    </StatusBadge>
                  </div>
                  <p className="task-healthy-note">
                    录入后会刷新当前发票的校验结果；这一步由材料提交人自己完成，不再要求管理员代填。
                  </p>
                  <div className="inline-actions">
                    <Button
                      type="button"
                      variant="contained"
                      onClick={() => {
                        if (activeEditorMaterialId === item.material.id) {
                          closeManualEditor();
                          return;
                        }
                        openManualEditor(item);
                      }}
                    >
                      {activeEditorMaterialId === item.material.id ? "收起人工填写" : "人工填写发票信息"}
                    </Button>
                  </div>
                  {activeEditorMaterialId === item.material.id && editorFormState ? (
                    <form
                      className="form-grid"
                      aria-label={`${item.material.id} 发票人工填写表单`}
                      onSubmit={(event) => {
                        void handleManualInvoiceSubmit(event, item);
                      }}
                    >
                      <TextField
                        label="发票号码"
                        value={editorFormState.invoiceNumber}
                        onChange={(event) => {
                          updateEditorField("invoiceNumber", event.target.value);
                        }}
                        error={Boolean(editorErrors.invoiceNumber)}
                        helperText={editorErrors.invoiceNumber}
                      />
                      <TextField
                        label="开票日期"
                        type="date"
                        value={editorFormState.issueDate}
                        onChange={(event) => {
                          updateEditorField("issueDate", event.target.value);
                        }}
                        slotProps={{ inputLabel: { shrink: true } }}
                      />
                      <TextField
                        label="交易时间"
                        type="datetime-local"
                        value={editorFormState.transactionTime}
                        onChange={(event) => {
                          updateEditorField("transactionTime", event.target.value);
                        }}
                        slotProps={{ inputLabel: { shrink: true } }}
                      />
                      <TextField
                        label="发票抬头"
                        value={editorFormState.buyerName}
                        onChange={(event) => {
                          updateEditorField("buyerName", event.target.value);
                        }}
                        error={Boolean(editorErrors.buyerName)}
                        helperText={editorErrors.buyerName}
                      />
                      <TextField
                        label="税号"
                        value={editorFormState.taxNumber}
                        onChange={(event) => {
                          updateEditorField("taxNumber", event.target.value);
                        }}
                        error={Boolean(editorErrors.taxNumber)}
                        helperText={editorErrors.taxNumber}
                      />
                      <TextField
                        label="销售方名称"
                        value={editorFormState.sellerName}
                        onChange={(event) => {
                          updateEditorField("sellerName", event.target.value);
                        }}
                      />
                      <TextField
                        label="金额（元）"
                        inputMode="decimal"
                        value={editorFormState.amountYuan}
                        onChange={(event) => {
                          updateEditorField("amountYuan", event.target.value);
                        }}
                        error={Boolean(editorErrors.amountYuan)}
                        helperText={editorErrors.amountYuan}
                      />
                      <TextField
                        select
                        label="费用类型"
                        value={editorFormState.expenseType}
                        onChange={(event) => {
                          updateEditorField("expenseType", event.target.value as ExpenseType);
                        }}
                        error={Boolean(editorErrors.expenseType)}
                        helperText={editorErrors.expenseType}
                      >
                        {allowedExpenseTypes.map((expenseType) => (
                          <MenuItem key={expenseType} value={expenseType}>
                            {formatExpenseType(expenseType)}
                          </MenuItem>
                        ))}
                      </TextField>
                      <div className="form-actions">
                        <Button
                          variant="contained"
                          disabled={savingMaterialId === item.material.id}
                          type="submit"
                        >
                          {savingMaterialId === item.material.id ? "保存中..." : "保存发票信息"}
                        </Button>
                        <Button
                          variant="outlined"
                          type="button"
                          onClick={() => {
                            closeManualEditor();
                          }}
                        >
                          取消
                        </Button>
                      </div>
                    </form>
                  ) : null}
                </section>
              ) : null}

              <section className="member-status-section">
                <div className="member-status-section-header">
                  <h4>缺失材料提示</h4>
                  <StatusBadge tone={item.missingMaterialTips.length > 0 ? "warning" : "success"}>
                    {item.missingMaterialTips.length > 0
                      ? `${item.missingMaterialTips.length} 条缺失提示`
                      : "当前无缺失提示"}
                  </StatusBadge>
                </div>
                {item.missingMaterialTips.length > 0 ? (
                  <ul className="member-status-message-list" aria-label={`${item.material.id} 缺失材料提示列表`}>
                    {item.missingMaterialTips.map((tip) => (
                      <li key={`${tip.ruleCode}:${tip.requiredMaterialType}`}>
                        <strong>{formatMaterialType(tip.requiredMaterialType)}</strong>
                        <span>{tip.message}</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="task-healthy-note">当前材料关联的发票没有命中可直接归类为“缺失材料”的失败规则。</p>
                )}
              </section>
            </article>
          );
        })()
      ) : null}
    </RoleWorkspace>
  );
}
