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

function renderSystemRoute() {
  const router = createMemoryRouter(routes, {
    initialEntries: ["/system"],
  });

  render(<RouterProvider router={router} />);
}

describe("system admin dashboard page", () => {
  beforeEach(() => {
    clearMockSession();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    clearMockSession();
  });

  it("loads the dashboard and allows saving global invoice config", async () => {
    setMockSession("system_admin");

    vi.spyOn(globalThis, "fetch").mockImplementation((input: string | URL | Request, init?: RequestInit) => {
      const url = resolveRequestUrl(input);

      if (url === "/api/system/dashboard") {
        return Promise.resolve(jsonResponse({
          service_health: "ok",
          global_invoice_config: {
            invoice_title: "同济大学 ACM 实验室",
            tax_number: "91310000TEST00001",
          },
          system_ai_provider_config: {
            text_llm: {
              base_url: "https://text.example.com/v1",
              model: "gpt-4.1-mini",
              timeout_seconds: 20,
              max_retries: 1,
              api_key_configured: true,
            },
            vlm: {
              base_url: null,
              model: null,
              timeout_seconds: null,
              max_retries: null,
              api_key_configured: false,
            },
          },
          runtime: {
            environment: "development",
            public_api_base_url: "http://127.0.0.1:9876/api",
            async_job_mode: "in_process",
            file_storage_backend: "local",
            llm_provider_configured: false,
            text_llm_provider_configured: true,
            vlm_provider_configured: false,
            allow_admin_self_register: true,
            bootstrap_admin_configured: false,
            telegram_inbound_configured: false,
            email_inbound_configured: false,
          },
          user_counts: {
            member: 5,
            admin: 2,
            system_admin: 1,
          },
        }));
      }

      if (url === "/api/system/global-invoice-config" && init?.method === "PUT") {
        expect(init.body).toBe(JSON.stringify({
          invoice_title: "同济大学",
          tax_number: "12100000425006117D",
        }));
        return Promise.resolve(jsonResponse({
          invoice_title: "同济大学",
          tax_number: "12100000425006117D",
        }));
      }

      if (url === "/api/system/recognition-provider-config" && init?.method === "PUT") {
        expect(init.body).toBe(JSON.stringify({
          text_llm: {
            base_url: "https://text.example.com/v1",
            model: "gpt-4.1-mini",
            timeout_seconds: 20,
            max_retries: 1,
            api_key: "sk-updated-text",
          },
          vlm: {
            base_url: "https://vlm.example.com/v1",
            model: "gpt-4.1",
            timeout_seconds: 45,
            max_retries: 2,
          },
        }));
        return Promise.resolve(jsonResponse({
          text_llm: {
            base_url: "https://text.example.com/v1",
            model: "gpt-4.1-mini",
            timeout_seconds: 20,
            max_retries: 1,
            api_key_configured: true,
          },
          vlm: {
            base_url: "https://vlm.example.com/v1",
            model: "gpt-4.1",
            timeout_seconds: 45,
            max_retries: 2,
            api_key_configured: false,
          },
        }));
      }

      if (url === "/api/system/users/search?keyword=member1&limit=10") {
        return Promise.resolve(jsonResponse({
          items: [
            {
              id: "user-member-1",
              actor_id: "2250001",
              username: "member1",
              display_name: "王队员",
              student_id: "2250001",
              roles: ["member"],
            },
          ],
        }));
      }

      if (url === "/api/system/users/user-member-1/roles/admin" && init?.method === "PUT") {
        return Promise.resolve(jsonResponse({
          user: {
            id: "user-member-1",
            username: "member1",
            role: "member",
            roles: ["member", "admin"],
            actor_id: "2250001",
            display_name: "王队员",
            member_code: "2250001",
            created_at: "2026-04-28T00:00:00Z",
            updated_at: "2026-05-02T23:00:00Z",
          },
          role: "admin",
          already_assigned: false,
        }));
      }

      throw new Error(`Unhandled fetch URL in system admin test: ${url}`);
    });

    renderSystemRoute();

    expect(await screen.findByRole("heading", { name: "系统管理员工作台" })).toBeInTheDocument();
    expect(screen.getByText("当前系统管理员：赵系统管理员")).toBeInTheDocument();
    expect(screen.getByText("5")).toBeInTheDocument();
    expect(screen.getByDisplayValue("同济大学 ACM 实验室")).toBeInTheDocument();
    expect(screen.getByText("http://127.0.0.1:9876/api")).toBeInTheDocument();
    expect(screen.getByDisplayValue("https://text.example.com/v1")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("发票抬头"), { target: { value: "同济大学" } });
    fireEvent.change(screen.getByLabelText("税号"), { target: { value: "12100000425006117D" } });
    fireEvent.click(screen.getByRole("button", { name: "保存全局配置" }));

    expect(await screen.findByDisplayValue("同济大学")).toBeInTheDocument();
    expect(screen.getByDisplayValue("12100000425006117D")).toBeInTheDocument();

    fireEvent.change(screen.getAllByLabelText("API Key")[0]!, { target: { value: "sk-updated-text" } });
    fireEvent.change(screen.getAllByLabelText("Base URL")[1]!, { target: { value: "https://vlm.example.com/v1" } });
    fireEvent.change(screen.getAllByLabelText("模型")[1]!, { target: { value: "gpt-4.1" } });
    fireEvent.change(screen.getAllByLabelText("超时秒数")[1]!, { target: { value: "45" } });
    fireEvent.change(screen.getAllByLabelText("最大重试次数")[1]!, { target: { value: "2" } });
    fireEvent.click(screen.getByRole("button", { name: "保存识别 Provider 配置" }));

    expect(await screen.findByDisplayValue("https://vlm.example.com/v1")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("检索账号"), { target: { value: "member1" } });
    fireEvent.click(screen.getByRole("button", { name: "检索账号" }));

    fireEvent.click(await screen.findByRole("button", { name: "王队员 / member1 / 2250001" }));
    const selectedUsers = await screen.findByLabelText("已选系统账号列表");
    expect(within(selectedUsers).getByText("王队员 / member1 / 2250001")).toBeInTheDocument();
    fireEvent.click(await screen.findByRole("button", { name: "授予管理员" }));
    expect(await screen.findByRole("button", { name: "已是管理员" })).toBeDisabled();
  });

  it("blocks ordinary admins before requesting system settings", async () => {
    setMockSession("admin");
    const fetchSpy = vi.spyOn(globalThis, "fetch");

    renderSystemRoute();

    expect(await screen.findByRole("heading", { name: "系统管理 暂不可访问" })).toBeInTheDocument();
    expect(screen.getByText("当前登录身份不匹配；此入口仅允许系统管理员访问。")).toBeInTheDocument();
    expect(fetchSpy).not.toHaveBeenCalled();
  });
});
