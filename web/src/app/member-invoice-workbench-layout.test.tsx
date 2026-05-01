import { act, render, screen, within } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";

import { clearMockSession, setMockSession } from "./auth-store";
import { routes } from "./routes";

function jsonResponse(body: unknown) {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

function renderWorkbench(entry = "/member/invoices/workbench?taskId=TASK-OPEN") {
  const router = createMemoryRouter(routes, {
    initialEntries: [entry],
  });
  act(() => {
    render(<RouterProvider router={router} />);
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

  it("does not render per-invoice edit forms inside the workbench", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((input: string | URL | Request) => {
      const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;
      if (url === "/api/tasks") {
        return Promise.resolve(jsonResponse([
          {
            id: "TASK-OPEN",
            status: "open",
            competition_name: "ICPC 区域赛",
            competition_location: "武汉",
            competition_start_date: "2026-05-01",
            competition_end_date: "2026-05-03",
            deadline: "2026-05-10T12:00:00+08:00",
            member_ids: ["2250001"],
            fee_categories: ["railway"],
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
      if (url === "/api/tasks/TASK-OPEN/member-workbench?actor_id=2250001") {
        return Promise.resolve(jsonResponse({
          task_id: "TASK-OPEN",
          actor_id: "2250001",
          report: {
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
          },
          items: [],
          pending_supporting_material_linkage_items: [],
          shared_invoices: [],
        }));
      }
      throw new Error(`Unhandled request ${url}`);
    });

    renderWorkbench();

    expect(await screen.findByRole("heading", { name: "比赛报销项目" })).toBeInTheDocument();
    expect(screen.getByRole("complementary", { name: "用户工作台分类" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /工作状态/ })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /上传页面/ })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /发票查看页面/ })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "识别结果" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "报销草稿汇总" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "展开的发票详情" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "保存发票字段" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "保存分摊方案" })).not.toBeInTheDocument();
  });

  it("keeps only compact invoice lists on the workbench", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((input: string | URL | Request) => {
      const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;
      if (url === "/api/tasks") {
        return Promise.resolve(jsonResponse([
          {
            id: "TASK-OPEN",
            status: "open",
            competition_name: "ICPC 区域赛",
            competition_location: "武汉",
            competition_start_date: "2026-05-01",
            competition_end_date: "2026-05-03",
            deadline: "2026-05-10T12:00:00+08:00",
            member_ids: ["2250001", "2250002"],
            fee_categories: ["railway"],
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
      if (url === "/api/tasks/TASK-OPEN/member-workbench?actor_id=2250001") {
        return Promise.resolve(jsonResponse({
          task_id: "TASK-OPEN",
          actor_id: "2250001",
          report: {
            task_id: "TASK-OPEN",
            actor_id: "2250001",
            total_expense_amount_cents: 10000,
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
                material_id: "MAT-001",
                submitter_id: "2250001",
                material_type: "invoice",
                original_filename: "invoice.pdf",
                material_status: "assigned",
                recognition_status: "succeeded",
                recognition_failure_stage: null,
                recognition_failure_reason: null,
                invoice_id: "INV-001",
                invoice_number: "INV-001",
                validation_status: "passed",
                validation_messages: [],
                created_at: "2026-04-28T10:00:00+08:00",
              },
              invoice: {
                id: "INV-001",
                task_id: "TASK-OPEN",
                material_id: "MAT-001",
                invoice_number: "INV-001",
                issue_date: "2026-04-26",
                transaction_time: null,
                buyer_name: "同济大学",
                tax_number: "91310113666007253C",
                seller_name: "12306",
                amount_cents: 10000,
                expense_type: "railway",
                member_submission_status: "unsubmitted",
                submitted_by_member_id: null,
                submitted_at: null,
                created_at: "2026-04-28T10:00:00+08:00",
                updated_at: "2026-04-28T10:00:00+08:00",
              },
              recognition: null,
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
          shared_invoices: [
            {
              invoice_id: "INV-SHARED",
              original_filename: "team-railway.pdf",
              invoice_number: "TEAM-001",
              validation_status: "passed",
              issue_date: "2026-04-26",
              buyer_name: "同济大学",
              seller_name: "12306",
              amount_cents: 20000,
              expense_type: "railway",
              submitter_id: "2250002",
              supporting_materials: [{ material_type: "payment_record", count: 1 }],
              splits: [{ member_id: "2250001", amount_cents: 10000 }],
              created_at: "2026-04-28T10:00:00+08:00",
              updated_at: "2026-04-28T10:00:00+08:00",
            },
          ],
        }));
      }
      throw new Error(`Unhandled request ${url}`);
    });

    renderWorkbench("/member/invoices/workbench?taskId=TASK-OPEN#member-workbench-invoices");

    const readySection = await screen.findByRole("region", { name: "未提交发票列表" });
    expect(within(readySection).getByRole("button", { name: /未提交发票 invoice\.pdf INV-001/ })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "所有发票列表" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /共享发票 team-railway\.pdf TEAM-001/ })).toBeInTheDocument();
    expect(screen.getByText("票号 TEAM-001")).toBeInTheDocument();
  });
});
