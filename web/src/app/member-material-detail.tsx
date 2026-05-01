import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import MenuItem from "@mui/material/MenuItem";
import TextField from "@mui/material/TextField";

import { ApiErrorNotice } from "../components/ApiErrorNotice";
import { InvoiceSummaryRow } from "../components/invoice-summary-row";
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
  MaterialType,
  PendingSupportingMaterialLinkageItem,
  ReimbursementTask,
  TaskMemberWorkbenchItem,
  TaskMemberWorkbenchSummary,
} from "../lib/api/types";
import {
  describeRecognitionFailure,
  formatExpenseType,
  formatMaterialType,
  formatRecognitionStatus,
  formatValidationRule,
  formatValidationStatus,
} from "../lib/ui-text";
import { useAuthSession } from "./auth-store";
import {
  buildInvoiceDetailPath,
  buildMaterialInvoiceDetailPath,
} from "./member-invoice-paths";

type DetailState =
  | { status: "loading" }
  | { status: "error"; error: unknown }
  | {
    status: "ready";
    task: ReimbursementTask;
    summary: TaskMemberWorkbenchSummary;
    item: TaskMemberWorkbenchItem | null;
  };

const MATERIAL_TYPE_OPTIONS: Array<{ value: MaterialType; label: string }> = [
  { value: "invoice", label: "发票" },
  { value: "payment_record", label: "支付记录" },
  { value: "competition_notice", label: "比赛通知" },
  { value: "itinerary", label: "行程单" },
  { value: "order_screenshot", label: "订单截图" },
  { value: "other_attachment", label: "其他材料" },
];

const CLASSIFICATION_FIELD_ORDER = [
  "document_family",
  "material_type",
  "expense_type_candidate",
  "classification_confidence",
  "is_reimbursement_voucher",
] as const;

const MATERIAL_FIELD_LABELS: Record<string, string> = {
  document_family: "识别文档族类",
  material_type: "识别材料类型",
  expense_type_candidate: "建议费用类型",
  classification_confidence: "分类置信度",
  is_reimbursement_voucher: "是否直接报销凭证",
  amount_cents: "金额",
  transaction_time: "时间",
  location: "地点",
  expense_type: "费用类型",
  trip_route: "行程/路线",
  transport_mode: "交通方式",
  cabin_class: "舱位/席别",
  departure_airport_code: "去程出发机场",
  arrival_airport_code: "去程到达机场",
  return_departure_airport_code: "返程出发机场",
  return_arrival_airport_code: "返程到达机场",
};

const MATERIAL_PAGE_CONFIG: Record<
  Exclude<MaterialType, "invoice">,
  {
    title: string;
    description: string;
    fields: string[];
    nextStep: string;
  }
> = {
  payment_record: {
    title: "支付记录详情",
    description: "这里处理支付时间、金额和支付场景，不再展示发票专有表单。",
    fields: ["amount_cents", "transaction_time", "location", "expense_type", "trip_route", "transport_mode"],
    nextStep: "确认支付记录金额和时间是否可信；若仍未归属到发票，请回工作台待关联区完成归属。",
  },
  competition_notice: {
    title: "比赛通知详情",
    description: "这里处理比赛通知里的比赛时间、地点和费用类别线索。",
    fields: ["transaction_time", "location", "expense_type", "trip_route"],
    nextStep: "确认比赛名称相关时间和地点线索是否足够支持报名费或差旅材料。",
  },
  itinerary: {
    title: "行程单详情",
    description: "这里处理行程路线、机场代码和舱位信息，不再展示发票金额分摊表单。",
    fields: [
      "transaction_time",
      "location",
      "expense_type",
      "trip_route",
      "transport_mode",
      "cabin_class",
      "departure_airport_code",
      "arrival_airport_code",
      "return_departure_airport_code",
      "return_arrival_airport_code",
    ],
    nextStep: "确认路线、机场代码和舱位是否完整，便于航空或市内交通发票通过校验。",
  },
  order_screenshot: {
    title: "订单截图详情",
    description: "这里处理订单截图中的金额、时间和路线证据，不再展示发票字段补录区。",
    fields: ["amount_cents", "transaction_time", "location", "expense_type", "trip_route", "transport_mode"],
    nextStep: "确认订单截图是否能作为住宿、交通或其他费用的辅助凭证。",
  },
  other_attachment: {
    title: "其他材料详情",
    description: "这里保留系统能识别出的时间、地点和费用线索，避免强行套用发票表单。",
    fields: ["transaction_time", "location", "expense_type", "trip_route", "transport_mode"],
    nextStep: "若系统误判了材料类型，请先改正类型；否则只保留明确可读的辅助线索。",
  },
};

