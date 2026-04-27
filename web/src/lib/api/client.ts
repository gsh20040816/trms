export type ApiErrorPayload = {
  detail?: unknown;
  message?: string;
  [key: string]: unknown;
};

type ApiRequestBody = string | FormData | URLSearchParams | Blob | Record<string, unknown> | null;

export type ApiRequestOptions = Omit<RequestInit, "body"> & {
  body?: ApiRequestBody;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

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
  readonly payload: ApiErrorPayload | null;

  constructor(status: number, message: string, payload: ApiErrorPayload | null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.payload = payload;
  }
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

    const response = await fetch(this.buildUrl(path), {
      ...options,
      body: requestBody,
      headers,
    });

    const payload: unknown = await this.parseResponse(response);
    if (!response.ok) {
      const message = this.extractErrorMessage(payload) ?? `Request failed with status ${response.status}`;
      throw new ApiError(response.status, message, this.asErrorPayload(payload));
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

  private extractErrorMessage(payload: unknown) {
    if (typeof payload === "string" && payload.length > 0) {
      return payload;
    }
    if (isRecord(payload)) {
      const message = payload["message"];
      if (typeof message === "string" && message.length > 0) {
        return message;
      }
      const detail = payload["detail"];
      if (typeof detail === "string" && detail.length > 0) {
        return detail;
      }
    }
    return null;
  }

  private asErrorPayload(payload: unknown) {
    return isRecord(payload) ? payload : null;
  }
}

export const apiClient = new ApiClient();
