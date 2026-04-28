import { useEffect, useMemo, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";

import { ApiErrorNotice } from "../components/ApiErrorNotice";
import { trmsApi } from "../lib/api/trms";
import type {
  ExpenseType,
  MaterialType,
  MissingMaterialItem,
  ReimbursementTask,
  TaskStatus,
  VisibleMissingMaterialList,
} from "../lib/api/types";
import { useAuthSession } from "./auth-store";

type GroupMode = "member" | "invoice" | "expense_type";

type MissingMaterialGroup = {
  key: string;
  title: string;
  subtitle: string;
  items: MissingMaterialItem[];
};

type AdminMissingMaterialState =
  | { status: "loading" }
  | { status: "error"; error: unknown }
  | { status: "ready"; task: ReimbursementTask; list: VisibleMissingMaterialList };

type MemberVisibleTaskState =
  | { status: "loading" }
  | { status: "error"; error: unknown }
  | { status: "ready"; visibleTasks: ReimbursementTask[] };

type SelectedTaskMissingMaterialState =
  | { status: "idle" }
  | { status: "loading"; task: ReimbursementTask }
  | { status: "error"; task: ReimbursementTask; error: unknown }
  | { status: "ready"; task: ReimbursementTask; list: VisibleMissingMaterialList };

const TASK_STATUS_LABELS: Record<TaskStatus, string> = {
  draft: "草稿",
  open: "开放提交",
  closed: "已关闭",
  reviewing: "复核中",
  ready_to_export: "可导出",
  completed: "已归档",
};

const MATERIAL_TYPE_LABELS: Record<MaterialType, string> = {
  invoice: "发票",
  payment_record: "支付记录",
  competition_notice: "比赛通知",
  itinerary: "行程单",
  order_screenshot: "订单截图",
  other_attachment: "其他附件",
};

const EXPENSE_TYPE_LABELS: Record<ExpenseType, string> = {
  registration: "参赛费",
  railway: "铁路交通",
  airfare: "航空交通",
  local_transport: "市内交通",
  hotel: "住宿费",
  other: "其他费用",
};

const GROUP_MODE_LABELS: Record<GroupMode, string> = {
  member: "按成员查看",
  invoice: "按发票查看",
  expense_type: "按费用类型查看",
};

function formatTaskStatus(status: TaskStatus) {
  return TASK_STATUS_LABELS[status];
}

function formatMaterialType(materialType: MaterialType) {
  return MATERIAL_TYPE_LABELS[materialType] ?? materialType;
}

function formatExpenseType(expenseType: ExpenseType) {
  return EXPENSE_TYPE_LABELS[expenseType] ?? expenseType;
}

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

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

function buildGroupDescriptor(item: MissingMaterialItem, groupMode: GroupMode) {
  if (groupMode === "member") {
    return {
      key: item.member_id ?? "__unresolved__",
      title: item.member_id ?? "未解析提交人",
      subtitle: item.member_id
        ? `当前成员涉及 ${formatExpenseType(item.expense_type)} 等缺失项`
        : "当前缺失项尚未解析到具体提交成员",
    };
  }

  if (groupMode === "invoice") {
    return {
      key: item.invoice_id,
      title: `发票 ${item.invoice_number}`,
      subtitle: `${formatExpenseType(item.expense_type)} / ${item.member_id ?? "未解析提交人"}`,
    };
  }

  return {
    key: item.expense_type,
    title: formatExpenseType(item.expense_type),
    subtitle: `当前费用类型下存在 ${formatMaterialType(item.required_material_type)} 等缺失项`,
  };
}

function buildMissingMaterialGroups(items: MissingMaterialItem[], groupMode: GroupMode) {
  const groups = new Map<string, MissingMaterialGroup>();
  const sortedItems = [...items].sort((left, right) =>
    right.detected_at.localeCompare(left.detected_at)
    || left.invoice_number.localeCompare(right.invoice_number)
    || (left.member_id ?? "").localeCompare(right.member_id ?? ""),
  );

  for (const item of sortedItems) {
    const descriptor = buildGroupDescriptor(item, groupMode);
    const existing = groups.get(descriptor.key);
    if (existing) {
      existing.items.push(item);
      continue;
    }
    groups.set(descriptor.key, {
      key: descriptor.key,
      title: descriptor.title,
      subtitle: descriptor.subtitle,
      items: [item],
    });
  }

  return [...groups.values()].sort((left, right) => left.title.localeCompare(right.title));
}

function buildMissingMaterialSummary(items: MissingMaterialItem[]) {
  return {
    totalItems: items.length,
    memberCount: new Set(items.map((item) => item.member_id ?? "__unresolved__")).size,
    invoiceCount: new Set(items.map((item) => item.invoice_id)).size,
    expenseTypeCount: new Set(items.map((item) => item.expense_type)).size,
  };
}

function MissingMaterialGroupList({
  groups,
}: {
  groups: MissingMaterialGroup[];
}) {
  return (
    <section className="admin-review-record-list" aria-label="缺失材料分组列表">
      {groups.map((group) => (
        <article key={group.key} className="admin-review-record-card">
          <div className="task-card-header">
            <div>
              <p className="task-card-id">{group.subtitle}</p>
              <h3>{group.title}</h3>
            </div>
            <span className="status-chip member-status-chip-pending">
              {group.items.length} 条缺失项
            </span>
          </div>

          <ul className="admin-review-list" aria-label={`${group.title} 缺失材料列表`}>
            {group.items.map((item) => (
              <li key={`${group.key}:${item.invoice_id}:${item.source_rule_code}:${item.required_material_type}`}>
                <strong>
                  {item.invoice_number} / {formatMaterialType(item.required_material_type)}
                </strong>
                <span>提交成员：{item.member_id ?? "未解析提交人"}</span>
                <span>费用类型：{formatExpenseType(item.expense_type)}</span>
                <span>规则编码：{item.source_rule_code}</span>
                <span>{item.message}</span>
                <span>发现时间：{formatDateTime(item.detected_at)}</span>
              </li>
            ))}
          </ul>
        </article>
      ))}
    </section>
  );
}

export function AdminMissingMaterialsPage() {
  const session = useAuthSession();
  const { taskId } = useParams<{ taskId: string }>();
  const [groupMode, setGroupMode] = useState<GroupMode>("member");
  const [state, setState] = useState<AdminMissingMaterialState>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;

    async function loadPage() {
      if (!session || session.role !== "admin" || !taskId) {
        return;
      }

      setState({ status: "loading" });

      try {
        const [task, list] = await Promise.all([
          trmsApi.getTask(taskId),
          trmsApi.getTaskMissingMaterials(taskId, session.actorId),
        ]);

        if (cancelled) {
          return;
        }

        setState({ status: "ready", task, list });
      } catch (error) {
        if (cancelled) {
          return;
        }
        setState({ status: "error", error });
      }
    }

    void loadPage();

    return () => {
      cancelled = true;
    };
  }, [session, taskId]);

  const readyGroups = useMemo(
    () => (state.status === "ready" ? buildMissingMaterialGroups(state.list.items, groupMode) : []),
    [groupMode, state],
  );

  if (!session || session.role !== "admin") {
    return null;
  }

  if (!taskId) {
    return (
      <div className="page-stack">
        <section className="status-card">
          <p className="eyebrow">Task Missing</p>
          <h2>任务标识缺失</h2>
          <p>当前路由未提供任务编号，无法查看缺失材料清单。</p>
        </section>
      </div>
    );
  }

  const task = state.status === "ready" ? state.task : null;
  const isForeignTask = task ? task.administrator_id !== session.actorId : false;
  const visibleTask = state.status === "ready" && !isForeignTask ? state.task : null;
  const visibleList = state.status === "ready" && !isForeignTask ? state.list : null;
  const summary = visibleList ? buildMissingMaterialSummary(visibleList.items) : null;

  return (
    <div className="page-stack">
      <section className="status-card admin-review-hero">
        <p className="eyebrow">Missing Materials</p>
        <h2>缺失材料清单</h2>
        <p>
          本页直接读取任务级缺失材料聚合结果，支持按成员、发票或费用类型切换查看，不把导出接口硬套成页面数据源。
        </p>
        <p className="status-note">
          当前仍使用 mock 管理员身份 {session.displayName}（{session.actorId}）。如果后端拒绝访问，本页会直接显示真实错误。
        </p>
        <div className="inline-actions">
          <Link className="route-link route-link-secondary" to="/admin">
            返回任务列表
          </Link>
          <Link className="route-link route-link-secondary" to={`/admin/tasks/${taskId}`}>
            返回任务详情
          </Link>
        </div>
      </section>

      {state.status === "loading" ? (
        <section className="status-card admin-review-panel">
          <p className="eyebrow">Loading</p>
          <h2>正在加载缺失材料清单</h2>
          <p>正在读取任务详情和缺失材料聚合结果，请稍候。</p>
        </section>
      ) : null}

      {state.status === "error" ? <ApiErrorNotice error={state.error} /> : null}

      {state.status === "ready" && isForeignTask ? (
        <section className="status-card admin-review-panel">
          <p className="eyebrow">Access Scope</p>
          <h2>当前任务不属于此管理员</h2>
          <p>
            当前任务的 `administrator_id` 为 {task?.administrator_id}，与当前 mock 管理员
            {session.actorId} 不一致。为避免在真实鉴权接入前误操作，本页不展示缺失材料详情。
          </p>
        </section>
      ) : null}

      {visibleTask && visibleList ? (
        <>
          <section className="status-card admin-review-panel">
            <div className="task-card-header">
              <div>
                <p className="task-card-id">任务编号 {visibleTask.id}</p>
                <h2>{visibleTask.competition_name}</h2>
              </div>
              <span className={`status-chip task-status-chip task-status-${visibleTask.status}`}>
                {formatTaskStatus(visibleTask.status)}
              </span>
            </div>
            <div className="admin-review-summary-grid">
              <div>
                <dt>比赛地点</dt>
                <dd>{visibleTask.competition_location}</dd>
              </div>
              <div>
                <dt>提交截止</dt>
                <dd>{formatDateTime(visibleTask.deadline)}</dd>
              </div>
              <div>
                <dt>缺失项总数</dt>
                <dd>{summary?.totalItems ?? 0}</dd>
              </div>
              <div>
                <dt>涉及成员</dt>
                <dd>{summary?.memberCount ?? 0}</dd>
              </div>
              <div>
                <dt>涉及发票</dt>
                <dd>{summary?.invoiceCount ?? 0}</dd>
              </div>
              <div>
                <dt>涉及费用类型</dt>
                <dd>{summary?.expenseTypeCount ?? 0}</dd>
              </div>
            </div>
          </section>

          <section className="status-card admin-review-panel">
            <div className="admin-form-header">
              <div>
                <p className="eyebrow">View Mode</p>
                <h2>切换查看维度</h2>
              </div>
              <span className="status-chip">{GROUP_MODE_LABELS[groupMode]}</span>
            </div>
            <div className="admin-form-grid">
              <label className="field-stack">
                <span>查看维度</span>
                <select
                  aria-label="查看维度"
                  value={groupMode}
                  onChange={(event) => {
                    setGroupMode(event.target.value as GroupMode);
                  }}
                >
                  <option value="member">按成员查看</option>
                  <option value="invoice">按发票查看</option>
                  <option value="expense_type">按费用类型查看</option>
                </select>
                <span className="field-hint">当前缺失项只读展示，不在本页直接代替管理员完成补材料提醒或人工更正。</span>
              </label>
            </div>
          </section>

          {visibleList.items.length === 0 ? (
            <section className="status-card admin-review-panel">
              <p className="eyebrow">Empty</p>
              <h2>当前任务没有缺失材料</h2>
              <p>现有缺失材料聚合结果为空，说明当前任务下没有命中“需补充材料”的失败校验。</p>
            </section>
          ) : (
            <MissingMaterialGroupList groups={readyGroups} />
          )}
        </>
      ) : null}
    </div>
  );
}

