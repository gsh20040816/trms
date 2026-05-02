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

function renderAdminRoute() {
  const router = createMemoryRouter(routes, {
    initialEntries: ["/admin"],
  });

  render(<RouterProvider router={router} />);
}

function mockAdminTaskEndpoints() {
  return vi.spyOn(globalThis, "fetch").mockImplementation((input: string | URL | Request) => {
    const url = resolveRequestUrl(input);

    if (url === "/api/tasks") {
      return Promise.resolve(jsonResponse([
        {
          id: "TASK-ALPHA",
          status: "reviewing",
          competition_name: "全国邀请赛",
          competition_location: "上海",
          competition_start_date: "2026-05-01",
          competition_end_date: "2026-05-03",
          deadline: "2026-05-10T18:00:00+08:00",
          member_ids: ["2250001", "2250002"],
          fee_categories: ["registration", "hotel"],
          administrator_id: "admin-1",
          administrator_ids: ["admin-1", "admin-2"],
          project_info: "Project A",
          reimburser_info: "张管理员",
          invoice_title: "同济大学",
          tax_number: "91310000TEST00001",
          created_at: "2026-04-20T09:00:00+08:00",
          updated_at: "2026-04-25T10:00:00+08:00",
        },
        {
          id: "TASK-BETA",
          status: "open",
          competition_name: "区域赛报销",
          competition_location: "杭州",
          competition_start_date: "2026-06-08",
          competition_end_date: "2026-06-10",
          deadline: "2026-06-15T20:00:00+08:00",
          member_ids: ["2250001"],
          fee_categories: ["registration"],
          administrator_id: "admin-1",
          administrator_ids: ["admin-1"],
          project_info: "Project B",
          reimburser_info: "张管理员",
          invoice_title: "同济大学",
          tax_number: "91310000TEST00001",
          created_at: "2026-04-22T09:00:00+08:00",
          updated_at: "2026-04-24T10:00:00+08:00",
        },
      ]));
    }

    if (url === "/api/tasks/TASK-ALPHA/review-summary?actor_id=admin-1") {
      return Promise.resolve(jsonResponse({
        task_id: "TASK-ALPHA",
        administrator_id: "admin-1",
        counts: {
          material_count: 5,
          invoice_count: 2,
          validation_count: 6,
          blocker_failed_validation_count: 2,
          split_count: 3,
          confirmed_split_count: 1,
          pending_confirmation_count: 1,
          disputed_confirmation_count: 1,
          missing_confirmation_count: 0,
          pending_recognition_count: 0,
          failed_recognition_count: 1,
          needs_confirmation_recognition_count: 1,
        },
      }));
    }

    if (url === "/api/tasks/TASK-BETA/review-summary?actor_id=admin-1") {
      return Promise.resolve(jsonResponse({
        task_id: "TASK-BETA",
        administrator_id: "admin-1",
        counts: {
          material_count: 1,
          invoice_count: 0,
          validation_count: 0,
          blocker_failed_validation_count: 0,
          split_count: 0,
          confirmed_split_count: 0,
          pending_confirmation_count: 0,
          disputed_confirmation_count: 0,
          missing_confirmation_count: 0,
          pending_recognition_count: 0,
          failed_recognition_count: 0,
          needs_confirmation_recognition_count: 0,
        },
      }));
    }

    if (url === "/api/tasks/TASK-ALPHA/overdue-confirmations?actor_id=admin-1") {
      return Promise.resolve(jsonResponse({
        task_id: "TASK-ALPHA",
        administrator_id: "admin-1",
        confirmation_deadline: "2026-05-10T18:00:00+08:00",
        is_overdue: true,
        total_overdue_members: 2,
        overdue_member_ids: ["2250001", "2250002"],
      }));
    }

    if (url === "/api/tasks/TASK-BETA/overdue-confirmations?actor_id=admin-1") {
      return Promise.resolve(jsonResponse({
        task_id: "TASK-BETA",
        administrator_id: "admin-1",
        confirmation_deadline: "2026-06-15T20:00:00+08:00",
        is_overdue: false,
        total_overdue_members: 0,
        overdue_member_ids: [],
      }));
    }

    throw new Error(`Unhandled fetch URL in test: ${url}`);
  });
}

