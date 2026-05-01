import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
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

function buildTask() {
  return {
    id: "TASK-ALPHA",
    status: "reviewing",
    competition_name: "全国邀请赛",
    competition_location: "上海",
    competition_start_date: "2026-05-01",
    competition_end_date: "2026-05-03",
    deadline: "2026-05-10T18:00:00+08:00",
    member_ids: ["2250001", "2250002", "2250003"],
    fee_categories: ["railway", "hotel"],
    administrator_id: "admin-1",
    project_info: "Project A",
    reimburser_info: "张管理员",
    invoice_title: "同济大学",
    tax_number: "91310000TEST00001",
    created_at: "2026-04-20T09:00:00+08:00",
    updated_at: "2026-04-25T10:00:00+08:00",
  };
}

function buildReviewSummary(options?: {
  splitAmounts?: number[];
  includeThirdSplit?: boolean;
}) {
  const splitAmounts = options?.splitAmounts ?? [6000, 6345];
  const includeThirdSplit = options?.includeThirdSplit ?? false;

  const baseSplits = [
    {
      split: {
        id: "SPLIT-1",
        invoice_id: "INV-1",
        member_id: "2250001",
        amount_cents: splitAmounts[0] ?? 6000,
        note: "self paid",
        version: 1,
        is_active: true,
        created_at: "2026-04-28T10:00:00+08:00",
        updated_at: "2026-04-28T10:00:00+08:00",
      },
      confirmation: {
        id: "CONFIRM-1",
        split_id: "SPLIT-1",
        member_id: "2250001",
        split_version: 1,
        split_amount_cents: splitAmounts[0] ?? 6000,
        split_note: "self paid",
        is_current: true,
        status: "confirmed",
        dispute_reason: null,
        confirmed_at: "2026-04-28T10:05:00+08:00",
        updated_at: "2026-04-28T10:05:00+08:00",
      },
    },
    {
      split: {
        id: "SPLIT-2",
        invoice_id: "INV-1",
        member_id: "2250002",
        amount_cents: splitAmounts[1] ?? 6345,
        note: "team shared",
        version: 1,
        is_active: true,
        created_at: "2026-04-28T10:00:00+08:00",
        updated_at: "2026-04-28T10:00:00+08:00",
      },
      confirmation: {
        id: "CONFIRM-2",
        split_id: "SPLIT-2",
        member_id: "2250002",
        split_version: 1,
        split_amount_cents: splitAmounts[1] ?? 6345,
        split_note: "team shared",
        is_current: true,
        status: "pending",
        dispute_reason: null,
        confirmed_at: "2026-04-28T10:06:00+08:00",
        updated_at: "2026-04-28T10:06:00+08:00",
      },
    },
  ];

  if (includeThirdSplit) {
    baseSplits.push({
      split: {
        id: "SPLIT-3",
        invoice_id: "INV-1",
        member_id: "2250003",
        amount_cents: splitAmounts[2] ?? 4345,
        note: "third member",
        version: 2,
        is_active: true,
        created_at: "2026-04-28T10:10:00+08:00",
        updated_at: "2026-04-28T10:10:00+08:00",
      },
      confirmation: {
        id: "CONFIRM-3",
        split_id: "SPLIT-3",
        member_id: "2250003",
        split_version: 2,
        split_amount_cents: splitAmounts[2] ?? 4345,
        split_note: "third member",
        is_current: true,
        status: "pending",
        dispute_reason: null,
        confirmed_at: "2026-04-28T10:12:00+08:00",
        updated_at: "2026-04-28T10:12:00+08:00",
      },
    });
  }

  return {
    task_id: "TASK-ALPHA",
    administrator_id: "admin-1",
    counts: {
      material_count: 1,
      invoice_count: 1,
      validation_count: 2,
      blocker_failed_validation_count: 1,
      split_count: baseSplits.length,
      confirmed_split_count: 1,
      pending_confirmation_count: includeThirdSplit ? 2 : 1,
      disputed_confirmation_count: 0,
      missing_confirmation_count: 0,
      pending_recognition_count: 0,
      failed_recognition_count: 0,
      needs_confirmation_recognition_count: 0,
    },
    materials: [
      {
        material: {
          id: "MAT-INV-1",
          status: "assigned",
          task_id: "TASK-ALPHA",
          submitter_id: "2250001",
          task_id_hint: null,
          submitter_id_hint: null,
          channel: "web",
          material_type: "invoice",
          storage_key: "TASK-ALPHA/MAT-INV-1-invoice.pdf",
          original_filename: "invoice.pdf",
          content_type: "application/pdf",
          size_bytes: 128,
          sha256: "a".repeat(64),
          duplicate_of: null,
          claimed_by: null,
          claimed_at: null,
          created_at: "2026-04-28T09:00:00+08:00",
        },
        latest_recognition: null,
        invoice_id: "INV-1",
        supporting_invoice_ids: [],
      },
    ],
    invoices: [
      {
        invoice: {
          id: "INV-1",
          task_id: "TASK-ALPHA",
          material_id: "MAT-INV-1",
          invoice_number: "INV-001",
          issue_date: "2026-04-21",
          transaction_time: "2026-04-21T09:30:00+08:00",
          buyer_name: "同济大学",
          tax_number: "91310000TEST00001",
          seller_name: "中国铁路",
          amount_cents: 12345,
          expense_type: "railway",
          created_at: "2026-04-28T09:10:00+08:00",
          updated_at: "2026-04-28T09:10:00+08:00",
        },
        supporting_material_ids: [],
        validations: [
          {
            id: "VAL-1",
            rule_code: "invoice_title_match",
            target_type: "invoice",
            target_id: "INV-1",
            severity: "blocker",
            status: "passed",
            message: "发票抬头匹配",
            evidence: {},
            created_at: "2026-04-28T09:10:00+08:00",
          },
          {
            id: "VAL-2",
            rule_code: "invoice_tax_number_match",
            target_type: "invoice",
            target_id: "INV-1",
            severity: "blocker",
            status: "failed",
            message: "税号不匹配",
            evidence: {},
            created_at: "2026-04-28T09:10:00+08:00",
          },
        ],
        splits: baseSplits,
      },
    ],
  };
}

