import { act, cleanup, render, screen } from "@testing-library/react";
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

function jsonResponse(body: unknown, init: ResponseInit = {}) {
  return new Response(JSON.stringify(body), {
    status: init.status ?? 200,
    headers: {
      "Content-Type": "application/json",
      ...init.headers,
    },
  });
}

function buildEmptySupportingMaterialLinkageResponse(url: string) {
  const matched = url.match(/^\/api\/tasks\/([^/]+)\/supporting-material-linkage(?:\?actor_id=([^&]+))?$/);
  if (!matched) {
    return null;
  }
  return {
    task_id: decodeURIComponent(matched[1] ?? ""),
    actor_id: matched[2] ?? "2250001",
    items: [],
  };
}

function renderLegacyRoute(entry: string) {
  const router = createMemoryRouter(routes, {
    initialEntries: [entry],
  });

  act(() => {
    render(<RouterProvider router={router} />);
  });

  return router;
}

describe("member legacy routes", () => {
  beforeEach(() => {
    clearMockSession();
    setMockSession("member");

    vi.spyOn(globalThis, "fetch").mockImplementation((input: string | URL | Request) => {
      const url = resolveRequestUrl(input);
      const emptySupportingMaterialLinkageResponse = buildEmptySupportingMaterialLinkageResponse(url);
      if (emptySupportingMaterialLinkageResponse) {
        return Promise.resolve(jsonResponse(emptySupportingMaterialLinkageResponse));
      }

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

      if (url === "/api/tasks/TASK-OPEN/member-status?actor_id=2250001") {
        return Promise.resolve(jsonResponse({
          task_id: "TASK-OPEN",
          actor_id: "2250001",
          total_expense_amount_cents: 0,
          counts: {
            material_count: 0,
            missing_material_count: 0,
            expense_detail_count: 0,
            recognition_pending_count: 0,
            recognition_succeeded_count: 0,
            recognition_failed_count: 0,
            recognition_needs_confirmation_count: 0,
            validation_passed_count: 0,
            validation_failed_count: 0,
            validation_pending_count: 0,
            validation_not_applicable_count: 0,
            confirmed_expense_count: 0,
            pending_confirmation_count: 0,
            disputed_confirmation_count: 0,
            missing_confirmation_count: 0,
          },
          materials: [],
          missing_materials: [],
          expense_details: [],
        }));
      }

      if (url === "/api/tasks/TASK-OPEN/shared-invoices?actor_id=2250001") {
        return Promise.resolve(jsonResponse({
          task_id: "TASK-OPEN",
          actor_id: "2250001",
          items: [],
        }));
      }

      if (url === "/api/tasks/TASK-OPEN/invoices") {
        return Promise.resolve(jsonResponse({ items: [] }));
      }

      throw new Error(`Unhandled fetch URL in legacy member route test: ${url}`);
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
    clearMockSession();
  });

  it("redirects legacy upload route to the workbench upload section", async () => {
    const router = renderLegacyRoute("/member/materials/upload?taskId=TASK-OPEN");

    expect(await screen.findByRole("heading", { name: "按任务查看我的发票与费用" })).toBeInTheDocument();
    expect(await screen.findByText("上传材料与附件")).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/member/invoices/workbench");
    expect(router.state.location.hash).toBe("#member-workbench-upload");
  });

  it("redirects legacy status and missing routes to the workbench status views", async () => {
    const statusRouter = renderLegacyRoute("/member/materials/status?taskId=TASK-OPEN");

    expect(await screen.findByRole("heading", { name: "按任务查看我的发票与费用" })).toBeInTheDocument();
    expect(await screen.findByText("当前任务下还没有可查看的发票")).toBeInTheDocument();
    expect(statusRouter.state.location.pathname).toBe("/member/invoices/workbench");
    expect(statusRouter.state.location.hash).toBe("#member-workbench-invoices");

    cleanup();
    clearMockSession();
    setMockSession("member");
    const missingRouter = renderLegacyRoute("/member/materials/missing?taskId=TASK-OPEN");

    expect(await screen.findByText("当前任务没有待补的缺失材料")).toBeInTheDocument();
    expect(missingRouter.state.location.pathname).toBe("/member/invoices/workbench");
    expect(missingRouter.state.location.hash).toBe("#member-workbench-missing-materials");
  });

  it("redirects legacy confirmation route to the workbench confirmation section", async () => {
    const router = renderLegacyRoute("/member/expenses/confirm?taskId=TASK-OPEN");

    expect(await screen.findByText("确认当前分到本人名下的费用")).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/member/invoices/workbench");
    expect(router.state.location.hash).toBe("#member-workbench-confirmations");
  });
});
