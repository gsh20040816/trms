import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";

import { clearMockSession, setMockSession } from "./auth-store";
import { routes } from "./routes";

function jsonResponse(body: unknown, init: ResponseInit = {}) {
  return new Response(JSON.stringify(body), {
    status: init.status ?? 200,
    headers: { "Content-Type": "application/json" },
  });
}

function resolveRequestUrl(input: string | URL | Request) {
  return typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;
}

function resolveRequestMethod(input: string | URL | Request, init: RequestInit | undefined) {
  return init?.method?.toUpperCase() ?? (input instanceof Request ? input.method.toUpperCase() : "GET");
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
  fee_categories: ["railway", "hotel", "registration", "local_transport"],
  administrator_id: "admin-1",
  project_info: "ACM 竞赛项目",
  reimburser_info: "张管理员",
  invoice_title: "同济大学",
  tax_number: "91310113666007253C",
  created_at: "2026-04-28T08:00:00+08:00",
  updated_at: "2026-04-28T08:00:00+08:00",
};

function buildMaterialSummary(
  materialType: "payment_record" | "competition_notice" | "itinerary" | "order_screenshot" | "other_attachment",
  fieldName: string,
  fieldValue: unknown,
) {
  return {
    task_id: "TASK-OPEN",
    actor_id: "2250001",
    report: {
      task_id: "TASK-OPEN",
      actor_id: "2250001",
      total_expense_amount_cents: 0,
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
          material_id: "MAT-TYPE-001",
          submitter_id: "2250001",
          material_type: materialType,
          original_filename: `${materialType}.pdf`,
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
          id: "REC-TYPE-001",
          material_id: "MAT-TYPE-001",
          status: "succeeded",
          failure: null,
          recognized_fields: {
            document_family: { value: materialType, source: "ai", confidence: 0.99, status: "recognized", updated_at: null },
            material_type: { value: materialType, source: "ai", confidence: 0.99, status: "recognized", updated_at: null },
            expense_type_candidate: { value: "local_transport", source: "ai", confidence: 0.85, status: "recognized", updated_at: null },
            classification_confidence: { value: 0.91, source: "ai", confidence: 0.91, status: "recognized", updated_at: null },
            is_reimbursement_voucher: { value: false, source: "ai", confidence: 0.95, status: "recognized", updated_at: null },
            [fieldName]: { value: fieldValue, source: "ai", confidence: 0.95, status: "recognized", updated_at: null },
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
        queue_group: "recognition_review",
        blocking_reasons: ["recognition_review"],
        ready_for_submission: false,
      },
    ],
    pending_supporting_material_linkage_items: [
      {
        material_id: "MAT-TYPE-001",
        submitter_id: "2250001",
        material_type: materialType,
        original_filename: `${materialType}.pdf`,
        pending_reason: "multiple_candidates",
        linked_invoices: [
          {
            invoice_id: "INV-LINKED-001",
            invoice_number: "INV-LINKED-001",
            amount_cents: 8888,
            expense_type: "railway",
            original_filename: "linked.pdf",
          },
        ],
        candidate_invoices: [
          {
            invoice_id: "INV-CANDIDATE-001",
            invoice_number: "INV-CANDIDATE-001",
            amount_cents: 12345,
            expense_type: "local_transport",
            original_filename: "candidate.pdf",
          },
        ],
        created_at: "2026-04-28T10:00:00+08:00",
      },
    ],
    shared_invoices: [],
  };
}

function renderMaterialRoute(summary: ReturnType<typeof buildMaterialSummary>) {
  vi.spyOn(globalThis, "fetch").mockImplementation((input: string | URL | Request, init?: RequestInit) => {
    const url = resolveRequestUrl(input);
    const method = resolveRequestMethod(input, init);

    if (url === "/api/tasks/TASK-OPEN" && method === "GET") {
      return Promise.resolve(jsonResponse(task));
    }
    if (url === "/api/tasks/TASK-OPEN/member-workbench?actor_id=2250001" && method === "GET") {
      return Promise.resolve(jsonResponse(summary));
    }

    throw new Error(`Unhandled request ${method} ${url}`);
  });

  const router = createMemoryRouter(routes, {
    initialEntries: ["/member/materials/MAT-TYPE-001?taskId=TASK-OPEN"],
  });

  act(() => {
    render(<RouterProvider router={router} />);
  });
}

