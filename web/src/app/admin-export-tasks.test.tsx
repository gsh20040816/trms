import { act, fireEvent, render, screen, within } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { clearMockSession, setMockSession } from "./auth-store";
import { routes } from "./routes";

function resolveRequestUrl(input: string | URL | Request) {
  if (typeof input === "string") {
    return input;
  }
  if (input instanceof URL) {
    return input.toString();
  }
  return input.url;
}

function jsonResponse(body: unknown, init: ResponseInit = {}) {
  return new Response(JSON.stringify(body), {
    status: init.status ?? 200,
    headers: {
      "Content-Type": "application/json",
      ...init.headers,
    },
  });
}

function textResponse(body: string, init: ResponseInit = {}) {
  return new Response(body, {
    status: init.status ?? 200,
    headers: {
      "Content-Type": "text/csv; charset=utf-8",
      ...init.headers,
    },
  });
}

function buildTask(taskId: string, status: "ready_to_export" | "reviewing") {
  return {
    id: taskId,
    status,
    competition_name: "ICPC 区域赛报销",
    competition_location: "上海",
    competition_start_date: "2026-05-01",
    competition_end_date: "2026-05-03",
    deadline: "2026-05-10T18:00:00+08:00",
    member_ids: ["2250001", "2250002"],
    fee_categories: ["registration", "hotel"],
    administrator_id: "admin-1",
    project_info: "Project Export",
    reimburser_info: "张管理员",
    invoice_title: "同济大学",
    tax_number: "91310000TEST00001",
    created_at: "2026-04-20T09:00:00+08:00",
    updated_at: "2026-04-25T10:00:00+08:00",
  };
}

function buildCapabilities(taskId: string, exportAllowed: boolean) {
  return {
    task_id: taskId,
    administrator_id: "admin-1",
    current_task_status: exportAllowed ? "ready_to_export" : "reviewing",
    export_allowed: exportAllowed,
    blocking_reasons: exportAllowed
      ? []
      : ["task must be ready_to_export or completed before real exports can be generated"],
    execution_mode: "async_worker",
    note: "reimbursement summary/member details/invoice details/missing materials CSV export and finance draft JSON export are available through async export jobs with persisted artifacts; merged PDF planning/validation remains a placeholder",
    supported_exports: [
      {
        kind: "reimbursement_summary",
        formats: ["xlsx", "csv"],
        implemented: true,
        implemented_formats: ["csv"],
      },
      {
        kind: "member_details",
        formats: ["xlsx", "csv"],
        implemented: true,
        implemented_formats: ["csv"],
      },
      {
        kind: "invoice_details",
        formats: ["xlsx", "csv"],
        implemented: true,
        implemented_formats: ["csv"],
      },
      {
        kind: "missing_materials",
        formats: ["xlsx", "csv"],
        implemented: true,
        implemented_formats: ["csv"],
      },
      {
        kind: "finance_draft",
        formats: ["xlsx", "json"],
        implemented: true,
        implemented_formats: ["json"],
      },
      {
        kind: "merged_pdf",
        formats: ["pdf"],
        implemented: false,
        implemented_formats: [],
      },
    ],
  };
}

function renderExportRoute(taskId = "TASK-EXPORT") {
  const router = createMemoryRouter(routes, {
    initialEntries: [`/admin/tasks/${taskId}/exports`],
  });

  render(<RouterProvider router={router} />);
}

