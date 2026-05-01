import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";

import type { ExpenseSplitRecord, InvoiceRecord, TaskMemberWorkbenchSummary } from "../lib/api/types";
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

const task = {
  id: "TASK-OPEN",
  status: "open",
  competition_name: "ICPC 区域赛",
  competition_location: "武汉",
  competition_start_date: "2026-05-01",
  competition_end_date: "2026-05-03",
  deadline: "2026-05-10T12:00:00+08:00",
  member_ids: ["2250001", "2250002"],
  fee_categories: ["railway", "hotel", "registration"],
  administrator_id: "admin-1",
  project_info: "ACM 竞赛项目",
  reimburser_info: "张管理员",
  invoice_title: "同济大学",
  tax_number: "91310113666007253C",
  created_at: "2026-04-28T08:00:00+08:00",
  updated_at: "2026-04-28T08:00:00+08:00",
};

const invoice: InvoiceRecord = {
  id: "INV-READY-001",
  task_id: "TASK-OPEN",
  material_id: "MAT-READY-001",
  invoice_number: "INV-READY-001",
  issue_date: "2026-04-26",
  transaction_time: "2026-04-26T08:00:00+08:00",
  buyer_name: "同济大学",
  tax_number: "91310113666007253C",
  seller_name: "12306",
  amount_cents: 12345,
  expense_type: "railway",
  member_submission_status: "unsubmitted",
  submitted_by_member_id: null,
  submitted_at: null,
  created_at: "2026-04-28T10:00:00+08:00",
  updated_at: "2026-04-28T10:00:00+08:00",
};

