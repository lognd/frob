// frob:tests web/tests/unit/Header.test.tsx kind="unit"
// frob:doc docs/index.md#routing-and-page-shell
/** Site footer with links to the cookie notice and data policy pages. */
export function Footer() {
  return (
    <footer className="flex items-center justify-center gap-space-16 bg-panel px-space-24 py-space-16 text-font-size-14 text-muted">
      {/* frob:todo T-0049 note="both links 404 until the data-policy route and page exist" */}
      <a href="/cookie-policy">Cookie policy</a>
      <a href="/data-policy">Data policy</a>
    </footer>
  );
}
