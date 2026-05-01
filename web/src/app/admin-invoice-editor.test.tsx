import { act, fireEvent, render, screen, within } from "@testing-library/react";
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

function binaryResponse(body: BodyInit, init: ResponseInit = {}) {
  return new Response(body, {
    status: init.status ?? 200,
    headers: init.headers,
  });
}

function parseRequestJsonBody(init?: RequestInit): Record<string, unknown> {
  if (typeof init?.body !== "string") {
    throw new Error("Expected request body to be a JSON string.");
  }
  const parsed: unknown = JSON.parse(init.body);
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    throw new Error("Expected parsed JSON body to be an object.");
  }
  return parsed as Record<string, unknown>;
}

function buildTask() {
  return {
    id: "TASK-ALPHA",
    status: "reviewing",
    competition_name: "全国邀请赛",
    competition_location: "上海",
    competition_start_date: "2026-05-01",
    competition_end_date: "2026-05-03",
    deadline: "2026-05-10T18:00:00+08:00",
    member_ids: ["2250001", "2250002"],
    fee_categories: ["railway", "hotel"],
    administrator_id: "admin-1",
    project_info: "Project A",
    reimburser_info: "张管理员",
    invoice_title: "同济大学",
    tax_number: "91310000TEST00001",
    created_at: "2026-04-20T09:00:00+08:00",
    updated_at: "2026-04-25T10:00:00+08:00",
  };
}

