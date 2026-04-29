import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { ApiError } from "../lib/api/client";
import { ApiErrorNotice } from "../components/ApiErrorNotice";
import { FileDropZone } from "../components/FileDropZone";
import { useSnackbar } from "../components/use-snackbar";
import { trmsApi } from "../lib/api/trms";
import type {
  MaterialBatchUploadResponse,
  MaterialRecord,
  MaterialType,
  ReimbursementTask,
  SubmissionChannel,
  TaskStatus,
} from "../lib/api/types";
import { useAuthSession } from "./auth-store";

type MemberMaterialUploadPageState =
  | { status: "loading" }
  | { status: "error"; error: unknown }
  | { status: "ready"; visibleTasks: ReimbursementTask[]; uploadableTasks: ReimbursementTask[] };

type UploadFormState = {
  taskId: string;
  materialType: MaterialType;
  files: File[];
};

type UploadValidationErrors = Partial<Record<keyof UploadFormState, string>>;

const WEB_CHANNEL: SubmissionChannel = "web";
const DEFAULT_MATERIAL_TYPE: MaterialType = "invoice";
const MATERIAL_FILE_ACCEPT = ".pdf,.zip,.jpg,.jpeg,.png,.webp";

const MATERIAL_TYPE_OPTIONS: Array<{ value: MaterialType; label: string }> = [
  { value: "invoice", label: "发票" },
  { value: "payment_record", label: "支付记录" },
  { value: "competition_notice", label: "比赛通知" },
  { value: "itinerary", label: "行程单" },
  { value: "order_screenshot", label: "订单截图" },
  { value: "other_attachment", label: "其他附件" },
];

const TASK_STATUS_LABELS: Record<TaskStatus, string> = {
  draft: "草稿",
  open: "开放提交",
  closed: "已关闭",
  reviewing: "复核中",
  ready_to_export: "可导出",
  completed: "已归档",
};

