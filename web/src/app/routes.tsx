import type { RouteObject } from "react-router-dom";

import { AdminTaskDetailPage } from "./admin-task-detail";
import { AdminTaskCreatePage } from "./admin-task-create";
import { AdminTaskListPage } from "./admin-task-list";
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
        ],
      },
      ...roleRoutes
        .filter((roleRoute) => roleRoute.role !== "admin")
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
