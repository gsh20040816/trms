import { fireEvent, render, screen, within } from "@testing-library/react";
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

function renderAdminCreateRoute() {
  const router = createMemoryRouter(routes, {
    initialEntries: ["/admin/tasks/new"],
  });

  render(<RouterProvider router={router} />);
}

async function selectMember(keyword: string, optionLabel: string) {
  const searchInput = screen.getByLabelText("成员名单搜索");
  fireEvent.change(searchInput, {
    target: { value: keyword },
  });
  fireEvent.click(await screen.findByRole("button", { name: optionLabel }));
}

async function fillRequiredTaskForm() {
  fireEvent.change(screen.getByLabelText("比赛名称"), {
    target: { value: "ICPC 区域赛" },
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
    target: { value: "2026-12-01T10:00" },
  });
  await selectMember("2250", "张三 / member1 / 2250001");
}

describe("admin task create page", () => {
  beforeEach(() => {
    clearMockSession();
    setMockSession("admin");
  });

  afterEach(() => {
    vi.restoreAllMocks();
    clearMockSession();
  });

  it("renders the task create form and submits successfully", async () => {
    const createdTask = {
      id: "TASK-NEW",
      status: "draft",
      competition_name: "ICPC 区域赛",
      competition_location: "上海",
      competition_start_date: "2026-11-01",
      competition_end_date: "2026-11-03",
      deadline: "2026-12-01T02:00:00.000Z",
      member_ids: ["2250001"],
      fee_categories: ["registration"],
      administrator_id: "admin-1",
      project_info: "",
      reimburser_info: "",
      invoice_title: "同济大学",
      tax_number: "12100000425006117D",
      created_at: "2026-04-28T08:00:00+08:00",
      updated_at: "2026-04-28T08:00:00+08:00",
    };

    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation((input: string | URL | Request, init?: RequestInit) => {
      const url = resolveRequestUrl(input);

      if (url === "/api/tasks" && init?.method === "POST") {
        return Promise.resolve(jsonResponse(createdTask, { status: 201 }));
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
        return Promise.resolve(jsonResponse([createdTask]));
      }
      if (url === "/api/tasks/TASK-NEW/review-summary?actor_id=admin-1") {
        return Promise.resolve(jsonResponse({
          task_id: "TASK-NEW",
          administrator_id: "admin-1",
          counts: {
            material_count: 0,
            invoice_count: 0,
            validation_count: 0,
            blocker_failed_validation_count: 0,
            split_count: 0,
            confirmed_split_count: 0,
            pending_confirmation_count: 0,
            disputed_confirmation_count: 0,
            missing_confirmation_count: 0,
            pending_recognition_count: 0,
            failed_recognition_count: 0,
            needs_confirmation_recognition_count: 0,
          },
        }));
      }
      if (url === "/api/tasks/TASK-NEW/overdue-confirmations?actor_id=admin-1") {
        return Promise.resolve(jsonResponse({
          task_id: "TASK-NEW",
          administrator_id: "admin-1",
          confirmation_deadline: "2026-12-01T02:00:00.000Z",
          is_overdue: false,
          total_overdue_members: 0,
          overdue_member_ids: [],
        }));
      }

      throw new Error(`Unhandled fetch URL in test: ${url}`);
    });

    renderAdminCreateRoute();

    expect(screen.getByRole("heading", { name: "创建报销任务" })).toBeInTheDocument();
    const moduleNav = screen.getByLabelText("管理员模块导航");
    expect(within(moduleNav).getByText("创建任务").closest("a")).toHaveAttribute("aria-current", "page");
    expect(within(moduleNav).getByText("首页总览").closest("a")).toHaveAttribute("href", "/admin");
    expect(within(moduleNav).queryByText("任务管理")).not.toBeInTheDocument();
    expect(within(moduleNav).queryByText("材料审核")).not.toBeInTheDocument();
    expect(screen.getByText("输入后会实时向后端检索候选成员。")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("输入成员姓名、用户名或学号检索")).toBeInTheDocument();
    expect(screen.getByLabelText("参赛费").closest("label")).toHaveClass("checkbox-card-surface");
    expect(screen.queryByLabelText("项目/课题信息")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("报销人信息")).not.toBeInTheDocument();
    expect(screen.getByLabelText("参赛费")).toBeChecked();
    expect(screen.getByLabelText("火车票")).toBeChecked();
    expect(screen.getByLabelText("航空费")).toBeChecked();
    expect(screen.getByLabelText("市内交通")).toBeChecked();
    expect(screen.getByLabelText("住宿费")).toBeChecked();
    expect(screen.getByLabelText("其他")).toBeChecked();

    await fillRequiredTaskForm();
    fireEvent.change(screen.getByLabelText("发票抬头"), {
      target: { value: "同济大学" },
    });
    fireEvent.change(screen.getByLabelText("税号"), {
      target: { value: "12100000425006117D" },
    });

    fireEvent.click(screen.getByRole("button", { name: "创建草稿任务" }));

    expect(await screen.findByRole("heading", { name: "按任务推进处理当前工作" })).toBeInTheDocument();
    expect((await screen.findAllByText("ICPC 区域赛")).length).toBeGreaterThan(0);

    const postCall = fetchSpy.mock.calls.find(([, init]) => init?.method === "POST");
    expect(postCall).toBeTruthy();
    const requestBody = JSON.parse((postCall?.[1]?.body as string) ?? "{}") as Record<string, unknown>;
    expect(requestBody.competition_name).toBe("ICPC 区域赛");
    expect(requestBody.member_ids).toEqual(["member-actor-1"]);
    expect(requestBody.fee_categories).toEqual([
      "registration",
      "railway",
      "airfare",
      "local_transport",
      "hotel",
      "other",
    ]);
    expect(requestBody.administrator_id).toBe("admin-1");
    expect(requestBody).not.toHaveProperty("project_info");
    expect(requestBody).not.toHaveProperty("reimburser_info");
    expect(requestBody.invoice_title).toBe("同济大学");
    expect(requestBody.tax_number).toBe("12100000425006117D");
  });

  it("defaults all fee categories to checked and still allows manual deselection", () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(() => {
      throw new Error("fetch should not be called in checkbox state test");
    });

    renderAdminCreateRoute();

    const railwayCheckbox = screen.getByLabelText("火车票");
    const hotelCheckbox = screen.getByLabelText("住宿费");
    expect(railwayCheckbox).toBeChecked();
    expect(hotelCheckbox).toBeChecked();

    fireEvent.click(railwayCheckbox);
    expect(railwayCheckbox).not.toBeChecked();
    expect(hotelCheckbox).toBeChecked();
  });

  it("blocks submit when the form contains invalid dates or blank member rows", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation(() => {
      throw new Error("fetch should not be called when frontend validation fails");
    });

    renderAdminCreateRoute();

    fireEvent.change(screen.getByLabelText("比赛名称"), {
      target: { value: "ICPC 区域赛" },
    });
    fireEvent.change(screen.getByLabelText("比赛地点"), {
      target: { value: "上海" },
    });
    fireEvent.change(screen.getByLabelText("比赛开始日期"), {
      target: { value: "2026-11-03" },
    });
    fireEvent.change(screen.getByLabelText("比赛结束日期"), {
      target: { value: "2026-11-01" },
    });
    fireEvent.change(screen.getByLabelText("提交截止时间"), {
      target: { value: "2026-12-01T10:00" },
    });

    fireEvent.click(screen.getByRole("button", { name: "创建草稿任务" }));

    expect(await screen.findByText("比赛结束日期不能早于开始日期。")).toBeInTheDocument();
    expect(screen.getByText("至少填写一名成员。")).toBeInTheDocument();
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("shows backend errors when task creation fails", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((input: string | URL | Request, init?: RequestInit) => {
      const url = resolveRequestUrl(input);

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
      if (url === "/api/tasks" && init?.method === "POST") {
        return Promise.resolve(jsonResponse(
          {
            detail: "missing invoice configuration fields: invoice_title, tax_number",
          },
          {
            status: 422,
          },
        ));
      }

      throw new Error(`Unhandled fetch URL in test: ${url}`);
    });

    renderAdminCreateRoute();

    await fillRequiredTaskForm();
    fireEvent.click(screen.getByRole("button", { name: "创建草稿任务" }));

    expect(await screen.findByRole("heading", { name: "操作未完成" })).toBeInTheDocument();
    expect(screen.getByText("任务缺少发票配置字段：invoice_title, tax_number。")).toBeInTheDocument();
  });
});
