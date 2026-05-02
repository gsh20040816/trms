import { expect, test } from "@playwright/test";
import { execFile } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { promisify } from "node:util";

const baseUrl = process.env.TRMS_UX_BASE_URL ?? "http://127.0.0.1:4173";
const apiBaseUrl = process.env.TRMS_UX_API_BASE_URL ?? "http://127.0.0.1:9877/api";
const dataRoot = process.env.TRMS_UX_DATA_ROOT ?? "tmp/ux-real-data";
const artifactRoot = process.env.TRMS_UX_ARTIFACT_ROOT ?? "test-artifacts/ux";
const uxRuntimeRoot = process.env.TRMS_UX_RUNTIME_ROOT ?? "tmp/ux-runtime";
const uxDatabaseUrl = process.env.DATABASE_URL ?? `sqlite:///./${uxRuntimeRoot}/ux-test.db`;
const uxMaterialStorageDir = process.env.MATERIAL_STORAGE_DIR ?? `./${uxRuntimeRoot}/materials`;
const uxDotenvPath = process.env.TRMS_DOTENV_PATH ?? `./${uxRuntimeRoot}/ux-empty.env`;
const execFileAsync = promisify(execFile);

const taskFiles = {
  wuhanInvoice: `${dataRoot}/武汉/报名费/ICPC武汉_同济大学_于离别之朝束起约定之花.pdf`,
  wuhanInvite: `${dataRoot}/武汉/50thICPC邀请函（武汉）.pdf`,
  taxiInvoice: `${dataRoot}/沈阳/【享道出行-49.34元-1个行程】高德打车电子发票.pdf`,
  itineraryPng: `${dataRoot}/沈阳/沈阳-上海1079.png`,
};

const password = "UxTestPass123";

function ensureDir(dirPath) {
  fs.mkdirSync(dirPath, { recursive: true });
}

function writeJsonArtifact(filename, payload) {
  ensureDir(artifactRoot);
  fs.writeFileSync(path.join(artifactRoot, filename), JSON.stringify(payload, null, 2), "utf-8");
}

function buildUxWorkerEnv() {
  const providerEnvPrefixes = ["TRMS_LLM_", "TRMS_TEXT_LLM_", "TRMS_VLM_"];
  const inheritedEnv = Object.fromEntries(
    Object.entries(process.env).filter(([key, value]) => (
      value !== undefined && !providerEnvPrefixes.some((prefix) => key.startsWith(prefix))
    )),
  );

  return {
    ...inheritedEnv,
    TRMS_ENV: "development",
    TRMS_DOTENV_PATH: uxDotenvPath,
    DATABASE_URL: uxDatabaseUrl,
    TRMS_STORAGE_BACKEND: "local",
    MATERIAL_STORAGE_DIR: uxMaterialStorageDir,
    TRMS_ASYNC_JOB_MODE: "worker",
    TRMS_AUTH_ALLOW_ADMIN_SELF_REGISTER: "true",
  };
}

async function runUxWorkerOnce() {
  const { stdout, stderr } = await execFileAsync(
    "uv",
    ["run", "python", "-m", "trms_backend", "worker", "--once"],
    {
      cwd: path.resolve("."),
      env: buildUxWorkerEnv(),
      timeout: 120_000,
    },
  );
  writeJsonArtifact("ux-worker-once.json", { stdout, stderr });
}

function sanitizeSlug(value) {
  return value.replace(/[^a-zA-Z0-9_-]+/g, "-");
}

function buildTinyPdfBytes(text) {
  const stream = `BT /F1 12 Tf 72 720 Td (${text}) Tj ET`;
  const objects = [
    "<< /Type /Catalog /Pages 2 0 R >>",
    "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
    "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
    "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    `<< /Length ${stream.length} >>\nstream\n${stream}\nendstream`,
  ];
  let body = "%PDF-1.4\n";
  const offsets = [0];
  for (let index = 0; index < objects.length; index += 1) {
    offsets.push(body.length);
    body += `${index + 1} 0 obj\n${objects[index]}\nendobj\n`;
  }
  const xrefOffset = body.length;
  body += `xref\n0 ${objects.length + 1}\n`;
  body += "0000000000 65535 f \n";
  for (let index = 1; index < offsets.length; index += 1) {
    body += `${String(offsets[index]).padStart(10, "0")} 00000 n \n`;
  }
  body += `trailer << /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xrefOffset}\n%%EOF\n`;
  return new TextEncoder().encode(body);
}

