import { extractApiErrorMessage, summarizeApiError, type ApiErrorSummary } from "./errors";

type ApiRequestBody = string | FormData | URLSearchParams | Blob | Record<string, unknown> | null;

export type ApiRequestOptions = Omit<RequestInit, "body"> & {
  body?: ApiRequestBody;
};

function normalizeBaseUrl(baseUrl: string) {
  return baseUrl.replace(/\/+$/, "");
}

function normalizePath(path: string) {
  return path.startsWith("/") ? path : `/${path}`;
}

function defaultApiBaseUrl() {
  const rawBaseUrl: unknown = import.meta.env.VITE_API_BASE_URL;
  const configuredBaseUrl = typeof rawBaseUrl === "string" ? rawBaseUrl.trim() : "";
  return normalizeBaseUrl(configuredBaseUrl && configuredBaseUrl.length > 0 ? configuredBaseUrl : "/api");
}

function shouldSerializeJson(body: ApiRequestBody | undefined): body is Record<string, unknown> {
  return body !== null && typeof body === "object" && !(body instanceof FormData) && !(body instanceof URLSearchParams) && !(body instanceof Blob);
}

function buildRequestBody(body: ApiRequestBody | undefined): BodyInit | null | undefined {
  if (shouldSerializeJson(body)) {
    return JSON.stringify(body);
  }
  return body;
}

export class ApiError extends Error {
  readonly status: number;
  readonly payload: unknown;
  readonly summary: ApiErrorSummary;

  constructor(status: number, payload: unknown) {
    const message = extractApiErrorMessage(payload) ?? `Request failed with status ${status}`;
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.payload = payload;
    this.summary = summarizeApiError(status, payload);
  }
}

function buildTransportErrorPayload(error: unknown) {
  return {
    message: "无法连接到 TRMS 后端服务",
    detail: error instanceof Error ? error.message : "unknown network error",
  };
}

function buildJsonParseErrorPayload(error: unknown) {
  return {
    message: "服务端返回了无法解析的响应",
    detail: error instanceof Error ? error.message : "unknown response parse error",
  };
}

export class ApiClient {
  readonly baseUrl: string;

  constructor(baseUrl = defaultApiBaseUrl()) {
    this.baseUrl = normalizeBaseUrl(baseUrl);
  }

  buildUrl(path: string) {
    return `${this.baseUrl}${normalizePath(path)}`;
  }

  async request<T>(path: string, options: ApiRequestOptions = {}) {
    const headers = new Headers(options.headers);
    const requestBody = buildRequestBody(options.body);

    if (requestBody && shouldSerializeJson(options.body) && !headers.has("Content-Type")) {
      headers.set("Content-Type", "application/json");
    }

    let response: Response;
    try {
      response = await fetch(this.buildUrl(path), {
        ...options,
        body: requestBody,
        headers,
      });
    } catch (error) {
      throw new ApiError(0, buildTransportErrorPayload(error));
    }

    let payload: unknown;
    try {
      payload = await this.parseResponse(response);
    } catch (error) {
      throw new ApiError(response.status, buildJsonParseErrorPayload(error));
    }
    if (!response.ok) {
      throw new ApiError(response.status, payload);
    }

    return payload as T;
  }

  private async parseResponse(response: Response): Promise<unknown> {
    if (response.status === 204) {
      return undefined;
    }

    const contentType = response.headers.get("Content-Type") ?? "";
    if (contentType.includes("application/json")) {
      const jsonText = await response.text();
      return jsonText.length > 0 ? (JSON.parse(jsonText) as unknown) : undefined;
    }

    return response.text();
  }
}

export const apiClient = new ApiClient();
