import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";

import { ApiErrorNotice } from "../components/ApiErrorNotice";
import { PageHeader, RoleWorkspace, StatCard } from "../components/dashboard";
import { UserSearchCandidatePicker } from "../components/UserSearchCandidatePicker";
import { useSnackbar } from "../components/use-snackbar";
import { trmsApi } from "../lib/api/trms";
import type {
  SystemAiProviderConfigPayload,
  SystemDashboard,
  SystemUserRoleSummary,
} from "../lib/api/types";
import { formatUserSearchSummary, formatUserRole } from "../lib/ui-text";
import { useAuthSession } from "./auth-store";

type SystemDashboardState =
  | { status: "loading" }
  | { status: "error"; error: unknown }
  | { status: "ready"; dashboard: SystemDashboard };

type ConfigFormState = {
  invoiceTitle: string;
  taxNumber: string;
};

type ConfigFormErrors = {
  invoiceTitle?: string;
  taxNumber?: string;
};

type RecognitionProviderFormState = {
  textBaseUrl: string;
  textModel: string;
  textTimeoutSeconds: string;
  textMaxRetries: string;
  textApiKey: string;
  vlmBaseUrl: string;
  vlmModel: string;
  vlmTimeoutSeconds: string;
  vlmMaxRetries: string;
  vlmApiKey: string;
};

type RecognitionProviderFormErrors = Partial<Record<keyof RecognitionProviderFormState, string>>;

type UserRoleManagementState =
  | { status: "idle"; items: SystemUserRoleSummary[] }
  | { status: "loading"; items: SystemUserRoleSummary[] }
  | { status: "error"; items: SystemUserRoleSummary[]; error: unknown }
  | { status: "ready"; items: SystemUserRoleSummary[] };

function buildConfigFormState(dashboard: SystemDashboard): ConfigFormState {
  return {
    invoiceTitle: dashboard.global_invoice_config?.invoice_title ?? "",
    taxNumber: dashboard.global_invoice_config?.tax_number ?? "",
  };
}

function buildRecognitionProviderFormState(dashboard: SystemDashboard): RecognitionProviderFormState {
  return {
    textBaseUrl: dashboard.system_ai_provider_config.text_llm.base_url ?? "",
    textModel: dashboard.system_ai_provider_config.text_llm.model ?? "",
    textTimeoutSeconds: dashboard.system_ai_provider_config.text_llm.timeout_seconds?.toString() ?? "",
    textMaxRetries: dashboard.system_ai_provider_config.text_llm.max_retries?.toString() ?? "",
    textApiKey: "",
    vlmBaseUrl: dashboard.system_ai_provider_config.vlm.base_url ?? "",
    vlmModel: dashboard.system_ai_provider_config.vlm.model ?? "",
    vlmTimeoutSeconds: dashboard.system_ai_provider_config.vlm.timeout_seconds?.toString() ?? "",
    vlmMaxRetries: dashboard.system_ai_provider_config.vlm.max_retries?.toString() ?? "",
    vlmApiKey: "",
  };
}

function validateConfigForm(formState: ConfigFormState) {
  const errors: ConfigFormErrors = {};
  if (formState.invoiceTitle.trim().length === 0) {
    errors.invoiceTitle = "发票抬头不能为空。";
  }
  if (formState.taxNumber.trim().length === 0) {
    errors.taxNumber = "税号不能为空。";
  }
  return errors;
}

function parseOptionalNumber(
  rawValue: string,
  fieldLabel: string,
  integerOnly = false,
): { value: number | null; error?: string } {
  const normalized = rawValue.trim();
  if (!normalized) {
    return { value: null };
  }
  const parsed = Number(normalized);
  if (!Number.isFinite(parsed)) {
    return { value: null, error: `${fieldLabel}必须是数字。` };
  }
  if (parsed <= 0 && fieldLabel.includes("超时")) {
    return { value: null, error: `${fieldLabel}必须大于 0。` };
  }
  if (parsed < 0 && fieldLabel.includes("重试")) {
    return { value: null, error: `${fieldLabel}不能小于 0。` };
  }
  if (integerOnly && !Number.isInteger(parsed)) {
    return { value: null, error: `${fieldLabel}必须是整数。` };
  }
  return { value: parsed };
}

