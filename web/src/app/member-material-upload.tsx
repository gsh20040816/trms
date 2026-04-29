import { useEffect, useState } from "react";
import { Link as RouterLink, useSearchParams } from "react-router-dom";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import LinearProgress from "@mui/material/LinearProgress";
import MenuItem from "@mui/material/MenuItem";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";

import { ApiError } from "../lib/api/client";
import { ApiErrorNotice } from "../components/ApiErrorNotice";
import {
  EmptyState,
  PageHeader,
  RoleWorkspace,
  SectionCard,
  StatusBadge,
} from "../components/dashboard";
import { FileDropZone } from "../components/FileDropZone";
import { useSnackbar } from "../components/use-snackbar";
import { trmsApi } from "../lib/api/trms";
import { findOversizedFile, MAX_UPLOAD_FILE_BYTES } from "../lib/upload-validation";
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

function buildUploadResultTone(status: MaterialBatchUploadResponse["status"]) {
  if (status === "failed") {
    return "warning" as const;
  }
  return "success" as const;
}

function formatUploadResultStatus(status: MaterialBatchUploadResponse["status"]) {
  if (status === "success") {
    return "全部成功";
  }
  if (status === "partial_success") {
    return "部分成功";
  }
  return "全部失败";
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
  } else {
    const oversizedFile = findOversizedFile(formState.files);
    if (oversizedFile) {
      errors.files = `文件 ${oversizedFile.name} 超过 ${Math.floor(MAX_UPLOAD_FILE_BYTES / 1024 / 1024)}MB，请压缩或拆分后再上传。`;
    }
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
    <RoleWorkspace
      header={(
        <PageHeader
          eyebrow="材料提交"
          title="成员材料上传"
          description="当前页是单任务发票工作台下的专项上传入口，用于补充发票或附件材料。"
          actions={(
            <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5} alignItems={{ xs: "stretch", sm: "center" }}>
              <StatusBadge tone="info">当前可见任务 {visibleTaskCount} 个</StatusBadge>
              <Button
                component={RouterLink}
                to={selectedTask ? `/member/invoices/workbench?taskId=${encodeURIComponent(selectedTask.id)}` : "/member/invoices/workbench"}
                variant="contained"
              >
                返回当前任务工作台
              </Button>
              <Button component={RouterLink} to="/member" variant="outlined">
                返回成员任务列表
              </Button>
              {selectedTask ? (
                <Button
                  component={RouterLink}
                  to={`/member/materials/status?taskId=${encodeURIComponent(selectedTask.id)}`}
                  variant="outlined"
                >
                  查看当前任务材料状态
                </Button>
              ) : null}
            </Stack>
          )}
        />
      )}
    >
      {pageState.status === "loading" ? (
        <SectionCard title="正在加载可上传任务" description="正在读取当前成员可访问的任务，并筛选仍开放提交的上传目标。" />
      ) : null}

      {pageState.status === "error" ? <ApiErrorNotice error={pageState.error} /> : null}

      {pageState.status === "ready" && uploadableTasks.length === 0 ? (
        <EmptyState
          title="当前没有可上传的开放任务"
          description={`你当前可见的任务共有 ${pageState.visibleTasks.length} 个，但目前都不在收集阶段。如需补交，请先由管理员重新开放任务或新建新的报销收集任务。`}
        />
      ) : null}

      {pageState.status === "ready" && uploadableTasks.length > 0 ? (
        <Box
          component="form"
          onSubmit={(event) => {
            void handleSubmit(event);
          }}
          noValidate
        >
          <SectionCard
            title="选择任务并上传文件"
            description="上传结果会显式展示材料编号、重复状态和逐文件失败原因，不把部分失败伪装成全部成功。"
            action={<StatusBadge tone="info">开放任务 {uploadableTasks.length} 个</StatusBadge>}
          >
            <Stack spacing={2.5}>
              <Box
                sx={{
                  display: "grid",
                  gridTemplateColumns: { xs: "1fr", md: "repeat(3, minmax(0, 1fr))" },
                  gap: 2,
                }}
              >
                <TextField
                  select
                  label="目标任务"
                  aria-label="目标任务"
                  name="task-id"
                  value={formState.taskId}
                  onChange={(event) => {
                    updateField("taskId", event.target.value);
                  }}
                  error={Boolean(validationErrors.taskId)}
                  helperText={validationErrors.taskId ?? "只列出当前成员可见且仍开放提交的任务。"}
                  fullWidth
                >
                  {uploadableTasks.map((task) => (
                    <MenuItem key={task.id} value={task.id}>
                      {task.competition_name}（{task.id}）
                    </MenuItem>
                  ))}
                </TextField>

                <TextField
                  label="提交方式"
                  name="channel"
                  value="网页提交"
                  disabled
                  helperText="当前页面默认按网页提交记录。"
                  fullWidth
                />

                <TextField
                  select
                  label="材料类型"
                  aria-label="材料类型"
                  name="material-type"
                  value={formState.materialType}
                  onChange={(event) => {
                    updateField("materialType", event.target.value as MaterialType);
                  }}
                  error={Boolean(validationErrors.materialType)}
                  helperText={validationErrors.materialType ?? "请选择最接近的材料类型，便于后续整理和复核。"}
                  fullWidth
                >
                  {MATERIAL_TYPE_OPTIONS.map((option) => (
                    <MenuItem key={option.value} value={option.value}>
                      {option.label}
                    </MenuItem>
                  ))}
                </TextField>
              </Box>

              <Box>
                <Typography variant="subtitle2" sx={{ mb: 1 }}>
                  上传文件
                </Typography>
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
                  <Typography color="error" variant="body2" sx={{ mt: 1 }}>
                    {validationErrors.files}
                  </Typography>
                ) : null}
              </Box>

              {isSubmitting ? <LinearProgress aria-label="材料上传进度" /> : null}

              {selectedTask ? (
                <Box
                  component="dl"
                  aria-label="当前选中任务摘要"
                  sx={{
                    display: "grid",
                    gridTemplateColumns: { xs: "1fr", sm: "repeat(2, minmax(0, 1fr))" },
                    gap: 2,
                    m: 0,
                    "& dt": {
                      color: "text.secondary",
                      fontSize: "0.875rem",
                      marginBottom: 0.5,
                    },
                    "& dd": {
                      margin: 0,
                      fontWeight: 600,
                    },
                  }}
                >
                  <Box component="div">
                    <Typography component="dt">比赛名称</Typography>
                    <Typography component="dd">{selectedTask.competition_name}</Typography>
                  </Box>
                  <Box component="div">
                    <Typography component="dt">任务编号</Typography>
                    <Typography component="dd">{selectedTask.id}</Typography>
                  </Box>
                  <Box component="div">
                    <Typography component="dt">任务状态</Typography>
                    <Typography component="dd">{formatTaskStatus(selectedTask.status)}</Typography>
                  </Box>
                  <Box component="div">
                    <Typography component="dt">截止时间</Typography>
                    <Typography component="dd">{formatDateTime(selectedTask.deadline)}</Typography>
                  </Box>
                </Box>
              ) : null}

              <Stack
                direction={{ xs: "column", sm: "row" }}
                spacing={1.5}
                alignItems={{ xs: "stretch", sm: "center" }}
                justifyContent="space-between"
              >
                <Typography variant="body2" color="text.secondary">
                  上传完成后会立即给出成功、部分成功或失败反馈。
                </Typography>
                <Button type="submit" variant="contained" disabled={isSubmitting}>
                  {isSubmitting ? "正在上传..." : "上传材料"}
                </Button>
              </Stack>
            </Stack>
          </SectionCard>
        </Box>
      ) : null}

      {uploadResult ? (
        <SectionCard
          title="上传结果"
          action={<StatusBadge tone={buildUploadResultTone(uploadResult.status)}>{formatUploadResultStatus(uploadResult.status)}</StatusBadge>}
        >
          <Stack spacing={2}>
            {uploadResult.items.length > 0 ? (
              <Stack spacing={2} aria-label="上传成功材料列表">
                {uploadResult.items.map((item) => (
                  <Card key={item.id} variant="outlined">
                    <CardContent>
                      <Stack spacing={1.5}>
                        <Stack direction={{ xs: "column", sm: "row" }} justifyContent="space-between" spacing={1}>
                          <Box>
                            <Typography variant="overline" color="text.secondary">
                              材料编号 {item.id}
                            </Typography>
                            <Typography variant="h6">{item.original_filename}</Typography>
                          </Box>
                          <StatusBadge tone="info">{formatMaterialType(item.material_type)}</StatusBadge>
                        </Stack>
                        <Box
                          component="dl"
                          sx={{
                            display: "grid",
                            gridTemplateColumns: { xs: "1fr", sm: "repeat(2, minmax(0, 1fr))" },
                            gap: 1.5,
                            m: 0,
                            "& dt": {
                              color: "text.secondary",
                              fontSize: "0.875rem",
                              marginBottom: 0.25,
                            },
                            "& dd": {
                              margin: 0,
                            },
                          }}
                        >
                          <Box component="div">
                            <Typography component="dt">提交渠道</Typography>
                            <Typography component="dd">{item.channel}</Typography>
                          </Box>
                          <Box component="div">
                            <Typography component="dt">重复状态</Typography>
                            <Typography component="dd">
                              {item.duplicate_of ? `与材料 ${item.duplicate_of} 重复` : "未检测到重复"}
                            </Typography>
                          </Box>
                          <Box component="div">
                            <Typography component="dt">提交人</Typography>
                            <Typography component="dd">{item.submitter_id ?? "未分配"}</Typography>
                          </Box>
                          <Box component="div">
                            <Typography component="dt">文件大小</Typography>
                            <Typography component="dd">{item.size_bytes} bytes</Typography>
                          </Box>
                        </Box>
                      </Stack>
                    </CardContent>
                  </Card>
                ))}
              </Stack>
            ) : (
              <Typography color="text.secondary">本次上传没有成功写入任何材料记录。</Typography>
            )}

            {uploadResult.failures && uploadResult.failures.length > 0 ? (
              <Box component="ul" aria-label="上传失败列表" sx={{ m: 0, pl: 2.5, display: "grid", gap: 1 }}>
                {uploadResult.failures.map((failure) => (
                  <Box
                    component="li"
                    key={`${failure.original_filename ?? "unknown"}:${failure.error_code}:${failure.detail}`}
                    sx={{ display: "grid", gap: 0.5 }}
                  >
                    <Typography component="strong" variant="body2">
                      {failure.original_filename || "未命名文件"}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {failure.detail}
                    </Typography>
                  </Box>
                ))}
              </Box>
            ) : null}
          </Stack>
        </SectionCard>
      ) : null}
    </RoleWorkspace>
  );
}