function formatCurrencyFromCents(cents: number) {
  return `￥${(cents / 100).toFixed(2)}`;
}

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function pickItemByMaterialId(summary: TaskMemberWorkbenchSummary, materialId: string | undefined) {
  if (!materialId) {
    return null;
  }
  return summary.items.find((item) => item.material.material_id === materialId) ?? null;
}

function collectAbnormalReasons(item: TaskMemberWorkbenchItem) {
  const reasons: string[] = [];
  const recognitionStatus = item.recognition?.status ?? item.material.recognition_status;
  if (recognitionStatus === "pending") {
    reasons.push("系统正在处理该材料识别；识别完成前只展示基础状态。");
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
    reasons.push("识别结果仍有待确认字段，请先核对当前材料的关键线索。");
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

function formatRecognizedFieldValue(fieldName: string, value: unknown) {
  if (value === null || value === undefined || value === "") {
    return "未识别";
  }
  if ((fieldName === "amount_cents") && typeof value === "number") {
    return formatCurrencyFromCents(value);
  }
  if (fieldName === "transaction_time" && typeof value === "string") {
    return formatDateTime(value);
  }
  if ((fieldName === "expense_type" || fieldName === "expense_type_candidate") && typeof value === "string") {
    return formatExpenseType(value);
  }
  if ((fieldName === "document_family" || fieldName === "material_type") && typeof value === "string") {
    return formatMaterialType(value as MaterialType);
  }
  if (fieldName === "classification_confidence" && typeof value === "number") {
    return `${Math.round(value * 100)}%`;
  }
  if (fieldName === "is_reimbursement_voucher" && typeof value === "boolean") {
    return value ? "是" : "否";
  }
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  return JSON.stringify(value);
}

function findPendingLinkageItem(
  summary: TaskMemberWorkbenchSummary,
  materialId: string | undefined,
): PendingSupportingMaterialLinkageItem | null {
  if (!materialId) {
    return null;
  }
  return summary.pending_supporting_material_linkage_items.find((item) => item.material_id === materialId) ?? null;
}

export function MemberMaterialDetailPage() {
  const session = useAuthSession();
  const navigate = useNavigate();
  const { materialId } = useParams();
  const [searchParams] = useSearchParams();
  const taskId = searchParams.get("taskId") ?? "";
  const { showError, showSuccess, showWarning } = useSnackbar();
  const [detailState, setDetailState] = useState<DetailState>({ status: "loading" });
  const [reloadVersion, setReloadVersion] = useState(0);
  const [materialTypeDraft, setMaterialTypeDraft] = useState<MaterialType | null>(null);
  const [savingMaterialType, setSavingMaterialType] = useState(false);
  const [retryingRecognition, setRetryingRecognition] = useState(false);
  const [openingOriginal, setOpeningOriginal] = useState(false);

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
        const item = pickItemByMaterialId(summary, materialId);
        if (cancelled) {
          return;
        }
        setDetailState({ status: "ready", task, summary, item });
        if (item) {
          setMaterialTypeDraft(item.material.material_type);
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
  }, [materialId, reloadVersion, session, taskId]);

  const item = detailState.status === "ready" ? detailState.item : null;
  const task = detailState.status === "ready" ? detailState.task : null;
  const currentTaskId = task?.id ?? taskId;
  const pendingLinkageItem = detailState.status === "ready"
    ? findPendingLinkageItem(detailState.summary, materialId)
    : null;
  const abnormalReasons = useMemo(() => (item ? collectAbnormalReasons(item) : []), [item]);

  useEffect(() => {
    if (!task || !item || item.material.material_type !== "invoice") {
      return;
    }
    if (item.invoice) {
      void navigate(buildInvoiceDetailPath(task.id, item.invoice.id), { replace: true });
      return;
    }
    void navigate(buildMaterialInvoiceDetailPath(task.id, item.material.material_id), { replace: true });
  }, [item, navigate, task]);

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

  async function handleViewOriginal() {
    if (!item) {
      return;
    }
    setOpeningOriginal(true);
    try {
      const file = await trmsApi.downloadMaterialContent(item.material.material_id);
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

  if (!session || session.role !== "member") {
    return null;
  }

  const materialType = item?.material.material_type;
  const pageConfig = materialType && materialType !== "invoice" ? MATERIAL_PAGE_CONFIG[materialType] : null;

  return (
    <RoleWorkspace
      header={(
        <PageHeader
        eyebrow="成员材料处理"
        title={pageConfig?.title ?? "材料详情"}
        description={pageConfig?.description ?? "按当前材料类型展示对应识别字段和处理动作，不再统一落到发票页。"}
        actions={(
          <Button
            component={Link}
            to={taskId ? `/member/invoices/workbench?taskId=${encodeURIComponent(taskId)}` : "/member/invoices/workbench"}
            variant="outlined"
          >
            返回工作台
          </Button>
        )}
        />
      )}
    >

      {detailState.status === "loading" ? (
        <SectionCard title="正在加载材料" description="正在读取当前材料、识别状态和归属上下文。" />
      ) : null}

      {detailState.status === "error" ? <ApiErrorNotice error={detailState.error} /> : null}

      {detailState.status === "ready" && !item ? (
        <EmptyState
          title="没有找到这份材料"
          description="它可能不属于当前任务，或者当前账号没有查看权限。"
          action={<Button component={Link} variant="contained" to={taskId ? `/member/invoices/workbench?taskId=${encodeURIComponent(taskId)}` : "/member/invoices/workbench"}>返回工作台</Button>}
        />
      ) : null}

      {detailState.status === "ready" && item && pageConfig ? (
        <>
          <SectionCard
            title="当前状态"
            description={pageConfig.nextStep}
            action={<StatusBadge tone={abnormalReasons.length > 0 ? "warning" : "success"}>{abnormalReasons.length > 0 ? `${abnormalReasons.length} 项待处理` : "状态稳定"}</StatusBadge>}
          >
            <dl className="task-meta-grid member-status-meta-grid">
              <div><dt>原始文件</dt><dd>{item.material.original_filename}</dd></div>
              <div><dt>材料类型</dt><dd>{formatMaterialType(item.material.material_type)}</dd></div>
              <div><dt>识别状态</dt><dd>{item.recognition ? formatRecognitionStatus(item.recognition.status) : "暂无识别"}</dd></div>
              <div><dt>校验状态</dt><dd>{formatValidationStatus(item.material.validation_status)}</dd></div>
              <div><dt>上传时间</dt><dd>{formatDateTime(item.material.created_at)}</dd></div>
              <div><dt>当前队列</dt><dd>{item.queue_group === "ready" ? "已就绪" : "仍需处理"}</dd></div>
            </dl>
            {abnormalReasons.length > 0 ? (
              <ul className="member-status-message-list" aria-label="当前材料待处理事项">
                {abnormalReasons.map((reason) => <li key={reason}>{reason}</li>)}
              </ul>
            ) : (
              <p className="field-hint">当前没有识别失败或校验阻塞。</p>
            )}
            <div className="inline-actions">
              <Button type="button" variant="outlined" disabled={openingOriginal} onClick={() => { void handleViewOriginal(); }}>
                {openingOriginal ? "正在打开..." : "查看原文件"}
              </Button>
              <Button type="button" variant="outlined" disabled={retryingRecognition} onClick={() => { void handleRecognitionRetry(); }}>
                {retryingRecognition ? "重新识别中..." : "运行重新识别"}
              </Button>
            </div>
          </SectionCard>

          <SectionCard title="材料类型" description="识别错类型时先在这里修正；改成发票后会自动切到发票处理页。">
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

          <SectionCard title="识别判断" description="这里展示系统先做出的类型判断和费用归类建议。">
            <ul className="member-status-message-list" aria-label="当前材料识别判断">
              {CLASSIFICATION_FIELD_ORDER.map((fieldName) => (
                <li key={fieldName}>
                  <strong>{MATERIAL_FIELD_LABELS[fieldName]}</strong>
                  <span>{formatRecognizedFieldValue(fieldName, item.recognition?.recognized_fields[fieldName]?.value ?? null)}</span>
                </li>
              ))}
            </ul>
          </SectionCard>

          <SectionCard title="已识别字段" description="不同材料类型只展示该类型真正需要的字段。">
            <ul className="member-status-message-list" aria-label={`${formatMaterialType(item.material.material_type)}识别字段`}>
              {pageConfig.fields.map((fieldName) => (
                <li key={fieldName}>
                  <strong>{MATERIAL_FIELD_LABELS[fieldName] ?? fieldName}</strong>
                  <span>{formatRecognizedFieldValue(fieldName, item.recognition?.recognized_fields[fieldName]?.value ?? null)}</span>
                </li>
              ))}
            </ul>
          </SectionCard>

          <SectionCard title="归属发票参考" description="当前页只展示候选归属和跳转入口，真正的归属确认仍在工作台中完成。">
            {pendingLinkageItem ? (
              <>
                {pendingLinkageItem.linked_invoices.length > 0 ? (
                  <>
                    <p className="field-hint">
                      当前材料已关联到 {pendingLinkageItem.linked_invoices.length} 张发票；如果还需要补到其他发票，继续在下方候选列表里处理。
                    </p>
                    <ul className="invoice-material-list" aria-label="当前已关联发票列表">
                      {pendingLinkageItem.linked_invoices.map((linkedInvoice) => (
                        <li key={linkedInvoice.invoice_id}>
                          <InvoiceSummaryRow
                            filename={item.material.original_filename}
                            invoiceNumber={linkedInvoice.invoice_number}
                            amountLabel={formatCurrencyFromCents(linkedInvoice.amount_cents)}
                            validationLabel="已关联"
                            validationTone="success"
                            supportingMaterialCount={1}
                            statusHint={`费用类型 ${formatExpenseType(linkedInvoice.expense_type)}`}
                            trailingContent={<StatusBadge tone="success">已关联</StatusBadge>}
                            action={{
                              ariaLabel: `已关联发票 ${linkedInvoice.invoice_number}`,
                              onClick: () => { void navigate(buildInvoiceDetailPath(currentTaskId, linkedInvoice.invoice_id)); },
                            }}
                          />
                        </li>
                      ))}
                    </ul>
                  </>
                ) : null}
                <p className="field-hint">
                  {pendingLinkageItem.pending_reason === "multiple_candidates"
                    ? "系统找到仍可继续关联的候选发票，尚未自动补齐全部归属。"
                    : "系统暂时没有找到安全候选发票，请先补发票或回工作台处理。"}
                </p>
                {pendingLinkageItem.candidate_invoices.length > 0 ? (
                  <ul className="invoice-material-list" aria-label="候选归属发票列表">
                    {pendingLinkageItem.candidate_invoices.map((candidate) => (
                      <li key={candidate.invoice_id}>
                        <InvoiceSummaryRow
                          filename={item.material.original_filename}
                          invoiceNumber={candidate.invoice_number}
                          amountLabel={formatCurrencyFromCents(candidate.amount_cents)}
                          validationLabel="候选归属"
                          validationTone="neutral"
                          supportingMaterialCount={0}
                          statusHint={`费用类型 ${formatExpenseType(candidate.expense_type)}`}
                          trailingContent={<StatusBadge tone="info">{formatExpenseType(candidate.expense_type)}</StatusBadge>}
                          action={{
                            ariaLabel: `候选发票 ${candidate.invoice_number}`,
                            onClick: () => { void navigate(buildInvoiceDetailPath(currentTaskId, candidate.invoice_id)); },
                          }}
                        />
                      </li>
                    ))}
                  </ul>
                ) : null}
              </>
            ) : (
              <p className="field-hint">当前材料没有待处理的归属候选；若你已在工作台完成归属，这里不会重复展示发票级编辑表单。</p>
            )}
          </SectionCard>
        </>
      ) : null}
    </RoleWorkspace>
  );
}