function buildReviewSummary(options?: {
  withInvoice?: boolean;
  buyerNameSource?: "ocr" | "manual";
  buyerNameValue?: string;
}) {
  const withInvoice = options?.withInvoice ?? false;
  const buyerNameSource = options?.buyerNameSource ?? "ocr";
  const buyerNameValue = options?.buyerNameValue ?? "Tongji ACM Lab";

  return {
    task_id: "TASK-ALPHA",
    administrator_id: "admin-1",
    counts: {
      material_count: 1,
      invoice_count: withInvoice ? 1 : 0,
      validation_count: withInvoice ? 2 : 0,
      blocker_failed_validation_count: withInvoice ? 1 : 0,
      split_count: 0,
      confirmed_split_count: 0,
      pending_confirmation_count: 0,
      disputed_confirmation_count: 0,
      missing_confirmation_count: 0,
      pending_recognition_count: 0,
      failed_recognition_count: 0,
      needs_confirmation_recognition_count: 1,
    },
    materials: [
      {
        material: {
          id: "MAT-INV-1",
          status: "assigned",
          task_id: "TASK-ALPHA",
          submitter_id: "2250001",
          task_id_hint: null,
          submitter_id_hint: null,
          channel: "web",
          material_type: "invoice",
          storage_key: "TASK-ALPHA/MAT-INV-1-invoice.pdf",
          original_filename: "invoice.pdf",
          content_type: "application/pdf",
          size_bytes: 128,
          sha256: "a".repeat(64),
          duplicate_of: null,
          claimed_by: null,
          claimed_at: null,
          created_at: "2026-04-28T09:00:00+08:00",
        },
        latest_recognition: {
          id: "REC-INV-1",
          material_id: "MAT-INV-1",
          status: "needs_confirmation",
          is_final_fact: false,
          failure: null,
          raw_response: { provider: "placeholder-ai", document_type: "invoice" },
          recognized_fields: {
            invoice_number: {
              value: "AI-INV-001",
              source: "ai",
              confidence: 0.97,
              status: "recognized",
              updated_at: "2026-04-28T09:03:00+08:00",
            },
            buyer_name: {
              value: buyerNameValue,
              source: buyerNameSource,
              confidence: buyerNameSource === "manual" ? 1 : 0.43,
              status: buyerNameSource === "manual" ? "recognized" : "needs_confirmation",
              updated_at: "2026-04-28T09:04:00+08:00",
            },
            tax_number: {
              value: "WRONG-TAX",
              source: "ocr",
              confidence: 0.31,
              status: "needs_confirmation",
              updated_at: "2026-04-28T09:04:00+08:00",
            },
            amount_cents: {
              value: 12345,
              source: "ai",
              confidence: 0.96,
              status: "recognized",
              updated_at: "2026-04-28T09:05:00+08:00",
            },
            transaction_time: {
              value: "2026-04-21T09:30:00+08:00",
              source: "pdf_text",
              confidence: 0.88,
              status: "recognized",
              updated_at: "2026-04-28T09:05:00+08:00",
            },
            expense_type: {
              value: "railway",
              source: "ai",
              confidence: 0.93,
              status: "recognized",
              updated_at: "2026-04-28T09:05:00+08:00",
            },
          },
          manual_corrections: withInvoice
            ? [
              {
                id: "CORR-1",
                field_name: "buyer_name",
                actor_id: "admin-1",
                before: {
                  value: "Tongji ACM Lab",
                  source: "ocr",
                  confidence: 0.43,
                  status: "needs_confirmation",
                  updated_at: "2026-04-28T09:04:00+08:00",
                },
                after: {
                  value: "同济大学",
                  source: "manual",
                  confidence: 1,
                  status: "recognized",
                  updated_at: "2026-04-28T09:10:00+08:00",
                },
                revalidation_status: "triggered",
                corrected_at: "2026-04-28T09:10:00+08:00",
              },
            ]
            : [],
          created_at: "2026-04-28T09:01:00+08:00",
          updated_at: "2026-04-28T09:05:00+08:00",
        },
        invoice_id: withInvoice ? "INV-1" : null,
        supporting_invoice_ids: [],
      },
    ],
    invoices: withInvoice
      ? [
        {
          invoice: {
            id: "INV-1",
            task_id: "TASK-ALPHA",
            material_id: "MAT-INV-1",
            invoice_number: "AI-INV-001",
            issue_date: "2026-04-21",
            transaction_time: "2026-04-21T09:30:00+08:00",
            buyer_name: "同济大学",
            tax_number: "91310000TEST00001",
            seller_name: "中国铁路",
            corporate_transfer_reference: null,
            is_paper_invoice: false,
            paper_invoice_received: false,
            paper_invoice_received_at: null as string | null,
            paper_invoice_received_by: null as string | null,
            amount_cents: 12345,
            expense_type: "railway",
            created_at: "2026-04-28T09:10:00+08:00",
            updated_at: "2026-04-28T09:10:00+08:00",
          },
          supporting_material_ids: [],
          validations: [
            {
              id: "VAL-1",
              rule_code: "invoice_title_match",
              target_type: "invoice",
              target_id: "INV-1",
              severity: "blocker",
              status: "passed",
              message: "发票抬头匹配",
              evidence: {},
              created_at: "2026-04-28T09:10:00+08:00",
            },
            {
              id: "VAL-2",
              rule_code: "invoice_tax_number_match",
              target_type: "invoice",
              target_id: "INV-1",
              severity: "blocker",
              status: "failed",
              message: "税号不匹配",
              evidence: {},
              created_at: "2026-04-28T09:10:00+08:00",
            },
          ],
          splits: [],
        },
      ]
      : [],
  };
}

function renderAdminInvoiceEditorRoute(entry = "/admin/tasks/TASK-ALPHA/invoices") {
  const router = createMemoryRouter(routes, {
    initialEntries: [entry],
  });

  render(<RouterProvider router={router} />);
}

