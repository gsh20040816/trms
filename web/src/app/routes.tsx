import type { RouteObject } from "react-router-dom";

import { AdminCorrectionsRemindersPage } from "./admin-corrections-reminders";
import { AdminExportTasksPage } from "./admin-export-tasks";
import { AdminTaskDetailPage } from "./admin-task-detail";
import { AdminTaskCreatePage } from "./admin-task-create";
import { AdminInvoiceEditorPage } from "./admin-invoice-editor";
import { AdminMissingMaterialsPage, MemberMissingMaterialsPage } from "./task-missing-materials";
import { AdminReviewOverviewPage } from "./admin-review-overview";
import { AdminSplitEditorPage } from "./admin-split-editor";
import { AdminTaskListPage } from "./admin-task-list";
import { MemberExpenseConfirmationPage } from "./member-expense-confirmation";
import { MemberMaterialStatusPage } from "./member-material-status";
import { MemberMaterialUploadPage } from "./member-material-upload";
import { MemberTaskListPage } from "./member-task-list";
import { MockLoginPage, ProtectedRoleRoute } from "./auth";
import { HomePage, NotFoundPage, RootLayout } from "./pages";
import { findRoleRouteByRole, roleRoutes, type UserRole } from "./role-routes";
import { SystemAdminDashboardPage } from "./system-admin-dashboard";

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
        path: memberRoleRoute.path.slice(1),
        element: <ProtectedRoleRoute roleRoute={memberRoleRoute} />,
        children: [
          {
            index: true,
            element: <MemberTaskListPage />,
          },
          {
            path: "materials/upload",
            element: <MemberMaterialUploadPage />,
          },
          {
            path: "materials/status",
            element: <MemberMaterialStatusPage />,
          },
          {
            path: "materials/missing",
            element: <MemberMissingMaterialsPage />,
          },
          {
            path: "expenses/confirm",
            element: <MemberExpenseConfirmationPage />,
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
          {
            path: "tasks/:taskId/missing-materials",
            element: <AdminMissingMaterialsPage />,
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
