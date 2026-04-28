import type { TaskStatus } from "../lib/api/types";

export type AdminTaskStageDescriptor = {
  label: string;
  summary: string;
};

const TASK_STAGE_DESCRIPTORS: Record<TaskStatus, AdminTaskStageDescriptor> = {
  draft: {
    label: "创建任务",
    summary: "补齐成员、费用类别和报销信息后再发布。",
  },
  open: {
    label: "材料收集",
    summary: "成员正在上传发票和附件，优先盯缺失项。",
  },
  closed: {
    label: "收集收口",
    summary: "普通成员已停止提交，准备进入集中复核。",
  },
  reviewing: {
    label: "审核异常",
    summary: "集中处理识别异常、分摊争议和待确认事项。",
  },
  ready_to_export: {
    label: "导出提交",
    summary: "当前任务已满足导出前置条件，可整理最终材料包。",
  },
  completed: {
    label: "完成归档",
    summary: "本系统内流程已完成，保留导出与追溯入口。",
  },
};

export function describeAdminTaskStage(status: TaskStatus) {
  return TASK_STAGE_DESCRIPTORS[status];
}
