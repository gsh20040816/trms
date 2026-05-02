import type { ReactNode } from "react";
import { Link as RouterLink } from "react-router-dom";

import AssignmentIcon from "@mui/icons-material/Assignment";
import ChevronRightIcon from "@mui/icons-material/ChevronRight";
import DashboardIcon from "@mui/icons-material/Dashboard";
import DownloadIcon from "@mui/icons-material/Download";
import FactCheckIcon from "@mui/icons-material/FactCheck";
import NotificationsActiveIcon from "@mui/icons-material/NotificationsActive";
import PaymentsIcon from "@mui/icons-material/Payments";

import Box from "@mui/material/Box";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import Divider from "@mui/material/Divider";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemButton from "@mui/material/ListItemButton";
import ListItemIcon from "@mui/material/ListItemIcon";
import ListItemText from "@mui/material/ListItemText";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

import type { ReimbursementTask } from "../lib/api/types";
import { formatTaskStatus } from "../lib/ui-text";
import { describeAdminTaskStage } from "./admin-task-stage";

export type AdminModuleKey =
  | "overview"
  | "create"
  | "tasks"
  | "review"
  | "corrections"
  | "splits"
  | "exports";

type AdminWorkspaceShellProps = {
  activeModule: AdminModuleKey;
  taskId?: string | null;
  task?: ReimbursementTask | null;
  header: ReactNode;
  children: ReactNode;
};

type AdminModuleDefinition = {
  key: AdminModuleKey;
  title: string;
  Icon: typeof DashboardIcon;
};

const ADMIN_CONTEXT_FREE_MODULES: AdminModuleDefinition[] = [
  {
    key: "overview",
    title: "首页总览",
    Icon: DashboardIcon,
  },
  {
    key: "create",
    title: "创建任务",
    Icon: AssignmentIcon,
  },
];

const ADMIN_TASK_CONTEXT_MODULES: AdminModuleDefinition[] = [
  {
    key: "overview",
    title: "首页总览",
    Icon: DashboardIcon,
  },
  {
    key: "tasks",
    title: "任务管理",
    Icon: AssignmentIcon,
  },
  {
    key: "review",
    title: "材料审核",
    Icon: FactCheckIcon,
  },
  {
    key: "corrections",
    title: "成员提醒",
    Icon: NotificationsActiveIcon,
  },
  {
    key: "splits",
    title: "分摊确认",
    Icon: PaymentsIcon,
  },
  {
    key: "exports",
    title: "导出打印",
    Icon: DownloadIcon,
  },
];

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function buildModulePath(moduleKey: AdminModuleKey, taskId?: string | null) {
  switch (moduleKey) {
    case "overview":
      return "/admin";
    case "create":
      return "/admin/tasks/new";
    case "tasks":
      return taskId ? `/admin/tasks/${taskId}` : null;
    case "review":
      return taskId ? `/admin/tasks/${taskId}/review` : null;
    case "corrections":
      return taskId ? `/admin/tasks/${taskId}/corrections` : null;
    case "splits":
      return taskId ? `/admin/tasks/${taskId}/splits` : null;
    case "exports":
      return taskId ? `/admin/tasks/${taskId}/exports` : null;
    default:
      return null;
  }
}

