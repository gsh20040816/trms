import type {
  ConfirmationStatus,
  ExpenseType,
  MaterialType,
  RecognitionFailureDetail,
  RecognitionTaskStatus,
  SubmissionChannel,
  TaskExportJobStatus,
  TaskStatus,
  ValidationSeverity,
  ValidationStatus,
} from "./api/types";
import type { UserRole } from "../app/role-routes";

export const ROLE_LABELS: Record<UserRole, string> = {
  member: "成员",
  admin: "管理员",
  system_admin: "系统管理员",
};

export const WORKSPACE_LABELS: Record<UserRole, string> = {
  member: "成员工作台",
  admin: "管理员工作台",
  system_admin: "系统管理",
};

export const TASK_STATUS_LABELS: Record<TaskStatus, string> = {
  draft: "草稿",
  open: "收集中",
  closed: "已截止",
  reviewing: "待复核",
  ready_to_export: "可导出",
  completed: "已完成",
};

export const MATERIAL_TYPE_LABELS: Record<MaterialType, string> = {
  invoice: "发票",
  payment_record: "支付记录",
  competition_notice: "比赛通知",
  itinerary: "行程单",
  order_screenshot: "订单截图",
  other_attachment: "其他材料",
};

export const EXPENSE_TYPE_LABELS: Record<ExpenseType, string> = {
  registration: "参赛费",
  railway: "铁路交通",
  airfare: "航空交通",
  local_transport: "市内交通",
  hotel: "住宿费",
  other: "其他费用",
};

export const SUBMISSION_CHANNEL_LABELS: Record<SubmissionChannel, string> = {
  web: "网页提交",
  cli: "命令行提交",
  telegram: "Telegram 提交",
  email: "邮件提交",
};

export const RECOGNITION_STATUS_LABELS: Record<RecognitionTaskStatus, string> = {
  pending: "识别处理中",
  succeeded: "已识别",
  failed: "无法识别",
  needs_confirmation: "信息待确认",
};

export const VALIDATION_STATUS_LABELS: Record<ValidationStatus, string> = {
  passed: "已通过",
  failed: "需要处理",
  pending: "待确认",
  not_applicable: "不适用",
};

export const VALIDATION_SEVERITY_LABELS: Record<ValidationSeverity, string> = {
  blocker: "需要立即处理",
  warning: "需要关注",
  info: "已记录",
};

export const CONFIRMATION_STATUS_LABELS: Record<ConfirmationStatus, string> = {
  pending: "待确认",
  confirmed: "已确认",
  disputed: "有异议",
};

export const EXPORT_JOB_STATUS_LABELS: Record<TaskExportJobStatus, string> = {
  pending: "待生成",
  running: "生成中",
  succeeded: "已完成",
  failed: "生成失败",
};

export const FIELD_LABELS: Record<string, string> = {
  username: "用户名",
  password: "密码",
  role: "角色",
  display_name: "姓名",
  actor_id: "身份编号",
  member_code: "成员编号",
  member_ids: "成员名单",
  competition_name: "任务名称",
  competition_location: "比赛地点",
  competition_start_date: "开始日期",
  competition_end_date: "结束日期",
  deadline: "截止时间",
  fee_categories: "费用类别",
  administrator_id: "负责人",
  project_info: "项目说明",
  reimburser_info: "报销人信息",
  invoice_title: "发票抬头",
  buyer_name: "发票抬头",
  tax_number: "税号",
  invoice_number: "发票号码",
  transaction_time: "交易时间",
  amount_cents: "金额",
  expense_type: "费用类型",
  seller_name: "销售方名称",
  dispute_reason: "异议说明",
  note: "备注",
};

const VALIDATION_RULE_LABELS: Record<string, string> = {
  invoice_title_match: "发票抬头需要核对",
  invoice_tax_number_match: "税号需要核对",
  invoice_payment_record_required: "缺少支付记录",
  invoice_competition_notice_required: "缺少比赛通知",
  invoice_airfare_itinerary_required: "缺少行程单",
  invoice_local_transport_rideshare_trip_required: "缺少行程信息",
  invoice_duplicate_number: "疑似重复发票",
  invoice_amount_split_mismatch: "分摊金额需要核对",
  invoice_transaction_time_range: "交易时间需要核对",
  invoice_location_range: "交易地点需要核对",
};

export function formatRole(role: UserRole) {
  return ROLE_LABELS[role];
}

export function formatWorkspace(role: UserRole) {
  return WORKSPACE_LABELS[role];
}

