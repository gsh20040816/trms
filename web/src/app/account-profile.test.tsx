import { fireEvent, render, screen } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";

import { clearMockSession, setMockSession } from "./auth-store";
import { routes } from "./routes";

function jsonResponse(body: unknown, init: ResponseInit = {}) {
  return new Response(JSON.stringify(body), {
    status: init.status ?? 200,
    headers: { "Content-Type": "application/json" },
  });
}

function resolveRequestUrl(input: string | URL | Request) {
  return typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;
}

function resolveRequestMethod(input: string | URL | Request, init: RequestInit | undefined) {
  return init?.method?.toUpperCase() ?? (input instanceof Request ? input.method.toUpperCase() : "GET");
}

describe("AccountProfilePage", () => {
  beforeEach(() => {
    clearMockSession();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    clearMockSession();
  });

  it("allows a member to update display name and member code", async () => {
    setMockSession("member", {
      actorId: "2250001",
      displayName: "王队员",
      memberCode: "2250001",
      username: "member1",
      accessToken: "token-member",
    });

    vi.spyOn(globalThis, "fetch").mockImplementation((input: string | URL | Request, init?: RequestInit) => {
      const url = resolveRequestUrl(input);
      const method = resolveRequestMethod(input, init);

      if (url === "/api/email-bindings" && method === "GET") {
        return Promise.resolve(jsonResponse({
          items: [
            {
              id: "email-binding-existing",
              member_id: "2250001",
              email: "backup.member1@tongji.edu.cn",
              created_at: "2026-05-03T08:00:00Z",
              updated_at: "2026-05-03T08:00:00Z",
            },
          ],
        }));
      }
      if (url === "/api/auth/me" && method === "PUT") {
        return Promise.resolve(jsonResponse({
          id: "user-member",
          username: "member1",
          role: "member",
          roles: ["member"],
          actor_id: "2250001",
          display_name: "新名字",
          member_code: "2250999",
          created_at: "2026-04-28T00:00:00Z",
          updated_at: "2026-05-02T22:40:00Z",
        }));
      }
      if (url === "/api/auth/me/password" && method === "PUT") {
        return Promise.resolve(new Response(null, { status: 204 }));
      }

      throw new Error(`Unhandled request ${method} ${url}`);
    });

    const router = createMemoryRouter(routes, {
      initialEntries: ["/profile"],
    });

    render(<RouterProvider router={router} />);

    expect(await screen.findByRole("heading", { name: "个人信息" })).toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: "绑定邮箱" })).toBeInTheDocument();
    fireEvent.change(await screen.findByDisplayValue("王队员"), { target: { value: "新名字" } });
    fireEvent.change(await screen.findByDisplayValue("2250001"), { target: { value: "2250999" } });
    fireEvent.click(await screen.findByRole("button", { name: "保存个人信息" }));

    expect(await screen.findByDisplayValue("新名字")).toBeInTheDocument();
    expect(screen.getByDisplayValue("2250999")).toBeInTheDocument();

    fireEvent.change(await screen.findByLabelText(/当前密码/), { target: { value: "old-password" } });
    fireEvent.change(await screen.findByLabelText(/^新密码$/), { target: { value: "new-password-123" } });
    fireEvent.change(await screen.findByLabelText(/^确认新密码$/), { target: { value: "new-password-123" } });
    fireEvent.click(await screen.findByRole("button", { name: "修改密码" }));

    expect(await screen.findByRole("button", { name: "修改密码" })).toBeInTheDocument();
  });

  it("hides member code editing for non-member accounts", async () => {
    setMockSession("admin", {
      actorId: "admin-1",
      displayName: "张管理员",
      memberCode: null,
      username: "admin1",
      accessToken: "token-admin",
    });

    const router = createMemoryRouter(routes, {
      initialEntries: ["/profile"],
    });

    render(<RouterProvider router={router} />);

    expect(await screen.findByRole("heading", { name: "个人信息" })).toBeInTheDocument();
    expect(screen.queryByLabelText("学号")).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "绑定邮箱" })).not.toBeInTheDocument();
  });

  it("allows a member to bind an email address with a verification code", async () => {
    setMockSession("member", {
      actorId: "2250001",
      displayName: "王队员",
      memberCode: "2250001",
      username: "member1",
      accessToken: "token-member",
    });

    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation((input: string | URL | Request, init?: RequestInit) => {
      const url = resolveRequestUrl(input);
      const method = resolveRequestMethod(input, init);

      if (url === "/api/email-bindings" && method === "GET") {
        return Promise.resolve(jsonResponse({
          items: [
            {
              id: "email-binding-existing",
              member_id: "2250001",
              email: "backup.member1@tongji.edu.cn",
              created_at: "2026-05-03T08:00:00Z",
              updated_at: "2026-05-03T08:00:00Z",
            },
          ],
        }));
      }
      if (url === "/api/email-bindings/verification-code" && method === "POST") {
        return Promise.resolve(jsonResponse({
          item: {
            email: "member1@tongji.edu.cn",
            expires_at: "2026-05-03T09:10:00Z",
          },
        }, { status: 202 }));
      }
      if (url === "/api/email-bindings/verify" && method === "POST") {
        return Promise.resolve(jsonResponse({
          item: {
            id: "email-binding-1",
            member_id: "2250001",
            email: "member1@tongji.edu.cn",
            created_at: "2026-05-03T09:00:00Z",
            updated_at: "2026-05-03T09:00:00Z",
          },
        }));
      }

      throw new Error(`Unhandled request ${method} ${url}`);
    });

    const router = createMemoryRouter(routes, {
      initialEntries: ["/profile"],
    });

    render(<RouterProvider router={router} />);

    expect(await screen.findByRole("heading", { name: "绑定邮箱" })).toBeInTheDocument();
    expect(await screen.findByText("backup.member1@tongji.edu.cn")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("邮箱地址"), {
      target: { value: "Member1@Tongji.edu.cn" },
    });
    fireEvent.click(screen.getByRole("button", { name: "发送验证码" }));

    expect(await screen.findByText("验证码已发送至 member1@tongji.edu.cn")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("验证码"), {
      target: { value: "123456" },
    });
    fireEvent.click(screen.getByRole("button", { name: "完成绑定" }));

    expect(await screen.findByText("member1@tongji.edu.cn")).toBeInTheDocument();
    expect(screen.getByText("backup.member1@tongji.edu.cn")).toBeInTheDocument();

    const codeRequest = fetchSpy.mock.calls.find(([input, init]) => (
      resolveRequestUrl(input) === "/api/email-bindings/verification-code"
      && resolveRequestMethod(input, init) === "POST"
    ));
    expect(codeRequest?.[1]?.body).toBe(JSON.stringify({ email: "member1@tongji.edu.cn" }));

    const verifyRequest = fetchSpy.mock.calls.find(([input, init]) => (
      resolveRequestUrl(input) === "/api/email-bindings/verify"
      && resolveRequestMethod(input, init) === "POST"
    ));
    expect(verifyRequest?.[1]?.body).toBe(JSON.stringify({
      email: "member1@tongji.edu.cn",
      code: "123456",
    }));
  });

  it("blocks password save when the new passwords do not match", async () => {
    setMockSession("member", {
      actorId: "2250001",
      displayName: "王队员",
      memberCode: "2250001",
      username: "member1",
      accessToken: "token-member",
    });

    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation((input: string | URL | Request, init?: RequestInit) => {
      const url = resolveRequestUrl(input);
      const method = resolveRequestMethod(input, init);

      if (url === "/api/email-bindings" && method === "GET") {
        return Promise.resolve(jsonResponse({ items: [] }));
      }

      throw new Error(`Unhandled request ${method} ${url}`);
    });
    const router = createMemoryRouter(routes, {
      initialEntries: ["/profile"],
    });

    render(<RouterProvider router={router} />);

    expect(await screen.findByRole("heading", { name: "个人信息" })).toBeInTheDocument();
    fireEvent.change(await screen.findByLabelText(/当前密码/), { target: { value: "old-password" } });
    fireEvent.change(await screen.findByLabelText(/^新密码$/), { target: { value: "new-password-123" } });
    fireEvent.change(await screen.findByLabelText(/^确认新密码$/), { target: { value: "new-password-456" } });
    fireEvent.click(await screen.findByRole("button", { name: "修改密码" }));

    const passwordRequests = fetchSpy.mock.calls.filter(([input, init]) => (
      resolveRequestUrl(input) === "/api/auth/me/password"
      && resolveRequestMethod(input, init) === "PUT"
    ));
    expect(passwordRequests).toHaveLength(0);
  });
});
