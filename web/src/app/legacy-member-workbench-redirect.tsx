import { Navigate, useSearchParams } from "react-router-dom";

export function LegacyMemberWorkbenchRedirect({ hash }: { hash: string }) {
  const [searchParams] = useSearchParams();
  const taskId = searchParams.get("taskId");
  const target = `/member/invoices/workbench${taskId ? `?taskId=${encodeURIComponent(taskId)}` : ""}${hash}`;
  return <Navigate to={target} replace />;
}
