import type { RouteObject } from "react-router-dom";

import { AdminCorrectionsRemindersPage } from "./admin-corrections-reminders";
import { AdminExportTasksPage } from "./admin-export-tasks";
import { AdminTaskDetailPage } from "./admin-task-detail";
import { AdminTaskCreatePage } from "./admin-task-create";
import { AdminInvoiceEditorPage } from "./admin-invoice-editor";
import { AdminReviewOverviewPage } from "./admin-review-overview";
import { AdminSplitEditorPage } from "./admin-split-editor";
import { AccountProfilePage } from "./account-profile";
import { MemberMaterialDetailPage } from "./member-material-detail";
import { MemberMaterialStatusPage } from "./member-material-status";
import { AdminTaskListPage } from "./admin-task-list";
import { MemberInvoiceWorkbenchPage } from "./member-invoice-workbench";
import { MemberInvoiceDetailPage } from "./member-invoice-detail";
import { MemberTaskListPage } from "./member-task-list";
import { MockLoginPage, ProtectedRoleRoute } from "./auth";
import { LegacyMemberWorkbenchRedirect } from "./legacy-member-workbench-redirect";
import { HomePage, NotFoundPage, RootLayout } from "./pages";
import { findRoleRouteByRole, roleRoutes, type UserRole } from "./role-routes";
import { SystemAdminDashboardPage } from "./system-admin-dashboard";
import { TelegramBindingPage } from "./telegram-binding";

function getRoleRouteOrThrow(role: UserRole) {
  const roleRoute = findRoleRouteByRole(role);
  if (!roleRoute) {
    throw new Error(`Unknown role route: ${role}`);
  }
  return roleRoute;
}

const memberRoleRoute = getRoleRouteOrThrow("member");
const adminRoleRoute = getRoleRouteOrThrow("admin");

export const routes: RouteObject[] = [
  {
    path: "/",
    element: <RootLayout />,
    children: [
      {
        index: true,
        element: <HomePage />,
      },
      {
        path: "login",
        element: <MockLoginPage />,
      },
      {
        path: "telegram/bind",
        element: <TelegramBindingPage />,
      },
      {
        path: "profile",
        element: <AccountProfilePage />,
      },
      {
        path: memberRoleRoute.path.slice(1),
        element: <ProtectedRoleRoute roleRoute={memberRoleRoute} />,
        children: [
          {
            index: true,
            element: <MemberTaskListPage />,
          },
          {
            path: "materials/upload",
            element: <LegacyMemberWorkbenchRedirect hash="#member-workbench-upload" />,
          },
          {
            path: "materials/status",
            element: <MemberMaterialStatusPage />,
          },
          {
            path: "invoices/workbench",
            element: <MemberInvoiceWorkbenchPage />,
          },
          {
            path: "invoices/:invoiceId",
            element: <MemberInvoiceDetailPage />,
          },
          {
            path: "materials/:materialId",
            element: <MemberMaterialDetailPage />,
          },
          {
            path: "materials/:materialId/invoice",
            element: <MemberInvoiceDetailPage />,
          },
          {
            path: "materials/missing",
            element: <LegacyMemberWorkbenchRedirect hash="#member-workbench-status" />,
          },
          {
            path: "expenses/confirm",
            element: <LegacyMemberWorkbenchRedirect hash="#member-workbench-invoices" />,
          },
        ],
      },
      {
        path: adminRoleRoute.path.slice(1),
        element: <ProtectedRoleRoute roleRoute={adminRoleRoute} />,
        children: [
          {
            index: true,
            element: <AdminTaskListPage />,
          },
          {
            path: "tasks/new",
            element: <AdminTaskCreatePage />,
          },
          {
            path: "tasks/:taskId",
            element: <AdminTaskDetailPage />,
          },
          {
            path: "tasks/:taskId/invoices",
            element: <AdminInvoiceEditorPage />,
          },
          {
            path: "tasks/:taskId/splits",
            element: <AdminSplitEditorPage />,
          },
          {
            path: "tasks/:taskId/review",
            element: <AdminReviewOverviewPage />,
          },
          {
            path: "tasks/:taskId/corrections",
            element: <AdminCorrectionsRemindersPage />,
          },
          {
            path: "tasks/:taskId/exports",
            element: <AdminExportTasksPage />,
          },
        ],
      },
      ...roleRoutes
        .filter((roleRoute) => roleRoute.role !== "admin" && roleRoute.role !== "member")
        .map((roleRoute) => ({
          path: roleRoute.path.slice(1),
          element: <ProtectedRoleRoute roleRoute={roleRoute} />,
          children: [
            {
              index: true,
              element: <SystemAdminDashboardPage />,
            },
          ],
        })),
      {
        path: "*",
        element: <NotFoundPage />,
      },
    ],
  },
];
