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

function buildReadinessResponse(overrides: Partial<Record<string, unknown>> = {}) {
  return {
    task_id: "TASK-ALPHA",
    administrator_id: "admin-1",
    ready_for_export: false,
    counts: {
      pending_recognition_count: 1,
      failed_recognition_count: 0,
      needs_confirmation_recognition_count: 0,
      pending_supporting_material_linkage_count: 1,
      missing_material_count: 1,
      blocker_validation_count: 0,
      split_incomplete_count: 0,
      pending_confirmation_count: 1,
      disputed_confirmation_count: 0,
      export_blocking_reason_count: 2,
    },
    issues: [
      {
        kind: "recognition_pending",
        label: "待识别",
        count: 1,
        blocking: true,
        invoice_ids: [],
        material_ids: ["MAT-1"],
        split_ids: [],
        details: [],
      },
      {
        kind: "missing_materials",
        label: "缺失材料",
        count: 1,
        blocking: true,
        invoice_ids: ["INV-1"],
        material_ids: [],
        split_ids: [],
        details: ["参赛费缺少比赛通知。"],
      },
      {
        kind: "member_confirmation_pending",
        label: "成员未确认",
        count: 1,
        blocking: true,
        invoice_ids: [],
        material_ids: [],
        split_ids: ["SPLIT-1"],
        details: [],
      },
      {
        kind: "export_blocker",
        label: "导出阻塞原因",
        count: 2,
        blocking: true,
        invoice_ids: [],
        material_ids: [],
        split_ids: [],
        details: [
          "task must be ready_to_export or completed before real exports can be generated",
          "task still has unresolved blocker validations",
        ],
      },
    ],
    export_blocking_reasons: [
      "task must be ready_to_export or completed before real exports can be generated",
      "task still has unresolved blocker validations",
    ],
    ...overrides,
  };
}

function renderAdminTaskDetailRoute(taskId = "TASK-ALPHA") {
  const router = createMemoryRouter(routes, {
    initialEntries: [`/admin/tasks/${taskId}`],
  });

  render(<RouterProvider router={router} />);
}

