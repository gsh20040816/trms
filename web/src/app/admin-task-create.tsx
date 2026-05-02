import { startTransition, useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import Button from "@mui/material/Button";
import Checkbox from "@mui/material/Checkbox";
import Chip from "@mui/material/Chip";
import FormControl from "@mui/material/FormControl";
import FormControlLabel from "@mui/material/FormControlLabel";
import FormGroup from "@mui/material/FormGroup";
import FormHelperText from "@mui/material/FormHelperText";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";

import { ApiErrorNotice } from "../components/ApiErrorNotice";
import { PageHeader } from "../components/dashboard";
import { useAuthSession } from "./auth-store";
import { trmsApi } from "../lib/api/trms";
import type { ExpenseType, TaskCreateInput, UserSearchSummary } from "../lib/api/types";
import { formatUserSearchSummary } from "../lib/ui-text";
import { AdminWorkspaceShell } from "./admin-workspace-shell";

type TaskCreateFormState = {
  competitionName: string;
  competitionLocation: string;
  competitionStartDate: string;
  competitionEndDate: string;
  deadline: string;
  memberIds: string[];
  feeCategories: ExpenseType[];
  administratorIds: string[];
  invoiceTitle: string;
  taxNumber: string;
};

type ValidationErrorState = Partial<Record<keyof TaskCreateFormState | "feeCategories", string>>;

const FEE_CATEGORY_OPTIONS: Array<{ value: ExpenseType; label: string }> = [
  { value: "registration", label: "参赛费" },
  { value: "railway", label: "火车票" },
  { value: "airfare", label: "航空费" },
  { value: "local_transport", label: "市内交通" },
  { value: "hotel", label: "住宿费" },
  { value: "other", label: "其他" },
];

const DEFAULT_FEE_CATEGORIES: ExpenseType[] = FEE_CATEGORY_OPTIONS.map((option) => option.value);

function buildInitialFormState(administratorId: string): TaskCreateFormState {
  return {
    competitionName: "",
    competitionLocation: "",
    competitionStartDate: "",
    competitionEndDate: "",
    deadline: "",
    memberIds: [],
    feeCategories: [...DEFAULT_FEE_CATEGORIES],
    administratorIds: administratorId.trim().length > 0 ? [administratorId] : [],
    invoiceTitle: "",
    taxNumber: "",
  };
}

function normalizeOptionalField(value: string) {
  const normalized = value.trim();
  return normalized.length > 0 ? normalized : undefined;
}

function validateForm(formState: TaskCreateFormState): {
  errors: ValidationErrorState;
  payload: TaskCreateInput | null;
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
  const normalizedAdministrators = formState.administratorIds.map((administratorId) => administratorId.trim());
  const hasAdministrator = normalizedAdministrators.some((administratorId) => administratorId.length > 0);
  if (!hasAdministrator) {
    errors.administratorIds = "至少选择一名管理员。";
  } else if (normalizedAdministrators.some((administratorId) => administratorId.length === 0)) {
    errors.administratorIds = "管理员列表不能包含空标识。";
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
      administrator_id: normalizedAdministrators[0] ?? "",
      administrator_ids: normalizedAdministrators,
      invoice_title: normalizeOptionalField(formState.invoiceTitle),
      tax_number: normalizeOptionalField(formState.taxNumber),
    },
  };
}

