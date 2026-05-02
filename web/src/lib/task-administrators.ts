import type { ReimbursementTask, UserSearchSummary } from "./api/types";

function normalizeAdministratorIds(administratorId: string, administratorIds?: string[] | null) {
  const rawIds = administratorIds && administratorIds.length > 0
    ? administratorIds
    : [administratorId];
  const uniqueIds: string[] = [];
  for (const rawId of rawIds) {
    const normalizedId = rawId.trim();
    if (normalizedId.length === 0 || uniqueIds.includes(normalizedId)) {
      continue;
    }
    uniqueIds.push(normalizedId);
  }
  return uniqueIds;
}

export function getTaskAdministratorIds(task: Pick<ReimbursementTask, "administrator_id" | "administrator_ids">) {
  return normalizeAdministratorIds(task.administrator_id, task.administrator_ids);
}

export function isTaskVisibleToAdministrator(
  task: Pick<ReimbursementTask, "administrator_id" | "administrator_ids">,
  actorId: string,
) {
  return getTaskAdministratorIds(task).includes(actorId.trim());
}

export function buildTaskAdministratorSearchOptions(
  administratorIds: string[],
  administratorOptions: UserSearchSummary[],
) {
  return administratorIds.map((administratorId) => (
    administratorOptions.find((option) => option.actor_id === administratorId) ?? {
      actor_id: administratorId,
      username: administratorId,
      display_name: administratorId,
      student_id: null,
    }
  ));
}

export function formatTaskAdministratorCountLabel(
  task: Pick<ReimbursementTask, "administrator_id" | "administrator_ids">,
) {
  const count = getTaskAdministratorIds(task).length;
  return count <= 1 ? "1 名管理员" : `${count} 名管理员`;
}
