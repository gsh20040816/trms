import { render, screen } from "@testing-library/react";
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

function renderRoute(entry: string) {
  const router = createMemoryRouter(routes, {
    initialEntries: [entry],
  });

  render(<RouterProvider router={router} />);
}

function expectSensitiveConfigNotVisible() {
  expect(screen.queryByText("系统管理员身份")).not.toBeInTheDocument();
  expect(screen.queryByText("赵系统管理员")).not.toBeInTheDocument();
  expect(screen.queryByText("系统配置、渠道配置与全局治理能力。")).not.toBeInTheDocument();
  expect(screen.queryByText(/access token/i)).not.toBeInTheDocument();
  expect(screen.queryByText(/refresh token/i)).not.toBeInTheDocument();
  expect(screen.queryByText(/cookie/i)).not.toBeInTheDocument();
  expect(screen.queryByText("VITE_API_BASE_URL")).not.toBeInTheDocument();
}

describe("front-end permission visibility", () => {
  beforeEach(() => {
    clearMockSession();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    clearMockSession();
  });

  it("does not render admin operations on member pages", async () => {
    setMockSession("member");

    vi.spyOn(globalThis, "fetch").mockImplementation((input: string | URL | Request) => {
      const url = resolveRequestUrl(input);

      if (url === "/api/tasks") {
        return Promise.resolve(jsonResponse([
          {
            id: "TASK-OPEN",
            status: "open",
            competition_name: "ICPC Xi'an Regional",
            competition_location: "西安",
            competition_start_date: "2026-05-01",
            competition_end_date: "2026-05-03",
            deadline: "2026-05-10T12:00:00+08:00",
            member_ids: ["2250001", "2250002"],
            fee_categories: ["railway", "hotel"],
            administrator_id: "admin-1",
            project_info: "ACM 竞赛项目",
            reimburser_info: "张管理员",
            invoice_title: "同济大学",
            tax_number: "91310113666007253C",
            created_at: "2026-04-28T08:00:00+08:00",
            updated_at: "2026-04-28T08:00:00+08:00",
          },
        ]));
      }

      throw new Error(`Unhandled fetch URL in permission visibility test: ${url}`);
    });

    renderRoute("/member");

    expect(await screen.findByRole("heading", { name: "成员可提交任务" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "上传材料" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "创建新任务" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "录入或更正发票" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "进入复核总览" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "进入导出管理" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "编辑费用分摊" })).not.toBeInTheDocument();
  });

  it("blocks member access to admin routes before any admin data is requested", async () => {
    setMockSession("member");

    const fetchSpy = vi.spyOn(globalThis, "fetch");

    renderRoute("/admin/tasks/TASK-SECRET");

    expect(await screen.findByRole("heading", { name: "管理员后台 暂不可访问" })).toBeInTheDocument();
    expect(screen.getByText("当前登录身份不匹配；此入口仅允许管理员身份访问。")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "录入或更正发票" })).not.toBeInTheDocument();
    expect(screen.queryByText("TASK-SECRET")).not.toBeInTheDocument();
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("shows the member loading state without rendering admin actions", () => {
    setMockSession("member");

    vi.spyOn(globalThis, "fetch").mockImplementation(
      () => new Promise<Response>(() => {}),
    );

    renderRoute("/member");

    expect(screen.getByRole("heading", { name: "正在加载成员可见任务" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "创建新任务" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "进入导出管理" })).not.toBeInTheDocument();
  });

  it("keeps unrelated long-lived credentials and system config out of admin pages", async () => {
    setMockSession("admin");

    vi.spyOn(globalThis, "fetch").mockImplementation((input: string | URL | Request) => {
      const url = resolveRequestUrl(input);

      if (url === "/api/tasks") {
        return Promise.resolve(jsonResponse([]));
      }

      throw new Error(`Unhandled fetch URL in permission visibility test: ${url}`);
    });

    renderRoute("/admin");

    expect(await screen.findByRole("heading", { name: "当前管理员名下还没有任务" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "创建新任务" })).toBeInTheDocument();
    expectSensitiveConfigNotVisible();
  });

  it("preserves the admin error state without exposing sensitive config", async () => {
    setMockSession("admin");

    vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse(
      {
        detail: "task list is temporarily unavailable",
      },
      {
        status: 503,
      },
    ));

    renderRoute("/admin");

    expect(await screen.findByRole("heading", { name: "接口请求失败" })).toBeInTheDocument();
    expect(screen.getByText("task list is temporarily unavailable")).toBeInTheDocument();
    expectSensitiveConfigNotVisible();
  });
});
