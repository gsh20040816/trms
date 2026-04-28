import { extractApiErrorMessage, summarizeApiError, type ApiErrorSummary } from "./errors";

type ApiRequestBody = string | FormData | URLSearchParams | Blob | Record<string, unknown> | null;

export type ApiRequestOptions = Omit<RequestInit, "body"> & {
  body?: ApiRequestBody;
};

export type ApiDownloadedFile = {
  blob: Blob;
  filename: string | null;
  contentType: string | null;
};

let apiAccessTokenProvider: (() => string | null) | null = null;

function normalizeBaseUrl(baseUrl: string) {
  return baseUrl.replace(/\/+$/, "");
}

function normalizePath(path: string) {
  return path.startsWith("/") ? path : `/${path}`;
}

type ApiBaseUrlEnvironment = {
  VITE_API_BASE_URL?: string;
};

export function resolveApiBaseUrl(environment: ApiBaseUrlEnvironment = import.meta.env) {
  const rawBaseUrl: unknown = environment.VITE_API_BASE_URL;
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

  constructor(baseUrl = resolveApiBaseUrl()) {
    this.baseUrl = normalizeBaseUrl(baseUrl);
  }

  buildUrl(path: string) {
    return `${this.baseUrl}${normalizePath(path)}`;
  }

  async request<T>(path: string, options: ApiRequestOptions = {}) {
    const response = await this.fetchResponse(path, options);
    const payload = await this.parseResponseOrThrow(response);
    if (!response.ok) {
      throw new ApiError(response.status, payload);
    }

    return payload as T;
  }

  async download(path: string, options: ApiRequestOptions = {}) {
    const response = await this.fetchResponse(path, options);
    if (!response.ok) {
      const payload = await this.parseResponseOrThrow(response);
      throw new ApiError(response.status, payload);
    }

    return {
      blob: await response.blob(),
      filename: extractFilenameFromContentDisposition(response.headers.get("Content-Disposition")),
      contentType: response.headers.get("Content-Type"),
    } satisfies ApiDownloadedFile;
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

  private async fetchResponse(path: string, options: ApiRequestOptions): Promise<Response> {
    const headers = new Headers(options.headers);
    const requestBody = buildRequestBody(options.body);

    if (requestBody && shouldSerializeJson(options.body) && !headers.has("Content-Type")) {
      headers.set("Content-Type", "application/json");
    }
    if (!headers.has("Authorization")) {
      const accessToken = apiAccessTokenProvider?.() ?? null;
      if (accessToken) {
        headers.set("Authorization", `Bearer ${accessToken}`);
      }
    }

    try {
      return await fetch(this.buildUrl(path), {
        ...options,
        body: requestBody,
        headers,
      });
    } catch (error) {
      throw new ApiError(0, buildTransportErrorPayload(error));
    }
  }

  private async parseResponseOrThrow(response: Response): Promise<unknown> {
    try {
      return await this.parseResponse(response);
    } catch (error) {
      throw new ApiError(response.status, buildJsonParseErrorPayload(error));
    }
  }
}

export const apiClient = new ApiClient();

export function setApiAccessTokenProvider(provider: (() => string | null) | null) {
  apiAccessTokenProvider = provider;
}

export function getConfiguredApiAccessToken() {
  return apiAccessTokenProvider?.() ?? null;
}

function extractFilenameFromContentDisposition(headerValue: string | null) {
  if (!headerValue) {
    return null;
  }

  const encodedMatch = /filename\*=UTF-8''([^;]+)/i.exec(headerValue);
  const encodedFilename = encodedMatch?.[1];
  if (encodedFilename) {
    return decodeURIComponent(encodedFilename);
  }

  const plainMatch = /filename="?([^";]+)"?/i.exec(headerValue);
  return plainMatch?.[1] ?? null;
}
