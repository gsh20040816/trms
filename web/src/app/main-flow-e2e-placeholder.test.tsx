import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
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

function buildEmptySupportingMaterialLinkageResponse(url: string) {
  const matched = url.match(/^\/api\/tasks\/([^/]+)\/supporting-material-linkage(?:\?actor_id=([^&]+))?$/);
  if (!matched) {
    return null;
  }
  return {
    task_id: decodeURIComponent(matched[1] ?? ""),
    actor_id: matched[2] ?? "2250001",
    items: [],
  };
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

function renderRoute(entry: string) {
  const router = createMemoryRouter(routes, {
    initialEntries: [entry],
  });

  return render(<RouterProvider router={router} />);
}

async function addMember(keyword: string, optionLabel: string) {
  const input = screen.getByLabelText("成员名单搜索");
  fireEvent.change(input, {
    target: { value: keyword },
  });
  fireEvent.click(await screen.findByRole("button", { name: optionLabel }));
}

async function fillRequiredTaskForm() {
  fireEvent.change(screen.getByLabelText("比赛名称"), {
    target: { value: "E2E 主流程任务" },
  });
  fireEvent.change(screen.getByLabelText("比赛地点"), {
    target: { value: "上海" },
  });
  fireEvent.change(screen.getByLabelText("比赛开始日期"), {
    target: { value: "2026-11-01" },
  });
  fireEvent.change(screen.getByLabelText("比赛结束日期"), {
    target: { value: "2026-11-03" },
  });
  fireEvent.change(screen.getByLabelText("提交截止时间"), {
    target: { value: "2026-11-10T18:00" },
  });
  await addMember("2250", "张三 / member1 / 2250001");
  fireEvent.change(screen.getByLabelText("发票抬头"), {
    target: { value: "同济大学" },
  });
  fireEvent.change(screen.getByLabelText("税号"), {
    target: { value: "91310000TEST00001" },
  });
}

function buildTask(status: "draft" | "open" | "ready_to_export") {
  return {
    id: "TASK-E2E",
    status,
    competition_name: "E2E 主流程任务",
    competition_location: "上海",
    competition_start_date: "2026-11-01",
    competition_end_date: "2026-11-03",
    deadline: "2026-11-10T10:00:00.000Z",
    member_ids: ["2250001"],
    fee_categories: ["railway"],
    administrator_id: "admin-1",
    project_info: "",
    reimburser_info: "",
    invoice_title: "同济大学",
    tax_number: "91310000TEST00001",
    created_at: "2026-04-28T12:00:00+08:00",
    updated_at: "2026-04-28T12:00:00+08:00",
  };
}

function buildMaterial() {
  return {
    id: "MAT-001",
    status: "assigned",
    task_id: "TASK-E2E",
    submitter_id: "2250001",
    task_id_hint: null,
    submitter_id_hint: null,
    channel: "web",
    material_type: "invoice",
    storage_key: "TASK-E2E/MAT-001-ticket.pdf",
    original_filename: "ticket.pdf",
    content_type: "application/pdf",
    size_bytes: 12,
    sha256: "a".repeat(64),
    duplicate_of: null,
    claimed_by: null,
    claimed_at: null,
    created_at: "2026-04-28T12:05:00+08:00",
  };
}

function buildInvoice() {
  return {
    id: "INV-001",
    task_id: "TASK-E2E",
    material_id: "MAT-001",
    invoice_number: "INV-E2E-001",
    issue_date: "2026-10-28",
    transaction_time: "2026-10-28T09:30:00+08:00",
    buyer_name: "同济大学",
    tax_number: "91310000TEST00001",
    seller_name: "中国铁路",
    amount_cents: 12345,
    expense_type: "railway",
    member_submission_status: "unsubmitted",
    submitted_by_member_id: null,
    submitted_at: null,
    created_at: "2026-04-28T12:10:00+08:00",
    updated_at: "2026-04-28T12:10:00+08:00",
  };
}

function buildValidation(ruleCode: string, message: string) {
  return {
    id: `VAL-${ruleCode}`,
    rule_code: ruleCode,
    target_type: "invoice",
    target_id: "INV-001",
    severity: "blocker",
    status: "passed",
    message,
    evidence: {},
    created_at: "2026-04-28T12:10:00+08:00",
  };
}

function buildMemberWorkbenchSummary(state: {
  materialUploaded: boolean;
  invoiceSaved: boolean;
  splitSaved: boolean;
  confirmed: boolean;
}) {
  const material = state.materialUploaded ? buildMaterial() : null;
  const invoice = state.invoiceSaved ? buildInvoice() : null;
  const split = state.splitSaved
    ? {
        id: "SPLIT-001",
        invoice_id: "INV-001",
        member_id: "2250001",
        amount_cents: 12345,
        note: "self paid",
        version: 1,
        is_active: true,
        created_at: "2026-04-28T12:15:00+08:00",
        updated_at: "2026-04-28T12:15:00+08:00",
      }
    : null;
  const confirmation = state.confirmed
    ? {
        id: "CONF-001",
        split_id: "SPLIT-001",
        member_id: "2250001",
        split_version: 1,
        split_amount_cents: 12345,
        split_note: "self paid",
        is_current: true,
        status: "confirmed",
        dispute_reason: null,
        confirmed_at: "2026-04-28T12:20:00+08:00",
        updated_at: "2026-04-28T12:20:00+08:00",
      }
    : null;
  const materialStatus = material
    ? {
        material_id: material.id,
        submitter_id: "2250001",
        material_type: "invoice",
        original_filename: "ticket.pdf",
        material_status: "assigned",
        recognition_status: invoice ? "succeeded" : "needs_confirmation",
        recognition_failure_stage: null,
        recognition_failure_reason: null,
        invoice_id: invoice?.id ?? null,
        invoice_number: invoice?.invoice_number ?? null,
        validation_status: invoice ? "passed" : "pending",
        validation_messages: [],
        created_at: "2026-04-28T12:05:00+08:00",
      }
    : null;
  const expenseDetail = split && invoice
    ? {
        split_id: "SPLIT-001",
        split_version: 1,
        member_id: "2250001",
        amount_cents: 12345,
        note: "self paid",
        created_at: "2026-04-28T12:15:00+08:00",
        updated_at: "2026-04-28T12:15:00+08:00",
        invoice,
        confirmation: confirmation
          ? {
              id: "CONF-001",
              member_id: "2250001",
              split_version: 1,
              status: "confirmed",
              dispute_reason: null,
              confirmed_at: "2026-04-28T12:20:00+08:00",
              updated_at: "2026-04-28T12:20:00+08:00",
            }
          : null,
      }
    : null;

  return {
    task_id: "TASK-E2E",
    actor_id: "2250001",
    report: {
      task_id: "TASK-E2E",
      actor_id: "2250001",
      total_expense_amount_cents: state.splitSaved ? 12345 : 0,
      counts: {
        material_count: material ? 1 : 0,
        missing_material_count: 0,
        expense_detail_count: expenseDetail ? 1 : 0,
        recognition_pending_count: 0,
        recognition_succeeded_count: invoice ? 1 : 0,
        recognition_failed_count: 0,
        recognition_needs_confirmation_count: material && !invoice ? 1 : 0,
        validation_passed_count: invoice ? 2 : 0,
        validation_failed_count: 0,
        validation_pending_count: 0,
        validation_not_applicable_count: 0,
        confirmed_expense_count: state.confirmed ? 1 : 0,
        pending_confirmation_count: state.splitSaved && !state.confirmed ? 1 : 0,
        disputed_confirmation_count: 0,
        missing_confirmation_count: 0,
      },
      materials: materialStatus ? [materialStatus] : [],
      missing_materials: [],
      expense_details: expenseDetail ? [expenseDetail] : [],
    },
    items: materialStatus
      ? [
          {
            material: materialStatus,
            invoice,
            recognition: {
              id: "REC-001",
              material_id: "MAT-001",
              status: invoice ? "succeeded" : "needs_confirmation",
              failure: null,
              recognized_fields: {
                invoice_number: { value: "INV-E2E-001", source: "ai", confidence: 0.95, status: "recognized", updated_at: "2026-04-28T12:06:00+08:00" },
                buyer_name: { value: invoice ? "同济大学" : "Tongji ACM Lab", source: invoice ? "manual" : "ocr", confidence: invoice ? 1 : 0.41, status: invoice ? "recognized" : "needs_confirmation", updated_at: "2026-04-28T12:06:30+08:00" },
                tax_number: { value: invoice ? "91310000TEST00001" : "WRONG-TAX", source: invoice ? "manual" : "ocr", confidence: invoice ? 1 : 0.32, status: invoice ? "recognized" : "needs_confirmation", updated_at: "2026-04-28T12:07:00+08:00" },
                amount_cents: { value: 12345, source: "ai", confidence: 0.97, status: "recognized", updated_at: "2026-04-28T12:07:30+08:00" },
                transaction_time: { value: "2026-10-28T09:30:00+08:00", source: "pdf_text", confidence: 0.88, status: "recognized", updated_at: "2026-04-28T12:08:00+08:00" },
                expense_type: { value: "railway", source: "ai", confidence: 0.93, status: "recognized", updated_at: "2026-04-28T12:08:30+08:00" },
              },
              manual_corrections: [],
              created_at: "2026-04-28T12:05:30+08:00",
              updated_at: "2026-04-28T12:10:00+08:00",
            },
            validations: invoice
              ? [
                  buildValidation("invoice_title_match", "发票抬头匹配"),
                  buildValidation("invoice_tax_number_match", "税号匹配"),
                ]
              : [],
            supporting_materials: [],
            splits: split ? [split] : [],
            confirmations: confirmation ? [confirmation] : [],
            related_expense_details: expenseDetail ? [expenseDetail] : [],
            missing_materials: [],
            queue_group: !invoice ? "recognition_review" : state.splitSaved && !state.confirmed ? "confirmation_incomplete" : "ready",
            blocking_reasons: !invoice ? ["recognition_review"] : state.splitSaved && !state.confirmed ? ["confirmation_incomplete"] : [],
            ready_for_submission: Boolean(invoice && (!state.splitSaved || state.confirmed)),
          },
        ]
      : [],
    pending_supporting_material_linkage_items: [],
    shared_invoices: [],
  };
}

function buildReviewSummary(state: {
  materialUploaded: boolean;
  invoiceSaved: boolean;
  splitSaved: boolean;
  confirmed: boolean;
}) {
  const material = state.materialUploaded ? buildMaterial() : null;
  const invoice = state.invoiceSaved ? buildInvoice() : null;
  const validations = invoice
    ? [
        buildValidation("invoice_title_match", "发票抬头匹配"),
        buildValidation("invoice_tax_number_match", "税号匹配"),
      ]
    : [];
  const split = state.splitSaved
    ? {
        split: {
          id: "SPLIT-001",
          invoice_id: "INV-001",
          member_id: "2250001",
          amount_cents: 12345,
          note: "self paid",
          version: 1,
          is_active: true,
          created_at: "2026-04-28T12:15:00+08:00",
          updated_at: "2026-04-28T12:15:00+08:00",
        },
        confirmation: state.confirmed
          ? {
              id: "CONF-001",
              split_id: "SPLIT-001",
              member_id: "2250001",
              split_version: 1,
              split_amount_cents: 12345,
              split_note: "self paid",
              is_current: true,
              status: "confirmed",
              dispute_reason: null,
              confirmed_at: "2026-04-28T12:20:00+08:00",
              updated_at: "2026-04-28T12:20:00+08:00",
            }
          : null,
      }
    : null;

  return {
    task_id: "TASK-E2E",
    administrator_id: "admin-1",
    counts: {
      material_count: material ? 1 : 0,
      pending_assignment_material_count: 0,
      invoice_count: invoice ? 1 : 0,
      validation_count: validations.length,
      blocker_failed_validation_count: 0,
      split_count: split ? 1 : 0,
      confirmed_split_count: state.confirmed ? 1 : 0,
      pending_confirmation_count: split && !state.confirmed ? 1 : 0,
      disputed_confirmation_count: 0,
      missing_confirmation_count: 0,
      pending_recognition_count: material && !invoice ? 1 : 0,
      failed_recognition_count: 0,
      needs_confirmation_recognition_count: material && !invoice ? 1 : 0,
    },
    materials: material
      ? [
          {
            material,
            latest_recognition: {
              id: "REC-001",
              material_id: "MAT-001",
              status: invoice ? "succeeded" : "needs_confirmation",
              is_final_fact: false,
              failure: null,
              raw_response: { provider: "placeholder-ai" },
              recognized_fields: {
                invoice_number: {
                  value: "INV-E2E-001",
                  source: "ai",
                  confidence: 0.95,
                  status: "recognized",
                  updated_at: "2026-04-28T12:06:00+08:00",
                },
                buyer_name: {
                  value: invoice ? "同济大学" : "Tongji ACM Lab",
                  source: invoice ? "manual" : "ocr",
                  confidence: invoice ? 1 : 0.41,
                  status: invoice ? "recognized" : "needs_confirmation",
                  updated_at: "2026-04-28T12:06:30+08:00",
                },
                tax_number: {
                  value: invoice ? "91310000TEST00001" : "WRONG-TAX",
                  source: invoice ? "manual" : "ocr",
                  confidence: invoice ? 1 : 0.32,
                  status: invoice ? "recognized" : "needs_confirmation",
                  updated_at: "2026-04-28T12:07:00+08:00",
                },
                amount_cents: {
                  value: 12345,
                  source: "ai",
                  confidence: 0.97,
                  status: "recognized",
                  updated_at: "2026-04-28T12:07:30+08:00",
                },
                transaction_time: {
                  value: "2026-10-28T09:30:00+08:00",
                  source: "pdf_text",
                  confidence: 0.88,
                  status: "recognized",
                  updated_at: "2026-04-28T12:08:00+08:00",
                },
                expense_type: {
                  value: "railway",
                  source: "ai",
                  confidence: 0.93,
                  status: "recognized",
                  updated_at: "2026-04-28T12:08:30+08:00",
                },
              },
              manual_corrections: invoice
                ? [
                    {
                      id: "CORR-001",
                      field_name: "buyer_name",
                      actor_id: "admin-1",
                      before: {
                        value: "Tongji ACM Lab",
                        source: "ocr",
                        confidence: 0.41,
                        status: "needs_confirmation",
                        updated_at: "2026-04-28T12:06:30+08:00",
                      },
                      after: {
                        value: "同济大学",
                        source: "manual",
                        confidence: 1,
                        status: "recognized",
                        updated_at: "2026-04-28T12:10:00+08:00",
                      },
                      revalidation_status: "triggered",
                      corrected_at: "2026-04-28T12:10:00+08:00",
                    },
                  ]
                : [],
              created_at: "2026-04-28T12:05:30+08:00",
              updated_at: "2026-04-28T12:10:00+08:00",
            },
            invoice_id: invoice ? invoice.id : null,
            supporting_invoice_ids: [],
          },
        ]
      : [],
    pending_assignment_materials: [],
    invoices: invoice
      ? [
          {
            invoice,
            supporting_material_ids: [],
            validations,
            splits: split ? [split] : [],
          },
        ]
      : [],
  };
}

describe("frontend main flow e2e placeholder", () => {
  beforeEach(() => {
    clearMockSession();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    clearMockSession();
    cleanup();
  });

  it(
    "covers the stage-one main flow with memory router and mock api boundaries",
    async () => {
      const workflowState = {
        taskCreated: false,
        taskStatus: "draft" as "draft" | "open" | "ready_to_export",
        materialUploaded: false,
        invoiceSaved: false,
      splitSaved: false,
      confirmed: false,
    };

    vi.spyOn(globalThis, "fetch").mockImplementation((input: string | URL | Request, init?: RequestInit) => {
      const url = resolveRequestUrl(input);
      const emptySupportingMaterialLinkageResponse = buildEmptySupportingMaterialLinkageResponse(url);
      if (emptySupportingMaterialLinkageResponse) {
        return Promise.resolve(jsonResponse(emptySupportingMaterialLinkageResponse));
      }

      if (url === "/api/tasks" && init?.method === "POST") {
        const body = parseRequestJsonBody(init);
        expect(body.member_ids).toEqual(["member-actor-1"]);
        workflowState.taskCreated = true;
        workflowState.taskStatus = "draft";
        return Promise.resolve(jsonResponse(buildTask("draft"), { status: 201 }));
      }

      if (url === "/api/tasks/search/member-candidates?keyword=2250&limit=10") {
        return Promise.resolve(jsonResponse({
          items: [
            {
              actor_id: "member-actor-1",
              username: "member1",
              display_name: "张三",
              student_id: "2250001",
            },
          ],
        }));
      }

      if (url === "/api/tasks") {
        return Promise.resolve(jsonResponse(workflowState.taskCreated ? [buildTask(workflowState.taskStatus)] : []));
      }

      if (url === "/api/tasks/TASK-E2E") {
        return Promise.resolve(jsonResponse(buildTask(workflowState.taskStatus)));
      }

      if (url === "/api/tasks/TASK-E2E/readiness?actor_id=admin-1") {
        return Promise.resolve(jsonResponse({
          task_id: "TASK-E2E",
          administrator_id: "admin-1",
          ready_for_export: false,
          counts: {
            pending_recognition_count: workflowState.materialUploaded && !workflowState.invoiceSaved ? 1 : 0,
            failed_recognition_count: 0,
            needs_confirmation_recognition_count: workflowState.materialUploaded && !workflowState.invoiceSaved ? 1 : 0,
            pending_supporting_material_linkage_count: 0,
            missing_material_count: 0,
            blocker_validation_count: 0,
            split_incomplete_count: workflowState.invoiceSaved && !workflowState.splitSaved ? 1 : 0,
            pending_confirmation_count: workflowState.splitSaved && !workflowState.confirmed ? 1 : 0,
            disputed_confirmation_count: 0,
            export_blocking_reason_count: workflowState.taskStatus === "ready_to_export" ? 0 : 1,
          },
          issues: workflowState.taskStatus === "ready_to_export"
            ? []
            : [
                {
                  kind: "export_blocker",
                  label: "导出阻塞原因",
                  count: 1,
                  blocking: true,
                  invoice_ids: [],
                  material_ids: [],
                  split_ids: [],
                  details: ["task must be ready_to_export or completed before real exports can be generated"],
                },
              ],
          export_blocking_reasons: workflowState.taskStatus === "ready_to_export"
            ? []
            : ["task must be ready_to_export or completed before real exports can be generated"],
        }));
      }

      if (url === "/api/tasks/TASK-E2E/member-status?actor_id=2250001") {
        return Promise.resolve(jsonResponse({
          task_id: "TASK-E2E",
          actor_id: "2250001",
          total_expense_amount_cents: workflowState.splitSaved ? 12345 : 0,
          counts: {
            material_count: workflowState.materialUploaded ? 1 : 0,
            missing_material_count: 0,
            expense_detail_count: workflowState.splitSaved ? 1 : 0,
            recognition_pending_count: 0,
            recognition_succeeded_count: workflowState.invoiceSaved ? 1 : 0,
            recognition_failed_count: 0,
            recognition_needs_confirmation_count: workflowState.materialUploaded && !workflowState.invoiceSaved ? 1 : 0,
            validation_passed_count: workflowState.invoiceSaved ? 2 : 0,
            validation_failed_count: 0,
            validation_pending_count: 0,
            validation_not_applicable_count: 0,
            confirmed_expense_count: workflowState.confirmed ? 1 : 0,
            pending_confirmation_count: workflowState.splitSaved && !workflowState.confirmed ? 1 : 0,
            disputed_confirmation_count: 0,
            missing_confirmation_count: 0,
          },
          materials: workflowState.materialUploaded ? [
            {
              material_id: "MAT-001",
              submitter_id: "2250001",
              material_type: "invoice",
              original_filename: "ticket.pdf",
              material_status: "assigned",
              recognition_status: workflowState.invoiceSaved ? "succeeded" : "needs_confirmation",
              recognition_failure_stage: null,
              recognition_failure_reason: null,
              invoice_id: workflowState.invoiceSaved ? "INV-001" : null,
              invoice_number: workflowState.invoiceSaved ? "INV-E2E-001" : null,
              validation_status: workflowState.invoiceSaved ? "passed" : "pending",
              validation_messages: [],
              created_at: "2026-04-28T12:05:00+08:00",
            },
          ] : [],
          missing_materials: [],
          expense_details: workflowState.splitSaved ? [
            {
              split_id: "SPLIT-001",
              split_version: 1,
              member_id: "2250001",
              amount_cents: 12345,
              note: "self paid",
              created_at: "2026-04-28T12:15:00+08:00",
              updated_at: "2026-04-28T12:15:00+08:00",
              invoice: buildInvoice(),
              confirmation: workflowState.confirmed
                ? {
                    id: "CONF-001",
                    member_id: "2250001",
                    split_version: 1,
                    status: "confirmed",
                    dispute_reason: null,
                    confirmed_at: "2026-04-28T12:20:00+08:00",
                    updated_at: "2026-04-28T12:20:00+08:00",
                  }
                : null,
            },
          ] : [],
        }));
      }

      if (url === "/api/tasks/TASK-E2E/member-workbench?actor_id=2250001") {
        return Promise.resolve(jsonResponse(buildMemberWorkbenchSummary(workflowState)));
      }

      if (url === "/api/tasks/TASK-E2E/shared-invoices?actor_id=2250001") {
        return Promise.resolve(jsonResponse({
          task_id: "TASK-E2E",
          actor_id: "2250001",
          items: [],
        }));
      }

      if (url === "/api/tasks/TASK-E2E/invoices") {
        return Promise.resolve(jsonResponse({
          items: workflowState.invoiceSaved ? [buildInvoice()] : [],
        }));
      }

      if (url === "/api/materials/MAT-001/recognition-tasks") {
        return Promise.resolve(jsonResponse({
          latest_effective: workflowState.materialUploaded
            ? {
                id: "REC-001",
                material_id: "MAT-001",
                status: workflowState.invoiceSaved ? "succeeded" : "needs_confirmation",
                is_final_fact: false,
                failure: null,
                raw_response: { provider: "placeholder-ai" },
                recognized_fields: {
                  invoice_number: {
                    value: "INV-E2E-001",
                    source: "ai",
                    confidence: 0.95,
                    status: "recognized",
                    updated_at: "2026-04-28T12:06:00+08:00",
                  },
                },
                manual_corrections: [],
                created_at: "2026-04-28T12:05:30+08:00",
                updated_at: "2026-04-28T12:10:00+08:00",
              }
            : null,
          items: [],
        }));
      }

      if (url === "/api/tasks/TASK-E2E/status" && init?.method === "PATCH") {
        const body = parseRequestJsonBody(init);
        const targetStatus = body["target_status"];
        if (targetStatus !== "open") {
          throw new Error(`Unexpected task status update target: ${String(targetStatus)}`);
        }
        workflowState.taskStatus = "open";
        return Promise.resolve(jsonResponse(buildTask("open")));
      }

      if (url === "/api/tasks/TASK-E2E/materials" && init?.method === "POST") {
        workflowState.materialUploaded = true;
        expect(init.body).toBeInstanceOf(FormData);
        return Promise.resolve(jsonResponse({
          status: "success",
          items: [buildMaterial()],
        }, { status: 201 }));
      }

      if (url === "/api/tasks/TASK-E2E/review-summary?actor_id=admin-1") {
        return Promise.resolve(jsonResponse(buildReviewSummary(workflowState)));
      }

      if (url === "/api/tasks/TASK-E2E/overdue-confirmations?actor_id=admin-1") {
        return Promise.resolve(jsonResponse({
          task_id: "TASK-E2E",
          administrator_id: "admin-1",
          confirmation_deadline: "2026-11-10T10:00:00.000Z",
          is_overdue: false,
          total_overdue_members: 0,
          overdue_member_ids: [],
        }));
      }

      if (url === "/api/materials/MAT-001/invoice" && init?.method === "POST") {
        const body = parseRequestJsonBody(init);
        expect(body["actor_id"]).toBe("admin-1");
        expect(body["buyer_name"]).toBe("同济大学");
        expect(body["tax_number"]).toBe("91310000TEST00001");
        workflowState.invoiceSaved = true;
        return Promise.resolve(jsonResponse({
          invoice: buildInvoice(),
          validations: [
            buildValidation("invoice_title_match", "发票抬头匹配"),
            buildValidation("invoice_tax_number_match", "税号匹配"),
          ],
        }));
      }

      if (url === "/api/invoices/INV-001/validations") {
        return Promise.resolve(jsonResponse({
          items: workflowState.invoiceSaved
            ? [
                buildValidation("invoice_title_match", "发票抬头匹配"),
                buildValidation("invoice_tax_number_match", "税号匹配"),
              ]
            : [],
        }));
      }

      if (url === "/api/invoices/INV-001/splits" && init?.method === "PUT") {
        const body = parseRequestJsonBody(init);
        expect(body).toEqual({
          actor_id: "admin-1",
          items: [
            { member_id: "2250001", amount_cents: 12345, note: null },
          ],
        });
        workflowState.splitSaved = true;
        workflowState.confirmed = true;
        workflowState.taskStatus = "ready_to_export";
        return Promise.resolve(jsonResponse({
          items: [
            {
              id: "SPLIT-001",
              invoice_id: "INV-001",
              member_id: "2250001",
              amount_cents: 12345,
              note: "",
              version: 1,
              is_active: true,
              created_at: "2026-04-28T12:15:00+08:00",
              updated_at: "2026-04-28T12:15:00+08:00",
            },
          ],
        }));
      }

      if (url === "/api/tasks/TASK-E2E/expense-details?actor_id=2250001") {
        return Promise.resolve(jsonResponse({
          actor_id: "2250001",
          scope: "member",
          total_amount_cents: 12345,
          items: workflowState.splitSaved
            ? [
                {
                  split_id: "SPLIT-001",
                  split_version: 1,
                  member_id: "2250001",
                  amount_cents: 12345,
                  note: "self paid",
                  created_at: "2026-04-28T12:15:00+08:00",
                  updated_at: "2026-04-28T12:15:00+08:00",
                  invoice: buildInvoice(),
                  confirmation: workflowState.confirmed
                    ? {
                        id: "CONF-001",
                        member_id: "2250001",
                        split_version: 1,
                        status: "confirmed",
                        dispute_reason: null,
                        confirmed_at: "2026-04-28T12:20:00+08:00",
                        updated_at: "2026-04-28T12:20:00+08:00",
                      }
                    : null,
                },
              ]
            : [],
        }));
      }

      if (url === "/api/invoices/INV-001/supporting-materials") {
        return Promise.resolve(jsonResponse({ items: [] }));
      }

      if (url === "/api/invoices/INV-001/splits") {
        return Promise.resolve(jsonResponse({
          items: workflowState.splitSaved
            ? [
                {
                  id: "SPLIT-001",
                  invoice_id: "INV-001",
                  member_id: "2250001",
                  amount_cents: 12345,
                  note: "self paid",
                  version: 1,
                  is_active: true,
                  created_at: "2026-04-28T12:15:00+08:00",
                  updated_at: "2026-04-28T12:15:00+08:00",
                },
              ]
            : [],
        }));
      }

      if (url === "/api/invoices/INV-001/confirmations") {
        return Promise.resolve(jsonResponse({
          items: workflowState.confirmed
            ? [
                {
                  id: "CONF-001",
                  split_id: "SPLIT-001",
                  member_id: "2250001",
                  split_version: 1,
                  split_amount_cents: 12345,
                  split_note: "self paid",
                  is_current: true,
                  status: "confirmed",
                  dispute_reason: null,
                  confirmed_at: "2026-04-28T12:20:00+08:00",
                  updated_at: "2026-04-28T12:20:00+08:00",
                },
              ]
            : [],
        }));
      }

      if (url === "/api/splits/SPLIT-001/confirmation" && init?.method === "PUT") {
        const body = parseRequestJsonBody(init);
        expect(body).toEqual({
          actor_id: "2250001",
          member_id: "2250001",
          status: "confirmed",
          dispute_reason: null,
        });
        workflowState.confirmed = true;
        workflowState.taskStatus = "ready_to_export";
        return Promise.resolve(jsonResponse({
          id: "CONF-001",
          split_id: "SPLIT-001",
          member_id: "2250001",
          split_version: 1,
          split_amount_cents: 12345,
          split_note: "self paid",
          is_current: true,
          status: "confirmed",
          dispute_reason: null,
          confirmed_at: "2026-04-28T12:20:00+08:00",
          updated_at: "2026-04-28T12:20:00+08:00",
        }));
      }

      if (url === "/api/tasks/TASK-E2E/exports/capabilities?actor_id=admin-1") {
        return Promise.resolve(jsonResponse({
          task_id: "TASK-E2E",
          administrator_id: "admin-1",
          current_task_status: workflowState.taskStatus,
          export_allowed: workflowState.taskStatus === "ready_to_export",
          blocking_reasons: workflowState.taskStatus === "ready_to_export"
            ? []
            : ["task must be ready_to_export or completed before real exports can be generated"],
          execution_mode: "mock_api_placeholder",
          note: "本测试使用 mock API 作为主流程占位，不接入真实外部服务。",
          supported_exports: [
            {
              kind: "reimbursement_summary",
              formats: ["xlsx", "csv"],
              implemented: true,
              implemented_formats: ["csv"],
            },
            {
              kind: "member_details",
              formats: ["xlsx", "csv"],
              implemented: true,
              implemented_formats: ["csv"],
            },
            {
              kind: "invoice_details",
              formats: ["xlsx", "csv"],
              implemented: true,
              implemented_formats: ["csv"],
            },
            {
              kind: "missing_materials",
              formats: ["xlsx", "csv"],
              implemented: true,
              implemented_formats: ["csv"],
            },
            {
              kind: "finance_draft",
              formats: ["xlsx", "json"],
              implemented: true,
              implemented_formats: ["json"],
            },
            {
              kind: "merged_pdf",
              formats: ["pdf"],
              implemented: false,
              implemented_formats: [],
            },
            {
              kind: "reimbursement_package",
              formats: ["zip"],
              implemented: true,
              implemented_formats: ["zip"],
            },
          ],
        }));
      }

      if (url === "/api/tasks/TASK-E2E/exports?actor_id=admin-1") {
        return Promise.resolve(jsonResponse([]));
      }

      throw new Error(`Unhandled fetch URL in main flow placeholder test: ${url}`);
    });

    setMockSession("admin");
    renderRoute("/admin/tasks/new");

    expect(await screen.findByRole("heading", { name: "创建报销任务" })).toBeInTheDocument();
    await fillRequiredTaskForm();
    fireEvent.click(screen.getByRole("button", { name: "创建草稿任务" }));

    expect(await screen.findByRole("heading", { name: "任务管理" })).toBeInTheDocument();
    expect((await screen.findAllByText("E2E 主流程任务")).length).toBeGreaterThan(0);

    cleanup();
    setMockSession("admin");
    renderRoute("/admin/tasks/TASK-E2E");

    expect(await screen.findByRole("heading", { name: "任务详情与状态操作" })).toBeInTheDocument();
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "切换为收集中" }));
      await Promise.resolve();
    });
    const confirmDialog = await screen.findByRole("dialog");
    await act(async () => {
      fireEvent.click(within(confirmDialog).getByRole("button", { name: "确认切换状态" }));
      await Promise.resolve();
    });
    await waitFor(() => {
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });
    expect((await screen.findAllByText("收集中")).length).toBeGreaterThan(0);

      cleanup();
      setMockSession("member");
      renderRoute("/member/invoices/workbench?taskId=TASK-E2E#member-workbench-upload");

      expect(await screen.findByRole("heading", { name: "比赛报销材料提交" })).toBeInTheDocument();
      expect(await screen.findByText("上传报销材料")).toBeInTheDocument();
      fireEvent.change(screen.getByLabelText("工作台上传文件"), {
        target: {
          files: [new File(["fake-pdf"], "ticket.pdf", { type: "application/pdf" })],
        },
      });
      fireEvent.click(screen.getByRole("button", { name: "选择文件并上传" }));

      expect(await screen.findByText("最近上传处理状态")).toBeInTheDocument();
      expect(screen.getByText("材料类型：发票")).toBeInTheDocument();

      cleanup();
      setMockSession("admin");
      renderRoute("/admin/tasks/TASK-E2E/invoices?materialId=MAT-001");

      expect(await screen.findByRole("heading", { name: "发票人工录入与更正" })).toBeInTheDocument();
      fireEvent.change(screen.getByLabelText("发票抬头"), {
        target: { value: "同济大学" },
      });
      fireEvent.change(screen.getByLabelText("税号"), {
        target: { value: "91310000TEST00001" },
      });
      fireEvent.click(screen.getByRole("button", { name: "保存发票字段" }));

      expect(await screen.findByRole("heading", { name: "保存完成并已刷新校验结果" })).toBeInTheDocument();
      expect(screen.getByText(/发票 INV-E2E-001 当前共有 2 条校验结果/)).toBeInTheDocument();

      cleanup();
      setMockSession("admin");
      renderRoute("/admin/tasks/TASK-E2E/splits?invoiceId=INV-001");

      expect(await screen.findByRole("heading", { name: "费用分摊编辑" })).toBeInTheDocument();
      await act(async () => {
        fireEvent.click(screen.getByRole("button", { name: "保存费用分摊" }));
        await Promise.resolve();
      });
      const splitConfirmDialog = await screen.findByRole("dialog");
      await act(async () => {
        fireEvent.click(within(splitConfirmDialog).getByRole("button", { name: "确认保存分摊" }));
        await Promise.resolve();
      });
      await waitFor(() => {
        expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
      });

      expect(await screen.findByText(/已保存 1 条分摊，合计 ￥123.45。/)).toBeInTheDocument();

      cleanup();
      setMockSession("member");
      renderRoute("/member/invoices/INV-001?taskId=TASK-E2E");

      expect(await screen.findByRole("heading", { level: 1, name: "INV-E2E-001" })).toBeInTheDocument();
      expect(await screen.findByRole("heading", { name: "金额归属" })).toBeInTheDocument();
      expect(screen.queryByText("本人费用确认")).not.toBeInTheDocument();
      expect(screen.queryByRole("button", { name: "确认这笔费用" })).not.toBeInTheDocument();

      cleanup();
      setMockSession("admin");
      renderRoute("/admin/tasks/TASK-E2E/review");

      expect(await screen.findByRole("heading", { name: "管理员复核总览" })).toBeInTheDocument();
      expect(screen.getByText("当前复核摘要下没有待突出显示的异常项。")).toBeInTheDocument();

      cleanup();
      setMockSession("admin");
      renderRoute("/admin/tasks/TASK-E2E/exports");

      expect(await screen.findByRole("heading", { name: "导出与下载" })).toBeInTheDocument();
      expect(screen.getByText("材料包就绪度")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "生成完整材料包" })).toBeInTheDocument();
      expect(screen.getAllByText("可导出").length).toBeGreaterThan(0);
    },
    15_000,
  );
});
