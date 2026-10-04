// frob:waive REF002 reason="single-purpose T-0257 acceptance fixture -- only \
// tests/unit/test_adapters_react_router.py's GALLERY005 end-to-end test ever \
// needs this router, by design (a second citing test would just be \
// duplicating that test)"
import { Routes, Route } from "react-router-dom";

// T-0257 acceptance fixture: every path here matches a declared
// [[screen]].entry EXCEPT "/settings", which is the one route this
// fixture's GALLERY005 test expects to fire on. "*" is a catch-all that
// must never require its own [[screen]] declaration.
export default function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/portal" element={<PortalLayout />}>
        <Route path="invoices" element={<PortalInvoices />} />
      </Route>
      <Route path="/login" element={<Login />} />
      <Route path="/settings" element={<Settings />} />
      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}
