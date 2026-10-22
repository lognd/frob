import { route, index } from "@react-router/dev/routes";

export const adminRoutes = [
  index("./routes/admin-home.tsx"),
  route("users/:id", "./routes/user.tsx"),
];
