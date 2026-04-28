import { fireEvent, render, screen, within } from "@testing-library/react";
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

function jsonResponse(body: unknown, init: ResponseInit = {}) {
  return new Response(JSON.stringify(body), {
    status: init.status ?? 200,
    headers: {
      "Content-Type": "application/json",
      ...init.headers,
    },
  });
}

function renderMemberUploadRoute(entry = "/member/materials/upload") {
  const router = createMemoryRouter(routes, {
    initialEntries: [entry],
  });

  render(<RouterProvider router={router} />);
}

describe("MemberMaterialUploadPage", () => {
  beforeEach(() => {
    clearMockSession();
    setMockSession("member");
  });

  afterEach(() => {
    vi.restoreAllMocks();
    clearMockSession();
  });

  it("submits batch materials and shows per-file results", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation((input: string | URL | Request, init?: RequestInit) => {
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
            id: "TASK-CLOSED",
            status: "closed",
            competition_name: "CCPC Final",
            competition_location: "成都",
            competition_start_date: "2026-06-01",
            competition_end_date: "2026-06-03",
            deadline: "2026-06-10T12:00:00+08:00",
            member_ids: ["2250001"],
            fee_categories: ["registration"],
            administrator_id: "admin-1",
            project_info: "ACM 竞赛项目",
            reimburser_info: "张管理员",
            invoice_title: "同济大学",
            tax_number: "91310113666007253C",
            created_at: "2026-04-28T08:10:00+08:00",
            updated_at: "2026-04-28T08:10:00+08:00",
          },
          {
            id: "TASK-HIDDEN",
            status: "open",
            competition_name: "Hidden Contest",
            competition_location: "兰州",
            competition_start_date: "2026-05-20",
            competition_end_date: "2026-05-22",
            deadline: "2026-05-30T18:00:00+08:00",
            member_ids: ["2250999"],
            fee_categories: ["registration"],
            administrator_id: "admin-1",
            project_info: "ACM 竞赛项目",
            reimburser_info: "张管理员",
            invoice_title: "同济大学",
            tax_number: "91310113666007253C",
            created_at: "2026-04-28T09:00:00+08:00",
            updated_at: "2026-04-28T09:00:00+08:00",
          },
        ]));
      }

      if (url === "/api/tasks/TASK-OPEN/materials" && init?.method === "POST") {
        expect(init.body).toBeInstanceOf(FormData);
        const body = init.body as FormData;
        expect(body.get("submitter_id")).toBe("2250001");
        expect(body.get("channel")).toBe("web");
        expect(body.get("material_type")).toBe("invoice");
        expect(body.getAll("files")).toHaveLength(2);

        return Promise.resolve(jsonResponse(
          {
            status: "partial_success",
            items: [
              {
                id: "MAT-001",
                status: "assigned",
                task_id: "TASK-OPEN",
                submitter_id: "2250001",
                task_id_hint: null,
                submitter_id_hint: null,
                channel: "web",
                material_type: "invoice",
                storage_key: "TASK-OPEN/MAT-001-ticket.pdf",
                original_filename: "ticket.pdf",
                content_type: "application/pdf",
                size_bytes: 12,
                sha256: "a".repeat(64),
                duplicate_of: null,
                claimed_by: null,
                claimed_at: null,
                created_at: "2026-04-28T10:00:00+08:00",
              },
              {
                id: "MAT-002",
                status: "assigned",
                task_id: "TASK-OPEN",
                submitter_id: "2250001",
                task_id_hint: null,
                submitter_id_hint: null,
                channel: "web",
                material_type: "invoice",
                storage_key: "TASK-OPEN/MAT-002-ticket-copy.pdf",
                original_filename: "ticket-copy.pdf",
                content_type: "application/pdf",
                size_bytes: 12,
                sha256: "b".repeat(64),
                duplicate_of: "MAT-001",
                claimed_by: null,
                claimed_at: null,
                created_at: "2026-04-28T10:00:01+08:00",
              },
            ],
            failures: [
              {
                original_filename: "notes.txt",
                error_code: "unsupported_content_type",
                detail: "unsupported material content type: text/plain; supported content types: application/pdf, application/zip, image/jpeg, image/png, image/webp",
              },
            ],
          },
          {
            status: 207,
          },
        ));
      }

      throw new Error(`Unhandled fetch URL in member upload test: ${url}`);
    });

    renderMemberUploadRoute("/member/materials/upload?taskId=TASK-OPEN");

    expect(await screen.findByRole("heading", { name: "成员材料上传" })).toBeInTheDocument();
    expect(await screen.findByLabelText("目标任务")).toHaveValue("TASK-OPEN");
    expect(screen.queryByText("Hidden Contest")).not.toBeInTheDocument();

    const fileInput = screen.getByLabelText("上传文件");
    fireEvent.change(fileInput, {
      target: {
        files: [
          new File(["fake-pdf-1"], "ticket.pdf", { type: "application/pdf" }),
          new File(["fake-text"], "notes.txt", { type: "text/plain" }),
        ],
      },
    });

    fireEvent.click(screen.getByRole("button", { name: "上传材料" }));

    expect(await screen.findByRole("heading", { name: "上传结果" })).toBeInTheDocument();
    const successList = screen.getByLabelText("上传成功材料列表");
    expect(within(successList).getByText("材料编号 MAT-001")).toBeInTheDocument();
    expect(within(successList).getByText("材料编号 MAT-002")).toBeInTheDocument();
    expect(within(successList).getByText("与材料 MAT-001 重复")).toBeInTheDocument();
    expect(screen.getByLabelText("上传失败列表")).toHaveTextContent("notes.txt");
    expect(screen.getByText(/unsupported material content type: text\/plain/)).toBeInTheDocument();

    expect(fetchSpy).toHaveBeenCalledTimes(2);
  });

  it("shows an explicit empty state when there is no open visible task", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((input: string | URL | Request) => {
      const url = resolveRequestUrl(input);

      if (url === "/api/tasks") {
        return Promise.resolve(jsonResponse([
          {
            id: "TASK-CLOSED",
            status: "closed",
            competition_name: "CCPC Final",
            competition_location: "成都",
            competition_start_date: "2026-06-01",
            competition_end_date: "2026-06-03",
            deadline: "2026-06-10T12:00:00+08:00",
            member_ids: ["2250001"],
            fee_categories: ["registration"],
            administrator_id: "admin-1",
            project_info: "ACM 竞赛项目",
            reimburser_info: "张管理员",
            invoice_title: "同济大学",
            tax_number: "91310113666007253C",
            created_at: "2026-04-28T08:10:00+08:00",
            updated_at: "2026-04-28T08:10:00+08:00",
          },
        ]));
      }

      throw new Error(`Unhandled fetch URL in member upload test: ${url}`);
    });

    renderMemberUploadRoute();

    expect(await screen.findByText("当前没有可上传的开放任务")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "上传材料" })).not.toBeInTheDocument();
  });

  it("shows backend errors when material upload is rejected", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((input: string | URL | Request, init?: RequestInit) => {
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
            fee_categories: ["railway", "hotel"],
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

      if (url === "/api/tasks/TASK-OPEN/materials" && init?.method === "POST") {
        return Promise.resolve(jsonResponse(
          { detail: "material upload window is closed" },
          { status: 409 },
        ));
      }

      throw new Error(`Unhandled fetch URL in member upload rejection test: ${url}`);
    });

    renderMemberUploadRoute("/member/materials/upload?taskId=TASK-OPEN");

    expect(await screen.findByRole("heading", { name: "成员材料上传" })).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("上传文件"), {
      target: {
        files: [new File(["fake-pdf"], "ticket.pdf", { type: "application/pdf" })],
      },
    });

    fireEvent.click(screen.getByRole("button", { name: "上传材料" }));

    expect(await screen.findByRole("heading", { name: "接口请求失败" })).toBeInTheDocument();
    expect(screen.getByText("material upload window is closed")).toBeInTheDocument();
  });
});
