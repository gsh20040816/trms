import { useEffect, useState } from "react";
import { Link as RouterLink } from "react-router-dom";

import ArrowForwardIcon from "@mui/icons-material/ArrowForward";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";

import Alert from "@mui/material/Alert";
import Avatar from "@mui/material/Avatar";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import Stack from "@mui/material/Stack";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableContainer from "@mui/material/TableContainer";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Typography from "@mui/material/Typography";

import { ApiErrorNotice } from "../components/ApiErrorNotice";
import { trmsApi } from "../lib/api/trms";
import { formatUserIdentityLabel } from "../lib/ui-text";
import type { ReimbursementTask, TaskStatus } from "../lib/api/types";
import { formatTaskStatus } from "../lib/ui-text";
import { useAuthSession } from "./auth-store";

type MemberTaskListState =
  | { status: "loading" }
  | { status: "error"; error: unknown }
  | { status: "ready"; items: ReimbursementTask[] };

const NEXT_ACTIONS: Record<TaskStatus, string> = {
  draft: "等待开放",
  open: "提交材料",
  closed: "确认费用",
  reviewing: "确认费用",
  ready_to_export: "查看结果",
  completed: "查看归档",
};

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function getTaskSortPriority(status: TaskStatus) {
  switch (status) {
    case "open":
      return 0;
    case "closed":
    case "reviewing":
      return 1;
    case "ready_to_export":
      return 2;
    case "completed":
      return 3;
    case "draft":
    default:
      return 4;
  }
}

function buildStatusChipColor(status: TaskStatus): "default" | "info" | "warning" | "success" {
  if (status === "open") {
    return "info";
  }
  if (status === "reviewing" || status === "closed") {
    return "warning";
  }
  if (status === "ready_to_export" || status === "completed") {
    return "success";
  }
  return "default";
}

function buildWorkbenchLink(task: ReimbursementTask) {
  return `/member/invoices/workbench?taskId=${encodeURIComponent(task.id)}`;
}

function buildDirectActionLink(task: ReimbursementTask) {
  if (task.status === "open") {
    return `/member/materials/upload?taskId=${encodeURIComponent(task.id)}`;
  }
  if (task.status === "closed" || task.status === "reviewing") {
    return `/member/expenses/confirm?taskId=${encodeURIComponent(task.id)}`;
  }
  return `/member/materials/status?taskId=${encodeURIComponent(task.id)}`;
}

function StatTile({
  label,
  value,
  description,
  accent,
}: {
  label: string;
  value: number | string;
  description: string;
  accent: "primary" | "info" | "warning" | "success";
}) {
  return (
    <Card variant="outlined" sx={{ height: "100%" }}>
      <CardContent>
        <Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ mb: 1 }}>
          <Typography variant="overline" color="text.secondary">
            {label}
          </Typography>
          <Avatar
            variant="rounded"
            sx={{
              width: 32,
              height: 32,
              bgcolor: `${accent}.main`,
              color: `${accent}.contrastText`,
              fontSize: 14,
              fontWeight: 700,
            }}
          >
            {typeof value === "number" ? value : value.slice(0, 1)}
          </Avatar>
        </Stack>
        <Typography variant="h4" sx={{ mb: 0.5, lineHeight: 1.1 }}>
          {value}
        </Typography>
        <Typography variant="body2" color="text.secondary">
          {description}
        </Typography>
      </CardContent>
    </Card>
  );
}

