import { startTransition, useEffect, useRef, useState } from "react";
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
import Typography from "@mui/material/Typography";

import { ApiErrorNotice } from "../components/ApiErrorNotice";
import { useConfirmDialog } from "../components/use-confirm-dialog";
import { MetadataChip, PageHeader, StatusBadge, SurfaceCard } from "../components/dashboard";
import { trmsApi } from "../lib/api/trms";
import type {
  ExpenseType,
  ReimbursementTask,
  TaskReadinessIssue,
  TaskReadinessIssueKind,
  TaskReadinessSummary,
  TaskStatus,
  TaskUpdateInput,
  UserSearchSummary,
} from "../lib/api/types";
import { buildTaskMemberSummaryMap, formatExpenseType, formatTaskMemberLabel, formatTaskStatus, formatUserSearchSummary } from "../lib/ui-text";
import {
  buildTaskAdministratorSearchOptions,
  formatTaskAdministratorCountLabel,
  getTaskAdministratorIds,
  isTaskVisibleToAdministrator,
} from "../lib/task-administrators";
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
  emailSubmissionKey: string;
  memberIds: string[];
  administratorIds: string[];
  feeCategories: ExpenseType[];
  invoiceTitle: string;
  taxNumber: string;
};

type ValidationErrorState = Partial<Record<keyof TaskEditFormState, string>>;

const TASK_STATUS_TRANSITIONS: Record<TaskStatus, TaskStatus[]> = {
  draft: ["open"],
  open: ["draft", "reviewing"],
  closed: ["open", "ready_to_export"],
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
  missing_materials: "review",
  split_incomplete: "splits",
  member_confirmation_pending: "splits",
  member_confirmation_disputed: "corrections",
  export_blocker: "exports",
};

const READINESS_GROUPS: Array<{
  key: string;
  title: string;
  items: Array<{
    label: string;
    getValue: (readiness: TaskReadinessSummary) => number;
  }>;
}> = [
  {
    key: "recognition",
    title: "识别与归档",
    items: [
      { label: "待识别", getValue: (readiness) => readiness.counts.pending_recognition_count },
      { label: "识别失败", getValue: (readiness) => readiness.counts.failed_recognition_count },
      { label: "待人工确认", getValue: (readiness) => readiness.counts.needs_confirmation_recognition_count },
      { label: "待关联附件", getValue: (readiness) => readiness.counts.pending_supporting_material_linkage_count },
    ],
  },
  {
    key: "materials",
    title: "材料与校验",
    items: [
      { label: "缺失材料", getValue: (readiness) => readiness.counts.missing_material_count },
      { label: "异常校验", getValue: (readiness) => readiness.counts.blocker_validation_count },
    ],
  },
  {
    key: "confirmation",
    title: "分摊与确认",
    items: [
      { label: "分摊未完成", getValue: (readiness) => readiness.counts.split_incomplete_count },
      { label: "成员未确认", getValue: (readiness) => readiness.counts.pending_confirmation_count },
      { label: "成员异议", getValue: (readiness) => readiness.counts.disputed_confirmation_count },
    ],
  },
  {
    key: "export",
    title: "导出准备",
    items: [
      { label: "导出阻塞", getValue: (readiness) => readiness.counts.export_blocking_reason_count },
    ],
  },
];

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
      return "进入材料审核";
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

function buildReadinessGroups(readiness: TaskReadinessSummary) {
  return READINESS_GROUPS.map((group) => ({
    ...group,
    total: group.items.reduce((sum, item) => sum + item.getValue(readiness), 0),
  }));
}

function isExportStageAvailable(taskStatus: TaskStatus) {
  return taskStatus === "ready_to_export" || taskStatus === "completed";
}

function buildReadinessGroupStatus(
  groupKey: string,
  total: number,
  taskStatus: TaskStatus,
) {
  if (groupKey === "export" && total === 0 && !isExportStageAvailable(taskStatus)) {
    return {
      tone: "neutral" as const,
      label: "阶段未到",
      title: "当前阶段未开放正式导出",
    };
  }
  return {
    tone: total > 0 ? "warning" as const : "success" as const,
    label: total > 0 ? "仍需处理" : "已通过",
    title: `${total} 项待处理`,
  };
}

function buildVisiblePriorityIssues(readiness: TaskReadinessSummary) {
  return readiness.issues.filter((issue) => issue.kind !== "export_blocker");
}

