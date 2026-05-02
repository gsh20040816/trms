import { useState, type MouseEvent, type ReactNode } from "react";
import { Link as RouterLink, useLocation, useNavigate } from "react-router-dom";

import AccountCircleIcon from "@mui/icons-material/AccountCircle";
import AdminPanelSettingsIcon from "@mui/icons-material/AdminPanelSettings";
import BadgeIcon from "@mui/icons-material/Badge";
import DashboardIcon from "@mui/icons-material/Dashboard";
import DarkModeIcon from "@mui/icons-material/DarkMode";
import LightModeIcon from "@mui/icons-material/LightMode";
import LogoutIcon from "@mui/icons-material/Logout";
import LoginIcon from "@mui/icons-material/Login";
import MenuIcon from "@mui/icons-material/Menu";
import PersonIcon from "@mui/icons-material/Person";
import SettingsBrightnessIcon from "@mui/icons-material/SettingsBrightness";
import SwapHorizIcon from "@mui/icons-material/SwapHoriz";
import EngineeringIcon from "@mui/icons-material/Engineering";

import AppBar from "@mui/material/AppBar";
import Avatar from "@mui/material/Avatar";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Divider from "@mui/material/Divider";
import IconButton from "@mui/material/IconButton";
import ListItemIcon from "@mui/material/ListItemIcon";
import ListItemText from "@mui/material/ListItemText";
import Menu from "@mui/material/Menu";
import MenuItem from "@mui/material/MenuItem";
import Stack from "@mui/material/Stack";
import SwipeableDrawer from "@mui/material/SwipeableDrawer";
import Toolbar from "@mui/material/Toolbar";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import BottomNavigation from "@mui/material/BottomNavigation";
import BottomNavigationAction from "@mui/material/BottomNavigationAction";
import Paper from "@mui/material/Paper";
import { useTheme } from "@mui/material/styles";
import useMediaQuery from "@mui/material/useMediaQuery";

import {
  clearMockSession,
  logoutCurrentSession,
  switchCurrentRole,
  useAuthSession,
} from "../app/auth-store";
import { roleRoutes, type UserRole } from "../app/role-routes";
import { formatUserIdentityLabel } from "../lib/ui-text";
import { useAppTheme } from "../theme/use-app-theme";
import { useSnackbar } from "./use-snackbar";

type NavItem = {
  to: string;
  label: string;
  icon: ReactNode;
  matchPrefix?: string;
};

const NAV_RAIL_WIDTH = 88;

function buildNavItems(availableRoles: UserRole[]): NavItem[] {
  const items: NavItem[] = [
    { to: "/", label: "总览", icon: <DashboardIcon /> },
  ];
  if (availableRoles.includes("member")) {
    items.push({ to: "/member", label: "我的任务", icon: <BadgeIcon />, matchPrefix: "/member" });
  }
  if (availableRoles.includes("admin")) {
    items.push({ to: "/admin", label: "任务管理", icon: <EngineeringIcon />, matchPrefix: "/admin" });
  }
  if (availableRoles.includes("system_admin")) {
    items.push({
      to: "/system",
      label: "系统管理",
      icon: <AdminPanelSettingsIcon />,
      matchPrefix: "/system",
    });
  }
  return items;
}

function isActive(pathname: string, item: NavItem) {
  if (item.matchPrefix) {
    return pathname === item.matchPrefix || pathname.startsWith(`${item.matchPrefix}/`);
  }
  return pathname === item.to;
}

function getRoleDisplay(role: UserRole) {
  return roleRoutes.find((roleRoute) => roleRoute.role === role);
}

