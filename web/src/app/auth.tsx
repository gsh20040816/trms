import { useEffect, useState, type FormEvent } from "react";
import { Link as RouterLink, Navigate, Outlet, useLocation, useNavigate, useSearchParams } from "react-router-dom";

import LoginIcon from "@mui/icons-material/Login";
import LogoutIcon from "@mui/icons-material/Logout";
import PersonAddAltIcon from "@mui/icons-material/PersonAddAlt";
import SwapHorizIcon from "@mui/icons-material/SwapHoriz";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import Collapse from "@mui/material/Collapse";
import Divider from "@mui/material/Divider";
import MenuItem from "@mui/material/MenuItem";
import Stack from "@mui/material/Stack";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";

import { useSnackbar } from "../components/use-snackbar";
import { ApiError } from "../lib/api/client";
import { summarizeUnknownError } from "../lib/api/errors";
import {
  buildLoginPath,
  clearMockSession,
  loginWithPassword,
  logoutCurrentSession,
  registerWithPassword,
  switchCurrentRole,
  useAuthSession,
} from "./auth-store";
import { resolveAuthUiConfig, type AuthUiConfig } from "./auth-ui-config";
import {
  findRoleRouteByRole,
  roleRoutes,
  type RoleRouteConfig,
  type UserRole,
} from "./role-routes";

function getRoleRouteOrThrow(role: UserRole) {
  const roleRoute = findRoleRouteByRole(role);
  if (!roleRoute) {
    throw new Error(`Unknown role route: ${role}`);
  }
  return roleRoute;
}

function normalizeNextPath(rawPath: string | null) {
  if (!rawPath || !rawPath.startsWith("/")) {
    return null;
  }
  return rawPath;
}

function describeError(error: unknown) {
  if (error instanceof ApiError) {
    return error.summary.message;
  }
  return summarizeUnknownError(error).message;
}

const DEV_ROLE_PASSWORD = "dev-password-123";

function buildDevRoleUsername(role: UserRole) {
  return `dev-${role.replaceAll("_", "-")}`;
}

