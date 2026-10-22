import { type RouteConfig, route, index, layout, prefix } from "@react-router/dev/routes";
import { adminRoutes } from "./admin-routes";
import { flatRoutes } from "@react-router/fs-routes";

const shop = [
  route("cart", "./routes/cart.tsx"),
  route("checkout", "./routes/checkout.tsx"),
];

const runtime = process.env.PATH_X;

export default [
  index("./routes/home.tsx"),
  route("about", "./routes/about.tsx"),
  layout("./routes/shell.tsx", [
    route("dash", "./routes/dash.tsx"),
  ]),
  ...prefix("shop", shop),
  ...prefix("admin", adminRoutes),
  route(runtime, "./routes/dyn.tsx"),
  ...(await flatRoutes()),
] satisfies RouteConfig;