function validateRecognitionProviderForm(formState: RecognitionProviderFormState) {
  const errors: RecognitionProviderFormErrors = {};

  for (const [fieldKey, fieldLabel, integerOnly] of [
    ["textTimeoutSeconds", "文本 LLM 超时秒数", false],
    ["textMaxRetries", "文本 LLM 重试次数", true],
    ["vlmTimeoutSeconds", "VLM 超时秒数", false],
    ["vlmMaxRetries", "VLM 重试次数", true],
  ] as const) {
    const parsed = parseOptionalNumber(formState[fieldKey], fieldLabel, integerOnly);
    if (parsed.error) {
      errors[fieldKey] = parsed.error;
    }
  }

  return errors;
}

function buildRecognitionProviderPayload(
  formState: RecognitionProviderFormState,
): SystemAiProviderConfigPayload {
  return {
    text_llm: {
      base_url: formState.textBaseUrl.trim() || null,
      model: formState.textModel.trim() || null,
      timeout_seconds: parseOptionalNumber(formState.textTimeoutSeconds, "文本 LLM 超时秒数").value,
      max_retries: parseOptionalNumber(formState.textMaxRetries, "文本 LLM 重试次数", true).value,
      ...(formState.textApiKey.trim() ? { api_key: formState.textApiKey.trim() } : {}),
    },
    vlm: {
      base_url: formState.vlmBaseUrl.trim() || null,
      model: formState.vlmModel.trim() || null,
      timeout_seconds: parseOptionalNumber(formState.vlmTimeoutSeconds, "VLM 超时秒数").value,
      max_retries: parseOptionalNumber(formState.vlmMaxRetries, "VLM 重试次数", true).value,
      ...(formState.vlmApiKey.trim() ? { api_key: formState.vlmApiKey.trim() } : {}),
    },
  };
}

function renderBooleanChip(value: boolean, trueLabel: string, falseLabel: string) {
  return (
    <Chip
      label={value ? trueLabel : falseLabel}
      color={value ? "success" : "default"}
      size="small"
      variant={value ? "filled" : "outlined"}
    />
  );
}

function resolveBrowserTimeZone() {
  try {
    const timeZone = Intl.DateTimeFormat().resolvedOptions().timeZone?.trim();
    return timeZone || "浏览器未提供";
  } catch {
    return "浏览器未提供";
  }
}

