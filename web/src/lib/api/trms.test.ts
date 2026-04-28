import { afterEach, describe, expect, it, vi } from "vitest";

import { setApiAccessTokenProvider } from "./client";
import { trmsApi } from "./trms";

function jsonResponse(body: unknown) {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: {
      "Content-Type": "application/json",
    },
  });
}

describe("trmsApi bearer identity migration", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    setApiAccessTokenProvider(null);
  });

  it("removes actor-scoped query parameters when a bearer token is available", async () => {
    setApiAccessTokenProvider(() => "access-token");
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse({
      task_id: "TASK-1",
      administrator_id: "admin-1",
      current_task_status: "ready_to_export",
      export_allowed: true,
      blocking_reasons: [],
      execution_mode: "async_worker",
      supported_exports: [],
      note: "ok",
    }));

    await trmsApi.getTaskExportCapabilities("TASK-1", "admin-1");

    const firstCall = fetchSpy.mock.calls[0];
    expect(firstCall).toBeDefined();
    const url = firstCall?.[0];
    expect(url).toBe("/api/tasks/TASK-1/exports/capabilities");
  });

  it("strips actor and member fields from confirmation payloads when a bearer token is available", async () => {
    setApiAccessTokenProvider(() => "access-token");
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse({
      id: "CONF-1",
      split_id: "SPLIT-1",
      member_id: "2250001",
      split_version: 1,
      split_amount_cents: 12345,
      split_note: null,
      is_current: true,
      status: "confirmed",
      dispute_reason: null,
      confirmed_at: "2026-04-28T10:00:00+08:00",
      updated_at: "2026-04-28T10:00:00+08:00",
    }));

    await trmsApi.submitSplitConfirmation("SPLIT-1", {
      actor_id: "2250001",
      member_id: "2250001",
      status: "confirmed",
    });

    const firstCall = fetchSpy.mock.calls[0];
    expect(firstCall).toBeDefined();
    const init = firstCall?.[1];
    expect(init?.body).toBe(JSON.stringify({ status: "confirmed" }));
  });

  it("keeps legacy actor fields for mock sessions without a bearer token", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse({
      actor_id: "2250001",
      scope: "member",
      total_amount_cents: 0,
      items: [],
    }));

    await trmsApi.listTaskExpenseDetails("TASK-1", "2250001");

    const firstCall = fetchSpy.mock.calls[0];
    expect(firstCall).toBeDefined();
    const url = firstCall?.[0];
    expect(url).toBe("/api/tasks/TASK-1/expense-details?actor_id=2250001");
  });
});
