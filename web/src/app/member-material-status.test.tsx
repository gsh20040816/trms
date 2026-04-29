import { act, fireEvent, render, screen, within } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";

import { clearMockSession, setMockSession } from "./auth-store";
import { MemberMaterialStatusPage } from "./member-material-status";

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

function renderMemberStatusRoute(entry = "/member/materials/status") {
  const router = createMemoryRouter([{
    path: "/member/materials/status",
    element: <MemberMaterialStatusPage />,
  }], {
    initialEntries: [entry],
  });

  act(() => {
    render(<RouterProvider router={router} />);
  });
}

describe("MemberMaterialStatusPage", () => {
  beforeEach(() => {
    clearMockSession();
    setMockSession("member");
  });

  afterEach(() => {
    vi.restoreAllMocks();
    clearMockSession();
  });

  it("shows only the current member materials with recognition, validation, and missing-material status", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation((input: string | URL | Request) => {
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
          {
            id: "TASK-HIDDEN",
            status: "open",
            competition_name: "Hidden Contest",
            competition_location: "兰州",
            competition_start_date: "2026-05-20",
            competition_end_date: "2026-05-22",
            deadline: "2026-05-30T18:00:00+08:00",
            member_ids: ["2250999"],
            fee_categories: ["registration"],
            administrator_id: "admin-1",
            project_info: "ACM 竞赛项目",
            reimburser_info: "张管理员",
            invoice_title: "同济大学",
            tax_number: "91310113666007253C",
            created_at: "2026-04-28T09:00:00+08:00",
            updated_at: "2026-04-28T09:00:00+08:00",
          },
        ]));
      }

      if (url === "/api/tasks/TASK-OPEN/materials") {
        return Promise.resolve(jsonResponse({
          items: [
            {
              id: "MAT-SELF-INV",
              status: "assigned",
              task_id: "TASK-OPEN",
              submitter_id: "2250001",
              task_id_hint: null,
              submitter_id_hint: null,
              channel: "web",
              material_type: "invoice",
              storage_key: "TASK-OPEN/MAT-SELF-INV-ticket.pdf",
              original_filename: "ticket.pdf",
              content_type: "application/pdf",
              size_bytes: 12,
              sha256: "a".repeat(64),
              duplicate_of: null,
              claimed_by: null,
              claimed_at: null,
              created_at: "2026-04-28T10:00:00+08:00",
            },
            {
              id: "MAT-SELF-ATT",
              status: "assigned",
              task_id: "TASK-OPEN",
              submitter_id: "2250001",
              task_id_hint: null,
              submitter_id_hint: null,
              channel: "web",
              material_type: "payment_record",
              storage_key: "TASK-OPEN/MAT-SELF-ATT-pay.png",
              original_filename: "pay.png",
              content_type: "image/png",
              size_bytes: 8,
              sha256: "b".repeat(64),
              duplicate_of: null,
              claimed_by: null,
              claimed_at: null,
              created_at: "2026-04-28T09:30:00+08:00",
            },
            {
              id: "MAT-OTHER",
              status: "assigned",
              task_id: "TASK-OPEN",
              submitter_id: "2250002",
              task_id_hint: null,
              submitter_id_hint: null,
              channel: "web",
              material_type: "invoice",
              storage_key: "TASK-OPEN/MAT-OTHER-other.pdf",
              original_filename: "other.pdf",
              content_type: "application/pdf",
              size_bytes: 12,
              sha256: "c".repeat(64),
              duplicate_of: null,
              claimed_by: null,
              claimed_at: null,
              created_at: "2026-04-28T08:00:00+08:00",
            },
          ],
        }));
      }

      if (url === "/api/tasks/TASK-OPEN/invoices") {
        return Promise.resolve(jsonResponse({
          items: [
            {
              id: "INV-001",
              task_id: "TASK-OPEN",
              material_id: "MAT-SELF-INV",
              invoice_number: "INV-001",
              issue_date: "2026-04-20",
              transaction_time: "2026-04-20T09:00:00+08:00",
              buyer_name: "同济大学",
              tax_number: "91310113666007253C",
              seller_name: "中国铁路",
              amount_cents: 123456,
              expense_type: "railway",
              created_at: "2026-04-28T10:05:00+08:00",
              updated_at: "2026-04-28T10:05:00+08:00",
            },
            {
              id: "INV-999",
              task_id: "TASK-OPEN",
              material_id: "MAT-OTHER",
              invoice_number: "INV-999",
              issue_date: "2026-04-19",
              transaction_time: "2026-04-19T09:00:00+08:00",
              buyer_name: "同济大学",
              tax_number: "91310113666007253C",
              seller_name: "Hidden",
              amount_cents: 1000,
              expense_type: "railway",
              created_at: "2026-04-28T08:05:00+08:00",
              updated_at: "2026-04-28T08:05:00+08:00",
            },
          ],
        }));
      }

      if (url === "/api/materials/MAT-SELF-INV/recognition-tasks") {
        return Promise.resolve(jsonResponse({
          latest_effective: {
            id: "REC-001",
            material_id: "MAT-SELF-INV",
            status: "needs_confirmation",
            is_final_fact: false,
            failure: null,
            raw_response: { provider: "placeholder-ai" },
            recognized_fields: {
              buyer_name: {
                value: "同济大学",
                source: "ai",
                confidence: 0.44,
                status: "needs_confirmation",
                updated_at: "2026-04-28T10:06:00+08:00",
              },
            },
            created_at: "2026-04-28T10:01:00+08:00",
            updated_at: "2026-04-28T10:06:00+08:00",
          },
          items: [],
        }));
      }

      if (url === "/api/materials/MAT-SELF-ATT/recognition-tasks") {
        return Promise.resolve(jsonResponse({
          latest_effective: null,
          items: [
            {
              id: "REC-002",
              material_id: "MAT-SELF-ATT",
              status: "pending",
              is_final_fact: false,
              failure: null,
              raw_response: null,
              recognized_fields: {},
              created_at: "2026-04-28T09:31:00+08:00",
              updated_at: "2026-04-28T09:31:00+08:00",
            },
          ],
        }));
      }

      if (url === "/api/invoices/INV-001/validations") {
        return Promise.resolve(jsonResponse({
          items: [
            {
              id: "VAL-001",
              rule_code: "invoice_payment_record_required",
              target_type: "invoice",
              target_id: "INV-001",
              severity: "blocker",
              status: "failed",
              message: "发票金额达到阈值，缺少支付记录",
              evidence: { requires_payment_record: true },
              created_at: "2026-04-28T10:07:00+08:00",
            },
            {
              id: "VAL-002",
              rule_code: "invoice_tax_number_match",
              target_type: "invoice",
              target_id: "INV-001",
              severity: "blocker",
              status: "pending",
              message: "税号缺失，需人工确认",
              evidence: {},
              created_at: "2026-04-28T10:07:30+08:00",
            },
          ],
        }));
      }

      throw new Error(`Unhandled fetch URL in member status test: ${url}`);
    });

    renderMemberStatusRoute("/member/materials/status?taskId=TASK-OPEN");

    expect(await screen.findByRole("heading", { name: "成员材料状态" })).toBeInTheDocument();
    expect(await screen.findByLabelText("目标任务")).toHaveValue("TASK-OPEN");
    expect(screen.getByRole("link", { name: "返回当前任务工作台" })).toHaveAttribute(
      "href",
      "/member/invoices/workbench?taskId=TASK-OPEN",
    );

    const statusList = await screen.findByLabelText("成员材料状态列表");
    const statusCards = within(statusList).getAllByRole("article");
    expect(statusCards).toHaveLength(2);
    expect(screen.queryByText("other.pdf")).not.toBeInTheDocument();

    const invoiceSummaryCard = within(statusCards[0] ?? document.body).getByText("ticket.pdf").closest("article");
    if (!invoiceSummaryCard) {
      throw new Error("expected invoice status summary card");
    }
    expect(within(invoiceSummaryCard).getByText("识别待确认")).toBeInTheDocument();
    expect(within(invoiceSummaryCard).getByText("存在 1 条失败校验")).toBeInTheDocument();

    let detailPanel = screen.getByLabelText("当前材料详情");
    expect(within(detailPanel).getByText("待确认字段：购买方名称")).toBeInTheDocument();
    expect(within(detailPanel).getByText("存在 1 条失败校验")).toBeInTheDocument();
    expect(within(detailPanel).getByLabelText("MAT-SELF-INV 缺失材料提示列表")).toHaveTextContent(
      "发票金额达到阈值，缺少支付记录",
    );
    expect(within(detailPanel).getByLabelText("MAT-SELF-INV 缺失材料提示列表")).toHaveTextContent("支付记录");
    expect(within(detailPanel).getByRole("button", { name: "运行重新识别" })).toBeInTheDocument();
    fireEvent.click(within(detailPanel).getByRole("button", { name: "人工填写发票信息" }));
    expect(
      within(detailPanel).getByRole("form", { name: "MAT-SELF-INV 发票人工填写表单" }),
    ).toBeInTheDocument();

    const attachmentSummaryCard = within(statusCards[1] ?? document.body).getByText("pay.png").closest("article");
    if (!attachmentSummaryCard) {
      throw new Error("expected attachment status summary card");
    }
    expect(within(attachmentSummaryCard).getByText("识别排队中")).toBeInTheDocument();
    expect(within(attachmentSummaryCard).getByText("当前材料暂无独立发票校验")).toBeInTheDocument();
    fireEvent.click(within(attachmentSummaryCard).getByRole("button", { name: "查看详情" }));
    detailPanel = screen.getByLabelText("当前材料详情");
    expect(within(detailPanel).getByText("pay.png")).toBeInTheDocument();
    expect(within(detailPanel).getByText("识别排队中")).toBeInTheDocument();
    expect(within(detailPanel).getByText("当前材料暂无独立发票校验")).toBeInTheDocument();
    expect(within(detailPanel).getByRole("button", { name: "运行重新识别" })).toBeInTheDocument();

    expect(screen.getByLabelText("材料状态摘要")).toHaveTextContent("本人材料 2 份");
    expect(fetchSpy).toHaveBeenCalledTimes(6);
  });

  it("shows an explicit empty state when the selected task has no current-member materials", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((input: string | URL | Request) => {
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

      if (url === "/api/tasks/TASK-OPEN/materials") {
        return Promise.resolve(jsonResponse({
          items: [
            {
              id: "MAT-OTHER",
              status: "assigned",
              task_id: "TASK-OPEN",
              submitter_id: "2250002",
              task_id_hint: null,
              submitter_id_hint: null,
              channel: "web",
              material_type: "invoice",
              storage_key: "TASK-OPEN/MAT-OTHER-other.pdf",
              original_filename: "other.pdf",
              content_type: "application/pdf",
              size_bytes: 12,
              sha256: "c".repeat(64),
              duplicate_of: null,
              claimed_by: null,
              claimed_at: null,
              created_at: "2026-04-28T08:00:00+08:00",
            },
          ],
        }));
      }

      if (url === "/api/tasks/TASK-OPEN/invoices") {
        return Promise.resolve(jsonResponse({ items: [] }));
      }

      throw new Error(`Unhandled fetch URL in member status empty test: ${url}`);
    });

    renderMemberStatusRoute("/member/materials/status?taskId=TASK-OPEN");

    expect(await screen.findByText("当前任务下还没有你提交的材料")).toBeInTheDocument();
    expect(screen.queryByLabelText("成员材料状态列表")).not.toBeInTheDocument();
  });

  it("shows a failure state when material status aggregation cannot be loaded", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((input: string | URL | Request) => {
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

      if (url === "/api/tasks/TASK-OPEN/materials") {
        return Promise.resolve(jsonResponse(
          { detail: "material list failed" },
          { status: 500 },
        ));
      }

      if (url === "/api/tasks/TASK-OPEN/invoices") {
        return Promise.resolve(jsonResponse({ items: [] }));
      }

      throw new Error(`Unhandled fetch URL in member status error test: ${url}`);
    });

    renderMemberStatusRoute("/member/materials/status?taskId=TASK-OPEN");

    expect(await screen.findByRole("alert")).toHaveTextContent("操作未完成");
    expect(screen.getByRole("alert")).toHaveTextContent("系统暂时无法完成该操作，请稍后重试。");
  });
});
