import { Route, Routes } from "react-router-dom";
import { USERS } from "./paths";
import { runtimePath } from "./dynamic";
import { About, Dyn, Home, Shell, User } from "./pages";

declare const flag: boolean;

export const App = () => (
  <Routes>
    <Route path="/" element={<Shell />}>
      <Route index element={<Home />} />
      <Route path="about" element={<About />} />
      <Route path={USERS + "/:id"} element={<User />} />
      {flag && <Route path="beta" element={<About />} />}
      <Route path={runtimePath} element={<Dyn />} />
    </Route>
  </Routes>
);