export function AppShell({ children }: { children: ReactNode }) {
  const session = useAuthSession();
  const location = useLocation();
  const navigate = useNavigate();
  const theme = useTheme();
  const isDesktop = useMediaQuery(theme.breakpoints.up("md"));
  const { preference, setPreference } = useAppTheme();
  const { showError, showSuccess } = useSnackbar();

  const [accountAnchor, setAccountAnchor] = useState<null | HTMLElement>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);

  const navItems = buildNavItems(session?.availableRoles ?? []);
  const activeRole = session ? getRoleDisplay(session.role) : null;

  function handleAccountOpen(event: MouseEvent<HTMLElement>) {
    setAccountAnchor(event.currentTarget);
  }
  function handleAccountClose() {
    setAccountAnchor(null);
  }

  function handleLogout() {
    handleAccountClose();
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
      .catch(() => {
        showError("退出登录失败，请稍后重试");
      });
  }

  function handleSwitchRole(targetRole: UserRole) {
    handleAccountClose();
    if (!session || session.role === targetRole) {
      return;
    }
    void switchCurrentRole(targetRole)
      .then((nextSession) => {
        const targetRoute = getRoleDisplay(targetRole);
        if (targetRoute) {
          void navigate(targetRoute.path);
        }
        if (nextSession) {
          showSuccess(`已切换到${getRoleDisplay(targetRole)?.loginLabel ?? "新身份"}`);
        }
      })
      .catch(() => {
        showError("切换身份失败，请稍后重试");
      });
  }

  const accountMenu = (
    <Menu
      anchorEl={accountAnchor}
      open={Boolean(accountAnchor)}
      onClose={handleAccountClose}
      anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
      transformOrigin={{ vertical: "top", horizontal: "right" }}
      slotProps={{ paper: { sx: { minWidth: 240 } } }}
    >
      {session ? (
        <Box sx={{ px: 2, py: 1.5 }}>
          <Typography variant="subtitle2" component="div" noWrap>
            {formatUserIdentityLabel(session)}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {activeRole?.loginLabel ?? "已登录"}
          </Typography>
        </Box>
      ) : null}
      {session ? <Divider /> : null}
      {session && session.availableRoles.length > 1
        ? session.availableRoles.map((availableRole) => {
            const availableRoute = getRoleDisplay(availableRole);
            const isCurrent = availableRole === session.role;
            return (
              <MenuItem
                key={availableRole}
                disabled={isCurrent}
                onClick={() => {
                  handleSwitchRole(availableRole);
                }}
              >
                <ListItemIcon>
                  <SwapHorizIcon fontSize="small" />
                </ListItemIcon>
                <ListItemText
                  primary={isCurrent ? `当前身份：${availableRoute?.loginLabel}` : `切换到${availableRoute?.loginLabel}`}
                />
              </MenuItem>
            );
          })
        : null}
      {session && session.availableRoles.length > 1 ? <Divider /> : null}
      {session ? (
        <MenuItem
          component={RouterLink}
          to="/profile"
          onClick={handleAccountClose}
        >
          <ListItemIcon>
            <PersonIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText primary="个人信息" />
        </MenuItem>
      ) : null}
      {session ? <Divider /> : null}
      <MenuItem
        onClick={() => {
          setPreference("light");
          handleAccountClose();
        }}
        selected={preference === "light"}
      >
        <ListItemIcon>
          <LightModeIcon fontSize="small" />
        </ListItemIcon>
        <ListItemText primary="亮色主题" />
      </MenuItem>
      <MenuItem
        onClick={() => {
          setPreference("dark");
          handleAccountClose();
        }}
        selected={preference === "dark"}
      >
        <ListItemIcon>
          <DarkModeIcon fontSize="small" />
        </ListItemIcon>
        <ListItemText primary="暗色主题" />
      </MenuItem>
      <MenuItem
        onClick={() => {
          setPreference("system");
          handleAccountClose();
        }}
        selected={preference === "system"}
      >
        <ListItemIcon>
          <SettingsBrightnessIcon fontSize="small" />
        </ListItemIcon>
        <ListItemText primary="跟随系统" />
      </MenuItem>
      <Divider />
      {session ? (
        <MenuItem onClick={handleLogout}>
          <ListItemIcon>
            <LogoutIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText primary="退出登录" />
        </MenuItem>
      ) : (
        <MenuItem
          component={RouterLink}
          to="/login"
          onClick={handleAccountClose}
        >
          <ListItemIcon>
            <LoginIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText primary="登录 / 注册" />
        </MenuItem>
      )}
    </Menu>
  );

  const navList = (variant: "rail" | "drawer") => (
    <Stack
      component="nav"
      aria-label="主导航"
      spacing={variant === "rail" ? 1.25 : 0.5}
      sx={{
        py: variant === "rail" ? 2 : 1,
        px: variant === "rail" ? 0.75 : 1,
        alignItems: variant === "rail" ? "stretch" : "stretch",
      }}
    >
      {navItems.map((item) => {
        const active = isActive(location.pathname, item);
        if (variant === "rail") {
          return (
            <Tooltip key={item.to} title={item.label} placement="right">
              <Box
                component={RouterLink}
                to={item.to}
                aria-current={active ? "page" : undefined}
                sx={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: 0.5,
                  textDecoration: "none",
                  px: 0.5,
                  py: 1.25,
                  borderRadius: 3,
                  color: active ? "primary.main" : "text.secondary",
                  bgcolor: active ? "action.selected" : "transparent",
                  "&:hover": { bgcolor: "action.hover", color: "text.primary" },
                  transition: "background-color 120ms, color 120ms",
                }}
              >
                <Box sx={{ display: "flex", alignItems: "center", justifyContent: "center", fontSize: 26 }}>
                  {item.icon}
                </Box>
                <Typography variant="caption" sx={{ fontWeight: 600 }}>
                  {item.label}
                </Typography>
              </Box>
            </Tooltip>
          );
        }
        return (
          <Box
            key={item.to}
            component={RouterLink}
            to={item.to}
            onClick={() => setDrawerOpen(false)}
            aria-current={active ? "page" : undefined}
            sx={{
              display: "flex",
              alignItems: "center",
              gap: 1.5,
              textDecoration: "none",
              color: active ? "primary.main" : "text.primary",
              bgcolor: active ? "action.selected" : "transparent",
              borderRadius: 2,
              px: 1.5,
              py: 1.25,
            }}
          >
            <Box sx={{ display: "inline-flex", alignItems: "center" }}>{item.icon}</Box>
            <Typography variant="body1" sx={{ fontWeight: 600 }}>
              {item.label}
            </Typography>
          </Box>
        );
      })}
    </Stack>
  );

  const bottomNav = !isDesktop && navItems.length > 1 ? (
    <Paper
      square
      elevation={3}
      sx={{
        position: "sticky",
        bottom: 0,
        zIndex: (t) => t.zIndex.appBar - 1,
      }}
    >
      <BottomNavigation
        showLabels
        value={navItems.findIndex((item) => isActive(location.pathname, item))}
        onChange={(_event, newValue: number) => {
          const target = navItems[newValue];
          if (target) {
            void navigate(target.to);
          }
        }}
      >
        {navItems.map((item) => (
          <BottomNavigationAction key={item.to} label={item.label} icon={item.icon} />
        ))}
      </BottomNavigation>
    </Paper>
  ) : null;

  return (
    <Box
      sx={{
        minHeight: "100vh",
        display: "flex",
        flexDirection: "column",
        bgcolor: "background.default",
      }}
    >
      <AppBar position="sticky">
        <Toolbar sx={{ gap: 2 }}>
          {!isDesktop ? (
            <IconButton
              edge="start"
              aria-label="打开导航菜单"
              onClick={() => setDrawerOpen(true)}
              size="large"
            >
              <MenuIcon />
            </IconButton>
          ) : null}
          <Box
            component={RouterLink}
            to="/"
            sx={{
              display: "inline-flex",
              alignItems: "center",
              gap: 1,
              textDecoration: "none",
              color: "text.primary",
            }}
          >
            <Avatar
              variant="rounded"
              sx={{
                bgcolor: "primary.main",
                color: "primary.contrastText",
                width: 36,
                height: 36,
                fontSize: 14,
                fontWeight: 800,
                letterSpacing: 1,
              }}
            >
              TR
            </Avatar>
            <Box sx={{ display: { xs: "none", sm: "block" } }}>
              <Typography variant="subtitle1" sx={{ fontWeight: 700, lineHeight: 1.1 }}>
                TRMS
              </Typography>
              <Typography variant="caption" color="text.secondary">
                同济 ACM 报销管理
              </Typography>
            </Box>
          </Box>
          <Box sx={{ flexGrow: 1 }} />
          {!session ? (
            <Button
              component={RouterLink}
              to="/login"
              variant="contained"
              startIcon={<LoginIcon />}
            >
              登录 / 注册
            </Button>
          ) : null}
          <Tooltip title={session ? "账号" : "外观与登录"}>
            <IconButton
              aria-label={session ? "账号菜单" : "应用菜单"}
              onClick={handleAccountOpen}
              size="large"
            >
              {session ? (
                <Avatar
                  sx={{
                    width: 32,
                    height: 32,
                    bgcolor: "primary.main",
                    color: "primary.contrastText",
                    fontSize: 14,
                    fontWeight: 700,
                  }}
                >
                  {session.displayName.slice(0, 1) || <PersonIcon fontSize="small" />}
                </Avatar>
              ) : (
                <AccountCircleIcon />
              )}
            </IconButton>
          </Tooltip>
        </Toolbar>
      </AppBar>
      {accountMenu}

      <SwipeableDrawer
        anchor="left"
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        onOpen={() => setDrawerOpen(true)}
        disableSwipeToOpen
      >
        <Box sx={{ width: 260 }} role="presentation">
          <Toolbar />
          {navList("drawer")}
        </Box>
      </SwipeableDrawer>

      <Box sx={{ display: "flex", flexGrow: 1, minHeight: 0 }}>
        {isDesktop && navItems.length > 1 ? (
          <Box
            component="aside"
            aria-label="侧边导航"
            sx={{
              width: NAV_RAIL_WIDTH,
              flexShrink: 0,
              borderRight: 1,
              borderColor: "divider",
              bgcolor: "background.paper",
              position: "sticky",
              top: 64,
              alignSelf: "flex-start",
              height: "calc(100vh - 64px)",
            }}
          >
            {navList("rail")}
          </Box>
        ) : null}
        <Box
          component="main"
          sx={{
            flexGrow: 1,
            minWidth: 0,
            display: "flex",
            flexDirection: "column",
          }}
        >
          <Box
            sx={{
              flexGrow: 1,
              width: "100%",
              maxWidth: 1280,
              mx: "auto",
              px: { xs: 2, md: 3 },
              py: { xs: 2, md: 3 },
            }}
          >
            {children}
          </Box>
          {bottomNav}
        </Box>
      </Box>
    </Box>
  );
}
