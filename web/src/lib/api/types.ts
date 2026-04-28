export type ApiDate = string;
export type ApiDateTime = string;

export type ApiListResponse<T> = {
  items: T[];
};

export type ApiItemResponse<T> = {
  item: T;
};

export type TaskStatus =
  | "draft"
  | "open"
  | "closed"
  | "reviewing"
  | "ready_to_export"
  | "completed";

export type SubmissionChannel = "web" | "cli" | "telegram" | "email";

export type MaterialType =
  | "invoice"
  | "payment_record"
  | "competition_notice"
  | "itinerary"
  | "order_screenshot"
  | "other_attachment";

export type MaterialStatus = "assigned" | "pending_assignment";

export type ExpenseType =
  | "registration"
  | "railway"
  | "airfare"
  | "local_transport"
  | "hotel"
  | "other";

export type ValidationSeverity = "blocker" | "warning" | "info";

export type ValidationStatus = "passed" | "failed" | "pending" | "not_applicable";

export type ConfirmationStatus = "pending" | "confirmed" | "disputed";

export type ExportArtifactKind =
  | "reimbursement_summary"
  | "member_details"
  | "invoice_details"
  | "missing_materials"
  | "finance_draft"
  | "merged_pdf";

export type ExportArtifactFormat = "xlsx" | "csv" | "json" | "pdf";

export type TaskExportJobStatus = "pending" | "running" | "succeeded" | "failed";
export type RecognitionTaskStatus = "pending" | "succeeded" | "failed" | "needs_confirmation";
export type RecognitionFieldSource = "ocr" | "pdf_text" | "ai" | "manual";
export type RecognitionFieldStatus = "recognized" | "needs_confirmation";
export type RecognitionFailureStage = "ocr" | "pdf" | "ai";
export type UserRole = "member" | "admin" | "system_admin";

export type AuthenticatedUser = {
  id: string;
  username: string;
  role: UserRole;
  roles?: UserRole[];
  actor_id: string;
  display_name: string;
  member_code: string | null;
  created_at: ApiDateTime;
  updated_at: ApiDateTime;
};

export type AuthSessionResponse = {
  access_token: string;
  token_type: "bearer";
  user: AuthenticatedUser;
};

export type RegisterPayload = {
  username: string;
  password: string;
  role: UserRole;
  display_name?: string | null;
  actor_id?: string | null;
  member_code?: string | null;
};

export type LoginPayload = {
  username: string;
  password: string;
};

export type ReimbursementTask = {
  id: string;
  status: TaskStatus;
  competition_name: string;
  competition_location: string;
  competition_start_date: ApiDate;
  competition_end_date: ApiDate;
  deadline: ApiDateTime;
  member_ids: string[];
  fee_categories: string[];
  administrator_id: string;
  project_info: string;
  reimburser_info: string;
  invoice_title: string;
  tax_number: string;
  created_at: ApiDateTime;
  updated_at: ApiDateTime;
};

export type TaskCreateInput = {
  competition_name: string;
  competition_location: string;
  competition_start_date: ApiDate;
  competition_end_date: ApiDate;
  deadline: ApiDateTime;
  member_ids: string[];
  fee_categories: string[];
  administrator_id: string;
  project_info: string;
  reimburser_info: string;
  invoice_title?: string | null;
  tax_number?: string | null;
};

export type TaskStatusUpdate = {
  target_status: TaskStatus;
};

export type TaskMembersUpdate = {
  member_ids: string[];
};

export type MaterialRecord = {
  id: string;
  status: MaterialStatus;
  task_id: string | null;
  submitter_id: string | null;
  task_id_hint: string | null;
  submitter_id_hint: string | null;
  channel: SubmissionChannel;
  material_type: MaterialType;
  storage_key: string;
  original_filename: string;
  content_type: string | null;
  size_bytes: number;
  sha256: string;
  duplicate_of: string | null;
  claimed_by: string | null;
  claimed_at: ApiDateTime | null;
  created_at: ApiDateTime;
};

export type MaterialUploadFailure = {
  original_filename: string | null;
  error_code: string;
  detail: string;
};

