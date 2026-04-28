import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { ApiErrorNotice } from "../components/ApiErrorNotice";
import { trmsApi } from "../lib/api/trms";
import type {
  InvoiceRecord,
  MaterialRecord,
  MaterialType,
  RecognitionTaskList,
  RecognitionTaskRecord,
  ReimbursementTask,
  TaskStatus,
  ValidationResult,
} from "../lib/api/types";
import { useAuthSession } from "./auth-store";

type VisibleTaskState =
  | { status: "loading" }
  | { status: "error"; error: unknown }
  | { status: "ready"; visibleTasks: ReimbursementTask[] };

type SelectedTaskMaterialState =
  | { status: "idle" }
  | { status: "loading"; task: ReimbursementTask }
  | { status: "error"; task: ReimbursementTask; error: unknown }
  | { status: "ready"; task: ReimbursementTask; items: MemberMaterialStatusItem[] };

type ValidationSummaryStatus = "passed" | "failed" | "pending" | "not_ready";

type MissingMaterialTip = {
  requiredMaterialType: MaterialType;
  message: string;
  ruleCode: string;
};

type MemberMaterialStatusItem = {
  material: MaterialRecord;
  recognition: RecognitionTaskRecord | null;
  invoice: InvoiceRecord | null;
  validations: ValidationResult[];
  missingMaterialTips: MissingMaterialTip[];
};

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

const RECOGNITION_STATUS_LABELS: Record<string, string> = {
  pending: "识别排队中",
  succeeded: "识别完成",
  failed: "识别失败",
  needs_confirmation: "识别待确认",
};

const RECOGNITION_FIELD_LABELS: Record<string, string> = {
  invoice_number: "发票号码",
  buyer_name: "购买方名称",
  tax_number: "税号",
  amount_cents: "金额",
  transaction_time: "交易时间",
  expense_type: "费用类型",
  departure_location: "出发地",
  arrival_location: "到达地",
  cabin_class: "舱位",
  seat_class: "座位等级",
};

