export type UserRole = "member" | "admin" | "system_admin";

export type RoleRouteConfig = {
  role: UserRole;
  path: string;
  title: string;
  summary: string;
  emphasis: string;
  loginLabel: string;
  mockActorId: string;
  mockDisplayName: string;
  mockMemberCode: string | null;
};

export const roleRoutes: RoleRouteConfig[] = [
  {
    role: "member",
    path: "/member",
    title: "成员工作台",
    summary: "查看我参与的任务、补充材料并确认个人费用。",
    emphasis: "我的报销任务",
    loginLabel: "成员",
    mockActorId: "2250001",
    mockDisplayName: "王队员",
    mockMemberCode: "MEM-001",
  },
  {
    role: "admin",
    path: "/admin",
    title: "管理员工作台",
    summary: "查看我负责的任务，处理缺失材料、复核和导出。",
    emphasis: "待处理任务",
    loginLabel: "管理员",
    mockActorId: "admin-1",
    mockDisplayName: "张管理员",
    mockMemberCode: null,
  },
  {
    role: "system_admin",
    path: "/system",
    title: "系统管理",
    summary: "管理用户角色、全局配置、系统状态和审计记录。",
    emphasis: "系统配置与巡检",
    loginLabel: "系统管理员",
    mockActorId: "sysadmin-1",
    mockDisplayName: "赵系统管理员",
    mockMemberCode: null,
  },
];

export function findRoleRouteByRole(role: UserRole) {
  return roleRoutes.find((roleRoute) => roleRoute.role === role);
}
