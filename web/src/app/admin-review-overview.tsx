import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { ApiErrorNotice } from "../components/ApiErrorNotice";
import { trmsApi } from "../lib/api/trms";
import type {
  ConfirmationRecord,
  ExpenseSplitRecord,
  RecognitionTaskRecord,
  RecognitionTaskStatus,
  ReimbursementTask,
  TaskReviewSummary,
  ValidationResult,
} from "../lib/api/types";
import {
  describeRecognitionFailure,
  formatConfirmationStatus,
  formatExpenseType,
  formatMaterialType,
  formatMemberLabel,
  formatSubmissionChannel,
  formatTaskStatus,
  formatValidationRule,
  formatValidationSeverity,
  formatValidationStatus,
} from "../lib/ui-text";
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

const RECOGNITION_STATUS_LABELS: Record<RecognitionTaskStatus, string> = {
  pending: "识别中",
  succeeded: "识别成功",
  failed: "识别失败",
  needs_confirmation: "待人工确认",
};

function formatRecognitionStatus(status: RecognitionTaskStatus) {
  return RECOGNITION_STATUS_LABELS[status];
}

function formatCurrencyFromCents(cents: number) {
  return `￥${(cents / 100).toFixed(2)}`;
}

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

function buildInvoiceReviewCards(summary: TaskReviewSummary) {
  const materialItemsById = new Map(
    summary.materials.map((item) => [item.material.id, item] as const),
  );

  return [...summary.invoices]
    .map((invoiceItem) => ({
      invoiceItem,
      invoiceMaterial: materialItemsById.get(invoiceItem.invoice.material_id) ?? null,
    }))
    .sort((left, right) => right.invoiceItem.invoice.updated_at.localeCompare(left.invoiceItem.invoice.updated_at));
}

