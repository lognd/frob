import { type RouteConfig, route, index } from "@react-router/dev/routes";

export default [
  index("./routes/good.tsx"),
  route("silent", "./routes/silent.tsx"),
  route("untitled", "./routes/untitled.tsx"),
] satisfies RouteConfig;