async function takeStepScreenshot(page, filename) {
  ensureDir(artifactRoot);
  await page.screenshot({
    path: path.join(artifactRoot, filename),
    fullPage: true,
  });
}

async function expectToast(page, text) {
  await expect(page.getByText(text)).toBeVisible();
}

async function waitForMaterialUploadResponse(page, taskId) {
  return page.waitForResponse((response) => {
    const request = response.request();
    return request.method() === "POST"
      && response.url() === `${apiBaseUrl}/tasks/${taskId}/materials`;
  }, { timeout: 60_000 });
}

async function addMemberTag(page, value) {
  const input = page.getByLabel("成员名单");
  await input.fill(value);
  await input.press("Enter");
}

async function registerAndLogin(page, {
  username,
  role = null,
  displayName,
  actorId,
  memberCode = null,
}) {
  const expectedPathPrefix = role === "管理员" ? "/admin" : role === "系统管理员" ? "/system" : "/member";
  await page.goto(`${baseUrl}/login`);
  await page.getByRole("tab", { name: "注册" }).click();
  const authForm = page.getByRole("form", { name: "账号登录注册表单" });
  await authForm.getByLabel("用户名").fill(username);
  await authForm.getByLabel("密码").fill(password);
  if (role) {
    await authForm.getByLabel("角色").click();
    await page.getByRole("option", { name: role, exact: true }).click();
  }
  if (displayName) {
    await authForm.getByLabel("显示名称").fill(displayName);
  }
  if (actorId) {
    await authForm.getByLabel("身份编号").fill(actorId);
  }
  if (memberCode !== null) {
    await authForm.getByLabel("成员编号").fill(memberCode);
  }
  await authForm.getByRole("button", { name: "注册并登录" }).click();
  await expect(page).toHaveURL(new RegExp(expectedPathPrefix));
}

async function login(page, { username, expectedPathPrefix = "/member" }) {
  await page.goto(`${baseUrl}/login`);
  await page.getByLabel("用户名").fill(username);
  await page.getByLabel("密码").fill(password);
  await page.getByRole("button", { name: "登录" }).click();
  await expect(page).toHaveURL(new RegExp(expectedPathPrefix));
}

async function apiRequest(pathname, options = {}) {
  const response = await fetch(`${apiBaseUrl}${pathname}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers ?? {}),
    },
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`API ${pathname} failed: ${response.status} ${detail}`);
  }
  if (response.status === 204) {
    return null;
  }
  return response.json();
}

async function registerUserViaApi({
  username,
  role,
  displayName,
  actorId,
  memberCode = null,
}) {
  try {
    return await apiRequest("/auth/register", {
      method: "POST",
      body: JSON.stringify({
        username,
        password,
        role,
        display_name: displayName,
        actor_id: actorId,
        member_code: memberCode,
      }),
    });
  } catch (error) {
    if (!String(error).includes("409")) {
      throw error;
    }
    return apiRequest("/auth/login", {
      method: "POST",
      body: JSON.stringify({
        username,
        password,
      }),
    });
  }
}

async function createTaskViaApi(adminSession, payload) {
  return apiRequest("/tasks", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${adminSession.access_token}`,
    },
    body: JSON.stringify(payload),
  });
}

async function patchTaskStatusViaApi(adminSession, taskId, targetStatus) {
  return apiRequest(`/tasks/${taskId}/status`, {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${adminSession.access_token}`,
    },
    body: JSON.stringify({ target_status: targetStatus }),
  });
}

async function uploadMaterialViaApi(session, taskId, {
  filename,
  materialType,
  submitterId,
  contentType,
  content,
}) {
  const formData = new FormData();
  formData.set("channel", "web");
  formData.set("material_type", materialType);
  formData.set("submitter_id", submitterId);
  formData.append("files", new File([content], filename, { type: contentType }));

  const response = await fetch(`${apiBaseUrl}/tasks/${taskId}/materials`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${session.access_token}`,
    },
    body: formData,
  });
  if (!response.ok) {
    throw new Error(`upload material failed: ${response.status} ${await response.text()}`);
  }
  const body = await response.json();
  return body.items[0];
}

async function listRecognitionTasksViaApi(session, materialId) {
  return apiRequest(`/materials/${materialId}/recognition-tasks`, {
    headers: {
      Authorization: `Bearer ${session.access_token}`,
    },
  });
}

