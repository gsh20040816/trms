import { fireEvent, render, screen, within } from "@testing-library/react";
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

function renderAdminTaskDetailRoute(taskId = "TASK-ALPHA") {
  const router = createMemoryRouter(routes, {
    initialEntries: [`/admin/tasks/${taskId}`],
  });

  render(<RouterProvider router={router} />);
}

describe("admin task detail page", () => {
  beforeEach(() => {
    clearMockSession();
    setMockSession("admin");
  });

  afterEach(() => {
    vi.restoreAllMocks();
    clearMockSession();
  });

  it("renders task details, members, fee categories and allowed transitions", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((input: string | URL | Request) => {
      const url = resolveRequestUrl(input);

      if (url === "/api/tasks/TASK-ALPHA") {
        return Promise.resolve(jsonResponse({
          id: "TASK-ALPHA",
          status: "closed",
          competition_name: "全国邀请赛",
          competition_location: "上海",
          competition_start_date: "2026-05-01",
          competition_end_date: "2026-05-03",
          deadline: "2026-05-10T18:00:00+08:00",
          member_ids: ["2250001", "2250002"],
          fee_categories: ["registration", "hotel"],
          administrator_id: "admin-1",
          project_info: "Project A",
          reimburser_info: "张管理员",
          invoice_title: "同济大学",
          tax_number: "91310000TEST00001",
          created_at: "2026-04-20T09:00:00+08:00",
          updated_at: "2026-04-25T10:00:00+08:00",
        }));
      }

      throw new Error(`Unhandled fetch URL in detail test: ${url}`);
    });

    renderAdminTaskDetailRoute();

    expect(await screen.findByRole("heading", { name: "任务详情与状态操作" })).toBeInTheDocument();
    expect(screen.getAllByText("全国邀请赛").length).toBeGreaterThan(0);
    expect(screen.getByText("Project A")).toBeInTheDocument();
    expect(screen.getAllByText("张管理员").length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText("同济大学")).toBeInTheDocument();
    expect(screen.getByText("91310000TEST00001")).toBeInTheDocument();
    const moduleNav = screen.getByLabelText("管理员模块导航");
    expect(within(moduleNav).getByText("任务管理").closest("a")).toHaveAttribute("aria-current", "page");
    expect(screen.getByLabelText("当前任务上下文")).toHaveTextContent("全国邀请赛");
    expect(screen.getByRole("link", { name: "录入或更正发票" })).toHaveAttribute(
      "href",
      "/admin/tasks/TASK-ALPHA/invoices",
    );
    expect(screen.getByRole("link", { name: "查看缺失材料" })).toHaveAttribute(
      "href",
      "/admin/tasks/TASK-ALPHA/missing-materials",
    );
    const quickActions = screen.getByLabelText("当前任务快捷入口");
    expect(within(quickActions).getByText("材料审核").closest("a")).toHaveAttribute(
      "href",
      "/admin/tasks/TASK-ALPHA/review",
    );
    expect(within(quickActions).getByText("导出打印").closest("a")).toHaveAttribute(
      "href",
      "/admin/tasks/TASK-ALPHA/exports",
    );
    expect(within(quickActions).getByText("分摊确认").closest("a")).toHaveAttribute(
      "href",
      "/admin/tasks/TASK-ALPHA/splits",
    );

    const members = within(screen.getByLabelText("任务成员名单"));
    expect(members.getByText("成员 2250001")).toBeInTheDocument();
    expect(members.getByText("成员 2250002")).toBeInTheDocument();

    const categories = within(screen.getByLabelText("任务费用类别"));
    expect(categories.getByText("参赛费")).toBeInTheDocument();
    expect(categories.getByText("住宿费")).toBeInTheDocument();

    expect(screen.getByRole("button", { name: "切换为收集中" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "切换为待复核" })).toBeInTheDocument();
  });

  it("updates task status when the backend accepts the transition", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((input: string | URL | Request, init?: RequestInit) => {
      const url = resolveRequestUrl(input);

      if (url === "/api/tasks/TASK-DRAFT") {
        return Promise.resolve(jsonResponse({
          id: "TASK-DRAFT",
          status: "draft",
          competition_name: "创建中任务",
          competition_location: "杭州",
          competition_start_date: "2026-06-01",
          competition_end_date: "2026-06-03",
          deadline: "2026-06-10T18:00:00+08:00",
          member_ids: ["2250001"],
          fee_categories: ["registration"],
          administrator_id: "admin-1",
          project_info: "Project Draft",
          reimburser_info: "张管理员",
          invoice_title: "同济大学",
          tax_number: "91310000TEST00001",
          created_at: "2026-04-20T09:00:00+08:00",
          updated_at: "2026-04-25T10:00:00+08:00",
        }));
      }

      if (url === "/api/tasks/TASK-DRAFT/status" && init?.method === "PATCH") {
        expect(init.body).toBe(JSON.stringify({ target_status: "open" }));
        return Promise.resolve(jsonResponse({
          id: "TASK-DRAFT",
          status: "open",
          competition_name: "创建中任务",
          competition_location: "杭州",
          competition_start_date: "2026-06-01",
          competition_end_date: "2026-06-03",
          deadline: "2026-06-10T18:00:00+08:00",
          member_ids: ["2250001"],
          fee_categories: ["registration"],
          administrator_id: "admin-1",
          project_info: "Project Draft",
          reimburser_info: "张管理员",
          invoice_title: "同济大学",
          tax_number: "91310000TEST00001",
          created_at: "2026-04-20T09:00:00+08:00",
          updated_at: "2026-04-26T10:00:00+08:00",
        }));
      }

      throw new Error(`Unhandled fetch URL in detail status test: ${url}`);
    });

    renderAdminTaskDetailRoute("TASK-DRAFT");

    const openButton = await screen.findByRole("button", { name: "切换为收集中" });
    fireEvent.click(openButton);

    expect(await screen.findByText("当前状态：收集中")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "切换为草稿" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "切换为已截止" })).toBeInTheDocument();
  });

  it("shows a page-level error when the backend rejects a status transition", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((input: string | URL | Request, init?: RequestInit) => {
      const url = resolveRequestUrl(input);

      if (url === "/api/tasks/TASK-READY") {
        return Promise.resolve(jsonResponse({
          id: "TASK-READY",
          status: "ready_to_export",
          competition_name: "待导出任务",
          competition_location: "南京",
          competition_start_date: "2026-07-01",
          competition_end_date: "2026-07-03",
          deadline: "2026-07-10T18:00:00+08:00",
          member_ids: ["2250001", "2250002"],
          fee_categories: ["registration", "hotel"],
          administrator_id: "admin-1",
          project_info: "Project Ready",
          reimburser_info: "张管理员",
          invoice_title: "同济大学",
          tax_number: "91310000TEST00001",
          created_at: "2026-04-20T09:00:00+08:00",
          updated_at: "2026-04-25T10:00:00+08:00",
        }));
      }

      if (url === "/api/tasks/TASK-READY/status" && init?.method === "PATCH") {
        return Promise.resolve(jsonResponse(
          {
            detail: "task cannot transition to completed before export completion is recorded",
          },
          { status: 409 },
        ));
      }

      throw new Error(`Unhandled fetch URL in detail rejection test: ${url}`);
    });

    renderAdminTaskDetailRoute("TASK-READY");

    fireEvent.click(await screen.findByRole("button", { name: "切换为已完成" }));

    expect(await screen.findByRole("heading", { name: "操作未完成" })).toBeInTheDocument();
    expect(screen.getByText("当前操作未完成，请检查填写内容后重试。")).toBeInTheDocument();
  });
});