describe("MemberMaterialDetailPage", () => {
  beforeEach(() => {
    clearMockSession();
    setMockSession("member");
  });

  afterEach(() => {
    vi.restoreAllMocks();
    clearMockSession();
  });

  it.each([
    ["payment_record", "支付记录详情", "金额", "￥123.45"],
    ["competition_notice", "比赛通知详情", "地点", "武汉赛区通知"],
    ["itinerary", "行程单详情", "交通方式", "SHA"],
    ["order_screenshot", "订单截图详情", "交通方式", "网约车"],
    ["other_attachment", "其他材料详情", "行程/路线", "同济大学-武汉站"],
  ] as const)("renders dedicated page for %s materials", async (materialType, heading, fieldLabel, expectedValue) => {
    const materialLabelMap = {
      payment_record: "支付记录",
      competition_notice: "比赛通知",
      itinerary: "行程单",
      order_screenshot: "订单截图",
      other_attachment: "其他材料",
    } as const;
    const fieldMap = {
      payment_record: ["amount_cents", 12345],
      competition_notice: ["location", "武汉赛区通知"],
      itinerary: ["transport_mode", "SHA"],
      order_screenshot: ["transport_mode", "网约车"],
      other_attachment: ["trip_route", "同济大学-武汉站"],
    } as const;
    const [fieldName, fieldValue] = fieldMap[materialType];
    renderMaterialRoute(buildMaterialSummary(materialType, fieldName, fieldValue));

    expect(await screen.findByRole("heading", { name: heading })).toBeInTheDocument();
    expect(screen.getByLabelText("当前材料识别判断")).toBeInTheDocument();
    const recognizedFieldSection = screen.getByLabelText(`${materialLabelMap[materialType]}识别字段`);
    expect(recognizedFieldSection).toBeInTheDocument();
    expect(within(recognizedFieldSection).getByText(fieldLabel)).toBeInTheDocument();
    expect(within(recognizedFieldSection).getByText(expectedValue)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "关联归属发票" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "归属发票参考" })).not.toBeInTheDocument();
    expect(screen.getByRole("checkbox", { name: /INV-LINKED-001/ })).toBeChecked();
    expect(screen.getByRole("checkbox", { name: /INV-CANDIDATE-001/ })).not.toBeChecked();
    expect(screen.getByRole("button", { name: "查看发票 INV-LINKED-001" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "查看发票 INV-CANDIDATE-001" })).toBeInTheDocument();
  });

  it("hides airfare-only fields for local transport itineraries", async () => {
    const summary = buildMaterialSummary("itinerary", "transport_mode", "网约车");
    const firstItem = summary.items[0];
    if (!firstItem?.recognition) {
      throw new Error("expected itinerary recognition fixture");
    }
    firstItem.recognition.recognized_fields.expense_type = {
      value: "local_transport",
      source: "ai",
      confidence: 0.98,
      status: "recognized",
      updated_at: null,
    };
    firstItem.recognition.recognized_fields.trip_route = {
      value: "同济大学嘉定校区(北门) -> 上海虹桥站(北进站口)",
      source: "ai",
      confidence: 0.95,
      status: "recognized",
      updated_at: null,
    };
    renderMaterialRoute(summary);

    expect(await screen.findByRole("heading", { name: "行程单详情" })).toBeInTheDocument();
    const recognizedFieldSection = screen.getByLabelText("行程单识别字段");
    expect(within(recognizedFieldSection).getByText("交通方式")).toBeInTheDocument();
    expect(within(recognizedFieldSection).queryByText("去程出发机场")).not.toBeInTheDocument();
    expect(screen.getByText("这里处理市内交通网约车行程单的时间、路线和出行方式，不再展示航空机场代码或舱位字段。")).toBeInTheDocument();
  });

  it("shows current linked invoices even when no remaining candidate invoices exist", async () => {
    const summary = buildMaterialSummary("itinerary", "transport_mode", "网约车");
    summary.pending_supporting_material_linkage_items = [
      {
        material_id: "MAT-TYPE-001",
        submitter_id: "2250001",
        material_type: "itinerary",
        original_filename: "itinerary.pdf",
        pending_reason: "manual_confirmation_required",
        linked_invoices: [
          {
            invoice_id: "INV-LINKED-001",
            invoice_number: "INV-LINKED-001",
            amount_cents: 8888,
            expense_type: "local_transport",
            original_filename: "linked.pdf",
          },
        ],
        candidate_invoices: [],
        created_at: "2026-04-28T10:00:00+08:00",
      },
    ];
    renderMaterialRoute(summary);

    expect(await screen.findByRole("heading", { name: "关联归属发票" })).toBeInTheDocument();
    expect(screen.getByLabelText("当前已关联发票列表")).toBeInTheDocument();
    expect(screen.getByText("INV-LINKED-001")).toBeInTheDocument();
    expect(screen.getByText("当前材料已经关联到发票，暂时没有新的候选发票需要处理。")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "去上传区补录或补传发票" })).not.toBeInTheDocument();
  });

  it("updates linked invoices from the material detail page", async () => {
    const requests: Array<{ method: string; url: string }> = [];
    const summary = buildMaterialSummary("payment_record", "amount_cents", 12345);

    vi.spyOn(globalThis, "fetch").mockImplementation((input: string | URL | Request, init?: RequestInit) => {
      const url = resolveRequestUrl(input);
      const method = resolveRequestMethod(input, init);
      requests.push({ method, url });

      if (url === "/api/tasks/TASK-OPEN" && method === "GET") {
        return Promise.resolve(jsonResponse(task));
      }
      if (url === "/api/tasks/TASK-OPEN/member-workbench?actor_id=2250001" && method === "GET") {
        return Promise.resolve(jsonResponse(summary));
      }
      if (url === "/api/invoices/INV-CANDIDATE-001/supporting-materials/MAT-TYPE-001" && method === "PUT") {
        return Promise.resolve(jsonResponse({ item: { id: "MAT-TYPE-001" } }));
      }
      if (url === "/api/invoices/INV-LINKED-001/supporting-materials/MAT-TYPE-001" && method === "DELETE") {
        return Promise.resolve(jsonResponse({ status: "deleted" }));
      }

      throw new Error(`Unhandled request ${method} ${url}`);
    });

    const router = createMemoryRouter(routes, {
      initialEntries: ["/member/materials/MAT-TYPE-001?taskId=TASK-OPEN"],
    });

    act(() => {
      render(<RouterProvider router={router} />);
    });

    expect(await screen.findByRole("heading", { name: "支付记录详情" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("checkbox", { name: /INV-LINKED-001/ }));
    fireEvent.click(screen.getByRole("checkbox", { name: /INV-CANDIDATE-001/ }));
    fireEvent.click(screen.getByRole("button", { name: "更改关联" }));

    await waitFor(() => {
      expect(requests).toContainEqual({
        method: "DELETE",
        url: "/api/invoices/INV-LINKED-001/supporting-materials/MAT-TYPE-001",
      });
      expect(requests).toContainEqual({
        method: "PUT",
        url: "/api/invoices/INV-CANDIDATE-001/supporting-materials/MAT-TYPE-001",
      });
    });
  });
});