function buildMaterialReviewItems(summary: TaskReviewSummary) {
  return [...summary.materials].sort((left, right) =>
    right.material.created_at.localeCompare(left.material.created_at),
  );
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

function buildRecognitionBadgeClass(recognition: RecognitionTaskRecord | null) {
  if (recognition === null) {
    return "member-status-chip-pending";
  }
  if (recognition.status === "succeeded") {
    return "member-status-chip-succeeded";
  }
  if (recognition.status === "failed") {
    return "member-status-chip-failed";
  }
  return "member-status-chip-needs_confirmation";
}

function buildValidationBadgeClass(validation: ValidationResult) {
  if (validation.status === "failed") {
    return "member-status-chip-failed";
  }
  if (validation.status === "pending") {
    return "member-status-chip-pending";
  }
  return "member-status-chip-passed";
}

function buildConfirmationBadgeClass(confirmation: ConfirmationRecord | null) {
  if (confirmation === null || confirmation.status === "pending") {
    return "member-status-chip-pending";
  }
  if (confirmation.status === "disputed") {
    return "member-status-chip-failed";
  }
  return "member-status-chip-passed";
}

export function AdminReviewOverviewPage() {
  const session = useAuthSession();
  const { taskId } = useParams<{ taskId: string }>();
  const [state, setState] = useState<ReviewPageState>({ status: "loading" });

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

  const invoiceReviewCards = useMemo(
    () => (state.status === "ready" ? buildInvoiceReviewCards(state.reviewSummary) : []),
    [state],
  );
  const materialReviewItems = useMemo(
    () => (state.status === "ready" ? buildMaterialReviewItems(state.reviewSummary) : []),
    [state],
  );

  if (!session || session.role !== "admin") {
    return null;
  }

  if (!taskId) {
    return (
      <div className="page-stack">
        <section className="status-card">
          <p className="eyebrow">复核总览</p>
          <h2>任务标识缺失</h2>
          <p>暂时无法读取该任务，请从任务列表重新进入。</p>
        </section>
      </div>
    );
  }

  const task = state.status === "ready" ? state.task : null;
  const isForeignTask = task ? task.administrator_id !== session.actorId : false;
  const visibleTask = state.status === "ready" && !isForeignTask ? state.task : null;
  const visibleSummary = state.status === "ready" && !isForeignTask ? state.reviewSummary : null;
  const visibleOverdueSummary = state.status === "ready" && !isForeignTask ? state.overdueSummary : null;
  const anomalyItems = visibleSummary && visibleOverdueSummary
    ? buildReviewAnomalies(visibleSummary, visibleOverdueSummary)
    : [];
  const outstandingMemberIds = visibleSummary
    ? buildOutstandingMemberIds(visibleSummary)
    : [];
  const disputedItems = visibleSummary
    ? buildDisputedConfirmationItems(visibleSummary)
    : [];

  return (
    <div className="page-stack">
      <section className="status-card admin-review-hero">
        <p className="eyebrow">复核总览</p>
        <h2>管理员复核总览</h2>
        <p>
          这里集中查看当前任务的材料风险、待确认费用、成员异议和导出准备情况。
        </p>
        <div className="inline-actions">
          <Link className="route-link route-link-secondary" to="/admin">
            返回任务列表
          </Link>
          <Link className="route-link route-link-secondary" to={`/admin/tasks/${taskId}`}>
            返回任务详情
          </Link>
          <Link className="route-link" to={`/admin/tasks/${taskId}/corrections`}>
            处理更正与提醒
          </Link>
          <Link className="route-link" to={`/admin/tasks/${taskId}/invoices`}>
            录入或更正发票
          </Link>
          <Link className="route-link route-link-secondary" to={`/admin/tasks/${taskId}/splits`}>
            编辑费用分摊
          </Link>
        </div>
      </section>

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
                <p className="task-card-id">任务编号 {visibleTask.id}</p>
                <h2>{visibleTask.competition_name}</h2>
              </div>
              <span className={`status-chip task-status-chip task-status-${visibleTask.status}`}>
                {formatTaskStatus(visibleTask.status)}
              </span>
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
              <span className="status-chip">{anomalyItems.length} 类重点项</span>
            </div>
            {anomalyItems.length > 0 ? (
              <ul className="task-anomaly-list" aria-label="复核风险摘要">
                {anomalyItems.map((item) => (
                  <li key={item.label}>
                    <strong>{item.label}</strong>
                    <span
                      className={`status-chip ${
                        item.tone === "failed" ? "member-status-chip-failed" : "member-status-chip-pending"
                      }`}
                    >
                      {item.count}
                    </span>
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
                      {memberId}
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
                        {split.member_id} / {invoiceNumber} / {formatCurrencyFromCents(split.amount_cents)}
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
              <span
                className={`status-chip ${
                  visibleSummary.pending_assignment_materials.length > 0
                    ? "member-status-chip-failed"
                    : "member-status-chip-passed"
                }`}
              >
                {visibleSummary.pending_assignment_materials.length} 份
              </span>
            </div>
            {visibleSummary.pending_assignment_materials.length > 0 ? (
              <ul className="admin-review-record-list" aria-label="待归属材料列表">
                {visibleSummary.pending_assignment_materials.map((material) => (
                  <li key={material.id} className="admin-review-record-card">
                    <div className="task-card-header">
                      <div>
                        <p className="task-card-id">材料编号 {material.id}</p>
                        <h3>{material.original_filename}</h3>
                      </div>
                      <span className="status-chip member-status-chip-failed">待归属</span>
                    </div>
                    <div className="admin-review-inline-metadata">
                      <span className="token-chip">{formatMaterialType(material.material_type)}</span>
                      <span className="token-chip">{formatSubmissionChannel(material.channel)}</span>
                    </div>
                    <div className="task-meta-grid admin-review-meta-grid">
                      <div>
                        <dt>任务提示</dt>
                        <dd>{material.task_id_hint ?? "未提供"}</dd>
                      </div>
                      <div>
                        <dt>成员提示</dt>
                        <dd>{material.submitter_id_hint ?? "未提供"}</dd>
                      </div>
                      <div>
                        <dt>上传时间</dt>
                        <dd>{formatDateTime(material.created_at)}</dd>
                      </div>
                      <div>
                        <dt>文件哈希</dt>
                        <dd>{material.sha256.slice(0, 12)}...</dd>
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="field-hint">当前任务提示下没有待归属材料。</p>
            )}
          </section>

          <section className="status-card admin-review-panel">
            <div className="admin-form-header">
              <div>
                <p className="eyebrow">Materials</p>
                <h2>材料与识别状态</h2>
              </div>
              <span className="status-chip">{materialReviewItems.length} 份材料</span>
            </div>
            {materialReviewItems.length > 0 ? (
              <ul className="admin-review-record-list" aria-label="任务材料列表">
                {materialReviewItems.map((item) => {
                  const recognition = item.latest_recognition;
                  const linkedInvoiceId = item.invoice_id;
                  const supportingInvoiceIds = item.supporting_invoice_ids;

                  return (
                    <li key={item.material.id} className="admin-review-record-card">
                      <div className="task-card-header">
                        <div>
                          <p className="task-card-id">材料编号 {item.material.id}</p>
                          <h3>{item.material.original_filename}</h3>
                        </div>
                        <span className={`status-chip ${buildRecognitionBadgeClass(recognition)}`}>
                          {recognition ? formatRecognitionStatus(recognition.status) : "未触发识别"}
                        </span>
                      </div>
                      <div className="admin-review-inline-metadata">
                        <span className="token-chip">{formatMaterialType(item.material.material_type)}</span>
                        <span className="token-chip">{formatSubmissionChannel(item.material.channel)}</span>
                        <span className="token-chip">{formatMemberLabel(item.material.submitter_id)}</span>
                      </div>
                      <div className="task-meta-grid admin-review-meta-grid">
                        <div>
                          <dt>主发票</dt>
                          <dd>{linkedInvoiceId ?? "未录入发票"}</dd>
                        </div>
                        <div>
                          <dt>辅助归属到</dt>
                          <dd>{supportingInvoiceIds.length > 0 ? supportingInvoiceIds.join("、") : "无"}</dd>
                        </div>
                        <div>
                          <dt>上传时间</dt>
                          <dd>{formatDateTime(item.material.created_at)}</dd>
                        </div>
                        <div>
                          <dt>识别原始状态</dt>
                          <dd>{recognition?.status ?? "无记录"}</dd>
                        </div>
                      </div>
                      <div className="admin-review-subsection">
                        <h4>识别摘要</h4>
                        {recognition ? (
                          <ul className="admin-review-list">
                            <li>
                              <strong>最近识别状态</strong>
                              <span>{formatRecognitionStatus(recognition.status)}</span>
                            </li>
                            {recognition.failure ? (
                              <li>
                                <strong>识别提示</strong>
                                <span>{describeRecognitionFailure(recognition.failure)}</span>
                              </li>
                            ) : null}
                            <li>
                              <strong>低置信度字段数</strong>
                              <span>
                                {
                                  Object.values(recognition.recognized_fields).filter(
                                    (field) => field.status === "needs_confirmation",
                                  ).length
                                }
                              </span>
                            </li>
                          </ul>
                        ) : (
                          <p className="field-hint">当前材料尚无识别任务结果。</p>
                        )}
                      </div>
                      {item.material.material_type === "invoice" ? (
                        <div className="inline-actions">
                          <Link
                            className="route-link route-link-secondary"
                            to={`/admin/tasks/${taskId}/invoices?materialId=${encodeURIComponent(item.material.id)}`}
                          >
                            更正识别字段
                          </Link>
                        </div>
                      ) : null}
                    </li>
                  );
                })}
              </ul>
            ) : (
              <p className="field-hint">当前任务还没有已归档材料。</p>
            )}
          </section>

          <section className="status-card admin-review-panel">
            <div className="admin-form-header">
              <div>
                <p className="eyebrow">Invoices</p>
                <h2>发票、校验与分摊确认</h2>
              </div>
              <span className="status-chip">{invoiceReviewCards.length} 张发票</span>
            </div>
            {invoiceReviewCards.length > 0 ? (
              <ul className="admin-review-record-list" aria-label="发票复核列表">
                {invoiceReviewCards.map(({ invoiceItem, invoiceMaterial }) => {
                  const abnormalValidations = invoiceItem.validations.filter(
                    (validation) => validation.status !== "passed" && validation.status !== "not_applicable",
                  );

                  return (
                    <li key={invoiceItem.invoice.id} className="admin-review-record-card">
                      <div className="task-card-header">
                        <div>
                          <p className="task-card-id">发票编号 {invoiceItem.invoice.id}</p>
                          <h3>{invoiceItem.invoice.invoice_number}</h3>
                        </div>
                        <span className="status-chip">
                          {formatCurrencyFromCents(invoiceItem.invoice.amount_cents)}
                        </span>
                      </div>
                      <div className="admin-review-inline-metadata">
                        <span className="token-chip">
                          {formatExpenseType(invoiceItem.invoice.expense_type)}
                        </span>
                        <span className="token-chip">{formatMemberLabel(invoiceMaterial?.material.submitter_id)}</span>
                        <span className="token-chip">
                          附件 {invoiceItem.supporting_material_ids.length} 份
                        </span>
                      </div>
                      <div className="task-meta-grid admin-review-meta-grid">
                        <div>
                          <dt>交易时间</dt>
                          <dd>
                            {invoiceItem.invoice.transaction_time
                              ? formatDateTime(invoiceItem.invoice.transaction_time)
                              : invoiceItem.invoice.issue_date ?? "未录入"}
                          </dd>
                        </div>
                        <div>
                          <dt>抬头 / 税号</dt>
                          <dd>
                            {invoiceItem.invoice.buyer_name} / {invoiceItem.invoice.tax_number}
                          </dd>
                        </div>
                        <div>
                          <dt>发票材料</dt>
                          <dd>{invoiceItem.invoice.material_id}</dd>
                        </div>
                        <div>
                          <dt>分摊条目</dt>
                          <dd>{invoiceItem.splits.length}</dd>
                        </div>
                      </div>
                      <div className="admin-review-subsection">
                        <h4>校验结果</h4>
                        {invoiceItem.validations.length > 0 ? (
                          <ul className="admin-review-list">
                            {abnormalValidations.length > 0
                              ? abnormalValidations.map((validation) => (
                                  <li key={validation.id}>
                                    <strong>
                                      {formatValidationSeverity(validation.severity)} / {formatValidationRule(validation.rule_code)}
                                    </strong>
                                    <span
                                      className={`status-chip ${buildValidationBadgeClass(validation)}`}
                                    >
                                      {formatValidationStatus(validation.status)}
                                    </span>
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
                      </div>
                      <div className="admin-review-subsection">
                        <h4>分摊与成员确认</h4>
                        {invoiceItem.splits.length > 0 ? (
                          <ul className="admin-review-list">
                            {invoiceItem.splits.map(({ split, confirmation }) => (
                              <li key={split.id}>
                                <strong>
                                  {formatMemberLabel(split.member_id)} / {formatCurrencyFromCents(split.amount_cents)}
                                </strong>
                                <span
                                  className={`status-chip ${buildConfirmationBadgeClass(confirmation)}`}
                                >
                                  {confirmation ? formatConfirmationStatus(confirmation.status) : "未提交确认"}
                                </span>
                                <span>版本 {split.version}</span>
                                {split.note ? <span>备注：{split.note}</span> : null}
                                {confirmation?.dispute_reason ? (
                                  <span>异议原因：{confirmation.dispute_reason}</span>
                                ) : null}
                              </li>
                            ))}
                          </ul>
                        ) : (
                          <p className="field-hint">当前发票还没有分摊记录。</p>
                        )}
                      </div>
                      <div className="inline-actions">
                        <Link
                          className="route-link"
                          to={
                            `/admin/tasks/${taskId}/invoices?materialId=${
                              encodeURIComponent(invoiceItem.invoice.material_id)
                            }`
                          }
                        >
                          更正金额与字段
                        </Link>
                        <Link
                          className="route-link route-link-secondary"
                          to={`/admin/tasks/${taskId}/splits?invoiceId=${encodeURIComponent(invoiceItem.invoice.id)}`}
                        >
                          调整分摊
                        </Link>
                      </div>
                    </li>
                  );
                })}
              </ul>
            ) : (
              <p className="field-hint">当前任务还没有发票可供复核。</p>
            )}
          </section>
        </>
      ) : null}
    </div>
  );
}
