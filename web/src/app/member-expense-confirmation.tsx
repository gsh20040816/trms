import { useEffect, useState } from "react";
import { Link as RouterLink, useSearchParams } from "react-router-dom";

import Button from "@mui/material/Button";
import MenuItem from "@mui/material/MenuItem";
import TextField from "@mui/material/TextField";

import { ApiErrorNotice } from "../components/ApiErrorNotice";
import {
  EmptyState,
  PageHeader,
  RoleWorkspace,
  SectionCard,
  StatCard,
  StatusBadge,
} from "../components/dashboard";
import { useSnackbar } from "../components/use-snackbar";
import { ApiError } from "../lib/api/client";
import { trmsApi } from "../lib/api/trms";
import { formatUserIdentityLabel } from "../lib/ui-text";
import type {
  ConfirmationStatus,
  ExpenseDetailItem,
  ExpenseDetailList,
  ExpenseType,
  MaterialRecord,
  MaterialType,
  ReimbursementTask,
  TaskStatus,
} from "../lib/api/types";
import { useAuthSession } from "./auth-store";

type VisibleTaskState =
  | { status: "loading" }
  | { status: "error"; error: unknown }
  | { status: "ready"; visibleTasks: ReimbursementTask[] };

type SelectedTaskExpenseState =
  | { status: "idle" }
  | { status: "loading"; task: ReimbursementTask }
  | { status: "error"; task: ReimbursementTask; error: unknown }
  | { status: "ready"; task: ReimbursementTask; details: ExpenseDetailList; items: ExpenseConfirmationItem[] };

type ExpenseConfirmationItem = {
  detail: ExpenseDetailItem;
  supportingMaterials: MaterialRecord[];
};

const TASK_STATUS_LABELS: Record<TaskStatus, string> = {
  draft: "草稿",
  open: "收集中",
  closed: "复核中",
  reviewing: "复核中",
  ready_to_export: "可导出",
  completed: "已完成",
};

const EXPENSE_TYPE_LABELS: Record<ExpenseType, string> = {
  registration: "参赛费",
  railway: "铁路交通",
  airfare: "航空交通",
  local_transport: "市内交通",
  hotel: "住宿费",
  other: "其他费用",
};

const MATERIAL_TYPE_LABELS: Record<MaterialType, string> = {
  invoice: "发票",
  payment_record: "支付记录",
  competition_notice: "比赛通知",
  itinerary: "行程单",
  order_screenshot: "订单截图",
  other_attachment: "其他附件",
};

const CONFIRMATION_STATUS_LABELS: Record<ConfirmationStatus, string> = {
  pending: "待确认",
  confirmed: "已确认",
  disputed: "有异议",
};

function pickSelectedTaskId(
  tasks: ReimbursementTask[],
  preferredTaskId: string | null,
  currentTaskId: string,
) {
  const visibleTaskIds = new Set(tasks.map((task) => task.id));
  if (currentTaskId.length > 0 && visibleTaskIds.has(currentTaskId)) {
    return currentTaskId;
  }
  if (preferredTaskId && visibleTaskIds.has(preferredTaskId)) {
    return preferredTaskId;
  }
  return tasks[0]?.id ?? "";
}

function buildExpenseConfirmationItems(
  details: ExpenseDetailList,
  supportingMaterialsByInvoiceId: Map<string, MaterialRecord[]>,
) {
  return [...details.items]
    .sort((left, right) => {
      const leftTime = left.invoice.transaction_time ?? left.updated_at;
      const rightTime = right.invoice.transaction_time ?? right.updated_at;
      return rightTime.localeCompare(leftTime);
    })
    .map((detail) => ({
      detail,
      supportingMaterials: supportingMaterialsByInvoiceId.get(detail.invoice.id) ?? [],
    }));
}

function getCurrentConfirmationStatus(item: ExpenseConfirmationItem): ConfirmationStatus {
  return item.detail.confirmation?.status ?? "pending";
}

function countItemsByStatus(
  items: ExpenseConfirmationItem[],
  targetStatus: ConfirmationStatus,
) {
  return items.filter((item) => getCurrentConfirmationStatus(item) === targetStatus).length;
}

function formatTaskStatus(status: TaskStatus) {
  return TASK_STATUS_LABELS[status];
}

