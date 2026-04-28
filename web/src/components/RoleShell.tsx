import type { ReactNode } from "react";

import { SectionCard, StatusBadge } from "./dashboard";

type RoleShellProps = {
  title: string;
  summary: string;
  emphasis: string;
  children?: ReactNode;
};

export function RoleShell({ title, summary, emphasis, children }: RoleShellProps) {
  return (
    <SectionCard
      title={title}
      description={summary}
      action={<StatusBadge tone="warning">{emphasis}</StatusBadge>}
    >
      {children}
    </SectionCard>
  );
}