export function MockLoginPage({ uiConfig = resolveAuthUiConfig() }: { uiConfig?: AuthUiConfig }) {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const session = useAuthSession();
  const { showError, showSuccess } = useSnackbar();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<UserRole>("member");
  const [displayName, setDisplayName] = useState("");
  const [actorId, setActorId] = useState("");
  const [memberCode, setMemberCode] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [devEntrySubmittingRole, setDevEntrySubmittingRole] = useState<UserRole | null>(null);
  const [formErrorMessage, setFormErrorMessage] = useState<string | null>(null);
  const nextPath = normalizeNextPath(searchParams.get("next"));
  const activeRoleRoute = session ? getRoleRouteOrThrow(session.role) : null;
  const registrationRoleRoutes = uiConfig.allowPrivilegedSelfRegistration
    ? roleRoutes
    : roleRoutes.filter((roleRoute) => roleRoute.role === "member");

  function handleCredentialSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormErrorMessage(null);
    setIsSubmitting(true);
    void (async () => {
      try {
        const nextSession = mode === "login"
          ? await loginWithPassword({ username, password })
          : await registerWithPassword({
            username,
            password,
            role,
            displayName,
            actorId,
            memberCode,
          });
        const targetRoleRoute = getRoleRouteOrThrow(nextSession.role);
        showSuccess(mode === "login" ? "登录成功" : "注册并登录成功");
        void navigate(nextPath ?? targetRoleRoute.path, {
          replace: true,
        });
      } catch (submitError) {
        const message = describeError(submitError);
        setFormErrorMessage(message);
        showError(message);
      } finally {
        setIsSubmitting(false);
      }
    })();
  }

  function handleDevRoleLogin(targetRole: UserRole) {
    const targetRoleRoute = getRoleRouteOrThrow(targetRole);
    setFormErrorMessage(null);
    setDevEntrySubmittingRole(targetRole);
    void (async () => {
      try {
        const username = buildDevRoleUsername(targetRole);
        try {
          await registerWithPassword({
            username,
            password: DEV_ROLE_PASSWORD,
            role: targetRole,
            displayName: targetRoleRoute.mockDisplayName,
            actorId: targetRoleRoute.mockActorId,
            memberCode: targetRoleRoute.mockMemberCode ?? undefined,
          });
        } catch (error) {
          if (!(error instanceof ApiError) || error.status !== 409) {
            throw error;
          }
          await loginWithPassword({
            username,
            password: DEV_ROLE_PASSWORD,
          });
        }

        showSuccess(`已使用开发快捷入口登录：${targetRoleRoute.loginLabel}`);
        void navigate(targetRoleRoute.path, {
          replace: true,
        });
      } catch (submitError) {
        const message = describeError(submitError);
        setFormErrorMessage(message);
        showError(message);
      } finally {
        setDevEntrySubmittingRole(null);
      }
    })();
  }

  function handleSwitchRole(targetRole: UserRole) {
    void switchCurrentRole(targetRole)
      .then(() => {
        showSuccess(`已切换到${getRoleRouteOrThrow(targetRole).loginLabel}`);
      })
      .catch((error: unknown) => {
        showError(describeError(error));
      });
  }

  function handleLogout() {
    if (!session) {
      return;
    }
    if (session.isMock) {
      clearMockSession();
      showSuccess("已退出当前调试身份");
      return;
    }
    void logoutCurrentSession()
      .then(() => {
        showSuccess("已退出登录");
      })
      .catch((error: unknown) => {
        showError(describeError(error));
      });
  }

  return (
    <Stack spacing={3} sx={{ maxWidth: 720, mx: "auto" }}>
      <Box>
        <Typography variant="overline" color="text.secondary">
          账号入口
        </Typography>
        <Typography variant="h4" component="h2" sx={{ mt: 0.5 }}>
          账号登录与注册
        </Typography>
        <Typography variant="body1" color="text.secondary" sx={{ mt: 1 }}>
          登录后将按你的身份进入对应工作台。成员可以查看任务和提交材料，管理员可以处理任务复核，系统管理员负责配置与巡检。
        </Typography>
        {nextPath ? (
          <Alert severity="info" sx={{ mt: 2 }}>
            检测到你需要先登录，登录后会自动返回原页面。
          </Alert>
        ) : (
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1.5 }}>
            请使用与你当前工作内容匹配的账号登录。
          </Typography>
        )}
      </Box>

      <Card>
        <CardContent>
          <Tabs
            value={mode}
            onChange={(_event, newValue: "login" | "register") => {
              setMode(newValue);
              setFormErrorMessage(null);
            }}
            aria-label="账号登录注册"
            sx={{ borderBottom: 1, borderColor: "divider", mb: 2 }}
          >
            <Tab value="login" label="登录" id="auth-tab-login" />
            <Tab value="register" label="注册" id="auth-tab-register" />
          </Tabs>

          <Box component="form" onSubmit={handleCredentialSubmit} aria-label="账号登录注册表单">
            <Stack spacing={2}>
              <TextField
                label="用户名"
                name="username"
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                required
                autoComplete="username"
                slotProps={{ htmlInput: { minLength: 3 } }}
                fullWidth
              />
              <TextField
                label="密码"
                name="password"
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                required
                autoComplete={mode === "login" ? "current-password" : "new-password"}
                slotProps={{ htmlInput: { minLength: 8 } }}
                fullWidth
              />
              {mode === "register" ? (
                <>
                  {uiConfig.allowPrivilegedSelfRegistration ? (
                    <TextField
                      select
                      label="角色"
                      name="role"
                      value={role}
                      onChange={(event) => setRole(event.target.value as UserRole)}
                      fullWidth
                    >
                      {registrationRoleRoutes.map((roleRoute) => (
                        <MenuItem key={roleRoute.role} value={roleRoute.role}>
                          {roleRoute.loginLabel}
                        </MenuItem>
                      ))}
                    </TextField>
                  ) : (
                    <Alert severity="info">
                      当前环境仅开放成员自注册；管理员与系统管理员账号必须通过受控初始化或后续邀请/审批流程创建。
                    </Alert>
                  )}
                  <TextField
                    label="显示名称"
                    name="display_name"
                    value={displayName}
                    onChange={(event) => setDisplayName(event.target.value)}
                    fullWidth
                  />
                  <TextField
                    label="身份编号"
                    name="actor_id"
                    placeholder={role === "member" ? "成员学号，例如 2250001" : "管理编号，例如 admin-1"}
                    value={actorId}
                    onChange={(event) => setActorId(event.target.value)}
                    fullWidth
                  />
                  <TextField
                    label="成员编号"
                    name="member_code"
                    placeholder="仅成员账号需要"
                    value={memberCode}
                    onChange={(event) => setMemberCode(event.target.value)}
                    disabled={role !== "member"}
                    fullWidth
                  />
                </>
              ) : null}
              {formErrorMessage ? (
                <Alert severity="error" onClose={() => setFormErrorMessage(null)}>
                  {formErrorMessage}
                </Alert>
              ) : null}
              <Box sx={{ display: "flex", justifyContent: "flex-end" }}>
                <Button
                  type="submit"
                  variant="contained"
                  disabled={isSubmitting}
                  startIcon={mode === "login" ? <LoginIcon /> : <PersonAddAltIcon />}
                  size="large"
                >
                  {isSubmitting ? "提交中..." : mode === "login" ? "登录" : "注册并登录"}
                </Button>
              </Box>
            </Stack>
          </Box>
        </CardContent>
      </Card>

      {uiConfig.enableDevRoleEntries ? (
        <Card variant="outlined" sx={{ borderStyle: "dashed" }}>
          <CardContent>
            <Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ mb: 1 }}>
              <Box>
                <Typography variant="overline" color="text.secondary">
                  开发调试角色入口
                </Typography>
                <Typography variant="subtitle1" sx={{ mt: 0.5 }}>
                  以下入口仅在开发构建中可见
                </Typography>
              </Box>
              <Chip label="DEV" color="warning" size="small" />
            </Stack>
            <Box
              role="group"
              aria-label="开发调试角色入口"
              sx={{
                display: "grid",
                gridTemplateColumns: { xs: "1fr", sm: "repeat(3, minmax(0, 1fr))" },
                gap: 2,
              }}
            >
              {roleRoutes.map((roleRoute) => (
                <Card key={roleRoute.role} variant="outlined">
                  <CardContent>
                    <Typography variant="overline" color="text.secondary">
                      调试入口
                    </Typography>
                    <Typography variant="h6" sx={{ mt: 0.5 }}>
                      {roleRoute.loginLabel}
                    </Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                      {roleRoute.summary}
                    </Typography>
                    <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 1 }}>
                      开发会话：{roleRoute.mockDisplayName}
                      {roleRoute.mockMemberCode ? `（${roleRoute.mockMemberCode}）` : ""}
                    </Typography>
                    <Button
                      variant="outlined"
                      size="small"
                      sx={{ mt: 1.5 }}
                      onClick={() => handleDevRoleLogin(roleRoute.role)}
                      disabled={devEntrySubmittingRole !== null}
                    >
                      {devEntrySubmittingRole === roleRoute.role
                        ? "进入中..."
                        : `以${roleRoute.loginLabel}进入`}
                    </Button>
                  </CardContent>
                </Card>
              ))}
            </Box>
          </CardContent>
        </Card>
      ) : null}

      <Collapse in={Boolean(activeRoleRoute && session)}>
        {activeRoleRoute && session ? (
          <Card>
            <CardContent>
              <Typography variant="overline" color="text.secondary">
                当前会话
              </Typography>
              <Typography variant="h5" sx={{ mt: 0.5 }}>
                当前已登录
              </Typography>
              <Typography variant="body1" sx={{ mt: 1 }}>
                你当前以 {activeRoleRoute.loginLabel} 身份登录，姓名为 {session.displayName}
                {session.memberCode ? `（${session.memberCode}）` : ""}。
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                {session.isMock
                  ? "当前是开发调试会话。"
                  : `当前账号：${session.username ?? session.actorId}。`}
              </Typography>
              {session.availableRoles.length > 1 ? (
                <Box sx={{ mt: 2 }} aria-label="可切换身份">
                  <Typography variant="subtitle2" sx={{ mb: 1 }}>
                    可切换身份
                  </Typography>
                  <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap">
                    {session.availableRoles.map((availableRole) => {
                      const availableRoleRoute = getRoleRouteOrThrow(availableRole);
                      const isActive = availableRole === session.role;
                      return (
                        <Button
                          key={availableRole}
                          variant={isActive ? "contained" : "outlined"}
                          size="small"
                          startIcon={<SwapHorizIcon />}
                          disabled={isActive}
                          onClick={() => handleSwitchRole(availableRole)}
                        >
                          {isActive
                            ? `当前身份：${availableRoleRoute.loginLabel}`
                            : `切换到${availableRoleRoute.loginLabel}`}
                        </Button>
                      );
                    })}
                  </Stack>
                </Box>
              ) : null}
              <Divider sx={{ my: 2 }} />
              <Stack direction="row" spacing={1.5} flexWrap="wrap" useFlexGap>
                <Button
                  component={RouterLink}
                  to={activeRoleRoute.path}
                  variant="contained"
                  startIcon={<LoginIcon />}
                >
                  进入当前入口
                </Button>
                <Button
                  variant="outlined"
                  startIcon={<LogoutIcon />}
                  onClick={handleLogout}
                >
                  退出当前会话
                </Button>
              </Stack>
            </CardContent>
          </Card>
        ) : (
          <Box />
        )}
      </Collapse>
    </Stack>
  );
}

