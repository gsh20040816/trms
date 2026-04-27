import { Link } from "react-router-dom";

type RoleShellProps = {
  title: string;
  summary: string;
  emphasis: string;
};

export function RoleShell({ title, summary, emphasis }: RoleShellProps) {
  return (
    <section className="status-card">
      <p className="eyebrow">{emphasis}</p>
      <h2>{title}</h2>
      <p>{summary}</p>
      <p className="status-note">
        当前页面只用于固化路由边界。真实认证与角色入口占位将在下一任务实现。
      </p>
      <Link className="route-link" to="/">
        返回首页
      </Link>
    </section>
  );
}
