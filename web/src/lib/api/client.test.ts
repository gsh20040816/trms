import { afterEach, describe, expect, it, vi } from "vitest";

import {
  ApiClient,
  ApiError,
  resolveApiBaseUrl,
  setApiAccessTokenProvider,
} from "./client";

describe("ApiClient", () => {
  const client = new ApiClient("/api");

  afterEach(() => {
    vi.restoreAllMocks();
    setApiAccessTokenProvider(null);
  });

  it("defaults to same-origin /api when no API base URL is configured", () => {
    expect(resolveApiBaseUrl({})).toBe("/api");
  });

  it("normalizes a configured API base URL without trailing slashes", () => {
    expect(resolveApiBaseUrl({
      VITE_API_BASE_URL: " http://127.0.0.1:8100/api/ ",
    })).toBe("http://127.0.0.1:8100/api");
  });

  it("normalizes field validation errors into a unified summary", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          detail: [
            {
              loc: ["body", "member_ids", 0],
              msg: "list items must not be blank",
              type: "value_error",
            },
          ],
        }),
        {
          status: 422,
          headers: {
            "Content-Type": "application/json",
          },
        },
      ),
    );

    await expect(client.request("/tasks", { method: "POST", body: { member_ids: [""] } })).rejects.toMatchObject({
      status: 422,
      summary: {
        title: "接口请求失败",
        message: "请求参数不合法",
        fieldIssues: [
          {
            path: "member_ids.0",
            message: "list items must not be blank",
          },
        ],
      },
    });
  });

  it("keeps service-side detail messages visible to the caller", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ detail: "task not found" }), {
        status: 404,
        headers: {
          "Content-Type": "application/json",
        },
      }),
    );

    await expect(client.request("/tasks/missing")).rejects.toMatchObject({
      status: 404,
      message: "task not found",
      summary: {
        detailLines: [],
      },
    });
  });

  it("wraps network failures instead of leaking raw fetch errors", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new TypeError("fetch failed"));

    await expect(client.request("/tasks")).rejects.toBeInstanceOf(ApiError);
    await expect(client.request("/tasks")).rejects.toMatchObject({
      status: 0,
      summary: {
        title: "网络请求失败",
        message: "无法连接到 TRMS 后端服务",
        detailLines: ["fetch failed"],
      },
    });
  });

  it("injects bearer authorization from the configured session provider", async () => {
    setApiAccessTokenProvider(() => "access-token-123");
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: {
          "Content-Type": "application/json",
        },
      }),
    );

    await expect(client.request("/tasks")).resolves.toEqual({ ok: true });

    const firstCall = fetchSpy.mock.calls[0];
    expect(firstCall).toBeDefined();
    const init = firstCall?.[1];
    const headers = new Headers(init?.headers);
    expect(headers.get("Authorization")).toBe("Bearer access-token-123");
  });
});
