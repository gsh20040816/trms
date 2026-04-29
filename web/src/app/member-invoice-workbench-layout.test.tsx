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

type FixtureInvoice = {
  id: string;
  material_id: string;
  invoice_number: string;
  amount_cents: number;
  expense_type: "railway" | "hotel";
  member_submission_status?: "unsubmitted" | "submitted";
};

type FixtureValidation = {
  rule_code: string;
  status: "passed" | "failed" | "pending";
  message: string;
};

type FixtureSplit = {
  id: string;
  member_id: string;
  amount_cents: number;
};

type FixtureConfirmation = {
  split_id: string;
  member_id: string;
  status: "pending" | "confirmed" | "disputed";
};

type FixtureMissingMaterial = {
  required_material_type: "payment_record" | "competition_notice" | "itinerary" | "order_screenshot" | "other_attachment";
  message: string;
};

type FixtureMaterial = {
  material_id: string;
  original_filename: string;
  created_at: string;
  recognition_status: "pending" | "succeeded" | "failed" | "needs_confirmation";
  material_type?: "invoice";
  validation_status?: "passed" | "failed" | "pending";
  validation_messages?: string[];
  invoice?: FixtureInvoice;
  validations?: FixtureValidation[];
  splits?: FixtureSplit[];
  confirmations?: FixtureConfirmation[];
  missing_materials?: FixtureMissingMaterial[];
};

type FixtureLinkageItem = {
  material_id: string;
  original_filename: string;
  pending_reason: "no_candidate" | "multiple_candidates";
  candidate_invoices: Array<{
    invoice_id: string;
    invoice_number: string;
    amount_cents: number;
    expense_type: "railway" | "hotel";
  }>;
};

type WorkbenchFixture = {
  materials: FixtureMaterial[];
  pending_linkage_items?: FixtureLinkageItem[];
};

function renderWorkbenchRoute(entry = "/member/invoices/workbench?taskId=TASK-OPEN") {
  const router = createMemoryRouter(routes, {
    initialEntries: [entry],
  });

  act(() => {
    render(<RouterProvider router={router} />);
  });
}

function buildMemberStatusCounts(materials: FixtureMaterial[]) {
  return {
    material_count: materials.length,
    missing_material_count: materials.reduce((count, item) => count + (item.missing_materials?.length ?? 0), 0),
    expense_detail_count: 0,
    recognition_pending_count: materials.filter((item) => item.recognition_status === "pending").length,
    recognition_succeeded_count: materials.filter((item) => item.recognition_status === "succeeded").length,
    recognition_failed_count: materials.filter((item) => item.recognition_status === "failed").length,
    recognition_needs_confirmation_count: materials.filter((item) => item.recognition_status === "needs_confirmation").length,
    validation_passed_count: materials.filter((item) => (item.validation_status ?? "passed") === "passed").length,
    validation_failed_count: materials.filter((item) => item.validation_status === "failed").length,
    validation_pending_count: materials.filter((item) => item.validation_status === "pending").length,
    validation_not_applicable_count: 0,
    confirmed_expense_count: 0,
    pending_confirmation_count: 0,
    disputed_confirmation_count: 0,
    missing_confirmation_count: 0,
  };
}

function buildRecognitionResponse(item: FixtureMaterial) {
  return {
    latest_effective: {
      id: `REC-${item.material_id}`,
      material_id: item.material_id,
      status: item.recognition_status,
      is_final_fact: false,
      failure: item.recognition_status === "failed"
        ? {
          stage: "ai",
          reason: "provider_error",
        }
        : null,
      raw_response: {},
      recognized_fields: {},
      manual_corrections: [],
      created_at: item.created_at,
      updated_at: item.created_at,
    },
    items: [],
  };
}