export function AdminWorkspaceShell({
  activeModule,
  taskId,
  task,
  header,
  children,
}: AdminWorkspaceShellProps) {
  const taskStage = task ? describeAdminTaskStage(task.status) : null;
  const navigationModules = taskId ? ADMIN_TASK_CONTEXT_MODULES : ADMIN_CONTEXT_FREE_MODULES;

  return (
    <Box
      sx={{
        display: "grid",
        gap: 2.5,
        gridTemplateColumns: { xs: "1fr", md: "220px minmax(0, 1fr)" },
        alignItems: "start",
      }}
    >
      <Box
        component="aside"
        sx={{
          display: "grid",
          gap: 1.5,
          position: { md: "sticky" },
          top: { md: 88 },
        }}
      >
        {/* 导航模块列表 */}
        <Card variant="outlined" component="section">
          <CardContent sx={{ py: 1.5, "&:last-child": { pb: 1.5 } }}>
            <List
              component="nav"
              aria-label="管理员模块导航"
              dense
              disablePadding
              sx={{ display: "grid", gap: 0.25 }}
            >
              {navigationModules.map((adminModule) => {
                const path = buildModulePath(adminModule.key, taskId);
                const isActive = adminModule.key === activeModule;
                if (!path) {
                  return (
                    <ListItem
                      key={adminModule.key}
                      disablePadding
                      aria-disabled="true"
                      sx={{ opacity: 0.45 }}
                    >
                      <ListItemButton
                        disabled
                        sx={{
                          borderRadius: 1.5,
                          py: 0.75,
                          minHeight: 40,
                        }}
                      >
                        <ListItemIcon sx={{ minWidth: 32 }}>
                          <adminModule.Icon fontSize="small" />
                        </ListItemIcon>
                        <ListItemText
                          primary={adminModule.title}
                          primaryTypographyProps={{ variant: "body2", fontWeight: 600 }}
                        />
                      </ListItemButton>
                    </ListItem>
                  );
                }
                return (
                  <ListItem key={adminModule.key} disablePadding>
                    <ListItemButton
                      component={RouterLink}
                      to={path}
                      selected={isActive}
                      aria-current={isActive ? "page" : undefined}
                      sx={{
                        borderRadius: 1.5,
                        py: 0.75,
                        minHeight: 40,
                        "&.Mui-selected": {
                          bgcolor: "primary.main",
                          color: "primary.contrastText",
                          "&:hover": {
                            bgcolor: "primary.dark",
                          },
                          "& .MuiListItemIcon-root": {
                            color: "primary.contrastText",
                          },
                        },
                      }}
                    >
                      <ListItemIcon
                        sx={{
                          minWidth: 32,
                          color: isActive ? "primary.contrastText" : "text.secondary",
                        }}
                      >
                        <adminModule.Icon fontSize="small" />
                      </ListItemIcon>
                      <ListItemText
                        primary={adminModule.title}
                        primaryTypographyProps={{
                          variant: "body2",
                          fontWeight: 600,
                        }}
                      />
                      {isActive ? (
                        <ChevronRightIcon
                          fontSize="small"
                          sx={{ color: "inherit", opacity: 0.7 }}
                        />
                      ) : null}
                    </ListItemButton>
                  </ListItem>
                );
              })}
            </List>
          </CardContent>
        </Card>

        {/* 当前任务摘要 */}
        <Card variant="outlined" component="section" aria-label="当前任务上下文">
          <CardContent sx={{ py: 1.5, "&:last-child": { pb: 1.5 } }}>
            {task ? (
              <Stack spacing={1}>
                <Stack direction="row" alignItems="center" justifyContent="space-between" spacing={1}>
                  <Typography
                    component="h3"
                    variant="subtitle2"
                    sx={{
                      fontWeight: 700,
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {task.competition_name}
                  </Typography>
                  <Chip
                    color={
                      task.status === "ready_to_export" || task.status === "completed"
                        ? "success"
                        : task.status === "draft"
                          ? "default"
                          : "warning"
                    }
                    size="small"
                    label={formatTaskStatus(task.status)}
                    sx={{ flexShrink: 0 }}
                  />
                </Stack>
                <Divider />
                <Box
                  sx={{
                    display: "grid",
                    gap: 0.75,
                    gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
                  }}
                  component="dl"
                >
                  <Box sx={{ p: 1, borderRadius: 1, bgcolor: "action.hover" }}>
                    <Typography component="dt" variant="caption" color="text.secondary" sx={{ fontSize: "0.7rem" }}>
                      阶段
                    </Typography>
                    <Typography component="dd" variant="body2" sx={{ fontWeight: 600, m: 0, fontSize: "0.8rem" }}>
                      {taskStage?.label}
                    </Typography>
                  </Box>
                  <Box sx={{ p: 1, borderRadius: 1, bgcolor: "action.hover" }}>
                    <Typography component="dt" variant="caption" color="text.secondary" sx={{ fontSize: "0.7rem" }}>
                      截止
                    </Typography>
                    <Typography component="dd" variant="body2" sx={{ fontWeight: 600, m: 0, fontSize: "0.8rem" }}>
                      {formatDateTime(task.deadline)}
                    </Typography>
                  </Box>
                </Box>
                {taskId ? (
                  <>
                    <Divider />
                    <Stack
                      component="nav"
                      aria-label="当前任务快捷入口"
                      direction="row"
                      spacing={0.75}
                      useFlexGap
                      flexWrap="wrap"
                    >
                      {([
                        ["tasks", "任务详情"],
                        ["review", "材料审核"],
                        ["splits", "分摊确认"],
                        ["exports", "导出打印"],
                      ] as const).map(([moduleKey, label]) => {
                        const path = buildModulePath(moduleKey, taskId);
                        if (!path || moduleKey === activeModule) {
                          return null;
                        }
                        return (
                          <Typography
                            key={moduleKey}
                            component={RouterLink}
                            to={path}
                            variant="caption"
                            sx={{
                              px: 1,
                              py: 0.5,
                              borderRadius: 999,
                              bgcolor: "action.hover",
                              color: "text.primary",
                              textDecoration: "none",
                              fontWeight: 600,
                              "&:hover": {
                                bgcolor: "action.selected",
                              },
                            }}
                          >
                            {label}
                          </Typography>
                        );
                      })}
                    </Stack>
                  </>
                ) : null}
              </Stack>
            ) : (
              <Box
                sx={{
                  py: 1,
                  textAlign: "center",
                }}
              >
                <Typography variant="body2" color="text.secondary">
                  {taskId
                    ? "正在读取任务信息…"
                    : "从首页选择任务后显示"}
                </Typography>
              </Box>
            )}
          </CardContent>
        </Card>
      </Box>

      <Box sx={{ minWidth: 0 }}>
        <Stack spacing={2.5}>
          {header}
          {children}
        </Stack>
      </Box>
    </Box>
  );
}
