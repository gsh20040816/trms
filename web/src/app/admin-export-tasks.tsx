import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { ApiErrorNotice } from "../components/ApiErrorNotice";
import { PageHeader } from "../components/dashboard";
import { trmsApi } from "../lib/api/trms";
import type {
  ExportArtifactFormat,
  ExportArtifactKind,
  FinanceDraftExport,
  MergedPdfExportPlan,
  ReimbursementTask,
  TaskExportBoundary,
  TaskExportCapability,
  TaskExportJobRecord,
  TaskExportJobStatus,
} from "../lib/api/types";
import { formatExportJobStatus, formatTaskStatus } from "../lib/ui-text";
import { AdminWorkspaceShell } from "./admin-workspace-shell";
import { useAuthSession } from "./auth-store";

type ExportPageState =
  | { status: "loading" }
  | { status: "error"; error: unknown }
  | {
      status: "ready";
      task: ReimbursementTask;
      boundary: TaskExportBoundary;
      jobs: TaskExportJobRecord[];
    };

type PreviewState =
  | { status: "idle" }
  | { status: "loading"; title: string }
  | { status: "error"; title: string; error: unknown }
  | {
      status: "ready";
      title: string;
      note: string;
      content: string;
    };

const EXPORT_KIND_LABELS: Record<ExportArtifactKind, string> = {
  reimbursement_summary: "报销汇总表",
  member_details: "成员明细表",
  invoice_details: "发票明细表",
  missing_materials: "缺失材料清单",
  finance_draft: "财务填报草稿",
  merged_pdf: "PDF 合并材料包",
};

const EXPORT_KIND_DESCRIPTIONS: Record<ExportArtifactKind, string> = {
  reimbursement_summary: "按费用类型和成员汇总当前任务金额，适合管理员最终核对。",
  member_details: "按成员展开当前有效分摊明细，不混入已失效历史版本。",
  invoice_details: "列出发票号码、金额、费用类型及异常校验摘要。",
  missing_materials: "按成员和费用列出仍缺失的支付记录、比赛通知或行程材料。",
  finance_draft: "输出项目、报销人、发票及分摊摘要，供人工录入财务系统。",
  merged_pdf: "校验材料并按系统默认顺序合并 PDF/图片，生成可下载的打印材料包。",
};

const EXPORT_FORMAT_LABELS: Record<ExportArtifactFormat, string> = {
  xlsx: "XLSX",
  csv: "CSV",
  json: "在线预览",
  pdf: "PDF",
};

const PREFERRED_JOB_FORMATS: Record<ExportArtifactKind, ExportArtifactFormat> = {
  reimbursement_summary: "xlsx",
  member_details: "xlsx",
  invoice_details: "xlsx",
  missing_materials: "xlsx",
  finance_draft: "xlsx",
  merged_pdf: "pdf",
};

function formatExportKind(kind: ExportArtifactKind) {
  return EXPORT_KIND_LABELS[kind];
}

function formatExportFormat(format: ExportArtifactFormat) {
  return EXPORT_FORMAT_LABELS[format] ?? format.toUpperCase();
}

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function sortJobsByCreatedAtDesc(jobs: TaskExportJobRecord[]) {
  return [...jobs].sort((left, right) =>
    right.created_at.localeCompare(left.created_at) || right.id.localeCompare(left.id),
  );
}

function buildJobStatusTone(status: TaskExportJobStatus) {
  if (status === "succeeded") {
    return "member-status-chip-passed";
  }
  if (status === "failed") {
    return "member-status-chip-failed";
  }
  return "member-status-chip-pending";
}

function buildPreviewDescriptor(capability: TaskExportCapability) {
  if (capability.kind === "merged_pdf") {
    return {
      available: true,
      buttonLabel: "查看 PDF 合并计划",
      placeholderLabel: "合并顺序预览",
    };
  }

  if (capability.kind === "finance_draft") {
    return {
      available: true,
      buttonLabel: "查看草稿预览",
      placeholderLabel: "在线草稿预览",
    };
  }

  return {
    available: capability.implemented_formats.includes("csv"),
    buttonLabel: "查看在线预览",
    placeholderLabel: capability.implemented_formats.includes("csv") ? "在线预览" : "下载入口待开放",
  };
}

