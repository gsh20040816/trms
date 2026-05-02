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
    expect(screen.getByRole("complementary", { name: "用户工作台分类" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /工作状态/ })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /上传页面/ })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /发票查看页面/ })).toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: "需要处理的发票列表" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "展开的发票详情" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "发票字段" })).not.toBeInTheDocument();
    expect(screen.getByRole("region", { name: "可提交发票列表" })).not.toHaveClass("member-status-section-warning");
    expect(screen.getByRole("region", { name: "问题发票分组" })).toHaveClass("member-status-section-warning");

    const readySection = screen.getByRole("region", { name: "未提交发票列表" });
    fireEvent.click(within(readySection).getByRole("button", { name: /未提交发票 ready\.pdf INV-READY-001/ }));

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

  it("shows pending supporting material linkage without opening a long detail panel", async () => {
    mockCommonFetch(buildWorkbenchSummary({
      pending_supporting_material_linkage_items: [
        {
          material_id: "MAT-PAY-001",
          submitter_id: "2250001",
          material_type: "payment_record",
          original_filename: "pay.png",
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

    expect(await screen.findByRole("heading", { name: "待关联辅助材料" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "待关联辅助材料列表" })).toHaveClass("member-status-section-warning");
    expect(screen.getByText("支付记录 / pay.png")).toBeInTheDocument();
    expect(screen.getByText(/当前已关联：INV-LINKED-001/)).toBeInTheDocument();
    expect(screen.getByText(/当前仍有 2 张候选发票可勾选：INV-READY-001/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "去辅助材料页处理" })).toBeInTheDocument();
    expect(screen.queryByRole("combobox", { name: "归属发票" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "展开的发票详情" })).not.toBeInTheDocument();
  });

  it("routes pending supporting materials to the dedicated material detail page for linkage editing", async () => {
    mockCommonFetch(buildWorkbenchSummary({
      pending_supporting_material_linkage_items: [
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
    const router = renderRoute("/member/invoices/workbench?taskId=TASK-OPEN#member-workbench-invoices");

    expect(await screen.findByRole("heading", { name: "待关联辅助材料" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("link", { name: "去辅助材料页处理" }));

    await waitFor(() => {
      expect(router.state.location.pathname).toBe("/member/materials/MAT-PAY-001");
    });
  });

  it("shows the empty-candidate state without rendering a select", async () => {
    mockCommonFetch(buildWorkbenchSummary({
      pending_supporting_material_linkage_items: [
        {
          material_id: "MAT-NO-CANDIDATE-001",
          submitter_id: "2250001",
          material_type: "competition_notice",
          original_filename: "notice.pdf",
          pending_reason: "no_candidate",
          linked_invoices: [],
          candidate_invoices: [],
          created_at: "2026-04-28T11:00:00+08:00",
        },
      ],
    }));
    renderRoute("/member/invoices/workbench?taskId=TASK-OPEN#member-workbench-invoices");

    expect(await screen.findByRole("heading", { name: "待关联辅助材料" })).toBeInTheDocument();
    expect(screen.getByText("当前没有候选发票；通常意味着你还没有创建对应发票，或材料提交人与现有发票不匹配。")).toBeInTheDocument();
    expect(screen.queryByRole("combobox", { name: "归属发票" })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "去辅助材料页处理" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "去上传区补录或补传发票" })).toBeInTheDocument();
  });

  it("routes non-invoice materials to the dedicated material detail page", async () => {
    mockCommonFetch(buildWorkbenchSummary({
      items: [
        {
          material: {
            material_id: "MAT-PAY-001",
            submitter_id: "2250001",
            material_type: "payment_record",
            original_filename: "pay.png",
            material_status: "assigned",
            recognition_status: "needs_confirmation",
            recognition_failure_stage: null,
            recognition_failure_reason: null,
            invoice_id: null,
            invoice_number: null,
            validation_status: "pending",
            validation_messages: [],
            created_at: "2026-04-28T10:00:00+08:00",
          },
          invoice: null,
          recognition: {
            id: "REC-PAY-001",
            material_id: "MAT-PAY-001",
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
        materials: [
          {
            material_id: "MAT-PAY-001",
            submitter_id: "2250001",
            material_type: "payment_record",
            original_filename: "pay.png",
            material_status: "assigned",
            recognition_status: "needs_confirmation",
            recognition_failure_stage: null,
            recognition_failure_reason: null,
            invoice_id: null,
            invoice_number: null,
            validation_status: "pending",
            validation_messages: [],
            created_at: "2026-04-28T10:00:00+08:00",
          },
        ],
      },
    }));
    const router = renderRoute("/member/invoices/workbench?taskId=TASK-OPEN#member-workbench-invoices");

    expect(await screen.findByRole("heading", { name: "需要处理的发票列表" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /识别失败或待确认 支付记录 pay\.png/ }));

    await waitFor(() => {
      expect(router.state.location.pathname).toBe("/member/materials/MAT-PAY-001");
    });
  });

  it("shows non-invoice problem rows with material labels and recognized amount", async () => {
    mockCommonFetch(buildWorkbenchSummary({
      items: [
        {
          material: {
            material_id: "MAT-PAY-001",
            submitter_id: "2250001",
            material_type: "payment_record",
            original_filename: "pay.png",
            material_status: "assigned",
            recognition_status: "needs_confirmation",
            recognition_failure_stage: null,
            recognition_failure_reason: null,
            invoice_id: null,
            invoice_number: null,
            validation_status: "pending",
            validation_messages: [],
            created_at: "2026-04-28T10:00:00+08:00",
          },
          invoice: null,
          recognition: {
            id: "REC-PAY-001",
            material_id: "MAT-PAY-001",
            status: "needs_confirmation",
            failure: null,
            recognized_fields: {
              amount_cents: {
                value: 12345,
                source: "ai",
                confidence: 0.76,
                status: "needs_confirmation",
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
          queue_group: "recognition_review",
          blocking_reasons: ["recognition_review"],
          ready_for_submission: false,
        },
      ],
      report: {
        ...buildWorkbenchSummary().report,
        materials: [
          {
            material_id: "MAT-PAY-001",
            submitter_id: "2250001",
            material_type: "payment_record",
            original_filename: "pay.png",
            material_status: "assigned",
            recognition_status: "needs_confirmation",
            recognition_failure_stage: null,
            recognition_failure_reason: null,
            invoice_id: null,
            invoice_number: null,
            validation_status: "pending",
            validation_messages: [],
            created_at: "2026-04-28T10:00:00+08:00",
          },
        ],
      },
    }));

    renderRoute("/member/invoices/workbench?taskId=TASK-OPEN#member-workbench-invoices");

    const summaryList = within(await screen.findByRole("list", { name: "识别失败或待确认 发票摘要列表" }));
    expect(summaryList.getByText("支付记录")).toBeInTheDocument();
    expect(summaryList.getByText("￥123.45")).toBeInTheDocument();
    expect(summaryList.queryByText("票号 待补录")).not.toBeInTheDocument();
  });

  it("allows members to create a paper invoice from the workbench", async () => {
    mockCommonFetch(buildWorkbenchSummary({
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
    fireEvent.change(screen.getByLabelText("纸质发票号码"), { target: { value: "PAPER-001" } });
    fireEvent.change(screen.getByLabelText("金额（元）"), { target: { value: "88.00" } });
    fireEvent.click(screen.getByRole("button", { name: "新增纸质发票" }));

    await waitFor(() => {
      expect(router.state.location.pathname).toBe("/member/invoices/INV-PAPER-001");
    });
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

    const problemSection = await screen.findByRole("region", { name: "问题发票分组" });
    const summaryList = within(problemSection).getByRole("list", { name: "识别失败或待确认 发票摘要列表" });
    expect(within(summaryList).getByRole("button", { name: /识别失败或待确认 problem\.pdf INV-PROBLEM-001/ })).toBeInTheDocument();
    expect(within(summaryList).getAllByText("识别失败或待确认").length).toBeGreaterThanOrEqual(1);
    expect(within(summaryList).queryByRole("button", { name: "批量提交选中发票" })).not.toBeInTheDocument();
  });
});
