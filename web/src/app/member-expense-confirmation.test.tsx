import { act, fireEvent, render, screen, within } from "@testing-library/react";
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

function renderMemberExpenseConfirmationRoute(entry = "/member/expenses/confirm?taskId=TASK-OPEN") {
  const router = createMemoryRouter(routes, {
    initialEntries: [entry],
  });

  act(() => {
    render(<RouterProvider router={router} />);
  });
}

describe("MemberExpenseConfirmationPage", () => {
  beforeEach(() => {
    clearMockSession();
    setMockSession("member");
  });

  afterEach(() => {
    vi.restoreAllMocks();
    clearMockSession();
  });

  it("renders member expense details with supporting-material summary and allows confirmation", async () => {
    let expenseDetailRequestCount = 0;

    vi.spyOn(globalThis, "fetch").mockImplementation((input: string | URL | Request, init?: RequestInit) => {
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

      if (url === "/api/tasks/TASK-OPEN/expense-details?actor_id=2250001") {
        expenseDetailRequestCount += 1;
        return Promise.resolve(jsonResponse({
          actor_id: "2250001",
          scope: "member",
          total_amount_cents: 6345,
          items: [
            {
              split_id: "SPLIT-001",
              split_version: 1,
              member_id: "2250001",
              amount_cents: 6345,
              note: "team shared",
              created_at: "2026-04-28T10:05:00+08:00",
              updated_at: "2026-04-28T10:05:00+08:00",
              invoice: {
                id: "INV-001",
                material_id: "MAT-INV-001",
                invoice_number: "INV-001",
                issue_date: "2026-04-20",
                transaction_time: "2026-04-20T09:00:00+08:00",
                buyer_name: "同济大学",
                seller_name: "中国铁路",
                amount_cents: 12345,
                expense_type: "railway",
                created_at: "2026-04-28T10:00:00+08:00",
                updated_at: "2026-04-28T10:05:00+08:00",
              },
              confirmation: expenseDetailRequestCount > 1
                ? {
                    id: "CONF-001",
                    member_id: "2250001",
                    split_version: 1,
                    status: "confirmed",
                    dispute_reason: null,
                    confirmed_at: "2026-04-28T11:00:00+08:00",
                    updated_at: "2026-04-28T11:00:00+08:00",
                  }
                : null,
            },
          ],
        }));
      }

      if (url === "/api/invoices/INV-001/supporting-materials") {
        return Promise.resolve(jsonResponse({
          items: [
            {
              id: "MAT-PAY-001",
              status: "assigned",
              task_id: "TASK-OPEN",
              submitter_id: "2250001",
              task_id_hint: null,
              submitter_id_hint: null,
              channel: "web",
              material_type: "payment_record",
              storage_key: "TASK-OPEN/MAT-PAY-001-pay.png",
              original_filename: "pay.png",
              content_type: "image/png",
              size_bytes: 2048,
              sha256: "a".repeat(64),
              duplicate_of: null,
              claimed_by: null,
              claimed_at: null,
              created_at: "2026-04-28T09:30:00+08:00",
            },
          ],
        }));
      }

      if (url === "/api/splits/SPLIT-001/confirmation" && init?.method === "PUT") {
        expect(init.body).toBe(JSON.stringify({
          actor_id: "2250001",
          member_id: "2250001",
          status: "confirmed",
          dispute_reason: null,
        }));
        return Promise.resolve(jsonResponse({
          id: "CONF-001",
          split_id: "SPLIT-001",
          member_id: "2250001",
          split_version: 1,
          split_amount_cents: 6345,
          split_note: "team shared",
          is_current: true,
          status: "confirmed",
          dispute_reason: null,
          confirmed_at: "2026-04-28T11:00:00+08:00",
          updated_at: "2026-04-28T11:00:00+08:00",
        }));
      }

      throw new Error(`Unhandled fetch URL in member confirmation test: ${url}`);
    });

    renderMemberExpenseConfirmationRoute();

    expect(await screen.findByRole("heading", { name: "成员费用确认" })).toBeInTheDocument();
    const detailList = await screen.findByLabelText("成员费用明细列表");
    const detailCard = within(detailList).getByRole("heading", { name: "INV-001" }).closest("article");
    if (!detailCard) {
      throw new Error("expected one expense detail card");
    }

    expect(within(detailCard).getByText("归属金额")).toBeInTheDocument();
    expect(within(detailCard).getByText("￥63.45")).toBeInTheDocument();
    expect(within(detailCard).getByText("支付记录 / pay.png")).toBeInTheDocument();

    fireEvent.click(within(detailCard).getByRole("button", { name: "确认这笔费用" }));

    expect(await within(detailCard).findByText("已提交确认，页面已刷新最新确认状态。")).toBeInTheDocument();
    expect(await screen.findByText("已确认")).toBeInTheDocument();
  });

  it("requires dispute reason and submits disputed confirmation after input", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((input: string | URL | Request, init?: RequestInit) => {
      const url = resolveRequestUrl(input);

      if (url === "/api/tasks") {
        return Promise.resolve(jsonResponse([
          {
            id: "TASK-OPEN",
            status: "reviewing",
            competition_name: "CCPC Final",
            competition_location: "成都",
            competition_start_date: "2026-06-01",
            competition_end_date: "2026-06-03",
            deadline: "2026-06-10T18:00:00+08:00",
            member_ids: ["2250001", "2250002"],
            fee_categories: ["hotel"],
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

      if (url === "/api/tasks/TASK-OPEN/expense-details?actor_id=2250001") {
        return Promise.resolve(jsonResponse({
          actor_id: "2250001",
          scope: "member",
          total_amount_cents: 20000,
          items: [
            {
              split_id: "SPLIT-002",
              split_version: 2,
              member_id: "2250001",
              amount_cents: 20000,
              note: "hotel shared",
              created_at: "2026-04-28T10:05:00+08:00",
              updated_at: "2026-04-28T10:05:00+08:00",
              invoice: {
                id: "INV-002",
                material_id: "MAT-INV-002",
                invoice_number: "HOTEL-001",
                issue_date: "2026-04-21",
                transaction_time: "2026-04-21T09:00:00+08:00",
                buyer_name: "同济大学",
                seller_name: "锦江酒店",
                amount_cents: 20000,
                expense_type: "hotel",
                created_at: "2026-04-28T10:00:00+08:00",
                updated_at: "2026-04-28T10:05:00+08:00",
              },
              confirmation: null,
            },
          ],
        }));
      }

      if (url === "/api/invoices/INV-002/supporting-materials") {
        return Promise.resolve(jsonResponse({ items: [] }));
      }

      if (url === "/api/splits/SPLIT-002/confirmation" && init?.method === "PUT") {
        expect(init.body).toBe(JSON.stringify({
          actor_id: "2250001",
          member_id: "2250001",
          status: "disputed",
          dispute_reason: "住宿分摊金额过高",
        }));
        return Promise.resolve(jsonResponse({
          id: "CONF-002",
          split_id: "SPLIT-002",
          member_id: "2250001",
          split_version: 2,
          split_amount_cents: 20000,
          split_note: "hotel shared",
          is_current: true,
          status: "disputed",
          dispute_reason: "住宿分摊金额过高",
          confirmed_at: "2026-04-28T11:05:00+08:00",
          updated_at: "2026-04-28T11:05:00+08:00",
        }));
      }

      throw new Error(`Unhandled fetch URL in member confirmation dispute test: ${url}`);
    });

    renderMemberExpenseConfirmationRoute();

    const detailList = await screen.findByLabelText("成员费用明细列表");
    const detailCard = within(detailList).getByRole("heading", { name: "HOTEL-001" }).closest("article");
    if (!detailCard) {
      throw new Error("expected one expense detail card");
    }

    fireEvent.click(within(detailCard).getByRole("button", { name: "提交异议" }));
    expect(await within(detailCard).findByText("提交异议时必须填写原因。")).toBeInTheDocument();

    fireEvent.change(within(detailCard).getByLabelText("异议原因 SPLIT-002"), {
      target: { value: "住宿分摊金额过高" },
    });
    fireEvent.click(within(detailCard).getByRole("button", { name: "提交异议" }));

    expect(await within(detailCard).findByText("已提交异议，页面已刷新最新确认状态。")).toBeInTheDocument();
  });

  it("shows a refresh prompt when the split version has become stale", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((input: string | URL | Request, init?: RequestInit) => {
      const url = resolveRequestUrl(input);

      if (url === "/api/tasks") {
        return Promise.resolve(jsonResponse([
          {
            id: "TASK-OPEN",
            status: "closed",
            competition_name: "Regional",
            competition_location: "上海",
            competition_start_date: "2026-05-01",
            competition_end_date: "2026-05-03",
            deadline: "2026-05-10T18:00:00+08:00",
            member_ids: ["2250001"],
            fee_categories: ["registration"],
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

      if (url === "/api/tasks/TASK-OPEN/expense-details?actor_id=2250001") {
        return Promise.resolve(jsonResponse({
          actor_id: "2250001",
          scope: "member",
          total_amount_cents: 10000,
          items: [
            {
              split_id: "SPLIT-003",
              split_version: 3,
              member_id: "2250001",
              amount_cents: 10000,
              note: null,
              created_at: "2026-04-28T10:05:00+08:00",
              updated_at: "2026-04-28T10:05:00+08:00",
              invoice: {
                id: "INV-003",
                material_id: "MAT-INV-003",
                invoice_number: "REG-001",
                issue_date: "2026-04-20",
                transaction_time: "2026-04-20T09:00:00+08:00",
                buyer_name: "同济大学",
                seller_name: "会务组",
                amount_cents: 10000,
                expense_type: "registration",
                created_at: "2026-04-28T10:00:00+08:00",
                updated_at: "2026-04-28T10:05:00+08:00",
              },
              confirmation: null,
            },
          ],
        }));
      }

      if (url === "/api/invoices/INV-003/supporting-materials") {
        return Promise.resolve(jsonResponse({ items: [] }));
      }

      if (url === "/api/splits/SPLIT-003/confirmation" && init?.method === "PUT") {
        return Promise.resolve(jsonResponse({ detail: "split not found" }, { status: 404 }));
      }

      throw new Error(`Unhandled fetch URL in member confirmation stale test: ${url}`);
    });

    renderMemberExpenseConfirmationRoute();

    const detailList = await screen.findByLabelText("成员费用明细列表");
    const detailCard = within(detailList).getByRole("heading", { name: "REG-001" }).closest("article");
    if (!detailCard) {
      throw new Error("expected one expense detail card");
    }

    fireEvent.click(within(detailCard).getByRole("button", { name: "确认这笔费用" }));

    expect(await within(detailCard).findByText("当前费用明细版本已失效，通常是管理员刚修改了分摊金额或成员归属；请刷新后再确认。")).toBeInTheDocument();
    expect(within(detailCard).getByRole("button", { name: "重新加载明细" })).toBeInTheDocument();
  });

  it("shows backend errors when confirmation submission fails for other reasons", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((input: string | URL | Request, init?: RequestInit) => {
      const url = resolveRequestUrl(input);

      if (url === "/api/tasks") {
        return Promise.resolve(jsonResponse([
          {
            id: "TASK-OPEN",
            status: "closed",
            competition_name: "Regional",
            competition_location: "上海",
            competition_start_date: "2026-05-01",
            competition_end_date: "2026-05-03",
            deadline: "2026-05-10T18:00:00+08:00",
            member_ids: ["2250001"],
            fee_categories: ["registration"],
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

      if (url === "/api/tasks/TASK-OPEN/expense-details?actor_id=2250001") {
        return Promise.resolve(jsonResponse({
          actor_id: "2250001",
          scope: "member",
          total_amount_cents: 10000,
          items: [
            {
              split_id: "SPLIT-004",
              split_version: 3,
              member_id: "2250001",
              amount_cents: 10000,
              note: null,
              created_at: "2026-04-28T10:05:00+08:00",
              updated_at: "2026-04-28T10:05:00+08:00",
              invoice: {
                id: "INV-004",
                material_id: "MAT-INV-004",
                invoice_number: "REG-002",
                issue_date: "2026-04-20",
                transaction_time: "2026-04-20T09:00:00+08:00",
                buyer_name: "同济大学",
                seller_name: "会务组",
                amount_cents: 10000,
                expense_type: "registration",
                created_at: "2026-04-28T10:00:00+08:00",
                updated_at: "2026-04-28T10:05:00+08:00",
              },
              confirmation: null,
            },
          ],
        }));
      }

      if (url === "/api/invoices/INV-004/supporting-materials") {
        return Promise.resolve(jsonResponse({ items: [] }));
      }

      if (url === "/api/splits/SPLIT-004/confirmation" && init?.method === "PUT") {
        return Promise.resolve(jsonResponse(
          { detail: "confirmation window has been locked" },
          { status: 409 },
        ));
      }

      throw new Error(`Unhandled fetch URL in member confirmation rejection test: ${url}`);
    });

    renderMemberExpenseConfirmationRoute();

    const detailList = await screen.findByLabelText("成员费用明细列表");
    const detailCard = within(detailList).getByRole("heading", { name: "REG-002" }).closest("article");
    if (!detailCard) {
      throw new Error("expected one expense detail card");
    }

    fireEvent.click(within(detailCard).getByRole("button", { name: "确认这笔费用" }));

    expect(await screen.findByRole("heading", { name: "接口请求失败" })).toBeInTheDocument();
    expect(screen.getByText("confirmation window has been locked")).toBeInTheDocument();
  });
});
