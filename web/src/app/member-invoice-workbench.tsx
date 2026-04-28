import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

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
  ConfirmationRecord,
  ExpenseDetailItem,
  ExpenseSplitRecord,
  InvoiceRecord,
  MaterialRecord,
  MaterialType,
  RecognitionFieldResult,
  RecognitionTaskRecord,
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

function summarizePendingActions(task: ReimbursementTask, report: TaskMemberStatusReport): PendingAction[] {
  const actions: PendingAction[] = [];

  if (report.counts.recognition_failed_count > 0 || report.counts.recognition_needs_confirmation_count > 0) {
    actions.push({
      id: "recognition",
      title: "先核对识别结果",
      detail: `当前有 ${report.counts.recognition_failed_count + report.counts.recognition_needs_confirmation_count} 份材料仍需人工确认或补录。`,
      to: `/member/materials/status?taskId=${encodeURIComponent(task.id)}`,
      tone: "warning",
      label: "查看材料状态",
    });
  }

  if (report.counts.missing_material_count > 0) {
    actions.push({
      id: "missing-materials",
      title: "补齐必传材料",
      detail: `当前有 ${report.counts.missing_material_count} 条缺失材料提示，会阻塞后续复核。`,
      to: `/member/materials/upload?taskId=${encodeURIComponent(task.id)}`,
      tone: "danger",
      label: "去补材料",
    });
  }

  if (report.counts.validation_failed_count > 0 || report.counts.validation_pending_count > 0) {
    actions.push({
      id: "validations",
      title: "处理异常校验",
      detail: `当前有 ${report.counts.validation_failed_count} 条失败校验、${report.counts.validation_pending_count} 条待确认校验。`,
      to: `/member/materials/status?taskId=${encodeURIComponent(task.id)}`,
      tone: "warning",
      label: "查看异常原因",
    });
  }

  if (report.counts.pending_confirmation_count > 0 || report.counts.missing_confirmation_count > 0) {
    actions.push({
      id: "confirmations",
      title: "确认本人费用",
      detail: `当前有 ${report.counts.pending_confirmation_count + report.counts.missing_confirmation_count} 条费用还未完成确认。`,
      to: `/member/expenses/confirm?taskId=${encodeURIComponent(task.id)}`,
      tone: "info",
      label: "去确认费用",
    });
  }

  if (actions.length === 0) {
    actions.push({
      id: "done",
      title: "当前任务已无明显待处理项",
      detail: "可以继续回看发票记录，或等待管理员进入下一阶段处理。",
      to: `/member/materials/status?taskId=${encodeURIComponent(task.id)}`,
      tone: "info",
      label: "查看材料记录",
    });
  }

  return actions;
}

