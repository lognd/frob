import { createBrowserRouter } from "react-router-dom";
import { ADMIN, USERS } from "./paths";
import { dynamicRoutes, runtimePath } from "./dynamic";
import { Hidden, Home, Settings, Shell, userAction, userLoader, Users } from "./pages";

const prefix = ADMIN;
declare const beta: boolean;

export const router = createBrowserRouter(
  [
    {
      path: "/",
      element: <Shell />,
      children: [
        { index: true, element: <Home /> },
        { path: USERS, Component: Users, loader: userLoader, action: userAction },
        { path: `${prefix}/settings`, element: <Settings /> },
        { path: runtimePath, element: <Hidden /> },
        { path: beta ? "/beta" : "/gamma", element: <Settings /> },
        ...dynamicRoutes,
      ],
    },
  ],
  { basename: "/app" },
);
