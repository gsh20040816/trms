import { useEffect, useState } from "react";
import { Link as RouterLink, useParams } from "react-router-dom";

import Autocomplete from "@mui/material/Autocomplete";
import Button from "@mui/material/Button";
import Checkbox from "@mui/material/Checkbox";
import FormControl from "@mui/material/FormControl";
import FormControlLabel from "@mui/material/FormControlLabel";
import FormGroup from "@mui/material/FormGroup";
import FormHelperText from "@mui/material/FormHelperText";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";

import { ApiErrorNotice } from "../components/ApiErrorNotice";
import { useConfirmDialog } from "../components/use-confirm-dialog";
import { PageHeader, StatusBadge } from "../components/dashboard";
import { trmsApi } from "../lib/api/trms";
import type {
  ExpenseType,
  ReimbursementTask,
  TaskReadinessIssue,
  TaskReadinessIssueKind,
  TaskReadinessSummary,
  TaskStatus,
  TaskUpdateInput,
} from "../lib/api/types";
import { buildTaskMemberSummaryMap, formatExpenseType, formatTaskMemberLabel, formatTaskStatus } from "../lib/ui-text";
import { AdminWorkspaceShell } from "./admin-workspace-shell";
import { useAuthSession } from "./auth-store";

type TaskDetailState =
  | { status: "loading" }
  | { status: "error"; error: unknown }
  | { status: "ready"; task: ReimbursementTask; readiness: TaskReadinessSummary };

type TaskEditFormState = {
  competitionName: string;
  competitionLocation: string;
  competitionStartDate: string;
  competitionEndDate: string;
  deadline: string;
  memberIds: string[];
  feeCategories: ExpenseType[];
  projectInfo: string;
  reimburserInfo: string;
  invoiceTitle: string;
  taxNumber: string;
};

type ValidationErrorState = Partial<Record<keyof TaskEditFormState, string>>;

const TASK_STATUS_TRANSITIONS: Record<TaskStatus, TaskStatus[]> = {
  draft: ["open"],
  open: ["draft", "closed"],
  closed: ["open", "reviewing"],
  reviewing: ["open", "ready_to_export"],
  ready_to_export: ["completed"],
  completed: [],
};

const FEE_CATEGORY_OPTIONS: Array<{ value: ExpenseType; label: string }> = [
  { value: "registration", label: "参赛费" },
  { value: "railway", label: "火车票" },
  { value: "airfare", label: "航空费" },
  { value: "local_transport", label: "市内交通" },
  { value: "hotel", label: "住宿费" },
  { value: "other", label: "其他" },
];

const READINESS_KIND_TO_ROUTE: Partial<Record<TaskReadinessIssueKind, string>> = {
  recognition_pending: "review",
  recognition_failed: "review",
  recognition_needs_confirmation: "review",
  supporting_material_linkage: "review",
  validation_blocker: "review",
  split_incomplete: "splits",
  member_confirmation_pending: "splits",
  member_confirmation_disputed: "corrections",
  missing_materials: "missing-materials",
  export_blocker: "exports",
};

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function toDateTimeLocalValue(value: string) {
  const date = new Date(value);
  const pad = (segment: number) => String(segment).padStart(2, "0");
  return [
    `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`,
    `${pad(date.getHours())}:${pad(date.getMinutes())}`,
  ].join("T");
}

function buildStatusActionLabel(targetStatus: TaskStatus) {
  return `切换为${formatTaskStatus(targetStatus)}`;
}

function buildReadinessTone(readyForExport: boolean) {
  return readyForExport ? "success" as const : "warning" as const;
}

function buildIssueTone(issue: TaskReadinessIssue) {
  if (
    issue.kind === "recognition_failed"
    || issue.kind === "validation_blocker"
    || issue.kind === "member_confirmation_disputed"
    || issue.kind === "export_blocker"
  ) {
    return "danger" as const;
  }
  return "warning" as const;
}