function collectAbnormalReasons(item: WorkbenchInvoiceItem) {
  const reasons: string[] = [];

  if (item.recognition?.status === "failed") {
    reasons.push(describeRecognitionFailure(item.recognition.failure));
  }
  if (item.recognition?.status === "needs_confirmation") {
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
        report.counts.recognition_failed_count
        + report.counts.recognition_needs_confirmation_count
        + report.counts.validation_failed_count
        + report.counts.missing_material_count
      ),
      description: "优先处理识别异常、失败校验和缺失材料。",
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

function formatSupportingMaterialSummary(item: TaskSharedInvoiceItem) {
  if (item.supporting_materials.length === 0) {
    return "当前还没有已关联的必要附件摘要。";
  }
  return item.supporting_materials
    .map((material) => `${formatMaterialType(material.material_type)} ${material.count} 份`)
    .join(" / ");
}

export function MemberInvoiceWorkbenchPage() {
  const session = useAuthSession();
  const actorId = session?.actorId ?? "";
  const [searchParams] = useSearchParams();
  const preferredTaskId = searchParams.get("taskId");
  const [taskState, setTaskState] = useState<VisibleTaskState>({ status: "loading" });
  const [selectedTaskId, setSelectedTaskId] = useState("");
  const [workbenchState, setWorkbenchState] = useState<SelectedTaskWorkbenchState>({ status: "idle" });
  const [materialTypeDrafts, setMaterialTypeDrafts] = useState<Record<string, MaterialType>>({});
  const [materialTypeErrors, setMaterialTypeErrors] = useState<Record<string, string>>({});
  const [updatingMaterialId, setUpdatingMaterialId] = useState<string | null>(null);
  const [splitDrafts, setSplitDrafts] = useState<Record<string, SplitDraftRow[]>>({});
  const [splitErrors, setSplitErrors] = useState<Record<string, string>>({});
  const [updatingSplitInvoiceId, setUpdatingSplitInvoiceId] = useState<string | null>(null);
  const [workbenchReloadVersion, setWorkbenchReloadVersion] = useState(0);

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
  const sharedInvoices = workbenchState.status === "ready"
    ? workbenchState.sharedInvoices.filter((item) => item.submitter_id !== actorId)
    : [];
  const abnormalCount = useMemo(() => {
    if (workbenchState.status !== "ready") {
      return 0;
    }
    return workbenchState.items.reduce((count, item) => count + collectAbnormalReasons(item).length, 0);
  }, [workbenchState]);

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
          title="任务范围"
          description="先选定一个任务，再围绕这一个任务查看待处理事项、异常原因和下一步动作。"
          action={selectedTask ? <StatusBadge tone="info">{formatTaskStatus(selectedTask.status)}</StatusBadge> : null}
        >
          <div className="admin-form-grid">
            <label className="field-stack">
              <span>目标任务</span>
              <select
                aria-label="目标任务"
                value={selectedTaskId}
                onChange={(event) => {
                  setSelectedTaskId(event.target.value);
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
            <StatusBadge tone={abnormalCount > 0 ? "warning" : "success"}>
              {abnormalCount > 0 ? `${abnormalCount} 条异常提示` : "当前无明显异常"}
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

      {workbenchState.status === "ready" && workbenchState.items.length === 0 ? (
        <EmptyState
          title="当前任务下还没有本人已上传发票"
          description="先上传发票材料，系统识别和费用确认才会在这里形成完整工作台。"
          action={(
            <Link className="button button-primary" to={`/member/materials/upload?taskId=${encodeURIComponent(workbenchState.task.id)}`}>
              去上传材料
            </Link>
          )}
        />
      ) : null}

      {workbenchState.status === "ready" && workbenchState.items.length > 0 ? (
        <section className="member-status-list" aria-label="成员发票工作台列表">
          {workbenchState.items.map((item) => {
            const abnormalReasons = collectAbnormalReasons(item);
            const invoice = item.invoice;
            const splitDraftRows = invoice
              ? (splitDrafts[invoice.id] ?? buildSplitDraftRows(item, session.actorId))
              : [];

            return (
              <article key={item.material.material_id} className="task-card member-status-card">
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
                    <dd>{item.recognition ? formatRecognitionStatus(item.recognition.status) : "暂无识别记录"}</dd>
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
                    <span className="status-chip">围绕当前任务继续处理</span>
                  </div>
                  <div className="inline-actions">
                    <Link className="route-link route-link-secondary" to={`/member/materials/upload?taskId=${encodeURIComponent(workbenchState.task.id)}`}>
                      上传或补充材料
                    </Link>
                    <Link className="route-link route-link-secondary" to={`/member/materials/status?taskId=${encodeURIComponent(workbenchState.task.id)}`}>
                      查看材料状态
                    </Link>
                    <Link className="route-link route-link-secondary" to={`/member/expenses/confirm?taskId=${encodeURIComponent(workbenchState.task.id)}`}>
                      确认费用
                    </Link>
                  </div>
                </section>
              </article>
            );
          })}
        </section>
      ) : null}

      {workbenchState.status === "ready" ? (
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
