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

describe("MemberTaskListPage", () => {
  beforeEach(() => {
    clearMockSession();
    setMockSession("member");
  });

  afterEach(() => {
    vi.restoreAllMocks();
    clearMockSession();
  });

  it("renders only tasks visible to the current member", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((input: string | URL | Request) => {
      const url = resolveRequestUrl(input);

      if (url === "/api/tasks") {
        return Promise.resolve(new Response(JSON.stringify([
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
            id: "TASK-HIDDEN",
            status: "reviewing",
            competition_name: "CCPC Final",
            competition_location: "成都",
            competition_start_date: "2026-06-01",
            competition_end_date: "2026-06-03",
            deadline: "2026-06-10T12:00:00+08:00",
            member_ids: ["2250009"],
            fee_categories: ["registration"],
            administrator_id: "admin-2",
            project_info: "ACM 竞赛项目",
            reimburser_info: "李管理员",
            invoice_title: "同济大学",
            tax_number: "91310113666007253C",
            created_at: "2026-04-28T08:10:00+08:00",
            updated_at: "2026-04-28T08:10:00+08:00",
          },
        ]), {
          status: 200,
          headers: {
            "Content-Type": "application/json",
          },
        }));
      }

      throw new Error(`Unhandled fetch URL in member task test: ${url}`);
    });

    const router = createMemoryRouter(routes, {
      initialEntries: ["/member"],
    });

    act(() => {
      render(<RouterProvider router={router} />);
    });

    expect(await screen.findByRole("heading", { name: "成员可提交任务" })).toBeInTheDocument();
    const taskList = screen.getByLabelText("成员可见任务列表");
    const taskCards = within(taskList).getAllByRole("article");
    expect(taskCards).toHaveLength(1);
    const [taskCard] = taskCards;
    if (!taskCard) {
      throw new Error("expected one visible member task card");
    }
    expect(within(taskCard).getByText("ICPC Xi'an Regional")).toBeInTheDocument();
    expect(within(taskCard).getAllByText("开放提交")).toHaveLength(2);
    expect(screen.queryByText("CCPC Final")).not.toBeInTheDocument();
  });

  it("shows an empty state when the current member has no visible tasks", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((input: string | URL | Request) => {
      const url = resolveRequestUrl(input);

      if (url === "/api/tasks") {
        return Promise.resolve(new Response(JSON.stringify([
          {
            id: "TASK-HIDDEN",
            status: "draft",
            competition_name: "Northwest Contest",
            competition_location: "兰州",
            competition_start_date: "2026-05-20",
            competition_end_date: "2026-05-22",
            deadline: "2026-05-30T18:00:00+08:00",
            member_ids: ["2250010"],
            fee_categories: ["registration"],
            administrator_id: "admin-1",
            project_info: "ACM 竞赛项目",
            reimburser_info: "张管理员",
            invoice_title: "同济大学",
            tax_number: "91310113666007253C",
            created_at: "2026-04-28T09:00:00+08:00",
            updated_at: "2026-04-28T09:00:00+08:00",
          },
        ]), {
          status: 200,
          headers: {
            "Content-Type": "application/json",
          },
        }));
      }

      throw new Error(`Unhandled fetch URL in member task test: ${url}`);
    });

    const router = createMemoryRouter(routes, {
      initialEntries: ["/member"],
    });

    act(() => {
      render(<RouterProvider router={router} />);
    });

    expect(await screen.findByText("当前没有可见报销任务")).toBeInTheDocument();
    expect(screen.queryByLabelText("成员可见任务列表")).not.toBeInTheDocument();
  });
});
