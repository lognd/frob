import { Outlet } from "react-router-dom";
import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";

// frob:tests web/tests/unit/Header.test.tsx kind="unit"
// frob:tests web/tests/unit/App.test.tsx kind="unit"
// frob:doc docs/index.md#routing-and-page-shell
/** Page shell: header and footer wrap whichever route matched (or nothing, outside a router). */
export function App() {
  return (
    <>
      <Header />
      {/* frob:todo T-0048 note="render <CookieNotice /> here, above the Outlet, until dismissed" */}
      <Outlet />
      <Footer />
    </>
  );
}
