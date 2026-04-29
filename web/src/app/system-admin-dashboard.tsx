import { useEffect, useState } from "react";
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
import { useSnackbar } from "../components/use-snackbar";
import { trmsApi } from "../lib/api/trms";
import type { SystemDashboard } from "../lib/api/types";
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

function buildConfigFormState(dashboard: SystemDashboard): ConfigFormState {
  return {
    invoiceTitle: dashboard.global_invoice_config?.invoice_title ?? "",
    taxNumber: dashboard.global_invoice_config?.tax_number ?? "",
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

export function SystemAdminDashboardPage() {
  const session = useAuthSession();
  const { showError, showSuccess } = useSnackbar();
  const [state, setState] = useState<SystemDashboardState>({ status: "loading" });
  const [formState, setFormState] = useState<ConfigFormState>({
    invoiceTitle: "",
    taxNumber: "",
  });
  const [formErrors, setFormErrors] = useState<ConfigFormErrors>({});
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState<unknown>(null);

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

  if (!session || session.role !== "system_admin") {
    return null;
  }

  const dashboard = state.status === "ready" ? state.dashboard : null;
  const validationErrors = validateConfigForm(formState);
  const hasValidationErrors = Object.keys(validationErrors).length > 0;
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
                <Typography variant="overline" color="text.secondary">
                  Runtime Summary
                </Typography>
                <Typography variant="h5" sx={{ mt: 0.5 }}>
                  当前运行状态
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                  这里只暴露排障必需的安全摘要，不展示 token、密钥或长期凭据原文。
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
