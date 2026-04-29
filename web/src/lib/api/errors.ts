import { formatFieldLabel, mapBackendMessage } from "../ui-text";

type ApiErrorRecord = Record<string, unknown>;

export type ApiErrorFieldIssue = {
  label: string;
  message: string;
};

export type ApiErrorSummary = {
  status: number;
  title: string;
  message: string;
  fieldIssues: ApiErrorFieldIssue[];
  detailLines: string[];
};

type ApiValidationIssue = {
  loc?: unknown;
  msg?: unknown;
};

function isRecord(value: unknown): value is ApiErrorRecord {
  return typeof value === "object" && value !== null;
}

function isValidationIssue(value: unknown): value is ApiValidationIssue {
  return isRecord(value);
}

function isLocationPrefix(segment: string) {
  return segment === "body" || segment === "query" || segment === "path" || segment === "header";
}

function formatLocation(loc: unknown) {
  if (!Array.isArray(loc)) {
    return "unknown";
  }

  const parts = loc
    .map((segment) => {
      if (typeof segment === "string" || typeof segment === "number") {
        return String(segment);
      }
      return null;
    })
    .filter((segment): segment is string => segment !== null);

  if (parts.length === 0) {
    return "unknown";
  }

  const firstPart = parts[0];
  const normalized = firstPart !== undefined && isLocationPrefix(firstPart) ? parts.slice(1) : parts;
  return normalized.length > 0 ? normalized.join(".") : parts.join(".");
}

function normalizeFieldIssues(detail: unknown): ApiErrorFieldIssue[] {
  if (!Array.isArray(detail)) {
    return [];
  }

  return detail.flatMap((item) => {
    if (!isValidationIssue(item) || typeof item.msg !== "string" || item.msg.length === 0) {
      return [];
    }

    return [
      {
        label: formatFieldLabel(formatLocation(item.loc)),
        message: translateFieldIssueMessage(String(item.msg)),
      },
    ];
  });
}

function detailText(detail: unknown) {
  if (typeof detail === "string" && detail.length > 0) {
    return detail;
  }
  return null;
}

function fallbackMessage(status: number) {
  if (status === 0) {
    return "网络连接异常，请检查网络后重试。";
  }
  return status >= 500
    ? "系统暂时无法完成该操作，请稍后重试。"
    : "当前操作未完成，请检查填写内容后重试。";
}

function translateFieldIssueMessage(message: string) {
  const normalized = message.toLowerCase();

  if (normalized === "field required") {
    return "请填写此项。";
  }
  if (normalized.includes("valid string")) {
    return "请输入有效内容。";
  }
  if (normalized.includes("valid integer") || normalized.includes("valid number")) {
    return "请输入有效数字。";
  }
  if (normalized.includes("should have at least")) {
    return "填写内容过短，请补充后重试。";
  }
  if (normalized.includes("unsupported fee categories")) {
    return "所选费用类别暂不支持。";
  }
  return message;
}

export function extractApiErrorMessage(payload: unknown) {
  if (typeof payload === "string" && payload.length > 0) {
    return payload;
  }

  if (!isRecord(payload)) {
    return null;
  }

  const directDetail = detailText(payload.detail);
  if (directDetail !== null) {
    return directDetail;
  }

  if (normalizeFieldIssues(payload.detail).length > 0) {
    return null;
  }

  if (typeof payload.message === "string" && payload.message.length > 0) {
    return payload.message;
  }

  return null;
}

export function summarizeApiError(status: number, payload: unknown): ApiErrorSummary {
  const fieldIssues = isRecord(payload) ? normalizeFieldIssues(payload.detail) : [];
  const rawMessage = extractApiErrorMessage(payload) ?? (
    fieldIssues.length > 0
      ? "提交信息有误，请检查以下字段。"
      : fallbackMessage(status)
  );
  const message = mapBackendMessage(rawMessage, status);
  const detailLines = (() => {
    return [];
  })();

  return {
    status,
    title: status === 0 ? "网络连接异常" : "操作未完成",
    message,
    fieldIssues,
    detailLines,
  };
}

export function summarizeUnknownError(error: unknown): ApiErrorSummary {
  if (error instanceof Error) {
    return {
      status: 0,
      title: "操作未完成",
      message: mapBackendMessage(error.message || "前端遇到未预期错误"),
      fieldIssues: [],
      detailLines: [],
    };
  }

  return {
    status: 0,
    title: "操作未完成",
    message: "系统暂时无法完成该操作，请稍后重试。",
    fieldIssues: [],
    detailLines: [],
  };
}
