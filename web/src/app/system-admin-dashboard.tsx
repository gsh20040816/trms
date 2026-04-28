import { Link } from "react-router-dom";

import { PageHeader, RoleWorkspace, SectionCard, StatCard, StatusBadge } from "../components/dashboard";

const SYSTEM_CARDS = [
  {
    title: "用户与角色管理",
    description: "维护成员、管理员和系统管理员账号，处理权限开通与停用。",
    action: "进入账号管理",
  },
  {
    title: "全局抬头与税号",
    description: "统一维护默认发票抬头、税号和全局报销基础信息。",
    action: "检查全局配置",
  },
  {
    title: "费用类别配置",
    description: "管理可选费用类别和相关校验规则的配置边界。",
    action: "查看费用配置",
  },
  {
    title: "系统运行状态",
    description: "查看系统状态、审计记录和诊断入口，不在普通工作台暴露技术细节。",
    action: "查看运行状态",
  },
];

export function SystemAdminDashboardPage() {
  return (
    <RoleWorkspace
      header={(
        <PageHeader
          eyebrow="系统管理"
          title="系统管理员工作台"
          description="这里集中处理账号、角色、全局配置和运行状态。普通报销任务入口不会显示技术诊断信息。"
          actions={(
            <div className="page-actions">
              <Link className="button button-primary" to="/login">
                切换账号
              </Link>
              <StatusBadge tone="info">诊断信息仅在系统管理页查看</StatusBadge>
            </div>
          )}
        />
      )}
      summary={(
        <section className="stat-grid" aria-label="系统管理概览">
          <StatCard label="账号管理" value="3" description="用户、角色、权限三类管理入口已集中。 " />
          <StatCard label="全局配置" value="2" description="统一维护抬头税号与费用类别配置。" />
          <StatCard label="运行巡检" value="2" description="系统状态与审计记录入口集中在这里。" />
        </section>
      )}
    >
      <section className="feature-grid" aria-label="系统管理员入口">
        {SYSTEM_CARDS.map((card) => (
          <SectionCard key={card.title} title={card.title} description={card.description} action={<StatusBadge tone="neutral">{card.action}</StatusBadge>} />
        ))}
      </section>
    </RoleWorkspace>
  );
}

