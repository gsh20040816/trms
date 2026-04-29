import { startTransition, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { ApiErrorNotice } from "../components/ApiErrorNotice";
import { PageHeader } from "../components/dashboard";
import { useAuthSession } from "./auth-store";
import { trmsApi } from "../lib/api/trms";
import type { ExpenseType, TaskCreateInput } from "../lib/api/types";
import { AdminWorkspaceShell } from "./admin-workspace-shell";

type TaskCreateFormState = {
  competitionName: string;
  competitionLocation: string;
  competitionStartDate: string;
  competitionEndDate: string;
  deadline: string;
  memberIds: string[];
  feeCategories: ExpenseType[];
  administratorId: string;
  projectInfo: string;
  reimburserInfo: string;
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

function buildInitialFormState(administratorId: string): TaskCreateFormState {
  return {
    competitionName: "",
    competitionLocation: "",
    competitionStartDate: "",
    competitionEndDate: "",
    deadline: "",
    memberIds: [""],
    feeCategories: [],
    administratorId,
    projectInfo: "",
    reimburserInfo: "",
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
  if (formState.administratorId.trim().length === 0) {
    errors.administratorId = "管理员标识不能为空。";
  }
  if (formState.projectInfo.trim().length === 0) {
    errors.projectInfo = "项目/课题信息不能为空。";
  }
  if (formState.reimburserInfo.trim().length === 0) {
    errors.reimburserInfo = "报销人信息不能为空。";
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
      administrator_id: formState.administratorId.trim(),
      project_info: formState.projectInfo.trim(),
      reimburser_info: formState.reimburserInfo.trim(),
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
  const [validationErrors, setValidationErrors] = useState<ValidationErrorState>({});
  const [submitError, setSubmitError] = useState<unknown>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!session || session.role !== "admin") {
    return null;
  }

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

  function updateMember(index: number, value: string) {
    const nextMembers = formState.memberIds.map((memberId, currentIndex) =>
      currentIndex === index ? value : memberId,
    );
    updateField("memberIds", nextMembers);
  }

  function addMemberRow() {
    updateField("memberIds", [...formState.memberIds, ""]);
  }

  function removeMemberRow(index: number) {
    const nextMembers =
      formState.memberIds.length === 1
        ? [""]
        : formState.memberIds.filter((_, currentIndex) => currentIndex !== index);
    updateField("memberIds", nextMembers);
  }

  function toggleFeeCategory(category: ExpenseType) {
    const nextCategories = formState.feeCategories.includes(category)
      ? formState.feeCategories.filter((value) => value !== category)
      : [...formState.feeCategories, category];
    updateField("feeCategories", nextCategories);
  }

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
      activeModule="tasks"
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
              <p className="eyebrow">Competition</p>
              <h2>比赛与时间信息</h2>
            </div>
            <span className="status-chip">创建后默认状态为草稿</span>
          </div>
          <div className="admin-form-grid">
            <label className="field-stack">
              <span>比赛名称</span>
              <input
                name="competition-name"
                value={formState.competitionName}
                onChange={(event) => {
                  updateField("competitionName", event.target.value);
                }}
              />
              {validationErrors.competitionName ? (
                <span className="field-error">{validationErrors.competitionName}</span>
              ) : null}
            </label>
            <label className="field-stack">
              <span>比赛地点</span>
              <input
                name="competition-location"
                value={formState.competitionLocation}
                onChange={(event) => {
                  updateField("competitionLocation", event.target.value);
                }}
              />
              {validationErrors.competitionLocation ? (
                <span className="field-error">{validationErrors.competitionLocation}</span>
              ) : null}
            </label>
            <label className="field-stack">
              <span>比赛开始日期</span>
              <input
                type="date"
                name="competition-start-date"
                value={formState.competitionStartDate}
                onChange={(event) => {
                  updateField("competitionStartDate", event.target.value);
                }}
              />
              {validationErrors.competitionStartDate ? (
                <span className="field-error">{validationErrors.competitionStartDate}</span>
              ) : null}
            </label>
            <label className="field-stack">
              <span>比赛结束日期</span>
              <input
                type="date"
                name="competition-end-date"
                value={formState.competitionEndDate}
                onChange={(event) => {
                  updateField("competitionEndDate", event.target.value);
                }}
              />
              {validationErrors.competitionEndDate ? (
                <span className="field-error">{validationErrors.competitionEndDate}</span>
              ) : null}
            </label>
            <label className="field-stack">
              <span>提交截止时间</span>
              <input
                type="datetime-local"
                name="deadline"
                value={formState.deadline}
                onChange={(event) => {
                  updateField("deadline", event.target.value);
                }}
              />
              {validationErrors.deadline ? (
                <span className="field-error">{validationErrors.deadline}</span>
              ) : null}
            </label>
          </div>
        </section>

        <section className="status-card admin-form-card">
          <div className="admin-form-header">
            <div>
              <p className="eyebrow">Members</p>
              <h2>成员名单与费用类别</h2>
            </div>
            <button className="route-link route-link-secondary" type="button" onClick={addMemberRow}>
              新增成员项
            </button>
          </div>

          <div className="member-list" aria-label="成员名单">
            {formState.memberIds.map((memberId, index) => (
              <div key={`member-${index}`} className="member-row">
                <label className="field-stack member-field">
                  <span>成员 {index + 1}（姓名或学号）</span>
                  <input
                    aria-label={`成员 ${index + 1}`}
                    value={memberId}
                    placeholder="输入成员姓名或学号"
                    onChange={(event) => {
                      updateMember(index, event.target.value);
                    }}
                  />
                </label>
                <button
                  className="route-link route-link-secondary member-remove-button"
                  type="button"
                  onClick={() => {
                    removeMemberRow(index);
                  }}
                >
                  移除
                </button>
              </div>
            ))}
          </div>
          {validationErrors.memberIds ? (
            <p className="field-error field-error-block">{validationErrors.memberIds}</p>
          ) : (
            <p className="field-hint">当前阶段请填写成员姓名或学号字符串，系统会把它作为该任务内的成员标识；不要填写内部数据库 ID。</p>
          )}

          <fieldset className="checkbox-group">
            <legend>费用类别</legend>
            <div className="checkbox-grid">
              {FEE_CATEGORY_OPTIONS.map((option) => (
                <label key={option.value} className="checkbox-card">
                  <input
                    type="checkbox"
                    checked={formState.feeCategories.includes(option.value)}
                    onChange={() => {
                      toggleFeeCategory(option.value);
                    }}
                  />
                  <span>{option.label}</span>
                </label>
              ))}
            </div>
          </fieldset>
          {validationErrors.feeCategories ? (
            <p className="field-error field-error-block">{validationErrors.feeCategories}</p>
          ) : null}
        </section>

        <section className="status-card admin-form-card">
          <div className="admin-form-header">
            <div>
              <p className="eyebrow">Reimbursement</p>
              <h2>管理员与报销信息</h2>
            </div>
          </div>
          <div className="admin-form-grid">
            <label className="field-stack">
              <span>管理员标识</span>
              <input
                name="administrator-id"
                value={formState.administratorId}
                onChange={(event) => {
                  updateField("administratorId", event.target.value);
                }}
              />
              {validationErrors.administratorId ? (
                <span className="field-error">{validationErrors.administratorId}</span>
              ) : null}
            </label>
            <label className="field-stack">
              <span>项目/课题信息</span>
              <textarea
                name="project-info"
                rows={3}
                value={formState.projectInfo}
                onChange={(event) => {
                  updateField("projectInfo", event.target.value);
                }}
              />
              {validationErrors.projectInfo ? (
                <span className="field-error">{validationErrors.projectInfo}</span>
              ) : null}
            </label>
            <label className="field-stack">
              <span>报销人信息</span>
              <textarea
                name="reimburser-info"
                rows={3}
                value={formState.reimburserInfo}
                onChange={(event) => {
                  updateField("reimburserInfo", event.target.value);
                }}
              />
              {validationErrors.reimburserInfo ? (
                <span className="field-error">{validationErrors.reimburserInfo}</span>
              ) : null}
            </label>
          </div>
        </section>

        <section className="status-card admin-form-card">
          <div className="admin-form-header">
            <div>
              <p className="eyebrow">Invoice Config</p>
              <h2>发票抬头与税号</h2>
            </div>
          </div>
          <div className="admin-form-grid">
            <label className="field-stack">
              <span>发票抬头</span>
              <input
                name="invoice-title"
                value={formState.invoiceTitle}
                placeholder="留空时尝试继承全局配置"
                onChange={(event) => {
                  updateField("invoiceTitle", event.target.value);
                }}
              />
            </label>
            <label className="field-stack">
              <span>税号</span>
              <input
                name="tax-number"
                value={formState.taxNumber}
                placeholder="留空时尝试继承全局配置"
                onChange={(event) => {
                  updateField("taxNumber", event.target.value);
                }}
              />
            </label>
          </div>
          <p className="field-hint">
            这两个字段可以留空；如果系统已配置默认值，会自动补入。
          </p>
        </section>

        <section className="status-card admin-form-card admin-form-footer">
          <div>
            <p className="eyebrow">提交</p>
            <h2>提交创建请求</h2>
            <p>如果信息不完整或不符合要求，页面会直接提示需要补充的内容。</p>
          </div>
          <div className="inline-actions">
            <Link className="route-link route-link-secondary" to="/admin">
              取消并返回
            </Link>
            <button className="route-link" type="submit" disabled={isSubmitting}>
              {isSubmitting ? "正在创建..." : "创建草稿任务"}
            </button>
          </div>
        </section>
      </form>
    </AdminWorkspaceShell>
  );
}
