import { fireEvent, render, screen } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";

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

describe("web app account auth", () => {
  beforeEach(() => {
    clearMockSession();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders role entry cards on the home page", () => {
    const router = createMemoryRouter(routes, {
      initialEntries: ["/"],
    });

    render(<RouterProvider router={router} />);

    expect(screen.getByRole("heading", { name: "报销收集前端入口与账号登录已建立" })).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: "登录后进入" })).toHaveLength(3);
    expect(screen.getByText("管理员后台")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "账号登录与角色入口边界已固定" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "前端 API 类型与错误边界已建立" })).toBeInTheDocument();
    expect(screen.getByText("统一解析 detail/message/字段校验错误，不在前端静默吞掉")).toBeInTheDocument();
  });

  it("redirects unauthenticated users to the account login page", () => {
    const router = createMemoryRouter(routes, {
      initialEntries: ["/admin"],
    });

    render(<RouterProvider router={router} />);

    expect(screen.getByRole("heading", { name: "账号登录与注册" })).toBeInTheDocument();
    expect(screen.getByText("检测到未登录访问，原请求入口：/admin")).toBeInTheDocument();
  });

  it("allows registering and entering the requested route with an account session", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((input: string | URL | Request) => {
      const url = resolveRequestUrl(input);

      if (url === "/api/auth/register") {
        return Promise.resolve(new Response(JSON.stringify({
          access_token: "token-admin",
          token_type: "bearer",
          user: {
            id: "user-admin",
            username: "admin",
            role: "admin",
            actor_id: "admin-1",
            display_name: "张管理员",
            member_code: null,
            created_at: "2026-04-28T00:00:00Z",
            updated_at: "2026-04-28T00:00:00Z",
          },
        }), {
          status: 201,
          headers: {
            "Content-Type": "application/json",
          },
        }));
      }

      if (url === "/api/tasks") {
        return Promise.resolve(new Response(JSON.stringify([]), {
          status: 200,
          headers: {
            "Content-Type": "application/json",
          },
        }));
      }

      throw new Error(`Unhandled fetch URL in auth test: ${url}`);
    });

    const router = createMemoryRouter(routes, {
      initialEntries: ["/login?next=%2Fadmin"],
    });

    render(<RouterProvider router={router} />);

    fireEvent.click(screen.getByRole("button", { name: "注册" }));
    fireEvent.change(screen.getByLabelText("用户名"), { target: { value: "admin" } });
    fireEvent.change(screen.getByLabelText("密码"), { target: { value: "password123" } });
    fireEvent.change(screen.getByLabelText("角色"), { target: { value: "admin" } });
    fireEvent.change(screen.getByLabelText("显示名称"), { target: { value: "张管理员" } });
    fireEvent.change(screen.getByLabelText("业务身份 ID"), { target: { value: "admin-1" } });
    fireEvent.click(screen.getByRole("button", { name: "注册并登录" }));

    expect(await screen.findByRole("heading", { name: "管理员任务列表" })).toBeInTheDocument();
    expect(
      await screen.findByText("当前管理员名下还没有任务"),
    ).toBeInTheDocument();
  });

  it("allows entering the requested route with a dev member session", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((input: string | URL | Request) => {
      const url = resolveRequestUrl(input);

      if (url === "/api/tasks") {
        return Promise.resolve(new Response(JSON.stringify([]), {
          status: 200,
          headers: {
            "Content-Type": "application/json",
          },
        }));
      }

      throw new Error(`Unhandled fetch URL in auth test: ${url}`);
    });

    const router = createMemoryRouter(routes, {
      initialEntries: ["/login?next=%2Fmember"],
    });

    render(<RouterProvider router={router} />);

    fireEvent.click(screen.getByRole("button", { name: "以成员身份进入" }));

    expect(await screen.findByRole("heading", { name: "成员可提交任务" })).toBeInTheDocument();
    expect(await screen.findByText("当前没有可见报销任务")).toBeInTheDocument();
  });

  it("shows a role mismatch placeholder for the wrong logged-in role", () => {
    setMockSession("member");

    const router = createMemoryRouter(routes, {
      initialEntries: ["/system"],
    });

    render(<RouterProvider router={router} />);

    expect(screen.getByRole("heading", { name: "系统管理 暂不可访问" })).toBeInTheDocument();
    expect(screen.getByText("当前身份为 成员身份 / 王队员（MEM-001）。")).toBeInTheDocument();
  });
});