function buildSummary(): TaskMemberWorkbenchSummary {
  return {
    task_id: "TASK-OPEN",
    actor_id: "2250001",
    report: {
      task_id: "TASK-OPEN",
      actor_id: "2250001",
      total_expense_amount_cents: 12345,
      counts: {
        material_count: 1,
        missing_material_count: 0,
        expense_detail_count: 0,
        recognition_pending_count: 0,
        recognition_succeeded_count: 1,
        recognition_failed_count: 0,
        recognition_needs_confirmation_count: 0,
        validation_passed_count: 1,
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
    },
    items: [
      {
        material: {
          material_id: "MAT-READY-001",
          submitter_id: "2250001",
          material_type: "invoice",
          original_filename: "ready.pdf",
          material_status: "assigned",
          recognition_status: "succeeded",
          recognition_failure_stage: null,
          recognition_failure_reason: null,
          invoice_id: "INV-READY-001",
          invoice_number: "INV-READY-001",
          validation_status: "passed",
          validation_messages: [],
          created_at: "2026-04-28T10:00:00+08:00",
        },
        invoice,
        recognition: {
          id: "REC-READY-001",
          material_id: "MAT-READY-001",
          status: "succeeded",
          failure: null,
          recognized_fields: {
            invoice_number: { value: "INV-READY-001", source: "ai", confidence: 0.99, status: "recognized", updated_at: null },
            amount_cents: { value: 12345, source: "ai", confidence: 0.99, status: "recognized", updated_at: null },
            buyer_name: { value: "同济大学", source: "ai", confidence: 0.99, status: "recognized", updated_at: null },
            tax_number: { value: "91310113666007253C", source: "ai", confidence: 0.99, status: "recognized", updated_at: null },
            expense_type: { value: "railway", source: "ai", confidence: 0.99, status: "recognized", updated_at: null },
          },
          manual_corrections: [],
          created_at: "2026-04-28T10:00:00+08:00",
          updated_at: "2026-04-28T10:00:00+08:00",
        },
        validations: [],
        supporting_materials: [],
        splits: [
          {
            id: "SPLIT-001",
            invoice_id: "INV-READY-001",
            member_id: "2250001",
            amount_cents: 12345,
            note: null,
            version: 1,
            is_active: true,
            created_at: "2026-04-28T10:00:00+08:00",
            updated_at: "2026-04-28T10:00:00+08:00",
          },
        ],
        confirmations: [],
        related_expense_details: [],
        missing_materials: [],
        queue_group: "ready",
        blocking_reasons: [],
        ready_for_submission: true,
      },
    ],
    pending_supporting_material_linkage_items: [],
    shared_invoices: [
      {
        invoice_id: "INV-SHARED-001",
        original_filename: "team-shared.pdf",
        invoice_number: "TEAM-SHARED-001",
        validation_status: "passed",
        issue_date: "2026-04-26",
        buyer_name: "同济大学",
        seller_name: "12306",
        amount_cents: 8888,
        expense_type: "railway",
        submitter_id: "2250002",
        supporting_materials: [{ material_type: "payment_record", count: 1 }],
        splits: [{ member_id: "2250001", amount_cents: 4444 }],
        created_at: "2026-04-28T10:00:00+08:00",
        updated_at: "2026-04-28T10:00:00+08:00",
      },
    ],
  };
}

function renderDetail() {
  const router = createMemoryRouter(routes, {
    initialEntries: ["/member/invoices/INV-READY-001?taskId=TASK-OPEN"],
  });
  act(() => {
    render(<RouterProvider router={router} />);
  });
}

describe("MemberInvoiceDetailPage", () => {
  beforeEach(() => {
    clearMockSession();
    setMockSession("member");
  });

  afterEach(() => {
    vi.restoreAllMocks();
    clearMockSession();
  });

  it("saves material type, invoice fields, split drafts, and recognition retry from the per-invoice page", async () => {
    const requests: Array<{ method: string; url: string; body: unknown }> = [];
    vi.spyOn(globalThis, "fetch").mockImplementation((input: string | URL | Request, init?: RequestInit) => {
      const url = resolveRequestUrl(input);
      const method = resolveRequestMethod(input, init);
      requests.push({ method, url, body: init?.body ? JSON.parse(init.body as string) : null });

      if (url === "/api/tasks/TASK-OPEN" && method === "GET") {
        return Promise.resolve(jsonResponse(task));
      }
      if (url === "/api/tasks/TASK-OPEN/member-workbench?actor_id=2250001" && method === "GET") {
        return Promise.resolve(jsonResponse(buildSummary()));
      }
      if (url === "/api/materials/MAT-READY-001/material-type" && method === "PATCH") {
        return Promise.resolve(jsonResponse({ item: { id: "MAT-READY-001", material_type: "payment_record" } }));
      }
      if (url === "/api/materials/MAT-READY-001/invoice" && method === "POST") {
        return Promise.resolve(jsonResponse({ invoice: { ...invoice, invoice_number: "MANUAL-001" }, validations: [] }, { status: 201 }));
      }
      if (url === "/api/invoices/INV-READY-001/splits" && method === "PUT") {
        return Promise.resolve(jsonResponse({ items: [] }));
      }
      if (url === "/api/materials/MAT-READY-001/recognition-tasks" && method === "POST") {
        return Promise.resolve(jsonResponse({ item: { id: "REC-NEW-001" } }, { status: 201 }));
      }
      if (url === "/api/recognition-tasks/REC-NEW-001/execute" && method === "POST") {
        return Promise.resolve(jsonResponse({
          item: { id: "REC-NEW-001" },
          dispatch: { mode: "in_process", status: "executed", message: "识别已在当前请求内执行。" },
        }));
      }
      throw new Error(`Unhandled request ${method} ${url}`);
    });

    renderDetail();

    expect(await screen.findByRole("heading", { name: "当前状态" })).toBeInTheDocument();

    fireEvent.mouseDown(screen.getByLabelText("当前材料类型"));
    fireEvent.click(await screen.findByRole("option", { name: "支付记录" }));
    fireEvent.click(screen.getByRole("button", { name: "保存材料类型" }));
    await waitFor(() => {
      expect(requests.some((request) => request.method === "PATCH" && request.url === "/api/materials/MAT-READY-001/material-type")).toBe(true);
    });

    const invoiceNumberInput = await screen.findByLabelText("发票号码");
    fireEvent.change(invoiceNumberInput, { target: { value: "MANUAL-001" } });
    fireEvent.click(screen.getByRole("button", { name: "保存发票字段并校验" }));
    await waitFor(() => {
      expect(requests.some((request) => (
        request.method === "POST"
        && request.url === "/api/materials/MAT-READY-001/invoice"
        && (request.body as { invoice_number?: string }).invoice_number === "MANUAL-001"
      ))).toBe(true);
    });

    const amountInputs = await screen.findAllByLabelText("金额（元）");
    const splitAmountInput = amountInputs[1];
    if (!splitAmountInput) {
      throw new Error("Expected split amount input.");
    }
    fireEvent.change(splitAmountInput, { target: { value: "100.00" } });
    fireEvent.click(await screen.findByRole("button", { name: "保存金额归属" }));
    const confirmDialog = await screen.findByRole("dialog");
    expect(within(confirmDialog).getByText("当前分摊合计 ￥100.00，比发票金额 ￥123.45 少了 ￥23.45。这表示仍有未报销金额；确认后仍会保存，但这张发票会继续停留在“分摊未完成”。")).toBeInTheDocument();
    await act(async () => {
      fireEvent.click(within(confirmDialog).getByRole("button", { name: "仍然保存" }));
      await Promise.resolve();
    });
    await waitFor(() => {
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });
    await waitFor(() => {
      expect(requests.some((request) => request.method === "PUT" && request.url === "/api/invoices/INV-READY-001/splits")).toBe(true);
    });

    fireEvent.click(screen.getByRole("button", { name: "运行重新识别" }));
    await waitFor(() => {
      expect(requests.some((request) => request.method === "POST" && request.url === "/api/recognition-tasks/REC-NEW-001/execute")).toBe(true);
    });
  });

  it("does not save splits when the member cancels the partial reimbursement confirmation", async () => {
    const requests: Array<{ method: string; url: string; body: unknown }> = [];
    vi.spyOn(globalThis, "fetch").mockImplementation((input: string | URL | Request, init?: RequestInit) => {
      const url = resolveRequestUrl(input);
      const method = resolveRequestMethod(input, init);
      requests.push({ method, url, body: init?.body ? JSON.parse(init.body as string) : null });

      if (url === "/api/tasks/TASK-OPEN" && method === "GET") {
        return Promise.resolve(jsonResponse(task));
      }
      if (url === "/api/tasks/TASK-OPEN/member-workbench?actor_id=2250001" && method === "GET") {
        return Promise.resolve(jsonResponse(buildSummary()));
      }
      throw new Error(`Unhandled request ${method} ${url}`);
    });

    renderDetail();

    const amountInputs = await screen.findAllByLabelText("金额（元）");
    const splitAmountInput = amountInputs[1];
    if (!splitAmountInput) {
      throw new Error("Expected split amount input.");
    }
    fireEvent.change(splitAmountInput, { target: { value: "100.00" } });
    fireEvent.click(await screen.findByRole("button", { name: "保存金额归属" }));

    const confirmDialog = await screen.findByRole("dialog");
    await act(async () => {
      fireEvent.click(within(confirmDialog).getByRole("button", { name: "继续编辑" }));
      await Promise.resolve();
    });
    await waitFor(() => {
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });

    expect(requests.some((request) => request.method === "PUT" && request.url === "/api/invoices/INV-READY-001/splits")).toBe(false);
  });

  it("does not ask the member to confirm the same invoice amount again", async () => {
    const requests: Array<{ method: string; url: string; body: unknown }> = [];
    const split: ExpenseSplitRecord = {
      id: "SPLIT-001",
      invoice_id: "INV-READY-001",
      member_id: "2250001",
      amount_cents: 12345,
      note: "self paid",
      version: 1,
      is_active: true,
      created_at: "2026-04-28T10:00:00+08:00",
      updated_at: "2026-04-28T10:00:00+08:00",
    };
    const summary = buildSummary();
    const firstItem = summary.items[0];
    if (!firstItem) {
      throw new Error("expected buildSummary to create an invoice workbench item");
    }
    summary.items[0] = {
      ...firstItem,
      splits: [split],
      related_expense_details: [
        {
          split_id: "SPLIT-001",
          split_version: 1,
          member_id: "2250001",
          amount_cents: 12345,
          note: "self paid",
          created_at: "2026-04-28T10:00:00+08:00",
          updated_at: "2026-04-28T10:00:00+08:00",
          invoice,
          confirmation: null,
        },
      ],
      queue_group: "confirmation_incomplete",
      blocking_reasons: ["confirmation_incomplete"],
      ready_for_submission: false,
    };

    vi.spyOn(globalThis, "fetch").mockImplementation((input: string | URL | Request, init?: RequestInit) => {
      const url = resolveRequestUrl(input);
      const method = resolveRequestMethod(input, init);
      requests.push({ method, url, body: init?.body ? JSON.parse(init.body as string) : null });

      if (url === "/api/tasks/TASK-OPEN" && method === "GET") {
        return Promise.resolve(jsonResponse(task));
      }
      if (url === "/api/tasks/TASK-OPEN/member-workbench?actor_id=2250001" && method === "GET") {
        return Promise.resolve(jsonResponse(summary));
      }
      throw new Error(`Unhandled request ${method} ${url}`);
    });

    renderDetail();

    expect(await screen.findByRole("heading", { name: "金额归属" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "本人费用确认" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "确认这笔费用" })).not.toBeInTheDocument();

    expect(requests.some((request) => request.url === "/api/splits/SPLIT-001/confirmation")).toBe(false);
  });

  it("renders shared invoices with the same one-line summary fields", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((input: string | URL | Request, init?: RequestInit) => {
      const url = resolveRequestUrl(input);
      const method = resolveRequestMethod(input, init);

      if (url === "/api/tasks/TASK-OPEN" && method === "GET") {
        return Promise.resolve(jsonResponse(task));
      }
      if (url === "/api/tasks/TASK-OPEN/member-workbench?actor_id=2250001" && method === "GET") {
        return Promise.resolve(jsonResponse(buildSummary()));
      }

      throw new Error(`Unhandled request ${method} ${url}`);
    });

    const router = createMemoryRouter(routes, {
      initialEntries: ["/member/invoices/INV-SHARED-001?taskId=TASK-OPEN"],
    });
    act(() => {
      render(<RouterProvider router={router} />);
    });

    expect(await screen.findByRole("heading", { name: "共享发票摘要" })).toBeInTheDocument();
    expect(screen.getByText("team-shared.pdf")).toBeInTheDocument();
    expect(screen.getByText("票号 TEAM-SHARED-001")).toBeInTheDocument();
    expect(screen.getByText("校验通过")).toBeInTheDocument();
    expect(screen.getByText("附件 1")).toBeInTheDocument();
  });
});
