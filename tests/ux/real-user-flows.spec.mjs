import { test, expect } from "@playwright/test";

const baseUrl = process.env.TRMS_UX_BASE_URL ?? "http://127.0.0.1:4173";
const dataRoot = process.env.TRMS_UX_DATA_ROOT ?? "tmp/ux-real-data";

const taskFiles = {
  wuhanInvoice: `${dataRoot}/武汉/报名费/ICPC武汉_同济大学_于离别之朝束起约定之花.pdf`,
  wuhanInvite: `${dataRoot}/武汉/50thICPC邀请函（武汉）.pdf`,
  taxiInvoice: `${dataRoot}/沈阳/【享道出行-49.34元-1个行程】高德打车电子发票.pdf`,
  itineraryPng: `${dataRoot}/沈阳/沈阳-上海1079.png`,
};

test.describe.serial("TRMS 真实用户 UX 基线", () => {
  let taskId = "";

  test("管理员创建并开放任务", async ({ page }) => {
    await page.goto(`${baseUrl}/login`);
    await page.getByRole("tab", { name: "注册" }).click();
    await page.getByLabel("用户名").fill("ux_admin");
    await page.getByLabel("密码").fill("UxTestPass123");
    await page.getByLabel("角色").click();
    await page.getByRole("option", { name: "管理员" }).click();
    await page.getByLabel("显示名称").fill("UX 管理员");
    await page.getByLabel("身份编号").fill("admin-ux");
    await page.getByRole("button", { name: "注册并登录" }).click();

    await page.getByRole("link", { name: "创建任务" }).click();
    await page.locator("input[name='competition-name']").fill("ICPC 2025 武汉区域赛");
    await page.locator("input[name='competition-location']").fill("武汉");
    await page.locator("input[name='competition-start-date']").fill("2025-10-21");
    await page.locator("input[name='competition-end-date']").fill("2025-10-21");
    await page.locator("input[name='deadline']").fill("2026-05-10T18:00");
    await page.getByLabel("成员 1").fill("高胜寒");
    await page.getByRole("button", { name: "新增成员项" }).click();
    await page.getByLabel("成员 2").fill("刘诗奇");
    await page.locator("label:has-text('参赛费')").click();
    await page.locator("label:has-text('市内交通')").click();
    await page.locator("textarea[name='project-info']").fill("ICPC/CCPC 比赛报销测试");
    await page.locator("textarea[name='reimburser-info']").fill("同济 ACM 实验室");
    await page.locator("input[name='invoice-title']").fill("同济大学");
    await page.locator("input[name='tax-number']").fill("12100000425006125J");
    await page.getByRole("button", { name: "创建草稿任务" }).click();

    await page.getByRole("link", { name: "完善任务" }).click();
    await expect(page).toHaveURL(/\/admin\/tasks\//);
    taskId = page.url().split("/admin/tasks/")[1] ?? "";
    taskId = taskId.split("?")[0];
    await page.getByRole("button", { name: "切换为收集中" }).click();
  });

  test("成员 A 上传发票与附件，并验证超大文件提示", async ({ page }) => {
    test.skip(!taskId, "任务未创建");

    await page.goto(`${baseUrl}/login`);
    await page.getByRole("tab", { name: "注册" }).click();
    await page.getByLabel("用户名").fill("member_gao");
    await page.getByLabel("密码").fill("UxTestPass123");
    await page.getByLabel("显示名称").fill("高胜寒");
    await page.getByLabel("身份编号").fill("高胜寒");
    await page.getByLabel("成员编号").fill("高胜寒");
    await page.getByRole("button", { name: "注册并登录" }).click();

    await page.goto(`${baseUrl}/member/invoices/workbench?taskId=${taskId}`);
    await page.getByLabel("工作台上传文件").setInputFiles(taskFiles.wuhanInvoice);
    await page.getByRole("button", { name: "上传到当前任务" }).click();

    await page.getByLabel("工作台上传材料类型").selectOption("itinerary");
    await page.getByLabel("工作台上传文件").setInputFiles(taskFiles.itineraryPng);
    await page.getByRole("button", { name: "上传到当前任务" }).click();

    await page.getByLabel("工作台上传材料类型").selectOption("competition_notice");
    await page.getByLabel("工作台上传文件").setInputFiles(taskFiles.wuhanInvite);
    await page.getByRole("button", { name: "上传到当前任务" }).click();
    await expect(page.getByText("上传文件过大")).toBeVisible();
  });

  test("成员 B 上传另一张发票，检查共享发票区域", async ({ page }) => {
    test.skip(!taskId, "任务未创建");

    await page.goto(`${baseUrl}/login`);
    await page.getByRole("tab", { name: "注册" }).click();
    await page.getByLabel("用户名").fill("member_liu");
    await page.getByLabel("密码").fill("UxTestPass123");
    await page.getByLabel("显示名称").fill("刘诗奇");
    await page.getByLabel("身份编号").fill("刘诗奇");
    await page.getByLabel("成员编号").fill("刘诗奇");
    await page.getByRole("button", { name: "注册并登录" }).click();

    await page.goto(`${baseUrl}/member/invoices/workbench?taskId=${taskId}`);
    await page.getByLabel("工作台上传文件").setInputFiles(taskFiles.taxiInvoice);
    await page.getByRole("button", { name: "上传到当前任务" }).click();

    await expect(page.getByText("任务内其他成员已上传发票")).toBeVisible();
  });
});