export type MaterialBatchUploadResponse = {
  status: "success" | "partial_success" | "failed";
  items: MaterialRecord[];
  failures?: MaterialUploadFailure[];
};

export type RecognitionFieldResult = {
  value: unknown;
  source: RecognitionFieldSource;
  confidence: number;
  status: RecognitionFieldStatus;
  updated_at: ApiDateTime | null;
};

export type RecognitionRevalidationStatus = "triggered" | "not_required";

export type RecognitionFieldCorrectionRecord = {
  id: string;
  field_name: string;
  actor_id: string;
  before: RecognitionFieldResult | null;
  after: RecognitionFieldResult;
  revalidation_status: RecognitionRevalidationStatus;
  corrected_at: ApiDateTime;
};

export type RecognitionFailureDetail = {
  stage: RecognitionFailureStage;
  reason: string;
};

export type RecognitionTaskRecord = {
  id: string;
  material_id: string;
  status: RecognitionTaskStatus;
  is_final_fact: false;
  failure: RecognitionFailureDetail | null;
  raw_response: unknown;
  recognized_fields: Record<string, RecognitionFieldResult>;
  manual_corrections: RecognitionFieldCorrectionRecord[];
  created_at: ApiDateTime;
  updated_at: ApiDateTime;
};

export type RecognitionTaskList = {
  latest_effective: RecognitionTaskRecord | null;
  items: RecognitionTaskRecord[];
};

export type InvoiceRecord = {
  id: string;
  task_id: string;
  material_id: string;
  invoice_number: string;
  issue_date: ApiDate | null;
  transaction_time: ApiDateTime | null;
  buyer_name: string;
  tax_number: string;
  seller_name: string | null;
  amount_cents: number;
  expense_type: ExpenseType;
  created_at: ApiDateTime;
  updated_at: ApiDateTime;
};

export type ManualInvoiceEntry = {
  actor_id: string;
  invoice_number: string;
  issue_date?: ApiDate | null;
  transaction_time?: ApiDateTime | null;
  buyer_name: string;
  tax_number: string;
  seller_name?: string | null;
  amount_cents: number;
  expense_type: ExpenseType;
};

export type ValidationResult = {
  id: string;
  rule_code: string;
  target_type: string;
  target_id: string;
  severity: ValidationSeverity;
  status: ValidationStatus;
  message: string;
  evidence: Record<string, unknown>;
  created_at: ApiDateTime;
};

export type ManualInvoiceEntryResponse = {
  invoice: InvoiceRecord;
  validations: ValidationResult[];
};

export type ExpenseSplitItem = {
  member_id: string;
  amount_cents: number;
  note?: string | null;
};

export type ExpenseSplitReplace = {
  actor_id: string;
  items: ExpenseSplitItem[];
};

export type ExpenseSplitRecord = {
  id: string;
  invoice_id: string;
  member_id: string;
  amount_cents: number;
  note: string | null;
  version: number;
  is_active: boolean;
  created_at: ApiDateTime;
  updated_at: ApiDateTime;
};

export type ConfirmationSubmit = {
  actor_id: string;
  member_id: string;
  status: Exclude<ConfirmationStatus, "pending">;
  dispute_reason?: string | null;
};

export type ConfirmationRecord = {
  id: string;
  split_id: string;
  member_id: string;
  split_version: number;
  split_amount_cents: number;
  split_note: string | null;
  is_current: boolean;
  status: ConfirmationStatus;
  dispute_reason: string | null;
  confirmed_at: ApiDateTime;
  updated_at: ApiDateTime;
};

export type TaskExportCapability = {
  kind: ExportArtifactKind;
  formats: ExportArtifactFormat[];
  implemented: boolean;
  implemented_formats: ExportArtifactFormat[];
};

export type TaskExportBoundary = {
  task_id: string;
  administrator_id: string;
  current_task_status: TaskStatus;
  export_allowed: boolean;
  blocking_reasons: string[];
  execution_mode: string;
  supported_exports: TaskExportCapability[];
  note: string;
};

export type TaskExportJobRequest = {
  actor_id: string;
  kind: ExportArtifactKind;
  format: ExportArtifactFormat;
  parameters?: Record<string, unknown>;
};