function buildWorkbenchFetchMock(fixture: WorkbenchFixture) {
  const invoices = fixture.materials
    .filter((item): item is FixtureMaterial & { invoice: FixtureInvoice } => Boolean(item.invoice))
    .map((item) => item.invoice);

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
          member_ids: ["2250001"],
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

    if (url === "/api/tasks/TASK-OPEN/member-status?actor_id=2250001" && method === "GET") {
      return Promise.resolve(jsonResponse({
        task_id: "TASK-OPEN",
        actor_id: "2250001",
        total_expense_amount_cents: invoices.reduce((sum, invoice) => sum + invoice.amount_cents, 0),
        counts: buildMemberStatusCounts(fixture.materials),
        materials: fixture.materials.map((item) => ({
          material_id: item.material_id,
          submitter_id: "2250001",
          material_type: item.material_type ?? "invoice",
          original_filename: item.original_filename,
          material_status: "assigned",
          recognition_status: item.recognition_status,
          recognition_failure_stage: item.recognition_status === "failed" ? "ai" : null,
          recognition_failure_reason: item.recognition_status === "failed" ? "provider_error" : null,
          invoice_id: item.invoice?.id ?? null,
          invoice_number: item.invoice?.invoice_number ?? null,
          validation_status: item.validation_status ?? "passed",
          validation_messages: item.validation_messages ?? [],
          created_at: item.created_at,
        })),
        missing_materials: fixture.materials.flatMap((item) => (
          (item.missing_materials ?? []).map((missingMaterial, index) => ({
            task_id: "TASK-OPEN",
            member_id: "2250001",
            invoice_id: item.invoice?.id ?? `MISSING-${item.material_id}`,
            invoice_number: item.invoice?.invoice_number ?? item.original_filename,
            expense_type: item.invoice?.expense_type ?? "railway",
            required_material_type: missingMaterial.required_material_type,
            source_rule_code: `fixture_missing_${index + 1}`,
            message: missingMaterial.message,
            evidence: {},
            detected_at: item.created_at,
          }))
        )),
        expense_details: [],
      }));
    }

    if (url === "/api/tasks/TASK-OPEN/shared-invoices?actor_id=2250001" && method === "GET") {
      return Promise.resolve(jsonResponse({
        task_id: "TASK-OPEN",
        actor_id: "2250001",
        items: [],
      }));
    }

    if (url === "/api/tasks/TASK-OPEN/supporting-material-linkage?actor_id=2250001" && method === "GET") {
      return Promise.resolve(jsonResponse({
        task_id: "TASK-OPEN",
        actor_id: "2250001",
        items: (fixture.pending_linkage_items ?? []).map((item) => ({
          material_id: item.material_id,
          submitter_id: "2250001",
          material_type: "payment_record",
          original_filename: item.original_filename,
          pending_reason: item.pending_reason,
          candidate_invoices: item.candidate_invoices,
          created_at: "2026-04-28T12:00:00+08:00",
        })),
      }));
    }

    if (url === "/api/tasks/TASK-OPEN/invoices" && method === "GET") {
      return Promise.resolve(jsonResponse({
        items: invoices.map((invoice) => ({
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
          member_submission_status: invoice.member_submission_status ?? "unsubmitted",
          submitted_by_member_id: invoice.member_submission_status === "submitted" ? "2250001" : null,
          submitted_at: invoice.member_submission_status === "submitted" ? "2026-04-29T12:00:00+08:00" : null,
          created_at: "2026-04-28T10:00:00+08:00",
          updated_at: "2026-04-28T10:05:00+08:00",
        })),
      }));
    }

    const materialRecognitionMatch = url.match(/^\/api\/materials\/([^/]+)\/recognition-tasks$/);
    if (materialRecognitionMatch && method === "GET") {
      const item = fixture.materials.find((entry) => entry.material_id === materialRecognitionMatch[1]);
      if (!item) {
        throw new Error(`Unknown material recognition request: ${url}`);
      }
      return Promise.resolve(jsonResponse(buildRecognitionResponse(item)));
    }

    const invoiceValidationMatch = url.match(/^\/api\/invoices\/([^/]+)\/validations$/);
    if (invoiceValidationMatch && method === "GET") {
      const item = fixture.materials.find((entry) => entry.invoice?.id === invoiceValidationMatch[1]);
      return Promise.resolve(jsonResponse({
        items: (item?.validations ?? []).map((validation, index) => ({
          id: `${invoiceValidationMatch[1]}-VAL-${index + 1}`,
          rule_code: validation.rule_code,
          target_type: "invoice",
          target_id: invoiceValidationMatch[1],
          severity: "blocker",
          status: validation.status,
          message: validation.message,
          evidence: {},
          created_at: item?.created_at ?? "2026-04-28T10:00:00+08:00",
        })),
      }));
    }

    const supportingMaterialMatch = url.match(/^\/api\/invoices\/([^/]+)\/supporting-materials$/);
    if (supportingMaterialMatch && method === "GET") {
      return Promise.resolve(jsonResponse({ items: [] }));
    }

    const splitMatch = url.match(/^\/api\/invoices\/([^/]+)\/splits$/);
    if (splitMatch && method === "GET") {
      const item = fixture.materials.find((entry) => entry.invoice?.id === splitMatch[1]);
      return Promise.resolve(jsonResponse({
        items: (item?.splits ?? []).map((split) => ({
          id: split.id,
          invoice_id: splitMatch[1],
          member_id: split.member_id,
          amount_cents: split.amount_cents,
          note: null,
          version: 1,
          is_active: true,
          created_at: item?.created_at ?? "2026-04-28T10:00:00+08:00",
          updated_at: item?.created_at ?? "2026-04-28T10:00:00+08:00",
        })),
      }));
    }

    const confirmationMatch = url.match(/^\/api\/invoices\/([^/]+)\/confirmations$/);
    if (confirmationMatch && method === "GET") {
      const item = fixture.materials.find((entry) => entry.invoice?.id === confirmationMatch[1]);
      return Promise.resolve(jsonResponse({
        items: (item?.confirmations ?? []).map((confirmation, index) => ({
          id: `${confirmation.split_id}-CONF-${index + 1}`,
          split_id: confirmation.split_id,
          member_id: confirmation.member_id,
          split_version: 1,
          split_amount_cents: item?.splits?.find((split) => split.id === confirmation.split_id)?.amount_cents ?? 0,
          split_note: null,
          is_current: true,
          status: confirmation.status,
          dispute_reason: confirmation.status === "disputed" ? "fixture dispute" : null,
          confirmed_at: item?.created_at ?? "2026-04-28T10:00:00+08:00",
          updated_at: item?.created_at ?? "2026-04-28T10:00:00+08:00",
        })),
      }));
    }

    throw new Error(`Unhandled fetch request: ${method} ${url}`);
  });
}

