import type { RouteObject } from "react-router-dom";

import { AdminTaskDetailPage } from "./admin-task-detail";
import { AdminTaskCreatePage } from "./admin-task-create";
import { AdminInvoiceEditorPage } from "./admin-invoice-editor";
import { AdminSplitEditorPage } from "./admin-split-editor";
import { AdminTaskListPage } from "./admin-task-list";
import { MemberMaterialStatusPage } from "./member-material-status";
import { MemberMaterialUploadPage } from "./member-material-upload";
import { MemberTaskListPage } from "./member-task-list";
import { MockLoginPage, ProtectedRoleRoute } from "./auth";
import { HomePage, NotFoundPage, RootLayout } from "./pages";
import { findRoleRouteByRole, roleRoutes, type UserRole } from "./role-routes";

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
        ],
      },
      ...roleRoutes
        .filter((roleRoute) => roleRoute.role !== "admin" && roleRoute.role !== "member")
        .map((roleRoute) => ({
          path: roleRoute.path.slice(1),
          element: <ProtectedRoleRoute roleRoute={roleRoute} />,
        })),
      {
        path: "*",
        element: <NotFoundPage />,
      },
    ],
  },
];
