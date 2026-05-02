import { act, fireEvent, render, screen, within } from "@testing-library/react";
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

function buildTask() {
  return {
    id: "TASK-REVIEW",
    status: "reviewing",
    competition_name: "ICPC 复核任务",
    competition_location: "上海",
    competition_start_date: "2026-05-01",
    competition_end_date: "2026-05-03",
    deadline: "2026-05-10T18:00:00+08:00",
    member_ids: ["2250001", "2250002"],
    member_summaries: [
      { member_id: "2250001", username: "member1", display_name: "张三", student_id: "2250001" },
      { member_id: "2250002", username: "member2", display_name: "李四", student_id: "2250002" },
    ],
    fee_categories: ["registration", "hotel"],
    administrator_id: "admin-1",
    project_info: "ACM 竞赛项目",
    reimburser_info: "张管理员",
    invoice_title: "同济大学",
    tax_number: "91310000TEST00001",
    created_at: "2026-04-20T09:00:00+08:00",
    updated_at: "2026-04-25T10:00:00+08:00",
  };
}

function buildReviewSummary() {
  return {
    task_id: "TASK-REVIEW",
    administrator_id: "admin-1",
    counts: {
      material_count: 1,
      pending_assignment_material_count: 0,
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
              confidence: 0.42,
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
    pending_assignment_materials: [],
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
        supporting_material_ids: [],
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
              member_id: "2250001",
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
              member_id: "2250002",
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
              member_id: "2250002",
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
  };
}

function renderCorrectionsRoute(entry = "/admin/tasks/TASK-REVIEW/corrections") {
  const router = createMemoryRouter(routes, {
    initialEntries: [entry],
  });

  render(<RouterProvider router={router} />);
}

describe("AdminCorrectionsRemindersPage", () => {
  beforeEach(() => {
    clearMockSession();
    setMockSession("admin");
  });

  afterEach(() => {
    vi.restoreAllMocks();
    clearMockSession();
  });

  it("shows only member reminder controls and records manual material reminders", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((input: string | URL | Request, init?: RequestInit) => {
      const url = resolveRequestUrl(input);

      if (url === "/api/tasks/TASK-REVIEW") {
        return Promise.resolve(jsonResponse(buildTask()));
      }

      if (url === "/api/tasks/TASK-REVIEW/review-summary?actor_id=admin-1") {
        return Promise.resolve(jsonResponse(buildReviewSummary()));
      }

      if (url === "/api/tasks/TASK-REVIEW/material-reminders?actor_id=admin-1") {
        return Promise.resolve(jsonResponse({
          items: [
            {
              id: "REM-001",
              task_id: "TASK-REVIEW",
              administrator_id: "admin-1",
              member_id: "2250001",
              content: "请补充支付记录。",
              created_at: "2026-04-28T09:40:00+08:00",
            },
          ],
        }));
      }

      if (url === "/api/tasks/TASK-REVIEW/material-reminders" && init?.method === "POST") {
        expect(init.body).toBe(JSON.stringify({
          administrator_id: "admin-1",
          member_id: "2250002",
          content: "请补充比赛通知，并在补交后重新确认金额。",
        }));
        return Promise.resolve(jsonResponse({
          id: "REM-002",
          task_id: "TASK-REVIEW",
          administrator_id: "admin-1",
          member_id: "2250002",
          content: "请补充比赛通知，并在补交后重新确认金额。",
          created_at: "2026-04-28T09:45:00+08:00",
        }, { status: 201 }));
      }

      throw new Error(`Unhandled fetch URL in admin corrections test: ${url}`);
    });

    renderCorrectionsRoute();

    expect(await screen.findByRole("heading", { name: "管理员补材料提醒" })).toBeInTheDocument();
    expect(screen.getByText("这里只保存内部提醒记录，不会自动发送短信、邮件或 Telegram 消息；如需真正通知成员，请另行联系。")).toBeInTheDocument();
    expect(screen.queryByText("待人工更正项")).not.toBeInTheDocument();
    expect(screen.queryByText("识别字段待确认或待补录材料")).not.toBeInTheDocument();
    expect(screen.queryByText("存在异常校验或异议的发票")).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "更正识别字段与金额" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "更正发票金额与字段" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "调整当前发票分摊" })).not.toBeInTheDocument();
    expect(screen.queryByText(/材料编号/)).not.toBeInTheDocument();

    const reminderList = within(await screen.findByLabelText("补材料提醒列表"));
    expect(reminderList.getByText("请补充支付记录。")).toBeInTheDocument();
    expect(reminderList.getByText("张三 / member1 / 2250001")).toBeInTheDocument();

    await act(async () => {
      fireEvent.mouseDown(screen.getByRole("combobox", { name: "提醒对象成员" }));
      await Promise.resolve();
    });
    fireEvent.click(await screen.findByRole("option", { name: "李四 / member2 / 2250002" }));
    fireEvent.change(screen.getByLabelText("提醒内容"), {
      target: { value: "请补充比赛通知，并在补交后重新确认金额。" },
    });
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "保存内部提醒记录" }));
      await Promise.resolve();
    });

    expect(await screen.findByText("已保存对李四 / member2 / 2250002的内部提醒记录；系统不会自动发送消息。")).toBeInTheDocument();
    const updatedReminderList = within(screen.getByLabelText("补材料提醒列表"));
    expect(updatedReminderList.getByText("请补充比赛通知，并在补交后重新确认金额。")).toBeInTheDocument();
  });

  it("shows backend reminder creation errors instead of pretending success", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((input: string | URL | Request, init?: RequestInit) => {
      const url = resolveRequestUrl(input);

      if (url === "/api/tasks/TASK-REVIEW") {
        return Promise.resolve(jsonResponse(buildTask()));
      }

      if (url === "/api/tasks/TASK-REVIEW/review-summary?actor_id=admin-1") {
        return Promise.resolve(jsonResponse(buildReviewSummary()));
      }

      if (url === "/api/tasks/TASK-REVIEW/material-reminders?actor_id=admin-1") {
        return Promise.resolve(jsonResponse({ items: [] }));
      }

      if (url === "/api/tasks/TASK-REVIEW/material-reminders" && init?.method === "POST") {
        return Promise.resolve(jsonResponse(
          { detail: "member 2250002 is not part of this task" },
          { status: 422 },
        ));
      }

      throw new Error(`Unhandled fetch URL in admin corrections error test: ${url}`);
    });

    renderCorrectionsRoute();

    await screen.findByRole("heading", { name: "管理员补材料提醒" });

    await act(async () => {
      fireEvent.mouseDown(screen.getByRole("combobox", { name: "提醒对象成员" }));
      await Promise.resolve();
    });
    fireEvent.click(await screen.findByRole("option", { name: "李四 / member2 / 2250002" }));
    fireEvent.change(screen.getByLabelText("提醒内容"), {
      target: { value: "请补交材料。" },
    });
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "保存内部提醒记录" }));
      await Promise.resolve();
    });

    expect(await screen.findByRole("heading", { name: "操作未完成" })).toBeInTheDocument();
    expect(screen.getByText("成员 2250002 不在当前任务成员名单中。")).toBeInTheDocument();
  });

  it("filters reminder members by keyword and shows no-result hint", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((input: string | URL | Request) => {
      const url = resolveRequestUrl(input);

      if (url === "/api/tasks/TASK-REVIEW") {
        return Promise.resolve(jsonResponse(buildTask()));
      }

      if (url === "/api/tasks/TASK-REVIEW/review-summary?actor_id=admin-1") {
        return Promise.resolve(jsonResponse(buildReviewSummary()));
      }

      if (url === "/api/tasks/TASK-REVIEW/material-reminders?actor_id=admin-1") {
        return Promise.resolve(jsonResponse({ items: [] }));
      }

      throw new Error(`Unhandled fetch URL in member filter test: ${url}`);
    });

    renderCorrectionsRoute();

    await screen.findByRole("heading", { name: "管理员补材料提醒" });

    const memberInput = screen.getByLabelText("提醒对象成员搜索");
    await act(async () => {
      fireEvent.change(memberInput, {
        target: { value: "02" },
      });
      await Promise.resolve();
    });
    await act(async () => {
      fireEvent.mouseDown(screen.getByRole("combobox", { name: "提醒对象成员" }));
      await Promise.resolve();
    });
    expect(await screen.findByRole("option", { name: "李四 / member2 / 2250002" })).toBeInTheDocument();
    expect(screen.queryByRole("option", { name: "张三 / member1 / 2250001" })).not.toBeInTheDocument();

    await act(async () => {
      fireEvent.change(memberInput, {
        target: { value: "999" },
      });
      await Promise.resolve();
    });
    expect(await screen.findByRole("option", { name: "没有匹配的成员" })).toBeInTheDocument();
  });
});