export function AdminTaskCreatePage() {
  const session = useAuthSession();
  const navigate = useNavigate();
  const [formState, setFormState] = useState<TaskCreateFormState>(() =>
    buildInitialFormState(session?.actorId ?? ""),
  );
  const [memberInputValue, setMemberInputValue] = useState("");
  const [memberOptions, setMemberOptions] = useState<UserSearchSummary[]>([]);
  const [administratorInputValue, setAdministratorInputValue] = useState("");
  const [administratorOptions, setAdministratorOptions] = useState<UserSearchSummary[]>([]);
  const [isSearchingMembers, setIsSearchingMembers] = useState(false);
  const [isSearchingAdministrators, setIsSearchingAdministrators] = useState(false);
  const [validationErrors, setValidationErrors] = useState<ValidationErrorState>({});
  const [submitError, setSubmitError] = useState<unknown>(null);
  const [memberSearchError, setMemberSearchError] = useState<unknown>(null);
  const [administratorSearchError, setAdministratorSearchError] = useState<unknown>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const memberSearchTimerRef = useRef<number | null>(null);
  const administratorSearchTimerRef = useRef<number | null>(null);

  useEffect(() => (
    () => {
      if (memberSearchTimerRef.current !== null) {
        window.clearTimeout(memberSearchTimerRef.current);
      }
      if (administratorSearchTimerRef.current !== null) {
        window.clearTimeout(administratorSearchTimerRef.current);
      }
    }
  ), []);

  if (!session || session.role !== "admin") {
    return null;
  }

  const selectedMemberOptions = formState.memberIds.map((memberId) => (
    memberOptions.find((option) => option.actor_id === memberId) ?? {
      actor_id: memberId,
      username: memberId,
      display_name: memberId,
      student_id: null,
    }
  ));
  const selectedAdministratorOptions = formState.administratorIds.map((administratorId) => (
    administratorOptions.find((option) => option.actor_id === administratorId) ?? {
      actor_id: administratorId,
      username: administratorId,
      display_name: administratorId,
      student_id: null,
    }
  ));

  function updateField<Key extends keyof TaskCreateFormState>(
    key: Key,
    value: TaskCreateFormState[Key],
  ) {
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

  function toggleFeeCategory(category: ExpenseType) {
    const nextCategories = formState.feeCategories.includes(category)
      ? formState.feeCategories.filter((value) => value !== category)
      : [...formState.feeCategories, category];
    updateField("feeCategories", nextCategories);
  }

  function addMember(member: UserSearchSummary) {
    if (formState.memberIds.includes(member.actor_id)) {
      return;
    }
    updateField("memberIds", [...formState.memberIds, member.actor_id]);
  }

  function removeMember(memberId: string) {
    updateField(
      "memberIds",
      formState.memberIds.filter((currentMemberId) => currentMemberId !== memberId),
    );
  }

  function addAdministrator(administrator: UserSearchSummary) {
    if (formState.administratorIds.includes(administrator.actor_id)) {
      return;
    }
    updateField("administratorIds", [...formState.administratorIds, administrator.actor_id]);
  }

  function removeAdministrator(administratorId: string) {
    updateField(
      "administratorIds",
      formState.administratorIds.filter(
        (currentAdministratorId) => currentAdministratorId !== administratorId,
      ),
    );
  }

  function handleMemberKeywordChange(value: string) {
    setMemberInputValue(value);
    const keyword = value.trim();
    if (memberSearchTimerRef.current !== null) {
      window.clearTimeout(memberSearchTimerRef.current);
      memberSearchTimerRef.current = null;
    }

    if (keyword.length === 0) {
      setMemberOptions([]);
      setMemberSearchError(null);
      setIsSearchingMembers(false);
      return;
    }
    setIsSearchingMembers(true);
    setMemberSearchError(null);
    memberSearchTimerRef.current = window.setTimeout(() => {
      void trmsApi.searchTaskMemberCandidates(keyword, 10)
        .then((response) => {
          setMemberOptions(response.items);
        })
        .catch((error) => {
          setMemberOptions([]);
          setMemberSearchError(error);
        })
        .finally(() => {
          setIsSearchingMembers(false);
          memberSearchTimerRef.current = null;
        });
    }, 250);
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
          setAdministratorOptions(response.items);
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

  const visibleMemberOptions = memberOptions.filter(
    (option) => !formState.memberIds.includes(option.actor_id),
  );
  const visibleAdministratorOptions = administratorOptions.filter(
    (option) => !formState.administratorIds.includes(option.actor_id),
  );

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitError(null);

    const { errors, payload } = validateForm(formState);
    setValidationErrors(errors);
    if (!payload) {
      return;
    }

    setIsSubmitting(true);
    try {
      await trmsApi.createTask(payload);
      startTransition(() => {
        void navigate("/admin", { replace: true });
      });
    } catch (error) {
      setSubmitError(error);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <AdminWorkspaceShell
      activeModule="create"
      header={(
        <PageHeader
          eyebrow="任务管理"
          title="创建报销任务"
          description="填写比赛信息、成员名单、费用类别和报销基础信息后，即可创建新的报销任务。"
          actions={(
            <div className="page-actions">
              <Link className="button button-secondary" to="/admin">
                返回任务列表
              </Link>
            </div>
          )}
        />
      )}
    >

      {submitError ? <ApiErrorNotice error={submitError} /> : null}

      <form
        className="page-stack"
        onSubmit={(event) => {
          void handleSubmit(event);
        }}
        noValidate
      >
        <section className="status-card admin-form-card">
          <div className="admin-form-header">
            <div>
              <p className="eyebrow">比赛信息</p>
              <h2>比赛与时间信息</h2>
            </div>
            <span className="status-chip">创建后默认状态为草稿</span>
          </div>
          <div className="admin-form-grid">
            <TextField
              label="比赛名称"
              name="competition-name"
              value={formState.competitionName}
              onChange={(event) => {
                updateField("competitionName", event.target.value);
              }}
              error={Boolean(validationErrors.competitionName)}
              helperText={validationErrors.competitionName}
              fullWidth
            />
            <TextField
              label="比赛地点"
              name="competition-location"
              value={formState.competitionLocation}
              onChange={(event) => {
                updateField("competitionLocation", event.target.value);
              }}
              error={Boolean(validationErrors.competitionLocation)}
              helperText={validationErrors.competitionLocation}
              fullWidth
            />
            <TextField
              label="比赛开始日期"
              type="date"
              name="competition-start-date"
              value={formState.competitionStartDate}
              onChange={(event) => {
                updateField("competitionStartDate", event.target.value);
              }}
              error={Boolean(validationErrors.competitionStartDate)}
              helperText={validationErrors.competitionStartDate}
              fullWidth
              slotProps={{ inputLabel: { shrink: true } }}
            />
            <TextField
              label="比赛结束日期"
              type="date"
              name="competition-end-date"
              value={formState.competitionEndDate}
              onChange={(event) => {
                updateField("competitionEndDate", event.target.value);
              }}
              error={Boolean(validationErrors.competitionEndDate)}
              helperText={validationErrors.competitionEndDate}
              fullWidth
              slotProps={{ inputLabel: { shrink: true } }}
            />
            <TextField
              label="提交截止时间"
              type="datetime-local"
              name="deadline"
              value={formState.deadline}
              onChange={(event) => {
                updateField("deadline", event.target.value);
              }}
              error={Boolean(validationErrors.deadline)}
              helperText={validationErrors.deadline}
              fullWidth
              slotProps={{ inputLabel: { shrink: true } }}
            />
          </div>
        </section>

        <section className="status-card admin-form-card">
          <div className="admin-form-header">
            <div>
              <p className="eyebrow">成员名单</p>
              <h2>成员名单与费用类别</h2>
            </div>
          </div>

          <Stack spacing={3}>
            <Stack spacing={0.75}>
              <TextField
                label="成员名单搜索"
                value={memberInputValue}
                onChange={(event) => {
                  handleMemberKeywordChange(event.target.value);
                }}
                placeholder="输入成员姓名、用户名或学号检索"
                helperText={isSearchingMembers ? "正在检索成员..." : "输入后会实时向后端检索候选成员。"}
                fullWidth
              />

              {memberInputValue.trim().length > 0 ? (
                <Stack
                  spacing={0.5}
                  aria-label="成员候选列表"
                  sx={{
                    borderRadius: 3,
                    border: "1px solid",
                    borderColor: "divider",
                    bgcolor: "background.paper",
                    py: 0.5,
                    overflow: "hidden",
                  }}
                >
                  {memberSearchError ? (
                    <Typography variant="body2" color="error" sx={{ px: 1.5, py: 1 }}>
                      成员检索失败，请稍后重试。
                    </Typography>
                  ) : null}
                  {!memberSearchError && visibleMemberOptions.length === 0 && !isSearchingMembers ? (
                    <Typography variant="body2" color="text.secondary" sx={{ px: 1.5, py: 1 }}>
                      没有匹配的成员。
                    </Typography>
                  ) : null}
                  {visibleMemberOptions.map((option) => (
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
                      onClick={() => {
                        addMember(option);
                      }}
                    >
                      {formatUserSearchSummary(option)}
                    </Button>
                  ))}
                </Stack>
              ) : null}
            </Stack>

            {validationErrors.memberIds ? (
              <FormHelperText error>{validationErrors.memberIds}</FormHelperText>
            ) : null}

            <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap" aria-label="已选成员列表">
              {selectedMemberOptions.map((member) => (
                <Chip
                  key={member.actor_id}
                  label={formatUserSearchSummary(member)}
                  onDelete={() => {
                    removeMember(member.actor_id);
                  }}
                />
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
                    />
                  )}
                  label={option.label}
                />
              ))}
              </FormGroup>
              <FormHelperText>
                {validationErrors.feeCategories ?? "请选择本次任务允许成员上传和分摊的费用类别。"}
              </FormHelperText>
            </FormControl>
          </Stack>
        </section>

        <section className="status-card admin-form-card">
          <div className="admin-form-header">
            <div>
              <p className="eyebrow">管理员</p>
              <h2>管理员信息</h2>
            </div>
          </div>
          <Stack spacing={3}>
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
                      : "默认已包含当前管理员；可继续追加其他管理员。"
                  )
                }
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

            <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap" aria-label="已选管理员列表">
              {selectedAdministratorOptions.map((administrator) => (
                <Chip
                  key={administrator.actor_id}
                  label={formatUserSearchSummary(administrator)}
                  onDelete={() => {
                    removeAdministrator(administrator.actor_id);
                  }}
                />
              ))}
            </Stack>
          </Stack>
        </section>

        <section className="status-card admin-form-card">
          <div className="admin-form-header">
            <div>
              <p className="eyebrow">发票信息</p>
              <h2>发票抬头与税号</h2>
            </div>
          </div>
          <div className="admin-form-grid">
            <TextField
              label="发票抬头"
              name="invoice-title"
              value={formState.invoiceTitle}
              placeholder="留空时尝试继承全局配置"
              onChange={(event) => {
                updateField("invoiceTitle", event.target.value);
              }}
              helperText="留空时尝试继承全局配置。"
              fullWidth
            />
            <TextField
              label="税号"
              name="tax-number"
              value={formState.taxNumber}
              placeholder="留空时尝试继承全局配置"
              onChange={(event) => {
                updateField("taxNumber", event.target.value);
              }}
              helperText="留空时尝试继承全局配置。"
              fullWidth
            />
          </div>
        </section>

        <section className="status-card admin-form-card admin-form-footer">
          <div>
            <p className="eyebrow">提交</p>
            <h2>提交创建请求</h2>
            <p>如果信息不完整或不符合要求，页面会直接提示需要补充的内容。</p>
          </div>
          <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5}>
            <Button component={Link} to="/admin" variant="outlined" color="inherit">
              取消并返回
            </Button>
            <Button type="submit" variant="contained" disabled={isSubmitting}>
              {isSubmitting ? "正在创建..." : "创建草稿任务"}
            </Button>
          </Stack>
        </section>
      </form>
    </AdminWorkspaceShell>
  );
}
