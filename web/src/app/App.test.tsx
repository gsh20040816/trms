import { fireEvent, render, screen } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";

import { MockLoginPage } from "./auth";
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

    expect(screen.getByRole("heading", { name: "登录后进入对应工作台" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "前往登录 / 注册" })).toBeInTheDocument();
    expect(screen.getByText("材料与确认")).toBeInTheDocument();
    expect(screen.queryByText("报销成员")).not.toBeInTheDocument();
    expect(screen.queryByText("管理员")).not.toBeInTheDocument();
  });

  it("redirects unauthenticated users to the account login page", () => {
    const router = createMemoryRouter(routes, {
      initialEntries: ["/admin"],
    });

    render(<RouterProvider router={router} />);

    expect(screen.getByRole("heading", { name: "账号登录与注册" })).toBeInTheDocument();
    expect(screen.getByText("检测到你需要先登录，登录后会自动返回原页面。")).toBeInTheDocument();
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
            roles: ["admin"],
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
    fireEvent.change(screen.getByLabelText("身份编号"), { target: { value: "admin-1" } });
    fireEvent.click(screen.getByRole("button", { name: "注册并登录" }));

    expect(await screen.findByRole("heading", { name: "按任务推进处理当前工作" })).toBeInTheDocument();
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

    fireEvent.click(screen.getByRole("button", { name: "以成员进入" }));

    expect(await screen.findByRole("heading", { name: "我的报销任务" })).toBeInTheDocument();
    expect(await screen.findByText("当前没有可见报销任务")).toBeInTheDocument();
  });

  it("hides dev role entries and privileged self-registration when auth ui config disables them", () => {
    const router = createMemoryRouter(
      [
        {
          path: "/login",
          element: (
            <MockLoginPage
              uiConfig={{
                enableDevRoleEntries: false,
                allowPrivilegedSelfRegistration: false,
              }}
            />
          ),
        },
      ],
      {
        initialEntries: ["/login"],
      },
    );

    render(<RouterProvider router={router} />);

    fireEvent.click(screen.getByRole("button", { name: "注册" }));

    expect(screen.queryByLabelText("角色")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("开发调试角色入口")).not.toBeInTheDocument();
    expect(
      screen.getByText("当前环境仅开放成员自注册；管理员与系统管理员账号必须通过受控初始化或后续邀请/审批流程创建。"),
    ).toBeInTheDocument();
  });

  it("shows a role mismatch placeholder for the wrong logged-in role", () => {
    setMockSession("member");

    const router = createMemoryRouter(routes, {
      initialEntries: ["/system"],
    });

    render(<RouterProvider router={router} />);

    expect(screen.getByRole("heading", { name: "系统管理 暂不可访问" })).toBeInTheDocument();
    expect(screen.getByText("当前身份为 成员 / 王队员（MEM-001）。")).toBeInTheDocument();
  });

  it("switches to another bound role when entering its workspace", async () => {
    setMockSession("member", ["member", "system_admin"]);

    const router = createMemoryRouter(routes, {
      initialEntries: ["/system"],
    });

    render(<RouterProvider router={router} />);

    expect(await screen.findByRole("heading", { name: "系统管理员工作台" })).toBeInTheDocument();
    expect(screen.getByText("这里集中处理账号、角色、全局配置和运行状态。普通报销任务入口不会显示技术诊断信息。")).toBeInTheDocument();
  });

  it("shows only the current member workspace on the logged-in home page", () => {
    setMockSession("member");

    const router = createMemoryRouter(routes, {
      initialEntries: ["/"],
    });

    render(<RouterProvider router={router} />);

    expect(screen.getByRole("heading", { name: "Tongji ACM 报销管理系统" })).toBeInTheDocument();
    expect(screen.getByText("登录后只展示当前账号可进入的工作台，不再把其他角色的业务板块混在首页。")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "进入我的工作台" })).toBeInTheDocument();
    expect(screen.getAllByText("报销成员").length).toBeGreaterThan(0);
    expect(screen.queryByText("管理员")).not.toBeInTheDocument();
    expect(screen.queryByText("系统管理员")).not.toBeInTheDocument();
  });
});
