import { act, render, screen, within } from "@testing-library/react";
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

function renderWorkbenchRoute(entry = "/member/invoices/workbench?taskId=TASK-OPEN#member-workbench-invoices") {
  const router = createMemoryRouter(routes, {
    initialEntries: [entry],
  });

  act(() => {
    render(<RouterProvider router={router} />);
  });
}

describe("MemberInvoiceWorkbenchPage aggregate loading", () => {
  beforeEach(() => {
    clearMockSession();
    setMockSession("member");
  });

  afterEach(() => {
    vi.restoreAllMocks();
    clearMockSession();
  });

  it("prefers the member workbench aggregate endpoint over legacy N+1 requests", async () => {
    const requestedUrls: string[] = [];

    vi.spyOn(globalThis, "fetch").mockImplementation((input: string | URL | Request) => {
      const url = resolveRequestUrl(input);
      requestedUrls.push(url);

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

      if (url === "/api/tasks/TASK-OPEN/member-workbench?actor_id=2250001") {
        return Promise.resolve(jsonResponse({
          task_id: "TASK-OPEN",
          actor_id: "2250001",
          report: {
            task_id: "TASK-OPEN",
            actor_id: "2250001",
            total_expense_amount_cents: 6345,
            counts: {
              material_count: 1,
              missing_material_count: 0,
              expense_detail_count: 1,
              recognition_pending_count: 0,
              recognition_succeeded_count: 1,
              recognition_failed_count: 0,
              recognition_needs_confirmation_count: 0,
              validation_passed_count: 1,
              validation_failed_count: 0,
              validation_pending_count: 0,
              validation_not_applicable_count: 0,
              confirmed_expense_count: 1,
              pending_confirmation_count: 0,
              disputed_confirmation_count: 0,
              missing_confirmation_count: 0,
            },
            materials: [
              {
                material_id: "MAT-OPEN-001",
                submitter_id: "2250001",
                material_type: "invoice",
                original_filename: "railway.pdf",
                material_status: "assigned",
                recognition_status: "succeeded",
                recognition_failure_stage: null,
                recognition_failure_reason: null,
                invoice_id: "INV-OPEN-001",
                invoice_number: "INV-OPEN-001",
                validation_status: "passed",
                validation_messages: [],
                created_at: "2026-04-28T10:00:00+08:00",
              },
            ],
            missing_materials: [],
            expense_details: [
              {
                split_id: "SPLIT-OPEN-001",
                split_version: 1,
                member_id: "2250001",
                amount_cents: 6345,
                note: "self paid",
                created_at: "2026-04-28T10:05:00+08:00",
                updated_at: "2026-04-28T10:05:00+08:00",
                invoice: {
                  id: "INV-OPEN-001",
                  material_id: "MAT-OPEN-001",
                  invoice_number: "INV-OPEN-001",
                  issue_date: "2026-04-20",
                  transaction_time: "2026-04-20T09:00:00+08:00",
                  buyer_name: "同济大学",
                  seller_name: "中国铁路",
                  amount_cents: 6345,
                  expense_type: "railway",
                  created_at: "2026-04-28T10:00:00+08:00",
                  updated_at: "2026-04-28T10:05:00+08:00",
                },
                confirmation: {
                  id: "CONF-OPEN-001",
                  member_id: "2250001",
                  split_version: 1,
                  status: "confirmed",
                  dispute_reason: null,
                  confirmed_at: "2026-04-28T10:06:00+08:00",
                  updated_at: "2026-04-28T10:06:00+08:00",
                },
              },
            ],
          },
          items: [
            {
              material: {
                material_id: "MAT-OPEN-001",
                submitter_id: "2250001",
                material_type: "invoice",
                original_filename: "railway.pdf",
                material_status: "assigned",
                recognition_status: "succeeded",
                recognition_failure_stage: null,
                recognition_failure_reason: null,
                invoice_id: "INV-OPEN-001",
                invoice_number: "INV-OPEN-001",
                validation_status: "passed",
                validation_messages: [],
                created_at: "2026-04-28T10:00:00+08:00",
              },
              invoice: {
                id: "INV-OPEN-001",
                task_id: "TASK-OPEN",
                material_id: "MAT-OPEN-001",
                invoice_number: "INV-OPEN-001",
                issue_date: "2026-04-20",
                transaction_time: "2026-04-20T09:00:00+08:00",
                buyer_name: "同济大学",
                tax_number: "91310113666007253C",
                seller_name: "中国铁路",
                amount_cents: 6345,
                expense_type: "railway",
                member_submission_status: "unsubmitted",
                submitted_by_member_id: null,
                submitted_at: null,
                created_at: "2026-04-28T10:00:00+08:00",
                updated_at: "2026-04-28T10:05:00+08:00",
              },
              recognition: {
                id: "REC-OPEN-001",
                material_id: "MAT-OPEN-001",
                status: "succeeded",
                failure: null,
                recognized_fields: {
                  buyer_name: {
                    value: "同济大学",
                    source: "manual",
                    confidence: 1,
                    status: "recognized",
                    updated_at: "2026-04-28T10:00:00+08:00",
                  },
                  tax_number: {
                    value: "91310113666007253C",
                    source: "manual",
                    confidence: 1,
                    status: "recognized",
                    updated_at: "2026-04-28T10:00:00+08:00",
                  },
                },
                manual_corrections: [],
                created_at: "2026-04-28T10:00:00+08:00",
                updated_at: "2026-04-28T10:05:00+08:00",
              },
              validations: [
                {
                  id: "VAL-OPEN-001",
                  rule_code: "invoice_title_match",
                  target_type: "invoice",
                  target_id: "INV-OPEN-001",
                  severity: "blocker",
                  status: "passed",
                  message: "发票抬头匹配",
                  evidence: {},
                  created_at: "2026-04-28T10:05:00+08:00",
                },
              ],
              supporting_materials: [],
              splits: [
                {
                  id: "SPLIT-OPEN-001",
                  invoice_id: "INV-OPEN-001",
                  member_id: "2250001",
                  amount_cents: 6345,
                  note: "self paid",
                  version: 1,
                  is_active: true,
                  created_at: "2026-04-28T10:05:00+08:00",
                  updated_at: "2026-04-28T10:05:00+08:00",
                },
              ],
              confirmations: [
                {
                  id: "CONF-OPEN-001",
                  split_id: "SPLIT-OPEN-001",
                  member_id: "2250001",
                  split_version: 1,
                  split_amount_cents: 6345,
                  split_note: "self paid",
                  is_current: true,
                  status: "confirmed",
                  dispute_reason: null,
                  confirmed_at: "2026-04-28T10:06:00+08:00",
                  updated_at: "2026-04-28T10:06:00+08:00",
                },
              ],
              related_expense_details: [
                {
                  split_id: "SPLIT-OPEN-001",
                  split_version: 1,
                  member_id: "2250001",
                  amount_cents: 6345,
                  note: "self paid",
                  created_at: "2026-04-28T10:05:00+08:00",
                  updated_at: "2026-04-28T10:05:00+08:00",
                  invoice: {
                    id: "INV-OPEN-001",
                    material_id: "MAT-OPEN-001",
                    invoice_number: "INV-OPEN-001",
                    issue_date: "2026-04-20",
                    transaction_time: "2026-04-20T09:00:00+08:00",
                    buyer_name: "同济大学",
                    seller_name: "中国铁路",
                    amount_cents: 6345,
                    expense_type: "railway",
                    created_at: "2026-04-28T10:00:00+08:00",
                    updated_at: "2026-04-28T10:05:00+08:00",
                  },
                  confirmation: {
                    id: "CONF-OPEN-001",
                    member_id: "2250001",
                    split_version: 1,
                    status: "confirmed",
                    dispute_reason: null,
                    confirmed_at: "2026-04-28T10:06:00+08:00",
                    updated_at: "2026-04-28T10:06:00+08:00",
                  },
                },
              ],
              missing_materials: [],
              queue_group: "ready",
              blocking_reasons: [],
              ready_for_submission: true,
            },
          ],
          pending_supporting_material_linkage_items: [],
          shared_invoices: [],
        }));
      }

      throw new Error(`Unhandled fetch URL in member invoice workbench aggregate test: ${url}`);
    });

    renderWorkbenchRoute();

    const readySection = await screen.findByRole("region", { name: "未提交材料列表" });
    expect(within(readySection).getByRole("button", { name: /未提交材料 railway\.pdf INV-OPEN-001/ })).toBeInTheDocument();
    expect(requestedUrls).toContain("/api/tasks/TASK-OPEN/member-workbench?actor_id=2250001");
    expect(requestedUrls).not.toContain("/api/tasks/TASK-OPEN/member-status?actor_id=2250001");
    expect(requestedUrls).not.toContain("/api/tasks/TASK-OPEN/shared-invoices?actor_id=2250001");
    expect(requestedUrls).not.toContain("/api/tasks/TASK-OPEN/supporting-material-linkage?actor_id=2250001");
    expect(requestedUrls.every((url) => !url.includes("/recognition-tasks"))).toBe(true);
    expect(requestedUrls.every((url) => !url.endsWith("/validations"))).toBe(true);
    expect(requestedUrls.every((url) => !url.endsWith("/supporting-materials"))).toBe(true);
    expect(requestedUrls.every((url) => !url.endsWith("/splits"))).toBe(true);
    expect(requestedUrls.every((url) => !url.endsWith("/confirmations"))).toBe(true);
  });
});
