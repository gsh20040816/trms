import { RoleShell } from "../components/RoleShell";

export type RoleRouteConfig = {
  path: string;
  title: string;
  summary: string;
  emphasis: string;
};

export const roleRoutes: RoleRouteConfig[] = [
  {
    path: "/member",
    title: "成员入口",
    summary: "后续承载可提交任务、材料上传与个人费用确认。",
    emphasis: "材料提交主链路",
  },
  {
    path: "/admin",
    title: "管理员后台",
    summary: "后续承载任务创建、复核、缺失材料与导出入口。",
    emphasis: "任务管理与复核",
  },
  {
    path: "/system",
    title: "系统管理",
    summary: "后续承载系统配置、渠道配置与全局治理能力。",
    emphasis: "全局配置边界",
  },
];

export function buildRoleShell(roleRoute: RoleRouteConfig) {
  return (
    <RoleShell
      title={roleRoute.title}
      summary={roleRoute.summary}
      emphasis={roleRoute.emphasis}
    />
  );
}
