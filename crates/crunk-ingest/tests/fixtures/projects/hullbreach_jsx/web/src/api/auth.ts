/** Base path for every auth endpoint (docs/design/sprint-1.md sec.5); vite proxies /api to the server in dev. */
const AUTH_BASE = "/api/v1/auth";

// frob:doc docs/index.md#auth-api-client-and-the-register-page
/** A user's role, as returned by every auth endpoint that exposes one. */
export type Role = "player" | "admin";

// frob:doc docs/index.md#auth-api-client-and-the-register-page
/** The profile shape every auth endpoint that returns a user echoes (docs/design/sprint-1.md sec.5). */
export type UserProfile = {
  id: string;
  username: string;
  email: string;
  role: Role;
  currency: number;
  rating: number;
  created_at: string;
};

// frob:doc docs/index.md#auth-api-client-and-the-register-page
/** POST /api/v1/auth/register's request body. */
export type RegisterRequest = {
  username: string;
  email: string;
  password: string;
};

// frob:doc docs/index.md#auth-api-client-and-the-register-page
/** POST /api/v1/auth/login's request body. */
export type LoginRequest = {
  username: string;
  password: string;
};

// frob:doc docs/index.md#auth-api-client-and-the-register-page
/** POST /api/v1/auth/login's 200 response body. */
export type LoginResponse = {
  token: string;
  user: UserProfile;
};

// frob:doc docs/index.md#auth-api-client-and-the-register-page
/** GET /api/v1/auth/session's 200 response body. */
export type SessionInfo = {
  user_id: string;
  role: Role;
};

// frob:doc docs/index.md#auth-api-client-and-the-register-page
/** A non-2xx auth response, normalized to a status/detail/optional field shape (docs/design/sprint-1.md sec.6). */
export class ApiError extends Error {
  status: number;
  detail: string;
  field?: string;

  // frob:tests web/tests/unit/Register.test.tsx kind="unit"
  // frob:doc docs/index.md#auth-api-client-and-the-register-page
  constructor(status: number, detail: string, field?: string) {
    super(detail);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
    this.field = field;
  }
}

/** Extracts a {detail, field?} pair from a non-ok Response body, tolerating FastAPI's array-shaped 422 detail. */
async function parseErrorBody(
  response: Response,
): Promise<{ detail: string; field?: string }> {
  let body: unknown = null;
  try {
    body = await response.json();
  } catch {
    body = null;
  }
  if (body !== null && typeof body === "object") {
    const record = body as Record<string, unknown>;
    if (typeof record.detail === "string") {
      const field = typeof record.field === "string" ? record.field : undefined;
      return { detail: record.detail, field };
    }
    if (Array.isArray(record.detail)) {
      return { detail: "validation failed" };
    }
  }
  return { detail: "request failed" };
}

/** Fetches `path`, parsing the JSON body or throwing an ApiError for a non-ok response. */
async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  // frob:todo T-0102 note="pass AbortSignal.timeout(...) in init so a hung server cannot hang the page"
  const response = await fetch(path, init);
  if (!response.ok) {
    const { detail, field } = await parseErrorBody(response);
    throw new ApiError(response.status, detail, field);
  }
  return (await response.json()) as T;
}

// frob:tests web/tests/unit/Register.test.tsx kind="unit"
// frob:doc docs/index.md#auth-api-client-and-the-register-page
/** POST /api/v1/auth/register; 201 UserProfile on success, 409/422 rejects with an ApiError. */
export async function register(payload: RegisterRequest): Promise<UserProfile> {
  return requestJson<UserProfile>(`${AUTH_BASE}/register`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(payload),
  });
}

// frob:tests web/tests/unit/Register.test.tsx kind="unit"
// frob:tests web/tests/unit/Login.test.tsx kind="unit"
// frob:doc docs/index.md#auth-api-client-and-the-register-page
/** POST /api/v1/auth/login; 200 LoginResponse on success, 401/429 rejects with an ApiError. */
export async function login(payload: LoginRequest): Promise<LoginResponse> {
  return requestJson<LoginResponse>(`${AUTH_BASE}/login`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(payload),
  });
}

// frob:tests web/tests/unit/Register.test.tsx kind="unit"
// frob:tests web/tests/unit/Header.test.tsx kind="unit"
// frob:doc docs/index.md#auth-api-client-and-the-register-page
/** POST /api/v1/auth/logout with the caller's bearer token; 204 on success, throws an ApiError otherwise. */
export async function logout(token: string): Promise<void> {
  const response = await fetch(`${AUTH_BASE}/logout`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) {
    const { detail, field } = await parseErrorBody(response);
    throw new ApiError(response.status, detail, field);
  }
}

// frob:tests web/tests/unit/Register.test.tsx kind="unit"
// frob:waive WIRE001 reason="no web production call site -- GET \
// /api/v1/auth/session (docs/design/sprint-1.md sec.5) is designed for the game \
// server to call directly, never this web client (T-0026); kept here for \
// API-surface completeness and T-0017's test suite" follow_up="T-0100"
// frob:doc docs/index.md#auth-api-client-and-the-register-page
/** GET /api/v1/auth/session with the caller's bearer token; 200 SessionInfo on success, throws an ApiError otherwise. */
export async function fetchSession(token: string): Promise<SessionInfo> {
  return requestJson<SessionInfo>(`${AUTH_BASE}/session`, {
    headers: { Authorization: `Bearer ${token}` },
  });
}