function buildFormState(task: ReimbursementTask): TaskEditFormState {
  return {
    competitionName: task.competition_name,
    competitionLocation: task.competition_location,
    competitionStartDate: task.competition_start_date,
    competitionEndDate: task.competition_end_date,
    deadline: toDateTimeLocalValue(task.deadline),
    emailSubmissionKey: task.email_submission_key ?? "",
    memberIds: [...task.member_ids],
    administratorIds: getTaskAdministratorIds(task),
    feeCategories: task.fee_categories as ExpenseType[],
    invoiceTitle: task.invoice_title,
    taxNumber: task.tax_number,
  };
}

function validateForm(formState: TaskEditFormState): {
  errors: ValidationErrorState;
  payload: TaskUpdateInput | null;
} {
  const errors: ValidationErrorState = {};
  const normalizedEmailSubmissionKey = formState.emailSubmissionKey.trim().toLowerCase();

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
  if (normalizedEmailSubmissionKey.length === 0) {
    errors.emailSubmissionKey = "请填写邮件提交标识。";
  } else if (!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(normalizedEmailSubmissionKey)) {
    errors.emailSubmissionKey = "邮件提交标识只能包含小写字母、数字和单个连字符。";
  } else if (/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(normalizedEmailSubmissionKey)) {
    errors.emailSubmissionKey = "邮件提交标识不能直接使用 UUID。";
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
      email_submission_key: normalizedEmailSubmissionKey,
      member_ids: normalizedMembers,
      fee_categories: formState.feeCategories,
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
  const [administratorInputValue, setAdministratorInputValue] = useState("");
  const [administratorOptions, setAdministratorOptions] = useState<UserSearchSummary[]>([]);
  const [administratorSearchError, setAdministratorSearchError] = useState<unknown>(null);
  const [isSearchingAdministrators, setIsSearchingAdministrators] = useState(false);
  const [validationErrors, setValidationErrors] = useState<ValidationErrorState>({});
  const [submitError, setSubmitError] = useState<unknown>(null);
  const [saveNotice, setSaveNotice] = useState<string | null>(null);
  const [statusUpdateError, setStatusUpdateError] = useState<unknown>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isUpdatingStatus, setIsUpdatingStatus] = useState(false);
  const administratorSearchTimerRef = useRef<number | null>(null);

  useEffect(() => (
    () => {
      if (administratorSearchTimerRef.current !== null) {
        window.clearTimeout(administratorSearchTimerRef.current);
      }
    }
  ), []);

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
        setAdministratorInputValue("");
        setAdministratorSearchError(null);
        setIsSearchingAdministrators(false);
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
        <SurfaceCard component="section" className="status-card">
          <p className="eyebrow">任务详情</p>
          <h2>任务标识缺失</h2>
          <p>暂时无法读取该任务，请从任务列表重新进入。</p>
        </SurfaceCard>
      </AdminWorkspaceShell>
    );
  }

  const task = state.status === "ready" ? state.task : null;
  const readiness = state.status === "ready" ? state.readiness : null;
  const allowedTransitions = task ? TASK_STATUS_TRANSITIONS[task.status] : [];
  const isForeignTask = task ? !isTaskVisibleToAdministrator(task, session.actorId) : false;
  const visibleTask = state.status === "ready" && !isForeignTask ? state.task : null;
  const visibleReadiness = state.status === "ready" && !isForeignTask ? state.readiness : null;
  const readinessGroups = visibleReadiness ? buildReadinessGroups(visibleReadiness) : [];
  const visiblePriorityIssues = visibleReadiness ? buildVisiblePriorityIssues(visibleReadiness) : [];
  const memberSummaryMap = visibleTask ? buildTaskMemberSummaryMap(visibleTask.member_summaries) : new Map();
  const isDraftEditable = visibleTask?.status === "draft";
  const selectedAdministratorOptions = formState
    ? buildTaskAdministratorSearchOptions(formState.administratorIds, administratorOptions)
    : [];
  const visibleAdministratorOptions = formState
    ? administratorOptions.filter((option) => !formState.administratorIds.includes(option.actor_id))
    : [];

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

  function addAdministrator(administrator: UserSearchSummary) {
    if (!formState || formState.administratorIds.includes(administrator.actor_id)) {
      return;
    }
    updateField("administratorIds", [...formState.administratorIds, administrator.actor_id]);
  }

  function removeAdministrator(administratorId: string) {
    if (!formState) {
      return;
    }
    updateField(
      "administratorIds",
      formState.administratorIds.filter(
        (currentAdministratorId) => currentAdministratorId !== administratorId,
      ),
    );
  }

  function handleAdministratorKeywordChange(value: string) {
    setAdministratorInputValue(value);
    const keyword = value.trim();
    if (administratorSearchTimerRef.current !== null) {
      window.clearTimeout(administratorSearchTimerRef.current);
      administratorSearchTimerRef.current = null;
    }

    if (keyword.length === 0) {
      setAdministratorOptions([]);
      setAdministratorSearchError(null);
      setIsSearchingAdministrators(false);
      return;
    }

    setIsSearchingAdministrators(true);
    setAdministratorSearchError(null);
    administratorSearchTimerRef.current = window.setTimeout(() => {
      void trmsApi.searchTaskAdministratorCandidates(keyword, 10)
        .then((response) => {
          startTransition(() => {
            setAdministratorOptions(response.items);
          });
        })
        .catch((error) => {
          setAdministratorOptions([]);
          setAdministratorSearchError(error);
        })
        .finally(() => {
          setIsSearchingAdministrators(false);
          administratorSearchTimerRef.current = null;
        });
    }, 250);
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
      const updatedTask = await trmsApi.updateTask(visibleTask.id, {
        ...payload,
        administrator_id: formState.administratorIds[0] ?? visibleTask.administrator_id,
        administrator_ids: formState.administratorIds,
      });
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
              <Button component={RouterLink} variant="outlined" to={`/admin/tasks/${taskId}/review`}>
                进入材料审核
              </Button>
            </div>
          )}
        />
      )}
    >
      {state.status === "loading" ? (
        <SurfaceCard component="section" className="status-card admin-task-detail-panel">
          <p className="eyebrow">加载中</p>
          <h2>正在加载任务详情</h2>
          <p>正在读取任务基础配置和当前状态，请稍候。</p>
        </SurfaceCard>
      ) : null}

      {state.status === "error" ? <ApiErrorNotice error={state.error} /> : null}
      {submitError ? <ApiErrorNotice error={submitError} /> : null}
      {statusUpdateError ? <ApiErrorNotice error={statusUpdateError} /> : null}

      {saveNotice ? (
        <SurfaceCard component="section" className="status-card admin-task-detail-panel">
          <p className="eyebrow">保存完成</p>
          <h2>任务基础配置已更新</h2>
          <p>{saveNotice}</p>
        </SurfaceCard>
      ) : null}

      {state.status === "ready" && isForeignTask ? (
        <SurfaceCard component="section" className="status-card admin-task-detail-panel">
          <p className="eyebrow">访问范围</p>
          <h2>当前任务不属于此管理员</h2>
          <p>你当前没有处理该任务的权限，如需访问请联系对应负责人。</p>
        </SurfaceCard>
      ) : null}

      {visibleTask && formState ? (
        <section className="task-detail-layout">
          <SurfaceCard component="article" className="status-card admin-task-detail-panel">
            <div className="task-card-header">
              <div>
                <p className="task-card-id">任务摘要</p>
                <h2>{visibleTask.competition_name}</h2>
              </div>
              <StatusBadge tone="info">{formatTaskStatus(visibleTask.status)}</StatusBadge>
            </div>

            <dl className="task-detail-grid admin-task-summary-grid">
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
                <dt>邮件提交标识</dt>
                <dd>{visibleTask.email_submission_key ?? "未配置"}</dd>
              </div>
              <div>
                <dt>任务管理员</dt>
                <dd>{formatTaskAdministratorCountLabel(visibleTask)}</dd>
              </div>
              <div>
                <dt>参赛成员</dt>
                <dd>{visibleTask.member_ids.length} 人</dd>
              </div>
              <div>
                <dt>费用类别</dt>
                <dd>{visibleTask.fee_categories.length} 类</dd>
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
            <div className="admin-task-summary-strip">
              <div>
                <span>管理员名单</span>
                <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap" aria-label="任务管理员列表" sx={{ mt: 1 }}>
                  {buildTaskAdministratorSearchOptions(getTaskAdministratorIds(visibleTask), administratorOptions).map((administrator) => (
                    <MetadataChip
                      key={administrator.actor_id}
                      component="span"
                      className="token-chip"
                      label={formatUserSearchSummary(administrator)}
                    />
                  ))}
                </Stack>
              </div>
              <div>
                <span>当前费用类别</span>
                <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap" aria-label="任务摘要费用类别" sx={{ mt: 1 }}>
                  {visibleTask.fee_categories.map((category) => (
                    <MetadataChip
                      key={category}
                      component="span"
                      className="token-chip"
                      label={formatExpenseType(category as ExpenseType)}
                    />
                  ))}
                </Stack>
              </div>
            </div>
          </SurfaceCard>

          {visibleReadiness ? (
            <>
              <SurfaceCard component="article" className="status-card admin-task-detail-panel">
                <div className="admin-form-header">
                  <div>
                    <p className="eyebrow">就绪度</p>
                    <h2>任务就绪度总览</h2>
                  </div>
                  <StatusBadge tone={buildReadinessTone(visibleReadiness.ready_for_export)}>
                    {visibleReadiness.ready_for_export ? "可导出" : "仍有阻塞"}
                  </StatusBadge>
                </div>
                <p className="field-hint">
                  第一屏先看还有哪些门禁没过；正常材料不要求管理员逐张点开确认。
                </p>
                <div className="admin-task-readiness-groups" aria-label="任务就绪度统计">
                  {readinessGroups.map((group) => (
                    <section key={group.key} className="admin-task-readiness-card">
                      {(() => {
                        const groupStatus = buildReadinessGroupStatus(group.key, group.total, visibleTask.status);
                        return (
                      <div className="task-card-header">
                        <div>
                          <p className="task-card-id">{group.title}</p>
                          <h3>{groupStatus.title}</h3>
                        </div>
                        <StatusBadge tone={groupStatus.tone}>
                          {groupStatus.label}
                        </StatusBadge>
                      </div>
                        );
                      })()}
                      <dl className="admin-task-readiness-metrics">
                        {group.items.map((item) => (
                          <div key={item.label}>
                            <dt>{item.label}</dt>
                            <dd>{item.getValue(visibleReadiness)}</dd>
                          </div>
                        ))}
                      </dl>
                    </section>
                  ))}
                </div>
                {visibleReadiness.export_blocking_reasons.length > 0 ? (
                  <div className="field-stack" aria-label="导出阻塞原因">
                    <p className="field-hint">导出前仍需先处理以下阻塞项：</p>
                    <ul className="admin-task-blocker-list">
                      {visibleReadiness.export_blocking_reasons.map((reason) => (
                        <li key={reason}>{reason}</li>
                      ))}
                    </ul>
                  </div>
                ) : !isExportStageAvailable(visibleTask.status) ? (
                  <p className="field-hint">
                    当前任务仍处于{formatTaskStatus(visibleTask.status)}阶段；进入“可导出”或“已完成”阶段后，再检查正式导出门禁。
                  </p>
                ) : (
                  <p className="field-hint">当前任务已满足导出边界，可以进入导出页生成材料包。</p>
                )}
              </SurfaceCard>

              <SurfaceCard component="article" className="status-card admin-task-detail-panel" aria-label="异常优先队列">
                <div className="admin-form-header">
                  <div>
                    <p className="eyebrow">优先处理</p>
                    <h2>异常优先队列</h2>
                  </div>
                  <StatusBadge tone={visiblePriorityIssues.length > 0 ? "warning" : "success"}>
                    {visiblePriorityIssues.length > 0 ? `${visiblePriorityIssues.length} 类待处理问题` : "全部通过"}
                  </StatusBadge>
                </div>
                {visiblePriorityIssues.length === 0 ? (
                  <p className="field-hint">
                    {visibleReadiness.export_blocking_reasons.length > 0
                      ? "当前没有待处理异常；导出阶段门禁请看上方“导出阻塞原因”。"
                      : !isExportStageAvailable(visibleTask.status)
                        ? "当前没有待处理异常；导出会在任务进入“可导出”或“已完成”阶段后开放。"
                        : "当前没有待处理异常，管理员可以直接进入导出页生成最新材料包。"}
                  </p>
                ) : (
                  <div className="page-stack">
                    {visiblePriorityIssues.map((issue) => (
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
                        <Stack className="admin-task-detail-issue-actions" spacing={1.5}>
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
              </SurfaceCard>
            </>
          ) : null}

          <SurfaceCard component="article" className="status-card admin-form-card">
            <div className="admin-form-header">
              <div>
                <p className="eyebrow">任务配置</p>
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
                    <p className="eyebrow">比赛信息</p>
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
                  <TextField
                    label="邮件提交标识"
                    value={formState.emailSubmissionKey}
                    onChange={(event) => {
                      updateField("emailSubmissionKey", event.target.value);
                    }}
                    error={Boolean(validationErrors.emailSubmissionKey)}
                    helperText={
                      validationErrors.emailSubmissionKey
                      ?? "成员发邮件时主题使用的稳定标识，例如 icpc-shanghai。"
                    }
                    disabled={!isDraftEditable}
                    placeholder="例如 icpc-shanghai"
                    fullWidth
                  />
                </div>
              </section>

              <section className="admin-form-card">
                <div className="admin-form-header">
                  <div>
                    <p className="eyebrow">成员与费用</p>
                    <h3>成员名单、管理员与费用类别</h3>
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
                      <MetadataChip
                        key={memberId}
                        component="li"
                        className="token-chip"
                        label={formatTaskMemberLabel(memberId, memberSummaryMap)}
                      />
                    ))}
                  </ul>

                  <Stack spacing={0.75}>
                    <TextField
                      label="管理员搜索"
                      value={administratorInputValue}
                      onChange={(event) => {
                        handleAdministratorKeywordChange(event.target.value);
                      }}
                      placeholder="输入管理员姓名、用户名或管理员标识检索"
                      error={Boolean(validationErrors.administratorIds)}
                      helperText={
                        validationErrors.administratorIds
                        ?? (
                          isSearchingAdministrators
                            ? "正在检索管理员..."
                            : "草稿任务可继续追加或移除管理员；首位管理员会作为兼容主负责人字段返回。"
                        )
                      }
                      disabled={!isDraftEditable}
                      fullWidth
                    />

                    {administratorInputValue.trim().length > 0 ? (
                      <Stack
                        spacing={0.5}
                        aria-label="管理员候选列表"
                        sx={{
                          borderRadius: 3,
                          border: "1px solid",
                          borderColor: "divider",
                          bgcolor: "background.paper",
                          py: 0.5,
                          overflow: "hidden",
                        }}
                      >
                        {administratorSearchError ? (
                          <Typography variant="body2" color="error" sx={{ px: 1.5, py: 1 }}>
                            管理员检索失败，请稍后重试。
                          </Typography>
                        ) : null}
                        {!administratorSearchError && visibleAdministratorOptions.length === 0 && !isSearchingAdministrators ? (
                          <Typography variant="body2" color="text.secondary" sx={{ px: 1.5, py: 1 }}>
                            没有匹配的管理员。
                          </Typography>
                        ) : null}
                        {visibleAdministratorOptions.map((option) => (
                          <Button
                            key={option.actor_id}
                            variant="text"
                            color="inherit"
                            sx={{
                              justifyContent: "flex-start",
                              borderRadius: 0,
                              px: 1.5,
                              py: 1,
                            }}
                            disabled={!isDraftEditable}
                            onClick={() => {
                              addAdministrator(option);
                            }}
                          >
                            {formatUserSearchSummary(option)}
                          </Button>
                        ))}
                      </Stack>
                    ) : null}
                  </Stack>

                  <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap" aria-label="任务管理员已选列表">
                    {selectedAdministratorOptions.map((administrator) => (
                      <Button
                        key={administrator.actor_id}
                        variant="outlined"
                        color="inherit"
                        size="small"
                        disabled={!isDraftEditable}
                        onClick={() => {
                          removeAdministrator(administrator.actor_id);
                        }}
                      >
                        {formatUserSearchSummary(administrator)}
                      </Button>
                    ))}
                  </Stack>

                  <FormControl error={Boolean(validationErrors.feeCategories)} component="fieldset" variant="standard">
                    <FormGroup className="checkbox-grid" aria-label="费用类别">
                      {FEE_CATEGORY_OPTIONS.map((option) => (
                        <FormControlLabel
                          key={option.value}
                          className="checkbox-card checkbox-card-surface"
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
                      <MetadataChip
                        key={category}
                        component="li"
                        className="token-chip"
                        label={formatExpenseType(category)}
                      />
                    ))}
                  </ul>
                </Stack>
              </section>

              <section className="admin-form-card">
                <div className="admin-form-header">
                  <div>
                    <p className="eyebrow">发票信息</p>
                    <h3>发票抬头与税号</h3>
                  </div>
                </div>
                <div className="admin-form-grid">
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

              <section className="admin-form-card admin-form-footer admin-task-detail-save-footer">
                <div>
                  <p className="eyebrow">保存</p>
                  <h3>更新草稿任务配置</h3>
                  <p>保存会覆盖当前草稿任务的基础信息，但不会改变状态。</p>
                </div>
                <Stack
                  className="admin-task-detail-save-actions"
                  direction={{ xs: "column", sm: "row" }}
                  spacing={1.5}
                >
                  <Button component={RouterLink} to="/admin" variant="outlined" color="inherit">
                    返回任务列表
                  </Button>
                  <Button type="submit" variant="contained" disabled={!isDraftEditable || isSubmitting}>
                    {isSubmitting ? "正在保存..." : "保存任务基础配置"}
                  </Button>
                </Stack>
              </section>
            </form>
          </SurfaceCard>

          <SurfaceCard component="article" className="status-card admin-task-detail-panel">
            <div className="admin-form-header">
              <div>
                <p className="eyebrow">状态操作</p>
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
          </SurfaceCard>
        </section>
      ) : null}
    </AdminWorkspaceShell>
  );
}
