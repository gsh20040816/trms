import { render, screen } from "@testing-library/react";

import { ApiErrorNotice } from "./ApiErrorNotice";
import { ApiError } from "../lib/api/client";

describe("ApiErrorNotice", () => {
  it("renders normalized field issues for user display", () => {
    const error = new ApiError(422, {
      detail: [
        {
          loc: ["body", "fee_categories", 1],
          msg: "unsupported fee categories: taxi",
        },
      ],
    });

    render(<ApiErrorNotice error={error} />);

    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(screen.getByText("接口请求失败")).toBeInTheDocument();
    expect(screen.getByText("请求参数不合法")).toBeInTheDocument();
    expect(screen.getByText("HTTP 422")).toBeInTheDocument();
    expect(screen.getByText("fee_categories.1")).toBeInTheDocument();
    expect(screen.getByText("unsupported fee categories: taxi")).toBeInTheDocument();
  });
});