export function MemberTaskListPage() {
  const session = useAuthSession();
  const [state, setState] = useState<MemberTaskListState>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;

    async function loadVisibleTasks() {
      if (!session || session.role !== "member") {
        return;
      }

      setState({ status: "loading" });

      try {
        const allTasks = await trmsApi.listTasks();
        const visibleTasks = allTasks.filter((task) => task.member_ids.includes(session.actorId));

        if (cancelled) {
          return;
        }

        setState({
          status: "ready",
          items: visibleTasks,
        });
      } catch (error) {
        if (cancelled) {
          return;
        }

        setState({
          status: "error",
          error,
        });
      }
    }

    void loadVisibleTasks();

    return () => {
      cancelled = true;
    };
  }, [session]);

  if (!session || session.role !== "member") {
    return null;
  }

  const visibleTasks = state.status === "ready" ? state.items : [];
  const sortedVisibleTasks = [...visibleTasks].sort((left, right) => {
    const priorityDifference = getTaskSortPriority(left.status) - getTaskSortPriority(right.status);
    if (priorityDifference !== 0) {
      return priorityDifference;
    }
    return left.deadline.localeCompare(right.deadline);
  });
  const dashboardStats = {
    total: visibleTasks.length,
    openCount: visibleTasks.filter((task) => task.status === "open").length,
    reviewCount: visibleTasks.filter((task) => task.status === "closed" || task.status === "reviewing").length,
    archivedCount: visibleTasks.filter((task) => task.status === "ready_to_export" || task.status === "completed").length,
  };

  return (
    <Stack spacing={3}>
      <Box>
        <Typography variant="overline" color="text.secondary">
          成员工作台
        </Typography>
        <Stack
          direction={{ xs: "column", md: "row" }}
          alignItems={{ xs: "flex-start", md: "flex-end" }}
          justifyContent="space-between"
          spacing={2}
          sx={{ mt: 0.5 }}
        >
          <Box>
            <Typography component="h1" variant="h3">
              我的报销任务
            </Typography>
            <Typography variant="body1" color="text.secondary" sx={{ mt: 1, maxWidth: 720 }}>
              先看我参与的任务，再进入单任务发票工作台处理上传、补材料和费用确认。
            </Typography>
            <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 1 }}>
              当前成员：{formatUserIdentityLabel(session)}
            </Typography>
          </Box>
          <Button
            component={RouterLink}
            to="/member/invoices/workbench"
            variant="contained"
            size="large"
            endIcon={<OpenInNewIcon />}
          >
            进入发票工作台
          </Button>
        </Stack>
      </Box>

      <Box
        aria-label="成员任务概览"
        sx={{
          display: "grid",
          gap: 2,
          gridTemplateColumns: { xs: "1fr", sm: "repeat(2, minmax(0, 1fr))", md: "repeat(4, minmax(0, 1fr))" },
        }}
      >
        <StatTile
          label="我参与的任务"
          value={dashboardStats.total}
          description="当前你可以查看或处理的全部报销任务。"
          accent="primary"
        />
        <StatTile
          label="正在收集"
          value={dashboardStats.openCount}
          description="优先在截止前提交或补充材料。"
          accent="info"
        />
        <StatTile
          label="待补充或确认"
          value={dashboardStats.reviewCount}
          description="需要查看材料状态或确认费用的任务。"
          accent="warning"
        />
        <StatTile
          label="已进入归档"
          value={dashboardStats.archivedCount}
          description="主要用于查询结果和回看记录。"
          accent="success"
        />
      </Box>

      {state.status === "loading" ? (
        <Card>
          <CardContent>
            <Stack direction="row" alignItems="center" spacing={2}>
              <CircularProgress size={20} />
              <Box>
                <Typography variant="subtitle1">正在加载成员可见任务</Typography>
                <Typography variant="body2" color="text.secondary">
                  正在读取你参与的报销任务，请稍候。
                </Typography>
              </Box>
            </Stack>
          </CardContent>
        </Card>
      ) : null}

      {state.status === "error" ? <ApiErrorNotice error={state.error} /> : null}

      {state.status === "ready" && sortedVisibleTasks.length === 0 ? (
        <Alert severity="info" sx={{ alignItems: "flex-start" }}>
          <Typography variant="subtitle1" component="div" sx={{ fontWeight: 700 }}>
            当前没有可见报销任务
          </Typography>
          <Typography variant="body2" sx={{ mt: 0.5 }}>
            管理员创建并发布包含你的报销任务后，会在这里显示。
          </Typography>
        </Alert>
      ) : null}

      {state.status === "ready" && sortedVisibleTasks.length > 0 ? (
        <Card>
          <CardContent>
            <Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ mb: 1.5 }}>
              <Box>
                <Typography variant="h6">任务列表</Typography>
                <Typography variant="body2" color="text.secondary">
                  优先从这里进入单任务发票工作台；如需跳过汇总页，也可以直接执行当前下一步。
                </Typography>
              </Box>
              <Chip color="info" size="small" label={`共 ${sortedVisibleTasks.length} 条`} />
            </Stack>
            <TableContainer>
              <Table aria-label="成员任务列表" size="small">
                <caption className="sr-only">成员任务列表</caption>
                <TableHead>
                  <TableRow>
                    <TableCell>任务名称</TableCell>
                    <TableCell>当前状态</TableCell>
                    <TableCell>截止时间</TableCell>
                    <TableCell>下一步</TableCell>
                    <TableCell align="right">操作</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {sortedVisibleTasks.map((task) => (
                    <TableRow key={task.id} hover>
                      <TableCell>
                        <Typography variant="subtitle2">{task.competition_name}</Typography>
                        <Typography variant="caption" color="text.secondary">
                          {task.competition_location}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Chip
                          size="small"
                          color={buildStatusChipColor(task.status)}
                          label={formatTaskStatus(task.status)}
                          variant={buildStatusChipColor(task.status) === "default" ? "outlined" : "filled"}
                        />
                      </TableCell>
                      <TableCell>{formatDateTime(task.deadline)}</TableCell>
                      <TableCell>{NEXT_ACTIONS[task.status]}</TableCell>
                      <TableCell align="right">
                        <Stack direction="row" spacing={1} justifyContent="flex-end" useFlexGap flexWrap="wrap">
                          <Button
                            component={RouterLink}
                            to={buildWorkbenchLink(task)}
                            variant="contained"
                            size="small"
                            endIcon={<ArrowForwardIcon />}
                          >
                            进入工作台
                          </Button>
                          <Button
                            component={RouterLink}
                            to={buildDirectActionLink(task)}
                            variant="outlined"
                            size="small"
                          >
                            {NEXT_ACTIONS[task.status]}
                          </Button>
                        </Stack>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </CardContent>
        </Card>
      ) : null}
    </Stack>
  );
}