const MISSING_MATERIAL_RULE_TO_TYPE: Partial<Record<string, MaterialType>> = {
  invoice_payment_record_required: "payment_record",
  invoice_competition_notice_required: "competition_notice",
  invoice_airfare_itinerary_required: "itinerary",
  invoice_local_transport_rideshare_trip_required: "itinerary",
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

function formatTaskStatus(status: TaskStatus) {
  return TASK_STATUS_LABELS[status];
}

function formatMaterialType(materialType: MaterialType) {
  return MATERIAL_TYPE_LABELS[materialType] ?? materialType;
}

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function formatRecognitionFieldName(fieldName: string) {
  return RECOGNITION_FIELD_LABELS[fieldName] ?? fieldName;
}

function getCurrentRecognitionTask(recognitionList: RecognitionTaskList): RecognitionTaskRecord | null {
  const latestEffective = recognitionList.latest_effective;
  if (latestEffective) {
    return latestEffective;
  }
  return recognitionList.items[recognitionList.items.length - 1] ?? null;
}

function deriveMissingMaterialTips(validations: ValidationResult[]): MissingMaterialTip[] {
  return validations.flatMap((validation) => {
    if (validation.status !== "failed") {
      return [];
    }
    const requiredMaterialType = MISSING_MATERIAL_RULE_TO_TYPE[validation.rule_code];
    if (!requiredMaterialType) {
      return [];
    }
    return [
      {
        requiredMaterialType,
        message: validation.message,
        ruleCode: validation.rule_code,
      },
    ];
  });
}

function summarizeRecognition(recognition: RecognitionTaskRecord | null) {
  if (!recognition) {
    return {
      tone: "pending" as const,
      title: "识别任务尚未创建",
      details: ["当前材料还没有可展示的识别任务记录。"],
    };
  }

  if (recognition.status === "failed") {
    return {
      tone: "failed" as const,
      title: RECOGNITION_STATUS_LABELS[recognition.status],
      details: recognition.failure
        ? [`失败阶段：${recognition.failure.stage}`, `失败原因：${recognition.failure.reason}`]
        : ["识别失败，但服务端未返回失败明细。"],
    };
  }

  if (recognition.status === "needs_confirmation") {
    const pendingFieldNames = Object.entries(recognition.recognized_fields)
      .filter(([, field]) => field.status === "needs_confirmation")
      .map(([fieldName]) => formatRecognitionFieldName(fieldName));

    return {
      tone: "needs_confirmation" as const,
      title: RECOGNITION_STATUS_LABELS[recognition.status],
      details: pendingFieldNames.length > 0
        ? [`待确认字段：${pendingFieldNames.join("、")}`]
        : ["识别结果包含待确认项，请管理员或成员人工复核。"],
    };
  }

  if (recognition.status === "succeeded") {
    const recognizedFieldCount = Object.keys(recognition.recognized_fields).length;
    return {
      tone: "succeeded" as const,
      title: RECOGNITION_STATUS_LABELS[recognition.status],
      details: [`已输出 ${recognizedFieldCount} 个识别字段。`],
    };
  }

  return {
    tone: "pending" as const,
    title: RECOGNITION_STATUS_LABELS[recognition.status],
    details: ["材料已进入统一识别流程，当前仍在排队或处理中。"],
  };
}

function summarizeValidations(
  materialType: MaterialType,
  invoice: InvoiceRecord | null,
  validations: ValidationResult[],
) {
  if (!invoice) {
    return {
      tone: "not_ready" as const,
      title: materialType === "invoice" ? "待录入发票字段" : "当前材料暂无独立发票校验",
      details: [
        materialType === "invoice"
          ? "该发票材料还没有对应的发票结构化记录，因此暂时没有可展示的校验结果。"
          : "当前校验结果只挂在发票记录上；辅助材料的影响会体现在关联发票的校验中。",
      ],
      abnormalValidations: [] as ValidationResult[],
    };
  }

  if (validations.length === 0) {
    return {
      tone: "not_ready" as const,
      title: "暂无校验结果",
      details: ["发票记录已存在，但当前还没有可展示的校验结果。"],
      abnormalValidations: [] as ValidationResult[],
    };
  }

  const failedValidations = validations.filter((validation) => validation.status === "failed");
  const pendingValidations = validations.filter((validation) => validation.status === "pending");
  const abnormalValidations = validations.filter(
    (validation) => validation.status === "failed" || validation.status === "pending",
  );

  let tone: ValidationSummaryStatus = "passed";
  let title = "全部校验通过";
  if (failedValidations.length > 0) {
    tone = "failed";
    title = `存在 ${failedValidations.length} 条失败校验`;
  } else if (pendingValidations.length > 0) {
    tone = "pending";
    title = `存在 ${pendingValidations.length} 条待确认校验`;
  }

  const details = [
    `总计 ${validations.length} 条校验结果`,
    `失败 ${failedValidations.length} 条，待确认 ${pendingValidations.length} 条`,
  ];

  return {
    tone,
    title,
    details,
    abnormalValidations,
  };
}

export function MemberMaterialStatusPage() {
  const session = useAuthSession();
  const [searchParams] = useSearchParams();
  const preferredTaskId = searchParams.get("taskId");
  const [taskState, setTaskState] = useState<VisibleTaskState>({ status: "loading" });
  const [selectedTaskId, setSelectedTaskId] = useState("");
  const [materialState, setMaterialState] = useState<SelectedTaskMaterialState>({ status: "idle" });

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

    async function loadSelectedTaskStatus(task: ReimbursementTask) {
      setMaterialState({ status: "loading", task });

      try {
        const [materialsResponse, invoicesResponse] = await Promise.all([
          trmsApi.listTaskMaterials(task.id),
          trmsApi.listTaskInvoices(task.id),
        ]);

        const ownMaterials = materialsResponse.items
          .filter((material) => material.submitter_id === session?.actorId)
          .sort((left, right) => right.created_at.localeCompare(left.created_at));
        const ownMaterialIds = new Set(ownMaterials.map((material) => material.id));
        const invoicesByMaterialId = new Map(
          invoicesResponse.items
            .filter((invoice) => ownMaterialIds.has(invoice.material_id))
            .map((invoice) => [invoice.material_id, invoice] as const),
        );

        const recognitionEntries = await Promise.all(
          ownMaterials.map(async (material) => [
            material.id,
            await trmsApi.listMaterialRecognitionTasks(material.id),
          ] as const),
        );
        const recognitionsByMaterialId = new Map(
          recognitionEntries.map(([materialId, recognitionList]) => [
            materialId,
            getCurrentRecognitionTask(recognitionList),
          ] as const),
        );

        const ownInvoices = Array.from(invoicesByMaterialId.values());
        const validationEntries = await Promise.all(
          ownInvoices.map(async (invoice) => [
            invoice.id,
            (await trmsApi.listInvoiceValidations(invoice.id)).items,
          ] as const),
        );
        const validationsByInvoiceId = new Map(validationEntries);

        if (cancelled) {
          return;
        }

        const items = ownMaterials.map((material) => {
          const invoice = invoicesByMaterialId.get(material.id) ?? null;
          const validations = invoice ? (validationsByInvoiceId.get(invoice.id) ?? []) : [];
          return {
            material,
            recognition: recognitionsByMaterialId.get(material.id) ?? null,
            invoice,
            validations,
            missingMaterialTips: deriveMissingMaterialTips(validations),
          };
        });

        setMaterialState({ status: "ready", task, items });
      } catch (error) {
        if (cancelled) {
          return;
        }

        setMaterialState({ status: "error", task, error });
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

    void loadSelectedTaskStatus(selectedTask);

    return () => {
      cancelled = true;
    };
  }, [selectedTaskId, session, taskState]);

  if (!session || session.role !== "member") {
    return null;
  }

  const visibleTasks = taskState.status === "ready" ? taskState.visibleTasks : [];
  const selectedTask = visibleTasks.find((task) => task.id === selectedTaskId) ?? null;
  const readyItems = materialState.status === "ready" ? materialState.items : [];
  const totalMissingTips = readyItems.reduce(
    (count, item) => count + item.missingMaterialTips.length,
    0,
  );
  const needsConfirmationRecognitions = readyItems.filter(
    (item) => item.recognition?.status === "needs_confirmation",
  ).length;
  const failedValidations = readyItems.reduce(
    (count, item) => count + item.validations.filter((validation) => validation.status === "failed").length,
    0,
  );

  return (
    <div className="page-stack">
      <section className="status-card auth-panel">
        <p className="eyebrow">Member Status</p>
        <h2>成员材料状态</h2>
        <p>
          当前页聚合当前成员自己提交的材料状态，只展示本人材料的识别进度、发票校验异常和缺失材料提示，不暴露同任务下其他成员的材料详情。
        </p>
        <p className="status-note">
          当前使用 mock 成员身份 {session.displayName}（{session.actorId}）。页面基于现有材料列表、识别任务和发票校验接口做只读聚合，不额外引入新的成员专用后端路由。
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
              去上传更多材料
            </Link>
          ) : null}
          <span className="status-chip">当前可见任务 {visibleTasks.length} 个</span>
        </div>
      </section>

      {taskState.status === "loading" ? (
        <section className="status-card">
          <p className="eyebrow">Loading</p>
          <h2>正在加载可见任务</h2>
          <p>正在读取当前成员可访问的报销任务，以便定位你自己的材料状态。</p>
        </section>
      ) : null}

      {taskState.status === "error" ? <ApiErrorNotice error={taskState.error} /> : null}

      {taskState.status === "ready" && visibleTasks.length === 0 ? (
        <section className="status-card">
          <p className="eyebrow">Empty</p>
          <h2>当前没有可查看状态的报销任务</h2>
          <p>当前 mock 成员尚未匹配到任何可见任务，因此也没有可聚合的材料状态。</p>
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
              <span className="field-hint">只列出当前成员可见任务；状态页继续只聚合你本人提交的材料。</span>
            </label>
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
              </dl>
            ) : null}
          </div>
          {materialState.status === "ready" ? (
            <div className="token-list" aria-label="材料状态摘要">
              <span className="token-chip">本人材料 {materialState.items.length} 份</span>
              <span className="token-chip">识别待确认 {needsConfirmationRecognitions} 份</span>
              <span className="token-chip">失败校验 {failedValidations} 条</span>
              <span className="token-chip">缺失提示 {totalMissingTips} 条</span>
            </div>
          ) : null}
        </section>
      ) : null}

      {selectedTask && materialState.status === "loading" ? (
        <section className="status-card">
          <p className="eyebrow">Loading</p>
          <h2>正在汇总成员材料状态</h2>
          <p>正在读取该任务下你本人提交的材料、识别任务和发票校验结果。</p>
        </section>
      ) : null}

      {selectedTask && materialState.status === "error" ? <ApiErrorNotice error={materialState.error} /> : null}

      {selectedTask && materialState.status === "ready" && materialState.items.length === 0 ? (
        <section className="status-card">
          <p className="eyebrow">Empty</p>
          <h2>当前任务下还没有你提交的材料</h2>
          <p>
            任务 {materialState.task.id} 当前对你可见，但在现有材料列表里还没有 `submitter_id`
            为 {session.actorId} 的记录，因此状态页不会显示同任务其他成员的材料。
          </p>
        </section>
      ) : null}

      {selectedTask && materialState.status === "ready" && materialState.items.length > 0 ? (
        <section className="member-status-list" aria-label="成员材料状态列表">
          {materialState.items.map((item) => {
            const recognitionSummary = summarizeRecognition(item.recognition);
            const validationSummary = summarizeValidations(
              item.material.material_type,
              item.invoice,
              item.validations,
            );

            return (
              <article key={item.material.id} className="task-card member-status-card">
                <div className="task-card-header">
                  <div>
                    <p className="task-card-id">材料编号 {item.material.id}</p>
                    <h3>{item.material.original_filename}</h3>
                  </div>
                  <span className="status-chip">{formatMaterialType(item.material.material_type)}</span>
                </div>

                <dl className="task-meta-grid member-status-meta-grid">
                  <div>
                    <dt>提交时间</dt>
                    <dd>{formatDateTime(item.material.created_at)}</dd>
                  </div>
                  <div>
                    <dt>提交渠道</dt>
                    <dd>{item.material.channel}</dd>
                  </div>
                  <div>
                    <dt>重复文件</dt>
                    <dd>{item.material.duplicate_of ? `与 ${item.material.duplicate_of} 重复` : "未标记重复"}</dd>
                  </div>
                  <div>
                    <dt>关联发票</dt>
                    <dd>{item.invoice ? item.invoice.invoice_number : "暂无发票记录"}</dd>
                  </div>
                </dl>

                <section className="member-status-section">
                  <div className="member-status-section-header">
                    <h4>识别状态</h4>
                    <span className={`status-chip member-status-chip member-status-chip-${recognitionSummary.tone}`}>
                      {recognitionSummary.title}
                    </span>
                  </div>
                  <ul className="member-status-detail-list">
                    {recognitionSummary.details.map((detail) => (
                      <li key={detail}>{detail}</li>
                    ))}
                  </ul>
                </section>

                <section className="member-status-section">
                  <div className="member-status-section-header">
                    <h4>校验状态</h4>
                    <span className={`status-chip member-status-chip member-status-chip-${validationSummary.tone}`}>
                      {validationSummary.title}
                    </span>
                  </div>
                  <ul className="member-status-detail-list">
                    {validationSummary.details.map((detail) => (
                      <li key={detail}>{detail}</li>
                    ))}
                  </ul>
                  {validationSummary.abnormalValidations.length > 0 ? (
                    <ul className="member-status-message-list" aria-label={`${item.material.id} 校验异常列表`}>
                      {validationSummary.abnormalValidations.map((validation) => (
                        <li key={validation.id}>
                          <strong>{validation.rule_code}</strong>
                          <span>{validation.message}</span>
                        </li>
                      ))}
                    </ul>
                  ) : null}
                </section>

                <section className="member-status-section">
                  <div className="member-status-section-header">
                    <h4>缺失材料提示</h4>
                    <span className="status-chip">
                      {item.missingMaterialTips.length > 0
                        ? `${item.missingMaterialTips.length} 条缺失提示`
                        : "当前无缺失提示"}
                    </span>
                  </div>
                  {item.missingMaterialTips.length > 0 ? (
                    <ul className="member-status-message-list" aria-label={`${item.material.id} 缺失材料提示列表`}>
                      {item.missingMaterialTips.map((tip) => (
                        <li key={`${tip.ruleCode}:${tip.requiredMaterialType}`}>
                          <strong>{formatMaterialType(tip.requiredMaterialType)}</strong>
                          <span>{tip.message}</span>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="task-healthy-note">当前材料关联的发票没有命中可直接归类为“缺失材料”的失败规则。</p>
                  )}
                </section>
              </article>
            );
          })}
        </section>
      ) : null}
    </div>
  );
}