function formatExpenseType(expenseType: ExpenseType) {
  return EXPENSE_TYPE_LABELS[expenseType] ?? expenseType;
}

function formatMaterialType(materialType: MaterialType) {
  return MATERIAL_TYPE_LABELS[materialType] ?? materialType;
}

function formatConfirmationStatus(status: ConfirmationStatus) {
  return CONFIRMATION_STATUS_LABELS[status];
}

function formatCurrencyFromCents(cents: number) {
  return `￥${(cents / 100).toFixed(2)}`;
}

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function resolveInvoiceTimeLabel(detail: ExpenseDetailItem) {
  if (detail.invoice.transaction_time) {
    return formatDateTime(detail.invoice.transaction_time);
  }
  if (detail.invoice.issue_date) {
    return detail.invoice.issue_date;
  }
  return "未录入";
}

function isSplitStaleError(error: unknown) {
  return error instanceof ApiError && error.status === 404 && error.message === "split not found";
}

function buildConfirmationBadgeTone(status: ConfirmationStatus) {
  switch (status) {
    case "confirmed":
      return "success" as const;
    case "disputed":
      return "danger" as const;
    default:
      return "warning" as const;
  }
}

export function MemberExpenseConfirmationPage() {
  const session = useAuthSession();
  const { showError, showSuccess, showWarning } = useSnackbar();
  const [searchParams] = useSearchParams();
  const preferredTaskId = searchParams.get("taskId");
  const [taskState, setTaskState] = useState<VisibleTaskState>({ status: "loading" });
  const [selectedTaskId, setSelectedTaskId] = useState("");
  const [expenseState, setExpenseState] = useState<SelectedTaskExpenseState>({ status: "idle" });
  const [refreshNonce, setRefreshNonce] = useState(0);
  const [submittingSplitId, setSubmittingSplitId] = useState<string | null>(null);
  const [staleSplitId, setStaleSplitId] = useState<string | null>(null);
  const [disputeReasons, setDisputeReasons] = useState<Record<string, string>>({});
  const [disputeErrors, setDisputeErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    let cancelled = false;

    async function loadVisibleTasks() {
      if (!session || session.role !== "member") {
        return;
      }

      setTaskState({ status: "loading" });

      try {
        const allTasks = await trmsApi.listTasks();
        const visibleTasks = allTasks.filter((task) => task.member_ids.includes(session.actorId));

        if (cancelled) {
          return;
        }

        setTaskState({ status: "ready", visibleTasks });
        setSelectedTaskId((currentTaskId) => pickSelectedTaskId(visibleTasks, preferredTaskId, currentTaskId));
      } catch (error) {
        if (cancelled) {
          return;
        }

        setTaskState({ status: "error", error });
      }
    }

    void loadVisibleTasks();

    return () => {
      cancelled = true;
    };
  }, [preferredTaskId, session]);

  useEffect(() => {
    let cancelled = false;

    async function loadSelectedTaskExpenses(task: ReimbursementTask) {
      setExpenseState({ status: "loading", task });

      try {
        const details = await trmsApi.listTaskExpenseDetails(task.id, session!.actorId);
        const uniqueInvoiceIds = [...new Set(details.items.map((item) => item.invoice.id))];
        const supportingEntries = await Promise.all(
          uniqueInvoiceIds.map(async (invoiceId) => [
            invoiceId,
            (await trmsApi.listInvoiceSupportingMaterials(invoiceId)).items,
          ] as const),
        );

        if (cancelled) {
          return;
        }

        const supportingMaterialsByInvoiceId = new Map(supportingEntries);
        setExpenseState({
          status: "ready",
          task,
          details,
          items: buildExpenseConfirmationItems(details, supportingMaterialsByInvoiceId),
        });
      } catch (error) {
        if (cancelled) {
          return;
        }

        setExpenseState({ status: "error", task, error });
      }
    }

    if (!session || session.role !== "member" || taskState.status !== "ready") {
      return () => {
        cancelled = true;
      };
    }

    const selectedTask = taskState.visibleTasks.find((task) => task.id === selectedTaskId) ?? null;
    if (!selectedTask) {
      return () => {
        cancelled = true;
      };
    }

    void loadSelectedTaskExpenses(selectedTask);

    return () => {
      cancelled = true;
    };
  }, [refreshNonce, selectedTaskId, session, taskState]);

  if (!session || session.role !== "member") {
    return null;
  }

  const actorId = session.actorId;
  const visibleTasks = taskState.status === "ready" ? taskState.visibleTasks : [];
  const selectedTask = visibleTasks.find((task) => task.id === selectedTaskId) ?? null;
  const readyItems = expenseState.status === "ready" ? expenseState.items : [];
  const totalAmountCents = expenseState.status === "ready" ? expenseState.details.total_amount_cents : 0;
  const pendingCount = countItemsByStatus(readyItems, "pending");
  const confirmedCount = countItemsByStatus(readyItems, "confirmed");
  const disputedCount = countItemsByStatus(readyItems, "disputed");
  const summaryCards = expenseState.status === "ready" ? [
    {
      label: "本人费用",
      value: readyItems.length,
      description: "当前任务下与你相关的费用明细条数。",
    },
    {
      label: "总金额",
      value: formatCurrencyFromCents(totalAmountCents),
      description: "当前任务下分到你名下的费用合计。",
    },
    {
      label: "待确认",
      value: pendingCount,
      description: "仍需你确认或提出异议的费用条数。",
    },
    {
      label: "已处理",
      value: `${confirmedCount + disputedCount}/${readyItems.length}`,
      description: "已确认或已提出异议的费用条数。",
    },
  ] : [];

  async function submitConfirmation(
    item: ExpenseConfirmationItem,
    status: Extract<ConfirmationStatus, "confirmed" | "disputed">,
  ) {
    const disputeReason = disputeReasons[item.detail.split_id]?.trim() ?? "";
    if (status === "disputed" && !disputeReason) {
      setDisputeErrors((current) => ({
        ...current,
        [item.detail.split_id]: "提交异议时必须填写原因。",
      }));
      return;
    }

    setStaleSplitId(null);
    setDisputeErrors((current) => {
      if (!(item.detail.split_id in current)) {
        return current;
      }
      const next = { ...current };
      delete next[item.detail.split_id];
      return next;
    });
    setSubmittingSplitId(item.detail.split_id);

    try {
      await trmsApi.submitSplitConfirmation(item.detail.split_id, {
        actor_id: actorId,
        member_id: actorId,
        status,
        dispute_reason: status === "disputed" ? disputeReason : null,
      });
      if (status === "confirmed") {
        showSuccess("已提交确认，页面已刷新最新确认状态。");
      } else {
        showWarning("已提交异议，页面已刷新最新确认状态。");
      }
      if (status === "disputed") {
        setDisputeReasons((current) => ({
          ...current,
          [item.detail.split_id]: "",
        }));
      }
      setRefreshNonce((current) => current + 1);
    } catch (error) {
      if (isSplitStaleError(error)) {
        setStaleSplitId(item.detail.split_id);
        return;
      }
      showError(error instanceof Error ? error.message : "费用确认提交失败，请稍后重试。");
    } finally {
      setSubmittingSplitId(null);
    }
  }

  return (
    <RoleWorkspace
      header={(
        <PageHeader
          eyebrow="费用确认"
          title="成员费用确认"
          description="在单任务上下文中核对当前分到自己名下的费用、关联附件和确认状态。"
          meta={`当前成员：${formatUserIdentityLabel(session)}`}
          actions={(
            <div className="page-actions">
              <Button
                component={RouterLink}
                variant="outlined"
                to={selectedTask ? `/member/invoices/workbench?taskId=${encodeURIComponent(selectedTask.id)}` : "/member/invoices/workbench"}
              >
                返回当前任务工作台
              </Button>
            </div>
          )}
        />
      )}
      summary={summaryCards.length > 0 ? (
        <section className="stat-grid" aria-label="费用确认摘要">
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
      {taskState.status === "loading" ? (
        <SectionCard title="正在加载可见任务" description="正在读取当前成员可访问的报销任务，以便定位待确认的费用明细。" />
      ) : null}

      {taskState.status === "error" ? <ApiErrorNotice error={taskState.error} /> : null}

      {taskState.status === "ready" && visibleTasks.length === 0 ? (
        <EmptyState
          title="当前没有可确认费用的报销任务"
          description="管理员创建并发布相关任务后，你可以在这里确认个人费用。"
        />
      ) : null}

      {taskState.status === "ready" && visibleTasks.length > 0 ? (
        <SectionCard
          title="当前任务上下文"
          description="先固定在一个任务里处理费用确认，再查看单张费用的发票和附件细节。"
          action={selectedTask ? <StatusBadge tone="info">{formatTaskStatus(selectedTask.status)}</StatusBadge> : null}
        >
          <div className="admin-form-grid">
            <TextField
              select
              label="目标任务"
              value={selectedTaskId}
              fullWidth
              helperText="这里只列出你可以查看和确认的任务。"
              onChange={(event) => {
                setSelectedTaskId(event.target.value);
                setStaleSplitId(null);
              }}
            >
              {visibleTasks.map((task) => (
                <MenuItem key={task.id} value={task.id}>
                  {task.competition_name}（{task.id}）
                </MenuItem>
              ))}
            </TextField>
            <div className="field-stack">
              <span>相关入口</span>
              <div className="inline-actions">
                <Button component={RouterLink} variant="outlined" to="/member">
                  返回成员任务列表
                </Button>
                {selectedTask ? (
                  <Button
                    component={RouterLink}
                    variant="outlined"
                    to={`/member/materials/status?taskId=${encodeURIComponent(selectedTask.id)}`}
                  >
                    查看材料状态
                  </Button>
                ) : null}
              </div>
            </div>
            {selectedTask ? (
              <dl className="task-meta-grid member-status-meta-grid">
                <div>
                  <dt>比赛名称</dt>
                  <dd>{selectedTask.competition_name}</dd>
                </div>
                <div>
                  <dt>截止时间</dt>
                  <dd>{formatDateTime(selectedTask.deadline)}</dd>
                </div>
                <div>
                  <dt>当前成员</dt>
                  <dd>{formatUserIdentityLabel(session)}</dd>
                </div>
              </dl>
            ) : null}
          </div>
        </SectionCard>
      ) : null}

      {selectedTask && expenseState.status === "loading" ? (
        <SectionCard title="正在汇总个人费用明细" description="正在读取当前任务下与你相关的分摊、确认状态和关联附件摘要。" />
      ) : null}

      {selectedTask && expenseState.status === "error" ? <ApiErrorNotice error={expenseState.error} /> : null}

      {expenseState.status === "ready" && readyItems.length === 0 ? (
        <EmptyState
          title="当前任务下没有待展示的个人费用"
          description="当前还没有分配到你名下的费用，管理员完成分摊后会在这里显示。"
        />
      ) : null}

      {expenseState.status === "ready" && readyItems.length > 0 ? (
        <section className="member-confirmation-list" aria-label="成员费用明细列表">
          {readyItems.map((item) => {
            const currentStatus = getCurrentConfirmationStatus(item);
            const disputeReason = disputeReasons[item.detail.split_id] ?? "";
            const disputeError = disputeErrors[item.detail.split_id];
            const isSubmitting = submittingSplitId === item.detail.split_id;
            const isStale = staleSplitId === item.detail.split_id;

            return (
              <article key={item.detail.split_id} className="status-card member-confirmation-card">
                <div className="member-status-section-header">
                  <div>
                    <p className="task-card-id">费用明细 {item.detail.split_id}</p>
                    <h2>{item.detail.invoice.invoice_number}</h2>
                  </div>
                  <StatusBadge tone={buildConfirmationBadgeTone(currentStatus)}>
                    {formatConfirmationStatus(currentStatus)}
                  </StatusBadge>
                </div>

                <dl className="task-meta-grid member-status-meta-grid">
                  <div>
                    <dt>归属金额</dt>
                    <dd>{formatCurrencyFromCents(item.detail.amount_cents)}</dd>
                  </div>
                  <div>
                    <dt>发票总额</dt>
                    <dd>{formatCurrencyFromCents(item.detail.invoice.amount_cents)}</dd>
                  </div>
                  <div>
                    <dt>费用类型</dt>
                    <dd>{formatExpenseType(item.detail.invoice.expense_type)}</dd>
                  </div>
                  <div>
                    <dt>明细版本</dt>
                    <dd>v{item.detail.split_version}</dd>
                  </div>
                  <div>
                    <dt>交易/开票时间</dt>
                    <dd>{resolveInvoiceTimeLabel(item.detail)}</dd>
                  </div>
                  <div>
                    <dt>最近确认更新时间</dt>
                    <dd>{item.detail.confirmation ? formatDateTime(item.detail.confirmation.updated_at) : "尚未确认"}</dd>
                  </div>
                </dl>

                <section className="member-status-section">
                  <div className="member-status-section-header">
                    <h4>关联发票摘要</h4>
                    <StatusBadge tone="info">{item.detail.invoice.id}</StatusBadge>
                  </div>
                  <ul className="member-status-detail-list">
                    <li>购买方：{item.detail.invoice.buyer_name}</li>
                    <li>销售方：{item.detail.invoice.seller_name ?? "未录入"}</li>
                    <li>发票材料：{item.detail.invoice.material_id}</li>
                    <li>任务成员备注：{item.detail.note ?? "无"}</li>
                  </ul>
                </section>

                <section className="member-status-section">
                  <div className="member-status-section-header">
                    <h4>关联附件摘要</h4>
                    <StatusBadge tone="info">{item.supportingMaterials.length} 份</StatusBadge>
                  </div>
                  {item.supportingMaterials.length === 0 ? (
                    <p className="field-hint">当前发票还没有已关联的辅助材料；如果你认为缺少支付记录、行程单或比赛通知，应先补材料或联系管理员关联。</p>
                  ) : (
                    <ul className="member-status-message-list">
                      {item.supportingMaterials.map((material) => (
                        <li key={material.id}>
                          <strong>{formatMaterialType(material.material_type)} / {material.original_filename}</strong>
                          <span>材料编号：{material.id}</span>
                          <span>上传时间：{formatDateTime(material.created_at)}</span>
                        </li>
                      ))}
                    </ul>
                  )}
                </section>

                {item.detail.confirmation?.dispute_reason ? (
                  <section className="member-status-section">
                    <div className="member-status-section-header">
                      <h4>当前异议记录</h4>
                      <StatusBadge tone="danger">需管理员处理</StatusBadge>
                    </div>
                    <p>{item.detail.confirmation.dispute_reason}</p>
                  </section>
                ) : null}

                <section className="member-status-section">
                  <div className="member-status-section-header">
                    <h4>确认或提出异议</h4>
                    <StatusBadge tone="info">成员本人提交</StatusBadge>
                  </div>
                  <TextField
                    className="confirmation-reason-field"
                    label="异议原因"
                    multiline
                    minRows={3}
                    value={disputeReason}
                    placeholder="如果金额、归属或附件关联不正确，请写明原因。"
                    error={Boolean(disputeError)}
                    helperText={disputeError}
                    slotProps={{
                      htmlInput: {
                        "aria-label": `异议原因 ${item.detail.split_id}`,
                      },
                    }}
                    onChange={(event) => {
                      const nextValue = event.target.value;
                      setDisputeReasons((current) => ({
                        ...current,
                        [item.detail.split_id]: nextValue,
                      }));
                      setDisputeErrors((current) => {
                        if (!(item.detail.split_id in current)) {
                          return current;
                        }
                        const next = { ...current };
                        delete next[item.detail.split_id];
                        return next;
                      });
                    }}
                  />
                  <div className="inline-actions">
                    <Button
                      type="button"
                      variant="contained"
                      disabled={isSubmitting}
                      onClick={() => {
                        void submitConfirmation(item, "confirmed");
                      }}
                    >
                      {isSubmitting ? "提交中..." : "确认这笔费用"}
                    </Button>
                    <Button
                      type="button"
                      variant="outlined"
                      disabled={isSubmitting}
                      onClick={() => {
                        void submitConfirmation(item, "disputed");
                      }}
                    >
                      {isSubmitting ? "提交中..." : "提交异议"}
                    </Button>
                    {isStale ? (
                      <Button
                        type="button"
                        variant="outlined"
                        onClick={() => {
                          setStaleSplitId(null);
                          setRefreshNonce((current) => current + 1);
                        }}
                      >
                        重新加载明细
                      </Button>
                    ) : null}
                  </div>
                  {isStale ? (
                    <p className="field-error-block">
                      当前费用明细版本已失效，通常是管理员刚修改了分摊金额或成员归属；请刷新后再确认。
                    </p>
                  ) : null}
                </section>
              </article>
            );
          })}
        </section>
      ) : null}
    </RoleWorkspace>
  );
}