describe("admin export tasks page", () => {
  beforeEach(() => {
    clearMockSession();
    setMockSession("admin");
  });

  afterEach(() => {
    vi.restoreAllMocks();
    clearMockSession();
  });

  it("creates export jobs, shows failed history and previews current output", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((input: string | URL | Request, init?: RequestInit) => {
      const url = resolveRequestUrl(input);

      if (url === "/api/tasks/TASK-EXPORT") {
        return Promise.resolve(jsonResponse(buildTask("TASK-EXPORT", "ready_to_export")));
      }

      if (url === "/api/tasks/TASK-EXPORT/exports/capabilities?actor_id=admin-1") {
        return Promise.resolve(jsonResponse(buildCapabilities("TASK-EXPORT", true)));
      }

      if (url === "/api/tasks/TASK-EXPORT/exports?actor_id=admin-1" && !init?.method) {
        return Promise.resolve(jsonResponse([
          {
            id: "export-job-merged",
            task_id: "TASK-EXPORT",
            requested_by: "admin-1",
            kind: "merged_pdf",
            format: "pdf",
            status: "failed",
            parameters: {},
            task_status_at_request: "ready_to_export",
            task_data_version: "a".repeat(64),
            is_latest_for_task: true,
            failure_reason: "failed to read encrypted material PDF",
            created_at: "2026-04-28T09:00:00+08:00",
            updated_at: "2026-04-28T09:05:00+08:00",
            started_at: "2026-04-28T09:01:00+08:00",
            finished_at: "2026-04-28T09:05:00+08:00",
          },
        ]));
      }

      if (url === "/api/tasks/TASK-EXPORT/exports" && init?.method === "POST") {
        expect(init.body).toBe(JSON.stringify({
          actor_id: "admin-1",
          kind: "reimbursement_summary",
          format: "xlsx",
          parameters: {},
        }));
        return Promise.resolve(jsonResponse(
          {
            id: "export-job-summary",
            task_id: "TASK-EXPORT",
            requested_by: "admin-1",
            kind: "reimbursement_summary",
            format: "xlsx",
            status: "pending",
            parameters: {},
            task_status_at_request: "ready_to_export",
            task_data_version: "b".repeat(64),
            is_latest_for_task: true,
            failure_reason: null,
            created_at: "2026-04-28T09:10:00+08:00",
            updated_at: "2026-04-28T09:10:00+08:00",
            started_at: null,
            finished_at: null,
          },
          { status: 201 },
        ));
      }

      if (url === "/api/tasks/TASK-EXPORT/exports/reimbursement-summary?actor_id=admin-1&format=csv") {
        return Promise.resolve(textResponse(
          "expense_type,total_amount_cents,2250001\nregistration,20000,20000\n",
        ));
      }

      throw new Error(`Unhandled fetch URL in export page test: ${url}`);
    });

    renderExportRoute();

    expect(await screen.findByRole("heading", { name: "导出任务页面" })).toBeInTheDocument();
    expect(await screen.findByText(/failed to read encrypted material PDF/)).toBeInTheDocument();

    const summaryCard = screen.getByRole("heading", { name: "报销汇总表" }).closest("article");
    expect(summaryCard).not.toBeNull();
    const summaryActions = within(summaryCard as HTMLElement);

    await act(async () => {
      fireEvent.click(summaryActions.getByRole("button", { name: "创建报销汇总表任务" }));
      await Promise.resolve();
    });

    expect(
      await screen.findByText("报销汇总表 导出任务已创建，当前状态：待生成。"),
    ).toBeInTheDocument();
    expect(screen.getByText("export-job-summary")).toBeInTheDocument();

    const refreshedSummaryCard = screen.getByRole("heading", { name: "报销汇总表" }).closest("article");
    expect(refreshedSummaryCard).not.toBeNull();
    const refreshedSummaryActions = within(refreshedSummaryCard as HTMLElement);

    await act(async () => {
      fireEvent.click(refreshedSummaryActions.getByRole("button", { name: "查看在线预览" }));
      await Promise.resolve();
    });

    expect(await screen.findByRole("heading", { name: "报销汇总表 即时输出" })).toBeInTheDocument();
    expect(screen.getByText(/expense_type,total_amount_cents,2250001/)).toBeInTheDocument();
  });

  it("shows blocking reasons and disables export creation before final confirmation", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((input: string | URL | Request, init?: RequestInit) => {
      const url = resolveRequestUrl(input);

      if (url === "/api/tasks/TASK-BLOCKED") {
        return Promise.resolve(jsonResponse(buildTask("TASK-BLOCKED", "reviewing")));
      }

      if (url === "/api/tasks/TASK-BLOCKED/exports/capabilities?actor_id=admin-1") {
        return Promise.resolve(jsonResponse(buildCapabilities("TASK-BLOCKED", false)));
      }

      if (url === "/api/tasks/TASK-BLOCKED/exports?actor_id=admin-1" && !init?.method) {
        return Promise.resolve(jsonResponse([]));
      }

      throw new Error(`Unhandled fetch URL in blocked export page test: ${url}`);
    });

    renderExportRoute("TASK-BLOCKED");

    expect(await screen.findByText("当前任务尚未满足导出前置条件")).toBeInTheDocument();
    expect(
      screen.getByText("task must be ready_to_export or completed before real exports can be generated"),
    ).toBeInTheDocument();

    const summaryCard = screen.getByRole("heading", { name: "报销汇总表" }).closest("article");
    expect(summaryCard).not.toBeNull();
    const summaryActions = within(summaryCard as HTMLElement);

    expect(summaryActions.getByRole("button", { name: "创建报销汇总表任务" })).toBeDisabled();
    expect(summaryActions.getByRole("button", { name: "查看在线预览" })).toBeDisabled();
    expect(
      screen.getByText("当前还没有导出任务记录。创建任务后，这里会显示状态、失败原因和下载入口占位说明。"),
    ).toBeInTheDocument();
  });
});
