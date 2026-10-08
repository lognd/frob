import { useState, type FormEvent } from "react";
import { ApiError, login } from "@/api/auth";
import { saveSession } from "@/auth/session";

// frob:tests web/tests/unit/Login.test.tsx kind="unit"
// frob:doc docs/index.md#auth-api-client-and-the-register-page
// frob:waive REF002 reason="single-anchor by design: wired only from \
// web/src/router.tsx's /login route plus this one doc anchor -- a second consumer \
// would be an unused, invented import"
/** Login form: submits to POST /api/v1/auth/login, persists the session on success, and navigates home; shows a form-level banner on 401/429. */
export function Login() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [formError, setFormError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setFormError(null);
    try {
      const response = await login({ username, password });
      saveSession({
        token: response.token,
        userId: response.user.id,
        username: response.user.username,
        role: response.user.role,
      });
      window.location.assign("/");
    } catch (error) {
      if (error instanceof ApiError) {
        setFormError(error.detail);
      } else {
        setFormError("Something went wrong. Please try again.");
      }
    }
  }

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-space-16 bg-paper text-ink">
      <h1 className="text-font-size-32 font-semibold">Log in</h1>
      {formError !== null ? (
        <p role="alert" className="text-font-size-14 text-stress-fail">
          {formError}
        </p>
      ) : null}
      <form
        onSubmit={(event) => {
          void handleSubmit(event);
        }}
        className="flex w-full max-w-[24rem] flex-col gap-space-12"
      >
        <div className="flex flex-col gap-space-4">
          <label htmlFor="login-username" className="text-font-size-14">
            Username
          </label>
          <input
            id="login-username"
            name="username"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
          />
        </div>

        <div className="flex flex-col gap-space-4">
          <label htmlFor="login-password" className="text-font-size-14">
            Password
          </label>
          <input
            id="login-password"
            name="password"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
        </div>

        <button type="submit" className="text-font-size-16">
          Log in
        </button>
      </form>
    </main>
  );
}
