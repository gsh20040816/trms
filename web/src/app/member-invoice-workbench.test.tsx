import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";

import { clearMockSession, setMockSession } from "./auth-store";
import type { RecognitionTaskRecord } from "../lib/api/types";
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

function renderWorkbenchRoute(entry = "/member/invoices/workbench?taskId=TASK-OPEN") {
  const router = createMemoryRouter(routes, {
    initialEntries: [entry],
  });

  act(() => {
    render(<RouterProvider router={router} />);
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

  it("switches tasks and refreshes the single-task summary", async () => {
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
          {
            id: "TASK-REVIEW",
            status: "reviewing",
            competition_name: "CCPC Final",
            competition_location: "成都",
            competition_start_date: "2026-06-01",
            competition_end_date: "2026-06-03",
            deadline: "2026-06-08T18:00:00+08:00",
            member_ids: ["2250001", "2250003"],
            fee_categories: ["hotel"],
            administrator_id: "admin-2",
            project_info: "ACM 竞赛项目",
            reimburser_info: "李管理员",
            invoice_title: "同济大学",
            tax_number: "91310113666007253C",
            created_at: "2026-04-28T09:00:00+08:00",
            updated_at: "2026-04-28T09:00:00+08:00",
          },
        ]));
      }

      if (url === "/api/tasks/TASK-OPEN/member-status?actor_id=2250001") {
        return Promise.resolve(jsonResponse({
          task_id: "TASK-OPEN",
          actor_id: "2250001",
          total_expense_amount_cents: 6345,
          counts: {
            material_count: 1,
            missing_material_count: 1,
            expense_detail_count: 1,
            recognition_pending_count: 0,
            recognition_succeeded_count: 0,
            recognition_failed_count: 0,
            recognition_needs_confirmation_count: 1,
            validation_passed_count: 0,
            validation_failed_count: 1,
            validation_pending_count: 0,
            validation_not_applicable_count: 0,
            confirmed_expense_count: 0,
            pending_confirmation_count: 1,
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
              recognition_status: "needs_confirmation",
              recognition_failure_stage: null,
              recognition_failure_reason: null,
              invoice_id: "INV-OPEN-001",
              invoice_number: "INV-OPEN-001",
              validation_status: "failed",
              validation_messages: ["缺少支付记录"],
              created_at: "2026-04-28T10:00:00+08:00",
            },
          ],
          missing_materials: [
            {
              task_id: "TASK-OPEN",
              member_id: "2250001",
              invoice_id: "INV-OPEN-001",
              invoice_number: "INV-OPEN-001",
              expense_type: "railway",
              required_material_type: "payment_record",
              source_rule_code: "invoice_payment_record_required",
              message: "缺少支付记录。",
              evidence: {},
              detected_at: "2026-04-28T10:10:00+08:00",
            },
          ],
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
                status: "pending",
                dispute_reason: null,
                confirmed_at: "2026-04-28T10:06:00+08:00",
                updated_at: "2026-04-28T10:06:00+08:00",
              },
            },
          ],
        }));
      }

      if (url === "/api/tasks/TASK-OPEN/invoices") {
        return Promise.resolve(jsonResponse({
          items: [
            {
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
              created_at: "2026-04-28T10:00:00+08:00",
              updated_at: "2026-04-28T10:05:00+08:00",
            },
          ],
        }));
      }

      if (url === "/api/materials/MAT-OPEN-001/recognition-tasks") {
        return Promise.resolve(jsonResponse({
          latest_effective: {
            id: "REC-OPEN-001",
            material_id: "MAT-OPEN-001",
            status: "needs_confirmation",
            is_final_fact: false,
            failure: null,
            raw_response: {},
            recognized_fields: {
              invoice_number: {
                value: "INV-OPEN-001",
                source: "ai",
                confidence: 0.95,
                status: "recognized",
                updated_at: "2026-04-28T10:01:00+08:00",
              },
              buyer_name: {
                value: "同济大学",
                source: "ai",
                confidence: 0.44,
                status: "needs_confirmation",
                updated_at: "2026-04-28T10:01:00+08:00",
              },
              amount_cents: {
                value: 6345,
                source: "ai",
                confidence: 0.93,
                status: "recognized",
                updated_at: "2026-04-28T10:01:00+08:00",
              },
              expense_type: {
                value: "railway",
                source: "ai",
                confidence: 0.9,
                status: "recognized",
                updated_at: "2026-04-28T10:01:00+08:00",
              },
            },
            manual_corrections: [],
            created_at: "2026-04-28T10:01:00+08:00",
            updated_at: "2026-04-28T10:01:00+08:00",
          },
        }));
      }

      if (url === "/api/invoices/INV-OPEN-001/validations") {
        return Promise.resolve(jsonResponse({
          items: [
            {
              id: "VAL-OPEN-001",
              rule_code: "invoice_payment_record_required",
              target_type: "invoice",
              target_id: "INV-OPEN-001",
              severity: "blocker",
              status: "failed",
              message: "缺少支付记录。",
              evidence: {},
              created_at: "2026-04-28T10:10:00+08:00",
            },
          ],
        }));
      }

      if (url === "/api/invoices/INV-OPEN-001/supporting-materials") {
        return Promise.resolve(jsonResponse({ items: [] }));
      }

      if (url === "/api/invoices/INV-OPEN-001/splits") {
        return Promise.resolve(jsonResponse({
          items: [
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
        }));
      }

      if (url === "/api/invoices/INV-OPEN-001/confirmations") {
        return Promise.resolve(jsonResponse({
          items: [
            {
              id: "CONF-OPEN-001",
              split_id: "SPLIT-OPEN-001",
              member_id: "2250001",
              split_version: 1,
              split_amount_cents: 6345,
              split_note: "self paid",
              is_current: true,
              status: "pending",
              dispute_reason: null,
              confirmed_at: "2026-04-28T10:06:00+08:00",
              updated_at: "2026-04-28T10:06:00+08:00",
            },
          ],
        }));
      }

      if (url === "/api/tasks/TASK-REVIEW/member-status?actor_id=2250001") {
        return Promise.resolve(jsonResponse({
          task_id: "TASK-REVIEW",
          actor_id: "2250001",
          total_expense_amount_cents: 20000,
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
              material_id: "MAT-REVIEW-001",
              submitter_id: "2250001",
              material_type: "invoice",
              original_filename: "hotel.pdf",
              material_status: "assigned",
              recognition_status: "succeeded",
              recognition_failure_stage: null,
              recognition_failure_reason: null,
              invoice_id: "INV-REVIEW-001",
              invoice_number: "HOTEL-001",
              validation_status: "passed",
              validation_messages: [],
              created_at: "2026-04-28T11:00:00+08:00",
            },
          ],
          missing_materials: [],
          expense_details: [
            {
              split_id: "SPLIT-REVIEW-001",
              split_version: 1,
              member_id: "2250001",
              amount_cents: 20000,
              note: "hotel shared",
              created_at: "2026-04-28T11:05:00+08:00",
              updated_at: "2026-04-28T11:05:00+08:00",
              invoice: {
                id: "INV-REVIEW-001",
                material_id: "MAT-REVIEW-001",
                invoice_number: "HOTEL-001",
                issue_date: "2026-04-22",
                transaction_time: "2026-04-22T09:00:00+08:00",
                buyer_name: "同济大学",
                seller_name: "锦江酒店",
                amount_cents: 20000,
                expense_type: "hotel",
                created_at: "2026-04-28T11:00:00+08:00",
                updated_at: "2026-04-28T11:05:00+08:00",
              },
              confirmation: {
                id: "CONF-REVIEW-001",
                member_id: "2250001",
                split_version: 1,
                status: "confirmed",
                dispute_reason: null,
                confirmed_at: "2026-04-28T11:06:00+08:00",
                updated_at: "2026-04-28T11:06:00+08:00",
              },
            },
          ],
        }));
      }

      if (url === "/api/tasks/TASK-REVIEW/invoices") {
        return Promise.resolve(jsonResponse({
          items: [
            {
              id: "INV-REVIEW-001",
              task_id: "TASK-REVIEW",
              material_id: "MAT-REVIEW-001",
              invoice_number: "HOTEL-001",
              issue_date: "2026-04-22",
              transaction_time: "2026-04-22T09:00:00+08:00",
              buyer_name: "同济大学",
              tax_number: "91310113666007253C",
              seller_name: "锦江酒店",
              amount_cents: 20000,
              expense_type: "hotel",
              created_at: "2026-04-28T11:00:00+08:00",
              updated_at: "2026-04-28T11:05:00+08:00",
            },
          ],
        }));
      }

      if (url === "/api/materials/MAT-REVIEW-001/recognition-tasks") {
        return Promise.resolve(jsonResponse({
          latest_effective: {
            id: "REC-REVIEW-001",
            material_id: "MAT-REVIEW-001",
            status: "succeeded",
            is_final_fact: false,
            failure: null,
            raw_response: {},
            recognized_fields: {
              invoice_number: {
                value: "HOTEL-001",
                source: "ai",
                confidence: 0.97,
                status: "recognized",
                updated_at: "2026-04-28T11:01:00+08:00",
              },
              buyer_name: {
                value: "同济大学",
                source: "ai",
                confidence: 0.95,
                status: "recognized",
                updated_at: "2026-04-28T11:01:00+08:00",
              },
              amount_cents: {
                value: 20000,
                source: "ai",
                confidence: 0.94,
                status: "recognized",
                updated_at: "2026-04-28T11:01:00+08:00",
              },
              expense_type: {
                value: "hotel",
                source: "ai",
                confidence: 0.9,
                status: "recognized",
                updated_at: "2026-04-28T11:01:00+08:00",
              },
            },
            manual_corrections: [],
            created_at: "2026-04-28T11:01:00+08:00",
            updated_at: "2026-04-28T11:01:00+08:00",
          },
        }));
      }

      if (url === "/api/invoices/INV-REVIEW-001/validations") {
        return Promise.resolve(jsonResponse({ items: [] }));
      }

      if (url === "/api/invoices/INV-REVIEW-001/supporting-materials") {
        return Promise.resolve(jsonResponse({
          items: [
            {
              id: "MAT-REVIEW-PAY",
              status: "assigned",
              task_id: "TASK-REVIEW",
              submitter_id: "2250001",
              task_id_hint: null,
              submitter_id_hint: null,
              channel: "web",
              material_type: "payment_record",
              storage_key: "TASK-REVIEW/MAT-REVIEW-PAY.png",
              original_filename: "pay.png",
              content_type: "image/png",
              size_bytes: 2048,
              sha256: "a".repeat(64),
              duplicate_of: null,
              claimed_by: null,
              claimed_at: null,
              created_at: "2026-04-28T10:40:00+08:00",
            },
          ],
        }));
      }

      if (url === "/api/invoices/INV-REVIEW-001/splits") {
        return Promise.resolve(jsonResponse({
          items: [
            {
              id: "SPLIT-REVIEW-001",
              invoice_id: "INV-REVIEW-001",
              member_id: "2250001",
              amount_cents: 20000,
              note: "hotel shared",
              version: 1,
              is_active: true,
              created_at: "2026-04-28T11:05:00+08:00",
              updated_at: "2026-04-28T11:05:00+08:00",
            },
          ],
        }));
      }

      if (url === "/api/invoices/INV-REVIEW-001/confirmations") {
        return Promise.resolve(jsonResponse({
          items: [
            {
              id: "CONF-REVIEW-001",
              split_id: "SPLIT-REVIEW-001",
              member_id: "2250001",
              split_version: 1,
              split_amount_cents: 20000,
              split_note: "hotel shared",
              is_current: true,
              status: "confirmed",
              dispute_reason: null,
              confirmed_at: "2026-04-28T11:06:00+08:00",
              updated_at: "2026-04-28T11:06:00+08:00",
            },
          ],
        }));
      }

      if (url.includes("/shared-invoices?actor_id=2250001")) {
        return Promise.resolve(jsonResponse({
          task_id: url.split("/")[3] ?? "TASK-OPEN",
          actor_id: "2250001",
          items: [],
        }));
      }

      throw new Error(`Unhandled fetch URL in member invoice workbench test: ${url}`);
    });

    renderWorkbenchRoute();

    expect(await screen.findByRole("heading", { name: "按任务查看我的发票与费用" })).toBeInTheDocument();
    const summary = await screen.findByLabelText("成员发票工作台摘要");
    expect(summary).toBeInTheDocument();
    expect(within(summary).getByText("￥63.45")).toBeInTheDocument();
    const workbenchList = await screen.findByLabelText("成员发票工作台列表");
    expect(within(workbenchList).getByRole("heading", { name: "INV-OPEN-001" })).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("目标任务"), {
      target: { value: "TASK-REVIEW" },
    });

    expect(within(await screen.findByLabelText("成员发票工作台列表")).getByRole("heading", { name: "HOTEL-001" })).toBeInTheDocument();
    expect(within(await screen.findByLabelText("成员发票工作台摘要")).getByText("￥200.00")).toBeInTheDocument();
    expect(screen.getByText("状态稳定")).toBeInTheDocument();
  });

  it("shows key abnormal prompts, manual override comparison, and next actions", async () => {
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
            fee_categories: ["airfare"],
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

      if (url === "/api/tasks/TASK-OPEN/member-status?actor_id=2250001") {
        return Promise.resolve(jsonResponse({
          task_id: "TASK-OPEN",
          actor_id: "2250001",
          total_expense_amount_cents: 12000,
          counts: {
            material_count: 1,
            missing_material_count: 1,
            expense_detail_count: 1,
            recognition_pending_count: 0,
            recognition_succeeded_count: 0,
            recognition_failed_count: 1,
            recognition_needs_confirmation_count: 0,
            validation_passed_count: 0,
            validation_failed_count: 1,
            validation_pending_count: 0,
            validation_not_applicable_count: 0,
            confirmed_expense_count: 0,
            pending_confirmation_count: 1,
            disputed_confirmation_count: 0,
            missing_confirmation_count: 0,
          },
          materials: [
            {
              material_id: "MAT-ABN-001",
              submitter_id: "2250001",
              material_type: "invoice",
              original_filename: "airfare.pdf",
              material_status: "assigned",
              recognition_status: "failed",
              recognition_failure_stage: "ai",
              recognition_failure_reason: "provider timeout",
              invoice_id: "INV-ABN-001",
              invoice_number: "AIR-001",
              validation_status: "failed",
              validation_messages: ["缺少行程单。"],
              created_at: "2026-04-28T12:00:00+08:00",
            },
          ],
          missing_materials: [
            {
              task_id: "TASK-OPEN",
              member_id: "2250001",
              invoice_id: "INV-ABN-001",
              invoice_number: "AIR-001",
              expense_type: "airfare",
              required_material_type: "itinerary",
              source_rule_code: "invoice_airfare_itinerary_required",
              message: "缺少行程单。",
              evidence: {},
              detected_at: "2026-04-28T12:10:00+08:00",
            },
          ],
          expense_details: [
            {
              split_id: "SPLIT-ABN-001",
              split_version: 2,
              member_id: "2250001",
              amount_cents: 12000,
              note: "team flight",
              created_at: "2026-04-28T12:05:00+08:00",
              updated_at: "2026-04-28T12:05:00+08:00",
              invoice: {
                id: "INV-ABN-001",
                material_id: "MAT-ABN-001",
                invoice_number: "AIR-001",
                issue_date: "2026-04-25",
                transaction_time: "2026-04-25T09:00:00+08:00",
                buyer_name: "同济大学",
                seller_name: "东方航空",
                amount_cents: 12000,
                expense_type: "airfare",
                created_at: "2026-04-28T12:00:00+08:00",
                updated_at: "2026-04-28T12:05:00+08:00",
              },
              confirmation: {
                id: "CONF-ABN-001",
                member_id: "2250001",
                split_version: 2,
                status: "pending",
                dispute_reason: null,
                confirmed_at: "2026-04-28T12:06:00+08:00",
                updated_at: "2026-04-28T12:06:00+08:00",
              },
            },
          ],
        }));
      }

      if (url === "/api/tasks/TASK-OPEN/invoices") {
        return Promise.resolve(jsonResponse({
          items: [
            {
              id: "INV-ABN-001",
              task_id: "TASK-OPEN",
              material_id: "MAT-ABN-001",
              invoice_number: "AIR-001",
              issue_date: "2026-04-25",
              transaction_time: "2026-04-25T09:00:00+08:00",
              buyer_name: "同济大学",
              tax_number: "91310113666007253C",
              seller_name: "东方航空",
              amount_cents: 12000,
              expense_type: "airfare",
              created_at: "2026-04-28T12:00:00+08:00",
              updated_at: "2026-04-28T12:05:00+08:00",
            },
          ],
        }));
      }

      if (url === "/api/materials/MAT-ABN-001/recognition-tasks") {
        return Promise.resolve(jsonResponse({
          latest_effective: {
            id: "REC-ABN-001",
            material_id: "MAT-ABN-001",
            status: "failed",
            is_final_fact: false,
            failure: {
              stage: "ai",
              reason: "provider timeout",
            },
            raw_response: {},
            recognized_fields: {
              buyer_name: {
                value: "同济",
                source: "ai",
                confidence: 0.31,
                status: "needs_confirmation",
                updated_at: "2026-04-28T12:01:00+08:00",
              },
              amount_cents: {
                value: 11000,
                source: "ai",
                confidence: 0.4,
                status: "needs_confirmation",
                updated_at: "2026-04-28T12:01:00+08:00",
              },
            },
            manual_corrections: [],
            created_at: "2026-04-28T12:01:00+08:00",
            updated_at: "2026-04-28T12:01:00+08:00",
          },
        }));
      }

      if (url === "/api/invoices/INV-ABN-001/validations") {
        return Promise.resolve(jsonResponse({
          items: [
            {
              id: "VAL-ABN-001",
              rule_code: "invoice_airfare_itinerary_required",
              target_type: "invoice",
              target_id: "INV-ABN-001",
              severity: "blocker",
              status: "failed",
              message: "缺少行程单。",
              evidence: {},
              created_at: "2026-04-28T12:10:00+08:00",
            },
          ],
        }));
      }

      if (url === "/api/invoices/INV-ABN-001/supporting-materials") {
        return Promise.resolve(jsonResponse({ items: [] }));
      }

      if (url === "/api/invoices/INV-ABN-001/splits") {
        return Promise.resolve(jsonResponse({
          items: [
            {
              id: "SPLIT-ABN-001",
              invoice_id: "INV-ABN-001",
              member_id: "2250001",
              amount_cents: 12000,
              note: "team flight",
              version: 2,
              is_active: true,
              created_at: "2026-04-28T12:05:00+08:00",
              updated_at: "2026-04-28T12:05:00+08:00",
            },
          ],
        }));
      }

      if (url === "/api/invoices/INV-ABN-001/confirmations") {
        return Promise.resolve(jsonResponse({
          items: [
            {
              id: "CONF-ABN-001",
              split_id: "SPLIT-ABN-001",
              member_id: "2250001",
              split_version: 2,
              split_amount_cents: 12000,
              split_note: "team flight",
              is_current: true,
              status: "pending",
              dispute_reason: null,
              confirmed_at: "2026-04-28T12:06:00+08:00",
              updated_at: "2026-04-28T12:06:00+08:00",
            },
          ],
        }));
      }

      if (url.includes("/shared-invoices?actor_id=2250001")) {
        return Promise.resolve(jsonResponse({
          task_id: url.split("/")[3] ?? "TASK-OPEN",
          actor_id: "2250001",
          items: [],
        }));
      }

      throw new Error(`Unhandled fetch URL in member invoice workbench test: ${url}`);
    });

    renderWorkbenchRoute();

    const cardList = await screen.findByLabelText("成员发票工作台列表");
    const card = within(cardList).getByRole("heading", { name: "AIR-001" }).closest("article");
    if (!card) {
      throw new Error("expected one workbench card");
    }

    expect(within(card).getByText("材料信息暂时无法整理，请稍后重试或改为人工补录。")).toBeInTheDocument();
    expect(within(card).getByText("缺少行程单。")).toBeInTheDocument();
    expect(within(card).getByText("识别值：同济")).toBeInTheDocument();
    expect(within(card).getByText("当前值：同济大学")).toBeInTheDocument();
    expect(within(card).getAllByText("状态：已人工更正").length).toBeGreaterThan(0);
    expect(within(card).getByText("确认状态：待确认")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "去上传区补材料" })).toHaveAttribute(
      "href",
      "/member/invoices/workbench?taskId=TASK-OPEN#member-workbench-upload",
    );
    expect(screen.getByRole("link", { name: "去确认区处理" })).toHaveAttribute(
      "href",
      "/member/invoices/workbench?taskId=TASK-OPEN#member-workbench-confirmations",
    );
  });

  it("shows pending recognition as a blocking state instead of pretending nothing happened", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((input: string | URL | Request) => {
      const url = resolveRequestUrl(input);

      if (url === "/api/tasks") {
        return Promise.resolve(jsonResponse([
          {
            id: "TASK-PENDING",
            status: "open",
            competition_name: "ICPC Pending Recognition",
            competition_location: "南京",
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

      if (url === "/api/tasks/TASK-PENDING/member-status?actor_id=2250001") {
        return Promise.resolve(jsonResponse({
          task_id: "TASK-PENDING",
          actor_id: "2250001",
          total_expense_amount_cents: 0,
          counts: {
            material_count: 1,
            missing_material_count: 0,
            expense_detail_count: 0,
            recognition_pending_count: 1,
            recognition_succeeded_count: 0,
            recognition_failed_count: 0,
            recognition_needs_confirmation_count: 0,
            validation_passed_count: 0,
            validation_failed_count: 0,
            validation_pending_count: 0,
            validation_not_applicable_count: 1,
            confirmed_expense_count: 0,
            pending_confirmation_count: 0,
            disputed_confirmation_count: 0,
            missing_confirmation_count: 0,
          },
          materials: [
            {
              material_id: "MAT-PENDING-001",
              submitter_id: "2250001",
              material_type: "invoice",
              original_filename: "pending.pdf",
              material_status: "assigned",
              recognition_status: "pending",
              recognition_failure_stage: null,
              recognition_failure_reason: null,
              invoice_id: null,
              invoice_number: null,
              validation_status: "not_applicable",
              validation_messages: [],
              created_at: "2026-04-28T14:00:00+08:00",
            },
          ],
          missing_materials: [],
          expense_details: [],
        }));
      }

      if (url === "/api/tasks/TASK-PENDING/invoices") {
        return Promise.resolve(jsonResponse({ items: [] }));
      }

      if (url === "/api/materials/MAT-PENDING-001/recognition-tasks") {
        return Promise.resolve(jsonResponse({
          latest_effective: null,
          items: [
            {
              id: "REC-PENDING-001",
              material_id: "MAT-PENDING-001",
              status: "pending",
              is_final_fact: false,
              failure: null,
              raw_response: null,
              recognized_fields: {},
              manual_corrections: [],
              created_at: "2026-04-28T14:00:10+08:00",
              updated_at: "2026-04-28T14:00:10+08:00",
            },
          ],
        }));
      }

      if (url.includes("/shared-invoices?actor_id=2250001")) {
        return Promise.resolve(jsonResponse({
          task_id: "TASK-PENDING",
          actor_id: "2250001",
          items: [],
        }));
      }

      throw new Error(`Unhandled fetch URL in pending recognition workbench test: ${url}`);
    });

    renderWorkbenchRoute("/member/invoices/workbench?taskId=TASK-PENDING");

    expect(await screen.findByText("1 项仍待处理")).toBeInTheDocument();
    expect(screen.getByText("等待系统完成识别")).toBeInTheDocument();
    expect(screen.queryByText("当前无明显异常")).not.toBeInTheDocument();

    const workbenchList = await screen.findByLabelText("成员发票工作台列表");
    const card = within(workbenchList).getByRole("heading", { name: "pending.pdf" }).closest("article");
    if (!card) {
      throw new Error("expected pending recognition card");
    }

    expect(within(card).getByText("识别状态")).toBeInTheDocument();
    expect(within(card).getByText("识别处理中")).toBeInTheDocument();
    expect(
      within(card).getByText("系统正在处理该材料识别；识别完成前，暂时还不能生成完整发票字段、分摊与确认上下文。"),
    ).toBeInTheDocument();
  });

  it("explains when recognition service is not configured instead of only showing a generic failure", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((input: string | URL | Request) => {
      const url = resolveRequestUrl(input);

      if (url === "/api/tasks") {
        return Promise.resolve(jsonResponse([
          {
            id: "TASK-DISABLED",
            status: "open",
            competition_name: "ICPC Disabled Recognition",
            competition_location: "上海",
            competition_start_date: "2026-05-01",
            competition_end_date: "2026-05-03",
            deadline: "2026-05-10T12:00:00+08:00",
            member_ids: ["2250001"],
            fee_categories: ["hotel"],
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

      if (url === "/api/tasks/TASK-DISABLED/member-status?actor_id=2250001") {
        return Promise.resolve(jsonResponse({
          task_id: "TASK-DISABLED",
          actor_id: "2250001",
          total_expense_amount_cents: 0,
          counts: {
            material_count: 1,
            missing_material_count: 0,
            expense_detail_count: 0,
            recognition_pending_count: 0,
            recognition_succeeded_count: 0,
            recognition_failed_count: 1,
            recognition_needs_confirmation_count: 0,
            validation_passed_count: 0,
            validation_failed_count: 0,
            validation_pending_count: 0,
            validation_not_applicable_count: 1,
            confirmed_expense_count: 0,
            pending_confirmation_count: 0,
            disputed_confirmation_count: 0,
            missing_confirmation_count: 0,
          },
          materials: [
            {
              material_id: "MAT-DISABLED-001",
              submitter_id: "2250001",
              material_type: "invoice",
              original_filename: "disabled.pdf",
              material_status: "assigned",
              recognition_status: "failed",
              recognition_failure_stage: "ai",
              recognition_failure_reason: "llm_provider_not_configured",
              invoice_id: null,
              invoice_number: null,
              validation_status: "not_applicable",
              validation_messages: [],
              created_at: "2026-04-28T15:00:00+08:00",
            },
          ],
          missing_materials: [],
          expense_details: [],
        }));
      }

      if (url === "/api/tasks/TASK-DISABLED/invoices") {
        return Promise.resolve(jsonResponse({ items: [] }));
      }

      if (url === "/api/materials/MAT-DISABLED-001/recognition-tasks") {
        return Promise.resolve(jsonResponse({
          latest_effective: {
            id: "REC-DISABLED-001",
            material_id: "MAT-DISABLED-001",
            status: "failed",
            is_final_fact: false,
            failure: {
              stage: "ai",
              reason: "llm_provider_not_configured",
            },
            raw_response: {},
            recognized_fields: {},
            manual_corrections: [],
            created_at: "2026-04-28T15:00:10+08:00",
            updated_at: "2026-04-28T15:00:10+08:00",
          },
          items: [],
        }));
      }

      if (url.includes("/shared-invoices?actor_id=2250001")) {
        return Promise.resolve(jsonResponse({
          task_id: "TASK-DISABLED",
          actor_id: "2250001",
          items: [],
        }));
      }

      throw new Error(`Unhandled fetch URL in disabled recognition workbench test: ${url}`);
    });

    renderWorkbenchRoute("/member/invoices/workbench?taskId=TASK-DISABLED");

    const workbenchList = await screen.findByLabelText("成员发票工作台列表");
    const card = within(workbenchList).getByRole("heading", { name: "disabled.pdf" }).closest("article");
    if (!card) {
      throw new Error("expected disabled recognition card");
    }

    expect(
      within(card).getByText("当前环境未配置识别服务，系统暂时不能自动生成发票结构化结果；请联系管理员配置识别服务或改为人工补录。"),
    ).toBeInTheDocument();
  });

  it("allows members to update material type from the workbench and refreshes the task summary", async () => {
    let currentMaterialType = "other_attachment";

    vi.spyOn(globalThis, "fetch").mockImplementation((input: string | URL | Request, init?: RequestInit) => {
      const url = resolveRequestUrl(input);
      const method = init?.method ?? (input instanceof Request ? input.method : "GET");

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

      if (url === "/api/tasks/TASK-OPEN/member-status?actor_id=2250001") {
        return Promise.resolve(jsonResponse({
          task_id: "TASK-OPEN",
          actor_id: "2250001",
          total_expense_amount_cents: 0,
          counts: {
            material_count: 1,
            missing_material_count: 0,
            expense_detail_count: 0,
            recognition_pending_count: 0,
            recognition_succeeded_count: 0,
            recognition_failed_count: 0,
            recognition_needs_confirmation_count: 0,
            validation_passed_count: 0,
            validation_failed_count: 0,
            validation_pending_count: 0,
            validation_not_applicable_count: 1,
            confirmed_expense_count: 0,
            pending_confirmation_count: 0,
            disputed_confirmation_count: 0,
            missing_confirmation_count: 0,
          },
          materials: [
            {
              material_id: "MAT-EDIT-001",
              submitter_id: "2250001",
              material_type: currentMaterialType,
              original_filename: "payment.pdf",
              material_status: "assigned",
              recognition_status: null,
              recognition_failure_stage: null,
              recognition_failure_reason: null,
              invoice_id: null,
              invoice_number: null,
              validation_status: "not_applicable",
              validation_messages: [],
              created_at: "2026-04-28T10:00:00+08:00",
            },
          ],
          missing_materials: [],
          expense_details: [],
        }));
      }

      if (url === "/api/tasks/TASK-OPEN/invoices") {
        return Promise.resolve(jsonResponse({ items: [] }));
      }

      if (url === "/api/materials/MAT-EDIT-001/recognition-tasks") {
        return Promise.resolve(jsonResponse({
          latest_effective: null,
          items: [],
        }));
      }

      if (url === "/api/materials/MAT-EDIT-001/material-type" && method === "PATCH") {
        if (typeof init?.body !== "string") {
          throw new Error("expected PATCH body to be serialized JSON");
        }
        const payload = JSON.parse(init.body) as { material_type: string };
        currentMaterialType = payload.material_type;
        return Promise.resolve(jsonResponse({
          item: {
            id: "MAT-EDIT-001",
            status: "assigned",
            task_id: "TASK-OPEN",
            submitter_id: "2250001",
            task_id_hint: null,
            submitter_id_hint: null,
            channel: "web",
            material_type: currentMaterialType,
            storage_key: "TASK-OPEN/payment.pdf",
            original_filename: "payment.pdf",
            content_type: "application/pdf",
            size_bytes: 16,
            sha256: "a".repeat(64),
            duplicate_of: null,
            claimed_by: null,
            claimed_at: null,
            created_at: "2026-04-28T10:00:00+08:00",
          },
        }));
      }

      if (url.includes("/shared-invoices?actor_id=2250001")) {
        return Promise.resolve(jsonResponse({
          task_id: url.split("/")[3] ?? "TASK-OPEN",
          actor_id: "2250001",
          items: [],
        }));
      }

      throw new Error(`Unhandled fetch URL in member invoice workbench test: ${url}`);
    });

    renderWorkbenchRoute();

    const select = await screen.findByLabelText("MAT-EDIT-001 材料类型");
    expect(select).toHaveValue("other_attachment");

    fireEvent.change(select, { target: { value: "payment_record" } });
    fireEvent.click(screen.getByRole("button", { name: "保存材料类型" }));

    await screen.findByText("支付记录 / MAT-EDIT-001");
    expect(screen.getByLabelText("MAT-EDIT-001 材料类型")).toHaveValue("payment_record");
  });

  it("lets the member adjust split targets and shows refreshed confirmation states", async () => {
    let currentSplits: Array<{
      id: string;
      invoice_id: string;
      member_id: string;
      amount_cents: number;
      note: string | null;
      version: number;
      is_active: boolean;
      created_at: string;
      updated_at: string;
    }> = [
      {
        id: "SPLIT-SHARED-001",
        invoice_id: "INV-SHARED-001",
        member_id: "2250001",
        amount_cents: 12345,
        note: "self paid",
        version: 1,
        is_active: true,
        created_at: "2026-04-28T13:05:00+08:00",
        updated_at: "2026-04-28T13:05:00+08:00",
      },
    ];
    let currentConfirmations = [
      {
        id: "CONF-SHARED-001",
        split_id: "SPLIT-SHARED-001",
        member_id: "2250001",
        split_version: 1,
        split_amount_cents: 12345,
        split_note: "self paid",
        is_current: true,
        status: "confirmed",
        dispute_reason: null,
        confirmed_at: "2026-04-28T13:06:00+08:00",
        updated_at: "2026-04-28T13:06:00+08:00",
      },
    ];
    let receivedSplitPayload: Array<{ member_id: string; amount_cents: number; note?: string | null }> = [];

    function buildMemberStatusResponse() {
      const ownSplit = currentSplits.find((split) => split.member_id === "2250001");
      const ownConfirmation = ownSplit
        ? currentConfirmations.find(
          (confirmation) => confirmation.split_id === ownSplit.id && confirmation.is_current,
        ) ?? null
        : null;
      return {
        task_id: "TASK-OPEN",
        actor_id: "2250001",
        total_expense_amount_cents: ownSplit?.amount_cents ?? 0,
        counts: {
          material_count: 1,
          missing_material_count: 0,
          expense_detail_count: ownSplit ? 1 : 0,
          recognition_pending_count: 0,
          recognition_succeeded_count: 0,
          recognition_failed_count: 0,
          recognition_needs_confirmation_count: 0,
          validation_passed_count: 1,
          validation_failed_count: 0,
          validation_pending_count: 0,
          validation_not_applicable_count: 0,
          confirmed_expense_count: ownConfirmation?.status === "confirmed" ? 1 : 0,
          pending_confirmation_count: ownConfirmation?.status === "pending" ? 1 : 0,
          disputed_confirmation_count: 0,
          missing_confirmation_count: ownConfirmation ? 0 : 1,
        },
        materials: [
          {
            material_id: "MAT-SHARED-001",
            submitter_id: "2250001",
            material_type: "invoice",
            original_filename: "shared.pdf",
            material_status: "assigned",
            recognition_status: null,
            recognition_failure_stage: null,
            recognition_failure_reason: null,
            invoice_id: "INV-SHARED-001",
            invoice_number: "SHARED-001",
            validation_status: "passed",
            validation_messages: [],
            created_at: "2026-04-28T13:00:00+08:00",
          },
        ],
        missing_materials: [],
        expense_details: ownSplit ? [
          {
            split_id: ownSplit.id,
            split_version: ownSplit.version,
            member_id: ownSplit.member_id,
            amount_cents: ownSplit.amount_cents,
            note: ownSplit.note,
            created_at: ownSplit.created_at,
            updated_at: ownSplit.updated_at,
            invoice: {
              id: "INV-SHARED-001",
              material_id: "MAT-SHARED-001",
              invoice_number: "SHARED-001",
              issue_date: "2026-04-25",
              transaction_time: "2026-04-25T09:00:00+08:00",
              buyer_name: "同济大学",
              seller_name: "12306",
              amount_cents: 12345,
              expense_type: "railway",
              created_at: "2026-04-28T13:00:00+08:00",
              updated_at: "2026-04-28T13:05:00+08:00",
            },
            confirmation: ownConfirmation ? {
              id: ownConfirmation.id,
              member_id: ownConfirmation.member_id,
              split_version: ownConfirmation.split_version,
              status: ownConfirmation.status,
              dispute_reason: ownConfirmation.dispute_reason,
              confirmed_at: ownConfirmation.confirmed_at,
              updated_at: ownConfirmation.updated_at,
            } : null,
          },
        ] : [],
      };
    }

    vi.spyOn(globalThis, "fetch").mockImplementation((input: string | URL | Request, init?: RequestInit) => {
      const url = resolveRequestUrl(input);
      const method = init?.method ?? "GET";

      if (url === "/api/tasks") {
        return Promise.resolve(jsonResponse([
          {
            id: "TASK-OPEN",
            status: "open",
            competition_name: "ICPC Shared Expense",
            competition_location: "杭州",
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

      if (url === "/api/tasks/TASK-OPEN/member-status?actor_id=2250001") {
        return Promise.resolve(jsonResponse(buildMemberStatusResponse()));
      }

      if (url === "/api/tasks/TASK-OPEN/invoices") {
        return Promise.resolve(jsonResponse({
          items: [
            {
              id: "INV-SHARED-001",
              task_id: "TASK-OPEN",
              material_id: "MAT-SHARED-001",
              invoice_number: "SHARED-001",
              issue_date: "2026-04-25",
              transaction_time: "2026-04-25T09:00:00+08:00",
              buyer_name: "同济大学",
              tax_number: "91310113666007253C",
              seller_name: "12306",
              amount_cents: 12345,
              expense_type: "railway",
              created_at: "2026-04-28T13:00:00+08:00",
              updated_at: "2026-04-28T13:05:00+08:00",
            },
          ],
        }));
      }

      if (url === "/api/materials/MAT-SHARED-001/recognition-tasks") {
        return Promise.resolve(jsonResponse({ latest_effective: null, items: [] }));
      }

      if (url === "/api/invoices/INV-SHARED-001/validations") {
        return Promise.resolve(jsonResponse({ items: [] }));
      }

      if (url === "/api/invoices/INV-SHARED-001/supporting-materials") {
        return Promise.resolve(jsonResponse({ items: [] }));
      }

      if (url === "/api/invoices/INV-SHARED-001/splits" && method === "GET") {
        return Promise.resolve(jsonResponse({ items: currentSplits }));
      }

      if (url === "/api/invoices/INV-SHARED-001/splits" && method === "PUT") {
        if (typeof init?.body !== "string") {
          throw new Error("expected PUT body to be serialized JSON");
        }
        const payload = JSON.parse(init.body) as {
          items: Array<{ member_id: string; amount_cents: number; note?: string | null }>;
        };
        receivedSplitPayload = payload.items;
        currentSplits = payload.items.map((item, index) => ({
          id: index === 0 ? "SPLIT-SHARED-001" : "SPLIT-SHARED-002",
          invoice_id: "INV-SHARED-001",
          member_id: item.member_id,
          amount_cents: item.amount_cents,
          note: item.note ?? null,
          version: 2,
          is_active: true,
          created_at: "2026-04-28T13:05:00+08:00",
          updated_at: "2026-04-28T13:20:00+08:00",
        }));
        currentConfirmations = [
          {
            id: "CONF-SHARED-002",
            split_id: "SPLIT-SHARED-001",
            member_id: "2250001",
            split_version: 2,
            split_amount_cents: 10000,
            split_note: "self adjusted",
            is_current: true,
            status: "pending",
            dispute_reason: null,
            confirmed_at: "2026-04-28T13:20:00+08:00",
            updated_at: "2026-04-28T13:20:00+08:00",
          },
        ];
        return Promise.resolve(jsonResponse({ items: currentSplits }));
      }

      if (url === "/api/invoices/INV-SHARED-001/confirmations") {
        return Promise.resolve(jsonResponse({ items: currentConfirmations }));
      }

      if (url.includes("/shared-invoices?actor_id=2250001")) {
        return Promise.resolve(jsonResponse({
          task_id: url.split("/")[3] ?? "TASK-OPEN",
          actor_id: "2250001",
          items: [],
        }));
      }

      throw new Error(`Unhandled fetch URL in member invoice workbench split test: ${url}`);
    });

    renderWorkbenchRoute();

    const splitWorkbenchList = await screen.findByLabelText("成员发票工作台列表");
    expect(within(splitWorkbenchList).getByRole("heading", { name: "SHARED-001" })).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("INV-SHARED-001 分摊行 1 金额"), {
      target: { value: "100.00" },
    });
    fireEvent.change(screen.getByLabelText("INV-SHARED-001 分摊行 1 备注"), {
      target: { value: "self adjusted" },
    });
    fireEvent.click(screen.getByRole("button", { name: "新增分摊对象" }));
    fireEvent.change(screen.getByLabelText("INV-SHARED-001 分摊行 2 成员"), {
      target: { value: "2250002" },
    });
    fireEvent.change(screen.getByLabelText("INV-SHARED-001 分摊行 2 金额"), {
      target: { value: "23.45" },
    });
    fireEvent.change(screen.getByLabelText("INV-SHARED-001 分摊行 2 备注"), {
      target: { value: "shared ride" },
    });
    fireEvent.click(screen.getByRole("button", { name: "保存分摊方案" }));

    await screen.findByText("备注：shared ride");
    expect(receivedSplitPayload).toEqual([
      { member_id: "2250001", amount_cents: 10000, note: "self adjusted" },
      { member_id: "2250002", amount_cents: 2345, note: "shared ride" },
    ]);

    const splitSection = screen.getByRole("list", { name: "MAT-SHARED-001 分摊列表" });
    const splitEntries = within(splitSection).getAllByRole("listitem");
    expect(splitEntries).toHaveLength(2);
    expect(within(splitEntries[0]!).getByText("确认状态：待确认")).toBeInTheDocument();
    expect(within(splitEntries[1]!).getByText("确认状态：待确认")).toBeInTheDocument();
  });

  it("shows backend failure reasons when saving split changes is rejected", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((input: string | URL | Request, init?: RequestInit) => {
      const url = resolveRequestUrl(input);
      const method = init?.method ?? "GET";

      if (url === "/api/tasks") {
        return Promise.resolve(jsonResponse([
          {
            id: "TASK-OPEN",
            status: "open",
            competition_name: "ICPC Shared Expense",
            competition_location: "杭州",
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

      if (url === "/api/tasks/TASK-OPEN/member-status?actor_id=2250001") {
        return Promise.resolve(jsonResponse({
          task_id: "TASK-OPEN",
          actor_id: "2250001",
          total_expense_amount_cents: 12345,
          counts: {
            material_count: 1,
            missing_material_count: 0,
            expense_detail_count: 1,
            recognition_pending_count: 0,
            recognition_succeeded_count: 0,
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
              material_id: "MAT-FAIL-001",
              submitter_id: "2250001",
              material_type: "invoice",
              original_filename: "shared.pdf",
              material_status: "assigned",
              recognition_status: null,
              recognition_failure_stage: null,
              recognition_failure_reason: null,
              invoice_id: "INV-FAIL-001",
              invoice_number: "FAIL-001",
              validation_status: "passed",
              validation_messages: [],
              created_at: "2026-04-28T13:00:00+08:00",
            },
          ],
          missing_materials: [],
          expense_details: [
            {
              split_id: "SPLIT-FAIL-001",
              split_version: 1,
              member_id: "2250001",
              amount_cents: 12345,
              note: "self paid",
              created_at: "2026-04-28T13:05:00+08:00",
              updated_at: "2026-04-28T13:05:00+08:00",
              invoice: {
                id: "INV-FAIL-001",
                material_id: "MAT-FAIL-001",
                invoice_number: "FAIL-001",
                issue_date: "2026-04-25",
                transaction_time: "2026-04-25T09:00:00+08:00",
                buyer_name: "同济大学",
                seller_name: "12306",
                amount_cents: 12345,
                expense_type: "railway",
                created_at: "2026-04-28T13:00:00+08:00",
                updated_at: "2026-04-28T13:05:00+08:00",
              },
              confirmation: {
                id: "CONF-FAIL-001",
                member_id: "2250001",
                split_version: 1,
                status: "confirmed",
                dispute_reason: null,
                confirmed_at: "2026-04-28T13:06:00+08:00",
                updated_at: "2026-04-28T13:06:00+08:00",
              },
            },
          ],
        }));
      }

      if (url === "/api/tasks/TASK-OPEN/invoices") {
        return Promise.resolve(jsonResponse({
          items: [
            {
              id: "INV-FAIL-001",
              task_id: "TASK-OPEN",
              material_id: "MAT-FAIL-001",
              invoice_number: "FAIL-001",
              issue_date: "2026-04-25",
              transaction_time: "2026-04-25T09:00:00+08:00",
              buyer_name: "同济大学",
              tax_number: "91310113666007253C",
              seller_name: "12306",
              amount_cents: 12345,
              expense_type: "railway",
              created_at: "2026-04-28T13:00:00+08:00",
              updated_at: "2026-04-28T13:05:00+08:00",
            },
          ],
        }));
      }

      if (url === "/api/materials/MAT-FAIL-001/recognition-tasks") {
        return Promise.resolve(jsonResponse({ latest_effective: null, items: [] }));
      }

      if (url === "/api/invoices/INV-FAIL-001/validations") {
        return Promise.resolve(jsonResponse({ items: [] }));
      }

      if (url === "/api/invoices/INV-FAIL-001/supporting-materials") {
        return Promise.resolve(jsonResponse({ items: [] }));
      }

      if (url === "/api/invoices/INV-FAIL-001/splits" && method === "GET") {
        return Promise.resolve(jsonResponse({
          items: [
            {
              id: "SPLIT-FAIL-001",
              invoice_id: "INV-FAIL-001",
              member_id: "2250001",
              amount_cents: 12345,
              note: "self paid",
              version: 1,
              is_active: true,
              created_at: "2026-04-28T13:05:00+08:00",
              updated_at: "2026-04-28T13:05:00+08:00",
            },
          ],
        }));
      }

      if (url === "/api/invoices/INV-FAIL-001/splits" && method === "PUT") {
        return Promise.resolve(jsonResponse(
          { detail: "split amount total must equal invoice amount" },
          { status: 409 },
        ));
      }

      if (url === "/api/invoices/INV-FAIL-001/confirmations") {
        return Promise.resolve(jsonResponse({
          items: [
            {
              id: "CONF-FAIL-001",
              split_id: "SPLIT-FAIL-001",
              member_id: "2250001",
              split_version: 1,
              split_amount_cents: 12345,
              split_note: "self paid",
              is_current: true,
              status: "confirmed",
              dispute_reason: null,
              confirmed_at: "2026-04-28T13:06:00+08:00",
              updated_at: "2026-04-28T13:06:00+08:00",
            },
          ],
        }));
      }

      if (url.includes("/shared-invoices?actor_id=2250001")) {
        return Promise.resolve(jsonResponse({
          task_id: url.split("/")[3] ?? "TASK-OPEN",
          actor_id: "2250001",
          items: [],
        }));
      }

      throw new Error(`Unhandled fetch URL in member invoice workbench split failure test: ${url}`);
    });

    renderWorkbenchRoute();

    const failureWorkbenchList = await screen.findByLabelText("成员发票工作台列表");
    expect(within(failureWorkbenchList).getByRole("heading", { name: "FAIL-001" })).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("INV-FAIL-001 分摊行 1 金额"), {
      target: { value: "100.00" },
    });
    fireEvent.click(screen.getByRole("button", { name: "保存分摊方案" }));

    expect(
      await screen.findByText("split amount total must equal invoice amount"),
    ).toBeInTheDocument();
  });

  it("uploads materials directly from the workbench and refreshes the current task view", async () => {
    let uploadCompleted = false;

    vi.spyOn(globalThis, "fetch").mockImplementation((input: string | URL | Request, init?: RequestInit) => {
      const url = resolveRequestUrl(input);
      const method = init?.method ?? (input instanceof Request ? input.method : "GET");

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

      if (url === "/api/tasks/TASK-OPEN/member-status?actor_id=2250001") {
        return Promise.resolve(jsonResponse({
          task_id: "TASK-OPEN",
          actor_id: "2250001",
          total_expense_amount_cents: 0,
          counts: {
            material_count: uploadCompleted ? 1 : 0,
            missing_material_count: 0,
            expense_detail_count: 0,
            recognition_pending_count: 0,
            recognition_succeeded_count: 0,
            recognition_failed_count: 0,
            recognition_needs_confirmation_count: 0,
            validation_passed_count: 0,
            validation_failed_count: 0,
            validation_pending_count: 0,
            validation_not_applicable_count: uploadCompleted ? 1 : 0,
            confirmed_expense_count: 0,
            pending_confirmation_count: 0,
            disputed_confirmation_count: 0,
            missing_confirmation_count: 0,
          },
          materials: uploadCompleted ? [
            {
              material_id: "MAT-UP-001",
              submitter_id: "2250001",
              material_type: "payment_record",
              original_filename: "pay.png",
              material_status: "assigned",
              recognition_status: null,
              recognition_failure_stage: null,
              recognition_failure_reason: null,
              invoice_id: null,
              invoice_number: null,
              validation_status: "not_applicable",
              validation_messages: [],
              created_at: "2026-04-28T14:00:00+08:00",
            },
          ] : [],
          missing_materials: [],
          expense_details: [],
        }));
      }

      if (url === "/api/tasks/TASK-OPEN/invoices") {
        return Promise.resolve(jsonResponse({ items: [] }));
      }

      if (url === "/api/materials/MAT-UP-001/recognition-tasks") {
        return Promise.resolve(jsonResponse({
          latest_effective: null,
          items: [],
        }));
      }

      if (url === "/api/tasks/TASK-OPEN/materials" && method === "POST") {
        uploadCompleted = true;
        return Promise.resolve(jsonResponse({
          status: "success",
          items: [
            {
              id: "MAT-UP-001",
              status: "assigned",
              task_id: "TASK-OPEN",
              submitter_id: "2250001",
              task_id_hint: null,
              submitter_id_hint: null,
              channel: "web",
              material_type: "payment_record",
              storage_key: "TASK-OPEN/pay.png",
              original_filename: "pay.png",
              content_type: "image/png",
              size_bytes: 128,
              sha256: "a".repeat(64),
              duplicate_of: null,
              claimed_by: null,
              claimed_at: null,
              created_at: "2026-04-28T14:00:00+08:00",
            },
          ],
          failures: [],
        }));
      }

      if (url.includes("/shared-invoices?actor_id=2250001")) {
        return Promise.resolve(jsonResponse({
          task_id: "TASK-OPEN",
          actor_id: "2250001",
          items: [],
        }));
      }

      throw new Error(`Unhandled fetch URL in member invoice workbench upload test: ${url}`);
    });

    renderWorkbenchRoute();

    expect(await screen.findByText("上传材料与附件")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("工作台上传材料类型"), {
      target: { value: "payment_record" },
    });
    fireEvent.change(screen.getByLabelText("工作台上传文件"), {
      target: {
        files: [new File(["payment"], "pay.png", { type: "image/png" })],
      },
    });
    fireEvent.click(screen.getByRole("button", { name: "上传到当前任务" }));

    expect(await screen.findByText("最近上传结果")).toBeInTheDocument();
    expect(screen.getByText("材料编号：MAT-UP-001")).toBeInTheDocument();
    expect(await screen.findByText("支付记录 / MAT-UP-001")).toBeInTheDocument();
  });

  it("blocks oversized files in the workbench upload area before sending the request", async () => {
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

      if (url === "/api/tasks/TASK-OPEN/member-status?actor_id=2250001") {
        return Promise.resolve(jsonResponse({
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
        }));
      }

      if (url === "/api/tasks/TASK-OPEN/invoices") {
        return Promise.resolve(jsonResponse({ items: [] }));
      }

      if (url.includes("/shared-invoices?actor_id=2250001")) {
        return Promise.resolve(jsonResponse({
          task_id: "TASK-OPEN",
          actor_id: "2250001",
          items: [],
        }));
      }

      throw new Error(`Unexpected fetch URL in workbench oversized upload test: ${url}`);
    });

    renderWorkbenchRoute();

    expect(await screen.findByText("上传材料与附件")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("工作台上传文件"), {
      target: {
        files: [
          new File([new Uint8Array(10 * 1024 * 1024 + 1)], "oversized.pdf", { type: "application/pdf" }),
        ],
      },
    });

    fireEvent.click(screen.getByRole("button", { name: "上传到当前任务" }));

    expect(await screen.findByText("文件 oversized.pdf 超过 10MB，请压缩或拆分后再上传。")).toBeInTheDocument();
    expect(fetchSpy).toHaveBeenCalledTimes(4);
  });

  it("submits confirmations directly from the workbench and refreshes current statuses", async () => {
    let confirmationStatus: "pending" | "confirmed" = "pending";

    vi.spyOn(globalThis, "fetch").mockImplementation((input: string | URL | Request, init?: RequestInit) => {
      const url = resolveRequestUrl(input);
      const method = init?.method ?? (input instanceof Request ? input.method : "GET");

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
            fee_categories: ["hotel"],
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

      if (url === "/api/tasks/TASK-OPEN/member-status?actor_id=2250001") {
        return Promise.resolve(jsonResponse({
          task_id: "TASK-OPEN",
          actor_id: "2250001",
          total_expense_amount_cents: 18800,
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
            confirmed_expense_count: confirmationStatus === "confirmed" ? 1 : 0,
            pending_confirmation_count: confirmationStatus === "pending" ? 1 : 0,
            disputed_confirmation_count: 0,
            missing_confirmation_count: 0,
          },
          materials: [
            {
              material_id: "MAT-CONF-001",
              submitter_id: "2250001",
              material_type: "invoice",
              original_filename: "hotel.pdf",
              material_status: "assigned",
              recognition_status: "succeeded",
              recognition_failure_stage: null,
              recognition_failure_reason: null,
              invoice_id: "INV-CONF-001",
              invoice_number: "HOTEL-188",
              validation_status: "passed",
              validation_messages: [],
              created_at: "2026-04-28T14:10:00+08:00",
            },
          ],
          missing_materials: [],
          expense_details: [
            {
              split_id: "SPLIT-CONF-001",
              split_version: 1,
              member_id: "2250001",
              amount_cents: 18800,
              note: "hotel shared",
              created_at: "2026-04-28T14:15:00+08:00",
              updated_at: "2026-04-28T14:15:00+08:00",
              invoice: {
                id: "INV-CONF-001",
                material_id: "MAT-CONF-001",
                invoice_number: "HOTEL-188",
                issue_date: "2026-04-25",
                transaction_time: "2026-04-25T09:00:00+08:00",
                buyer_name: "同济大学",
                seller_name: "锦江酒店",
                amount_cents: 18800,
                expense_type: "hotel",
                created_at: "2026-04-28T14:10:00+08:00",
                updated_at: "2026-04-28T14:15:00+08:00",
              },
              confirmation: {
                id: "CONF-CONF-001",
                member_id: "2250001",
                split_version: 1,
                status: confirmationStatus,
                dispute_reason: null,
                confirmed_at: "2026-04-28T14:16:00+08:00",
                updated_at: "2026-04-28T14:16:00+08:00",
              },
            },
          ],
        }));
      }

      if (url === "/api/tasks/TASK-OPEN/invoices") {
        return Promise.resolve(jsonResponse({
          items: [
            {
              id: "INV-CONF-001",
              task_id: "TASK-OPEN",
              material_id: "MAT-CONF-001",
              invoice_number: "HOTEL-188",
              issue_date: "2026-04-25",
              transaction_time: "2026-04-25T09:00:00+08:00",
              buyer_name: "同济大学",
              tax_number: "91310113666007253C",
              seller_name: "锦江酒店",
              amount_cents: 18800,
              expense_type: "hotel",
              created_at: "2026-04-28T14:10:00+08:00",
              updated_at: "2026-04-28T14:15:00+08:00",
            },
          ],
        }));
      }

      if (url === "/api/materials/MAT-CONF-001/recognition-tasks") {
        return Promise.resolve(jsonResponse({
          latest_effective: {
            id: "REC-CONF-001",
            material_id: "MAT-CONF-001",
            status: "succeeded",
            is_final_fact: false,
            failure: null,
            raw_response: {},
            recognized_fields: {
              invoice_number: {
                value: "HOTEL-188",
                source: "ai",
                confidence: 0.97,
                status: "recognized",
                updated_at: "2026-04-28T14:11:00+08:00",
              },
            },
            manual_corrections: [],
            created_at: "2026-04-28T14:11:00+08:00",
            updated_at: "2026-04-28T14:11:00+08:00",
          },
        }));
      }

      if (url === "/api/invoices/INV-CONF-001/validations") {
        return Promise.resolve(jsonResponse({ items: [] }));
      }

      if (url === "/api/invoices/INV-CONF-001/supporting-materials") {
        return Promise.resolve(jsonResponse({
          items: [
            {
              id: "MAT-CONF-PAY",
              status: "assigned",
              task_id: "TASK-OPEN",
              submitter_id: "2250001",
              task_id_hint: null,
              submitter_id_hint: null,
              channel: "web",
              material_type: "payment_record",
              storage_key: "TASK-OPEN/pay.png",
              original_filename: "pay.png",
              content_type: "image/png",
              size_bytes: 128,
              sha256: "b".repeat(64),
              duplicate_of: null,
              claimed_by: null,
              claimed_at: null,
              created_at: "2026-04-28T14:12:00+08:00",
            },
          ],
        }));
      }

      if (url === "/api/invoices/INV-CONF-001/splits") {
        return Promise.resolve(jsonResponse({
          items: [
            {
              id: "SPLIT-CONF-001",
              invoice_id: "INV-CONF-001",
              member_id: "2250001",
              amount_cents: 18800,
              note: "hotel shared",
              version: 1,
              is_active: true,
              created_at: "2026-04-28T14:15:00+08:00",
              updated_at: "2026-04-28T14:15:00+08:00",
            },
          ],
        }));
      }

      if (url === "/api/invoices/INV-CONF-001/confirmations") {
        return Promise.resolve(jsonResponse({
          items: [
            {
              id: "CONF-CONF-001",
              split_id: "SPLIT-CONF-001",
              member_id: "2250001",
              split_version: 1,
              split_amount_cents: 18800,
              split_note: "hotel shared",
              is_current: true,
              status: confirmationStatus,
              dispute_reason: null,
              confirmed_at: "2026-04-28T14:16:00+08:00",
              updated_at: "2026-04-28T14:16:00+08:00",
            },
          ],
        }));
      }

      if (url === "/api/splits/SPLIT-CONF-001/confirmation" && method === "PUT") {
        confirmationStatus = "confirmed";
        return Promise.resolve(jsonResponse({
          id: "CONF-CONF-001",
          split_id: "SPLIT-CONF-001",
          member_id: "2250001",
          split_version: 1,
          split_amount_cents: 18800,
          split_note: "hotel shared",
          is_current: true,
          status: "confirmed",
          dispute_reason: null,
          confirmed_at: "2026-04-28T14:16:30+08:00",
          updated_at: "2026-04-28T14:16:30+08:00",
        }));
      }

      if (url.includes("/shared-invoices?actor_id=2250001")) {
        return Promise.resolve(jsonResponse({
          task_id: "TASK-OPEN",
          actor_id: "2250001",
          items: [],
        }));
      }

      throw new Error(`Unhandled fetch URL in member invoice workbench confirmation test: ${url}`);
    });

    renderWorkbenchRoute();

    fireEvent.click(await screen.findByRole("tab", { name: "费用确认" }));
    expect(await screen.findByText("确认当前分到本人名下的费用")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "确认这笔费用" }));

    expect(await screen.findByText("已提交确认，工作台已刷新最新确认状态。")).toBeInTheDocument();
    expect(await screen.findByText("待确认 0 条")).toBeInTheDocument();
  });

  it("lets the member manually fill invoice fields from the current workbench path", async () => {
    let currentInvoice: Record<string, unknown> | null = null;
    let currentValidations: Array<Record<string, unknown>> = [];
    let currentRecognition: RecognitionTaskRecord = {
      id: "REC-MANUAL-001",
      material_id: "MAT-MANUAL-001",
      status: "needs_confirmation",
      is_final_fact: false,
      failure: null,
      raw_response: {},
      recognized_fields: {
        invoice_number: {
          value: "AI-001",
          source: "ai",
          confidence: 0.42,
          status: "needs_confirmation",
          updated_at: "2026-04-28T09:01:00+08:00",
        },
        buyer_name: {
          value: "同济大学",
          source: "ai",
          confidence: 0.9,
          status: "recognized",
          updated_at: "2026-04-28T09:01:00+08:00",
        },
        tax_number: {
          value: "91310113666007253C",
          source: "ai",
          confidence: 0.91,
          status: "recognized",
          updated_at: "2026-04-28T09:01:00+08:00",
        },
        amount_cents: {
          value: 4567,
          source: "ai",
          confidence: 0.88,
          status: "recognized",
          updated_at: "2026-04-28T09:01:00+08:00",
        },
        expense_type: {
          value: "railway",
          source: "ai",
          confidence: 0.95,
          status: "recognized",
          updated_at: "2026-04-28T09:01:00+08:00",
        },
      },
      manual_corrections: [],
      created_at: "2026-04-28T09:00:00+08:00",
      updated_at: "2026-04-28T09:01:00+08:00",
    };
    let receivedPayload: Record<string, unknown> | null = null;

    vi.spyOn(globalThis, "fetch").mockImplementation((input: string | URL | Request, init?: RequestInit) => {
      const url = resolveRequestUrl(input);
      const method = init?.method ?? (input instanceof Request ? input.method : "GET");

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

      if (url === "/api/tasks/TASK-OPEN/member-status?actor_id=2250001") {
        return Promise.resolve(jsonResponse({
          task_id: "TASK-OPEN",
          actor_id: "2250001",
          total_expense_amount_cents: currentInvoice ? 4567 : 0,
          counts: {
            material_count: 1,
            missing_material_count: 0,
            expense_detail_count: 0,
            recognition_pending_count: 0,
            recognition_succeeded_count: 0,
            recognition_failed_count: 0,
            recognition_needs_confirmation_count: 1,
            validation_passed_count: 0,
            validation_failed_count: 0,
            validation_pending_count: currentValidations.length,
            validation_not_applicable_count: currentInvoice ? 0 : 1,
            confirmed_expense_count: 0,
            pending_confirmation_count: 0,
            disputed_confirmation_count: 0,
            missing_confirmation_count: 0,
          },
          materials: [
            {
              material_id: "MAT-MANUAL-001",
              submitter_id: "2250001",
              material_type: "invoice",
              original_filename: "manual.pdf",
              material_status: "assigned",
              recognition_status: "needs_confirmation",
              recognition_failure_stage: null,
              recognition_failure_reason: null,
              invoice_id: currentInvoice?.id ?? null,
              invoice_number: currentInvoice?.invoice_number ?? null,
              validation_status: currentInvoice ? "pending" : "not_applicable",
              validation_messages: currentValidations.map((item) => (
                typeof item.message === "string" ? item.message : ""
              )),
              created_at: "2026-04-28T09:00:00+08:00",
            },
          ],
          missing_materials: [],
          expense_details: [],
        }));
      }

      if (url === "/api/tasks/TASK-OPEN/invoices") {
        return Promise.resolve(jsonResponse({
          items: currentInvoice ? [currentInvoice] : [],
        }));
      }

      if (url === "/api/materials/MAT-MANUAL-001/recognition-tasks") {
        return Promise.resolve(jsonResponse({
          latest_effective: currentRecognition,
          items: [],
        }));
      }

      if (url === "/api/materials/MAT-MANUAL-001/invoice" && method === "POST") {
        if (typeof init?.body !== "string") {
          throw new Error("expected invoice payload to be serialized JSON");
        }
        receivedPayload = JSON.parse(init.body) as Record<string, unknown>;
        currentInvoice = {
          id: "INV-MANUAL-001",
          task_id: "TASK-OPEN",
          material_id: "MAT-MANUAL-001",
          invoice_number: receivedPayload.invoice_number,
          issue_date: receivedPayload.issue_date,
          transaction_time: receivedPayload.transaction_time,
          buyer_name: receivedPayload.buyer_name,
          tax_number: receivedPayload.tax_number,
          seller_name: receivedPayload.seller_name,
          amount_cents: receivedPayload.amount_cents,
          expense_type: receivedPayload.expense_type,
          created_at: "2026-04-28T09:02:00+08:00",
          updated_at: "2026-04-28T09:03:00+08:00",
        };
        currentValidations = [
          {
            id: "VAL-MANUAL-001",
            rule_code: "invoice_transaction_time_range",
            target_type: "invoice",
            target_id: "INV-MANUAL-001",
            severity: "warning",
            status: "pending",
            message: "交易时间需要管理员确认。",
            evidence: {},
            created_at: "2026-04-28T09:04:00+08:00",
          },
        ];
        currentRecognition = {
          ...currentRecognition,
          manual_corrections: [
            {
              id: "CORR-MANUAL-001",
              field_name: "invoice_number",
              actor_id: "2250001",
              before: currentRecognition.recognized_fields.invoice_number ?? null,
              after: {
                value: receivedPayload.invoice_number,
                source: "manual",
                confidence: 1,
                status: "recognized",
                updated_at: "2026-04-28T09:03:00+08:00",
              },
              revalidation_status: "triggered",
              corrected_at: "2026-04-28T09:03:00+08:00",
            },
          ],
        };
        return Promise.resolve(jsonResponse({
          invoice: currentInvoice,
          validations: currentValidations,
        }, { status: 201 }));
      }

      if (url === "/api/invoices/INV-MANUAL-001/validations") {
        return Promise.resolve(jsonResponse({ items: currentValidations }));
      }

      if (url === "/api/invoices/INV-MANUAL-001/supporting-materials") {
        return Promise.resolve(jsonResponse({ items: [] }));
      }

      if (url === "/api/invoices/INV-MANUAL-001/splits") {
        return Promise.resolve(jsonResponse({ items: [] }));
      }

      if (url === "/api/invoices/INV-MANUAL-001/confirmations") {
        return Promise.resolve(jsonResponse({ items: [] }));
      }

      if (url.includes("/shared-invoices?actor_id=2250001")) {
        return Promise.resolve(jsonResponse({
          task_id: "TASK-OPEN",
          actor_id: "2250001",
          items: [],
        }));
      }

      throw new Error(`Unhandled fetch URL in member invoice workbench manual entry test: ${url}`);
    });

    renderWorkbenchRoute();

    expect(await screen.findByRole("heading", { name: "manual.pdf" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "手动填写或更正发票" }));

    const form = await screen.findByRole("form", { name: "MAT-MANUAL-001 发票手动补录表单" });
    expect(within(form).getByLabelText("MAT-MANUAL-001 发票号码")).toHaveValue("AI-001");
    expect(within(form).getByLabelText("MAT-MANUAL-001 金额")).toHaveValue("45.67");

    fireEvent.change(within(form).getByLabelText("MAT-MANUAL-001 发票号码"), {
      target: { value: "MANUAL-001" },
    });
    fireEvent.click(within(form).getByRole("button", { name: "保存发票字段" }));

    expect(receivedPayload).toMatchObject({
      actor_id: "2250001",
      invoice_number: "MANUAL-001",
      buyer_name: "同济大学",
      tax_number: "91310113666007253C",
      amount_cents: 4567,
      expense_type: "railway",
    });
    expect(await screen.findByRole("heading", { name: "MANUAL-001" })).toBeInTheDocument();
    expect(
      await screen.findByText("已保存发票 MANUAL-001；当前共有 1 条校验结果，其中失败 0 条、待确认 1 条。"),
    ).toBeInTheDocument();
    expect(screen.queryByRole("form", { name: "MAT-MANUAL-001 发票手动补录表单" })).not.toBeInTheDocument();
  });

  it("shows retrying feedback when the member re-runs recognition", async () => {
    const latestRecognition: Record<string, unknown> = {
      id: "REC-RETRY-BASE",
      material_id: "MAT-RETRY-001",
      status: "failed",
      is_final_fact: false,
      failure: {
        stage: "ai",
        reason: "initial extraction failed",
      },
      raw_response: {},
      recognized_fields: {},
      manual_corrections: [],
      created_at: "2026-04-28T10:00:00+08:00",
      updated_at: "2026-04-28T10:01:00+08:00",
    };
    let resolveExecute: ((value: Response) => void) | null = null;

    vi.spyOn(globalThis, "fetch").mockImplementation((input: string | URL | Request, init?: RequestInit) => {
      const url = resolveRequestUrl(input);
      const method = init?.method ?? (input instanceof Request ? input.method : "GET");

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

      if (url === "/api/tasks/TASK-OPEN/member-status?actor_id=2250001") {
        return Promise.resolve(jsonResponse({
          task_id: "TASK-OPEN",
          actor_id: "2250001",
          total_expense_amount_cents: 0,
          counts: {
            material_count: 1,
            missing_material_count: 0,
            expense_detail_count: 0,
            recognition_pending_count: 0,
            recognition_succeeded_count: 0,
            recognition_failed_count: 1,
            recognition_needs_confirmation_count: 0,
            validation_passed_count: 0,
            validation_failed_count: 0,
            validation_pending_count: 0,
            validation_not_applicable_count: 1,
            confirmed_expense_count: 0,
            pending_confirmation_count: 0,
            disputed_confirmation_count: 0,
            missing_confirmation_count: 0,
          },
          materials: [
            {
              material_id: "MAT-RETRY-001",
              submitter_id: "2250001",
              material_type: "payment_record",
              original_filename: "retry.png",
              material_status: "assigned",
              recognition_status: "failed",
              recognition_failure_stage: "ai",
              recognition_failure_reason: "initial extraction failed",
              invoice_id: null,
              invoice_number: null,
              validation_status: "not_applicable",
              validation_messages: [],
              created_at: "2026-04-28T10:00:00+08:00",
            },
          ],
          missing_materials: [],
          expense_details: [],
        }));
      }

      if (url === "/api/tasks/TASK-OPEN/invoices") {
        return Promise.resolve(jsonResponse({ items: [] }));
      }

      if (url === "/api/materials/MAT-RETRY-001/recognition-tasks") {
        return Promise.resolve(jsonResponse({
          latest_effective: latestRecognition,
          items: [],
        }));
      }

      if (url === "/api/materials/MAT-RETRY-001/recognition-tasks" && method === "POST") {
        return Promise.resolve(jsonResponse({
          item: {
            id: "REC-RETRY-1",
            material_id: "MAT-RETRY-001",
            status: "pending",
            is_final_fact: false,
            failure: null,
            raw_response: null,
            recognized_fields: {},
            manual_corrections: [],
            created_at: "2026-04-28T10:02:00+08:00",
            updated_at: "2026-04-28T10:02:00+08:00",
          },
        }, { status: 201 }));
      }

      if (url === "/api/recognition-tasks/REC-RETRY-1/execute" && method === "POST") {
        return new Promise((resolve) => {
          resolveExecute = resolve;
        });
      }

      if (url.includes("/shared-invoices?actor_id=2250001")) {
        return Promise.resolve(jsonResponse({
          task_id: "TASK-OPEN",
          actor_id: "2250001",
          items: [],
        }));
      }

      throw new Error(`Unhandled fetch URL in member invoice workbench retry feedback test: ${url}`);
    });

    renderWorkbenchRoute();

    const firstRetryButton = await screen.findByRole("button", { name: "运行重新识别" });
    fireEvent.click(firstRetryButton);
    expect(await screen.findByRole("button", { name: "重新识别中..." })).toBeInTheDocument();

    act(() => {
      resolveExecute?.(jsonResponse({
        item: {
          id: "REC-RETRY-1",
          material_id: "MAT-RETRY-001",
          status: "pending",
          is_final_fact: false,
          failure: null,
          raw_response: null,
          recognized_fields: {},
          manual_corrections: [],
          created_at: "2026-04-28T10:02:00+08:00",
          updated_at: "2026-04-28T10:02:00+08:00",
        },
      }));
    });

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "运行重新识别" })).toBeInTheDocument();
    });
  });

  it("shows shared invoice summaries for other task members without exposing raw attachment details", async () => {
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

      if (url === "/api/tasks/TASK-OPEN/member-status?actor_id=2250001") {
        return Promise.resolve(jsonResponse({
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
        }));
      }

      if (url === "/api/tasks/TASK-OPEN/shared-invoices?actor_id=2250001") {
        return Promise.resolve(jsonResponse({
          task_id: "TASK-OPEN",
          actor_id: "2250001",
          items: [
            {
              invoice_id: "INV-TEAM-001",
              invoice_number: "TEAM-001",
              issue_date: "2026-04-26",
              buyer_name: "同济大学",
              seller_name: "12306",
              amount_cents: 20000,
              expense_type: "railway",
              submitter_id: "2250002",
              supporting_materials: [
                { material_type: "payment_record", count: 1 },
                { material_type: "order_screenshot", count: 1 },
              ],
              splits: [
                { member_id: "2250001", amount_cents: 12000 },
                { member_id: "2250002", amount_cents: 8000 },
              ],
              created_at: "2026-04-28T13:00:00+08:00",
              updated_at: "2026-04-28T13:05:00+08:00",
            },
          ],
        }));
      }

      if (url === "/api/tasks/TASK-OPEN/invoices") {
        return Promise.resolve(jsonResponse({ items: [] }));
      }

      throw new Error(`Unhandled fetch URL in member invoice workbench shared summary test: ${url}`);
    });

    renderWorkbenchRoute();

    expect(await screen.findByText("任务内其他成员已上传发票")).toBeInTheDocument();
    expect(screen.getByText("TEAM-001")).toBeInTheDocument();
    expect(
      screen.getByText("这里仅共享发票基础元数据、当前分摊去向和必要附件摘要；不提供原始文件下载、支付截图全文或识别原始响应。"),
    ).toBeInTheDocument();
    expect(screen.getByText("支付记录 1 份 / 订单截图 1 份")).toBeInTheDocument();

    const sharedCard = screen.getByRole("heading", { name: "TEAM-001" }).closest("article");
    expect(sharedCard).not.toBeNull();
    expect(within(sharedCard as HTMLElement).getAllByText("成员 2250002")).toHaveLength(2);
    expect(within(sharedCard as HTMLElement).getByText("￥120.00")).toBeInTheDocument();
    expect(within(sharedCard as HTMLElement).getByText("￥80.00")).toBeInTheDocument();
    expect(within(sharedCard as HTMLElement).queryByText("member-two-order.png")).not.toBeInTheDocument();
    expect(within(sharedCard as HTMLElement).queryByRole("button", { name: "运行重新识别" })).not.toBeInTheDocument();
    expect(within(sharedCard as HTMLElement).queryByRole("button", { name: "手动填写或更正发票" })).not.toBeInTheDocument();
    expect(within(sharedCard as HTMLElement).queryByRole("button", { name: "保存发票字段" })).not.toBeInTheDocument();
  });
});
