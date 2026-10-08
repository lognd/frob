import { useEffect, useState } from "react";

/** localStorage key backing the signed-in session (see docs/design/sprint-1.md sec.6). */
const STORAGE_KEY = "hullbreach.session";

// frob:doc docs/index.md#session-persistence
/** The signed-in user's session as persisted client-side; shape T-0021 populates via login. */
export type StoredSession = {
  token: string;
  userId: string;
  username: string;
  role: string;
};

/** Type-guards an unknown parsed value as a well-formed StoredSession. */
function isStoredSession(value: unknown): value is StoredSession {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const candidate = value as Record<string, unknown>;
  return (
    typeof candidate.token === "string" &&
    typeof candidate.userId === "string" &&
    typeof candidate.username === "string" &&
    typeof candidate.role === "string"
  );
}

// frob:tests web/tests/unit/Header.test.tsx kind="unit"
// frob:tests web/tests/unit/Login.test.tsx kind="unit"
// frob:doc docs/index.md#session-persistence
/** Persists the given session to localStorage so it survives a reload. */
export function saveSession(session: StoredSession): void {
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
}

// frob:tests web/tests/unit/Login.test.tsx kind="unit"
// frob:doc docs/index.md#session-persistence
/** Reads the persisted session back, or null if absent or corrupt. */
export function loadSession(): StoredSession | null {
  const raw = window.localStorage.getItem(STORAGE_KEY);
  if (raw === null) {
    return null;
  }
  try {
    const parsed: unknown = JSON.parse(raw);
    return isStoredSession(parsed) ? parsed : null;
  } catch {
    return null;
  }
}

// frob:tests web/tests/unit/Login.test.tsx kind="unit"
// frob:tests web/tests/unit/Header.test.tsx kind="unit"
// frob:doc docs/index.md#session-persistence
/** Removes the persisted session, e.g. on logout. */
export function clearSession(): void {
  window.localStorage.removeItem(STORAGE_KEY);
}

// frob:tests web/tests/unit/Header.test.tsx kind="unit"
// frob:tests web/tests/unit/Login.test.tsx kind="unit"
// frob:doc docs/index.md#session-persistence
/** React hook exposing the current session, live-updated across tabs via the storage event. */
export function useSession(): StoredSession | null {
  const [session, setSession] = useState<StoredSession | null>(() => loadSession());

  useEffect(() => {
    function handleStorage(event: StorageEvent): void {
      if (event.key === STORAGE_KEY || event.key === null) {
        setSession(loadSession());
      }
    }
    window.addEventListener("storage", handleStorage);
    return () => window.removeEventListener("storage", handleStorage);
  }, []);

  return session;
}