export type TaskExportJobRecord = {
  id: string;
  task_id: string;
  requested_by: string;
  kind: ExportArtifactKind;
  format: ExportArtifactFormat;
  status: TaskExportJobStatus;
  parameters: Record<string, unknown>;
  task_status_at_request: TaskStatus | null;
  task_data_version: string | null;
  is_latest_for_task: boolean | null;
  failure_reason: string | null;
  created_at: ApiDateTime;
  updated_at: ApiDateTime;
  started_at: ApiDateTime | null;
  finished_at: ApiDateTime | null;
};

export type MaterialReminderCreate = {
  administrator_id: string;
  member_id: string;
  content: string;
};

export type MaterialReminderRecord = {
  id: string;
  task_id: string;
  administrator_id: string;
  member_id: string;
  content: string;
  created_at: ApiDateTime;
};

export type TaskReviewSummaryCounts = {
  material_count: number;
  pending_assignment_material_count: number;
  invoice_count: number;
  validation_count: number;
  blocker_failed_validation_count: number;
  split_count: number;
  confirmed_split_count: number;
  pending_confirmation_count: number;
  disputed_confirmation_count: number;
  missing_confirmation_count: number;
  pending_recognition_count: number;
  failed_recognition_count: number;
  needs_confirmation_recognition_count: number;
};

export type TaskReviewSummary = {
  task_id: string;
  administrator_id: string;
  counts: TaskReviewSummaryCounts;
  materials: TaskReviewSummaryMaterialItem[];
  pending_assignment_materials: MaterialRecord[];
  invoices: TaskReviewSummaryInvoiceItem[];
};

export type TaskReviewSummaryMaterialItem = {
  material: MaterialRecord;
  latest_recognition: RecognitionTaskRecord | null;
  invoice_id: string | null;
  supporting_invoice_ids: string[];
};

export type TaskReviewSummarySplitItem = {
  split: ExpenseSplitRecord;
  confirmation: ConfirmationRecord | null;
};

export type TaskReviewSummaryInvoiceItem = {
  invoice: InvoiceRecord;
  supporting_material_ids: string[];
  validations: ValidationResult[];
  splits: TaskReviewSummarySplitItem[];
};

export type ExpenseDetailScope = "member" | "task";
export type MissingMaterialScope = "member" | "task";

export type ExpenseDetailInvoiceSnapshot = {
  id: string;
  material_id: string;
  invoice_number: string;
  issue_date: ApiDate | null;
  transaction_time: ApiDateTime | null;
  buyer_name: string;
  seller_name: string | null;
  amount_cents: number;
  expense_type: ExpenseType;
  created_at: ApiDateTime;
  updated_at: ApiDateTime;
};

export type ExpenseDetailConfirmationSnapshot = {
  id: string;
  member_id: string;
  split_version: number;
  status: ConfirmationStatus;
  dispute_reason: string | null;
  confirmed_at: ApiDateTime;
  updated_at: ApiDateTime;
};

export type ExpenseDetailItem = {
  split_id: string;
  split_version: number;
  member_id: string;
  amount_cents: number;
  note: string | null;
  created_at: ApiDateTime;
  updated_at: ApiDateTime;
  invoice: ExpenseDetailInvoiceSnapshot;
  confirmation: ExpenseDetailConfirmationSnapshot | null;
};

export type ExpenseDetailList = {
  actor_id: string;
  scope: ExpenseDetailScope;
  total_amount_cents: number;
  items: ExpenseDetailItem[];
};

export type OverdueConfirmationList = {
  task_id: string;
  administrator_id: string;
  confirmation_deadline: ApiDateTime;
  is_overdue: boolean;
  total_overdue_members: number;
  overdue_member_ids: string[];
};

export type TaskExportJobStatusUpdate = {
  actor_id: string;
  target_status: TaskExportJobStatus;
  failure_reason?: string | null;
};

export type ReimbursementSummaryRow = {
  expense_type: ExpenseType;
  total_amount_cents: number;
  member_amounts_cents: Record<string, number>;
};

export type ReimbursementSummaryExport = {
  task_id: string;
  administrator_id: string;
  format: ExportArtifactFormat;
  filename: string;
  generated_at: ApiDateTime;
  member_ids: string[];
  rows: ReimbursementSummaryRow[];
  grand_total_amount_cents: number;
  grand_total_amounts_cents_by_member: Record<string, number>;
};

