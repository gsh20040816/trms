import type { ReactNode } from "react";

type RoleShellProps = {
  title: string;
  summary: string;
  emphasis: string;
  children?: ReactNode;
};

export function RoleShell({ title, summary, emphasis, children }: RoleShellProps) {
  return (
    <section className="status-card">
      <p className="eyebrow">{emphasis}</p>
      <h2>{title}</h2>
      <p>{summary}</p>
      {children}
    </section>
  );
}