export function SystemAdminDashboardPage() {
  const session = useAuthSession();
  const { showError, showSuccess } = useSnackbar();
  const [state, setState] = useState<SystemDashboardState>({ status: "loading" });
  const [formState, setFormState] = useState<ConfigFormState>({
    invoiceTitle: "",
    taxNumber: "",
  });
  const [formErrors, setFormErrors] = useState<ConfigFormErrors>({});
  const [recognitionProviderFormState, setRecognitionProviderFormState] = useState<RecognitionProviderFormState>({
    textBaseUrl: "",
    textModel: "",
    textTimeoutSeconds: "",
    textMaxRetries: "",
    textApiKey: "",
    vlmBaseUrl: "",
    vlmModel: "",
    vlmTimeoutSeconds: "",
    vlmMaxRetries: "",
    vlmApiKey: "",
  });
  const [recognitionProviderFormErrors, setRecognitionProviderFormErrors] = useState<RecognitionProviderFormErrors>({});
  const [isSaving, setIsSaving] = useState(false);
  const [isSavingRecognitionProviders, setIsSavingRecognitionProviders] = useState(false);
  const [saveError, setSaveError] = useState<unknown>(null);
  const [userSearchKeyword, setUserSearchKeyword] = useState("");
  const [userRoleManagementState, setUserRoleManagementState] = useState<UserRoleManagementState>({
    status: "idle",
    items: [],
  });
  const [selectedSystemUser, setSelectedSystemUser] = useState<SystemUserRoleSummary | null>(null);
  const [grantingUserId, setGrantingUserId] = useState<string | null>(null);
  const userSearchTimerRef = useRef<number | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadDashboard() {
      if (!session || session.role !== "system_admin") {
        return;
      }

      setState({ status: "loading" });
      setSaveError(null);

      try {
        const dashboard = await trmsApi.getSystemDashboard();
        if (cancelled) {
          return;
        }
        setState({ status: "ready", dashboard });
        setFormState(buildConfigFormState(dashboard));
        setRecognitionProviderFormState(buildRecognitionProviderFormState(dashboard));
        setRecognitionProviderFormErrors({});
      } catch (error) {
        if (cancelled) {
          return;
        }
        setState({ status: "error", error });
      }
    }

    void loadDashboard();

    return () => {
      cancelled = true;
    };
  }, [session]);

  useEffect(() => (
    () => {
      if (userSearchTimerRef.current !== null) {
        window.clearTimeout(userSearchTimerRef.current);
      }
    }
  ), []);

  if (!session || session.role !== "system_admin") {
    return null;
  }

  const dashboard = state.status === "ready" ? state.dashboard : null;
  const validationErrors = validateConfigForm(formState);
  const hasValidationErrors = Object.keys(validationErrors).length > 0;
  const recognitionProviderValidationErrors = validateRecognitionProviderForm(recognitionProviderFormState);
  const hasRecognitionProviderValidationErrors = Object.keys(recognitionProviderValidationErrors).length > 0;
  const browserTimeZone = resolveBrowserTimeZone();
  const summaryCards = dashboard ? [
    {
      label: "成员账号",
      value: dashboard.user_counts.member,
      description: "已存在的成员角色账号数量。",
    },
    {
      label: "管理员账号",
      value: dashboard.user_counts.admin,
      description: "当前可处理任务的管理员角色账号数量。",
    },
    {
      label: "系统管理员",
      value: dashboard.user_counts.system_admin,
      description: "当前可维护系统配置与巡检入口的系统管理员数量。",
    },
  ] : [];

  async function handleSave() {
    const nextErrors = validateConfigForm(formState);
    setFormErrors(nextErrors);
    setSaveError(null);
    if (Object.keys(nextErrors).length > 0) {
      return;
    }

    setIsSaving(true);
    try {
      const savedConfig = await trmsApi.updateGlobalInvoiceConfig({
        invoice_title: formState.invoiceTitle.trim(),
        tax_number: formState.taxNumber.trim(),
      });
      setState((current) => (
        current.status === "ready"
          ? {
            status: "ready",
            dashboard: {
              ...current.dashboard,
              global_invoice_config: savedConfig,
            },
          }
          : current
      ));
      setFormState({
        invoiceTitle: savedConfig.invoice_title,
        taxNumber: savedConfig.tax_number,
      });
      showSuccess("已保存全局发票配置");
    } catch (error) {
      setSaveError(error);
      showError("保存全局发票配置失败");
    } finally {
      setIsSaving(false);
    }
  }

  async function handleRecognitionProviderSave() {
    const nextErrors = validateRecognitionProviderForm(recognitionProviderFormState);
    setRecognitionProviderFormErrors(nextErrors);
    setSaveError(null);
    if (Object.keys(nextErrors).length > 0) {
      return;
    }

    setIsSavingRecognitionProviders(true);
    try {
      const savedConfig = await trmsApi.updateRecognitionProviderConfig(
        buildRecognitionProviderPayload(recognitionProviderFormState),
      );
      setState((current) => (
        current.status === "ready"
          ? {
            status: "ready",
            dashboard: {
              ...current.dashboard,
              system_ai_provider_config: savedConfig,
            },
          }
          : current
      ));
      setRecognitionProviderFormState((current) => ({
        ...current,
        textApiKey: "",
        vlmApiKey: "",
      }));
      showSuccess("已保存识别 Provider 系统配置");
    } catch (error) {
      setSaveError(error);
      showError("保存识别 Provider 系统配置失败");
    } finally {
      setIsSavingRecognitionProviders(false);
    }
  }

  function handleSystemUserKeywordChange(value: string) {
    setUserSearchKeyword(value);
    const keyword = value.trim();

    if (userSearchTimerRef.current !== null) {
      window.clearTimeout(userSearchTimerRef.current);
      userSearchTimerRef.current = null;
    }

    if (keyword.length === 0) {
      setUserRoleManagementState({
        status: "idle",
        items: [],
      });
      return;
    }

    setUserRoleManagementState((current) => ({
      status: "loading",
      items: current.items,
    }));
    userSearchTimerRef.current = window.setTimeout(() => {
      void trmsApi.searchSystemUsers(keyword)
        .then((response) => {
          setUserRoleManagementState({
            status: "ready",
            items: response.items,
          });
        })
        .catch((error) => {
          setUserRoleManagementState((current) => ({
            status: "error",
            items: current.items,
            error,
          }));
          showError("检索系统账号失败");
        })
        .finally(() => {
          userSearchTimerRef.current = null;
        });
    }, 250);
  }

  async function handleGrantAdminRole(user: SystemUserRoleSummary) {
    setGrantingUserId(user.id);
    try {
      const response = await trmsApi.grantUserAdminRole(user.id);
      const updatedUser = response.user;
      const updatedUserSummary: SystemUserRoleSummary = {
        id: updatedUser.id,
        actor_id: updatedUser.actor_id,
        username: updatedUser.username,
        display_name: updatedUser.display_name,
        student_id: updatedUser.member_code,
        roles: updatedUser.roles,
      };
      setUserRoleManagementState((current) => ({
        status: "ready",
        items: current.items.map((item) => (
          item.id === user.id
            ? updatedUserSummary
            : item
        )),
      }));
      setSelectedSystemUser(updatedUserSummary);
      if (!response.already_assigned) {
        setState((current) => (
          current.status === "ready"
            ? {
              status: "ready",
              dashboard: {
                ...current.dashboard,
                user_counts: {
                  ...current.dashboard.user_counts,
                  admin: current.dashboard.user_counts.admin + 1,
                },
              },
            }
            : current
        ));
      }
      showSuccess(
        response.already_assigned
          ? `账号 ${updatedUser.username} 已具备管理员角色`
          : `已为账号 ${updatedUser.username} 授予管理员角色`,
      );
    } catch {
      showError("授予管理员角色失败");
    } finally {
      setGrantingUserId(null);
    }
  }

  return (
    <RoleWorkspace
      header={(
        <PageHeader
          eyebrow="系统管理"
          title="系统管理员工作台"
          description="集中维护全局发票配置，并查看当前运行环境、异步模式和渠道开关等安全可见的系统状态。"
          meta={`当前系统管理员：${session.displayName}`}
          actions={(
            <div className="page-actions">
              <Link className="button button-secondary" to="/">
                返回总览
              </Link>
            </div>
          )}
        />
      )}
      summary={summaryCards.length > 0 ? (
        <section className="stat-grid" aria-label="系统管理概览">
          {summaryCards.map((item) => (
            <StatCard
              key={item.label}
              label={item.label}
              value={item.value}
              description={item.description}
            />
          ))}
        </section>
      ) : undefined}
    >
      <Stack spacing={3}>
        {state.status === "loading" ? (
          <Card>
            <CardContent>
              <Typography variant="overline" color="text.secondary">
                Loading
              </Typography>
              <Typography variant="h5" sx={{ mt: 0.5 }}>
                正在加载系统管理面板
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                正在读取全局配置与运行态摘要，请稍候。
              </Typography>
            </CardContent>
          </Card>
        ) : null}

        {state.status === "error" ? <ApiErrorNotice error={state.error} /> : null}
        {saveError ? <ApiErrorNotice error={saveError} /> : null}

        {dashboard ? (
          <>
            <Card>
              <CardContent>
                <Stack direction="row" justifyContent="space-between" alignItems="flex-start" spacing={2}>
                  <Box>
                    <Typography variant="overline" color="text.secondary">
                      User Roles
                    </Typography>
                    <Typography variant="h5" sx={{ mt: 0.5 }}>
                      用户身份管理
                    </Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                      在这里检索现有账号，并把成员或普通账号追加为管理员角色。真实多角色来源应走这里的受控授权，而不是公开注册时直接写入多角色数组。
                    </Typography>
                  </Box>
                  <Chip label="仅系统管理员" color="primary" size="small" variant="outlined" />
                </Stack>

                <Stack spacing={3} sx={{ mt: 3 }}>
                  <UserSearchCandidatePicker
                    label="检索账号"
                    value={userSearchKeyword}
                    onChange={handleSystemUserKeywordChange}
                    placeholder="输入用户名、显示名称、学号或业务标识"
                    helperText={
                      userRoleManagementState.status === "loading"
                        ? "正在检索系统账号..."
                        : "输入后会实时向后端检索已有账号；选择一个账号后再执行授予管理员。"
                    }
                    showOptions={userSearchKeyword.trim().length > 0}
                    options={userRoleManagementState.items.map((user) => ({
                      key: user.id,
                      label: formatUserSearchSummary(user),
                      onSelect: () => {
                        setSelectedSystemUser(user);
                        setUserSearchKeyword("");
                      },
                    }))}
                    listAriaLabel="系统账号候选列表"
                    searchErrorText={
                      userRoleManagementState.status === "error"
                        ? "系统账号检索失败，请稍后重试。"
                        : null
                    }
                    emptyText={userRoleManagementState.status !== "loading" ? "没有匹配的系统账号。" : ""}
                  />

                  <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap" aria-label="已选系统账号列表">
                    {selectedSystemUser ? (
                      <Chip
                        label={formatUserSearchSummary(selectedSystemUser)}
                        onDelete={() => {
                          setSelectedSystemUser(null);
                        }}
                      />
                    ) : null}
                  </Stack>

                  {selectedSystemUser ? (
                    <Card variant="outlined">
                      <CardContent>
                        <Stack direction={{ xs: "column", md: "row" }} justifyContent="space-between" spacing={2}>
                          <Box>
                            <Typography variant="subtitle1">{formatUserSearchSummary(selectedSystemUser)}</Typography>
                            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                              业务标识：{selectedSystemUser.actor_id}
                            </Typography>
                            <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap" sx={{ mt: 1 }}>
                              {selectedSystemUser.roles.map((role) => (
                                <Chip key={role} size="small" label={formatUserRole(role)} />
                              ))}
                            </Stack>
                          </Box>
                          <Stack direction="row" spacing={1} alignItems="flex-start">
                            <Button
                              variant="outlined"
                              disabled={
                                grantingUserId === selectedSystemUser.id
                                || selectedSystemUser.roles.includes("admin")
                                || selectedSystemUser.roles.includes("system_admin")
                              }
                              onClick={() => {
                                void handleGrantAdminRole(selectedSystemUser);
                              }}
                            >
                              {grantingUserId === selectedSystemUser.id
                                ? "授权中..."
                                : selectedSystemUser.roles.includes("system_admin")
                                  ? "系统管理员"
                                  : selectedSystemUser.roles.includes("admin")
                                    ? "已是管理员"
                                    : "授予管理员"}
                            </Button>
                          </Stack>
                        </Stack>
                      </CardContent>
                    </Card>
                  ) : null}
                </Stack>
              </CardContent>
            </Card>

            <Card>
              <CardContent>
                <Stack direction="row" justifyContent="space-between" alignItems="flex-start" spacing={2}>
                  <Box>
                    <Typography variant="overline" color="text.secondary">
                      Global Invoice Config
                    </Typography>
                    <Typography variant="h5" sx={{ mt: 0.5 }}>
                      全局发票抬头与税号
                    </Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                      新建任务默认继承这里的抬头和税号；管理员仍可在具体任务内覆盖。
                    </Typography>
                  </Box>
                  {renderBooleanChip(
                    dashboard.global_invoice_config !== null,
                    "已配置默认值",
                    "尚未配置默认值",
                  )}
                </Stack>

                <Box
                  sx={{
                    display: "grid",
                    gridTemplateColumns: { xs: "1fr", md: "repeat(2, minmax(0, 1fr))" },
                    gap: 2,
                    mt: 3,
                  }}
                >
                  <TextField
                    label="发票抬头"
                    value={formState.invoiceTitle}
                    onChange={(event) => {
                      setFormState((current) => ({
                        ...current,
                        invoiceTitle: event.target.value,
                      }));
                      setFormErrors((current) => ({ ...current, invoiceTitle: undefined }));
                    }}
                    error={Boolean(formErrors.invoiceTitle)}
                    helperText={formErrors.invoiceTitle}
                    fullWidth
                  />
                  <TextField
                    label="税号"
                    value={formState.taxNumber}
                    onChange={(event) => {
                      setFormState((current) => ({
                        ...current,
                        taxNumber: event.target.value,
                      }));
                      setFormErrors((current) => ({ ...current, taxNumber: undefined }));
                    }}
                    error={Boolean(formErrors.taxNumber)}
                    helperText={formErrors.taxNumber}
                    fullWidth
                  />
                </Box>

                {hasValidationErrors ? (
                  <Alert severity="warning" sx={{ mt: 2 }}>
                    请先补齐发票抬头和税号，再保存全局配置。
                  </Alert>
                ) : null}

                <Stack direction="row" justifyContent="flex-end" sx={{ mt: 3 }}>
                  <Button
                    variant="contained"
                    onClick={() => {
                      void handleSave();
                    }}
                    disabled={isSaving}
                  >
                    {isSaving ? "保存中..." : "保存全局配置"}
                  </Button>
                </Stack>
              </CardContent>
            </Card>

            <Card>
              <CardContent>
                <Stack direction="row" justifyContent="space-between" alignItems="flex-start" spacing={2}>
                  <Box>
                    <Typography variant="overline" color="text.secondary">
                      Recognition Providers
                    </Typography>
                    <Typography variant="h5" sx={{ mt: 0.5 }}>
                      文本 LLM 与 VLM 配置
                    </Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                      系统配置优先于 `.env`；当前表单留空的字段会继续回退到环境变量。API key 不回显，留空表示保持现有系统密钥不变。
                    </Typography>
                  </Box>
                  <Stack spacing={1} alignItems="flex-end">
                    {renderBooleanChip(
                      dashboard.runtime.text_llm_provider_configured,
                      "文本 LLM 已生效",
                      "文本 LLM 未生效",
                    )}
                    {renderBooleanChip(
                      dashboard.runtime.vlm_provider_configured,
                      "VLM 已生效",
                      "VLM 未生效",
                    )}
                  </Stack>
                </Stack>

                <Box
                  sx={{
                    display: "grid",
                    gridTemplateColumns: { xs: "1fr", xl: "repeat(2, minmax(0, 1fr))" },
                    gap: 3,
                    mt: 3,
                  }}
                >
                  {([
                    {
                      key: "text",
                      title: "纯文本材料 / PDF 文本提取",
                      summary: dashboard.system_ai_provider_config.text_llm,
                      baseUrlKey: "textBaseUrl",
                      modelKey: "textModel",
                      timeoutKey: "textTimeoutSeconds",
                      retryKey: "textMaxRetries",
                      apiKeyKey: "textApiKey",
                    },
                    {
                      key: "vlm",
                      title: "扫描 PDF / 图片 / 截图",
                      summary: dashboard.system_ai_provider_config.vlm,
                      baseUrlKey: "vlmBaseUrl",
                      modelKey: "vlmModel",
                      timeoutKey: "vlmTimeoutSeconds",
                      retryKey: "vlmMaxRetries",
                      apiKeyKey: "vlmApiKey",
                    },
                  ] as const).map((provider) => (
                    <Card key={provider.key} variant="outlined">
                      <CardContent>
                        <Stack spacing={2}>
                          <Stack direction="row" justifyContent="space-between" alignItems="flex-start" spacing={2}>
                            <Box>
                              <Typography variant="subtitle1">{provider.title}</Typography>
                              <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                                当前系统覆盖：{provider.summary.base_url ?? "未设置 base URL"} / {provider.summary.model ?? "未设置模型"}
                              </Typography>
                            </Box>
                            {renderBooleanChip(
                              provider.summary.api_key_configured,
                              "系统密钥已保存",
                              "系统密钥未保存",
                            )}
                          </Stack>

                          <TextField
                            label="Base URL"
                            value={recognitionProviderFormState[provider.baseUrlKey]}
                            onChange={(event) => {
                              const nextValue = event.target.value;
                              setRecognitionProviderFormState((current) => ({
                                ...current,
                                [provider.baseUrlKey]: nextValue,
                              }));
                            }}
                            fullWidth
                          />
                          <TextField
                            label="模型"
                            value={recognitionProviderFormState[provider.modelKey]}
                            onChange={(event) => {
                              const nextValue = event.target.value;
                              setRecognitionProviderFormState((current) => ({
                                ...current,
                                [provider.modelKey]: nextValue,
                              }));
                            }}
                            fullWidth
                          />
                          <Box
                            sx={{
                              display: "grid",
                              gridTemplateColumns: { xs: "1fr", sm: "repeat(2, minmax(0, 1fr))" },
                              gap: 2,
                            }}
                          >
                            <TextField
                              label="超时秒数"
                              value={recognitionProviderFormState[provider.timeoutKey]}
                              onChange={(event) => {
                                const nextValue = event.target.value;
                                setRecognitionProviderFormState((current) => ({
                                  ...current,
                                  [provider.timeoutKey]: nextValue,
                                }));
                                setRecognitionProviderFormErrors((current) => ({
                                  ...current,
                                  [provider.timeoutKey]: undefined,
                                }));
                              }}
                              error={Boolean(recognitionProviderFormErrors[provider.timeoutKey])}
                              helperText={recognitionProviderFormErrors[provider.timeoutKey]}
                              fullWidth
                            />
                            <TextField
                              label="最大重试次数"
                              value={recognitionProviderFormState[provider.retryKey]}
                              onChange={(event) => {
                                const nextValue = event.target.value;
                                setRecognitionProviderFormState((current) => ({
                                  ...current,
                                  [provider.retryKey]: nextValue,
                                }));
                                setRecognitionProviderFormErrors((current) => ({
                                  ...current,
                                  [provider.retryKey]: undefined,
                                }));
                              }}
                              error={Boolean(recognitionProviderFormErrors[provider.retryKey])}
                              helperText={recognitionProviderFormErrors[provider.retryKey]}
                              fullWidth
                            />
                          </Box>
                          <TextField
                            label="API Key"
                            type="password"
                            value={recognitionProviderFormState[provider.apiKeyKey]}
                            onChange={(event) => {
                              const nextValue = event.target.value;
                              setRecognitionProviderFormState((current) => ({
                                ...current,
                                [provider.apiKeyKey]: nextValue,
                              }));
                            }}
                            helperText="留空表示保持当前系统配置中的密钥；若系统配置未保存密钥，则继续 fallback 到 .env。"
                            fullWidth
                          />
                        </Stack>
                      </CardContent>
                    </Card>
                  ))}
                </Box>

                {hasRecognitionProviderValidationErrors ? (
                  <Alert severity="warning" sx={{ mt: 2 }}>
                    请先修正文本 LLM / VLM 的数字字段格式，再保存识别 Provider 配置。
                  </Alert>
                ) : null}

                <Stack direction="row" justifyContent="flex-end" sx={{ mt: 3 }}>
                  <Button
                    variant="contained"
                    onClick={() => {
                      void handleRecognitionProviderSave();
                    }}
                    disabled={isSavingRecognitionProviders}
                  >
                    {isSavingRecognitionProviders ? "保存中..." : "保存识别 Provider 配置"}
                  </Button>
                </Stack>
              </CardContent>
            </Card>

            <Card>
              <CardContent>
                <Typography variant="overline" color="text.secondary">
                  Runtime Summary
                </Typography>
                <Typography variant="h5" sx={{ mt: 0.5 }}>
                  当前运行状态
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                  此处仅展示排障必需的安全摘要，不会显示 token、密钥或长期凭据原文。
                </Typography>

                <Box
                  sx={{
                    display: "grid",
                    gridTemplateColumns: { xs: "1fr", md: "repeat(2, minmax(0, 1fr))" },
                    gap: 2,
                    mt: 3,
                  }}
                >
                  <Box>
                    <Typography variant="subtitle2">服务健康状态</Typography>
                    <Box sx={{ mt: 1 }}>
                      {renderBooleanChip(dashboard.service_health === "ok", "服务正常", "服务异常")}
                    </Box>
                  </Box>
                  <Box>
                    <Typography variant="subtitle2">运行环境</Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                      {dashboard.runtime.environment}
                    </Typography>
                  </Box>
                  <Box>
                    <Typography variant="subtitle2">公开 API 基地址</Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                      {dashboard.runtime.public_api_base_url}
                    </Typography>
                  </Box>
                  <Box>
                    <Typography variant="subtitle2">系统时区</Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                      {dashboard.runtime.system_timezone}
                    </Typography>
                  </Box>
                  <Box>
                    <Typography variant="subtitle2">浏览器时区</Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                      {browserTimeZone}
                    </Typography>
                  </Box>
                  <Box>
                    <Typography variant="subtitle2">异步任务模式</Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                      {dashboard.runtime.async_job_mode}
                    </Typography>
                  </Box>
                  <Box>
                    <Typography variant="subtitle2">文件存储后端</Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                      {dashboard.runtime.file_storage_backend}
                    </Typography>
                  </Box>
                  <Box>
                    <Typography variant="subtitle2">LLM Provider</Typography>
                    <Box sx={{ mt: 1 }}>
                      {renderBooleanChip(
                        dashboard.runtime.llm_provider_configured,
                        "已配置",
                        "未配置",
                      )}
                    </Box>
                  </Box>
                  <Box>
                    <Typography variant="subtitle2">纯文本材料 Provider</Typography>
                    <Box sx={{ mt: 1 }}>
                      {renderBooleanChip(
                        dashboard.runtime.text_llm_provider_configured,
                        "已生效",
                        "未生效",
                      )}
                    </Box>
                  </Box>
                  <Box>
                    <Typography variant="subtitle2">VLM Provider</Typography>
                    <Box sx={{ mt: 1 }}>
                      {renderBooleanChip(
                        dashboard.runtime.vlm_provider_configured,
                        "已生效",
                        "未生效",
                      )}
                    </Box>
                  </Box>
                  <Box>
                    <Typography variant="subtitle2">管理员自注册</Typography>
                    <Box sx={{ mt: 1 }}>
                      {renderBooleanChip(
                        dashboard.runtime.allow_admin_self_register,
                        "已开放",
                        "已关闭",
                      )}
                    </Box>
                  </Box>
                  <Box>
                    <Typography variant="subtitle2">引导管理员 Token</Typography>
                    <Box sx={{ mt: 1 }}>
                      {renderBooleanChip(
                        dashboard.runtime.bootstrap_admin_configured,
                        "已配置",
                        "未配置",
                      )}
                    </Box>
                  </Box>
                  <Box>
                    <Typography variant="subtitle2">Telegram 入站令牌</Typography>
                    <Box sx={{ mt: 1 }}>
                      {renderBooleanChip(
                        dashboard.runtime.telegram_inbound_configured,
                        "已配置",
                        "未配置",
                      )}
                    </Box>
                  </Box>
                  <Box>
                    <Typography variant="subtitle2">邮件入站令牌</Typography>
                    <Box sx={{ mt: 1 }}>
                      {renderBooleanChip(
                        dashboard.runtime.email_inbound_configured,
                        "已配置",
                        "未配置",
                      )}
                    </Box>
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </>
        ) : null}
      </Stack>
    </RoleWorkspace>
  );
}
