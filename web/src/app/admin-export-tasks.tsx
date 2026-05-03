import { useEffect, useMemo, useState } from "react";
import { Link as RouterLink, useParams } from "react-router-dom";

import Button from "@mui/material/Button";

import { ApiErrorNotice } from "../components/ApiErrorNotice";
import { useConfirmDialog } from "../components/use-confirm-dialog";
import { PageHeader, StatusBadge, SurfaceCard } from "../components/dashboard";
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
  reimbursement_package: "完整报销材料包",
};

const EXPORT_KIND_DESCRIPTIONS: Record<ExportArtifactKind, string> = {
  reimbursement_summary: "按费用类型和成员汇总当前任务金额，适合管理员最终核对。",
  member_details: "按成员展开当前有效分摊明细，不混入已失效历史版本。",
  invoice_details: "列出发票号码、金额、费用类型及异常校验摘要。",
  missing_materials: "按成员和费用列出仍缺失的支付记录、比赛通知或行程材料。",
  finance_draft: "输出项目、报销人、发票及分摊摘要，供人工录入财务系统。",
  merged_pdf: "校验材料并按系统默认顺序合并 PDF/图片，生成可下载的打印材料包。",
  reimbursement_package:
    "生成一个 ZIP 完整材料包，内含合并 PDF、汇总/明细、缺失清单、财务草稿和 manifest。",
};

const EXPORT_FORMAT_LABELS: Record<ExportArtifactFormat, string> = {
  xlsx: "XLSX",
  csv: "CSV",
  json: "页面预览",
  pdf: "PDF",
  zip: "ZIP",
};

const PREFERRED_JOB_FORMATS: Record<ExportArtifactKind, ExportArtifactFormat> = {
  reimbursement_summary: "xlsx",
  member_details: "xlsx",
  invoice_details: "xlsx",
  missing_materials: "xlsx",
  finance_draft: "xlsx",
  merged_pdf: "pdf",
  reimbursement_package: "zip",
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
    return "success" as const;
  }
  if (status === "failed") {
    return "danger" as const;
  }
  return "warning" as const;
}

function buildPreviewDescriptor(capability: TaskExportCapability) {
  if (capability.kind === "merged_pdf") {
    return {
      available: true,
      buttonLabel: "查看合并顺序",
      placeholderLabel: "合并顺序",
    };
  }

  if (capability.kind === "finance_draft") {
    return {
      available: true,
      buttonLabel: "查看填报草稿",
      placeholderLabel: "页面草稿",
    };
  }

  if (capability.kind === "reimbursement_package") {
    return {
      available: false,
      buttonLabel: "暂不支持页面查看",
      placeholderLabel: "生成后下载",
    };
  }

  return {
    available: capability.implemented_formats.includes("csv"),
    buttonLabel: "直接查看内容",
    placeholderLabel: capability.implemented_formats.includes("csv") ? "页面预览" : "需生成后下载",
  };
}

