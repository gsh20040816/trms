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

function resolveRequestMethod(input: string | URL | Request, init: RequestInit | undefined) {
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

function renderRoute(entry = "/member/invoices/workbench?taskId=TASK-OPEN") {
  const router = createMemoryRouter(routes, {
    initialEntries: [entry],
  });

  act(() => {
    render(<RouterProvider router={router} />);
  });

  return router;
}

const task = {
  id: "TASK-OPEN",
  status: "open",
  competition_name: "ICPC 区域赛",
  competition_location: "武汉",
  competition_start_date: "2026-05-01",
  competition_end_date: "2026-05-03",
  deadline: "2026-05-10T12:00:00+08:00",
  email_submission_key: "icpc-wuhan",
  submission_key: "icpc-wuhan",
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

const invoice = {
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

function buildWorkbenchSummary(overrides: Partial<Record<string, unknown>> = {}) {
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
      materials: [
        {
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
      ],
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
        confirmations: [
          {
            id: "CONF-001",
            split_id: "SPLIT-001",
            member_id: "2250001",
            split_version: 1,
            split_amount_cents: 12345,
            split_note: null,
            is_current: true,
            status: "confirmed",
            dispute_reason: null,
            confirmed_at: "2026-04-28T10:00:00+08:00",
            updated_at: "2026-04-28T10:00:00+08:00",
          },
        ],
        related_expense_details: [],
        missing_materials: [],
        queue_group: "ready",
        blocking_reasons: [],
        ready_for_submission: true,
      },
    ],
    pending_supporting_material_linkage_items: [],
    shared_invoices: [],
    ...overrides,
  };
}

function mockCommonFetch(summary = buildWorkbenchSummary()) {
  return vi.spyOn(globalThis, "fetch").mockImplementation((input: string | URL | Request, init?: RequestInit) => {
    const url = resolveRequestUrl(input);
    const method = resolveRequestMethod(input, init);

    if (url === "/api/tasks" && method === "GET") {
      return Promise.resolve(jsonResponse([task]));
    }
    if (url === "/api/tasks/TASK-OPEN" && method === "GET") {
      return Promise.resolve(jsonResponse(task));
    }
    if (url === "/api/tasks/TASK-OPEN/member-workbench?actor_id=2250001" && method === "GET") {
      return Promise.resolve(jsonResponse(summary));
    }
    if (url === "/api/system/submission-guide" && method === "GET") {
      return Promise.resolve(jsonResponse({
        email_submission_address: "submit@example.edu",
        telegram_bot_url: "https://t.me/trms_bot",
      }));
    }
    if (url === "/api/tasks/TASK-OPEN/paper-invoices" && method === "POST") {
      return Promise.resolve(jsonResponse({
        invoice: {
          ...invoice,
          id: "INV-PAPER-001",
          material_id: "MAT-PAPER-001",
          invoice_number: "PAPER-001",
          expense_type: "registration",
          is_paper_invoice: true,
          paper_invoice_received: false,
          paper_invoice_received_at: null,
          paper_invoice_received_by: null,
        },
        validations: [
          {
            id: "VAL-PAPER-001",
            rule_code: "invoice_paper_receipt_required",
            target_type: "invoice",
            target_id: "INV-PAPER-001",
            severity: "blocker",
            status: "failed",
            message: "纸质发票待管理员确认已收到纸票",
            evidence: {},
            created_at: "2026-04-28T11:00:00+08:00",
          },
        ],
      }));
    }
    if (url === "/api/tasks/TASK-OPEN/invoice-submissions" && method === "POST") {
      return Promise.resolve(jsonResponse({
        status: "success",
        items: [{ ...invoice, member_submission_status: "submitted", submitted_by_member_id: "2250001", submitted_at: "2026-04-28T11:00:00+08:00" }],
        failures: [],
      }));
    }
    if (url.startsWith("/api/invoices/") && url.includes("/supporting-materials/") && method === "PUT") {
      return Promise.resolve(jsonResponse({
        item: {
          id: "MAT-PAY-001",
        },
      }));
    }

    throw new Error(`Unhandled fetch request: ${method} ${url}`);
  });
}

describe("MemberInvoiceWorkbenchPage", () => {
  beforeEach(() => {
    clearMockSession();
    setMockSession("member");
  });

  afterEach(() => {
    vi.restoreAllMocks();
    clearMockSession();
  });

  it("keeps the workbench concise and links invoice summary rows to the per-invoice page", async () => {
    mockCommonFetch();
    const router = renderRoute("/member/invoices/workbench?taskId=TASK-OPEN#member-workbench-invoices");

    expect(await screen.findByRole("heading", { name: "比赛报销项目" })).toBeInTheDocument();
    expect(await screen.findByRole("region", { name: "材料提交说明" })).toHaveTextContent("网页");
    expect(screen.getByRole("region", { name: "材料提交说明" })).toHaveTextContent("<icpc-wuhan>");
    expect(screen.getByRole("region", { name: "材料提交说明" })).toHaveTextContent("先在个人信息页绑定发件邮箱");
    expect(screen.getByRole("region", { name: "材料提交说明" })).toHaveTextContent("submit@example.edu");
    expect(screen.getByRole("link", { name: "绑定邮箱" })).toHaveAttribute("href", "/profile");
    expect(screen.getByRole("link", { name: "Telegram Bot" })).toHaveAttribute("href", "https://t.me/trms_bot");
    expect(screen.getByRole("region", { name: "材料提交说明" })).toHaveTextContent("/task icpc-wuhan");
    expect(screen.getByRole("complementary", { name: "用户工作台分类" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /工作状态/ })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /上传页面/ })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /材料查看页面/ })).toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: "需要处理的发票列表" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "展开的发票详情" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "发票字段" })).not.toBeInTheDocument();
    expect(screen.getByRole("region", { name: "可提交材料列表" })).not.toHaveClass("member-status-section-warning");
    expect(screen.getByRole("region", { name: "问题材料分组" })).toHaveClass("member-status-section-warning");

    const readySection = screen.getByRole("region", { name: "未提交材料列表" });
    fireEvent.click(within(readySection).getByRole("button", { name: /未提交材料 ready\.pdf INV-READY-001/ }));

    await waitFor(() => {
      expect(router.state.location.pathname).toBe("/member/invoices/INV-READY-001");
    });
  });

  it("submits selected ready invoices from the workbench", async () => {
    mockCommonFetch();
    renderRoute("/member/invoices/workbench?taskId=TASK-OPEN#member-workbench-invoices");

    expect(await screen.findByText("未提交列表已选 0 / 1")).toBeInTheDocument();
    fireEvent.click(screen.getByLabelText("批量选择发票 INV-READY-001"));
    fireEvent.click(screen.getByRole("button", { name: "批量提交选中发票" }));

    expect(await screen.findByText("批量提交成功：共处理 1 张发票。")).toBeInTheDocument();
  });

  it("shows pending supporting materials inside problem material groups instead of a standalone section", async () => {
    mockCommonFetch(buildWorkbenchSummary({
      items: [
        ...buildWorkbenchSummary().items,
        {
          material: {
            material_id: "MAT-PAY-001",
            submitter_id: "2250001",
            material_type: "payment_record",
            original_filename: "pay.png",
            material_status: "assigned",
            recognition_status: "succeeded",
            recognition_failure_stage: null,
            recognition_failure_reason: null,
            invoice_id: null,
            invoice_number: null,
            validation_status: "passed",
            validation_messages: [],
            created_at: "2026-04-28T11:00:00+08:00",
          },
          invoice: null,
          recognition: {
            id: "REC-PAY-001",
            material_id: "MAT-PAY-001",
            status: "succeeded",
            failure: null,
            recognized_fields: {
              material_type: { value: "payment_record", source: "ai", confidence: 0.99, status: "recognized", updated_at: null },
              amount_cents: { value: 12345, source: "ai", confidence: 0.99, status: "recognized", updated_at: null },
            },
            manual_corrections: [],
            created_at: "2026-04-28T11:00:00+08:00",
            updated_at: "2026-04-28T11:00:00+08:00",
          },
          validations: [],
          supporting_materials: [],
          splits: [],
          confirmations: [],
          related_expense_details: [],
          missing_materials: [],
          queue_group: "ready",
          blocking_reasons: [],
          ready_for_submission: true,
        },
      ],
      pending_supporting_material_linkage_items: [
        {
          material_id: "MAT-LINKED-001",
          submitter_id: "2250001",
          material_type: "payment_record",
          original_filename: "linked-pay.png",
          pending_reason: "multiple_candidates",
          linked_invoices: [
            {
              invoice_id: "INV-LINKED-001",
              invoice_number: "INV-LINKED-001",
              amount_cents: 8000,
              expense_type: "hotel",
              original_filename: "linked.pdf",
            },
          ],
          candidate_invoices: [
            {
              invoice_id: "INV-READY-001",
              invoice_number: "INV-READY-001",
              amount_cents: 12345,
              expense_type: "railway",
              original_filename: "ready.pdf",
            },
          ],
          created_at: "2026-04-28T10:30:00+08:00",
        },
        {
          material_id: "MAT-PAY-001",
          submitter_id: "2250001",
          material_type: "payment_record",
          original_filename: "pay.png",
          pending_reason: "multiple_candidates",
          linked_invoices: [],
          candidate_invoices: [
            {
              invoice_id: "INV-READY-001",
              invoice_number: "INV-READY-001",
              amount_cents: 12345,
              expense_type: "railway",
              original_filename: "ready.pdf",
            },
            {
              invoice_id: "INV-SECOND-001",
              invoice_number: "INV-SECOND-001",
              amount_cents: 54321,
              expense_type: "hotel",
              original_filename: "second.pdf",
            },
          ],
          created_at: "2026-04-28T11:00:00+08:00",
        },
      ],
    }));
    renderRoute("/member/invoices/workbench?taskId=TASK-OPEN#member-workbench-invoices");

    expect(await screen.findByRole("heading", { name: "问题材料" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "待关联辅助材料" })).not.toBeInTheDocument();
    const problemSection = screen.getByRole("region", { name: "问题材料分组" });
    expect(within(problemSection).getByRole("region", { name: "附件待关联 分组" })).toBeInTheDocument();
    expect(within(problemSection).getByRole("button", { name: /附件待关联 支付记录 pay\.png/ })).toBeInTheDocument();
    expect(within(problemSection).queryByRole("checkbox", { name: /批量选择发票/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("combobox", { name: "归属发票" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "展开的发票详情" })).not.toBeInTheDocument();
  });

  it("routes pending supporting materials from problem material groups to the dedicated material detail page", async () => {
    mockCommonFetch(buildWorkbenchSummary({
      items: [
        ...buildWorkbenchSummary().items,
        {
          material: {
            material_id: "MAT-PAY-001",
            submitter_id: "2250001",
            material_type: "payment_record",
            original_filename: "pay.png",
            material_status: "assigned",
            recognition_status: "succeeded",
            recognition_failure_stage: null,
            recognition_failure_reason: null,
            invoice_id: null,
            invoice_number: null,
            validation_status: "passed",
            validation_messages: [],
            created_at: "2026-04-28T10:00:00+08:00",
          },
          invoice: null,
          recognition: {
            id: "REC-PAY-001",
            material_id: "MAT-PAY-001",
            status: "succeeded",
            failure: null,
            recognized_fields: {
              material_type: { value: "payment_record", source: "ai", confidence: 0.99, status: "recognized", updated_at: null },
              amount_cents: { value: 308700, source: "ai", confidence: 0.96, status: "recognized", updated_at: null },
            },
            manual_corrections: [],
            created_at: "2026-04-28T10:00:00+08:00",
            updated_at: "2026-04-28T10:00:00+08:00",
          },
          validations: [],
          supporting_materials: [],
          splits: [],
          confirmations: [],
          related_expense_details: [],
          missing_materials: [],
          queue_group: "ready",
          blocking_reasons: [],
          ready_for_submission: true,
        },
      ],
      pending_supporting_material_linkage_items: [
        {
          material_id: "MAT-PAY-001",
          submitter_id: "2250001",
          material_type: "payment_record",
          original_filename: "pay.png",
          pending_reason: "manual_confirmation_required",
          linked_invoices: [],
          candidate_invoices: [
            {
              invoice_id: "INV-READY-001",
              invoice_number: "INV-READY-001",
              amount_cents: 12345,
              expense_type: "railway",
              original_filename: "ready.pdf",
            },
          ],
          created_at: "2026-04-28T10:00:00+08:00",
        },
      ],
    }));
    const router = renderRoute("/member/invoices/workbench?taskId=TASK-OPEN#member-workbench-invoices");

    const problemSection = await screen.findByRole("region", { name: "问题材料分组" });
    fireEvent.click(within(problemSection).getByRole("button", { name: /附件待关联 支付记录 pay\.png/ }));

    await waitFor(() => {
      expect(router.state.location.pathname).toBe("/member/materials/MAT-PAY-001");
    });
  });

  it("shows ready non-invoice materials inside the unsubmitted material list without batch checkbox", async () => {
    mockCommonFetch(buildWorkbenchSummary({
      items: [
        ...buildWorkbenchSummary().items,
        {
          material: {
            material_id: "MAT-PAY-001",
            submitter_id: "2250001",
            material_type: "payment_record",
            original_filename: "pay.png",
            material_status: "assigned",
            recognition_status: "succeeded",
            recognition_failure_stage: null,
            recognition_failure_reason: null,
            invoice_id: null,
            invoice_number: null,
            validation_status: "passed",
            validation_messages: [],
            created_at: "2026-04-28T10:00:00+08:00",
          },
          invoice: null,
          recognition: {
            id: "REC-PAY-001",
            material_id: "MAT-PAY-001",
            status: "succeeded",
            failure: null,
            recognized_fields: {
              amount_cents: {
                value: 12345,
                source: "ai",
                confidence: 0.76,
                status: "recognized",
                updated_at: "2026-04-28T10:05:00+08:00",
              },
              material_type: {
                value: "payment_record",
                source: "ai",
                confidence: 0.99,
                status: "recognized",
                updated_at: "2026-04-28T10:05:00+08:00",
              },
            },
            manual_corrections: [],
            created_at: "2026-04-28T10:00:00+08:00",
            updated_at: "2026-04-28T10:05:00+08:00",
          },
          validations: [],
          supporting_materials: [],
          splits: [],
          confirmations: [],
          related_expense_details: [],
          missing_materials: [],
          queue_group: "ready",
          blocking_reasons: [],
          ready_for_submission: true,
        },
      ],
      pending_supporting_material_linkage_items: [],
    }));

    renderRoute("/member/invoices/workbench?taskId=TASK-OPEN#member-workbench-invoices");

    const readySection = await screen.findByRole("region", { name: "未提交材料列表" });
    expect(within(readySection).getByRole("button", { name: /未提交材料 支付记录 pay\.png/ })).toBeInTheDocument();
    expect(within(readySection).queryByRole("checkbox", { name: /批量选择发票 pay\.png/ })).not.toBeInTheDocument();
    expect(within(readySection).getByText("校验跟随发票")).toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "问题材料分组" })).toHaveTextContent("当前无问题材料");
  });

  it("moves linked supporting materials into the submitted material list when their invoice is submitted", async () => {
    mockCommonFetch(buildWorkbenchSummary({
      items: [
        {
          ...buildWorkbenchSummary().items[0],
          supporting_materials: [
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
              size_bytes: 8,
              sha256: "b".repeat(64),
              duplicate_of: null,
              claimed_by: null,
              claimed_at: null,
              created_at: "2026-04-28T09:30:00+08:00",
            },
          ],
        },
        {
          material: {
            material_id: "MAT-PAY-001",
            submitter_id: "2250001",
            material_type: "payment_record",
            original_filename: "pay.png",
            material_status: "assigned",
            recognition_status: "succeeded",
            recognition_failure_stage: null,
            recognition_failure_reason: null,
            invoice_id: null,
            invoice_number: null,
            validation_status: "passed",
            validation_messages: [],
            created_at: "2026-04-28T09:30:00+08:00",
          },
          invoice: null,
          recognition: {
            id: "REC-PAY-001",
            material_id: "MAT-PAY-001",
            status: "succeeded",
            failure: null,
            recognized_fields: {
              material_type: { value: "payment_record", source: "ai", confidence: 0.99, status: "recognized", updated_at: null },
            },
            manual_corrections: [],
            created_at: "2026-04-28T09:30:00+08:00",
            updated_at: "2026-04-28T09:30:00+08:00",
          },
          validations: [],
          supporting_materials: [],
          splits: [],
          confirmations: [],
          related_expense_details: [],
          missing_materials: [],
          queue_group: "ready",
          blocking_reasons: [],
          ready_for_submission: true,
        },
      ],
      report: {
        ...buildWorkbenchSummary().report,
        counts: {
          ...buildWorkbenchSummary().report.counts,
          material_count: 2,
          recognition_succeeded_count: 2,
          validation_passed_count: 2,
        },
        materials: [
          ...buildWorkbenchSummary().report.materials,
          {
            material_id: "MAT-PAY-001",
            submitter_id: "2250001",
            material_type: "payment_record",
            original_filename: "pay.png",
            material_status: "assigned",
            recognition_status: "succeeded",
            recognition_failure_stage: null,
            recognition_failure_reason: null,
            invoice_id: null,
            invoice_number: null,
            validation_status: "passed",
            validation_messages: [],
            created_at: "2026-04-28T09:30:00+08:00",
          },
        ],
      },
    }));
    renderRoute("/member/invoices/workbench?taskId=TASK-OPEN#member-workbench-invoices");

    const readySection = await screen.findByRole("region", { name: "未提交材料列表" });
    expect(within(readySection).getByText("已关联到发票 INV-READY-001；选择该发票时会一并提交此附件。")).toBeInTheDocument();
  });

  it("shows a disabled gray checkbox for linked supporting materials and syncs its checked state with the parent invoice", async () => {
    mockCommonFetch(buildWorkbenchSummary({
      items: [
        {
          ...buildWorkbenchSummary().items[0],
          supporting_materials: [
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
              size_bytes: 8,
              sha256: "b".repeat(64),
              duplicate_of: null,
              claimed_by: null,
              claimed_at: null,
              created_at: "2026-04-28T09:30:00+08:00",
            },
          ],
        },
        {
          material: {
            material_id: "MAT-PAY-001",
            submitter_id: "2250001",
            material_type: "payment_record",
            original_filename: "pay.png",
            material_status: "assigned",
            recognition_status: "succeeded",
            recognition_failure_stage: null,
            recognition_failure_reason: null,
            invoice_id: null,
            invoice_number: null,
            validation_status: "passed",
            validation_messages: [],
            created_at: "2026-04-28T09:30:00+08:00",
          },
          invoice: null,
          recognition: {
            id: "REC-PAY-001",
            material_id: "MAT-PAY-001",
            status: "succeeded",
            failure: null,
            recognized_fields: {
              material_type: { value: "payment_record", source: "ai", confidence: 0.99, status: "recognized", updated_at: null },
            },
            manual_corrections: [],
            created_at: "2026-04-28T09:30:00+08:00",
            updated_at: "2026-04-28T09:30:00+08:00",
          },
          validations: [],
          supporting_materials: [],
          splits: [],
          confirmations: [],
          related_expense_details: [],
          missing_materials: [],
          queue_group: "ready",
          blocking_reasons: [],
          ready_for_submission: true,
        },
      ],
      report: {
        ...buildWorkbenchSummary().report,
        counts: {
          ...buildWorkbenchSummary().report.counts,
          material_count: 2,
          recognition_succeeded_count: 2,
          validation_passed_count: 2,
        },
        materials: [
          ...buildWorkbenchSummary().report.materials,
          {
            material_id: "MAT-PAY-001",
            submitter_id: "2250001",
            material_type: "payment_record",
            original_filename: "pay.png",
            material_status: "assigned",
            recognition_status: "succeeded",
            recognition_failure_stage: null,
            recognition_failure_reason: null,
            invoice_id: null,
            invoice_number: null,
            validation_status: "passed",
            validation_messages: [],
            created_at: "2026-04-28T09:30:00+08:00",
          },
        ],
      },
    }));
    renderRoute("/member/invoices/workbench?taskId=TASK-OPEN#member-workbench-invoices");

    const readySection = await screen.findByRole("region", { name: "未提交材料列表" });
    const attachmentCheckbox = within(readySection).getByRole("checkbox", { name: "关联附件随发票提交 pay.png" });
    expect(attachmentCheckbox).toBeDisabled();
    expect(attachmentCheckbox).not.toBeChecked();

    fireEvent.click(within(readySection).getByRole("checkbox", { name: "批量选择发票 INV-READY-001" }));
    expect(attachmentCheckbox).toBeChecked();
  });

  it("allows members to create a paper invoice from the workbench", async () => {
    const fetchSpy = mockCommonFetch(buildWorkbenchSummary({
      items: [],
      report: {
        ...buildWorkbenchSummary().report,
        materials: [],
        counts: {
          ...buildWorkbenchSummary().report.counts,
          material_count: 0,
        },
      },
    }));
    const router = renderRoute("/member/invoices/workbench?taskId=TASK-OPEN#member-workbench-invoices");

    expect(await screen.findByRole("heading", { name: "手动录入纸质发票" })).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("金额（元）"), { target: { value: "88.00" } });
    fireEvent.click(screen.getByRole("button", { name: "新增纸质发票" }));

    await waitFor(() => {
      expect(router.state.location.pathname).toBe("/member/invoices/INV-PAPER-001");
    });
    const paperInvoiceRequest = fetchSpy.mock.calls.find(([input, init]) => (
      resolveRequestUrl(input) === "/api/tasks/TASK-OPEN/paper-invoices"
      && resolveRequestMethod(input, init) === "POST"
    ));
    expect(paperInvoiceRequest).toBeDefined();
    const requestInit = paperInvoiceRequest?.[1];
    const requestBody = typeof requestInit?.body === "string" ? requestInit.body : "";
    expect(JSON.parse(requestBody)).toEqual({
      actor_id: "2250001",
      amount_cents: 8800,
      expense_type: "railway",
    });
  });

  it("hides paper receipt confirmation blockers before member submission", async () => {
    const baseSummary = buildWorkbenchSummary();
    const [baseItem] = baseSummary.items;
    const [baseMaterial] = baseSummary.report.materials;
    if (!baseItem || !baseMaterial || !baseItem.invoice) {
      throw new Error("Expected default workbench summary to include one invoice item.");
    }

    mockCommonFetch(buildWorkbenchSummary({
      items: [
        {
          ...baseItem,
          material: {
            ...baseItem.material,
            original_filename: "paper.pdf",
            validation_status: "failed",
          },
          invoice: {
            ...baseItem.invoice,
            id: "INV-PAPER-READY-001",
            material_id: "MAT-PAPER-READY-001",
            invoice_number: "PAPER-READY-001",
            expense_type: "registration",
            is_paper_invoice: true,
            paper_invoice_received: false,
            paper_invoice_received_at: null,
            paper_invoice_received_by: null,
          },
          validations: [
            {
              id: "VAL-PAPER-ONLY-001",
              rule_code: "invoice_paper_receipt_required",
              target_type: "invoice",
              target_id: "INV-PAPER-READY-001",
              severity: "blocker",
              status: "failed",
              message: "纸质发票待管理员确认已收到纸票",
              evidence: {},
              created_at: "2026-04-28T11:00:00+08:00",
            },
          ],
          queue_group: "ready",
          blocking_reasons: [],
          ready_for_submission: true,
        },
      ],
      report: {
        ...baseSummary.report,
        materials: [
          {
            ...baseMaterial,
            material_id: "MAT-PAPER-READY-001",
            original_filename: "paper.pdf",
            invoice_id: "INV-PAPER-READY-001",
            invoice_number: "PAPER-READY-001",
            validation_status: "failed",
          },
        ],
      },
    }));

    renderRoute("/member/invoices/workbench?taskId=TASK-OPEN#member-workbench-invoices");

    const readySection = await screen.findByRole("region", { name: "未提交材料列表" });
    expect(within(readySection).getByText("paper.pdf")).toBeInTheDocument();
    expect(within(readySection).queryByText("纸质发票待管理员确认已收到纸票")).not.toBeInTheDocument();
    expect(within(readySection).queryByText("校验失败")).not.toBeInTheDocument();
    expect(within(readySection).getByText("校验通过")).toBeInTheDocument();
  });

  it("marks problem invoices with emphasis while keeping the list collapsed to one-line summaries", async () => {
    mockCommonFetch(buildWorkbenchSummary({
      items: [
        {
          material: {
            material_id: "MAT-PROBLEM-001",
            submitter_id: "2250001",
            material_type: "invoice",
            original_filename: "problem.pdf",
            material_status: "assigned",
            recognition_status: "needs_confirmation",
            recognition_failure_stage: null,
            recognition_failure_reason: null,
            invoice_id: "INV-PROBLEM-001",
            invoice_number: "INV-PROBLEM-001",
            validation_status: "pending",
            validation_messages: [],
            created_at: "2026-04-28T10:00:00+08:00",
          },
          invoice: {
            ...invoice,
            id: "INV-PROBLEM-001",
            material_id: "MAT-PROBLEM-001",
            invoice_number: "INV-PROBLEM-001",
            member_submission_status: "unsubmitted",
          },
          recognition: {
            id: "REC-PROBLEM-001",
            material_id: "MAT-PROBLEM-001",
            status: "needs_confirmation",
            failure: null,
            recognized_fields: {},
            manual_corrections: [],
            created_at: "2026-04-28T10:00:00+08:00",
            updated_at: "2026-04-28T10:00:00+08:00",
          },
          validations: [],
          supporting_materials: [],
          splits: [],
          confirmations: [],
          related_expense_details: [],
          missing_materials: [],
          queue_group: "recognition_review",
          blocking_reasons: ["recognition_review"],
          ready_for_submission: false,
        },
      ],
      report: {
        ...buildWorkbenchSummary().report,
        counts: {
          ...buildWorkbenchSummary().report.counts,
          recognition_needs_confirmation_count: 1,
          validation_pending_count: 1,
        },
      },
    }));
    renderRoute("/member/invoices/workbench?taskId=TASK-OPEN#member-workbench-invoices");

    const problemSection = await screen.findByRole("region", { name: "问题材料分组" });
    const summaryList = within(problemSection).getByRole("list", { name: "识别失败或待确认 材料摘要列表" });
    expect(within(summaryList).getByRole("button", { name: /识别失败或待确认 problem\.pdf INV-PROBLEM-001/ })).toBeInTheDocument();
    expect(within(summaryList).getAllByText("识别失败或待确认").length).toBeGreaterThanOrEqual(1);
    expect(within(summaryList).queryByRole("button", { name: "批量提交选中发票" })).not.toBeInTheDocument();
  });

  it("does not move non-invoice supporting materials with needs-confirmation recognition into problem groups", async () => {
    mockCommonFetch(buildWorkbenchSummary({
      items: [
        {
          material: {
            material_id: "MAT-PAYMENT-001",
            submitter_id: "2250001",
            material_type: "payment_record",
            original_filename: "Screenshot_20251119-161841.支付宝.png",
            material_status: "assigned",
            recognition_status: "needs_confirmation",
            recognition_failure_stage: null,
            recognition_failure_reason: null,
            invoice_id: null,
            invoice_number: null,
            validation_status: "passed",
            validation_messages: [],
            created_at: "2026-04-28T10:00:00+08:00",
          },
          invoice: null,
          recognition: {
            id: "REC-PAYMENT-001",
            material_id: "MAT-PAYMENT-001",
            status: "needs_confirmation",
            failure: null,
            recognized_fields: {
              amount_cents: {
                value: 308700,
                source: "ai",
                confidence: 0.76,
                status: "needs_confirmation",
                updated_at: "2026-04-28T10:00:00+08:00",
              },
            },
            manual_corrections: [],
            created_at: "2026-04-28T10:00:00+08:00",
            updated_at: "2026-04-28T10:00:00+08:00",
          },
          validations: [],
          supporting_materials: [],
          splits: [],
          confirmations: [],
          related_expense_details: [],
          missing_materials: [],
          queue_group: "ready",
          blocking_reasons: [],
          ready_for_submission: true,
        },
      ],
      report: {
        ...buildWorkbenchSummary().report,
        counts: {
          ...buildWorkbenchSummary().report.counts,
          material_count: 1,
          recognition_succeeded_count: 0,
          recognition_needs_confirmation_count: 1,
        },
        materials: [
          {
            material_id: "MAT-PAYMENT-001",
            submitter_id: "2250001",
            material_type: "payment_record",
            original_filename: "Screenshot_20251119-161841.支付宝.png",
            material_status: "assigned",
            recognition_status: "needs_confirmation",
            recognition_failure_stage: null,
            recognition_failure_reason: null,
            invoice_id: null,
            invoice_number: null,
            validation_status: "passed",
            validation_messages: [],
            created_at: "2026-04-28T10:00:00+08:00",
          },
        ],
      },
    }));

    renderRoute("/member/invoices/workbench?taskId=TASK-OPEN#member-workbench-invoices");

    const readySection = await screen.findByRole("region", { name: "未提交材料列表" });
    expect(within(readySection).getByText("Screenshot_20251119-161841.支付宝.png")).toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "问题材料分组" })).toHaveTextContent("当前无问题材料");
    expect(screen.getByText("当前无明显异常")).toBeInTheDocument();
    expect(screen.queryByText("先核对识别结果")).not.toBeInTheDocument();
  });
});
