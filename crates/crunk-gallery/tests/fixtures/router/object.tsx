import { createBrowserRouter } from "react-router-dom";

// path: "/commented-out" must not count
interface Meta { path: string }

export const router = createBrowserRouter([
  {
    path: "/",
    element: <Layout />,
    children: [
      { index: true, element: <Home /> },
      { path: "about", element: <About /> },
      { path: "users/:id", element: <User />, children: [{ path: "edit", element: <Edit /> }] },
      { path: "/settings/", element: <Settings /> },
    ],
  },
  { path: "*", element: <NotFound /> },
]);
