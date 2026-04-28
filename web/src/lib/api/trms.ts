import { apiClient, type ApiDownloadedFile, getConfiguredApiAccessToken } from "./client";
import type {
  ApiItemResponse,
  ApiListResponse,
  AuthenticatedUser,
  AuthSessionResponse,
  ConfirmationRecord,
  ConfirmationSubmit,
  ExpenseDetailList,
  ExpenseSplitRecord,
  ExpenseSplitReplace,
  FinanceDraftExport,
  InvoiceRecord,
  LoginPayload,
  ManualInvoiceEntry,
  ManualInvoiceEntryResponse,
  MaterialBatchUploadResponse,
  MaterialReminderCreate,
  MaterialReminderRecord,
  MaterialRecord,
  MaterialTypeUpdatePayload,
  MergedPdfExportPlan,
  VisibleMissingMaterialList,
  OverdueConfirmationList,
  RecognitionTaskList,
  RegisterPayload,
  ReimbursementTask,
  TaskCreateInput,
  TaskExportBoundary,
  TaskExportJobRecord,
  TaskExportJobRequest,
  TaskSharedInvoiceReport,
  TaskMemberStatusReport,
  TaskMembersUpdate,
  TaskReviewSummary,
  TaskStatusUpdate,
  ValidationResult,
} from "./types";

function buildQuery(params: Record<string, string | undefined>) {
  const searchParams = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value) {
      searchParams.set(key, value);
    }
  }
  const query = searchParams.toString();
  return query.length > 0 ? `?${query}` : "";
}

function encodeSegment(value: string) {
  return encodeURIComponent(value);
}

function shouldUseBearerIdentity() {
  return getConfiguredApiAccessToken() !== null;
}

function buildActorScopedQuery(actorId: string) {
  return shouldUseBearerIdentity() ? "" : buildQuery({ actor_id: actorId });
}

function buildActorScopedExportQuery(
  actorId: string,
  format: "csv" | "json" | "pdf",
) {
  return shouldUseBearerIdentity()
    ? buildQuery({ format })
    : buildQuery({ actor_id: actorId, format });
}

function buildActorScopedBody<T extends Record<string, unknown>>(
  payload: T,
  actorFieldNames: Array<keyof T>,
) {
  if (!shouldUseBearerIdentity()) {
    return payload;
  }

  const nextPayload = { ...payload };
  for (const fieldName of actorFieldNames) {
    delete nextPayload[fieldName];
  }
  return nextPayload;
}

function buildActorScopedFormData(
  formData: FormData,
  actorFieldNames: string[],
) {
  if (!shouldUseBearerIdentity()) {
    return formData;
  }

  const nextFormData = new FormData();
  for (const [key, value] of formData.entries()) {
    if (actorFieldNames.includes(key)) {
      continue;
    }
    nextFormData.append(key, value);
  }
  return nextFormData;
}

