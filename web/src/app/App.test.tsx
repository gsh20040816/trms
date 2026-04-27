import { render, screen } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";

import { routes } from "./routes";

describe("web app skeleton", () => {
  it("renders role entry cards on the home page", () => {
    const router = createMemoryRouter(routes, {
      initialEntries: ["/"],
    });

    render(<RouterProvider router={router} />);

    expect(screen.getByRole("heading", { name: "报销收集前端骨架已建立" })).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: "进入占位页" })).toHaveLength(3);
    expect(screen.getByText("管理员后台")).toBeInTheDocument();
  });

  it("keeps a dedicated admin placeholder route", () => {
    const router = createMemoryRouter(routes, {
      initialEntries: ["/admin"],
    });

    render(<RouterProvider router={router} />);

    expect(screen.getByRole("heading", { name: "管理员后台" })).toBeInTheDocument();
    expect(screen.getByText("当前页面只用于固化路由边界。真实认证与角色入口占位将在下一任务实现。")).toBeInTheDocument();
  });
});
