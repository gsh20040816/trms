import { fireEvent, render, screen } from "@testing-library/react";
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
          runtime: {
            environment: "development",
            public_api_base_url: "http://127.0.0.1:9876/api",
            async_job_mode: "in_process",
            file_storage_backend: "local",
            llm_provider_configured: false,
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

      throw new Error(`Unhandled fetch URL in system admin test: ${url}`);
    });

    renderSystemRoute();

    expect(await screen.findByRole("heading", { name: "系统管理员工作台" })).toBeInTheDocument();
    expect(screen.getByText("当前系统管理员：赵系统管理员")).toBeInTheDocument();
    expect(screen.getByText("5")).toBeInTheDocument();
    expect(screen.getByDisplayValue("同济大学 ACM 实验室")).toBeInTheDocument();
    expect(screen.getByText("http://127.0.0.1:9876/api")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("发票抬头"), { target: { value: "同济大学" } });
    fireEvent.change(screen.getByLabelText("税号"), { target: { value: "12100000425006117D" } });
    fireEvent.click(screen.getByRole("button", { name: "保存全局配置" }));

    expect(await screen.findByDisplayValue("同济大学")).toBeInTheDocument();
    expect(screen.getByDisplayValue("12100000425006117D")).toBeInTheDocument();
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
