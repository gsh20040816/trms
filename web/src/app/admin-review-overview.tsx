import { useEffect, useMemo, useState } from "react";
import { Link as RouterLink, useParams } from "react-router-dom";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import ButtonBase from "@mui/material/ButtonBase";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";

import { ApiErrorNotice } from "../components/ApiErrorNotice";
import { InvoiceSummaryRow } from "../components/invoice-summary-row";
import { PageHeader, StatusBadge } from "../components/dashboard";
import { trmsApi } from "../lib/api/trms";
import type {
  ConfirmationRecord,
  ExpenseSplitRecord,
  RecognitionTaskRecord,
  ReimbursementTask,
  TaskReviewSummary,
  TaskReviewSummaryInvoiceItem,
  TaskReviewSummaryMaterialItem,
  ValidationResult,
} from "../lib/api/types";
import { formatCurrencyFromCents, formatInvoiceAmountFromCents } from "../lib/currency";
import {
  describeRecognitionFailure,
  formatConfirmationStatus,
  formatExpenseType,
  formatFieldLabel,
  formatMaterialType,
  formatMemberLabel,
  formatRecognitionStatus,
  formatSubmissionChannel,
  formatTaskStatus,
  formatValidationRule,
  formatValidationSeverity,
  formatValidationStatus,
} from "../lib/ui-text";
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

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
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

function describeRecognitionFieldValue(value: unknown, fieldName?: string) {
  if (fieldName === "amount_cents") {
    return typeof value === "number" ? formatInvoiceAmountFromCents(value) : formatInvoiceAmountFromCents(null);
  }
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  if (value === null || value === undefined) {
    return "未识别";
  }
  return "复杂结构";
}