describe("admin task list page", () => {
  beforeEach(() => {
    clearMockSession();
    setMockSession("admin");
  });

  afterEach(() => {
    vi.restoreAllMocks();
    clearMockSession();
  });

  it("renders admin tasks with anomaly summary, search and status filter", async () => {
    mockAdminTaskEndpoints();

    renderAdminRoute();

    expect(await screen.findByRole("heading", { name: "任务管理" })).toBeInTheDocument();
    expect(screen.getByLabelText("管理员任务概览")).toBeInTheDocument();
    const moduleNav = screen.getByLabelText("管理员模块导航");
    expect(within(moduleNav).getByText("首页总览").closest("a")).toHaveAttribute("aria-current", "page");
    expect(within(moduleNav).getByText("创建任务").closest("a")).toHaveAttribute("href", "/admin/tasks/new");
    expect(within(moduleNav).queryByText("任务管理")).not.toBeInTheDocument();
    expect(within(moduleNav).queryByText("材料审核")).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "建议优先处理的任务" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "进入当前优先任务" })).toHaveAttribute(
      "href",
      "/admin/tasks/TASK-ALPHA/missing-materials",
    );
    expect(screen.getByLabelText("当前优先任务提醒")).toHaveTextContent("项材料或校验待补齐");
    expect(screen.getAllByText("全国邀请赛").length).toBeGreaterThan(0);
    expect(screen.getAllByText("区域赛报销").length).toBeGreaterThan(0);
    expect(screen.getByRole("link", { name: "补材料" })).toBeInTheDocument();
    expect(screen.getAllByText("上海 · 2 名管理员").length).toBeGreaterThan(0);

    await act(async () => {
      fireEvent.change(screen.getByRole("searchbox", { name: "搜索任务" }), {
        target: { value: "区域赛" },
      });
      await Promise.resolve();
    });

    expect(await screen.findAllByText("区域赛报销")).not.toHaveLength(0);
    expect(screen.queryByText("全国邀请赛")).not.toBeInTheDocument();

    await act(async () => {
      fireEvent.change(screen.getByRole("searchbox", { name: "搜索任务" }), {
        target: { value: "" },
      });
      await Promise.resolve();
    });
    await act(async () => {
      fireEvent.change(screen.getByRole("combobox", { name: "任务状态" }), {
        target: { value: "reviewing" },
      });
      await Promise.resolve();
    });

    expect(await screen.findAllByText("全国邀请赛")).not.toHaveLength(0);
    expect(screen.queryByText("区域赛报销")).not.toBeInTheDocument();
  });

  it("shows a loading state while requests are still pending", () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(
      () => new Promise<Response>(() => {}),
    );

    renderAdminRoute();

    expect(screen.getByRole("heading", { name: "正在加载任务列表" })).toBeInTheDocument();
  });

  it("shows an empty state when the current admin has no matching tasks", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse([
        {
          id: "TASK-OTHER",
          status: "open",
          competition_name: "其他管理员任务",
          competition_location: "南京",
          competition_start_date: "2026-05-01",
          competition_end_date: "2026-05-02",
          deadline: "2026-05-06T18:00:00+08:00",
          member_ids: ["2250001"],
          fee_categories: ["registration"],
          administrator_id: "admin-2",
          administrator_ids: ["admin-2"],
          project_info: "Project C",
          reimburser_info: "李管理员",
          invoice_title: "同济大学",
          tax_number: "91310000TEST00002",
          created_at: "2026-04-20T09:00:00+08:00",
          updated_at: "2026-04-20T09:00:00+08:00",
        },
      ]),
    );

    renderAdminRoute();

    expect(await screen.findByRole("heading", { name: "当前管理员名下还没有任务" })).toBeInTheDocument();
  });

  it("shows a page-level error when task loading fails", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse(
        {
          detail: "task list is temporarily unavailable",
        },
        {
          status: 503,
        },
      ),
    );

    renderAdminRoute();

    expect(await screen.findByRole("heading", { name: "操作未完成" })).toBeInTheDocument();
    expect(screen.getByText("系统暂时不可用，请稍后再试。")).toBeInTheDocument();
  });
});
