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
    expect(screen.getByText("操作未完成")).toBeInTheDocument();
    expect(screen.getByText("当前操作未完成，请检查填写内容后重试。")).toBeInTheDocument();
    expect(screen.getByText("费用类别第 2 项")).toBeInTheDocument();
    expect(screen.getByText("所选费用类别暂不支持。")).toBeInTheDocument();
  });
});