export function AdminReviewOverviewPage() {
  const session = useAuthSession();
  const { taskId } = useParams<{ taskId: string }>();
  const [state, setState] = useState<ReviewPageState>({ status: "loading" });
  const [selectedMaterialId, setSelectedMaterialId] = useState("");
  const [previewState, setPreviewState] = useState<ReviewPreviewState>({ status: "idle" });
  const [detailTab, setDetailTab] = useState<ReviewDetailTab>("preview");

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
        setSelectedMaterialId((current) => pickSelectedMaterialId(detailItems, current));
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
  }, [session, taskId]);

  const detailItems = useMemo(
    () => (state.status === "ready" ? buildReviewDetailItems(state.reviewSummary) : []),
    [state],
  );

  const task = state.status === "ready" ? state.task : null;
  const isForeignTask = task ? task.administrator_id !== session?.actorId : false;
  const visibleTask = state.status === "ready" && !isForeignTask ? state.task : null;
  const visibleSummary = state.status === "ready" && !isForeignTask ? state.reviewSummary : null;
  const visibleOverdueSummary = state.status === "ready" && !isForeignTask ? state.overdueSummary : null;
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
        <section className="status-card">
          <p className="eyebrow">复核总览</p>
          <h2>任务标识缺失</h2>
          <p>暂时无法读取该任务，请从任务列表重新进入。</p>
        </section>
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
        <section className="status-card admin-review-panel">
          <p className="eyebrow">Loading</p>
          <h2>正在加载复核总览</h2>
          <p>正在读取任务详情、复核摘要和逾期确认信息，请稍候。</p>
        </section>
      ) : null}

      {state.status === "error" ? <ApiErrorNotice error={state.error} /> : null}

      {state.status === "ready" && isForeignTask ? (
        <section className="status-card admin-review-panel">
          <p className="eyebrow">访问范围</p>
          <h2>当前任务不属于此管理员</h2>
          <p>你当前没有查看该任务的权限，如需访问请联系对应负责人。</p>
        </section>
      ) : null}

      {visibleTask && visibleSummary && visibleOverdueSummary ? (
        <>
          <section className="status-card admin-review-panel">
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
          </section>

          <section className="status-card admin-review-panel">
            <div className="admin-form-header">
              <div>
                <p className="eyebrow">Review Risks</p>
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
                    <li key={memberId} className="token-chip">
                      {formatMemberLabel(memberId)}
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
            {visibleOverdueSummary.overdue_member_ids.length > 0 ? (
              <div className="admin-review-subsection">
                <h4>已逾期未确认成员</h4>
                <ul className="token-list" aria-label="逾期未确认成员">
                  {visibleOverdueSummary.overdue_member_ids.map((memberId) => (
                    <li key={memberId} className="token-chip">
                      {formatMemberLabel(memberId)}
                    </li>
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
                        {formatMemberLabel(split.member_id)} / {invoiceNumber} / {formatCurrencyFromCents(split.amount_cents)}
                      </strong>
                      <span>{confirmation.dispute_reason ?? "未填写异议原因"}</span>
                      <span>提交时间：{formatDateTime(confirmation.updated_at)}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
          </section>

          <section className="status-card admin-review-panel">
            <div className="admin-form-header">
              <div>
                <p className="eyebrow">Pending Assignment</p>
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
                    <div className="task-card-header">
                      <div>
                        <p className="task-card-id">待归属材料</p>
                        <h3>{material.original_filename}</h3>
                      </div>
                      <StatusBadge tone="danger">待归属</StatusBadge>
                    </div>
                    <div className="admin-review-inline-metadata">
                      <span className="token-chip">{formatMaterialType(material.material_type)}</span>
                      <span className="token-chip">{formatSubmissionChannel(material.channel)}</span>
                    </div>
                    <div className="task-meta-grid admin-review-meta-grid">
                      <div>
                        <dt>成员提示</dt>
                        <dd>{material.submitter_id_hint ? formatMemberLabel(material.submitter_id_hint) : "未提供"}</dd>
                      </div>
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
          </section>

          <section className="admin-review-workspace">
            <article className="status-card admin-task-detail-panel admin-review-list-panel">
              <div className="admin-form-header">
                <div>
                  <p className="eyebrow">Materials</p>
                  <h2>材料审核列表</h2>
                </div>
                <StatusBadge tone="info">{detailItems.length} 份材料</StatusBadge>
              </div>
              <p className="field-hint">
                先从左侧选中当前要处理的材料，再在右侧同页查看原件、识别字段、校验异常和分摊去向。
              </p>
              {detailItems.length > 0 ? (
                <ul className="invoice-material-list" aria-label="材料审核列表">
                  {detailItems.map((item) => {
                    const material = item.materialItem.material;
                    const recognition = item.materialItem.latest_recognition;
                    const failedValidationCount = item.primaryInvoice?.validations.filter(
                      (validation) => validation.status === "failed",
                    ).length ?? 0;
                    const pendingValidationCount = item.primaryInvoice?.validations.filter(
                      (validation) => validation.status === "pending",
                    ).length ?? 0;
                    const isSelected = material.id === selectedMaterialId;
                    return (
                      <li key={material.id}>
                        <ButtonBase
                          className={`invoice-material-button ${isSelected ? "invoice-material-button-selected" : ""}`}
                          aria-pressed={isSelected}
                          onClick={() => {
                            setSelectedMaterialId(material.id);
                          }}
                          sx={{ display: "block", width: "100%", textAlign: "left", borderRadius: 2 }}
                        >
                          <div className="task-card-header">
                            <div>
                              <p className="task-card-id">材料摘要</p>
                              <h3>{material.original_filename}</h3>
                            </div>
                            <StatusBadge tone={buildRecognitionBadgeTone(recognition)}>
                              {recognition ? formatRecognitionStatus(recognition.status) : "未触发识别"}
                            </StatusBadge>
                          </div>
                          <div className="admin-review-inline-metadata">
                            <span className="token-chip">{formatMaterialType(material.material_type)}</span>
                            <span className="token-chip">{formatSubmissionChannel(material.channel)}</span>
                            <span className="token-chip">{formatMemberLabel(material.submitter_id)}</span>
                          </div>
                          <dl className="task-meta-grid invoice-editor-summary-grid">
                            <div>
                              <dt>主发票</dt>
                              <dd>{describeInvoiceReference(item.primaryInvoice)}</dd>
                            </div>
                            <div>
                              <dt>关联发票</dt>
                              <dd>{item.relatedInvoices.length}</dd>
                            </div>
                            <div>
                              <dt>校验异常</dt>
                              <dd>失败 {failedValidationCount} 条，待确认 {pendingValidationCount} 条</dd>
                            </div>
                            <div>
                              <dt>上传时间</dt>
                              <dd>{formatDateTime(material.created_at)}</dd>
                            </div>
                          </dl>
                        </ButtonBase>
                      </li>
                    );
                  })}
                </ul>
              ) : (
                <p className="field-hint">当前任务还没有已归档材料。</p>
              )}
            </article>

            <article className="status-card admin-form-card admin-review-detail-panel" aria-label="当前材料详情">
              {selectedMaterial ? (
                <>
                  <div className="admin-form-header">
                    <div>
                      <p className="eyebrow">Selected Material</p>
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
                    <span className="token-chip">{formatMaterialType(selectedMaterial.material_type)}</span>
                    <span className="token-chip">{formatSubmissionChannel(selectedMaterial.channel)}</span>
                    <span className="token-chip">{formatMemberLabel(selectedMaterial.submitter_id)}</span>
                    {selectedInvoice ? (
                      <span className="token-chip">{formatExpenseType(selectedInvoice.invoice.expense_type)}</span>
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
                              <p className="field-hint">当前环境无法直接显示 PDF 预览，但材料内容已成功加载。</p>
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
                                    {describeRecognitionFieldValue(field.value, fieldName)}
                                  </p>
                                  <dl className="task-meta-grid admin-review-detail-field-grid">
                                    <div>
                                      <dt>来源</dt>
                                      <dd>{field.source}</dd>
                                    </div>
                                    <div>
                                      <dt>置信度</dt>
                                      <dd>{Math.round(field.confidence * 100)}%</dd>
                                    </div>
                                    <div>
                                      <dt>状态</dt>
                                      <dd>{field.status === "needs_confirmation" ? "待人工确认" : "可直接采用"}</dd>
                                    </div>
                                    <div>
                                      <dt>更新时间</dt>
                                      <dd>{field.updated_at ? formatDateTime(field.updated_at) : "暂无"}</dd>
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
                      <section className="admin-review-subsection">
                        <h4>分摊去向与成员确认</h4>
                        {selectedInvoice ? (
                          selectedInvoice.splits.length > 0 ? (
                            <ul className="admin-review-list" aria-label="当前材料分摊列表">
                              {selectedInvoice.splits.map(({ split, confirmation }) => (
                                <li key={split.id}>
                                  <strong>
                                    {formatMemberLabel(split.member_id)} / {formatCurrencyFromCents(split.amount_cents)}
                                  </strong>
                                  <StatusBadge tone={buildConfirmationBadgeTone(confirmation)}>
                                    {confirmation ? formatConfirmationStatus(confirmation.status) : "未提交确认"}
                                  </StatusBadge>
                                  <span>版本 {split.version}</span>
                                  {split.note ? <span>备注：{split.note}</span> : null}
                                  {confirmation?.dispute_reason ? <span>异议原因：{confirmation.dispute_reason}</span> : null}
                                </li>
                              ))}
                            </ul>
                          ) : (
                            <p className="field-hint">当前发票还没有分摊记录。</p>
                          )
                        ) : (
                          <p className="field-hint">当前材料没有直接可编辑的分摊记录；若它属于某张发票，请从对应发票的详情动作进入分摊调整。</p>
                        )}
                      </section>

                      <div className="inline-actions admin-review-action-row">
                        {selectedInvoice ? (
                          <>
                            <Button
                              component={RouterLink}
                              variant="contained"
                              size="small"
                              to={`/admin/tasks/${taskId}/invoices?materialId=${encodeURIComponent(selectedInvoice.invoice.material_id)}`}
                            >
                              更正金额与字段
                            </Button>
                            <Button
                              component={RouterLink}
                              variant="outlined"
                              size="small"
                              to={`/admin/tasks/${taskId}/splits?invoiceId=${encodeURIComponent(selectedInvoice.invoice.id)}`}
                            >
                              调整分摊
                            </Button>
                          </>
                        ) : selectedMaterial.material_type === "invoice" ? (
                          <Button
                            component={RouterLink}
                            variant="contained"
                            size="small"
                            to={`/admin/tasks/${taskId}/invoices?materialId=${encodeURIComponent(selectedMaterial.id)}`}
                          >
                            补录当前发票
                          </Button>
                        ) : relatedInvoices[0] ? (
                          <>
                            <Button
                              component={RouterLink}
                              variant="contained"
                              size="small"
                              to={`/admin/tasks/${taskId}/invoices?materialId=${encodeURIComponent(relatedInvoices[0].invoice.material_id)}`}
                            >
                              查看关联发票
                            </Button>
                            <Button
                              component={RouterLink}
                              variant="outlined"
                              size="small"
                              to={`/admin/tasks/${taskId}/splits?invoiceId=${encodeURIComponent(relatedInvoices[0].invoice.id)}`}
                            >
                              调整关联分摊
                            </Button>
                          </>
                        ) : null}
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
                  <p className="eyebrow">Selected Material</p>
                  <h2>当前没有可查看的材料</h2>
                  <p className="field-hint">当前任务还没有已归档材料，暂时无法进入列表-详情联动复核。</p>
                </>
              )}
            </article>
          </section>
        </>
      ) : null}
    </AdminWorkspaceShell>
  );
}
