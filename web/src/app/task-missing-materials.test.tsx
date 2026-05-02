import { act, fireEvent, render, screen } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { clearMockSession, setMockSession } from "./auth-store";
import { MemberMissingMaterialsPage } from "./task-missing-materials";

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

function renderMemberRoute(entry: string) {
  const router = createMemoryRouter([{
    path: "/member/materials/missing",
    element: <MemberMissingMaterialsPage />,
  }], {
    initialEntries: [entry],
  });

  act(() => {
    render(<RouterProvider router={router} />);
  });
}

async function selectMuiOption(name: string, optionText: string) {
  const select = screen.getByRole("combobox", { name });
  act(() => {
    fireEvent.mouseDown(select);
  });
  const option = await screen.findByRole("option", { name: optionText });
  act(() => {
    fireEvent.click(option);
  });
}

describe("task missing materials pages", () => {
  beforeEach(() => {
    clearMockSession();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    clearMockSession();
  });

  it("renders member missing materials view with only current-member items", async () => {
    setMockSession("member");

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
            fee_categories: ["registration", "railway"],
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

      if (url === "/api/tasks/TASK-OPEN/missing-materials?actor_id=2250001") {
        return Promise.resolve(jsonResponse({
          task_id: "TASK-OPEN",
          actor_id: "2250001",
          scope: "member",
          items: [
            {
              task_id: "TASK-OPEN",
              member_id: "2250001",
              invoice_id: "INV-REG-001",
              invoice_number: "REG-001",
              expense_type: "registration",
              required_material_type: "competition_notice",
              source_rule_code: "invoice_competition_notice_required",
              message: "参赛费缺少比赛通知",
              evidence: {},
              detected_at: "2026-04-28T09:10:00+08:00",
            },
            {
              task_id: "TASK-OPEN",
              member_id: "2250001",
              invoice_id: "INV-REG-001",
              invoice_number: "REG-001",
              expense_type: "registration",
              required_material_type: "payment_record",
              source_rule_code: "invoice_payment_record_required",
              message: "发票金额达到阈值，缺少支付记录",
              evidence: {},
              detected_at: "2026-04-28T09:11:00+08:00",
            },
          ],
        }));
      }

      throw new Error(`Unhandled fetch URL in missing materials member test: ${url}`);
    });

    renderMemberRoute("/member/materials/missing?taskId=TASK-OPEN");

    expect(await screen.findByRole("heading", { name: "我的缺失材料" })).toBeInTheDocument();
    expect(await screen.findByRole("combobox", { name: "目标任务" })).toHaveTextContent(
      "ICPC Xi'an Regional（TASK-OPEN）",
    );
    expect(screen.getByRole("combobox", { name: "查看维度" })).toHaveTextContent("按发票查看");
    const groupedList = await screen.findByLabelText("缺失材料分组列表");
    expect(await screen.findByLabelText("缺失材料摘要")).toHaveTextContent("缺失项");
    expect(screen.getByLabelText("缺失材料摘要")).toHaveTextContent("2");
    expect(groupedList).toHaveTextContent("发票 REG-001");
    expect(groupedList).toHaveTextContent("参赛费缺少比赛通知");
    expect(screen.queryByText("2250002")).not.toBeInTheDocument();

    await selectMuiOption("查看维度", "按费用类型查看");

    expect(await screen.findByText("参赛费")).toBeInTheDocument();
  });
});
