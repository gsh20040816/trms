import { act, render, screen, within } from "@testing-library/react";
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

function renderReviewRoute(entry = "/admin/tasks/TASK-REVIEW/review") {
  const router = createMemoryRouter(routes, {
    initialEntries: [entry],
  });

  act(() => {
    render(<RouterProvider router={router} />);
  });
}

describe("AdminReviewOverviewPage", () => {
  beforeEach(() => {
    clearMockSession();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    clearMockSession();
  });

  it("renders highlighted review risks, pending-assignment materials and invoice review details", async () => {
    setMockSession("admin");

    vi.spyOn(globalThis, "fetch").mockImplementation((input: string | URL | Request) => {
      const url = resolveRequestUrl(input);

      if (url === "/api/tasks/TASK-REVIEW") {
        return Promise.resolve(jsonResponse({
          id: "TASK-REVIEW",
          status: "reviewing",
          competition_name: "ICPC 复核任务",
          competition_location: "上海",
          competition_start_date: "2026-05-01",
          competition_end_date: "2026-05-03",
          deadline: "2026-05-10T18:00:00+08:00",
          member_ids: ["2250001", "2250002", "2250003"],
          fee_categories: ["registration", "hotel"],
          administrator_id: "admin-1",
          project_info: "ACM 竞赛项目",
          reimburser_info: "张管理员",
          invoice_title: "同济大学",
          tax_number: "91310000TEST00001",
          created_at: "2026-04-20T09:00:00+08:00",
          updated_at: "2026-04-25T10:00:00+08:00",
        }));
      }

      if (url === "/api/tasks/TASK-REVIEW/review-summary?actor_id=admin-1") {
        return Promise.resolve(jsonResponse({
          task_id: "TASK-REVIEW",
          administrator_id: "admin-1",
          counts: {
            material_count: 1,
            pending_assignment_material_count: 1,
            invoice_count: 1,
            validation_count: 2,
            blocker_failed_validation_count: 1,
            split_count: 2,
            confirmed_split_count: 0,
            pending_confirmation_count: 1,
            disputed_confirmation_count: 1,
            missing_confirmation_count: 0,
            pending_recognition_count: 0,
            failed_recognition_count: 0,
            needs_confirmation_recognition_count: 1,
          },
          materials: [
            {
              material: {
                id: "MAT-INV-001",
                status: "assigned",
                task_id: "TASK-REVIEW",
                submitter_id: "2250001",
                task_id_hint: null,
                submitter_id_hint: null,
                channel: "web",
                material_type: "invoice",
                storage_key: "TASK-REVIEW/invoice.pdf",
                original_filename: "invoice.pdf",
                content_type: "application/pdf",
                size_bytes: 4096,
                sha256: "a".repeat(64),
                duplicate_of: null,
                claimed_by: null,
                claimed_at: null,
                created_at: "2026-04-28T09:00:00+08:00",
              },
              latest_recognition: {
                id: "REC-001",
                material_id: "MAT-INV-001",
                status: "needs_confirmation",
                is_final_fact: false,
                failure: null,
                raw_response: { provider: "placeholder-ai" },
                recognized_fields: {
                  buyer_name: {
                    value: "同济大学",
                    source: "ocr",
                    confidence: 0.4,
                    status: "needs_confirmation",
                    updated_at: "2026-04-28T09:05:00+08:00",
                  },
                },
                manual_corrections: [],
                created_at: "2026-04-28T09:01:00+08:00",
                updated_at: "2026-04-28T09:05:00+08:00",
              },
              invoice_id: "INV-001",
              supporting_invoice_ids: [],
            },
          ],
          pending_assignment_materials: [
            {
              id: "MAT-PENDING-001",
              status: "pending_assignment",
              task_id: null,
              submitter_id: null,
              task_id_hint: "TASK-REVIEW",
              submitter_id_hint: "2250003",
              channel: "email",
              material_type: "payment_record",
              storage_key: "_pending_assignment/pending-pay.pdf",
              original_filename: "pending-pay.pdf",
              content_type: "application/pdf",
              size_bytes: 2048,
              sha256: "b".repeat(64),
              duplicate_of: null,
              claimed_by: null,
              claimed_at: null,
              created_at: "2026-04-28T10:00:00+08:00",
            },
          ],
          invoices: [
            {
              invoice: {
                id: "INV-001",
                task_id: "TASK-REVIEW",
                material_id: "MAT-INV-001",
                invoice_number: "INV-001",
                issue_date: "2026-04-20",
                transaction_time: "2026-04-20T09:00:00+08:00",
                buyer_name: "同济大学",
                tax_number: "91310000TEST00001",
                seller_name: "赛事平台",
                amount_cents: 12345,
                expense_type: "registration",
                created_at: "2026-04-28T09:10:00+08:00",
                updated_at: "2026-04-28T09:12:00+08:00",
              },
              supporting_material_ids: ["MAT-PAY-001"],
              validations: [
                {
                  id: "VAL-001",
                  rule_code: "invoice_title_match",
                  target_type: "invoice",
                  target_id: "INV-001",
                  severity: "blocker",
                  status: "failed",
                  message: "发票抬头与任务抬头不一致",
                  evidence: {},
                  created_at: "2026-04-28T09:15:00+08:00",
                },
                {
                  id: "VAL-002",
                  rule_code: "payment_record_required",
                  target_type: "invoice",
                  target_id: "INV-001",
                  severity: "warning",
                  status: "pending",
                  message: "仍需补充支付记录金额核对",
                  evidence: {},
                  created_at: "2026-04-28T09:16:00+08:00",
                },
              ],
              splits: [
                {
                  split: {
                    id: "SPLIT-001",
                    invoice_id: "INV-001",
                    member_id: "2250002",
                    amount_cents: 6000,
                    note: "team share",
                    version: 2,
                    is_active: true,
                    created_at: "2026-04-28T09:20:00+08:00",
                    updated_at: "2026-04-28T09:20:00+08:00",
                  },
                  confirmation: null,
                },
                {
                  split: {
                    id: "SPLIT-002",
                    invoice_id: "INV-001",
                    member_id: "2250003",
                    amount_cents: 6345,
                    note: "shared registration",
                    version: 2,
                    is_active: true,
                    created_at: "2026-04-28T09:20:00+08:00",
                    updated_at: "2026-04-28T09:21:00+08:00",
                  },
                  confirmation: {
                    id: "CONF-002",
                    split_id: "SPLIT-002",
                    member_id: "2250003",
                    split_version: 2,
                    split_amount_cents: 6345,
                    split_note: "shared registration",
                    is_current: true,
                    status: "disputed",
                    dispute_reason: "报名费分摊比例需要调整",
                    confirmed_at: "2026-04-28T09:30:00+08:00",
                    updated_at: "2026-04-28T09:31:00+08:00",
                  },
                },
              ],
            },
          ],
        }));
      }

      if (url === "/api/tasks/TASK-REVIEW/overdue-confirmations?actor_id=admin-1") {
        return Promise.resolve(jsonResponse({
          task_id: "TASK-REVIEW",
          administrator_id: "admin-1",
          confirmation_deadline: "2026-05-10T18:00:00+08:00",
          is_overdue: true,
          total_overdue_members: 1,
          overdue_member_ids: ["2250002"],
        }));
      }

      throw new Error(`Unhandled fetch URL in admin review overview test: ${url}`);
    });

    renderReviewRoute();

    expect(await screen.findByRole("heading", { name: "管理员复核总览" })).toBeInTheDocument();
    const moduleNav = screen.getByLabelText("管理员模块导航");
    expect(within(moduleNav).getByText("材料审核").closest("a")).toHaveAttribute("aria-current", "page");
    expect(screen.getByLabelText("当前任务上下文")).toHaveTextContent("ICPC 复核任务");
    expect(screen.getAllByText("ICPC 复核任务").length).toBeGreaterThan(0);
    expect(screen.getByRole("link", { name: "处理更正与提醒" })).toHaveAttribute(
      "href",
      "/admin/tasks/TASK-REVIEW/corrections",
    );

    const riskSummary = within(screen.getByLabelText("复核风险摘要"));
    expect(riskSummary.getByText("需要立即处理")).toBeInTheDocument();
    expect(riskSummary.getByText("待归属材料")).toBeInTheDocument();
    expect(riskSummary.getByText("待成员确认")).toBeInTheDocument();
    expect(riskSummary.getByText("成员异议")).toBeInTheDocument();
    expect(riskSummary.getByText("逾期未确认成员")).toBeInTheDocument();

    const pendingList = within(screen.getByLabelText("待归属材料列表"));
    expect(pendingList.getByText("pending-pay.pdf")).toBeInTheDocument();
    expect(pendingList.getByText("2250003")).toBeInTheDocument();

    const materialList = within(screen.getByLabelText("任务材料列表"));
    expect(materialList.getByText("invoice.pdf")).toBeInTheDocument();
    expect(materialList.getAllByText("待人工确认")).toHaveLength(2);
    expect(materialList.getByRole("link", { name: "更正识别字段" })).toHaveAttribute(
      "href",
      "/admin/tasks/TASK-REVIEW/invoices?materialId=MAT-INV-001",
    );

    const invoiceList = within(screen.getByLabelText("发票复核列表"));
    expect(invoiceList.getByText("INV-001")).toBeInTheDocument();
    expect(invoiceList.getByText("发票抬头与任务抬头不一致")).toBeInTheDocument();
    expect(invoiceList.getByText("异议原因：报名费分摊比例需要调整")).toBeInTheDocument();
    expect(invoiceList.getByRole("link", { name: "更正金额与字段" })).toHaveAttribute(
      "href",
      "/admin/tasks/TASK-REVIEW/invoices?materialId=MAT-INV-001",
    );
    expect(invoiceList.getByRole("link", { name: "调整分摊" })).toHaveAttribute(
      "href",
      "/admin/tasks/TASK-REVIEW/splits?invoiceId=INV-001",
    );

    const outstandingMembers = within(screen.getByLabelText("未完成确认成员"));
    expect(outstandingMembers.getByText("成员 2250002")).toBeInTheDocument();
    const overdueMembers = within(screen.getByLabelText("逾期未确认成员"));
    expect(overdueMembers.getByText("2250002")).toBeInTheDocument();
  });

  it("blocks member access through the existing protected admin route", async () => {
    setMockSession("member");

    renderReviewRoute();

    expect(await screen.findByRole("heading", { name: "管理员工作台 暂不可访问" })).toBeInTheDocument();
    expect(screen.getByText("当前登录身份不匹配；此入口仅允许管理员访问。")).toBeInTheDocument();
  });
});
