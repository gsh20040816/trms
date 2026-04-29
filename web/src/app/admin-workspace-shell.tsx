import type { ReactNode } from "react";
import { Link as RouterLink } from "react-router-dom";

import AssignmentIcon from "@mui/icons-material/Assignment";
import AssignmentTurnedInIcon from "@mui/icons-material/AssignmentTurnedIn";
import ChevronRightIcon from "@mui/icons-material/ChevronRight";
import DashboardIcon from "@mui/icons-material/Dashboard";
import DownloadIcon from "@mui/icons-material/Download";
import FactCheckIcon from "@mui/icons-material/FactCheck";
import NotificationsActiveIcon from "@mui/icons-material/NotificationsActive";
import PaymentsIcon from "@mui/icons-material/Payments";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
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

import { StatusBadge } from "../components/dashboard";
import type { ReimbursementTask } from "../lib/api/types";
import { formatTaskStatus } from "../lib/ui-text";
import { describeAdminTaskStage } from "./admin-task-stage";

export type AdminModuleKey =
  | "overview"
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
  description: string;
  Icon: typeof DashboardIcon;
};

const ADMIN_MODULES: AdminModuleDefinition[] = [
  {
    key: "overview",
    title: "首页总览",
    description: "按任务推进查看当前最紧急的处理事项。",
    Icon: DashboardIcon,
  },
  {
    key: "tasks",
    title: "任务管理",
    description: "查看任务配置、成员范围和状态流转。",
    Icon: AssignmentIcon,
  },
  {
    key: "review",
    title: "材料审核",
    description: "集中处理识别异常、缺失材料和复核问题。",
    Icon: FactCheckIcon,
  },
  {
    key: "corrections",
    title: "成员提醒",
    description: "统一跟进成员补材料、更正和异议处理。",
    Icon: NotificationsActiveIcon,
  },
  {
    key: "splits",
    title: "分摊确认",
    description: "调整费用归属并跟踪成员确认状态。",
    Icon: PaymentsIcon,
  },
  {
    key: "exports",
    title: "导出打印",
    description: "查看导出准备度并生成最终材料包。",
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
    case "tasks":
      return taskId ? `/admin/tasks/${taskId}` : "/admin/tasks/new";
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

  return (
    <Box
      sx={{
        display: "grid",
        gap: 2.5,
        gridTemplateColumns: { xs: "1fr", md: "minmax(260px, 320px) minmax(0, 1fr)" },
        alignItems: "start",
      }}
    >
      <Box
        component="aside"
        sx={{
          display: "grid",
          gap: 2,
          position: { md: "sticky" },
          top: { md: 88 },
        }}
      >
        <Card variant="outlined" component="section">
          <CardContent>
            <Stack direction="row" alignItems="flex-start" justifyContent="space-between" spacing={1}>
              <Box>
                <Typography variant="overline" color="text.secondary">
                  管理员工作台
                </Typography>
                <Typography component="h2" variant="h6">
                  任务推进导航
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                  固定模块和当前任务上下文保持在同一位置。
                </Typography>
              </Box>
              <StatusBadge tone="info">导航骨架</StatusBadge>
            </Stack>

            <Divider sx={{ my: 1.5 }} />

            <List
              component="nav"
              aria-label="管理员模块导航"
              dense
              disablePadding
              sx={{ display: "grid", gap: 0.5 }}
            >
              {ADMIN_MODULES.map((adminModule) => {
                const path = buildModulePath(adminModule.key, taskId);
                const isActive = adminModule.key === activeModule;
                if (!path) {
                  return (
                    <ListItem
                      key={adminModule.key}
                      disablePadding
                      aria-disabled="true"
                      sx={{ opacity: 0.55 }}
                    >
                      <ListItemButton
                        disabled
                        sx={{
                          borderRadius: 2,
                          alignItems: "flex-start",
                          py: 1,
                        }}
                      >
                        <ListItemIcon sx={{ minWidth: 36, mt: 0.5 }}>
                          <adminModule.Icon fontSize="small" />
                        </ListItemIcon>
                        <ListItemText
                          primary={adminModule.title}
                          secondary={adminModule.description}
                          primaryTypographyProps={{ fontWeight: 600 }}
                          secondaryTypographyProps={{ variant: "caption" }}
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
                        borderRadius: 2,
                        alignItems: "flex-start",
                        py: 1,
                        "&.Mui-selected": {
                          bgcolor: "action.selected",
                        },
                      }}
                    >
                      <ListItemIcon
                        sx={{
                          minWidth: 36,
                          mt: 0.5,
                          color: isActive ? "primary.main" : "text.secondary",
                        }}
                      >
                        <adminModule.Icon fontSize="small" />
                      </ListItemIcon>
                      <ListItemText
                        primary={adminModule.title}
                        secondary={adminModule.description}
                        primaryTypographyProps={{
                          fontWeight: 600,
                          color: isActive ? "primary.main" : "text.primary",
                        }}
                        secondaryTypographyProps={{ variant: "caption" }}
                      />
                      {isActive ? (
                        <ChevronRightIcon
                          fontSize="small"
                          sx={{ color: "primary.main", mt: 0.5 }}
                        />
                      ) : null}
                    </ListItemButton>
                  </ListItem>
                );
              })}
            </List>
          </CardContent>
        </Card>

        <Card variant="outlined" component="section" aria-label="当前任务上下文">
          <CardContent>
            <Box>
              <Typography component="h2" variant="h6">
                当前任务上下文
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                把当前任务阶段、状态和快捷入口固定下来，避免处理过程中丢失上下文。
              </Typography>
            </Box>

            <Divider sx={{ my: 1.5 }} />

            {task ? (
              <Stack spacing={1.5}>
                <Stack direction="row" alignItems="flex-start" justifyContent="space-between" spacing={1}>
                  <Box sx={{ minWidth: 0 }}>
                    <Typography variant="caption" color="text.secondary">
                      任务编号 {task.id}
                    </Typography>
                    <Typography component="h3" variant="subtitle1" sx={{ fontWeight: 700 }}>
                      {task.competition_name}
                    </Typography>
                  </Box>
                  <Chip
                    color={
                      task.status === "ready_to_export" || task.status === "completed"
                        ? "success"
                        : "warning"
                    }
                    size="small"
                    label={formatTaskStatus(task.status)}
                  />
                </Stack>
                <Box
                  sx={{
                    display: "grid",
                    gap: 1,
                    gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
                  }}
                  component="dl"
                >
                  <Box sx={{ p: 1.25, borderRadius: 1.5, bgcolor: "action.hover" }}>
                    <Typography component="dt" variant="caption" color="text.secondary">
                      当前阶段
                    </Typography>
                    <Typography component="dd" variant="body2" sx={{ fontWeight: 600, m: 0 }}>
                      {taskStage?.label}
                    </Typography>
                  </Box>
                  <Box sx={{ p: 1.25, borderRadius: 1.5, bgcolor: "action.hover" }}>
                    <Typography component="dt" variant="caption" color="text.secondary">
                      截止时间
                    </Typography>
                    <Typography component="dd" variant="body2" sx={{ fontWeight: 600, m: 0 }}>
                      {formatDateTime(task.deadline)}
                    </Typography>
                  </Box>
                </Box>
                <Typography variant="body2" color="text.secondary">
                  {taskStage?.summary}
                </Typography>
              </Stack>
            ) : (
              <Box
                sx={{
                  p: 1.5,
                  borderRadius: 1.5,
                  border: 1,
                  borderColor: "divider",
                  borderStyle: "dashed",
                }}
              >
                <Typography component="h3" variant="subtitle2">
                  {taskId ? `任务 ${taskId}` : "尚未选中任务"}
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                  {taskId
                    ? "正在读取当前任务上下文或当前账号无权访问该任务。"
                    : "先从首页选择任务，右侧模块就会自动带入当前任务上下文。"}
                </Typography>
              </Box>
            )}

            {taskId ? (
              <Stack
                direction="row"
                spacing={1}
                useFlexGap
                flexWrap="wrap"
                aria-label="当前任务快捷入口"
                sx={{ mt: 2 }}
              >
                <Button
                  component={RouterLink}
                  to={`/admin/tasks/${taskId}`}
                  variant="outlined"
                  size="small"
                  startIcon={<AssignmentTurnedInIcon />}
                >
                  任务详情
                </Button>
                <Button
                  component={RouterLink}
                  to={`/admin/tasks/${taskId}/review`}
                  variant="outlined"
                  size="small"
                  startIcon={<FactCheckIcon />}
                >
                  材料审核
                </Button>
                <Button
                  component={RouterLink}
                  to={`/admin/tasks/${taskId}/splits`}
                  variant="outlined"
                  size="small"
                  startIcon={<PaymentsIcon />}
                >
                  分摊确认
                </Button>
                <Button
                  component={RouterLink}
                  to={`/admin/tasks/${taskId}/exports`}
                  variant="outlined"
                  size="small"
                  startIcon={<DownloadIcon />}
                >
                  导出打印
                </Button>
              </Stack>
            ) : null}
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