describe("MemberInvoiceWorkbenchPage layout grouping", () => {
  beforeEach(() => {
    clearMockSession();
    setMockSession("member");
  });

  afterEach(() => {
    vi.restoreAllMocks();
    clearMockSession();
  });

  it("shows the ready section empty state when every invoice is still blocked", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(buildWorkbenchFetchMock({
      materials: [
        {
          material_id: "MAT-PENDING-001",
          original_filename: "pending.pdf",
          created_at: "2026-04-28T10:00:00+08:00",
          recognition_status: "pending",
          invoice: {
            id: "INV-PENDING-001",
            material_id: "MAT-PENDING-001",
            invoice_number: "INV-PENDING-001",
            amount_cents: 8800,
            expense_type: "hotel",
          },
        },
      ],
    }));

    renderWorkbenchRoute();

    expect(await screen.findByText("当前还没有可直接提交的发票；先处理下面的问题分组。")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "识别中" })).toBeInTheDocument();
  });

  it("shows stable invoices in the ready section", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(buildWorkbenchFetchMock({
      materials: [
        {
          material_id: "MAT-READY-001",
          original_filename: "ready.pdf",
          created_at: "2026-04-28T10:00:00+08:00",
          recognition_status: "succeeded",
          invoice: {
            id: "INV-READY-001",
            material_id: "MAT-READY-001",
            invoice_number: "INV-READY-001",
            amount_cents: 6345,
            expense_type: "railway",
          },
        },
      ],
    }));

    renderWorkbenchRoute();

    const readySection = await screen.findByRole("region", { name: "可提交发票列表" });
    expect(within(readySection).getByRole("heading", { name: "INV-READY-001" })).toBeInTheDocument();
    expect(screen.getByText("当前没有识别或校验阻塞的发票；可以直接从上面的可提交区处理。")).toBeInTheDocument();
  });

  it("groups blocked invoices by their primary blocker", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(buildWorkbenchFetchMock({
      materials: [
        {
          material_id: "MAT-PENDING-001",
          original_filename: "pending.pdf",
          created_at: "2026-04-28T10:00:00+08:00",
          recognition_status: "pending",
          invoice: {
            id: "INV-PENDING-001",
            material_id: "MAT-PENDING-001",
            invoice_number: "INV-PENDING-001",
            amount_cents: 10000,
            expense_type: "railway",
          },
        },
        {
          material_id: "MAT-REVIEW-001",
          original_filename: "review.pdf",
          created_at: "2026-04-28T10:01:00+08:00",
          recognition_status: "needs_confirmation",
          invoice: {
            id: "INV-REVIEW-001",
            material_id: "MAT-REVIEW-001",
            invoice_number: "INV-REVIEW-001",
            amount_cents: 11000,
            expense_type: "hotel",
          },
        },
        {
          material_id: "MAT-LINK-001",
          original_filename: "link.pdf",
          created_at: "2026-04-28T10:02:00+08:00",
          recognition_status: "succeeded",
          invoice: {
            id: "INV-LINK-001",
            material_id: "MAT-LINK-001",
            invoice_number: "INV-LINK-001",
            amount_cents: 12000,
            expense_type: "railway",
          },
        },
        {
          material_id: "MAT-MISSING-001",
          original_filename: "missing.pdf",
          created_at: "2026-04-28T10:03:00+08:00",
          recognition_status: "succeeded",
          invoice: {
            id: "INV-MISSING-001",
            material_id: "MAT-MISSING-001",
            invoice_number: "INV-MISSING-001",
            amount_cents: 13000,
            expense_type: "hotel",
          },
          missing_materials: [
            {
              required_material_type: "payment_record",
              message: "缺少支付记录。",
            },
          ],
        },
        {
          material_id: "MAT-SPLIT-001",
          original_filename: "split.pdf",
          created_at: "2026-04-28T10:04:00+08:00",
          recognition_status: "succeeded",
          invoice: {
            id: "INV-SPLIT-001",
            material_id: "MAT-SPLIT-001",
            invoice_number: "INV-SPLIT-001",
            amount_cents: 14000,
            expense_type: "railway",
          },
          splits: [
            {
              id: "SPLIT-001",
              member_id: "2250001",
              amount_cents: 6000,
            },
          ],
        },
        {
          material_id: "MAT-CONFIRM-001",
          original_filename: "confirm.pdf",
          created_at: "2026-04-28T10:05:00+08:00",
          recognition_status: "succeeded",
          invoice: {
            id: "INV-CONFIRM-001",
            material_id: "MAT-CONFIRM-001",
            invoice_number: "INV-CONFIRM-001",
            amount_cents: 15000,
            expense_type: "hotel",
          },
          splits: [
            {
              id: "SPLIT-CONFIRM-001",
              member_id: "2250001",
              amount_cents: 15000,
            },
          ],
          confirmations: [
            {
              split_id: "SPLIT-CONFIRM-001",
              member_id: "2250001",
              status: "pending",
            },
          ],
        },
      ],
      pending_linkage_items: [
        {
          material_id: "MAT-PAY-001",
          original_filename: "payment.png",
          pending_reason: "multiple_candidates",
          candidate_invoices: [
            {
              invoice_id: "INV-LINK-001",
              invoice_number: "INV-LINK-001",
              amount_cents: 12000,
              expense_type: "railway",
            },
          ],
        },
      ],
    }));

    renderWorkbenchRoute();

    expect(within(await screen.findByRole("region", { name: "识别中 分组" })).getByRole("heading", { name: "INV-PENDING-001" })).toBeInTheDocument();
    expect(within(screen.getByRole("region", { name: "识别失败或待确认 分组" })).getByRole("heading", { name: "INV-REVIEW-001" })).toBeInTheDocument();
    expect(within(screen.getByRole("region", { name: "附件待关联 分组" })).getByRole("heading", { name: "INV-LINK-001" })).toBeInTheDocument();
    expect(within(screen.getByRole("region", { name: "缺失材料 分组" })).getByRole("heading", { name: "INV-MISSING-001" })).toBeInTheDocument();
    expect(within(screen.getByRole("region", { name: "分摊未完成 分组" })).getByRole("heading", { name: "INV-SPLIT-001" })).toBeInTheDocument();
    expect(within(screen.getByRole("region", { name: "确认未完成 分组" })).getByRole("heading", { name: "INV-CONFIRM-001" })).toBeInTheDocument();
  });

  it("switches the expanded detail panel when selecting another invoice card", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(buildWorkbenchFetchMock({
      materials: [
        {
          material_id: "MAT-READY-001",
          original_filename: "railway.pdf",
          created_at: "2026-04-28T11:00:00+08:00",
          recognition_status: "succeeded",
          invoice: {
            id: "INV-READY-001",
            material_id: "MAT-READY-001",
            invoice_number: "INV-READY-001",
            amount_cents: 6345,
            expense_type: "railway",
          },
        },
        {
          material_id: "MAT-READY-002",
          original_filename: "hotel.pdf",
          created_at: "2026-04-28T10:00:00+08:00",
          recognition_status: "succeeded",
          invoice: {
            id: "INV-READY-002",
            material_id: "MAT-READY-002",
            invoice_number: "INV-READY-002",
            amount_cents: 8800,
            expense_type: "hotel",
          },
        },
      ],
    }));

    renderWorkbenchRoute();

    const detailPanel = await screen.findByLabelText("成员发票工作台列表");
    expect(within(detailPanel).getByRole("heading", { name: "INV-READY-001" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /INV-READY-002/ }));

    expect(within(detailPanel).getByRole("heading", { name: "INV-READY-002" })).toBeInTheDocument();
  });
});
