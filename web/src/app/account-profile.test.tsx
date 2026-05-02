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

      throw new Error(`Unhandled request ${method} ${url}`);
    });

    const router = createMemoryRouter(routes, {
      initialEntries: ["/profile"],
    });

    render(<RouterProvider router={router} />);

    expect(await screen.findByRole("heading", { name: "个人信息" })).toBeInTheDocument();
    fireEvent.change(await screen.findByDisplayValue("王队员"), { target: { value: "新名字" } });
    fireEvent.change(await screen.findByDisplayValue("2250001"), { target: { value: "2250999" } });
    fireEvent.click(await screen.findByRole("button", { name: "保存个人信息" }));

    expect(await screen.findByDisplayValue("新名字")).toBeInTheDocument();
    expect(screen.getByDisplayValue("2250999")).toBeInTheDocument();
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
  });
});