async function createRecognitionTaskViaApi(session, materialId) {
  return apiRequest(`/materials/${materialId}/recognition-tasks`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${session.access_token}`,
    },
  });
}

async function patchRecognitionStatusViaApi(adminSession, recognitionTaskId, payload) {
  return apiRequest(`/recognition-tasks/${recognitionTaskId}/status`, {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${adminSession.access_token}`,
    },
    body: JSON.stringify(payload),
  });
}

async function createInvoiceViaApi(session, materialId, payload) {
  return apiRequest(`/materials/${materialId}/invoice`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${session.access_token}`,
    },
    body: JSON.stringify(payload),
  });
}

async function replaceInvoiceSplitsViaApi(session, invoiceId, payload) {
  return apiRequest(`/invoices/${invoiceId}/splits`, {
    method: "PUT",
    headers: {
      Authorization: `Bearer ${session.access_token}`,
    },
    body: JSON.stringify(payload),
  });
}

async function confirmSplitViaApi(session, splitId, payload) {
  return apiRequest(`/splits/${splitId}/confirmation`, {
    method: "PUT",
    headers: {
      Authorization: `Bearer ${session.access_token}`,
    },
    body: JSON.stringify(payload),
  });
}

async function createExportJobViaApi(adminSession, taskId, payload) {
  return apiRequest(`/tasks/${taskId}/exports`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${adminSession.access_token}`,
    },
    body: JSON.stringify(payload),
  });
}

async function getExportJobViaApi(adminSession, exportJobId) {
  return apiRequest(`/tasks/exports/${exportJobId}`, {
    headers: {
      Authorization: `Bearer ${adminSession.access_token}`,
    },
  });
}