function buildPreviewNote(kind: ExportArtifactKind) {
  if (kind === "merged_pdf") {
    return "该预览用于核对打印材料的合并顺序和可读性；正式 PDF 请下载导出文件。";
  }
  if (kind === "finance_draft") {
    return "该预览用于快速核对填报草稿；正式文件请在导出成功后下载。";
  }
  return "该预览用于快速核对导出内容；正式文件请在导出成功后下载。";
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

function describeExportArtifact(contentType: string | null | undefined) {
  if (contentType === "application/zip") {
    return "ZIP 材料包";
  }
  if (contentType === "application/pdf") {
    return "PDF 材料包";
  }
  if (contentType === "text/csv") {
    return "CSV 文件";
  }
  return contentType ?? "导出产物";
}

function buildPackageJobSummary(job: TaskExportJobRecord | null) {
  if (!job) {
    return {
      badge: "尚未生成完整材料包",
      tone: "warning" as const,
      note: "当前还没有完整材料包记录。主流程应先生成一个 ZIP 材料包，再决定是否需要单项导出排障。",
    };
  }

  if (job.status === "failed") {
    return {
      badge: "最近一次完整材料包生成失败",
      tone: "danger" as const,
      note: "最近一次完整材料包生成失败。处理失败原因后，需要重新生成一个新的完整材料包。",
    };
  }

  if (job.status === "pending" || job.status === "running") {
    return {
      badge: "完整材料包生成中",
      tone: "warning" as const,
      note: "后台正在生成最新完整材料包。生成完成后，会提供下载入口并标记是否仍是最新任务数据版本。",
    };
  }

  if (job.is_latest_for_task) {
    return {
      badge: "已生成最新完整材料包",
      tone: "success" as const,
      note: "最近一次完整材料包已经生成，并且对应当前最新任务数据版本。",
    };
  }

  return {
    badge: "最近一次完整材料包不是最新版本",
    tone: "warning" as const,
    note: "最近一次完整材料包虽然可下载，但任务数据已经变化。继续下载只适合排障或临时比对，主流程应重新生成。",
  };
}

function buildBoundaryStatusItems(boundary: TaskExportBoundary, latestPackageJob: TaskExportJobRecord | null) {
  return [
    {
      label: "材料包就绪度",
      value: boundary.export_allowed ? "已满足" : "未满足",
      tone: boundary.export_allowed ? "success" as const : "danger" as const,
    },
    {
      label: "最近完整包状态",
      value: latestPackageJob ? formatExportJobStatus(latestPackageJob.status) : "尚未生成",
      tone: latestPackageJob
        ? buildJobStatusTone(latestPackageJob.status)
        : "warning" as const,
    },
    {
      label: "数据版本",
      value: latestPackageJob
        ? latestPackageJob.is_latest_for_task
          ? "当前最新版本"
          : "任务数据已更新"
        : "暂无完整包",
      tone: latestPackageJob?.is_latest_for_task ? "success" as const : "warning" as const,
    },
    {
      label: "生成方式",
      value: boundary.execution_mode === "worker" ? "后台生成" : "立即生成",
      tone: "info" as const,
    },
  ];
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
  const { confirm } = useConfirmDialog();
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

  const latestPackageJob =
    pageState.status === "ready"
      ? latestJobsByKind.get("reimbursement_package") ?? null
      : null;
  const packageJobSummary = buildPackageJobSummary(latestPackageJob);
  const boundaryStatusItems = pageState.status === "ready"
    ? buildBoundaryStatusItems(pageState.boundary, latestPackageJob)
    : [];

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
            title="导出与下载"
            description="生成汇总、明细、草稿和打印材料包。"
          />
        )}
      >
        <SurfaceCard component="section" className="status-card">
          <p className="eyebrow">导出任务</p>
          <h2>任务标识缺失</h2>
          <p>暂时无法读取该任务，请从任务列表重新进入。</p>
        </SurfaceCard>
      </AdminWorkspaceShell>
    );
  }

  async function handleCreateJob(kind: ExportArtifactKind) {
    if (!session || pageState.status !== "ready" || !taskId) {
      return;
    }

    const confirmed = await confirm({
      title: `确认创建${formatExportKind(kind)}任务？`,
      description: `任务 ${pageState.task.competition_name} 当前处于${formatTaskStatus(pageState.task.status)}。确认后，系统会按当前数据版本创建一个 ${formatExportFormat(PREFERRED_JOB_FORMATS[kind])} 导出任务并放入后台队列。`,
      confirmLabel: "创建导出任务",
      cancelLabel: "暂不创建",
      tone: kind === "merged_pdf" ? "warning" : "info",
    });
    if (!confirmed) {
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
        `${formatExportKind(kind)}已加入导出队列，当前状态：${formatExportJobStatus(created.status)}。`,
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
      title: `${formatExportKind(kind)} 页面查看`,
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
        case "reimbursement_package":
          content = "";
          break;
        default:
          content = "";
      }

      setPreviewState({
        status: "ready",
        title: `${formatExportKind(kind)} 页面查看`,
        note: buildPreviewNote(kind),
        content,
      });
    } catch (error) {
      setPreviewState({
        status: "error",
        title: `${formatExportKind(kind)} 页面查看`,
        error,
      });
    } finally {
      setActivePreviewKind(null);
    }
  }

  async function handleDownload(job: TaskExportJobRecord) {
    if (!session) {
      return;
    }

    setActionError(null);
    setActionFeedback(null);
    setActiveDownloadJobId(job.id);

    try {
      const downloaded = await trmsApi.downloadTaskExportArtifact(job.id, session.actorId);
      triggerBrowserDownload(downloaded.blob, downloaded.filename ?? `${job.kind}.bin`);
      setActionFeedback(`${formatExportKind(job.kind)}已开始下载。`);
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
          title="导出与下载"
          description="主流程优先生成完整材料包；单项导出仅在核对局部内容或排查问题时使用。"
          actions={(
            <div className="page-actions">
              <Button component={RouterLink} variant="outlined" to={`/admin/tasks/${taskId}/review`}>
                返回复核总览
              </Button>
              <Button component={RouterLink} variant="outlined" to={`/admin/tasks/${taskId}/corrections`}>
                返回更正与提醒
              </Button>
            </div>
          )}
        />
      )}
    >

      {pageState.status === "loading" ? (
        <SurfaceCard component="section" className="status-card admin-review-panel">
          <p className="eyebrow">导出任务</p>
          <h2>正在加载导出准备情况</h2>
          <p>正在读取任务信息、导出能力和既有导出记录，请稍候。</p>
        </SurfaceCard>
      ) : null}

      {pageState.status === "error" ? <ApiErrorNotice error={pageState.error} /> : null}
      {actionError ? <ApiErrorNotice error={actionError} /> : null}

      {pageState.status === "ready" ? (
        <>
          <SurfaceCard component="section" className="status-card admin-review-panel">
            <div className="task-card-header">
              <div>
                <p className="task-card-id">导出打印</p>
                <h2>{pageState.task.competition_name}</h2>
              </div>
              <StatusBadge tone={packageJobSummary.tone}>{packageJobSummary.badge}</StatusBadge>
            </div>

            <div className="export-primary-shell">
              <div className="export-primary-main">
                <p className="eyebrow">主操作</p>
                <h3>先生成完整材料包</h3>
                <p className="status-note">{packageJobSummary.note}</p>
                <p className="status-note">{pageState.boundary.note}</p>
                <div className="inline-actions export-action-row">
                  <Button
                    type="button"
                    variant="contained"
                    disabled={!pageState.boundary.export_allowed || activeCreateKind === "reimbursement_package"}
                    onClick={() => {
                      void handleCreateJob("reimbursement_package");
                    }}
                  >
                    {activeCreateKind === "reimbursement_package" ? "正在生成..." : "生成完整材料包"}
                  </Button>
                  {latestPackageJob?.artifact ? (
                    <Button
                      type="button"
                      variant="outlined"
                      disabled={activeDownloadJobId === latestPackageJob.id}
                      onClick={() => {
                        void handleDownload(latestPackageJob);
                      }}
                    >
                      {activeDownloadJobId === latestPackageJob.id ? "正在下载..." : "下载最近完整材料包"}
                    </Button>
                  ) : (
                    <span className="field-hint">
                      生成成功后，这里会出现完整材料包下载入口。
                    </span>
                  )}
                </div>
              </div>
              <div className="export-primary-status-grid" aria-label="材料包状态摘要">
                {boundaryStatusItems.map((item) => (
                  <section key={item.label} className="export-primary-status-card">
                    <span>{item.label}</span>
                    <strong>{item.value}</strong>
                    <StatusBadge tone={item.tone}>{item.value}</StatusBadge>
                  </section>
                ))}
              </div>
            </div>

            {latestPackageJob ? (
              <section className="admin-review-subsection">
                <div className="task-card-header">
                  <div>
                    <p className="task-card-id">最近完整材料包</p>
                    <h4>{formatDateTime(latestPackageJob.created_at)}</h4>
                  </div>
                  <StatusBadge tone={buildJobStatusTone(latestPackageJob.status)}>
                    {formatExportJobStatus(latestPackageJob.status)}
                  </StatusBadge>
                </div>

                <dl className="task-detail-grid export-job-grid">
                  <div>
                    <dt>创建时间</dt>
                    <dd>{formatDateTime(latestPackageJob.created_at)}</dd>
                  </div>
                  <div>
                    <dt>更新时间</dt>
                    <dd>{formatDateTime(latestPackageJob.updated_at)}</dd>
                  </div>
                </dl>

                {latestPackageJob.failure_reason ? (
                  <div className="status-note">
                    <p>失败原因：{latestPackageJob.failure_reason}</p>
                  </div>
                ) : null}

                {latestPackageJob.artifact ? (
                  <div className="status-note">
                    <p>
                      下载产物：{describeExportArtifact(latestPackageJob.artifact.content_type)} ·{" "}
                      {latestPackageJob.artifact.content_type ?? "未知类型"} ·{" "}
                      {formatFileSize(latestPackageJob.artifact.size_bytes)}
                    </p>
                  </div>
                ) : (
                  <p className="field-hint">当前完整材料包尚未生成可下载产物。</p>
                )}
              </section>
            ) : null}
            {!pageState.boundary.export_allowed ? (
              <section className="admin-review-subsection">
                <div className="task-card-header">
                  <div>
                    <p className="task-card-id">导出门禁</p>
                    <h4>当前任务尚未满足导出前置条件</h4>
                  </div>
                  <StatusBadge tone="danger">已阻止导出</StatusBadge>
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
          </SurfaceCard>

          <SurfaceCard
            component="section"
            id="advanced-export-options"
            className="status-card admin-review-panel"
            aria-label="高级单项导出"
          >
            <div className="task-card-header">
              <div>
                <p className="task-card-id">高级操作</p>
                <h2>高级单项导出</h2>
              </div>
              <StatusBadge tone="info">仅用于排障或临时下载</StatusBadge>
            </div>
            <p className="status-note">
              默认主流程请优先生成完整材料包。下面的单项导出保留给排查问题、核对局部内容或临时下载使用。
            </p>

            <div className="admin-review-record-list export-capability-grid">
              {pageState.boundary.supported_exports
                .filter((capability) => capability.kind !== "reimbursement_package")
                .map((capability) => {
              const latestJob = latestJobsByKind.get(capability.kind) ?? null;
              const previewDescriptor = buildPreviewDescriptor(capability);
              const preferredFormat = PREFERRED_JOB_FORMATS[capability.kind];
              const isCreating = activeCreateKind === capability.kind;
              const isPreviewing = activePreviewKind === capability.kind;

              return (
                <SurfaceCard key={capability.kind} component="article" className="admin-review-record-card export-capability-card">
                  <div className="task-card-header">
                    <div>
                      <p className="task-card-id">
                        首选任务格式 {formatExportFormat(preferredFormat)}
                      </p>
                      <h3>{formatExportKind(capability.kind)}</h3>
                    </div>
                    <StatusBadge tone={capability.implemented ? "success" : "warning"}>
                      {capability.implemented ? "可直接查看" : "需先生成"}
                    </StatusBadge>
                  </div>

                  <p>{EXPORT_KIND_DESCRIPTIONS[capability.kind]}</p>

                  <div className="admin-review-inline-metadata">
                    <StatusBadge tone="info">
                      允许格式：{capability.formats.map(formatExportFormat).join(" / ")}
                    </StatusBadge>
                    <StatusBadge tone="info">
                      页面查看：{previewDescriptor.placeholderLabel}
                    </StatusBadge>
                    {latestJob ? (
                      <StatusBadge tone={buildJobStatusTone(latestJob.status)}>
                        最近任务：{formatExportJobStatus(latestJob.status)}
                      </StatusBadge>
                    ) : null}
                  </div>

                  <div className="inline-actions export-action-row">
                    <Button
                      type="button"
                      variant="contained"
                      disabled={!pageState.boundary.export_allowed || isCreating}
                      onClick={() => {
                        void handleCreateJob(capability.kind);
                      }}
                    >
                      {isCreating ? "正在创建..." : `创建${formatExportKind(capability.kind)}任务`}
                    </Button>
                    {previewDescriptor.available ? (
                      <Button
                        type="button"
                        variant="outlined"
                        disabled={!pageState.boundary.export_allowed || isPreviewing}
                        onClick={() => {
                          void handlePreview(capability.kind);
                        }}
                      >
                        {isPreviewing ? "正在加载预览..." : previewDescriptor.buttonLabel}
                      </Button>
                    ) : (
                      <span className="field-hint">
                        该导出项暂时不能直接在页面查看，可先创建导出任务。
                      </span>
                    )}
                  </div>
                </SurfaceCard>
              );
                })}
            </div>
          </SurfaceCard>

          {previewState.status === "loading" ? (
            <SurfaceCard component="section" className="status-card admin-review-panel export-preview-panel">
              <p className="eyebrow">预览加载中</p>
              <h2>{previewState.title}</h2>
              <p>正在准备当前预览内容，请稍候。</p>
            </SurfaceCard>
          ) : null}

          {previewState.status === "error" ? (
            <section className="page-stack">
              <ApiErrorNotice error={previewState.error} />
            </section>
          ) : null}

          {previewState.status === "ready" ? (
            <SurfaceCard component="section" className="status-card admin-review-panel export-preview-panel">
              <p className="eyebrow">预览</p>
              <h2>{previewState.title}</h2>
              <p>{previewState.note}</p>
              <pre className="export-preview-content">{previewState.content}</pre>
            </SurfaceCard>
          ) : null}

          <SurfaceCard component="section" className="status-card admin-review-panel">
            <div className="task-card-header">
              <div>
                <p className="task-card-id">导出任务</p>
                <h2>导出任务历史</h2>
              </div>
              <StatusBadge tone="info">{pageState.jobs.length} 条记录</StatusBadge>
            </div>

            {pageState.jobs.length === 0 ? (
              <p className="task-healthy-note">
                当前还没有导出任务记录。创建任务后，会在这里显示状态、失败原因和可下载产物信息。
              </p>
            ) : (
              <div className="admin-review-record-list" aria-label="导出任务历史列表">
                {pageState.jobs.map((job) => (
                  <SurfaceCard key={job.id} component="article" className="admin-review-record-card">
                    <div className="task-card-header">
                      <div>
                        <p className="task-card-id">
                          {formatExportKind(job.kind)} / {formatExportFormat(job.format)}
                        </p>
                        <h3>{formatDateTime(job.created_at)}</h3>
                      </div>
                      <StatusBadge tone={buildJobStatusTone(job.status)}>
                        {formatExportJobStatus(job.status)}
                      </StatusBadge>
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
                            导出产物：{describeExportArtifact(job.artifact.content_type)} · {job.artifact.content_type ?? "未知类型"} ·{" "}
                            {formatFileSize(job.artifact.size_bytes)}
                          </p>
                        </div>
                        <div className="inline-actions export-action-row">
                          <Button
                            type="button"
                            variant="outlined"
                            disabled={activeDownloadJobId === job.id}
                            onClick={() => {
                              void handleDownload(job);
                            }}
                          >
                            {activeDownloadJobId === job.id ? "正在下载..." : "下载导出文件"}
                          </Button>
                        </div>
                      </>
                    ) : (
                      <p className="field-hint">当前任务尚无可下载产物；生成成功后会在这里显示下载入口。</p>
                    )}
                  </SurfaceCard>
                ))}
              </div>
            )}
          </SurfaceCard>
        </>
      ) : null}
    </AdminWorkspaceShell>
  );
}