describe("admin task detail page", () => {
  beforeEach(() => {
    clearMockSession();
    setMockSession("admin");
  });

  afterEach(() => {
    vi.restoreAllMocks();
    clearMockSession();
  });

  it("renders task details, members, fee categories and allowed transitions", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((input: string | URL | Request) => {
      const url = resolveRequestUrl(input);

      if (url === "/api/tasks/TASK-ALPHA") {
        return Promise.resolve(jsonResponse({
          id: "TASK-ALPHA",
          status: "closed",
          competition_name: "全国邀请赛",
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
          administrator_ids: ["admin-1", "admin-2"],
          project_info: "Project A",
          reimburser_info: "张管理员",
          invoice_title: "同济大学",
          tax_number: "91310000TEST00001",
          created_at: "2026-04-20T09:00:00+08:00",
          updated_at: "2026-04-25T10:00:00+08:00",
        }));
      }

      if (url === "/api/tasks/TASK-ALPHA/readiness?actor_id=admin-1") {
        return Promise.resolve(jsonResponse(buildReadinessResponse()));
      }

      throw new Error(`Unhandled fetch URL in detail test: ${url}`);
    });

    renderAdminTaskDetailRoute();

    expect(await screen.findAllByText("全国邀请赛")).toHaveLength(2);
    expect(screen.queryByText(/任务编号/)).not.toBeInTheDocument();
    expect(screen.queryByText("项目/课题信息")).not.toBeInTheDocument();
    expect(screen.queryByText("报销人信息")).not.toBeInTheDocument();
    expect(screen.getByText("同济大学")).toBeInTheDocument();
    expect(screen.getByText("91310000TEST00001")).toBeInTheDocument();
    expect(screen.getByText("2 名管理员")).toBeInTheDocument();
    expect(screen.getByLabelText("任务管理员列表")).toHaveTextContent("admin-1");
    expect(screen.getByLabelText("任务管理员列表")).toHaveTextContent("admin-2");
    const moduleNav = screen.getByLabelText("管理员模块导航");
    expect(within(moduleNav).getByText("任务管理").closest("a")).toHaveAttribute("aria-current", "page");
    expect(within(moduleNav).getByText("材料审核").closest("a")).toHaveAttribute("href", "/admin/tasks/TASK-ALPHA/review");
    expect(within(moduleNav).getByText("成员提醒").closest("a")).toHaveAttribute("href", "/admin/tasks/TASK-ALPHA/corrections");
    expect(within(moduleNav).queryByText("分摊确认")).not.toBeInTheDocument();
    expect(within(moduleNav).getByText("导出打印").closest("a")).toHaveAttribute("href", "/admin/tasks/TASK-ALPHA/exports");
    expect(within(moduleNav).queryByText("创建任务")).not.toBeInTheDocument();
    expect(screen.getByLabelText("当前任务上下文")).toHaveTextContent("全国邀请赛");
    expect(screen.getByRole("link", { name: "录入或更正发票" })).toHaveAttribute(
      "href",
      "/admin/tasks/TASK-ALPHA/invoices",
    );
    expect(screen.getAllByRole("link", { name: "进入材料审核" })[0]).toHaveAttribute(
      "href",
      "/admin/tasks/TASK-ALPHA/review",
    );
    expect(screen.getByRole("heading", { name: "任务就绪度总览" })).toBeInTheDocument();
    expect(screen.getByLabelText("任务摘要费用类别")).toHaveTextContent("参赛费");
    expect(screen.getByLabelText("任务就绪度统计")).toHaveTextContent("识别与归档");
    expect(screen.getByLabelText("任务就绪度统计")).toHaveTextContent("材料与校验");
    expect(screen.getByLabelText("任务就绪度统计")).toHaveTextContent("待识别");
    expect(screen.getByLabelText("导出阻塞原因")).toHaveTextContent(
      "task must be ready_to_export or completed before real exports can be generated",
    );
    const readinessQueue = screen.getByLabelText("异常优先队列");
    expect(within(readinessQueue).getByRole("link", { name: "进入材料审核" })).toHaveAttribute(
      "href",
      "/admin/tasks/TASK-ALPHA/review",
    );
    expect(within(readinessQueue).getByRole("link", { name: "进入分摊确认" })).toHaveAttribute(
      "href",
      "/admin/tasks/TASK-ALPHA/splits",
    );
    const quickActions = screen.getByLabelText("当前任务快捷入口");
    expect(within(quickActions).getByText("材料审核").closest("a")).toHaveAttribute(
      "href",
      "/admin/tasks/TASK-ALPHA/review",
    );
    expect(within(quickActions).getByText("导出打印").closest("a")).toHaveAttribute(
      "href",
      "/admin/tasks/TASK-ALPHA/exports",
    );
    expect(within(quickActions).getByText("成员提醒").closest("a")).toHaveAttribute(
      "href",
      "/admin/tasks/TASK-ALPHA/corrections",
    );

    const members = within(screen.getByLabelText("任务成员名单"));
    expect(members.getByText("张三 / member1 / 2250001")).toBeInTheDocument();
    expect(members.getByText("李四 / member2 / 2250002")).toBeInTheDocument();

    const categories = within(screen.getByLabelText("任务费用类别"));
    expect(categories.getByText("参赛费")).toBeInTheDocument();
    expect(categories.getByText("住宿费")).toBeInTheDocument();
    expect(screen.getByLabelText("参赛费").closest("label")).toHaveClass("checkbox-card-surface");

    expect(screen.getByRole("button", { name: "切换为收集中" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "切换为待复核" })).toBeInTheDocument();
  });

  it("updates task status when the backend accepts the transition", async () => {
    let statusUpdateRequestCount = 0;
    let readinessRequestCount = 0;

    vi.spyOn(globalThis, "fetch").mockImplementation((input: string | URL | Request, init?: RequestInit) => {
      const url = resolveRequestUrl(input);

      if (url === "/api/tasks/TASK-DRAFT") {
        return Promise.resolve(jsonResponse({
          id: "TASK-DRAFT",
          status: "draft",
          competition_name: "创建中任务",
          competition_location: "杭州",
          competition_start_date: "2026-06-01",
          competition_end_date: "2026-06-03",
          deadline: "2026-06-10T18:00:00+08:00",
          member_ids: ["2250001"],
          fee_categories: ["registration"],
          administrator_id: "admin-1",
          project_info: "Project Draft",
          reimburser_info: "张管理员",
          invoice_title: "同济大学",
          tax_number: "91310000TEST00001",
          created_at: "2026-04-20T09:00:00+08:00",
          updated_at: "2026-04-25T10:00:00+08:00",
        }));
      }

      if (url === "/api/tasks/TASK-DRAFT/readiness?actor_id=admin-1") {
        readinessRequestCount += 1;
        return Promise.resolve(jsonResponse(buildReadinessResponse({
          task_id: "TASK-DRAFT",
          ...(readinessRequestCount > 1
            ? {
                ready_for_export: false,
                counts: {
                  pending_recognition_count: 0,
                  failed_recognition_count: 0,
                  needs_confirmation_recognition_count: 0,
                  pending_supporting_material_linkage_count: 0,
                  missing_material_count: 0,
                  blocker_validation_count: 0,
                  split_incomplete_count: 0,
                  pending_confirmation_count: 0,
                  disputed_confirmation_count: 0,
                  export_blocking_reason_count: 1,
                },
                issues: [
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
                export_blocking_reasons: [
                  "task must be ready_to_export or completed before real exports can be generated",
                ],
              }
            : {}),
        })));
      }

      if (url === "/api/tasks/TASK-DRAFT/status" && init?.method === "PATCH") {
        statusUpdateRequestCount += 1;
        expect(init.body).toBe(JSON.stringify({ target_status: "open" }));
        return Promise.resolve(jsonResponse({
          id: "TASK-DRAFT",
          status: "open",
          competition_name: "创建中任务",
          competition_location: "杭州",
          competition_start_date: "2026-06-01",
          competition_end_date: "2026-06-03",
          deadline: "2026-06-10T18:00:00+08:00",
          member_ids: ["2250001"],
          fee_categories: ["registration"],
          administrator_id: "admin-1",
          project_info: "Project Draft",
          reimburser_info: "张管理员",
          invoice_title: "同济大学",
          tax_number: "91310000TEST00001",
          created_at: "2026-04-20T09:00:00+08:00",
          updated_at: "2026-04-26T10:00:00+08:00",
        }));
      }

      throw new Error(`Unhandled fetch URL in detail status test: ${url}`);
    });

    renderAdminTaskDetailRoute("TASK-DRAFT");

    const openButton = await screen.findByRole("button", { name: "切换为收集中" });
    await act(async () => {
      fireEvent.click(openButton);
      await Promise.resolve();
    });
    const confirmDialog = await screen.findByRole("dialog");
    expect(within(confirmDialog).getByText("任务 创建中任务 将从草稿切换为收集中。请确认当前阶段的成员提交流程、复核进度和导出准备度都已符合预期。")).toBeInTheDocument();
    await act(async () => {
      fireEvent.click(within(confirmDialog).getByRole("button", { name: "保留当前状态" }));
      await Promise.resolve();
    });
    await waitFor(() => {
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });

    expect(statusUpdateRequestCount).toBe(0);
    expect(screen.queryByText("当前状态：收集中")).not.toBeInTheDocument();

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "切换为收集中" }));
      await Promise.resolve();
    });
    const secondConfirmDialog = await screen.findByRole("dialog");
    await act(async () => {
      fireEvent.click(within(secondConfirmDialog).getByRole("button", { name: "确认切换状态" }));
      await Promise.resolve();
    });
    await waitFor(() => {
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });

    expect((await screen.findAllByText("当前状态：收集中")).length).toBeGreaterThan(0);
    expect(statusUpdateRequestCount).toBe(1);
    expect(screen.getByRole("button", { name: "切换为草稿" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "切换为已截止" })).toBeInTheDocument();
  });

  it("allows saving draft task basic configuration", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((input: string | URL | Request, init?: RequestInit) => {
      const url = resolveRequestUrl(input);

      if (url === "/api/tasks/TASK-DRAFT-EDIT" && init?.method === "PUT") {
        expect(init.body).toBe(JSON.stringify({
          competition_name: "已更新任务",
          competition_location: "上海",
          competition_start_date: "2026-08-01",
          competition_end_date: "2026-08-03",
          deadline: "2026-08-10T10:00:00.000Z",
          member_ids: ["2250001", "2250002"],
          administrator_id: "admin-1",
          administrator_ids: ["admin-1", "admin-2"],
          fee_categories: ["registration", "hotel"],
          invoice_title: "同济大学",
          tax_number: "91310000TEST00001",
        }));
        return Promise.resolve(jsonResponse({
          id: "TASK-DRAFT-EDIT",
          status: "draft",
          competition_name: "已更新任务",
          competition_location: "上海",
          competition_start_date: "2026-08-01",
          competition_end_date: "2026-08-03",
          deadline: "2026-08-10T10:00:00.000Z",
          member_ids: ["2250001", "2250002"],
          fee_categories: ["registration", "hotel"],
          administrator_id: "admin-1",
          administrator_ids: ["admin-1", "admin-2"],
          project_info: "Project After",
          reimburser_info: "张管理员",
          invoice_title: "同济大学",
          tax_number: "91310000TEST00001",
          created_at: "2026-04-20T09:00:00+08:00",
          updated_at: "2026-04-26T10:00:00+08:00",
        }));
      }

      if (url === "/api/tasks/TASK-DRAFT-EDIT/readiness?actor_id=admin-1") {
        return Promise.resolve(jsonResponse(buildReadinessResponse({
          task_id: "TASK-DRAFT-EDIT",
        })));
      }

      if (url === "/api/tasks/search/administrator-candidates?keyword=%E6%9D%8E&limit=10") {
        return Promise.resolve(jsonResponse({
          items: [
            {
              actor_id: "admin-2",
              username: "admin2",
              display_name: "李管理员",
              student_id: null,
            },
          ],
        }));
      }

      if (url === "/api/tasks/TASK-DRAFT-EDIT") {
        return Promise.resolve(jsonResponse({
          id: "TASK-DRAFT-EDIT",
          status: "draft",
          competition_name: "待编辑任务",
          competition_location: "上海",
          competition_start_date: "2026-08-01",
          competition_end_date: "2026-08-03",
          deadline: "2026-08-10T18:00:00+08:00",
          member_ids: ["2250001", "2250002"],
          fee_categories: ["registration", "hotel"],
          administrator_id: "admin-1",
          administrator_ids: ["admin-1"],
          project_info: "Project Before",
          reimburser_info: "张管理员",
          invoice_title: "同济大学",
          tax_number: "91310000TEST00001",
          created_at: "2026-04-20T09:00:00+08:00",
          updated_at: "2026-04-25T10:00:00+08:00",
        }));
      }

      throw new Error(`Unhandled fetch URL in detail edit test: ${url}`);
    });

    renderAdminTaskDetailRoute("TASK-DRAFT-EDIT");

    expect(await screen.findByDisplayValue("待编辑任务")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("管理员搜索"), {
      target: { value: "李" },
    });
    await act(async () => {
      await new Promise((resolve) => {
        setTimeout(resolve, 260);
      });
    });
    fireEvent.click(await screen.findByText("李管理员 / admin2"));
    expect(await screen.findByLabelText("任务管理员已选列表")).toHaveTextContent("李管理员 / admin2");
    fireEvent.change(screen.getByLabelText("比赛名称"), {
      target: { value: "已更新任务" },
    });
    fireEvent.click(screen.getByRole("button", { name: "保存任务基础配置" }));

    expect(await screen.findByDisplayValue("已更新任务")).toBeInTheDocument();
    expect(screen.queryByLabelText("项目/课题信息")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("报销人信息")).not.toBeInTheDocument();
    expect(screen.getByLabelText("任务管理员已选列表")).toHaveTextContent("李管理员 / admin2");
  });

  it("allows a secondary administrator to access the task detail page", async () => {
    clearMockSession();
    setMockSession("admin", {
      actorId: "admin-2",
      displayName: "李管理员",
      username: "admin2",
    });

    vi.spyOn(globalThis, "fetch").mockImplementation((input: string | URL | Request) => {
      const url = resolveRequestUrl(input);

      if (url === "/api/tasks/TASK-SECONDARY") {
        return Promise.resolve(jsonResponse({
          id: "TASK-SECONDARY",
          status: "reviewing",
          competition_name: "多管理员任务",
          competition_location: "上海",
          competition_start_date: "2026-08-01",
          competition_end_date: "2026-08-03",
          deadline: "2026-08-10T18:00:00+08:00",
          member_ids: ["2250001"],
          member_summaries: [
            { member_id: "2250001", username: "member1", display_name: "张三", student_id: "2250001" },
          ],
          fee_categories: ["registration"],
          administrator_id: "admin-1",
          administrator_ids: ["admin-1", "admin-2"],
          project_info: "",
          reimburser_info: "",
          invoice_title: "同济大学",
          tax_number: "91310000TEST00001",
          created_at: "2026-04-20T09:00:00+08:00",
          updated_at: "2026-04-25T10:00:00+08:00",
        }));
      }

      if (url === "/api/tasks/TASK-SECONDARY/readiness?actor_id=admin-2") {
        return Promise.resolve(jsonResponse(buildReadinessResponse({
          task_id: "TASK-SECONDARY",
          administrator_id: "admin-2",
        })));
      }

      throw new Error(`Unhandled fetch URL in secondary admin detail test: ${url}`);
    });

    renderAdminTaskDetailRoute("TASK-SECONDARY");

    expect(await screen.findByRole("heading", { name: "任务就绪度总览" })).toBeInTheDocument();
    expect(screen.queryByText("当前任务不属于此管理员")).not.toBeInTheDocument();
  });

  it("shows task config as read-only once the task is no longer draft", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((input: string | URL | Request) => {
      const url = resolveRequestUrl(input);

      if (url === "/api/tasks/TASK-CLOSED") {
        return Promise.resolve(jsonResponse({
          id: "TASK-CLOSED",
          status: "closed",
          competition_name: "已截止任务",
          competition_location: "南京",
          competition_start_date: "2026-09-01",
          competition_end_date: "2026-09-03",
          deadline: "2026-09-10T18:00:00+08:00",
          member_ids: ["2250001"],
          fee_categories: ["registration"],
          administrator_id: "admin-1",
          project_info: "Closed Project",
          reimburser_info: "张管理员",
          invoice_title: "同济大学",
          tax_number: "91310000TEST00001",
          created_at: "2026-04-20T09:00:00+08:00",
          updated_at: "2026-04-25T10:00:00+08:00",
        }));
      }

      if (url === "/api/tasks/TASK-CLOSED/readiness?actor_id=admin-1") {
        return Promise.resolve(jsonResponse(buildReadinessResponse({
          task_id: "TASK-CLOSED",
        })));
      }

      throw new Error(`Unhandled fetch URL in detail read-only test: ${url}`);
    });

    renderAdminTaskDetailRoute("TASK-CLOSED");

    expect(await screen.findByText("当前任务已不在草稿状态，基础配置仅供查看；如需调整，请先处理状态回退或重新创建任务。")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "保存任务基础配置" })).toBeDisabled();
  });

  it("shows a page-level error when the backend rejects a status transition", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((input: string | URL | Request, init?: RequestInit) => {
      const url = resolveRequestUrl(input);

      if (url === "/api/tasks/TASK-READY") {
        return Promise.resolve(jsonResponse({
          id: "TASK-READY",
          status: "ready_to_export",
          competition_name: "待导出任务",
          competition_location: "南京",
          competition_start_date: "2026-07-01",
          competition_end_date: "2026-07-03",
          deadline: "2026-07-10T18:00:00+08:00",
          member_ids: ["2250001", "2250002"],
          fee_categories: ["registration", "hotel"],
          administrator_id: "admin-1",
          project_info: "Project Ready",
          reimburser_info: "张管理员",
          invoice_title: "同济大学",
          tax_number: "91310000TEST00001",
          created_at: "2026-04-20T09:00:00+08:00",
          updated_at: "2026-04-25T10:00:00+08:00",
        }));
      }

      if (url === "/api/tasks/TASK-READY/readiness?actor_id=admin-1") {
        return Promise.resolve(jsonResponse(buildReadinessResponse({
          task_id: "TASK-READY",
        })));
      }

      if (url === "/api/tasks/TASK-READY/status" && init?.method === "PATCH") {
        return Promise.resolve(jsonResponse(
          {
            detail: "task cannot transition to completed before export completion is recorded",
          },
          { status: 409 },
        ));
      }

      throw new Error(`Unhandled fetch URL in detail rejection test: ${url}`);
    });

    renderAdminTaskDetailRoute("TASK-READY");

    fireEvent.click(await screen.findByText("切换为已完成"));
    const confirmDialog = await screen.findByRole("dialog");
    fireEvent.change(within(confirmDialog).getByLabelText("确认动作输入框"), {
      target: { value: "待导出任务" },
    });
    await act(async () => {
      fireEvent.click(within(confirmDialog).getByRole("button", { name: "确认切换状态" }));
      await Promise.resolve();
    });

    expect(await screen.findByRole("heading", { name: "操作未完成" })).toBeInTheDocument();
    expect(screen.getByText("导出完成前，任务不能切换为已完成。")).toBeInTheDocument();
  });
});