async function submitInvoicesViaApi(session, taskId, payload) {
  return apiRequest(`/tasks/${taskId}/invoice-submissions`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${session.access_token}`,
    },
    body: JSON.stringify(payload),
  });
}

async function createReadyWorkflowFixture() {
  const adminSession = await registerUserViaApi({
    username: "ux_fixture_admin",
    role: "admin",
    displayName: "UX Fixture Admin",
    actorId: "admin-ux-fixture",
  });
  const memberOneSession = await registerUserViaApi({
    username: "ux_fixture_member_1",
    role: "member",
    displayName: "高胜寒",
    actorId: "高胜寒",
    memberCode: "高胜寒",
  });
  const memberTwoSession = await registerUserViaApi({
    username: "ux_fixture_member_2",
    role: "member",
    displayName: "刘诗奇",
    actorId: "刘诗奇",
    memberCode: "刘诗奇",
  });

  const task = await createTaskViaApi(adminSession, {
    competition_name: "ICPC 2025 UX Fixture",
    competition_location: "武汉",
    competition_start_date: "2025-10-21",
    competition_end_date: "2025-10-21",
    deadline: "2026-05-10T18:00:00Z",
    member_ids: ["高胜寒", "刘诗奇"],
    fee_categories: ["registration", "railway"],
    administrator_id: "admin-ux-fixture",
    project_info: "UX fixture task",
    reimburser_info: "同济 ACM 实验室",
    invoice_title: "同济大学",
    tax_number: "12100000425006125J",
  });

  await patchTaskStatusViaApi(adminSession, task.id, "open");

  const invoiceOneMaterial = await uploadMaterialViaApi(memberOneSession, task.id, {
    filename: "fixture-registration.pdf",
    materialType: "invoice",
    submitterId: "高胜寒",
    contentType: "application/pdf",
    content: fs.readFileSync(taskFiles.wuhanInvoice),
  });
  const invoiceTwoMaterial = await uploadMaterialViaApi(memberOneSession, task.id, {
    filename: "fixture-railway.pdf",
    materialType: "invoice",
    submitterId: "高胜寒",
    contentType: "application/pdf",
    content: fs.readFileSync(taskFiles.taxiInvoice),
  });
  const inviteMaterial = await uploadMaterialViaApi(memberOneSession, task.id, {
    filename: "fixture-notice.pdf",
    materialType: "competition_notice",
    submitterId: "高胜寒",
    contentType: "application/pdf",
    content: buildTinyPdfBytes("ICPC UX fixture competition notice"),
  });

  const recognitionOne = await createRecognitionTaskViaApi(adminSession, invoiceOneMaterial.id);
  const recognitionTwo = await createRecognitionTaskViaApi(adminSession, invoiceTwoMaterial.id);
  const inviteRecognition = await createRecognitionTaskViaApi(adminSession, inviteMaterial.id);

  await patchRecognitionStatusViaApi(
    adminSession,
    recognitionOne.item.id,
    {
      target_status: "succeeded",
      result: {
        raw_response: { provider: "ux-fixture", mode: "manual" },
        recognized_fields: {
          buyer_name: { value: "同济大学", source: "manual", confidence: 1, status: "recognized" },
          tax_number: { value: "12100000425006125J", source: "manual", confidence: 1, status: "recognized" },
        },
      },
    },
  );
  await patchRecognitionStatusViaApi(
    adminSession,
    recognitionTwo.item.id,
    {
      target_status: "succeeded",
      result: {
        raw_response: { provider: "ux-fixture", mode: "manual" },
        recognized_fields: {
          buyer_name: { value: "同济大学", source: "manual", confidence: 1, status: "recognized" },
          tax_number: { value: "12100000425006125J", source: "manual", confidence: 1, status: "recognized" },
        },
      },
    },
  );
  await patchRecognitionStatusViaApi(
    adminSession,
    inviteRecognition.item.id,
    {
      target_status: "succeeded",
      result: {
        raw_response: { provider: "ux-fixture", mode: "manual" },
        recognized_fields: {
          buyer_name: { value: "同济大学", source: "manual", confidence: 1, status: "recognized" },
          tax_number: { value: "12100000425006125J", source: "manual", confidence: 1, status: "recognized" },
        },
      },
    },
  );

  const invoiceOne = await createInvoiceViaApi(adminSession, invoiceOneMaterial.id, {
    actor_id: "admin-ux-fixture",
    invoice_number: "UX-FIX-REG-001",
    issue_date: "2025-10-21",
    transaction_time: "2025-10-21T08:00:00Z",
    buyer_name: "同济大学",
    tax_number: "12100000425006125J",
    seller_name: "ICPC",
    amount_cents: 90000,
    expense_type: "registration",
  });
  const invoiceTwo = await createInvoiceViaApi(adminSession, invoiceTwoMaterial.id, {
    actor_id: "admin-ux-fixture",
    invoice_number: "UX-FIX-RAIL-001",
    issue_date: "2025-10-21",
    transaction_time: "2025-10-21T09:00:00Z",
    buyer_name: "同济大学",
    tax_number: "12100000425006125J",
    seller_name: "高德打车",
    amount_cents: 4934,
    expense_type: "railway",
  });

  const pendingMaterial = await uploadMaterialViaApi(memberOneSession, task.id, {
    filename: "fixture-itinerary.png",
    materialType: "itinerary",
    submitterId: "高胜寒",
    contentType: "image/png",
    content: fs.readFileSync(taskFiles.itineraryPng),
  });
  const pendingRecognition = await createRecognitionTaskViaApi(adminSession, pendingMaterial.id);
  await patchRecognitionStatusViaApi(
    adminSession,
    pendingRecognition.item.id,
    {
      target_status: "succeeded",
      result: {
        raw_response: { provider: "ux-fixture", mode: "manual" },
        recognized_fields: {
          buyer_name: { value: "同济大学", source: "manual", confidence: 1, status: "recognized" },
          tax_number: { value: "12100000425006125J", source: "manual", confidence: 1, status: "recognized" },
        },
      },
    },
  );

  await apiRequest(`/invoices/${invoiceOne.invoice.id}/supporting-materials/${inviteMaterial.id}`, {
    method: "PUT",
    headers: {
      Authorization: `Bearer ${adminSession.access_token}`,
    },
  });

  const invoiceOneSplits = await replaceInvoiceSplitsViaApi(memberOneSession, invoiceOne.invoice.id, {
    actor_id: "高胜寒",
    items: [
      { member_id: "高胜寒", amount_cents: 90000, note: "registration self paid" },
    ],
  });
  const invoiceTwoSplits = await replaceInvoiceSplitsViaApi(memberOneSession, invoiceTwo.invoice.id, {
    actor_id: "高胜寒",
    items: [
      { member_id: "高胜寒", amount_cents: 4934, note: "railway self paid" },
    ],
  });

  await confirmSplitViaApi(memberOneSession, invoiceOneSplits.items[0].id, {
    actor_id: "高胜寒",
    member_id: "高胜寒",
    status: "confirmed",
  });
  await confirmSplitViaApi(memberOneSession, invoiceTwoSplits.items[0].id, {
    actor_id: "高胜寒",
    member_id: "高胜寒",
    status: "confirmed",
  });

  const fixture = {
    admin: { username: "ux_fixture_admin" },
    member: { username: "ux_fixture_member_1" },
    observer: { username: "ux_fixture_member_2" },
    taskId: task.id,
    invoiceIds: {
      registration: invoiceOne.invoice.id,
      railway: invoiceTwo.invoice.id,
    },
    materialIds: {
      pending: pendingMaterial.id,
    },
    exportJobId: null,
  };
  writeJsonArtifact("ux-ready-workflow-fixture.json", fixture);
  return fixture;
}

test.describe.serial("TRMS 真实主流程 UX 验收", () => {
  let uploadTaskId = "";
  let readyFixture = null;

  test("管理员创建并开放真实上传任务", async ({ page }) => {
    const adminUsername = `ux_admin_${Date.now()}`;
    await registerAndLogin(page, {
      username: adminUsername,
      role: "管理员",
      displayName: "UX 管理员",
      actorId: `admin-ux-${Date.now()}`,
    });

    await page.getByRole("link", { name: "创建任务" }).click();
    await page.locator("input[name='competition-name']").fill("ICPC 2025 武汉区域赛 UX 上传");
    await page.locator("input[name='competition-location']").fill("武汉");
    await page.locator("input[name='competition-start-date']").fill("2025-10-21");
    await page.locator("input[name='competition-end-date']").fill("2025-10-21");
    await page.locator("input[name='deadline']").fill("2026-05-10T18:00");
    await addMemberTag(page, "高胜寒");
    await addMemberTag(page, "刘诗奇");
    await page.locator("textarea[name='project-info']").fill("ICPC/CCPC 报销 UX 上传验收");
    await page.locator("textarea[name='reimburser-info']").fill("同济 ACM 实验室");
    await page.locator("input[name='invoice-title']").fill("同济大学");
    await page.locator("input[name='tax-number']").fill("12100000425006125J");
    await page.getByRole("button", { name: "创建草稿任务" }).click();

    await expect(page).toHaveURL(/\/admin$/);
    await page.getByRole("link", { name: "进入当前优先任务" }).click();
    await expect(page).toHaveURL(/\/admin\/tasks\//);
    uploadTaskId = page.url().split("/admin/tasks/")[1]?.split("?")[0] ?? "";
    await takeStepScreenshot(page, "ux-upload-admin-task-detail.png");
    await page.getByRole("button", { name: "切换为收集中" }).click();
    await page.getByRole("button", { name: "确认切换状态" }).click();
    await expect(page.getByText("当前任务已不在草稿状态，基础配置仅供查看；如需调整，请先处理状态回退或重新创建任务。")).toBeVisible();
  });

  test("成员真实批量上传后只处理待办，并明确看到未配置识别服务阻塞", async ({ page }) => {
    test.skip(!uploadTaskId, "上传任务未创建");

    const memberUsername = `ux_member_upload_${Date.now()}`;
    await registerAndLogin(page, {
      username: memberUsername,
      displayName: "高胜寒",
      actorId: "高胜寒",
      memberCode: "高胜寒",
    });

    await page.goto(`${baseUrl}/member/invoices/workbench?taskId=${uploadTaskId}`);
    await page.getByLabel("工作台上传文件").setInputFiles([
      taskFiles.wuhanInvoice,
      taskFiles.itineraryPng,
    ]);
    const uploadResponsePromise = waitForMaterialUploadResponse(page, uploadTaskId);
    await page.getByRole("button", { name: "上传到当前任务" }).click();
    const uploadResponse = await uploadResponsePromise;
    expect(uploadResponse.ok()).toBeTruthy();

    await expect(page.getByRole("heading", { name: "最近上传处理状态" })).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText("当前环境未配置识别服务；请联系管理员配置 provider，或直接在下面工作台手动补录发票字段。").first()).toBeVisible();
    await expect(page.getByRole("heading", { name: "待处理事项" }).first()).toBeVisible();
    await expect(page.getByRole("heading", { name: "可提交与问题发票分组" })).toBeVisible();
    await takeStepScreenshot(page, "ux-upload-member-workbench-blocked.png");
  });

  test("成员工作台覆盖多候选归票、批量提交与撤回", async ({ page }) => {
    readyFixture = await createReadyWorkflowFixture();

    await login(page, { username: readyFixture.member.username });
    await page.goto(`${baseUrl}/member/invoices/workbench?taskId=${readyFixture.taskId}`);

    await expect(page.getByRole("heading", { name: "待关联辅助材料" })).toBeVisible();
    await expect(page.getByText("当前存在多张候选发票，系统不会自动绑定")).toBeVisible();
    await page.getByRole("link", { name: "去辅助材料页处理" }).click();
    await expect(page.getByRole("heading", { name: "行程单详情" })).toBeVisible();
    await page.getByRole("checkbox", { name: /UX-FIX-RAIL-001/ }).check();
    await page.getByRole("button", { name: "更改关联" }).click();
    await expectToast(page, "辅助材料归属已更新，页面已刷新最新关联结果。");
    await takeStepScreenshot(page, "ux-ready-member-linked.png");

    await page.goto(`${baseUrl}/member/invoices/workbench?taskId=${readyFixture.taskId}`);
    await page.getByRole("button", { name: "选择全部本人发票" }).click();
    await page.getByRole("button", { name: "批量提交选中发票" }).click();
    await expect(page.getByText("批量提交成功：共处理 2 张发票。")).toBeVisible();
    await takeStepScreenshot(page, "ux-ready-member-submitted.png");

    await expect(page.getByText("已提交管理员").first()).toBeVisible();
    await page.getByRole("button", { name: "批量撤回选中发票" }).click();
    await expect(page.getByText("批量撤回成功：共处理 2 张发票。")).toBeVisible();
    await takeStepScreenshot(page, "ux-ready-member-withdrawn.png");
  });

  test("管理员查看就绪度并下载完整材料包", async ({ page }) => {
    test.skip(!readyFixture, "就绪态夹具未创建");

    await login(page, { username: readyFixture.admin.username, expectedPathPrefix: "/admin" });
    await page.goto(`${baseUrl}/admin/tasks/${readyFixture.taskId}`);

    await submitInvoicesViaApi(
      await registerUserViaApi({
        username: readyFixture.member.username,
        role: "member",
        displayName: "高胜寒",
        actorId: "高胜寒",
        memberCode: "高胜寒",
      }),
      readyFixture.taskId,
      {
        actor_id: "高胜寒",
        invoice_ids: [
          readyFixture.invoiceIds.registration,
          readyFixture.invoiceIds.railway,
        ],
      },
    );
    const adminSession = await registerUserViaApi({
      username: readyFixture.admin.username,
      role: "admin",
      displayName: "UX Fixture Admin",
      actorId: "admin-ux-fixture",
    });
    await patchTaskStatusViaApi(adminSession, readyFixture.taskId, "reviewing");
    await patchTaskStatusViaApi(adminSession, readyFixture.taskId, "ready_to_export");
    const packageJob = await createExportJobViaApi(adminSession, readyFixture.taskId, {
      actor_id: "admin-ux-fixture",
      kind: "reimbursement_package",
      format: "zip",
      parameters: {},
    });
    await runUxWorkerOnce();
    const completedPackageJob = await getExportJobViaApi(adminSession, packageJob.id);
    expect(completedPackageJob.status).toBe("succeeded");
    expect(completedPackageJob.artifact?.filename).toContain("reimbursement-package.zip");
    readyFixture.exportJobId = packageJob.id;

    await page.reload();
    await expect(page.getByRole("heading", { name: "任务就绪度总览" })).toBeVisible();
    await expect(page.getByText("当前任务已满足导出边界，可以进入导出页生成材料包。")).toBeVisible();
    await takeStepScreenshot(page, "ux-ready-admin-readiness.png");

    await page.getByRole("link", { name: "导出打印" }).first().click();
    await expect(page.getByRole("heading", { name: "导出任务页面" })).toBeVisible();
    await expect(page.getByText("最近完整材料包", { exact: true })).toBeVisible();

    const downloadPromise = page.waitForEvent("download");
    await page.getByRole("button", { name: "下载最近完整材料包" }).click();
    const download = await downloadPromise;
    const suggestedFilename = download.suggestedFilename();
    writeJsonArtifact("ux-ready-export-download.json", {
      suggestedFilename,
      exportJobId: readyFixture.exportJobId,
      taskId: readyFixture.taskId,
    });
    expect(suggestedFilename).toContain(".zip");
    await takeStepScreenshot(page, "ux-ready-admin-export.png");
  });
});
