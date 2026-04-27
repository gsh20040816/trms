type ApiErrorRecord = Record<string, unknown>;

export type ApiErrorFieldIssue = {
  path: string;
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
        path: formatLocation(item.loc),
        message: item.msg,
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
    return "无法连接到 TRMS 后端服务";
  }
  return `请求失败（HTTP ${status}）`;
}

export function extractApiErrorMessage(payload: unknown) {
  if (typeof payload === "string" && payload.length > 0) {
    return payload;
  }

  if (!isRecord(payload)) {
    return null;
  }

  if (typeof payload.message === "string" && payload.message.length > 0) {
    return payload.message;
  }

  const directDetail = detailText(payload.detail);
  if (directDetail !== null) {
    return directDetail;
  }

  if (normalizeFieldIssues(payload.detail).length > 0) {
    return "请求参数不合法";
  }

  return null;
}

export function summarizeApiError(status: number, payload: unknown): ApiErrorSummary {
  const fieldIssues = isRecord(payload) ? normalizeFieldIssues(payload.detail) : [];
  const message = extractApiErrorMessage(payload) ?? fallbackMessage(status);
  const detailLines = (() => {
    if (fieldIssues.length > 0) {
      return fieldIssues.map((issue) => `${issue.path}: ${issue.message}`);
    }

    if (isRecord(payload)) {
      const directDetail = detailText(payload.detail);
      if (directDetail !== null && directDetail !== message) {
        return [directDetail];
      }
    }

    if (typeof payload === "string" && payload !== message) {
      return [payload];
    }

    return [];
  })();

  return {
    status,
    title: status === 0 ? "网络请求失败" : "接口请求失败",
    message,
    fieldIssues,
    detailLines,
  };
}

export function summarizeUnknownError(error: unknown): ApiErrorSummary {
  if (error instanceof Error) {
    return {
      status: 0,
      title: "前端处理失败",
      message: error.message || "前端遇到未预期错误",
      fieldIssues: [],
      detailLines: [],
    };
  }

  return {
    status: 0,
    title: "前端处理失败",
    message: "前端遇到未预期错误",
    fieldIssues: [],
    detailLines: [],
  };
}
