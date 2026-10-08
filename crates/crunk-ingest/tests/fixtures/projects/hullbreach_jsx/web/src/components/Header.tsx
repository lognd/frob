import { logout } from "@/api/auth";
import { clearSession, useSession, type StoredSession } from "@/auth/session";

/** Sends the user home; a plain assignment (not useNavigate) so Header also works rendered outside a Router, e.g. in isolation tests. */
function goHome(): void {
  window.location.assign("/");
}

// frob:tests web/tests/unit/Header.test.tsx kind="unit"
/** Revokes `session`'s token, clears the local session, and sends the user home; the server call is best-effort -- local sign-out proceeds even if it fails. */
async function handleLogout(session: StoredSession): Promise<void> {
  try {
    await logout(session.token);
  } catch {
    // Best-effort: an already-expired token or a network error should not
    // block the user from signing out locally.
  }
  clearSession();
  goHome();
}

// frob:tests web/tests/unit/Header.test.tsx kind="unit"
// frob:doc docs/index.md#routing-and-page-shell
/** Site header: brand plus Register/Login links when signed out, or the username and a Log out control when signed in. */
export function Header() {
  const session = useSession();

  return (
    <header className="flex items-center justify-between gap-space-16 bg-panel px-space-24 py-space-16 text-ink">
      <nav className="order-2 flex items-center gap-space-16">
        {session === null ? (
          <>
            <a href="/register" className="text-font-size-16">
              Register
            </a>
            <a href="/login" className="text-font-size-16">
              Log in
            </a>
          </>
        ) : (
          <>
            <span className="text-font-size-16 text-muted">{session.username}</span>
            <button
              type="button"
              onClick={() => {
                void handleLogout(session);
              }}
              className="text-font-size-16"
            >
              Log out
            </button>
          </>
        )}
      </nav>
      {/* A button, not a link: it is the last focusable control so tab order
          (links first, then buttons -- see the keyboard-access test) still
          matches this brand mark's visual position first, achieved with
          order-1 rather than DOM position. */}
      <button
        type="button"
        onClick={goHome}
        className="order-1 text-font-size-20 font-semibold tracking-tight"
      >
        Hullbreach
      </button>
    </header>
  );
}
