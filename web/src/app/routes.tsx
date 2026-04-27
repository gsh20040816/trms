import type { RouteObject } from "react-router-dom";

import { HomePage, NotFoundPage, RootLayout } from "./pages";
import { buildRoleShell, roleRoutes } from "./role-routes";

export const routes: RouteObject[] = [
  {
    path: "/",
    element: <RootLayout />,
    children: [
      {
        index: true,
        element: <HomePage />,
      },
      ...roleRoutes.map((roleRoute) => ({
        path: roleRoute.path.slice(1),
        element: buildRoleShell(roleRoute),
      })),
      {
        path: "*",
        element: <NotFoundPage />,
      },
    ],
  },
];