export type MemberDetailRow = {
  member_id: string;
  expense_type: ExpenseType;
  invoice_number: string;
  invoice_amount_cents: number;
  split_amount_cents: number;
  split_version: number;
  confirmation_status: ConfirmationStatus | null;
  split_note: string | null;
};

export type MemberDetailsExport = {
  task_id: string;
  administrator_id: string;
  format: ExportArtifactFormat;
  filename: string;
  generated_at: ApiDateTime;
  rows: MemberDetailRow[];
  grand_total_amount_cents: number;
};

export type InvoiceDetailRow = {
  invoice_number: string;
  amount_cents: number;
  expense_type: ExpenseType;
  submitter_id: string | null;
  validation_status: ValidationStatus;
  failed_rule_codes: string[];
  pending_rule_codes: string[];
  abnormal_validation_messages: string[];
};

export type InvoiceDetailsExport = {
  task_id: string;
  administrator_id: string;
  format: ExportArtifactFormat;
  filename: string;
  generated_at: ApiDateTime;
  rows: InvoiceDetailRow[];
};

export type MissingMaterialExportRow = {
  member_id: string | null;
  expense_type: ExpenseType;
  invoice_number: string;
  required_material_type: MaterialType;
  source_rule_code: string;
  message: string;
};

export type MissingMaterialItem = {
  task_id: string;
  member_id: string | null;
  invoice_id: string;
  invoice_number: string;
  expense_type: ExpenseType;
  required_material_type: MaterialType;
  source_rule_code: string;
  message: string;
  evidence: Record<string, unknown>;
  detected_at: ApiDateTime;
};

export type VisibleMissingMaterialList = {
  task_id: string;
  actor_id: string;
  scope: MissingMaterialScope;
  items: MissingMaterialItem[];
};

export type MissingMaterialsExport = {
  task_id: string;
  administrator_id: string;
  format: ExportArtifactFormat;
  filename: string;
  generated_at: ApiDateTime;
  rows: MissingMaterialExportRow[];
};

export type FinanceDraftSplitRow = {
  member_id: string;
  amount_cents: number;
  split_version: number;
  split_note: string | null;
};

export type FinanceDraftInvoiceRow = {
  invoice_number: string;
  expense_type: ExpenseType;
  amount_cents: number;
  buyer_name: string;
  tax_number: string;
  seller_name: string | null;
  issue_date: ApiDate | null;
  transaction_time: ApiDateTime | null;
  submitter_id: string | null;
  validation_status: ValidationStatus;
  failed_rule_codes: string[];
  pending_rule_codes: string[];
  split_items: FinanceDraftSplitRow[];
};

export type FinanceDraftExport = {
  task_id: string;
  administrator_id: string;
  format: ExportArtifactFormat;
  filename: string;
  generated_at: ApiDateTime;
  competition_name: string;
  competition_location: string;
  competition_start_date: ApiDate;
  competition_end_date: ApiDate;
  project_info: string;
  reimburser_info: string;
  invoice_title: string;
  tax_number: string;
  total_amount_cents: number;
  invoice_count: number;
  expense_totals_cents: Record<string, number>;
  member_totals_cents: Record<string, number>;
  invoice_rows: FinanceDraftInvoiceRow[];
};

export type MergedPdfPlanItemKind =
  | "reimbursement_summary"
  | "member_details"
  | "invoice_details"
  | "invoice_material"
  | "supporting_material";

export type MergedPdfPlanItemStatus = "placeholder" | "ready";

export type MergedPdfPlanItem = {
  sequence: number;
  kind: MergedPdfPlanItemKind;
  status: MergedPdfPlanItemStatus;
  label: string;
  note: string | null;
  material_id: string | null;
  material_type: MaterialType | null;
  original_filename: string | null;
};

export type MergedPdfExportPlan = {
  task_id: string;
  administrator_id: string;
  format: ExportArtifactFormat;
  filename: string;
  generated_at: ApiDateTime;
  ordered_items: MergedPdfPlanItem[];
  note: string;
};