export const trmsApi = {
  register(payload: RegisterPayload) {
    return apiClient.request<AuthSessionResponse>("/auth/register", {
      method: "POST",
      body: payload,
    });
  },

  login(payload: LoginPayload) {
    return apiClient.request<AuthSessionResponse>("/auth/login", {
      method: "POST",
      body: payload,
    });
  },

  getCurrentUser(accessToken: string) {
    return apiClient.request<AuthenticatedUser>("/auth/me", {
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    });
  },

  logout(accessToken: string) {
    return apiClient.request<void>("/auth/logout", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    });
  },

  createTask(payload: TaskCreateInput) {
    return apiClient.request<ReimbursementTask>("/tasks", {
      method: "POST",
      body: payload,
    });
  },

  listTasks() {
    return apiClient.request<ReimbursementTask[]>("/tasks");
  },

  getTask(taskId: string) {
    return apiClient.request<ReimbursementTask>(`/tasks/${encodeSegment(taskId)}`);
  },

  getTaskReviewSummary(taskId: string, actorId: string) {
    return apiClient.request<TaskReviewSummary>(
      `/tasks/${encodeSegment(taskId)}/review-summary${buildActorScopedQuery(actorId)}`,
    );
  },

  listTaskExpenseDetails(taskId: string, actorId: string) {
    return apiClient.request<ExpenseDetailList>(
      `/tasks/${encodeSegment(taskId)}/expense-details${buildActorScopedQuery(actorId)}`,
    );
  },

  getTaskMemberStatus(taskId: string, actorId: string) {
    return apiClient.request<TaskMemberStatusReport>(
      `/tasks/${encodeSegment(taskId)}/member-status${buildActorScopedQuery(actorId)}`,
    );
  },

  getTaskSharedInvoices(taskId: string, actorId: string) {
    return apiClient.request<TaskSharedInvoiceReport>(
      `/tasks/${encodeSegment(taskId)}/shared-invoices${buildActorScopedQuery(actorId)}`,
    );
  },

  getTaskMissingMaterials(taskId: string, actorId: string) {
    return apiClient.request<VisibleMissingMaterialList>(
      `/tasks/${encodeSegment(taskId)}/missing-materials${buildActorScopedQuery(actorId)}`,
    );
  },

  listTaskOverdueConfirmations(taskId: string, actorId: string) {
    return apiClient.request<OverdueConfirmationList>(
      `/tasks/${encodeSegment(taskId)}/overdue-confirmations${buildActorScopedQuery(actorId)}`,
    );
  },

  listTaskMaterialReminders(taskId: string, actorId: string) {
    return apiClient.request<ApiListResponse<MaterialReminderRecord>>(
      `/tasks/${encodeSegment(taskId)}/material-reminders${buildActorScopedQuery(actorId)}`,
    );
  },

  createTaskMaterialReminder(taskId: string, payload: MaterialReminderCreate) {
    return apiClient.request<MaterialReminderRecord>(
      `/tasks/${encodeSegment(taskId)}/material-reminders`,
      {
        method: "POST",
        body: payload,
      },
    );
  },

  updateTaskMembers(taskId: string, payload: TaskMembersUpdate) {
    return apiClient.request<ReimbursementTask>(`/tasks/${encodeSegment(taskId)}/members`, {
      method: "PUT",
      body: payload,
    });
  },

  updateTaskStatus(taskId: string, payload: TaskStatusUpdate) {
    return apiClient.request<ReimbursementTask>(`/tasks/${encodeSegment(taskId)}/status`, {
      method: "PATCH",
      body: payload,
    });
  },

  listTaskMembers(taskId: string) {
    return apiClient.request<ApiListResponse<string>>(`/tasks/${encodeSegment(taskId)}/members`);
  },

  listTaskMaterials(taskId: string) {
    return apiClient.request<ApiListResponse<MaterialRecord>>(
      `/tasks/${encodeSegment(taskId)}/materials`,
    );
  },

  listMaterialRecognitionTasks(materialId: string) {
    return apiClient.request<RecognitionTaskList>(
      `/materials/${encodeSegment(materialId)}/recognition-tasks`,
    );
  },

  createRecognitionTask(materialId: string) {
    return apiClient.request<ApiItemResponse<RecognitionTaskList["items"][number]>>(
      `/materials/${encodeSegment(materialId)}/recognition-tasks`,
      {
        method: "POST",
      },
    );
  },

  executeRecognitionTask(recognitionTaskId: string) {
    return apiClient.request<ApiItemResponse<RecognitionTaskList["items"][number]>>(
      `/recognition-tasks/${encodeSegment(recognitionTaskId)}/execute`,
      {
        method: "POST",
      },
    );
  },

  submitTaskMaterials(taskId: string, formData: FormData) {
    return apiClient.request<MaterialBatchUploadResponse>(
      `/tasks/${encodeSegment(taskId)}/materials`,
      {
        method: "POST",
        body: buildActorScopedFormData(formData, ["submitter_id"]),
      },
    );
  },

  claimPendingMaterial(materialId: string, formData: FormData) {
    return apiClient.request<ApiItemResponse<MaterialRecord>>(
      `/materials/${encodeSegment(materialId)}/claim`,
      {
        method: "POST",
        body: formData,
      },
    );
  },

  updateMaterialType(materialId: string, payload: MaterialTypeUpdatePayload) {
    return apiClient.request<ApiItemResponse<MaterialRecord>>(
      `/materials/${encodeSegment(materialId)}/material-type`,
      {
        method: "PATCH",
        body: buildActorScopedBody(payload, ["actor_id"]),
      },
    );
  },

  listTaskInvoices(taskId: string) {
    return apiClient.request<ApiListResponse<InvoiceRecord>>(
      `/tasks/${encodeSegment(taskId)}/invoices`,
    );
  },

  createOrUpdateInvoice(materialId: string, payload: ManualInvoiceEntry) {
    return apiClient.request<ManualInvoiceEntryResponse>(
      `/materials/${encodeSegment(materialId)}/invoice`,
      {
        method: "POST",
        body: buildActorScopedBody(payload, ["actor_id"]),
      },
    );
  },

  listInvoiceValidations(invoiceId: string) {
    return apiClient.request<ApiListResponse<ValidationResult>>(
      `/invoices/${encodeSegment(invoiceId)}/validations`,
    );
  },

  listInvoiceSupportingMaterials(invoiceId: string) {
    return apiClient.request<ApiListResponse<MaterialRecord>>(
      `/invoices/${encodeSegment(invoiceId)}/supporting-materials`,
    );
  },

  listInvoiceSplits(invoiceId: string) {
    return apiClient.request<ApiListResponse<ExpenseSplitRecord>>(
      `/invoices/${encodeSegment(invoiceId)}/splits`,
    );
  },

  replaceInvoiceSplits(invoiceId: string, payload: ExpenseSplitReplace) {
    return apiClient.request<ApiListResponse<ExpenseSplitRecord>>(
      `/invoices/${encodeSegment(invoiceId)}/splits`,
      {
        method: "PUT",
        body: buildActorScopedBody(payload, ["actor_id"]),
      },
    );
  },

  listInvoiceConfirmations(invoiceId: string) {
    return apiClient.request<ApiListResponse<ConfirmationRecord>>(
      `/invoices/${encodeSegment(invoiceId)}/confirmations`,
    );
  },

  submitSplitConfirmation(splitId: string, payload: ConfirmationSubmit) {
    return apiClient.request<ConfirmationRecord>(`/splits/${encodeSegment(splitId)}/confirmation`, {
      method: "PUT",
      body: buildActorScopedBody(payload, ["actor_id", "member_id"]),
    });
  },

  getTaskExportCapabilities(taskId: string, actorId: string) {
    return apiClient.request<TaskExportBoundary>(
      `/tasks/${encodeSegment(taskId)}/exports/capabilities${buildActorScopedQuery(actorId)}`,
    );
  },

  listTaskExportJobs(taskId: string, actorId: string) {
    return apiClient.request<TaskExportJobRecord[]>(
      `/tasks/${encodeSegment(taskId)}/exports${buildActorScopedQuery(actorId)}`,
    );
  },

  createTaskExportJob(taskId: string, payload: TaskExportJobRequest) {
    return apiClient.request<TaskExportJobRecord>(`/tasks/${encodeSegment(taskId)}/exports`, {
      method: "POST",
      body: buildActorScopedBody(payload, ["actor_id"]),
    });
  },

  downloadReimbursementSummaryCsv(taskId: string, actorId: string) {
    return apiClient.request<string>(
      `/tasks/${encodeSegment(taskId)}/exports/reimbursement-summary${buildActorScopedExportQuery(actorId, "csv")}`,
    );
  },

  downloadMemberDetailsCsv(taskId: string, actorId: string) {
    return apiClient.request<string>(
      `/tasks/${encodeSegment(taskId)}/exports/member-details${buildActorScopedExportQuery(actorId, "csv")}`,
    );
  },

  downloadInvoiceDetailsCsv(taskId: string, actorId: string) {
    return apiClient.request<string>(
      `/tasks/${encodeSegment(taskId)}/exports/invoice-details${buildActorScopedExportQuery(actorId, "csv")}`,
    );
  },

  downloadMissingMaterialsCsv(taskId: string, actorId: string) {
    return apiClient.request<string>(
      `/tasks/${encodeSegment(taskId)}/exports/missing-materials${buildActorScopedExportQuery(actorId, "csv")}`,
    );
  },

  exportFinanceDraft(taskId: string, actorId: string) {
    return apiClient.request<FinanceDraftExport>(
      `/tasks/${encodeSegment(taskId)}/exports/finance-draft${buildActorScopedExportQuery(actorId, "json")}`,
    );
  },

  exportMergedPdfPlan(taskId: string, actorId: string) {
    return apiClient.request<MergedPdfExportPlan>(
      `/tasks/${encodeSegment(taskId)}/exports/merged-pdf${buildActorScopedExportQuery(actorId, "pdf")}`,
    );
  },

  downloadTaskExportArtifact(exportJobId: string, actorId: string) {
    return apiClient.download(
      `/tasks/exports/${encodeSegment(exportJobId)}/artifact${buildActorScopedQuery(actorId)}`,
    ) as Promise<ApiDownloadedFile>;
  },
};
