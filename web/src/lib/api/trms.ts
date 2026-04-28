import { apiClient } from "./client";
import type {
  ApiItemResponse,
  ApiListResponse,
  ConfirmationRecord,
  ConfirmationSubmit,
  ExpenseDetailList,
  ExpenseSplitRecord,
  ExpenseSplitReplace,
  FinanceDraftExport,
  InvoiceRecord,
  ManualInvoiceEntry,
  ManualInvoiceEntryResponse,
  MaterialBatchUploadResponse,
  MaterialRecord,
  MergedPdfExportPlan,
  OverdueConfirmationList,
  RecognitionTaskList,
  ReimbursementTask,
  TaskCreateInput,
  TaskExportBoundary,
  TaskExportJobRecord,
  TaskExportJobRequest,
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

export const trmsApi = {
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
      `/tasks/${encodeSegment(taskId)}/review-summary${buildQuery({ actor_id: actorId })}`,
    );
  },

  listTaskExpenseDetails(taskId: string, actorId: string) {
    return apiClient.request<ExpenseDetailList>(
      `/tasks/${encodeSegment(taskId)}/expense-details${buildQuery({ actor_id: actorId })}`,
    );
  },

  listTaskOverdueConfirmations(taskId: string, actorId: string) {
    return apiClient.request<OverdueConfirmationList>(
      `/tasks/${encodeSegment(taskId)}/overdue-confirmations${buildQuery({ actor_id: actorId })}`,
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

  submitTaskMaterials(taskId: string, formData: FormData) {
    return apiClient.request<MaterialBatchUploadResponse>(
      `/tasks/${encodeSegment(taskId)}/materials`,
      {
        method: "POST",
        body: formData,
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
        body: payload,
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
        body: payload,
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
      body: payload,
    });
  },

  getTaskExportCapabilities(taskId: string, actorId: string) {
    return apiClient.request<TaskExportBoundary>(
      `/tasks/${encodeSegment(taskId)}/exports/capabilities${buildQuery({ actor_id: actorId })}`,
    );
  },

  listTaskExportJobs(taskId: string, actorId: string) {
    return apiClient.request<ApiListResponse<TaskExportJobRecord>>(
      `/tasks/${encodeSegment(taskId)}/exports${buildQuery({ actor_id: actorId })}`,
    );
  },

  createTaskExportJob(taskId: string, payload: TaskExportJobRequest) {
    return apiClient.request<TaskExportJobRecord>(`/tasks/${encodeSegment(taskId)}/exports`, {
      method: "POST",
      body: payload,
    });
  },

  downloadReimbursementSummaryCsv(taskId: string, actorId: string) {
    return apiClient.request<string>(
      `/tasks/${encodeSegment(taskId)}/exports/reimbursement-summary${buildQuery({
        actor_id: actorId,
        format: "csv",
      })}`,
    );
  },

  downloadMemberDetailsCsv(taskId: string, actorId: string) {
    return apiClient.request<string>(
      `/tasks/${encodeSegment(taskId)}/exports/member-details${buildQuery({
        actor_id: actorId,
        format: "csv",
      })}`,
    );
  },

  downloadInvoiceDetailsCsv(taskId: string, actorId: string) {
    return apiClient.request<string>(
      `/tasks/${encodeSegment(taskId)}/exports/invoice-details${buildQuery({
        actor_id: actorId,
        format: "csv",
      })}`,
    );
  },

  downloadMissingMaterialsCsv(taskId: string, actorId: string) {
    return apiClient.request<string>(
      `/tasks/${encodeSegment(taskId)}/exports/missing-materials${buildQuery({
        actor_id: actorId,
        format: "csv",
      })}`,
    );
  },

  exportFinanceDraft(taskId: string, actorId: string) {
    return apiClient.request<FinanceDraftExport>(
      `/tasks/${encodeSegment(taskId)}/exports/finance-draft${buildQuery({
        actor_id: actorId,
        format: "json",
      })}`,
    );
  },

  exportMergedPdfPlan(taskId: string, actorId: string) {
    return apiClient.request<MergedPdfExportPlan>(
      `/tasks/${encodeSegment(taskId)}/exports/merged-pdf${buildQuery({
        actor_id: actorId,
        format: "json",
      })}`,
    );
  },
};