function buildInitialFormState(): UploadFormState {
  return {
    taskId: "",
    materialType: DEFAULT_MATERIAL_TYPE,
    files: [],
  };
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

function pickSelectedTaskId(tasks: ReimbursementTask[], preferredTaskId: string | null, currentTaskId: string) {
  const visibleTaskIds = new Set(tasks.map((task) => task.id));
  if (currentTaskId.length > 0 && visibleTaskIds.has(currentTaskId)) {
    return currentTaskId;
  }
  if (preferredTaskId && visibleTaskIds.has(preferredTaskId)) {
    return preferredTaskId;
  }
  return tasks[0]?.id ?? "";
}

function formatTaskStatus(status: TaskStatus) {
  return TASK_STATUS_LABELS[status];
}

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function formatMaterialType(materialType: MaterialType) {
  const matched = MATERIAL_TYPE_OPTIONS.find((option) => option.value === materialType);
  return matched?.label ?? materialType;
}

function validateUploadForm(
  formState: UploadFormState,
  uploadableTasks: ReimbursementTask[],
): UploadValidationErrors {
  const errors: UploadValidationErrors = {};

  if (!uploadableTasks.some((task) => task.id === formState.taskId)) {
    errors.taskId = "请选择一个当前仍开放提交的报销任务。";
  }
  if (!MATERIAL_TYPE_OPTIONS.some((option) => option.value === formState.materialType)) {
    errors.materialType = "请选择受支持的材料类型。";
  }
  if (formState.files.length === 0) {
    errors.files = "至少选择一个要上传的文件。";
  }

  return errors;
}

export function MemberMaterialUploadPage() {
  const session = useAuthSession();
  const { showError, showSuccess, showWarning } = useSnackbar();
  const [searchParams] = useSearchParams();
  const preferredTaskId = searchParams.get("taskId");
  const [pageState, setPageState] = useState<MemberMaterialUploadPageState>({ status: "loading" });
  const [formState, setFormState] = useState<UploadFormState>(() => buildInitialFormState());
  const [validationErrors, setValidationErrors] = useState<UploadValidationErrors>({});
  const [uploadResult, setUploadResult] = useState<MaterialBatchUploadResponse | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function loadVisibleTasks() {
      if (!session || session.role !== "member") {
        return;
      }

      setPageState({ status: "loading" });

      try {
        const allTasks = await trmsApi.listTasks();
        const visibleTasks = allTasks.filter((task) => task.member_ids.includes(session.actorId));
        const uploadableTasks = visibleTasks.filter((task) => task.status === "open");

        if (cancelled) {
          return;
        }

        setPageState({
          status: "ready",
          visibleTasks,
          uploadableTasks,
        });
        setFormState((current) => ({
          ...current,
          taskId: pickSelectedTaskId(uploadableTasks, preferredTaskId, current.taskId),
        }));
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

    void loadVisibleTasks();

    return () => {
      cancelled = true;
    };
  }, [preferredTaskId, session]);

  if (!session || session.role !== "member") {
    return null;
  }

  const memberSession = session;

  function updateField<Key extends keyof UploadFormState>(key: Key, value: UploadFormState[Key]) {
    setFormState((current) => ({
      ...current,
      [key]: value,
    }));
    setValidationErrors((current) => {
      if (!(key in current)) {
        return current;
      }
      const next = { ...current };
      delete next[key];
      return next;
    });
  }

  function resetSelectedFiles() {
    setFormState((current) => ({
      ...current,
      files: [],
    }));
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (pageState.status !== "ready") {
      return;
    }

    setUploadResult(null);

    const errors = validateUploadForm(formState, pageState.uploadableTasks);
    setValidationErrors(errors);
    if (Object.keys(errors).length > 0) {
      return;
    }

    const requestBody = new FormData();
    requestBody.set("submitter_id", memberSession.actorId);
    requestBody.set("channel", WEB_CHANNEL);
    requestBody.set("material_type", formState.materialType);
    formState.files.forEach((file) => {
      requestBody.append("files", file);
    });

    setIsSubmitting(true);
    try {
      const response = await trmsApi.submitTaskMaterials(formState.taskId, requestBody);
      setUploadResult(response);
      resetSelectedFiles();
      if (response.status === "success") {
        showSuccess(`上传成功：${response.items.length} 个文件已归档到当前任务。`);
      } else {
        const failureCount = response.failures?.length ?? 0;
        showWarning(`上传完成：${response.items.length} 个成功，${failureCount} 个失败。`);
      }
    } catch (error) {
      const failedBatch = extractFailedBatchUploadResponse(error);
      if (failedBatch) {
        setUploadResult(failedBatch);
        resetSelectedFiles();
        const failureCount = failedBatch.failures?.length ?? 0;
        showError(`上传失败：${failureCount} 个文件未通过，请查看逐文件原因。`);
      } else {
        const message = error instanceof ApiError ? error.summary.message : "材料上传失败，请稍后重试。";
        showError(message);
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  const visibleTaskCount = pageState.status === "ready" ? pageState.visibleTasks.length : 0;
  const uploadableTasks = pageState.status === "ready" ? pageState.uploadableTasks : [];
  const selectedTask =
    pageState.status === "ready"
      ? pageState.uploadableTasks.find((task) => task.id === formState.taskId) ?? null
      : null;

  return (
    <div className="page-stack">
      <section className="status-card auth-panel">
        <p className="eyebrow">材料提交</p>
        <h2>成员材料上传</h2>
        <p>
          当前页是单任务发票工作台下的专项上传入口，用于补充发票或附件材料。
        </p>
        <div className="inline-actions">
          <Link
            className="route-link"
            to={selectedTask ? `/member/invoices/workbench?taskId=${encodeURIComponent(selectedTask.id)}` : "/member/invoices/workbench"}
          >
            返回当前任务工作台
          </Link>
          <Link className="route-link route-link-secondary" to="/member">
            返回成员任务列表
          </Link>
          {selectedTask ? (
            <Link
              className="route-link route-link-secondary"
              to={`/member/materials/status?taskId=${encodeURIComponent(selectedTask.id)}`}
            >
              查看当前任务材料状态
            </Link>
          ) : null}
          <span className="status-chip">当前可见任务 {visibleTaskCount} 个</span>
        </div>
      </section>

      {pageState.status === "loading" ? (
        <section className="status-card">
          <p className="eyebrow">材料提交</p>
          <h2>正在加载可上传任务</h2>
          <p>正在读取当前成员可访问的任务，并筛选仍开放提交的上传目标。</p>
        </section>
      ) : null}

      {pageState.status === "error" ? <ApiErrorNotice error={pageState.error} /> : null}

      {pageState.status === "ready" && uploadableTasks.length === 0 ? (
        <section className="status-card">
          <p className="eyebrow">暂无开放任务</p>
          <h2>当前没有可上传的开放任务</h2>
          <p>
            你当前可见的任务共有 {pageState.visibleTasks.length} 个，但目前都不在收集阶段。
          </p>
          <p className="status-note">
            如需补交，请先由管理员重新开放任务或新建新的报销收集任务。
          </p>
        </section>
      ) : null}

      {pageState.status === "ready" && uploadableTasks.length > 0 ? (
        <form
          className="page-stack"
          onSubmit={(event) => {
            void handleSubmit(event);
          }}
          noValidate
        >
          <section className="status-card auth-panel">
            <div className="admin-form-header">
              <div>
                <p className="eyebrow">上传表单</p>
                <h2>选择任务并上传文件</h2>
              </div>
              <span className="status-chip">开放任务 {uploadableTasks.length} 个</span>
            </div>
            <div className="admin-form-grid">
              <label className="field-stack">
                <span>目标任务</span>
                <select
                  aria-label="目标任务"
                  name="task-id"
                  value={formState.taskId}
                  onChange={(event) => {
                    updateField("taskId", event.target.value);
                  }}
                >
                  {uploadableTasks.map((task) => (
                    <option key={task.id} value={task.id}>
                      {task.competition_name}（{task.id}）
                    </option>
                  ))}
                </select>
                {validationErrors.taskId ? (
                  <span className="field-error">{validationErrors.taskId}</span>
                ) : (
                  <span className="field-hint">只列出当前成员可见且仍开放提交的任务。</span>
                )}
              </label>

              <label className="field-stack">
                <span>提交方式</span>
                <select name="channel" value={WEB_CHANNEL} disabled>
                  <option value={WEB_CHANNEL}>网页提交</option>
                </select>
                <span className="field-hint">当前页面默认按网页提交记录。</span>
              </label>

              <label className="field-stack">
                <span>材料类型</span>
                <select
                  aria-label="材料类型"
                  name="material-type"
                  value={formState.materialType}
                  onChange={(event) => {
                    updateField("materialType", event.target.value as MaterialType);
                  }}
                >
                  {MATERIAL_TYPE_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
                {validationErrors.materialType ? (
                  <span className="field-error">{validationErrors.materialType}</span>
                ) : (
                  <span className="field-hint">请选择最接近的材料类型，便于后续整理和复核。</span>
                )}
              </label>

              <div className="field-stack">
                <span>上传文件</span>
                <FileDropZone
                  files={formState.files}
                  onChange={(files) => {
                    updateField("files", files);
                  }}
                  accept={MATERIAL_FILE_ACCEPT}
                  disabled={isSubmitting}
                  ariaLabel="上传文件"
                  fileListAriaLabel="待上传文件列表"
                  hint="支持 PDF、ZIP、JPG、PNG、WEBP；单文件最大 10MB。批量上传时会分别提示每个文件的结果。"
                />
                {validationErrors.files ? (
                  <span className="field-error">{validationErrors.files}</span>
                ) : null}
              </div>
            </div>

            {selectedTask ? (
              <dl className="task-meta-grid member-upload-meta-grid" aria-label="当前选中任务摘要">
                <div>
                  <dt>比赛名称</dt>
                  <dd>{selectedTask.competition_name}</dd>
                </div>
                <div>
                  <dt>任务编号</dt>
                  <dd>{selectedTask.id}</dd>
                </div>
                <div>
                  <dt>任务状态</dt>
                  <dd>{formatTaskStatus(selectedTask.status)}</dd>
                </div>
                <div>
                  <dt>截止时间</dt>
                  <dd>{formatDateTime(selectedTask.deadline)}</dd>
                </div>
              </dl>
            ) : null}
            <div className="admin-form-footer">
              <p className="field-hint">
                上传结果会显式展示材料编号、重复状态和逐文件失败原因，不把部分失败伪装成全部成功。
              </p>
              <button className="route-link" type="submit" disabled={isSubmitting}>
                {isSubmitting ? "正在上传..." : "上传材料"}
              </button>
            </div>
          </section>
        </form>
      ) : null}

      {uploadResult ? (
        <section className="status-card auth-panel">
          <div className="admin-form-header">
            <div>
              <p className="eyebrow">上传结果</p>
              <h2>上传结果</h2>
            </div>
            <span className={`status-chip upload-status-chip upload-status-${uploadResult.status}`}>
              {uploadResult.status === "success"
                ? "全部成功"
                : uploadResult.status === "partial_success"
                  ? "部分成功"
                  : "全部失败"}
            </span>
          </div>

          {uploadResult.items.length > 0 ? (
            <div className="task-card-grid" aria-label="上传成功材料列表">
              {uploadResult.items.map((item) => (
                <article key={item.id} className="task-card">
                  <div className="task-card-header">
                    <div>
                      <p className="task-card-id">材料编号 {item.id}</p>
                      <h3>{item.original_filename}</h3>
                    </div>
                    <span className="status-chip">{formatMaterialType(item.material_type)}</span>
                  </div>
                  <dl className="task-meta-grid">
                    <div>
                      <dt>提交渠道</dt>
                      <dd>{item.channel}</dd>
                    </div>
                    <div>
                      <dt>重复状态</dt>
                      <dd>
                        {item.duplicate_of
                          ? `与材料 ${item.duplicate_of} 重复`
                          : "未检测到重复"}
                      </dd>
                    </div>
                    <div>
                      <dt>提交人</dt>
                      <dd>{item.submitter_id ?? "未分配"}</dd>
                    </div>
                    <div>
                      <dt>文件大小</dt>
                      <dd>{item.size_bytes} bytes</dd>
                    </div>
                  </dl>
                </article>
              ))}
            </div>
          ) : (
            <p>本次上传没有成功写入任何材料记录。</p>
          )}

          {uploadResult.failures && uploadResult.failures.length > 0 ? (
            <ul className="upload-failure-list" aria-label="上传失败列表">
              {uploadResult.failures.map((failure) => (
                <li key={`${failure.original_filename ?? "unknown"}:${failure.error_code}:${failure.detail}`}>
                  <strong>{failure.original_filename || "未命名文件"}</strong>
                  <span>{failure.detail}</span>
                </li>
              ))}
            </ul>
          ) : null}
        </section>
      ) : null}
    </div>
  );
}