function buildIssueDescription(issue: TaskReadinessIssue) {
  if (issue.details.length > 0) {
    return issue.details[0];
  }
  switch (issue.kind) {
    case "recognition_pending":
      return "仍有材料处于识别排队或处理中，管理员先无需逐张点开正常材料。";
    case "recognition_failed":
      return "有材料识别失败，需要进入审核页查看原件和失败原因。";
    case "recognition_needs_confirmation":
      return "有识别结果置信度不足，需人工确认关键字段。";
    case "supporting_material_linkage":
      return "仍有辅助材料未安全归到具体发票，需优先处理。";
    case "missing_materials":
      return "仍有必传材料缺失，会直接阻塞后续导出。";
    case "validation_blocker":
      return "当前存在 blocker 级校验失败，任务还不能进入最终导出。";
    case "split_incomplete":
      return "仍有发票分摊金额未闭合，需先补齐金额归属。";
    case "member_confirmation_pending":
      return "仍有成员未确认当前费用明细，需要继续催办或回退处理。";
    case "member_confirmation_disputed":
      return "已有成员提出异议，建议先处理争议再推进任务状态。";
    case "export_blocker":
      return "当前导出 boundary 仍未满足，导出页会展示完整阻塞原因。";
    default:
      return "当前存在待处理问题，请进入对应工作页继续处理。";
  }
}

function buildIssueActionLabel(issue: TaskReadinessIssue) {
  switch (issue.kind) {
    case "missing_materials":
      return "查看缺失材料";
    case "split_incomplete":
    case "member_confirmation_pending":
      return "进入分摊确认";
    case "member_confirmation_disputed":
      return "进入成员提醒";
    case "export_blocker":
      return "查看导出阻塞";
    default:
      return "进入异常处理";
  }
}

function buildIssueActionHref(taskId: string, issue: TaskReadinessIssue) {
  const route = READINESS_KIND_TO_ROUTE[issue.kind];
  return route ? `/admin/tasks/${taskId}/${route}` : `/admin/tasks/${taskId}`;
}

function buildFormState(task: ReimbursementTask): TaskEditFormState {
  return {
    competitionName: task.competition_name,
    competitionLocation: task.competition_location,
    competitionStartDate: task.competition_start_date,
    competitionEndDate: task.competition_end_date,
    deadline: toDateTimeLocalValue(task.deadline),
    memberIds: [...task.member_ids],
    feeCategories: task.fee_categories as ExpenseType[],
    projectInfo: task.project_info,
    reimburserInfo: task.reimburser_info,
    invoiceTitle: task.invoice_title,
    taxNumber: task.tax_number,
  };
}

function validateForm(formState: TaskEditFormState): {
  errors: ValidationErrorState;
  payload: TaskUpdateInput | null;
} {
  const errors: ValidationErrorState = {};

  if (formState.competitionName.trim().length === 0) {
    errors.competitionName = "比赛名称不能为空。";
  }
  if (formState.competitionLocation.trim().length === 0) {
    errors.competitionLocation = "比赛地点不能为空。";
  }
  if (formState.competitionStartDate.length === 0) {
    errors.competitionStartDate = "请选择比赛开始日期。";
  }
  if (formState.competitionEndDate.length === 0) {
    errors.competitionEndDate = "请选择比赛结束日期。";
  }
  if (
    formState.competitionStartDate.length > 0
    && formState.competitionEndDate.length > 0
    && formState.competitionEndDate < formState.competitionStartDate
  ) {
    errors.competitionEndDate = "比赛结束日期不能早于开始日期。";
  }
  if (formState.deadline.length === 0) {
    errors.deadline = "请选择提交截止时间。";
  }

  const normalizedMembers = formState.memberIds.map((memberId) => memberId.trim());
  const hasMember = normalizedMembers.some((memberId) => memberId.length > 0);
  if (!hasMember) {
    errors.memberIds = "至少填写一名成员。";
  } else if (normalizedMembers.some((memberId) => memberId.length === 0)) {
    errors.memberIds = "成员名单不能包含空成员项。";
  }

  if (formState.feeCategories.length === 0) {
    errors.feeCategories = "至少选择一个费用类别。";
  }
  if (formState.projectInfo.trim().length === 0) {
    errors.projectInfo = "项目/课题信息不能为空。";
  }
  if (formState.reimburserInfo.trim().length === 0) {
    errors.reimburserInfo = "报销人信息不能为空。";
  }
  if (formState.invoiceTitle.trim().length === 0) {
    errors.invoiceTitle = "发票抬头不能为空。";
  }
  if (formState.taxNumber.trim().length === 0) {
    errors.taxNumber = "税号不能为空。";
  }

  if (Object.keys(errors).length > 0) {
    return {
      errors,
      payload: null,
    };
  }

  return {
    errors: {},
    payload: {
      competition_name: formState.competitionName.trim(),
      competition_location: formState.competitionLocation.trim(),
      competition_start_date: formState.competitionStartDate,
      competition_end_date: formState.competitionEndDate,
      deadline: new Date(formState.deadline).toISOString(),
      member_ids: normalizedMembers,
      fee_categories: formState.feeCategories,
      project_info: formState.projectInfo.trim(),
      reimburser_info: formState.reimburserInfo.trim(),
      invoice_title: formState.invoiceTitle.trim(),
      tax_number: formState.taxNumber.trim(),
    },
  };
}

