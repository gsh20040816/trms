import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
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

function resolveRequestMethod(
  input: string | URL | Request,
  init: RequestInit | undefined,
) {
  if (init?.method) {
    return init.method.toUpperCase();
  }
  if (input instanceof Request) {
    return input.method.toUpperCase();
  }
  return "GET";
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

function parseJsonRequestBody(init: RequestInit | undefined) {
  const body = init?.body;
  if (typeof body !== "string" || body.length === 0) {
    return {};
  }
  return JSON.parse(body) as Record<string, unknown>;
}

type MutableInvoiceState = {
  id: string;
  material_id: string;
  invoice_number: string;
  amount_cents: number;
  expense_type: "railway" | "hotel";
  member_submission_status: "unsubmitted" | "submitted";
  submitted_by_member_id: string | null;
  submitted_at: string | null;
};

type BatchRequestBody = {
  invoice_ids: string[];
};

type WorkbenchFetchOptions = {
  onSubmit?: (args: {
    body: BatchRequestBody;
    invoices: MutableInvoiceState[];
  }) => unknown;
  onWithdraw?: (args: {
    body: BatchRequestBody;
    invoices: MutableInvoiceState[];
  }) => unknown;
};

function buildInvoiceResponse(invoice: MutableInvoiceState) {
  return {
    id: invoice.id,
    task_id: "TASK-OPEN",
    material_id: invoice.material_id,
    invoice_number: invoice.invoice_number,
    issue_date: "2026-04-20",
    transaction_time: "2026-04-20T09:00:00+08:00",
    buyer_name: "同济大学",
    tax_number: "91310113666007253C",
    seller_name: invoice.expense_type === "railway" ? "中国铁路" : "同济酒店",
    amount_cents: invoice.amount_cents,
    expense_type: invoice.expense_type,
    member_submission_status: invoice.member_submission_status,
    submitted_by_member_id: invoice.submitted_by_member_id,
    submitted_at: invoice.submitted_at,
    created_at: "2026-04-28T10:00:00+08:00",
    updated_at: "2026-04-28T10:05:00+08:00",
  };
}

function buildMaterialStatusResponse(invoice: MutableInvoiceState) {
  const isRailway = invoice.id === "INV-001";
  return {
    material_id: invoice.material_id,
    submitter_id: "2250001",
    material_type: "invoice",
    original_filename: isRailway ? "railway.pdf" : "hotel.pdf",
    material_status: "assigned",
    recognition_status: "succeeded",
    recognition_failure_stage: null,
    recognition_failure_reason: null,
    invoice_id: invoice.id,
    invoice_number: invoice.invoice_number,
    validation_status: "passed",
    validation_messages: [],
    created_at: isRailway ? "2026-04-28T10:00:00+08:00" : "2026-04-28T11:00:00+08:00",
  };
}

function buildSplitResponse(invoice: MutableInvoiceState) {
  const isRailway = invoice.id === "INV-001";
  return {
    id: isRailway ? "SPLIT-001" : "SPLIT-002",
    invoice_id: invoice.id,
    member_id: "2250001",
    amount_cents: invoice.amount_cents,
    note: "self paid",
    version: 1,
    is_active: true,
    created_at: isRailway ? "2026-04-28T10:05:00+08:00" : "2026-04-28T11:05:00+08:00",
    updated_at: isRailway ? "2026-04-28T10:05:00+08:00" : "2026-04-28T11:05:00+08:00",
  };
}

function buildConfirmationResponse(invoice: MutableInvoiceState) {
  const isRailway = invoice.id === "INV-001";
  return {
    id: isRailway ? "CONF-001" : "CONF-002",
    split_id: isRailway ? "SPLIT-001" : "SPLIT-002",
    member_id: "2250001",
    split_version: 1,
    split_amount_cents: invoice.amount_cents,
    split_note: "self paid",
    is_current: true,
    status: "confirmed",
    dispute_reason: null,
    confirmed_at: isRailway ? "2026-04-28T10:06:00+08:00" : "2026-04-28T11:06:00+08:00",
    updated_at: isRailway ? "2026-04-28T10:06:00+08:00" : "2026-04-28T11:06:00+08:00",
  };
}

function buildRecognitionResponse(invoice: MutableInvoiceState) {
  const isRailway = invoice.id === "INV-001";
  return {
    id: isRailway ? "REC-001" : "REC-002",
    material_id: invoice.material_id,
    status: "succeeded",
    is_final_fact: false,
    failure: null,
    raw_response: {},
    recognized_fields: {},
    manual_corrections: [],
    created_at: isRailway ? "2026-04-28T10:01:00+08:00" : "2026-04-28T11:01:00+08:00",
    updated_at: isRailway ? "2026-04-28T10:01:00+08:00" : "2026-04-28T11:01:00+08:00",
  };
}

function buildTaskMemberStatusReport(invoices: MutableInvoiceState[]) {
  return {
    task_id: "TASK-OPEN",
    actor_id: "2250001",
    total_expense_amount_cents: invoices.reduce((sum, invoice) => sum + invoice.amount_cents, 0),
    counts: {
      material_count: invoices.length,
      missing_material_count: 0,
      expense_detail_count: 0,
      recognition_pending_count: 0,
      recognition_succeeded_count: invoices.length,
      recognition_failed_count: 0,
      recognition_needs_confirmation_count: 0,
      validation_passed_count: invoices.length,
      validation_failed_count: 0,
      validation_pending_count: 0,
      validation_not_applicable_count: 0,
      confirmed_expense_count: 0,
      pending_confirmation_count: 0,
      disputed_confirmation_count: 0,
      missing_confirmation_count: 0,
    },
    materials: invoices.map(buildMaterialStatusResponse),
    missing_materials: [],
    expense_details: [],
  };
}

function buildWorkbenchSummaryItem(invoice: MutableInvoiceState) {
  const split = buildSplitResponse(invoice);
  const confirmation = buildConfirmationResponse(invoice);
  const recognition = buildRecognitionResponse(invoice);
  const summaryRecognition = {
    id: recognition.id,
    status: recognition.status,
    is_final_fact: recognition.is_final_fact,
    failure: recognition.failure,
    recognized_fields: recognition.recognized_fields,
    manual_corrections: recognition.manual_corrections,
    created_at: recognition.created_at,
    updated_at: recognition.updated_at,
  };

  return {
    material: buildMaterialStatusResponse(invoice),
    invoice: buildInvoiceResponse(invoice),
    recognition: summaryRecognition,
    validations: [],
    supporting_materials: [],
    splits: [split],
    confirmations: [confirmation],
    related_expense_details: [
      {
        split_id: split.id,
        invoice: buildInvoiceResponse(invoice),
        member_id: "2250001",
        amount_cents: invoice.amount_cents,
        note: "self paid",
        confirmation,
      },
    ],
    missing_materials: [],
    queue_group: "ready",
    blocking_reasons: [],
    ready_for_submission: true,
  };
}

function buildWorkbenchFetchMock(options: WorkbenchFetchOptions = {}) {
  const invoices: MutableInvoiceState[] = [
    {
      id: "INV-001",
      material_id: "MAT-001",
      invoice_number: "INV-001",
      amount_cents: 6345,
      expense_type: "railway",
      member_submission_status: "unsubmitted",
      submitted_by_member_id: null,
      submitted_at: null,
    },
    {
      id: "INV-002",
      material_id: "MAT-002",
      invoice_number: "INV-002",
      amount_cents: 8800,
      expense_type: "hotel",
      member_submission_status: "submitted",
      submitted_by_member_id: "2250001",
      submitted_at: "2026-04-29T12:00:00+08:00",
    },
  ];
  const [firstInvoice, secondInvoice] = invoices as [MutableInvoiceState, MutableInvoiceState];

  return vi.fn((input: string | URL | Request, init?: RequestInit) => {
    const url = resolveRequestUrl(input);
    const method = resolveRequestMethod(input, init);

    if (url === "/api/tasks" && method === "GET") {
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

    if (url === "/api/tasks/TASK-OPEN/member-workbench?actor_id=2250001" && method === "GET") {
      return Promise.resolve(jsonResponse({
        task_id: "TASK-OPEN",
        actor_id: "2250001",
        report: buildTaskMemberStatusReport(invoices),
        items: invoices.map(buildWorkbenchSummaryItem),
        pending_supporting_material_linkage_items: [],
        shared_invoices: [],
      }));
    }

    if (url === "/api/tasks/TASK-OPEN/member-status?actor_id=2250001" && method === "GET") {
      return Promise.resolve(jsonResponse(buildTaskMemberStatusReport(invoices)));
    }

    if (url === "/api/tasks/TASK-OPEN/shared-invoices?actor_id=2250001" && method === "GET") {
      return Promise.resolve(jsonResponse({ items: [] }));
    }

    if (url === "/api/tasks/TASK-OPEN/supporting-material-linkage?actor_id=2250001" && method === "GET") {
      return Promise.resolve(jsonResponse({
        task_id: "TASK-OPEN",
        actor_id: "2250001",
        items: [],
      }));
    }

    if (url === "/api/tasks/TASK-OPEN/invoices" && method === "GET") {
      return Promise.resolve(jsonResponse({
        items: invoices.map(buildInvoiceResponse),
      }));
    }

    if (url === "/api/materials/MAT-001/recognition-tasks" && method === "GET") {
      return Promise.resolve(jsonResponse({
        latest_effective: buildRecognitionResponse(firstInvoice),
        items: [],
      }));
    }

    if (url === "/api/materials/MAT-002/recognition-tasks" && method === "GET") {
      return Promise.resolve(jsonResponse({
        latest_effective: buildRecognitionResponse(secondInvoice),
        items: [],
      }));
    }

    if (/^\/api\/invoices\/INV-00[12]\/validations$/.test(url) && method === "GET") {
      return Promise.resolve(jsonResponse({ items: [] }));
    }

    if (/^\/api\/invoices\/INV-00[12]\/supporting-materials$/.test(url) && method === "GET") {
      return Promise.resolve(jsonResponse({ items: [] }));
    }

    if (url === "/api/invoices/INV-001/splits" && method === "GET") {
      return Promise.resolve(jsonResponse({
        items: [buildSplitResponse(firstInvoice)],
      }));
    }

    if (url === "/api/invoices/INV-002/splits" && method === "GET") {
      return Promise.resolve(jsonResponse({
        items: [buildSplitResponse(secondInvoice)],
      }));
    }

    if (url === "/api/invoices/INV-001/confirmations" && method === "GET") {
      return Promise.resolve(jsonResponse({
        items: [buildConfirmationResponse(firstInvoice)],
      }));
    }

    if (url === "/api/invoices/INV-002/confirmations" && method === "GET") {
      return Promise.resolve(jsonResponse({
        items: [buildConfirmationResponse(secondInvoice)],
      }));
    }

    if (url === "/api/tasks/TASK-OPEN/invoice-submissions" && method === "POST") {
      const body = parseJsonRequestBody(init) as BatchRequestBody;
      return Promise.resolve(jsonResponse(options.onSubmit ? options.onSubmit({ body, invoices }) : {
        status: "success",
        items: body.invoice_ids.map((invoiceId) => {
          const matched = invoices.find((invoice) => invoice.id === invoiceId)!;
          matched.member_submission_status = "submitted";
          matched.submitted_by_member_id = "2250001";
          matched.submitted_at = "2026-04-30T03:00:00+08:00";
          return buildInvoiceResponse(matched);
        }),
        failures: [],
      }));
    }

    if (url === "/api/tasks/TASK-OPEN/invoice-submission-withdrawals" && method === "POST") {
      const body = parseJsonRequestBody(init) as BatchRequestBody;
      return Promise.resolve(jsonResponse(options.onWithdraw ? options.onWithdraw({ body, invoices }) : {
        status: "success",
        items: body.invoice_ids.map((invoiceId) => {
          const matched = invoices.find((invoice) => invoice.id === invoiceId)!;
          matched.member_submission_status = "unsubmitted";
          matched.submitted_by_member_id = null;
          matched.submitted_at = null;
          return buildInvoiceResponse(matched);
        }),
        failures: [],
      }));
    }

    throw new Error(`Unhandled request: ${method} ${url}`);
  });
}

function renderWorkbenchRoute(entry = "/member/invoices/workbench?taskId=TASK-OPEN") {
  const router = createMemoryRouter(routes, {
    initialEntries: [entry],
  });

  act(() => {
    render(<RouterProvider router={router} />);
  });
}

describe("MemberInvoiceWorkbenchPage batch submission", () => {
  beforeEach(() => {
    clearMockSession();
    setMockSession("member");
  });

  afterEach(() => {
    vi.restoreAllMocks();
    clearMockSession();
  });

  it("displays submission statuses and updates batch selection summary", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(buildWorkbenchFetchMock());

    renderWorkbenchRoute();

    const batchSection = await screen.findByRole("region", { name: "批量提交与撤回区" });
    expect(screen.getAllByText("已提交管理员").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("未提交管理员").length).toBeGreaterThanOrEqual(1);
    expect(within(batchSection).getByText("已选 0 张")).toBeInTheDocument();

    act(() => {
      fireEvent.click(screen.getByRole("checkbox", { name: "批量选择发票 INV-001" }));
    });

    expect(within(batchSection).getByText("已选 1 张")).toBeInTheDocument();
    expect(within(batchSection).getByRole("button", { name: "清空选择" })).toBeEnabled();
    expect(within(batchSection).getByRole("button", { name: "批量提交选中发票" })).toBeEnabled();
  });

  it("submits selected invoices and shows per-invoice failure reasons", async () => {
    const fetchMock = buildWorkbenchFetchMock({
      onSubmit: ({ body, invoices }) => {
        expect(body.invoice_ids).toEqual(["INV-001", "INV-002"]);
        const firstInvoice = invoices.find((invoice) => invoice.id === "INV-001")!;
        firstInvoice.member_submission_status = "submitted";
        firstInvoice.submitted_by_member_id = "2250001";
        firstInvoice.submitted_at = "2026-04-30T03:00:00+08:00";
        return {
          status: "partial_success",
          items: [buildInvoiceResponse(firstInvoice)],
          failures: [
            {
              invoice_id: "INV-002",
              error_code: "invoice_already_submitted",
              detail: "invoice is already submitted",
            },
          ],
        };
      },
    });
    vi.spyOn(globalThis, "fetch").mockImplementation(fetchMock);

    renderWorkbenchRoute();

    await screen.findByRole("region", { name: "批量提交与撤回区" });
    act(() => {
      fireEvent.click(screen.getByRole("checkbox", { name: "批量选择发票 INV-001" }));
      fireEvent.click(screen.getByRole("checkbox", { name: "批量选择发票 INV-002" }));
      fireEvent.click(screen.getByRole("button", { name: "批量提交选中发票" }));
    });

    expect((await screen.findAllByText("批量提交部分成功：已处理 1 张，另有 1 张失败。")).length).toBeGreaterThanOrEqual(1);
    expect(await screen.findByText(/invoice is already submitted/)).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getAllByText("已提交管理员").length).toBeGreaterThanOrEqual(2);
    });
  });

  it("withdraws selected invoices and shows success feedback", async () => {
    const fetchMock = buildWorkbenchFetchMock({
      onWithdraw: ({ body, invoices }) => {
        expect(body.invoice_ids).toEqual(["INV-002"]);
        const secondInvoice = invoices.find((invoice) => invoice.id === "INV-002")!;
        secondInvoice.member_submission_status = "unsubmitted";
        secondInvoice.submitted_by_member_id = null;
        secondInvoice.submitted_at = null;
        return {
          status: "success",
          items: [buildInvoiceResponse(secondInvoice)],
          failures: [],
        };
      },
    });
    vi.spyOn(globalThis, "fetch").mockImplementation(fetchMock);

    renderWorkbenchRoute();

    await screen.findByRole("region", { name: "批量提交与撤回区" });
    act(() => {
      fireEvent.click(screen.getByRole("checkbox", { name: "批量选择发票 INV-002" }));
      fireEvent.click(screen.getByRole("button", { name: "批量撤回选中发票" }));
    });

    expect((await screen.findAllByText("批量撤回成功：共处理 1 张发票。")).length).toBeGreaterThanOrEqual(1);
    await waitFor(() => {
      expect(screen.getAllByText("未提交管理员").length).toBeGreaterThanOrEqual(2);
    });
  });
});