export function ProtectedRoleRoute({ roleRoute }: { roleRoute: RoleRouteConfig }) {
  const session = useAuthSession();
  const location = useLocation();
  const { showError } = useSnackbar();
  const [switchFailure, setSwitchFailure] = useState<{
    error: unknown;
    role: UserRole;
  } | null>(null);
  const canSwitchToRole = session?.availableRoles.includes(roleRoute.role) ?? false;
  const switchError = switchFailure?.role === roleRoute.role ? switchFailure.error : null;

  useEffect(() => {
    if (!session || session.role === roleRoute.role || !canSwitchToRole) {
      return;
    }

    let isCancelled = false;
    void switchCurrentRole(roleRoute.role).catch((error: unknown) => {
      if (!isCancelled) {
        setSwitchFailure({
          error,
          role: roleRoute.role,
        });
        showError(describeError(error));
      }
    });
    return () => {
      isCancelled = true;
    };
  }, [canSwitchToRole, roleRoute.role, session, showError]);

  if (!session) {
    return (
      <Navigate
        replace
        to={buildLoginPath(`${location.pathname}${location.search}`)}
      />
    );
  }

  if (session.role !== roleRoute.role) {
    if (canSwitchToRole && !switchError) {
      return (
        <Card sx={{ maxWidth: 640, mx: "auto", mt: 4 }}>
          <CardContent>
            <Typography variant="overline" color="text.secondary">
              切换身份
            </Typography>
            <Typography variant="h5" sx={{ mt: 0.5 }}>
              {`正在切换到${roleRoute.loginLabel}`}
            </Typography>
            <Typography variant="body1" color="text.secondary" sx={{ mt: 1 }}>
              当前账号已绑定该角色，系统正在切换激活身份并进入对应工作台。
            </Typography>
            <Alert severity="info" sx={{ mt: 2 }}>
              目标入口：{roleRoute.title}
            </Alert>
          </CardContent>
        </Card>
      );
    }
    const currentRoleRoute = getRoleRouteOrThrow(session.role);
    return (
      <Card sx={{ maxWidth: 640, mx: "auto", mt: 4 }}>
        <CardContent>
          <Typography variant="overline" color="warning.main">
            访问受限
          </Typography>
          <Typography variant="h5" sx={{ mt: 0.5 }}>
            {`${roleRoute.title} 暂不可访问`}
          </Typography>
          <Typography variant="body1" color="text.secondary" sx={{ mt: 1 }}>
            {switchError
              ? `切换到${roleRoute.loginLabel}失败；请稍后重试。`
              : `当前登录身份不匹配；此入口仅允许${roleRoute.loginLabel}访问。`}
          </Typography>
          <Alert severity="info" sx={{ mt: 2 }}>
            当前身份为 {currentRoleRoute.loginLabel} / {session.displayName}
            {session.memberCode ? `（${session.memberCode}）` : ""}。
          </Alert>
          {switchError ? (
            <Alert severity="error" sx={{ mt: 2 }}>
              {describeError(switchError)}
            </Alert>
          ) : null}
          <Stack direction="row" spacing={1.5} sx={{ mt: 2 }} flexWrap="wrap" useFlexGap>
            <Button component={RouterLink} to={currentRoleRoute.path} variant="contained">
              进入我的入口
            </Button>
            <Button component={RouterLink} to="/" variant="outlined">
              返回首页
            </Button>
          </Stack>
        </CardContent>
      </Card>
    );
  }

  if (roleRoute.role === "admin" || roleRoute.role === "member" || roleRoute.role === "system_admin") {
    return <Outlet />;
  }

  return null;
}
