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

describe("TelegramBindingPage", () => {
  beforeEach(() => {
    clearMockSession();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    clearMockSession();
  });

  it("loads the authorization and confirms the binding for the current account", async () => {
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

      if (url === "/api/telegram-bindings/oauth/token-123" && method === "GET") {
        return Promise.resolve(jsonResponse({
          item: {
            telegram_user_id: 123456789,
            telegram_chat_id: 123456789,
            telegram_username: "tongjicoder",
            expires_at: "2099-01-01T00:00:00Z",
            consumed_at: null,
            status: "pending",
          },
        }));
      }
      if (url === "/api/telegram-bindings/oauth/token-123/confirm" && method === "POST") {
        return Promise.resolve(jsonResponse({
          item: {
            id: "binding-1",
            telegram_user_id: 123456789,
            member_id: "2250001",
            telegram_username: "tongjicoder",
            created_at: "2026-05-03T15:00:00Z",
            updated_at: "2026-05-03T15:00:00Z",
          },
        }));
      }

      throw new Error(`Unhandled request ${method} ${url}`);
    });

    const router = createMemoryRouter(routes, {
      initialEntries: ["/telegram/bind?token=token-123"],
    });

    render(<RouterProvider router={router} />);

    expect(await screen.findByRole("heading", { name: "绑定 Telegram 账号" })).toBeInTheDocument();
    expect(await screen.findByText(/@tongjicoder/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "确认绑定当前账号" }));

    expect(await screen.findByText("这个 Telegram 账号已经绑定完成，可以回到 Telegram 继续操作。")).toBeInTheDocument();

    const confirmRequest = fetchSpy.mock.calls.find(([input, init]) => (
      resolveRequestUrl(input) === "/api/telegram-bindings/oauth/token-123/confirm"
      && resolveRequestMethod(input, init) === "POST"
    ));
    expect(confirmRequest).toBeDefined();
  });
});