function buildPreviewNote(kind: ExportArtifactKind) {
  if (kind === "merged_pdf") {
    return "当前展示的是实际导出将采用的材料顺序与可读性检查结果；正式 PDF 请通过导出任务下载。";
  }
  if (kind === "finance_draft") {
    return "当前展示的是在线草稿预览，正式下载入口会在导出产物生成后提供。";
  }
  return "当前展示的是在线预览，正式下载入口会在导出产物生成后提供。";
}

function stringifyStructuredPreview(payload: FinanceDraftExport | MergedPdfExportPlan) {
  return JSON.stringify(payload, null, 2);
}

function formatFileSize(sizeBytes: number) {
  if (sizeBytes < 1024) {
    return `${sizeBytes} B`;
  }
  if (sizeBytes < 1024 * 1024) {
    return `${(sizeBytes / 1024).toFixed(1)} KB`;
  }
  return `${(sizeBytes / (1024 * 1024)).toFixed(1)} MB`;
}

function triggerBrowserDownload(blob: Blob, filename: string) {
  const objectUrl = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = objectUrl;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(objectUrl);
}

export function AdminExportTasksPage() {
  const session = useAuthSession();
  const { taskId } = useParams<{ taskId: string }>();
  const [pageState, setPageState] = useState<ExportPageState>({ status: "loading" });
  const [actionError, setActionError] = useState<unknown>(null);
  const [actionFeedback, setActionFeedback] = useState<string | null>(null);
  const [previewState, setPreviewState] = useState<PreviewState>({ status: "idle" });
  const [activeCreateKind, setActiveCreateKind] = useState<ExportArtifactKind | null>(null);
  const [activePreviewKind, setActivePreviewKind] = useState<ExportArtifactKind | null>(null);
  const [activeDownloadJobId, setActiveDownloadJobId] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadPage() {
      if (!session || session.role !== "admin" || !taskId) {
        return;
      }

      setPageState({ status: "loading" });
      setActionError(null);

      try {
        const [task, boundary, jobs] = await Promise.all([
          trmsApi.getTask(taskId),
          trmsApi.getTaskExportCapabilities(taskId, session.actorId),
          trmsApi.listTaskExportJobs(taskId, session.actorId),
        ]);

        if (cancelled) {
          return;
        }

        setPageState({
          status: "ready",
          task,
          boundary,
          jobs: sortJobsByCreatedAtDesc(jobs),
        });
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
  }, [session, taskId]);

  const latestJobsByKind = useMemo(() => {
    if (pageState.status !== "ready") {
      return new Map<ExportArtifactKind, TaskExportJobRecord>();
    }

    const latest = new Map<ExportArtifactKind, TaskExportJobRecord>();
    for (const job of pageState.jobs) {
      if (!latest.has(job.kind)) {
        latest.set(job.kind, job);
      }
    }
    return latest;
  }, [pageState]);

  if (!session || session.role !== "admin") {
    return null;
  }

  if (!taskId) {
    return (
      <AdminWorkspaceShell
        activeModule="exports"
        header={(
          <PageHeader
            eyebrow="导出打印"
            title="导出任务页面"
            description="生成汇总、明细、草稿和打印材料包。"
          />
        )}
      >
        <section className="status-card">
          <p className="eyebrow">导出任务</p>
          <h2>任务标识缺失</h2>
          <p>暂时无法读取该任务，请从任务列表重新进入。</p>
        </section>
      </AdminWorkspaceShell>
    );
  }

  async function handleCreateJob(kind: ExportArtifactKind) {
    if (!session || pageState.status !== "ready" || !taskId) {
      return;
    }

    setActionError(null);
    setActionFeedback(null);
    setActiveCreateKind(kind);

    try {
      const created = await trmsApi.createTaskExportJob(taskId, {
        actor_id: session.actorId,
        kind,
        format: PREFERRED_JOB_FORMATS[kind],
        parameters: {},
      });
      setPageState({
        ...pageState,
        jobs: sortJobsByCreatedAtDesc([created, ...pageState.jobs]),
      });
      setActionFeedback(
        `${formatExportKind(kind)} 导出任务已创建，当前状态：${formatExportJobStatus(created.status)}。`,
      );
    } catch (error) {
      setActionError(error);
    } finally {
      setActiveCreateKind(null);
    }
  }

  async function handlePreview(kind: ExportArtifactKind) {
    if (!session || pageState.status !== "ready" || !taskId) {
      return;
    }

    setActionError(null);
    setActivePreviewKind(kind);
    setPreviewState({
      status: "loading",
      title: `${formatExportKind(kind)} 即时输出`,
    });

    try {
      let content: string;

      switch (kind) {
        case "reimbursement_summary":
          content = await trmsApi.downloadReimbursementSummaryCsv(taskId, session.actorId);
          break;
        case "member_details":
          content = await trmsApi.downloadMemberDetailsCsv(taskId, session.actorId);
          break;
        case "invoice_details":
          content = await trmsApi.downloadInvoiceDetailsCsv(taskId, session.actorId);
          break;
        case "missing_materials":
          content = await trmsApi.downloadMissingMaterialsCsv(taskId, session.actorId);
          break;
        case "finance_draft":
          content = stringifyStructuredPreview(
            await trmsApi.exportFinanceDraft(taskId, session.actorId),
          );
          break;
        case "merged_pdf":
          content = stringifyStructuredPreview(
            await trmsApi.exportMergedPdfPlan(taskId, session.actorId),
          );
          break;
        default:
          content = "";
      }

      setPreviewState({
        status: "ready",
        title: `${formatExportKind(kind)} 即时输出`,
        note: buildPreviewNote(kind),
        content,
      });
    } catch (error) {
      setPreviewState({
        status: "error",
        title: `${formatExportKind(kind)} 即时输出`,
        error,
      });
    } finally {
      setActivePreviewKind(null);
    }
  }

  async function handleDownload(jobId: string) {
    if (!session) {
      return;
    }

    setActionError(null);
    setActionFeedback(null);
    setActiveDownloadJobId(jobId);

    try {
      const downloaded = await trmsApi.downloadTaskExportArtifact(jobId, session.actorId);
      triggerBrowserDownload(downloaded.blob, downloaded.filename ?? `${jobId}.bin`);
      setActionFeedback(`导出文件 ${downloaded.filename ?? jobId} 已开始下载。`);
    } catch (error) {
      setActionError(error);
    } finally {
      setActiveDownloadJobId(null);
    }
  }

  return (
    <AdminWorkspaceShell
      activeModule="exports"
      taskId={taskId}
      task={pageState.status === "ready" ? pageState.task : null}
      header={(
        <PageHeader
          eyebrow="导出打印"
          title="导出任务页面"
          description="这里用于生成汇总表、成员明细、缺失材料清单和提交草稿，并查看最近一次导出状态。"
          actions={(
            <div className="page-actions">
              <Link className="button button-secondary" to={`/admin/tasks/${taskId}/review`}>
                返回复核总览
              </Link>
              <Link className="button button-secondary" to={`/admin/tasks/${taskId}/corrections`}>
                返回更正与提醒
              </Link>
            </div>
          )}
        />
      )}
    >

      {pageState.status === "loading" ? (
        <section className="status-card admin-review-panel">
          <p className="eyebrow">导出任务</p>
          <h2>正在加载导出边界</h2>
          <p>正在读取任务信息、导出能力和既有导出任务，请稍候。</p>
        </section>
      ) : null}

      {pageState.status === "error" ? <ApiErrorNotice error={pageState.error} /> : null}
      {actionError ? <ApiErrorNotice error={actionError} /> : null}

      {pageState.status === "ready" ? (
        <>
          <section className="status-card admin-review-panel">
            <div className="task-card-header">
              <div>
                <p className="task-card-id">任务编号 {pageState.task.id}</p>
                <h2>{pageState.task.competition_name}</h2>
              </div>
              <span className={`status-chip task-status-chip task-status-${pageState.task.status}`}>
                {formatTaskStatus(pageState.task.status)}
              </span>
            </div>

            <dl className="admin-review-summary-grid export-summary-grid">
              <div>
                <dt>导出门禁</dt>
                <dd>{pageState.boundary.export_allowed ? "已满足" : "未满足"}</dd>
              </div>
              <div>
                <dt>导出方式</dt>
                <dd>{pageState.boundary.execution_mode === "worker" ? "后台生成" : "立即生成"}</dd>
              </div>
              <div>
                <dt>导出任务数</dt>
                <dd>{pageState.jobs.length}</dd>
              </div>
            </dl>

            <p className="status-note">{pageState.boundary.note}</p>

            {!pageState.boundary.export_allowed ? (
              <section className="admin-review-subsection">
                <div className="task-card-header">
                  <div>
                    <p className="task-card-id">导出门禁</p>
                    <h4>当前任务尚未满足导出前置条件</h4>
                  </div>
                  <span className="status-chip member-status-chip-failed">已阻止导出</span>
                </div>
                <ul className="admin-review-list" aria-label="导出阻塞原因">
                  {pageState.boundary.blocking_reasons.map((reason) => (
                    <li key={reason}>
                      <strong>待处理事项</strong>
                      <span>{reason}</span>
                    </li>
                  ))}
                </ul>
              </section>
            ) : null}

            {actionFeedback ? <p className="confirmation-feedback">{actionFeedback}</p> : null}
          </section>

          <section className="admin-review-record-list export-capability-grid" aria-label="导出能力列表">
            {pageState.boundary.supported_exports.map((capability) => {
              const latestJob = latestJobsByKind.get(capability.kind) ?? null;
              const previewDescriptor = buildPreviewDescriptor(capability);
              const preferredFormat = PREFERRED_JOB_FORMATS[capability.kind];
              const isCreating = activeCreateKind === capability.kind;
              const isPreviewing = activePreviewKind === capability.kind;

              return (
                <article key={capability.kind} className="admin-review-record-card export-capability-card">
                  <div className="task-card-header">
                    <div>
                      <p className="task-card-id">
                        首选任务格式 {formatExportFormat(preferredFormat)}
                      </p>
                      <h3>{formatExportKind(capability.kind)}</h3>
                    </div>
                    <span
                      className={`status-chip ${
                        capability.implemented ? "member-status-chip-passed" : "member-status-chip-pending"
                      }`}
                    >
                      {capability.implemented ? "已有即时输出" : "占位能力"}
                    </span>
                  </div>

                  <p>{EXPORT_KIND_DESCRIPTIONS[capability.kind]}</p>

                  <div className="admin-review-inline-metadata">
                    <span className="status-chip">
                      允许格式：{capability.formats.map(formatExportFormat).join(" / ")}
                    </span>
                    <span className="status-chip">
                      在线预览：{previewDescriptor.placeholderLabel}
                    </span>
                    {latestJob ? (
                      <span className={`status-chip ${buildJobStatusTone(latestJob.status)}`}>
                        最近任务：{formatExportJobStatus(latestJob.status)}
                      </span>
                    ) : null}
                  </div>

                  <div className="inline-actions export-action-row">
                    <button
                      className="route-link"
                      type="button"
                      disabled={!pageState.boundary.export_allowed || isCreating}
                      onClick={() => {
                        void handleCreateJob(capability.kind);
                      }}
                    >
                      {isCreating ? "正在创建..." : `创建${formatExportKind(capability.kind)}任务`}
                    </button>
                    {previewDescriptor.available ? (
                      <button
                        className="route-link route-link-secondary"
                        type="button"
                        disabled={!pageState.boundary.export_allowed || isPreviewing}
                        onClick={() => {
                          void handlePreview(capability.kind);
                        }}
                      >
                        {isPreviewing ? "正在加载预览..." : previewDescriptor.buttonLabel}
                      </button>
                    ) : (
                      <span className="field-hint">
                        当前还没有可预览的在线内容，可先创建导出任务。
                      </span>
                    )}
                  </div>
                </article>
              );
            })}
          </section>

          {previewState.status === "loading" ? (
            <section className="status-card admin-review-panel export-preview-panel">
              <p className="eyebrow">预览加载中</p>
              <h2>{previewState.title}</h2>
              <p>正在准备当前预览内容，请稍候。</p>
            </section>
          ) : null}

          {previewState.status === "error" ? (
            <section className="page-stack">
              <ApiErrorNotice error={previewState.error} />
            </section>
          ) : null}

          {previewState.status === "ready" ? (
            <section className="status-card admin-review-panel export-preview-panel">
              <p className="eyebrow">预览</p>
              <h2>{previewState.title}</h2>
              <p>{previewState.note}</p>
              <pre className="export-preview-content">{previewState.content}</pre>
            </section>
          ) : null}

          <section className="status-card admin-review-panel">
            <div className="task-card-header">
              <div>
                <p className="task-card-id">导出任务</p>
                <h2>导出任务历史</h2>
              </div>
              <span className="status-chip">{pageState.jobs.length} 条记录</span>
            </div>

            {pageState.jobs.length === 0 ? (
              <p className="task-healthy-note">
                当前还没有导出任务记录。创建任务后，这里会显示状态、失败原因和可下载产物信息。
              </p>
            ) : (
              <div className="admin-review-record-list" aria-label="导出任务历史列表">
                {pageState.jobs.map((job) => (
                  <article key={job.id} className="admin-review-record-card">
                    <div className="task-card-header">
                      <div>
                        <p className="task-card-id">
                          {formatExportKind(job.kind)} / {formatExportFormat(job.format)}
                        </p>
                        <h3>{job.id}</h3>
                      </div>
                      <span className={`status-chip ${buildJobStatusTone(job.status)}`}>
                        {formatExportJobStatus(job.status)}
                      </span>
                    </div>

                    <dl className="task-detail-grid export-job-grid">
                      <div>
                        <dt>请求时任务状态</dt>
                        <dd>{job.task_status_at_request ? formatTaskStatus(job.task_status_at_request) : "未记录"}</dd>
                      </div>
                      <div>
                        <dt>数据版本</dt>
                        <dd>{job.is_latest_for_task ? "当前最新版本" : "任务数据已更新"}</dd>
                      </div>
                      <div>
                        <dt>创建时间</dt>
                        <dd>{formatDateTime(job.created_at)}</dd>
                      </div>
                      <div>
                        <dt>更新时间</dt>
                        <dd>{formatDateTime(job.updated_at)}</dd>
                      </div>
                    </dl>

                    {job.failure_reason ? (
                      <div className="status-note">
                        <p>失败原因：{job.failure_reason}</p>
                      </div>
                    ) : null}

                    {job.artifact ? (
                      <>
                        <div className="status-note">
                          <p>
                            导出产物：{job.artifact.filename} · {job.artifact.content_type ?? "未知类型"} ·{" "}
                            {formatFileSize(job.artifact.size_bytes)}
                          </p>
                        </div>
                        <div className="inline-actions export-action-row">
                          <button
                            className="route-link route-link-secondary"
                            type="button"
                            disabled={activeDownloadJobId === job.id}
                            onClick={() => {
                              void handleDownload(job.id);
                            }}
                          >
                            {activeDownloadJobId === job.id ? "正在下载..." : "下载导出文件"}
                          </button>
                        </div>
                      </>
                    ) : (
                      <p className="field-hint">当前任务尚无可下载产物；生成成功后这里会显示下载入口。</p>
                    )}
                  </article>
                ))}
              </div>
            )}
          </section>
        </>
      ) : null}
    </AdminWorkspaceShell>
  );
}
