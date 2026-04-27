import { fireEvent, render, screen } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";

import { clearMockSession, setMockSession } from "./auth-store";
import { routes } from "./routes";

describe("web app auth placeholder", () => {
  beforeEach(() => {
    clearMockSession();
  });

  it("renders role entry cards on the home page", () => {
    const router = createMemoryRouter(routes, {
      initialEntries: ["/"],
    });

    render(<RouterProvider router={router} />);

    expect(screen.getByRole("heading", { name: "报销收集前端入口与登录占位已建立" })).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: "登录后进入" })).toHaveLength(3);
    expect(screen.getByText("管理员后台")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "登录与角色入口边界已固定" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "前端 API 类型与错误边界已建立" })).toBeInTheDocument();
    expect(screen.getByText("统一解析 detail/message/字段校验错误，不在前端静默吞掉")).toBeInTheDocument();
  });

  it("redirects unauthenticated users to the mock login page", () => {
    const router = createMemoryRouter(routes, {
      initialEntries: ["/admin"],
    });

    render(<RouterProvider router={router} />);

    expect(screen.getByRole("heading", { name: "登录占位" })).toBeInTheDocument();
    expect(screen.getByText("检测到未登录访问，原请求入口：/admin")).toBeInTheDocument();
  });

  it("allows entering the requested route with a mock admin session", async () => {
    const router = createMemoryRouter(routes, {
      initialEntries: ["/login?next=%2Fadmin"],
    });

    render(<RouterProvider router={router} />);

    fireEvent.click(screen.getByRole("button", { name: "以管理员身份进入" }));

    expect(await screen.findByRole("heading", { name: "管理员后台" })).toBeInTheDocument();
    expect(
      await screen.findByText(
        "当前以 mock 身份 张管理员 进入。此页只固化登录态与角色入口边界，真实业务内容将在后续任务补齐。",
      ),
    ).toBeInTheDocument();
  });

  it("shows a role mismatch placeholder for the wrong logged-in role", () => {
    setMockSession("member");

    const router = createMemoryRouter(routes, {
      initialEntries: ["/system"],
    });

    render(<RouterProvider router={router} />);

    expect(screen.getByRole("heading", { name: "系统管理 暂不可访问" })).toBeInTheDocument();
    expect(screen.getByText("当前 mock 身份为 成员身份 / 王队员（MEM-001）。")).toBeInTheDocument();
  });
});
