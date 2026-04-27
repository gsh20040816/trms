import type { RouteObject } from "react-router-dom";

import { MockLoginPage, ProtectedRoleRoute } from "./auth";
import { HomePage, NotFoundPage, RootLayout } from "./pages";
import { roleRoutes } from "./role-routes";

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
      ...roleRoutes.map((roleRoute) => ({
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
