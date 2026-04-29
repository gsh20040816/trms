import type { ComponentType } from "react";
import { Link as RouterLink, Outlet } from "react-router-dom";

import AdminPanelSettingsIcon from "@mui/icons-material/AdminPanelSettings";
import ArrowForwardIcon from "@mui/icons-material/ArrowForward";
import BadgeIcon from "@mui/icons-material/Badge";
import EngineeringIcon from "@mui/icons-material/Engineering";
import LoginIcon from "@mui/icons-material/Login";
import SearchOffIcon from "@mui/icons-material/SearchOff";
import type { SvgIconProps } from "@mui/material/SvgIcon";

import Alert from "@mui/material/Alert";
import Avatar from "@mui/material/Avatar";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardActionArea from "@mui/material/CardActionArea";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

import { AppShell } from "../components/AppShell";
import { SnackbarProvider } from "../components/AppSnackbar";
import { ConfirmDialogProvider } from "../components/ConfirmDialog";
import { AppThemeProvider } from "../theme/AppThemeProvider";
import { useAuthSession } from "./auth-store";
import { roleRoutes, type UserRole } from "./role-routes";

type RoleOverview = {
  role: UserRole;
  title: string;
  summary: string;
  actions: string[];
  Icon: ComponentType<SvgIconProps>;
};

const ROLE_OVERVIEWS: RoleOverview[] = [
  {
    role: "member",
    title: "报销成员",
    summary: "查看我参与的任务、补充材料、确认个人费用。",
    actions: ["查看我的任务", "提交或补充材料", "确认个人费用"],
    Icon: BadgeIcon,
  },
  {
    role: "admin",
    title: "管理员",
    summary: "以任务推进为中心，优先处理缺失材料、待确认费用和导出准备。",
    actions: ["创建任务", "处理缺失材料", "复核与导出"],
    Icon: EngineeringIcon,
  },
  {
    role: "system_admin",
    title: "系统管理员",
    summary: "集中处理用户角色、全局配置、系统状态与审计记录。",
    actions: ["管理用户角色", "维护全局配置", "查看系统状态"],
    Icon: AdminPanelSettingsIcon,
  },
];

function getActiveOverview(role: UserRole) {
  return ROLE_OVERVIEWS.find((item) => item.role === role) ?? null;
}

function getVisibleRoleRoutes(roleNames: UserRole[]) {
  const roleNameSet = new Set(roleNames);
  return roleRoutes.filter((roleRoute) => roleNameSet.has(roleRoute.role));
}

export function RootLayout() {
  return (
    <AppThemeProvider>
      <SnackbarProvider>
        <ConfirmDialogProvider>
          <AppShell>
            <Outlet />
          </AppShell>
        </ConfirmDialogProvider>
      </SnackbarProvider>
    </AppThemeProvider>
  );
}

function GuestHomePage() {
  return (
    <Stack spacing={3}>
      <Box>
        <Typography variant="overline" color="text.secondary">
          账号入口
        </Typography>
        <Typography component="h1" variant="h3" sx={{ mt: 0.5, mb: 1 }}>
          登录后进入对应工作台
        </Typography>
        <Typography variant="body1" color="text.secondary" sx={{ maxWidth: 720 }}>
          先登录账号，再按你的身份进入材料提交、任务复核或系统配置。未登录状态下不会展示与当前职责无关的入口。
        </Typography>
        <Stack direction="row" spacing={1.5} sx={{ mt: 2 }}>
          <Button
            component={RouterLink}
            to="/login"
            variant="contained"
            size="large"
            startIcon={<LoginIcon />}
          >
            前往登录 / 注册
          </Button>
        </Stack>
      </Box>

      <Box
        sx={{
          display: "grid",
          gap: 2,
          gridTemplateColumns: { xs: "1fr", sm: "repeat(2, minmax(0, 1fr))", md: "repeat(3, minmax(0, 1fr))" },
        }}
      >
        {[
          {
            label: "成员账号",
            value: "材料与确认",
            description: "提交发票、查看识别状态、确认个人费用。",
            Icon: BadgeIcon,
            color: "primary.main",
          },
          {
            label: "管理员账号",
            value: "任务复核",
            description: "登录后进入任务管理、复核与导出。",
            Icon: EngineeringIcon,
            color: "warning.main",
          },
          {
            label: "系统管理员",
            value: "系统配置",
            description: "系统配置和诊断入口不对未登录用户展示。",
            Icon: AdminPanelSettingsIcon,
            color: "secondary.main",
          },
        ].map((item) => (
          <Card key={item.label} variant="outlined">
            <CardContent>
              <Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ mb: 1 }}>
                <Typography variant="overline" color="text.secondary">
                  {item.label}
                </Typography>
                <Avatar
                  sx={{
                    width: 32,
                    height: 32,
                    bgcolor: "action.hover",
                    color: item.color,
                  }}
                  variant="rounded"
                >
                  <item.Icon fontSize="small" />
                </Avatar>
              </Stack>
              <Typography variant="h5" sx={{ mb: 0.5 }}>
                {item.value}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {item.description}
              </Typography>
            </CardContent>
          </Card>
        ))}
      </Box>
    </Stack>
  );
}

