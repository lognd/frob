import { useState, type FormEvent } from "react";
import { ApiError, register } from "@/api/auth";

/** Field-keyed validation errors, e.g. `{ username: "username already taken" }`. */
type FieldErrors = Record<string, string>;

// frob:tests web/tests/unit/Register.test.tsx kind="unit"
// frob:doc docs/index.md#auth-api-client-and-the-register-page
// frob:waive REF002 reason="single-anchor by design: wired only from web/src/router.tsx's /register route plus this one doc anchor -- a second consumer would be an unused, invented import"
/** Registration form: submits to POST /api/v1/auth/register and shows errors inline next to the offending field, or a form-level banner for a non-field error. */
export function Register() {
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [submitted, setSubmitted] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setFieldErrors({});
    setFormError(null);
    try {
      await register({ username, email, password });
      setSubmitted(true);
    } catch (error) {
      if (error instanceof ApiError && error.field !== undefined) {
        setFieldErrors({ [error.field]: error.detail });
      } else if (error instanceof ApiError) {
        setFormError(error.detail);
      } else {
        setFormError("Something went wrong. Please try again.");
      }
    }
  }

  if (submitted) {
    return (
      <main className="flex min-h-screen flex-col items-center justify-center gap-space-8 bg-paper text-ink">
        <h1 className="text-font-size-32 font-semibold">Registration complete</h1>
        <p className="text-font-size-16 text-muted">You can now log in.</p>
      </main>
    );
  }

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-space-16 bg-paper text-ink">
      <h1 className="text-font-size-32 font-semibold">Register</h1>
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
          <label htmlFor="register-username" className="text-font-size-14">
            Username
          </label>
          <input
            id="register-username"
            name="username"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            aria-describedby={fieldErrors.username ? "username-error" : undefined}
          />
          {fieldErrors.username ? (
            <p id="username-error" className="text-font-size-14 text-stress-fail">
              {fieldErrors.username}
            </p>
          ) : null}
        </div>

        <div className="flex flex-col gap-space-4">
          <label htmlFor="register-email" className="text-font-size-14">
            Email
          </label>
          <input
            id="register-email"
            name="email"
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            aria-describedby={fieldErrors.email ? "email-error" : undefined}
          />
          {fieldErrors.email ? (
            <p id="email-error" className="text-font-size-14 text-stress-fail">
              {fieldErrors.email}
            </p>
          ) : null}
        </div>

        <div className="flex flex-col gap-space-4">
          <label htmlFor="register-password" className="text-font-size-14">
            Password
          </label>
          <input
            id="register-password"
            name="password"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            aria-describedby={fieldErrors.password ? "password-error" : undefined}
          />
          {fieldErrors.password ? (
            <p id="password-error" className="text-font-size-14 text-stress-fail">
              {fieldErrors.password}
            </p>
          ) : null}
        </div>

        <button type="submit" className="text-font-size-16">
          Register
        </button>
      </form>
    </main>
  );
}