export function MemberMissingMaterialsPage() {
  const session = useAuthSession();
  const [searchParams] = useSearchParams();
  const preferredTaskId = searchParams.get("taskId");
  const [groupMode, setGroupMode] = useState<GroupMode>("invoice");
  const [selectedTaskId, setSelectedTaskId] = useState("");
  const [taskState, setTaskState] = useState<MemberVisibleTaskState>({ status: "loading" });
  const [listState, setListState] = useState<SelectedTaskMissingMaterialState>({ status: "idle" });

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
        setSelectedTaskId((currentTaskId) => (
          pickSelectedTaskId(visibleTasks, preferredTaskId, currentTaskId)
        ));
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

    async function loadSelectedTaskMissingMaterials(task: ReimbursementTask) {
      setListState({ status: "loading", task });

      try {
        const list = await trmsApi.getTaskMissingMaterials(task.id, session!.actorId);

        if (cancelled) {
          return;
        }

        setListState({ status: "ready", task, list });
      } catch (error) {
        if (cancelled) {
          return;
        }

        setListState({ status: "error", task, error });
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

    void loadSelectedTaskMissingMaterials(selectedTask);

    return () => {
      cancelled = true;
    };
  }, [selectedTaskId, session, taskState]);

  const readyGroups = useMemo(
    () => (listState.status === "ready" ? buildMissingMaterialGroups(listState.list.items, groupMode) : []),
    [groupMode, listState],
  );

  if (!session || session.role !== "member") {
    return null;
  }

  const visibleTasks = taskState.status === "ready" ? taskState.visibleTasks : [];
  const selectedTask = visibleTasks.find((task) => task.id === selectedTaskId) ?? null;
  const visibleList = listState.status === "ready" ? listState.list : null;
  const summary = visibleList ? buildMissingMaterialSummary(visibleList.items) : null;

  return (
    <div className="page-stack">
      <section className="status-card auth-panel">
        <p className="eyebrow">Member Missing Materials</p>
        <h2>我的缺失材料</h2>
        <p>
          当前页只展示当前成员本人需要补充的材料，不暴露同任务下其他成员的缺失项。
        </p>
        <p className="status-note">
          当前仍使用 mock 成员身份 {session.displayName}（{session.actorId}）。页面直接读取服务端按成员裁剪后的缺失材料列表，不在前端二次猜测权限。
        </p>
        <div className="inline-actions">
          <Link className="route-link route-link-secondary" to="/member">
            返回成员任务列表
          </Link>
          {selectedTask?.status === "open" ? (
            <Link
              className="route-link"
              to={`/member/materials/upload?taskId=${encodeURIComponent(selectedTask.id)}`}
            >
              去补充材料
            </Link>
          ) : null}
        </div>
      </section>

      {taskState.status === "loading" ? (
        <section className="status-card">
          <p className="eyebrow">Loading</p>
          <h2>正在加载可见任务</h2>
          <p>正在读取当前成员可访问的任务，以便定位你自己的缺失材料。</p>
        </section>
      ) : null}

      {taskState.status === "error" ? <ApiErrorNotice error={taskState.error} /> : null}

      {taskState.status === "ready" && visibleTasks.length === 0 ? (
        <section className="status-card">
          <p className="eyebrow">Empty</p>
          <h2>当前没有可查看的报销任务</h2>
          <p>当前 mock 成员尚未匹配到任何可见任务，因此也没有可读取的缺失材料清单。</p>
        </section>
      ) : null}

      {taskState.status === "ready" && visibleTasks.length > 0 ? (
        <section className="status-card auth-panel">
          <div className="admin-form-header">
            <div>
              <p className="eyebrow">Task Scope</p>
              <h2>选择要查看的任务</h2>
            </div>
            {selectedTask ? (
              <span className={`status-chip task-status-chip task-status-${selectedTask.status}`}>
                {formatTaskStatus(selectedTask.status)}
              </span>
            ) : null}
          </div>
          <div className="admin-form-grid">
            <label className="field-stack">
              <span>目标任务</span>
              <select
                aria-label="目标任务"
                value={selectedTaskId}
                onChange={(event) => {
                  setSelectedTaskId(event.target.value);
                }}
              >
                {visibleTasks.map((task) => (
                  <option key={task.id} value={task.id}>
                    {task.competition_name}（{task.id}）
                  </option>
                ))}
              </select>
              <span className="field-hint">这里只列出当前成员可见任务，且缺失材料清单继续只返回当前成员本人相关条目。</span>
            </label>
            <label className="field-stack">
              <span>查看维度</span>
              <select
                aria-label="查看维度"
                value={groupMode}
                onChange={(event) => {
                  setGroupMode(event.target.value as GroupMode);
                }}
              >
                <option value="invoice">按发票查看</option>
                <option value="expense_type">按费用类型查看</option>
              </select>
              <span className="field-hint">成员视角不提供“按成员查看”，因为当前列表不会包含其他成员数据。</span>
            </label>
          </div>
          {selectedTask && visibleList ? (
            <div className="token-list" aria-label="缺失材料摘要">
              <span className="token-chip">缺失项 {summary?.totalItems ?? 0} 条</span>
              <span className="token-chip">涉及发票 {summary?.invoiceCount ?? 0} 张</span>
              <span className="token-chip">涉及费用类型 {summary?.expenseTypeCount ?? 0} 类</span>
            </div>
          ) : null}
        </section>
      ) : null}

      {selectedTask && listState.status === "loading" ? (
        <section className="status-card">
          <p className="eyebrow">Loading</p>
          <h2>正在加载我的缺失材料</h2>
          <p>正在读取当前任务下与你本人相关的缺失材料项，请稍候。</p>
        </section>
      ) : null}

      {selectedTask && listState.status === "error" ? <ApiErrorNotice error={listState.error} /> : null}

      {selectedTask && listState.status === "ready" && listState.list.items.length === 0 ? (
        <section className="status-card">
          <p className="eyebrow">Empty</p>
          <h2>当前任务下你没有待补材料</h2>
          <p>
            任务 {listState.task.id} 当前对你可见，但现有缺失材料聚合结果里没有 `member_id`
            为 {session.actorId} 的条目。
          </p>
        </section>
      ) : null}

      {selectedTask && listState.status === "ready" && listState.list.items.length > 0 ? (
        <MissingMaterialGroupList groups={readyGroups} />
      ) : null}
    </div>
  );
}