function renderAdminSplitEditorRoute(entry = "/admin/tasks/TASK-ALPHA/splits") {
  const router = createMemoryRouter(routes, {
    initialEntries: [entry],
  });

  render(<RouterProvider router={router} />);
}

async function chooseSplitMember(row: HTMLElement, memberId: string) {
  act(() => {
    fireEvent.mouseDown(within(row).getByRole("combobox", { name: "归属成员" }));
  });
  const option = await screen.findByRole("option", { name: memberId });
  await act(async () => {
    fireEvent.click(option);
    await Promise.resolve();
  });
}

describe("admin split editor page", () => {
  beforeEach(() => {
    clearMockSession();
    setMockSession("admin");
  });

  afterEach(() => {
    vi.restoreAllMocks();
    clearMockSession();
  });

  it("renders split rows, shows difference, saves splits, and refreshes summary", async () => {
    let reviewSummaryRequestCount = 0;
    let replaceSplitsRequestCount = 0;

    vi.spyOn(globalThis, "fetch").mockImplementation((input: string | URL | Request, init?: RequestInit) => {
      const url = resolveRequestUrl(input);

      if (url === "/api/tasks/TASK-ALPHA") {
        return Promise.resolve(jsonResponse(buildTask()));
      }

      if (url === "/api/tasks/TASK-ALPHA/review-summary?actor_id=admin-1") {
        reviewSummaryRequestCount += 1;
        if (reviewSummaryRequestCount === 1) {
          return Promise.resolve(jsonResponse(buildReviewSummary()));
        }
        return Promise.resolve(jsonResponse(buildReviewSummary({
          splitAmounts: [5000, 3000, 4345],
          includeThirdSplit: true,
        })));
      }

      if (url === "/api/invoices/INV-1/splits" && init?.method === "PUT") {
        replaceSplitsRequestCount += 1;
        expect(parseRequestJsonBody(init)).toEqual({
          actor_id: "admin-1",
          items: [
            { member_id: "2250001", amount_cents: 5000, note: "self paid" },
            { member_id: "2250002", amount_cents: 3000, note: "team shared" },
            { member_id: "2250003", amount_cents: 4345, note: "third member" },
          ],
        });
        return Promise.resolve(jsonResponse({
          items: [
            {
              id: "SPLIT-1",
              invoice_id: "INV-1",
              member_id: "2250001",
              amount_cents: 5000,
              note: "self paid",
              version: 2,
              is_active: true,
              created_at: "2026-04-28T10:00:00+08:00",
              updated_at: "2026-04-28T10:20:00+08:00",
            },
            {
              id: "SPLIT-2",
              invoice_id: "INV-1",
              member_id: "2250002",
              amount_cents: 3000,
              note: "team shared",
              version: 2,
              is_active: true,
              created_at: "2026-04-28T10:00:00+08:00",
              updated_at: "2026-04-28T10:20:00+08:00",
            },
            {
              id: "SPLIT-3",
              invoice_id: "INV-1",
              member_id: "2250003",
              amount_cents: 4345,
              note: "third member",
              version: 2,
              is_active: true,
              created_at: "2026-04-28T10:20:00+08:00",
              updated_at: "2026-04-28T10:20:00+08:00",
            },
          ],
        }));
      }

      throw new Error(`Unhandled fetch URL in split editor test: ${url}`);
    });

    renderAdminSplitEditorRoute();

    expect(await screen.findByRole("heading", { name: "费用分摊编辑" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /任务发票 invoice\.pdf INV-001/ })).toBeInTheDocument();
    expect(screen.getByText("票号 INV-001")).toBeInTheDocument();
    expect(screen.getByText("当前发票号 INV-001")).toBeInTheDocument();
    expect(screen.getByText("+￥0.00")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "新增分摊行" }));

    const thirdRow = await screen.findByRole("group", { name: "分摊行 3" });
    await chooseSplitMember(thirdRow, "2250003");
    fireEvent.change(within(thirdRow).getByRole("textbox", { name: "分摊金额（元）" }), {
      target: { value: "43.45" },
    });
    fireEvent.change(within(thirdRow).getByRole("textbox", { name: "备注" }), {
      target: { value: "third member" },
    });

    const secondRow = screen.getByRole("group", { name: "分摊行 2" });
    fireEvent.change(within(secondRow).getByRole("textbox", { name: "分摊金额（元）" }), {
      target: { value: "30" },
    });

    expect(screen.getByText("+￥10.00")).toBeInTheDocument();

    const firstRow = screen.getByRole("group", { name: "分摊行 1" });
    fireEvent.change(within(firstRow).getByRole("textbox", { name: "分摊金额（元）" }), {
      target: { value: "50" },
    });
    fireEvent.change(within(firstRow).getByRole("textbox", { name: "分摊金额（元）" }), {
      target: { value: "50.00" },
    });
    expect(screen.getByText("+￥0.00")).toBeInTheDocument();

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "保存费用分摊" }));
      await Promise.resolve();
    });
    const confirmDialog = await screen.findByRole("dialog");
    expect(within(confirmDialog).getByText("任务 全国邀请赛（TASK-ALPHA）的发票 INV-001 将按当前表单覆盖保存 3 条分摊。服务端可能把受影响成员的确认状态重置为待确认，请确认金额和归属成员已核对无误。")).toBeInTheDocument();
    await act(async () => {
      fireEvent.click(within(confirmDialog).getByRole("button", { name: "继续编辑" }));
      await Promise.resolve();
    });
    await waitFor(() => {
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });

    expect(replaceSplitsRequestCount).toBe(0);

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "保存费用分摊" }));
      await Promise.resolve();
    });
    const secondConfirmDialog = await screen.findByRole("dialog");
    await act(async () => {
      fireEvent.click(within(secondConfirmDialog).getByRole("button", { name: "确认保存分摊" }));
      await Promise.resolve();
    });
    await waitFor(() => {
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });

    expect(await screen.findByText(/2250003 · ￥43.45/)).toBeInTheDocument();
    expect(replaceSplitsRequestCount).toBe(1);
    expect(screen.getByText("已确认 1 / 3")).toBeInTheDocument();
  });

  it("confirms before deleting a split row and keeps the row when canceled", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((input: string | URL | Request) => {
      const url = resolveRequestUrl(input);

      if (url === "/api/tasks/TASK-ALPHA") {
        return Promise.resolve(jsonResponse(buildTask()));
      }

      if (url === "/api/tasks/TASK-ALPHA/review-summary?actor_id=admin-1") {
        return Promise.resolve(jsonResponse(buildReviewSummary()));
      }

      throw new Error(`Unhandled fetch URL in split row delete confirmation test: ${url}`);
    });

    renderAdminSplitEditorRoute();

    expect(await screen.findByRole("heading", { name: "费用分摊编辑" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "新增分摊行" }));

    const thirdRow = await screen.findByRole("group", { name: "分摊行 3" });
    fireEvent.click(within(thirdRow).getByRole("button", { name: "删除" }));
    const confirmDialog = await screen.findByRole("dialog");
    expect(within(confirmDialog).getByText("当前正在编辑任务 全国邀请赛（TASK-ALPHA）下发票 INV-001 的分摊方案。删除后，这一行尚未保存的成员、金额和备注会直接丢失。")).toBeInTheDocument();
    await act(async () => {
      fireEvent.click(within(confirmDialog).getByRole("button", { name: "继续编辑" }));
      await Promise.resolve();
    });
    await waitFor(() => {
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });

    expect(screen.getByRole("group", { name: "分摊行 3" })).toBeInTheDocument();

    fireEvent.click(within(screen.getByRole("group", { name: "分摊行 3" })).getByRole("button", { name: "删除" }));
    const secondConfirmDialog = await screen.findByRole("dialog");
    await act(async () => {
      fireEvent.click(within(secondConfirmDialog).getByRole("button", { name: "删除分摊行" }));
      await Promise.resolve();
    });
    await waitFor(() => {
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });

    expect(screen.queryByRole("group", { name: "分摊行 3" })).not.toBeInTheDocument();
  });

  it("shows helper text and does not submit when a split row is invalid", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((input: string | URL | Request, init?: RequestInit) => {
      const url = resolveRequestUrl(input);

      if (url === "/api/tasks/TASK-ALPHA") {
        return Promise.resolve(jsonResponse(buildTask()));
      }

      if (url === "/api/tasks/TASK-ALPHA/review-summary?actor_id=admin-1") {
        return Promise.resolve(jsonResponse(buildReviewSummary()));
      }

      if (url === "/api/invoices/INV-1/splits" && init?.method === "PUT") {
        throw new Error("Expected validation to prevent the split submit request.");
      }

      throw new Error(`Unhandled fetch URL in split editor validation test: ${url}`);
    });

    renderAdminSplitEditorRoute();

    const firstRow = await screen.findByRole("group", { name: "分摊行 1" });
    await chooseSplitMember(firstRow, "请选择成员");
    fireEvent.change(within(firstRow).getByRole("textbox", { name: "分摊金额（元）" }), {
      target: { value: "" },
    });

    fireEvent.click(screen.getByRole("button", { name: "保存费用分摊" }));

    expect(await screen.findByText("请选择归属成员。")).toBeInTheDocument();
    expect(screen.getByText("请输入大于 0 的金额，单位为元。")).toBeInTheDocument();
  });

  it("shows backend rejection details instead of pretending save succeeded", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((input: string | URL | Request, init?: RequestInit) => {
      const url = resolveRequestUrl(input);

      if (url === "/api/tasks/TASK-ALPHA") {
        return Promise.resolve(jsonResponse(buildTask()));
      }

      if (url === "/api/tasks/TASK-ALPHA/review-summary?actor_id=admin-1") {
        return Promise.resolve(jsonResponse(buildReviewSummary()));
      }

      if (url === "/api/invoices/INV-1/splits" && init?.method === "PUT") {
        return Promise.resolve(jsonResponse({
          items: [
            {
              id: "SPLIT-1",
              invoice_id: "INV-1",
              member_id: "2250001",
              amount_cents: 6000,
              note: "self paid",
              version: 2,
              is_active: true,
              created_at: "2026-04-28T10:00:00+08:00",
              updated_at: "2026-04-28T10:10:00+08:00",
            },
            {
              id: "SPLIT-2",
              invoice_id: "INV-1",
              member_id: "2250002",
              amount_cents: 1000,
              note: "team shared",
              version: 2,
              is_active: true,
              created_at: "2026-04-28T10:00:00+08:00",
              updated_at: "2026-04-28T10:10:00+08:00",
            },
          ],
        }));
      }

      throw new Error(`Unhandled fetch URL in split rejection test: ${url}`);
    });

    renderAdminSplitEditorRoute();

    const secondRow = within(await screen.findByRole("group", { name: "分摊行 2" }));
    fireEvent.change(secondRow.getByRole("textbox", { name: "分摊金额（元）" }), {
      target: { value: "10" },
    });

    fireEvent.click(screen.getByRole("button", { name: "保存费用分摊" }));
    const confirmDialog = await screen.findByRole("dialog");
    expect(within(confirmDialog).getByText("任务 全国邀请赛（TASK-ALPHA）的发票 INV-001 当前分摊合计比票面金额少了 ￥53.45。这表示仍有未报销金额；确认后仍会保存，但该发票会继续保留“分摊未完成”门禁。")).toBeInTheDocument();
    await act(async () => {
      fireEvent.click(within(confirmDialog).getByRole("button", { name: "确认保存分摊" }));
      await Promise.resolve();
    });
    await waitFor(() => {
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });

    expect(await screen.findByText("已保存 2 条分摊，合计 ￥70.00。任务摘要已重新拉取，当前确认状态以下方最新数据为准。")).toBeInTheDocument();
  });
});