describe("admin invoice editor page", () => {
  const originalCreateObjectURL = URL.createObjectURL?.bind(URL);
  const originalRevokeObjectURL = URL.revokeObjectURL?.bind(URL);

  beforeEach(() => {
    clearMockSession();
    setMockSession("admin");

    Object.defineProperty(URL, "createObjectURL", {
      configurable: true,
      writable: true,
      value: vi.fn(() => "blob:invoice-preview-1"),
    });
    Object.defineProperty(URL, "revokeObjectURL", {
      configurable: true,
      writable: true,
      value: vi.fn(),
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
    clearMockSession();
    Object.defineProperty(URL, "createObjectURL", {
      configurable: true,
      writable: true,
      value: originalCreateObjectURL,
    });
    Object.defineProperty(URL, "revokeObjectURL", {
      configurable: true,
      writable: true,
      value: originalRevokeObjectURL,
    });
  });

  it("renders invoice material list, recognition field sources, and pending hints", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((input: string | URL | Request) => {
      const url = resolveRequestUrl(input);

      if (url === "/api/tasks/TASK-ALPHA") {
        return Promise.resolve(jsonResponse(buildTask()));
      }
      if (url === "/api/tasks/TASK-ALPHA/review-summary?actor_id=admin-1") {
        return Promise.resolve(jsonResponse(buildReviewSummary()));
      }
      if (url === "/api/materials/MAT-INV-1/content") {
        return Promise.resolve(binaryResponse("pdf-binary", {
          headers: {
            "Content-Type": "application/pdf",
            "Content-Disposition": 'inline; filename="invoice.pdf"',
          },
        }));
      }

      throw new Error(`Unhandled fetch URL in admin invoice editor render test: ${url}`);
    });

    renderAdminInvoiceEditorRoute("/admin/tasks/TASK-ALPHA/invoices?materialId=MAT-INV-1");

    expect(await screen.findByRole("heading", { name: "发票人工录入与更正" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "保存发票字段" })).toBeInTheDocument();
    expect(screen.getByDisplayValue("AI-INV-001")).toBeInTheDocument();
    expect(screen.getByDisplayValue("123.45")).toBeInTheDocument();

    const materialList = within(screen.getByLabelText("发票材料列表"));
    expect(materialList.getByText("invoice.pdf")).toBeInTheDocument();
    expect(materialList.getByText("票号 待补录")).toBeInTheDocument();
    expect(materialList.getByText("待录入")).toBeInTheDocument();

    const detailTabs = within(screen.getByRole("tablist", { name: "发票详情标签页" }));
    act(() => {
      fireEvent.click(detailTabs.getByRole("tab", { name: "识别字段" }));
    });
    expect(await screen.findByRole("heading", { name: "业务字段审核参考" })).toBeInTheDocument();
    expect(await screen.findByDisplayValue("Tongji ACM Lab")).toBeInTheDocument();
    expect(screen.getAllByText("系统已给出建议，但该字段仍需管理员人工确认或更正。").length).toBeGreaterThan(0);
    expect(screen.queryByText("来源：图片识别，置信度 43%")).not.toBeInTheDocument();
    expect(screen.getByText("待人工确认字段")).toBeInTheDocument();
    expect(screen.getByText("2")).toBeInTheDocument();
    expect(screen.getByText("展开调试与审计信息")).toBeInTheDocument();

    act(() => {
      fireEvent.click(detailTabs.getByRole("tab", { name: "校验异常" }));
    });
    expect(await screen.findByText("当前材料还没有对应发票校验结果；若这是首次录入，保存后会生成新的校验结果。")).toBeInTheDocument();

    act(() => {
      fireEvent.click(detailTabs.getByRole("tab", { name: "附件预览" }));
    });
    expect(await screen.findByLabelText("原始票据 PDF 预览")).toHaveAttribute("data", "blob:invoice-preview-1");
  });

  it("submits manual invoice entry, refreshes the summary, and shows refreshed validations", async () => {
    let reviewSummary = buildReviewSummary();

    vi.spyOn(globalThis, "fetch").mockImplementation((input: string | URL | Request, init?: RequestInit) => {
      const url = resolveRequestUrl(input);

      if (url === "/api/tasks/TASK-ALPHA") {
        return Promise.resolve(jsonResponse(buildTask()));
      }
      if (url === "/api/tasks/TASK-ALPHA/review-summary?actor_id=admin-1") {
        return Promise.resolve(jsonResponse(reviewSummary));
      }
      if (url === "/api/materials/MAT-INV-1/invoice" && init?.method === "POST") {
        const body = parseRequestJsonBody(init);
        expect(body["actor_id"]).toBe("admin-1");
        expect(body["invoice_number"]).toBe("AI-INV-001");
        expect(body["buyer_name"]).toBe("同济大学");
        expect(body["tax_number"]).toBe("91310000TEST00001");
        expect(body["corporate_transfer_reference"]).toBe("CORP-REF-001");
        expect(body["amount_cents"]).toBe(12345);
        expect(body["expense_type"]).toBe("railway");
        const transactionTime = body["transaction_time"];
        expect(
          typeof transactionTime === "string"
          && transactionTime.startsWith("2026-04-21T09:30:00"),
        ).toBe(true);

        reviewSummary = buildReviewSummary({
          withInvoice: true,
          buyerNameSource: "manual",
          buyerNameValue: "同济大学",
        });
        const refreshedInvoice = reviewSummary.invoices[0];
        if (!refreshedInvoice) {
          throw new Error("Expected refreshed invoice summary to exist.");
        }

        return Promise.resolve(jsonResponse({
          invoice: refreshedInvoice.invoice,
          validations: refreshedInvoice.validations,
        }, { status: 201 }));
      }

      throw new Error(`Unhandled fetch URL in admin invoice editor submit test: ${url}`);
    });

    renderAdminInvoiceEditorRoute();

    const buyerNameInput = await screen.findByDisplayValue("Tongji ACM Lab");
    fireEvent.change(buyerNameInput, {
      target: {
        value: "同济大学",
      },
    });
    fireEvent.change(screen.getByDisplayValue("WRONG-TAX"), {
      target: {
        value: "91310000TEST00001",
      },
    });
    fireEvent.change(screen.getByLabelText("公对公转账编号"), {
      target: {
        value: "CORP-REF-001",
      },
    });

    act(() => {
      fireEvent.click(screen.getByRole("button", { name: "保存发票字段" }));
    });

    expect(await screen.findByText("保存完成并已刷新校验结果")).toBeInTheDocument();
    expect(screen.getByText("发票 AI-INV-001 当前共有 2 条校验结果，其中失败 1 条、待确认 0 条。")).toBeInTheDocument();
    const detailTabs = within(screen.getByRole("tablist", { name: "发票详情标签页" }));
    act(() => {
      fireEvent.click(detailTabs.getByRole("tab", { name: "识别字段" }));
    });
    expect(await screen.findByDisplayValue("同济大学")).toBeInTheDocument();
    expect(screen.queryByText("来源：人工更正，置信度 100%")).not.toBeInTheDocument();

    act(() => {
      fireEvent.click(screen.getByText("展开调试与审计信息"));
    });
    expect(await screen.findByText("来源：人工更正，置信度 100%")).toBeInTheDocument();
    expect(await screen.findByText((content) => content.includes("已触发重新校验"))).toBeInTheDocument();

    act(() => {
      fireEvent.click(detailTabs.getByRole("tab", { name: "校验异常" }));
    });
    const validationList = within(screen.getByLabelText("发票校验结果列表"));
    expect(validationList.getByText("税号需要核对")).toBeInTheDocument();
    expect(validationList.getByText("税号不匹配")).toBeInTheDocument();
  });

  it("allows administrators to confirm receipt for paper invoices", async () => {
    let reviewSummary = buildReviewSummary({ withInvoice: true });
    reviewSummary.invoices[0]!.invoice.is_paper_invoice = true;
    reviewSummary.invoices[0]!.invoice.paper_invoice_received = false;
    reviewSummary.invoices[0]!.invoice.paper_invoice_received_at = null;
    reviewSummary.invoices[0]!.invoice.paper_invoice_received_by = null;

    vi.spyOn(globalThis, "fetch").mockImplementation((input: string | URL | Request, init?: RequestInit) => {
      const url = resolveRequestUrl(input);

      if (url === "/api/tasks/TASK-ALPHA") {
        return Promise.resolve(jsonResponse(buildTask()));
      }
      if (url === "/api/tasks/TASK-ALPHA/review-summary?actor_id=admin-1") {
        return Promise.resolve(jsonResponse(reviewSummary));
      }
      if (url === "/api/invoices/INV-1/paper-receipt" && init?.method === "PUT") {
        reviewSummary = buildReviewSummary({ withInvoice: true });
        reviewSummary.invoices[0]!.invoice.is_paper_invoice = true;
        reviewSummary.invoices[0]!.invoice.paper_invoice_received = true;
        reviewSummary.invoices[0]!.invoice.paper_invoice_received_at = "2026-04-28T09:20:00+08:00";
        reviewSummary.invoices[0]!.invoice.paper_invoice_received_by = "admin-1";
        return Promise.resolve(jsonResponse({
          invoice: reviewSummary.invoices[0]!.invoice,
          validations: [
            {
              id: "VAL-PAPER-1",
              rule_code: "invoice_paper_receipt_required",
              target_type: "invoice",
              target_id: "INV-1",
              severity: "blocker",
              status: "passed",
              message: "纸质发票已由管理员确认收到",
              evidence: {},
              created_at: "2026-04-28T09:20:00+08:00",
            },
          ],
        }));
      }

      throw new Error(`Unhandled fetch URL in admin paper receipt test: ${url}`);
    });

    renderAdminInvoiceEditorRoute();

    expect(await screen.findByRole("heading", { name: "纸票接收确认" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "确认已收到纸票" }));

    expect(await screen.findByText("已确认收票")).toBeInTheDocument();
  });

  it("shows validation helper text and does not submit when required fields are empty", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((input: string | URL | Request, init?: RequestInit) => {
      const url = resolveRequestUrl(input);

      if (url === "/api/tasks/TASK-ALPHA") {
        return Promise.resolve(jsonResponse(buildTask()));
      }
      if (url === "/api/tasks/TASK-ALPHA/review-summary?actor_id=admin-1") {
        return Promise.resolve(jsonResponse(buildReviewSummary()));
      }
      if (url === "/api/materials/MAT-INV-1/invoice" && init?.method === "POST") {
        throw new Error("Expected validation to prevent the invoice submit request.");
      }

      throw new Error(`Unhandled fetch URL in admin invoice editor validation test: ${url}`);
    });

    renderAdminInvoiceEditorRoute();

    fireEvent.change(await screen.findByLabelText("发票号码"), {
      target: { value: "" },
    });
    fireEvent.change(screen.getByLabelText("发票抬头"), {
      target: { value: "" },
    });
    fireEvent.change(screen.getByLabelText("税号"), {
      target: { value: "" },
    });
    fireEvent.change(screen.getByLabelText("金额（元）"), {
      target: { value: "" },
    });

    fireEvent.click(screen.getByRole("button", { name: "保存发票字段" }));

    expect(await screen.findByText("发票号码不能为空。")).toBeInTheDocument();
    expect(screen.getByText("发票抬头不能为空。")).toBeInTheDocument();
    expect(screen.getByText("税号不能为空。")).toBeInTheDocument();
    expect(screen.getByText("请输入大于 0 的金额，单位为元。")).toBeInTheDocument();
  });

  it("groups editable form fields by business review order", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((input: string | URL | Request) => {
      const url = resolveRequestUrl(input);

      if (url === "/api/tasks/TASK-ALPHA") {
        return Promise.resolve(jsonResponse(buildTask()));
      }
      if (url === "/api/tasks/TASK-ALPHA/review-summary?actor_id=admin-1") {
        return Promise.resolve(jsonResponse(buildReviewSummary()));
      }

      throw new Error(`Unhandled fetch URL in admin invoice editor grouping test: ${url}`);
    });

    renderAdminInvoiceEditorRoute();

    expect(await screen.findByRole("heading", { name: "票据核心字段" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "抬头与税号" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "报销归类与补充信息" })).toBeInTheDocument();
    expect(screen.getByText("先核对票号、金额和日期，再处理后续抬头与费用归类，避免在多个标签页之间来回切换。")).toBeInTheDocument();
  });

  it("shows an error notice when the backend rejects the invoice update", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((input: string | URL | Request, init?: RequestInit) => {
      const url = resolveRequestUrl(input);

      if (url === "/api/tasks/TASK-ALPHA") {
        return Promise.resolve(jsonResponse(buildTask()));
      }
      if (url === "/api/tasks/TASK-ALPHA/review-summary?actor_id=admin-1") {
        return Promise.resolve(jsonResponse(buildReviewSummary()));
      }
      if (url === "/api/materials/MAT-INV-1/invoice" && init?.method === "POST") {
        return Promise.resolve(jsonResponse(
          {
            detail: "invoice expense type railway is not allowed for task; allowed fee categories: hotel",
          },
          { status: 409 },
        ));
      }

      throw new Error(`Unhandled fetch URL in admin invoice editor rejection test: ${url}`);
    });

    renderAdminInvoiceEditorRoute();

    fireEvent.click(await screen.findByRole("button", { name: "保存发票字段" }));

    expect(await screen.findByRole("heading", { name: "操作未完成" })).toBeInTheDocument();
    expect(screen.getByText("当前发票费用类型“铁路交通”不在任务允许范围内；当前任务只允许：住宿费。")).toBeInTheDocument();
  });
});