export function AdminTaskDetailPage() {
  const session = useAuthSession();
  const { confirm } = useConfirmDialog();
  const { taskId } = useParams<{ taskId: string }>();
  const [state, setState] = useState<TaskDetailState>({ status: "loading" });
  const [formState, setFormState] = useState<TaskEditFormState | null>(null);
  const [memberInputValue, setMemberInputValue] = useState("");
  const [validationErrors, setValidationErrors] = useState<ValidationErrorState>({});
  const [submitError, setSubmitError] = useState<unknown>(null);
  const [saveNotice, setSaveNotice] = useState<string | null>(null);
  const [statusUpdateError, setStatusUpdateError] = useState<unknown>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isUpdatingStatus, setIsUpdatingStatus] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function loadTask() {
      if (!session || session.role !== "admin" || !taskId) {
        return;
      }

      setState({ status: "loading" });
      setSubmitError(null);
      setStatusUpdateError(null);
      setSaveNotice(null);

      try {
        const [task, readiness] = await Promise.all([
          trmsApi.getTask(taskId),
          trmsApi.getTaskReadiness(taskId, session.actorId),
        ]);
        if (cancelled) {
          return;
        }
        setState({
          status: "ready",
          task,
          readiness,
        });
        setFormState(buildFormState(task));
        setValidationErrors({});
        setMemberInputValue("");
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

    void loadTask();

    return () => {
      cancelled = true;
    };
  }, [session, taskId]);

  if (!session || session.role !== "admin") {
    return null;
  }

  if (!taskId) {
    return (
      <AdminWorkspaceShell
        activeModule="tasks"
        header={(
          <PageHeader
            eyebrow="任务管理"
            title="任务详情与状态操作"
            description="查看任务配置、编辑草稿基础信息并推进状态。"
          />
        )}
      >
        <section className="status-card">
          <p className="eyebrow">任务详情</p>
          <h2>任务标识缺失</h2>
          <p>暂时无法读取该任务，请从任务列表重新进入。</p>
        </section>
      </AdminWorkspaceShell>
    );
  }

  const task = state.status === "ready" ? state.task : null;
  const readiness = state.status === "ready" ? state.readiness : null;
  const allowedTransitions = task ? TASK_STATUS_TRANSITIONS[task.status] : [];
  const isForeignTask = task ? task.administrator_id !== session.actorId : false;
  const visibleTask = state.status === "ready" && !isForeignTask ? state.task : null;
  const visibleReadiness = state.status === "ready" && !isForeignTask ? state.readiness : null;
  const memberSummaryMap = visibleTask ? buildTaskMemberSummaryMap(visibleTask.member_summaries) : new Map();
  const isDraftEditable = visibleTask?.status === "draft";

  function updateField<Key extends keyof TaskEditFormState>(
    key: Key,
    value: TaskEditFormState[Key],
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
    setValidationErrors((current) => {
      if (!(key in current)) {
        return current;
      }
      const next = { ...current };
      delete next[key];
      return next;
    });
    setSaveNotice(null);
  }

  function toggleFeeCategory(category: ExpenseType) {
    if (!formState) {
      return;
    }
    const nextCategories = formState.feeCategories.includes(category)
      ? formState.feeCategories.filter((value) => value !== category)
      : [...formState.feeCategories, category];
    updateField("feeCategories", nextCategories);
  }

  function commitMemberInput() {
    if (!formState) {
      return;
    }
    const normalized = memberInputValue.trim();
    if (normalized.length === 0) {
      return;
    }
    updateField("memberIds", [...formState.memberIds, normalized]);
    setMemberInputValue("");
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!visibleTask || !formState || !isDraftEditable) {
      return;
    }

    const { errors, payload } = validateForm(formState);
    setValidationErrors(errors);
    setSubmitError(null);
    setSaveNotice(null);
    if (!payload) {
      return;
    }

    setIsSubmitting(true);
    try {
      const updatedTask = await trmsApi.updateTask(visibleTask.id, payload);
      setState({
        status: "ready",
        task: updatedTask,
        readiness: readiness!,
      });
      setFormState(buildFormState(updatedTask));
      setValidationErrors({});
      setSaveNotice("已保存任务基础配置，当前任务仍保持草稿状态。");
    } catch (error) {
      setSubmitError(error);
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleStatusUpdate(targetStatus: TaskStatus) {
    if (!task || !session) {
      return;
    }
    const actorId = session.actorId;

    const confirmed = await confirm({
      title: `确认将任务切换为${formatTaskStatus(targetStatus)}？`,
      description: `任务 ${task.competition_name} 将从${formatTaskStatus(task.status)}切换为${formatTaskStatus(targetStatus)}。请确认当前阶段的成员提交流程、复核进度和导出准备度都已符合预期。`,
      confirmLabel: "确认切换状态",
      cancelLabel: "保留当前状态",
      destructive: targetStatus === "completed",
      requireTyping: targetStatus === "completed" ? task.competition_name : undefined,
    });
    if (!confirmed) {
      return;
    }

    setStatusUpdateError(null);
    setSubmitError(null);
    setSaveNotice(null);
    setIsUpdatingStatus(true);
    try {
      const updatedTask = await trmsApi.updateTaskStatus(task.id, {
        target_status: targetStatus,
      });
      const updatedReadiness = await trmsApi.getTaskReadiness(task.id, actorId);
      setState({
        status: "ready",
        task: updatedTask,
        readiness: updatedReadiness,
      });
      setFormState(buildFormState(updatedTask));
      setValidationErrors({});
    } catch (error) {
      setStatusUpdateError(error);
    } finally {
      setIsUpdatingStatus(false);
    }
  }

  return (
    <AdminWorkspaceShell
      activeModule="tasks"
      taskId={taskId}
      task={visibleTask}
      header={(
          <PageHeader
            eyebrow="任务管理"
            title="任务详情与状态操作"
            description="这里优先查看任务就绪度和异常优先队列，再处理草稿配置和状态推进。"
            actions={(
              <div className="page-actions">
                <Button component={RouterLink} variant="contained" to={`/admin/tasks/${taskId}/invoices`}>
                录入或更正发票
              </Button>
              <Button component={RouterLink} variant="outlined" to={`/admin/tasks/${taskId}/missing-materials`}>
                查看缺失材料
              </Button>
            </div>
          )}
        />
      )}
    >
      {state.status === "loading" ? (
        <section className="status-card admin-task-detail-panel">
          <p className="eyebrow">Loading</p>
          <h2>正在加载任务详情</h2>
          <p>正在读取任务基础配置和当前状态，请稍候。</p>
        </section>
      ) : null}

      {state.status === "error" ? <ApiErrorNotice error={state.error} /> : null}
      {submitError ? <ApiErrorNotice error={submitError} /> : null}
      {statusUpdateError ? <ApiErrorNotice error={statusUpdateError} /> : null}

      {saveNotice ? (
        <section className="status-card admin-task-detail-panel">
          <p className="eyebrow">保存完成</p>
          <h2>任务基础配置已更新</h2>
          <p>{saveNotice}</p>
        </section>
      ) : null}

      {state.status === "ready" && isForeignTask ? (
        <section className="status-card admin-task-detail-panel">
          <p className="eyebrow">访问范围</p>
          <h2>当前任务不属于此管理员</h2>
          <p>你当前没有处理该任务的权限，如需访问请联系对应负责人。</p>
        </section>
      ) : null}

      {visibleTask && formState ? (
        <section className="task-detail-layout">
          <article className="status-card admin-task-detail-panel">
            <div className="task-card-header">
              <div>
                <p className="task-card-id">任务详情</p>
                <h2>{visibleTask.competition_name}</h2>
              </div>
              <StatusBadge tone="info">{formatTaskStatus(visibleTask.status)}</StatusBadge>
            </div>

            <dl className="task-detail-grid">
              <div>
                <dt>比赛地点</dt>
                <dd>{visibleTask.competition_location}</dd>
              </div>
              <div>
                <dt>比赛时间</dt>
                <dd>
                  {visibleTask.competition_start_date} 至 {visibleTask.competition_end_date}
                </dd>
              </div>
              <div>
                <dt>提交截止时间</dt>
                <dd>{formatDateTime(visibleTask.deadline)}</dd>
              </div>
              <div>
                <dt>任务负责人</dt>
                <dd>{session.displayName}</dd>
              </div>
              <div>
                <dt>项目/课题信息</dt>
                <dd>{visibleTask.project_info}</dd>
              </div>
              <div>
                <dt>报销人信息</dt>
                <dd>{visibleTask.reimburser_info}</dd>
              </div>
              <div>
                <dt>发票抬头</dt>
                <dd>{visibleTask.invoice_title}</dd>
              </div>
              <div>
                <dt>税号</dt>
                <dd>{visibleTask.tax_number}</dd>
              </div>
            </dl>
          </article>

          {visibleReadiness ? (
            <>
              <article className="status-card admin-task-detail-panel">
                <div className="admin-form-header">
                  <div>
                    <p className="eyebrow">Task Readiness</p>
                    <h2>任务就绪度总览</h2>
                  </div>
                  <StatusBadge tone={buildReadinessTone(visibleReadiness.ready_for_export)}>
                    {visibleReadiness.ready_for_export ? "可导出" : "仍有阻塞"}
                  </StatusBadge>
                </div>
                <p className="field-hint">
                  第一屏先看还有哪些门禁没过；正常材料不要求管理员逐张点开确认。
                </p>
                <dl className="task-detail-grid" aria-label="任务就绪度统计">
                  <div>
                    <dt>待识别</dt>
                    <dd>{visibleReadiness.counts.pending_recognition_count}</dd>
                  </div>
                  <div>
                    <dt>识别失败</dt>
                    <dd>{visibleReadiness.counts.failed_recognition_count}</dd>
                  </div>
                  <div>
                    <dt>低置信待确认</dt>
                    <dd>{visibleReadiness.counts.needs_confirmation_recognition_count}</dd>
                  </div>
                  <div>
                    <dt>待关联附件</dt>
                    <dd>{visibleReadiness.counts.pending_supporting_material_linkage_count}</dd>
                  </div>
                  <div>
                    <dt>缺失材料</dt>
                    <dd>{visibleReadiness.counts.missing_material_count}</dd>
                  </div>
                  <div>
                    <dt>异常校验</dt>
                    <dd>{visibleReadiness.counts.blocker_validation_count}</dd>
                  </div>
                  <div>
                    <dt>分摊未完成</dt>
                    <dd>{visibleReadiness.counts.split_incomplete_count}</dd>
                  </div>
                  <div>
                    <dt>成员未确认</dt>
                    <dd>{visibleReadiness.counts.pending_confirmation_count}</dd>
                  </div>
                  <div>
                    <dt>有异议</dt>
                    <dd>{visibleReadiness.counts.disputed_confirmation_count}</dd>
                  </div>
                  <div>
                    <dt>导出阻塞原因</dt>
                    <dd>{visibleReadiness.counts.export_blocking_reason_count}</dd>
                  </div>
                </dl>
                {visibleReadiness.export_blocking_reasons.length > 0 ? (
                  <div className="field-stack" aria-label="导出阻塞原因">
                    <p className="field-hint">当前仍存在以下导出阻塞原因：</p>
                    <ul className="admin-review-list">
                      {visibleReadiness.export_blocking_reasons.map((reason) => (
                        <li key={reason}>{reason}</li>
                      ))}
                    </ul>
                  </div>
                ) : (
                  <p className="field-hint">当前任务已满足导出边界，可以进入导出页生成材料包。</p>
                )}
              </article>

              <article className="status-card admin-task-detail-panel" aria-label="异常优先队列">
                <div className="admin-form-header">
                  <div>
                    <p className="eyebrow">Priority Queue</p>
                    <h2>异常优先队列</h2>
                  </div>
                  <StatusBadge tone={visibleReadiness.issues.length > 0 ? "warning" : "success"}>
                    {visibleReadiness.issues.length > 0 ? `${visibleReadiness.issues.length} 类待处理问题` : "全部通过"}
                  </StatusBadge>
                </div>
                {visibleReadiness.issues.length === 0 ? (
                  <p className="field-hint">
                    当前没有待处理异常，管理员可以直接进入导出页生成最新材料包。
                  </p>
                ) : (
                  <div className="page-stack">
                    {visibleReadiness.issues.map((issue) => (
                      <section key={issue.kind} className="admin-form-card">
                        <div className="task-card-header">
                          <div>
                            <p className="task-card-id">
                              {issue.count} 项待处理
                              {issue.invoice_ids.length > 0 ? ` / ${issue.invoice_ids.length} 张发票` : ""}
                              {issue.material_ids.length > 0 ? ` / ${issue.material_ids.length} 份材料` : ""}
                            </p>
                            <h3>{issue.label}</h3>
                          </div>
                          <StatusBadge tone={buildIssueTone(issue)}>
                            {issue.blocking ? "阻塞中" : "需关注"}
                          </StatusBadge>
                        </div>
                        <p className="field-hint">{buildIssueDescription(issue)}</p>
                        <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5}>
                          <Button
                            component={RouterLink}
                            variant="contained"
                            to={buildIssueActionHref(taskId, issue)}
                          >
                            {buildIssueActionLabel(issue)}
                          </Button>
                          {issue.details.length > 0 ? (
                            <div className="field-stack">
                              <span className="field-hint">示例问题：</span>
                              <span>{issue.details[0]}</span>
                            </div>
                          ) : null}
                        </Stack>
                      </section>
                    ))}
                  </div>
                )}
              </article>
            </>
          ) : null}

          <article className="status-card admin-form-card">
            <div className="admin-form-header">
              <div>
                <p className="eyebrow">Task Config</p>
                <h2>任务基础配置</h2>
              </div>
              <StatusBadge tone={isDraftEditable ? "warning" : "info"}>
                {isDraftEditable ? "草稿中，可编辑" : `当前状态：${formatTaskStatus(visibleTask.status)}`}
              </StatusBadge>
            </div>

            {!isDraftEditable ? (
              <p className="field-hint">
                当前任务已不在草稿状态，基础配置仅供查看；如需调整，请先处理状态回退或重新创建任务。
              </p>
            ) : (
              <p className="field-hint">
                仅草稿任务允许修改基础配置。保存成功后不会自动发布，仍需你手动推进状态。
              </p>
            )}

            <form
              className="page-stack"
              onSubmit={(event) => {
                void handleSubmit(event);
              }}
              noValidate
            >
              <section className="admin-form-card">
                <div className="admin-form-header">
                  <div>
                    <p className="eyebrow">Competition</p>
                    <h3>比赛与时间信息</h3>
                  </div>
                </div>
                <div className="admin-form-grid">
                  <TextField
                    label="比赛名称"
                    value={formState.competitionName}
                    onChange={(event) => {
                      updateField("competitionName", event.target.value);
                    }}
                    error={Boolean(validationErrors.competitionName)}
                    helperText={validationErrors.competitionName}
                    disabled={!isDraftEditable}
                    fullWidth
                  />
                  <TextField
                    label="比赛地点"
                    value={formState.competitionLocation}
                    onChange={(event) => {
                      updateField("competitionLocation", event.target.value);
                    }}
                    error={Boolean(validationErrors.competitionLocation)}
                    helperText={validationErrors.competitionLocation}
                    disabled={!isDraftEditable}
                    fullWidth
                  />
                  <TextField
                    label="比赛开始日期"
                    type="date"
                    value={formState.competitionStartDate}
                    onChange={(event) => {
                      updateField("competitionStartDate", event.target.value);
                    }}
                    error={Boolean(validationErrors.competitionStartDate)}
                    helperText={validationErrors.competitionStartDate}
                    disabled={!isDraftEditable}
                    fullWidth
                    slotProps={{ inputLabel: { shrink: true } }}
                  />
                  <TextField
                    label="比赛结束日期"
                    type="date"
                    value={formState.competitionEndDate}
                    onChange={(event) => {
                      updateField("competitionEndDate", event.target.value);
                    }}
                    error={Boolean(validationErrors.competitionEndDate)}
                    helperText={validationErrors.competitionEndDate}
                    disabled={!isDraftEditable}
                    fullWidth
                    slotProps={{ inputLabel: { shrink: true } }}
                  />
                  <TextField
                    label="提交截止时间"
                    type="datetime-local"
                    value={formState.deadline}
                    onChange={(event) => {
                      updateField("deadline", event.target.value);
                    }}
                    error={Boolean(validationErrors.deadline)}
                    helperText={validationErrors.deadline}
                    disabled={!isDraftEditable}
                    fullWidth
                    slotProps={{ inputLabel: { shrink: true } }}
                  />
                </div>
              </section>

              <section className="admin-form-card">
                <div className="admin-form-header">
                  <div>
                    <p className="eyebrow">Members</p>
                    <h3>成员名单与费用类别</h3>
                  </div>
                </div>

                <Stack spacing={3}>
                  <Autocomplete
                    multiple
                    freeSolo
                    options={[]}
                    value={formState.memberIds}
                    inputValue={memberInputValue}
                    readOnly={!isDraftEditable}
                    onInputChange={(_event, value, reason) => {
                      if (reason === "reset") {
                        setMemberInputValue("");
                        return;
                      }
                      setMemberInputValue(value);
                    }}
                    onChange={(_event, value) => {
                      updateField(
                        "memberIds",
                        value
                          .map((memberId) => memberId.trim())
                          .filter((memberId) => memberId.length > 0),
                      );
                    }}
                    onKeyDown={(event) => {
                      if ((event.key === "Enter" || event.key === ",") && memberInputValue.trim().length > 0) {
                        event.preventDefault();
                        commitMemberInput();
                      }
                    }}
                    renderInput={(params) => (
                      <TextField
                        {...params}
                        label="成员名单"
                        placeholder="输入成员姓名或学号后按回车添加"
                        error={Boolean(validationErrors.memberIds)}
                        helperText={validationErrors.memberIds ?? "当前阶段请填写成员姓名或学号字符串，不要填写内部数据库 ID。"}
                      />
                    )}
                  />

                  <ul className="token-list" aria-label="任务成员名单">
                    {formState.memberIds.map((memberId) => (
                      <li key={memberId} className="token-chip">
                        {formatTaskMemberLabel(memberId, memberSummaryMap)}
                      </li>
                    ))}
                  </ul>

                  <FormControl error={Boolean(validationErrors.feeCategories)} component="fieldset" variant="standard">
                    <FormGroup className="checkbox-grid" aria-label="费用类别">
                      {FEE_CATEGORY_OPTIONS.map((option) => (
                        <FormControlLabel
                          key={option.value}
                          className="checkbox-card"
                          control={(
                            <Checkbox
                              checked={formState.feeCategories.includes(option.value)}
                              onChange={() => {
                                toggleFeeCategory(option.value);
                              }}
                              disabled={!isDraftEditable}
                            />
                          )}
                          label={option.label}
                        />
                      ))}
                    </FormGroup>
                    <FormHelperText>
                      {validationErrors.feeCategories ?? "请选择当前任务允许的费用类别。"}
                    </FormHelperText>
                  </FormControl>

                  <ul className="token-list" aria-label="任务费用类别">
                    {formState.feeCategories.map((category) => (
                      <li key={category} className="token-chip">
                        {formatExpenseType(category)}
                      </li>
                    ))}
                  </ul>
                </Stack>
              </section>

              <section className="admin-form-card">
                <div className="admin-form-header">
                  <div>
                    <p className="eyebrow">Reimbursement</p>
                    <h3>项目与报销信息</h3>
                  </div>
                </div>
                <div className="admin-form-grid">
                  <TextField
                    label="项目/课题信息"
                    value={formState.projectInfo}
                    onChange={(event) => {
                      updateField("projectInfo", event.target.value);
                    }}
                    error={Boolean(validationErrors.projectInfo)}
                    helperText={validationErrors.projectInfo}
                    disabled={!isDraftEditable}
                    multiline
                    minRows={3}
                    fullWidth
                  />
                  <TextField
                    label="报销人信息"
                    value={formState.reimburserInfo}
                    onChange={(event) => {
                      updateField("reimburserInfo", event.target.value);
                    }}
                    error={Boolean(validationErrors.reimburserInfo)}
                    helperText={validationErrors.reimburserInfo}
                    disabled={!isDraftEditable}
                    multiline
                    minRows={3}
                    fullWidth
                  />
                  <TextField
                    label="发票抬头"
                    value={formState.invoiceTitle}
                    onChange={(event) => {
                      updateField("invoiceTitle", event.target.value);
                    }}
                    error={Boolean(validationErrors.invoiceTitle)}
                    helperText={validationErrors.invoiceTitle}
                    disabled={!isDraftEditable}
                    fullWidth
                  />
                  <TextField
                    label="税号"
                    value={formState.taxNumber}
                    onChange={(event) => {
                      updateField("taxNumber", event.target.value);
                    }}
                    error={Boolean(validationErrors.taxNumber)}
                    helperText={validationErrors.taxNumber}
                    disabled={!isDraftEditable}
                    fullWidth
                  />
                </div>
              </section>

              <section className="admin-form-card admin-form-footer">
                <div>
                  <p className="eyebrow">保存</p>
                  <h3>更新草稿任务配置</h3>
                  <p>保存会覆盖当前草稿任务的基础信息，但不会改变状态。</p>
                </div>
                <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5}>
                  <Button component={RouterLink} to="/admin" variant="outlined" color="inherit">
                    返回任务列表
                  </Button>
                  <Button type="submit" variant="contained" disabled={!isDraftEditable || isSubmitting}>
                    {isSubmitting ? "正在保存..." : "保存任务基础配置"}
                  </Button>
                </Stack>
              </section>
            </form>
          </article>

          <article className="status-card admin-task-detail-panel">
            <div className="admin-form-header">
              <div>
                <p className="eyebrow">Status Actions</p>
                <h2>状态流转操作</h2>
              </div>
              <StatusBadge tone="info">
                当前状态：{formatTaskStatus(visibleTask.status)}
              </StatusBadge>
            </div>
            {allowedTransitions.length > 0 ? (
              <>
                <p className="field-hint">
                  只显示当前可执行的下一步操作。如果条件未满足，页面会给出可执行提示。
                </p>
                <div className="status-action-grid">
                  {allowedTransitions.map((targetStatus) => (
                    <Button
                      key={targetStatus}
                      type="button"
                      variant="contained"
                      disabled={isUpdatingStatus}
                      onClick={() => {
                        void handleStatusUpdate(targetStatus);
                      }}
                    >
                      {isUpdatingStatus ? "正在提交状态更新..." : buildStatusActionLabel(targetStatus)}
                    </Button>
                  ))}
                </div>
              </>
            ) : (
              <p className="field-hint">
                当前任务已经没有可继续推进的下一步操作，可返回任务列表查看其他事项。
              </p>
            )}
          </article>
        </section>
      ) : null}
    </AdminWorkspaceShell>
  );
}
