import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
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
    note: "reimbursement summary/member details/invoice details/missing materials CSV export and finance draft JSON export and merged PDF export are available through async export jobs with persisted artifacts",
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
        implemented: true,
        implemented_formats: ["pdf"],
      },
      {
        kind: "reimbursement_package",
        formats: ["zip"],
        implemented: true,
        implemented_formats: ["zip"],
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
    let createJobRequestCount = 0;

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
            retry_count: 0,
            artifact: null,
          },
          {
            id: "export-job-csv",
            task_id: "TASK-EXPORT",
            requested_by: "admin-1",
            kind: "invoice_details",
            format: "csv",
            status: "succeeded",
            parameters: {},
            task_status_at_request: "ready_to_export",
            task_data_version: "c".repeat(64),
            is_latest_for_task: true,
            failure_reason: null,
            created_at: "2026-04-28T08:40:00+08:00",
            updated_at: "2026-04-28T08:41:00+08:00",
            started_at: "2026-04-28T08:40:10+08:00",
            finished_at: "2026-04-28T08:41:00+08:00",
            retry_count: 0,
            artifact: {
              filename: "TASK-EXPORT-invoice-details.csv",
              content_type: "text/csv",
              size_bytes: 321,
              sha256: "d".repeat(64),
            },
          },
        ]));
      }

      if (url === "/api/tasks/TASK-EXPORT/exports" && init?.method === "POST") {
        createJobRequestCount += 1;
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
            retry_count: 0,
            artifact: null,
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

    expect(await screen.findByRole("heading", { name: "导出与下载" })).toBeInTheDocument();
    const moduleNav = screen.getByLabelText("管理员模块导航");
    expect(within(moduleNav).getByText("导出打印").closest("a")).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("heading", { name: "先生成完整材料包" })).toBeInTheDocument();
    expect(screen.getByLabelText("材料包状态摘要")).toHaveTextContent("材料包就绪度");
    expect(await screen.findByText(/failed to read encrypted material PDF/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "下载导出文件" })).toBeInTheDocument();

    const summaryCard = screen.getByRole("heading", { name: "报销汇总表" }).closest("article");
    expect(summaryCard).not.toBeNull();
    const summaryActions = within(summaryCard as HTMLElement);

    await act(async () => {
      fireEvent.click(summaryActions.getByRole("button", { name: "创建报销汇总表任务" }));
      await Promise.resolve();
    });
    const confirmDialog = await screen.findByRole("dialog");
    expect(within(confirmDialog).getByText("任务 ICPC 区域赛报销 当前处于可导出。确认后，系统会按当前数据版本创建一个 XLSX 导出任务并放入后台队列。")).toBeInTheDocument();
    await act(async () => {
      fireEvent.click(within(confirmDialog).getByRole("button", { name: "暂不创建" }));
      await Promise.resolve();
    });
    await waitFor(() => {
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });

    expect(createJobRequestCount).toBe(0);
    expect(screen.queryByText("报销汇总表已加入导出队列，当前状态：待生成。")).not.toBeInTheDocument();

    await act(async () => {
      fireEvent.click(summaryActions.getByRole("button", { name: "创建报销汇总表任务" }));
      await Promise.resolve();
    });
    const secondConfirmDialog = await screen.findByRole("dialog");
    await act(async () => {
      fireEvent.click(within(secondConfirmDialog).getByRole("button", { name: "创建导出任务" }));
      await Promise.resolve();
    });
    await waitFor(() => {
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });

    expect(
      await screen.findByText("报销汇总表已加入导出队列，当前状态：待生成。"),
    ).toBeInTheDocument();
    expect(createJobRequestCount).toBe(1);
    const exportHistory = within(screen.getByLabelText("导出任务历史列表"));
    expect(exportHistory.getByText(/报销汇总表\s*\/\s*XLSX/)).toBeInTheDocument();
    expect(screen.queryByText("export-job-summary")).not.toBeInTheDocument();

    const refreshedSummaryCard = screen.getByRole("heading", { name: "报销汇总表" }).closest("article");
    expect(refreshedSummaryCard).not.toBeNull();
    const refreshedSummaryActions = within(refreshedSummaryCard as HTMLElement);

    await act(async () => {
      fireEvent.click(refreshedSummaryActions.getByRole("button", { name: "直接查看内容" }));
      await Promise.resolve();
    });

    expect(await screen.findByRole("heading", { name: "报销汇总表 页面查看" })).toBeInTheDocument();
    expect(screen.getByText(/expense_type,total_amount_cents,2250001/)).toBeInTheDocument();
  });

  it("prioritizes reimbursement package generation and shows stale package warning", async () => {
    const createRequests: Array<{ kind: string; format: string }> = [];
    const packageBlob = new Blob(["zip-bytes"], { type: "application/zip" });

    const createObjectUrlSpy = vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:package-download");
    const revokeObjectUrlSpy = vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => {});
    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});

    vi.spyOn(globalThis, "fetch").mockImplementation((input: string | URL | Request, init?: RequestInit) => {
      const url = resolveRequestUrl(input);

      if (url === "/api/tasks/TASK-PACKAGE") {
        return Promise.resolve(jsonResponse(buildTask("TASK-PACKAGE", "ready_to_export")));
      }

      if (url === "/api/tasks/TASK-PACKAGE/exports/capabilities?actor_id=admin-1") {
        return Promise.resolve(jsonResponse(buildCapabilities("TASK-PACKAGE", true)));
      }

      if (url === "/api/tasks/TASK-PACKAGE/exports?actor_id=admin-1" && !init?.method) {
        return Promise.resolve(jsonResponse([
          {
            id: "export-job-package-old",
            task_id: "TASK-PACKAGE",
            requested_by: "admin-1",
            kind: "reimbursement_package",
            format: "zip",
            status: "succeeded",
            parameters: {},
            task_status_at_request: "ready_to_export",
            task_data_version: "e".repeat(64),
            is_latest_for_task: false,
            failure_reason: null,
            created_at: "2026-04-28T09:00:00+08:00",
            updated_at: "2026-04-28T09:08:00+08:00",
            started_at: "2026-04-28T09:00:10+08:00",
            finished_at: "2026-04-28T09:08:00+08:00",
            retry_count: 0,
            artifact: {
              filename: "TASK-PACKAGE-reimbursement-package-old.zip",
              content_type: "application/zip",
              size_bytes: 4096,
              sha256: "f".repeat(64),
            },
          },
          {
            id: "export-job-summary-existing",
            task_id: "TASK-PACKAGE",
            requested_by: "admin-1",
            kind: "reimbursement_summary",
            format: "csv",
            status: "succeeded",
            parameters: {},
            task_status_at_request: "ready_to_export",
            task_data_version: "g".repeat(64),
            is_latest_for_task: true,
            failure_reason: null,
            created_at: "2026-04-27T08:40:00+08:00",
            updated_at: "2026-04-27T08:41:00+08:00",
            started_at: "2026-04-27T08:40:10+08:00",
            finished_at: "2026-04-27T08:41:00+08:00",
            retry_count: 0,
            artifact: {
              filename: "TASK-PACKAGE-summary.csv",
              content_type: "text/csv",
              size_bytes: 321,
              sha256: "h".repeat(64),
            },
          },
        ]));
      }

      if (url === "/api/tasks/TASK-PACKAGE/exports" && init?.method === "POST") {
        if (typeof init.body !== "string") {
          throw new Error("Expected export creation body to be a JSON string");
        }
        const body = JSON.parse(init.body) as { kind: string; format: string };
        createRequests.push({ kind: body.kind, format: body.format });
        return Promise.resolve(jsonResponse(
          {
            id: "export-job-package-new",
            task_id: "TASK-PACKAGE",
            requested_by: "admin-1",
            kind: "reimbursement_package",
            format: "zip",
            status: "pending",
            parameters: {},
            task_status_at_request: "ready_to_export",
            task_data_version: "i".repeat(64),
            is_latest_for_task: true,
            failure_reason: null,
            created_at: "2026-04-28T10:10:00+08:00",
            updated_at: "2026-04-28T10:10:00+08:00",
            started_at: null,
            finished_at: null,
            retry_count: 0,
            artifact: null,
          },
          { status: 201 },
        ));
      }

      if (url === "/api/tasks/exports/export-job-package-old/artifact?actor_id=admin-1") {
        return Promise.resolve(new Response(packageBlob, {
          status: 200,
          headers: {
            "Content-Type": "application/zip",
            "Content-Disposition": "attachment; filename=\"TASK-PACKAGE-reimbursement-package-old.zip\"",
          },
        }));
      }

      throw new Error(`Unhandled fetch URL in reimbursement package export page test: ${url}`);
    });

    renderExportRoute("TASK-PACKAGE");

    expect(await screen.findByText("最近一次完整材料包不是最新版本")).toBeInTheDocument();
    expect(screen.getAllByText("任务数据已更新").length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: "生成完整材料包" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "下载最近完整材料包" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "高级单项导出" })).toBeInTheDocument();
    expect(screen.getByText("仅用于排障或临时下载")).toBeInTheDocument();

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "下载最近完整材料包" }));
      await Promise.resolve();
    });

    await waitFor(() => {
      expect(clickSpy).toHaveBeenCalledTimes(1);
    });
    expect(createObjectUrlSpy).toHaveBeenCalled();
    expect(revokeObjectUrlSpy).toHaveBeenCalled();

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "生成完整材料包" }));
      await Promise.resolve();
    });

    const confirmDialog = await screen.findByRole("dialog");
    expect(within(confirmDialog).getByText(
      "任务 ICPC 区域赛报销 当前处于可导出。确认后，系统会按当前数据版本创建一个 ZIP 导出任务并放入后台队列。",
    )).toBeInTheDocument();
    await act(async () => {
      fireEvent.click(within(confirmDialog).getByRole("button", { name: "创建导出任务" }));
      await Promise.resolve();
    });
    await waitFor(() => {
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });

    expect(createRequests).toEqual([{ kind: "reimbursement_package", format: "zip" }]);
    expect(
      await screen.findByText("完整报销材料包已加入导出队列，当前状态：待生成。"),
    ).toBeInTheDocument();
    const packageHistory = within(screen.getByLabelText("导出任务历史列表"));
    expect(packageHistory.getAllByText(/完整报销材料包\s*\/\s*ZIP/).length).toBe(2);
    expect(screen.queryByText("export-job-package-new")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "创建报销汇总表任务" })).toBeInTheDocument();
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
    expect(summaryActions.getByRole("button", { name: "直接查看内容" })).toBeDisabled();
    expect(
      screen.getByText("当前还没有导出任务记录。创建任务后，会在这里显示状态、失败原因和可下载产物信息。"),
    ).toBeInTheDocument();
  });
});
