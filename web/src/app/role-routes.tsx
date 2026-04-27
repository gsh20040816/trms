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
    title: "成员入口",
    summary: "后续承载可提交任务、材料上传与个人费用确认。",
    emphasis: "材料提交主链路",
    loginLabel: "成员身份",
    mockActorId: "2250001",
    mockDisplayName: "王队员",
    mockMemberCode: "MEM-001",
  },
  {
    role: "admin",
    path: "/admin",
    title: "管理员后台",
    summary: "后续承载任务创建、复核、缺失材料与导出入口。",
    emphasis: "任务管理与复核",
    loginLabel: "管理员身份",
    mockActorId: "admin-1",
    mockDisplayName: "张管理员",
    mockMemberCode: null,
  },
  {
    role: "system_admin",
    path: "/system",
    title: "系统管理",
    summary: "后续承载系统配置、渠道配置与全局治理能力。",
    emphasis: "全局配置边界",
    loginLabel: "系统管理员身份",
    mockActorId: "sysadmin-1",
    mockDisplayName: "赵系统管理员",
    mockMemberCode: null,
  },
];

export function findRoleRouteByRole(role: UserRole) {
  return roleRoutes.find((roleRoute) => roleRoute.role === role);
}