function AuthenticatedHomePage() {
  const session = useAuthSession();
  if (!session) {
    return null;
  }
  const currentOverview = getActiveOverview(session.role);
  const visibleRoleRoutes = getVisibleRoleRoutes(session.availableRoles);
  const currentRolePath = roleRoutes.find((item) => item.role === session.role)?.path ?? "/login";

  return (
    <Stack spacing={3}>
      <Box>
        <Typography variant="overline" color="text.secondary">
          报销任务总览
        </Typography>
        <Stack direction={{ xs: "column", sm: "row" }} alignItems={{ xs: "flex-start", sm: "flex-end" }} justifyContent="space-between" spacing={2}>
          <Box>
            <Typography component="h1" variant="h3" sx={{ mt: 0.5 }}>
              Tongji ACM 报销管理系统
            </Typography>
            <Typography variant="body1" color="text.secondary" sx={{ mt: 1, maxWidth: 720 }}>
              直接进入你的工作台查看当前需要处理的任务和异常事项。
            </Typography>
            <Stack direction="row" spacing={1} sx={{ mt: 1.5 }} useFlexGap flexWrap="wrap">
              <Chip
                size="small"
                label={`当前身份：${currentOverview?.title ?? session.role}`}
                color="primary"
                variant="outlined"
              />
              <Chip
                size="small"
                label={`${session.displayName}${session.memberCode ? `（${session.memberCode}）` : ""}`}
                variant="outlined"
              />
            </Stack>
          </Box>
          <Button
            component={RouterLink}
            to={currentRolePath}
            variant="contained"
            size="large"
            endIcon={<ArrowForwardIcon />}
          >
            进入我的工作台
          </Button>
        </Stack>
      </Box>

      {currentOverview ? (
        <Card>
          <CardContent>
            <Stack direction="row" spacing={2} alignItems="center" sx={{ mb: 1.5 }}>
              <Avatar sx={{ bgcolor: "primary.main", color: "primary.contrastText" }}>
                <currentOverview.Icon />
              </Avatar>
              <Box>
                <Typography variant="overline" color="text.secondary">
                  当前身份
                </Typography>
                <Typography variant="h5">{currentOverview.title}</Typography>
              </Box>
              <Box sx={{ flexGrow: 1 }} />
              <Chip color="success" size="small" label="当前身份" />
            </Stack>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
              {currentOverview.summary}
            </Typography>
            <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap aria-label="当前身份推荐操作">
              {currentOverview.actions.map((action) => (
                <Chip key={action} label={action} variant="outlined" />
              ))}
            </Stack>
          </CardContent>
        </Card>
      ) : null}

      {visibleRoleRoutes.length > 0 ? (
        <Box>
          <Typography variant="h6" sx={{ mb: 1.5 }}>
            可进入的工作台
          </Typography>
          <Box
            sx={{
              display: "grid",
              gap: 2,
              gridTemplateColumns: { xs: "1fr", md: "repeat(3, minmax(0, 1fr))" },
            }}
            aria-label="当前账号可见入口"
          >
            {visibleRoleRoutes.map((roleRoute) => {
              const overview = getActiveOverview(roleRoute.role);
              const Icon = overview?.Icon ?? BadgeIcon;
              return (
                <Card key={roleRoute.path} variant="outlined">
                  <CardActionArea component={RouterLink} to={roleRoute.path}>
                    <CardContent>
                      <Stack direction="row" alignItems="center" spacing={1.5} sx={{ mb: 1 }}>
                        <Avatar sx={{ bgcolor: "action.hover", color: "primary.main" }} variant="rounded">
                          <Icon fontSize="small" />
                        </Avatar>
                        <Box>
                          <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
                            {overview?.title ?? roleRoute.title}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {roleRoute.title}
                          </Typography>
                        </Box>
                        <Box sx={{ flexGrow: 1 }} />
                        <ArrowForwardIcon fontSize="small" color="action" />
                      </Stack>
                      <Typography variant="body2" color="text.secondary">
                        {overview?.summary ?? roleRoute.summary}
                      </Typography>
                      {overview?.actions?.length ? (
                        <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap sx={{ mt: 1.5 }} aria-label={`${roleRoute.title} 操作入口`}>
                          {overview.actions.map((action) => (
                            <Chip key={`${roleRoute.role}:${action}`} label={action} size="small" variant="outlined" />
                          ))}
                        </Stack>
                      ) : null}
                    </CardContent>
                  </CardActionArea>
                </Card>
              );
            })}
          </Box>
        </Box>
      ) : null}
    </Stack>
  );
}

export function HomePage() {
  const session = useAuthSession();
  if (!session) {
    return <GuestHomePage />;
  }
  return <AuthenticatedHomePage />;
}

export function NotFoundPage() {
  return (
    <Stack spacing={2} sx={{ maxWidth: 520, mx: "auto", mt: 6, alignItems: "center", textAlign: "center" }}>
      <Avatar sx={{ width: 56, height: 56, bgcolor: "action.hover", color: "text.secondary" }}>
        <SearchOffIcon />
      </Avatar>
      <Typography variant="h4" component="h1">
        未找到页面
      </Typography>
      <Alert severity="info" sx={{ width: "100%" }}>
        请返回总览页重新选择工作台或操作入口。
      </Alert>
      <Button component={RouterLink} to="/" variant="contained" startIcon={<ArrowForwardIcon />}>
        返回总览
      </Button>
    </Stack>
  );
}
