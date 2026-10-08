import { createBrowserRouter } from "react-router-dom";
import { App } from "@/App";
import { Register } from "@/pages/Register";
import { Login } from "@/pages/Login";

/** Landing route content; a fuller version lands with T-0045/T-0046 in a later milestone. */
function Landing() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-space-8 bg-paper font-base text-ink">
      <h1 className="text-font-size-48 font-semibold tracking-tight">
        Project Hullbreach
      </h1>
      <p className="text-font-size-20 text-muted">Build a ship. Breach a hull.</p>
    </main>
  );
}

/** Fallback route for an unmatched path. */
function NotFound() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-space-8 bg-paper text-ink">
      <p>Page not found.</p>
    </main>
  );
}

// frob:tests web/tests/unit/Header.test.tsx kind="unit"
// frob:doc docs/index.md#routing-and-page-shell
// frob:waive REF002 reason="single-anchor by design: wired only from web/src/main.tsx \
// (the app's one entry point) plus this one doc anchor -- a second consumer would be \
// an unused, invented import"
/** The app's data router: App is the page shell, its children are routed under the Outlet. */
export const router = createBrowserRouter([
  {
    path: "/",
    element: <App />,
    children: [
      { index: true, element: <Landing /> },
      { path: "register", element: <Register /> },
      { path: "login", element: <Login /> },
      // Each queued page is one more route here plus a pages/<Name>.tsx and
      // a tests/unit/<Name>.test.tsx; copy pages/Login.tsx. Add this file to
      // the ticket's scope first (`frob ticket scope T-#### --add`).
      // frob:todo T-0046 note="index route -> pages/Landing.tsx replaces the stub above"
      // frob:todo T-0032 note="path me -> pages/Profile.tsx (needs T-0031's GET /me)"
      // frob:todo T-0035 note="path settings -> pages/Settings.tsx"
      // frob:todo T-0049 note="path data-policy -> pages/DataPolicy.tsx (Footer already links it)"
      // frob:todo T-0060 note="path me/matches -> pages/MatchHistory.tsx"
      // frob:todo T-0063 note="path leaderboard -> pages/Leaderboard.tsx"
      // frob:todo T-0068 note="path store -> pages/Store.tsx"
      // frob:todo T-0078 note="path admin/* -> pages/admin/, gated on role is admin"
      { path: "*", element: <NotFound /> },
    ],
  },
]);