export function formatTaskStatus(status: TaskStatus) {
  return TASK_STATUS_LABELS[status];
}

export function formatMaterialType(type: MaterialType) {
  return MATERIAL_TYPE_LABELS[type] ?? "材料";
}

export function formatExpenseType(type: string) {
  return EXPENSE_TYPE_LABELS[type as ExpenseType] ?? type;
}

export function formatSubmissionChannel(channel: SubmissionChannel) {
  return SUBMISSION_CHANNEL_LABELS[channel] ?? "其他渠道";
}

export function formatRecognitionStatus(status: RecognitionTaskStatus) {
  return RECOGNITION_STATUS_LABELS[status];
}

export function formatValidationStatus(status: ValidationStatus) {
  return VALIDATION_STATUS_LABELS[status];
}

export function formatValidationSeverity(severity: ValidationSeverity) {
  return VALIDATION_SEVERITY_LABELS[severity];
}

export function formatConfirmationStatus(status: ConfirmationStatus) {
  return CONFIRMATION_STATUS_LABELS[status];
}

export function formatExportJobStatus(status: TaskExportJobStatus) {
  return EXPORT_JOB_STATUS_LABELS[status];
}

export function formatFieldLabel(path: string) {
  const segments = path.split(".");
  const first = segments[0] ?? path;
  const mapped = FIELD_LABELS[first] ?? "填写项";
  if (segments.length > 1 && Number.isInteger(Number(segments[1]))) {
    return `${mapped}第 ${Number(segments[1]) + 1} 项`;
  }
  return mapped;
}

export function formatValidationRule(ruleCode: string) {
  return VALIDATION_RULE_LABELS[ruleCode] ?? "需要补充或核对的信息";
}

export function formatMemberLabel(memberId: string | null | undefined) {
  if (!memberId) {
    return "待确认成员";
  }
  return `成员 ${memberId}`;
}

export function describeRecognitionFailure(failure: RecognitionFailureDetail | null) {
  if (!failure) {
    return "系统暂时无法识别该材料，请补充更清晰的文件或稍后重试。";
  }

  if (
    failure.stage === "ai"
    && (
      failure.reason === "llm_provider_not_configured"
      || failure.reason === "structured_recognition_not_configured"
    )
  ) {
    return "当前环境未配置识别服务，系统暂时不能自动生成发票结构化结果；请联系管理员配置识别服务或改为人工补录。";
  }
  if (failure.stage === "ocr") {
    return "图片内容未能成功识别，请上传更清晰的图片或手动补充信息。";
  }
  if (failure.stage === "pdf") {
    return "文件内容暂时无法读取，请确认文件完整后重新上传。";
  }
  return "材料信息暂时无法整理，请稍后重试或改为人工补录。";
}

export function mapBackendMessage(message: string, status = 0) {
  const normalized = message.trim().toLowerCase();

  if (status === 0 || normalized.includes("network") || normalized.includes("fetch failed")) {
    return "网络连接异常，请检查网络后重试。";
  }
  if (normalized.includes("permission denied") || normalized.includes("forbidden")) {
    return "你没有权限处理此内容，如需访问请联系管理员。";
  }
  if (normalized.includes("not found")) {
    return "请求的内容不存在或已被移除，请刷新页面后重试。";
  }
  if (normalized.includes("temporarily unavailable") || normalized.includes("service unavailable")) {
    return "系统暂时不可用，请稍后再试。";
  }
  if (normalized.includes("ocr") || normalized.includes("parse failed")) {
    return "材料识别失败，请上传更清晰的文件或改为人工补录。";
  }
  if (normalized.includes("payload is too large") || normalized.includes("content too large")) {
    return "上传文件过大，请缩小到页面允许的大小后重试。";
  }
  if (normalized.includes("ready_to_export") || normalized.includes("可导出")) {
    return "当前任务还没完成导出前置条件，请先处理缺失材料、复核或状态推进。";
  }
  if (normalized.includes("unsupported fee categories")) {
    return "所选费用类别暂不支持，请调整后再提交。";
  }
  if (normalized.includes("task list")) {
    return "暂时无法读取任务列表，请稍后刷新。";
  }
  if (normalized.includes("missing required field")) {
    const field = message.split(":").pop()?.trim() ?? "";
    return `缺少${FIELD_LABELS[field] ?? "必要信息"}，请补充后再提交。`;
  }
  if (status >= 500) {
    return "系统暂时无法完成该操作，请稍后重试。";
  }
  if (status >= 400) {
    return "当前操作未完成，请检查填写内容后重试。";
  }
  return message;
}
