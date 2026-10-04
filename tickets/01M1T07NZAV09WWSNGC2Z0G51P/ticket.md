+++
id = "01M1T07NZAV09WWSNGC2Z0G51P"
title = "H-2: unguarded default for required build-time env config"
type = "security"
category = "triage"
priority = "low"
parent = "01M1T07NZ7QPBX3WD3ZVWSJX8H"
reporter = "agent"
created = "2026-09-06T00:00:00Z"
updated = "2026-10-04T21:05:25Z"
aliases = ["T-4074"]
labels = ["v1-cluster:B4", "triage:accepted"]
scope = ["src/frob/gates/_secrets.py"]

[[acceptance]]
text = "given a design decision between a lint-only check on import.meta.env.VITE_* defaults and a strata attr flag= construct, when this ticket's design step completes, then the choice is recorded before implementation"
bound = false

[[acceptance]]
text = "given import.meta.env.VITE_* read with an unguarded ??/|| default, when the new rule runs, then it is flagged unless the default is guarded by import.meta.env.DEV"
bound = false
+++

H-2 (F-273). IMPORTANT FRAMING, per the coordinator's explicit instruction: SEC110 fired here and was CORRECTLY waived -- the Turnstile site key genuinely is public, so the waiver's reasoning is right. Do NOT read this as "a waiver hid a defect." The waiver is correct; the actual defect is adjacent and is something SEC110 (a secret-material rule) was never meant to catch.

VERIFIED: git grep for a rule checking `??`/`||` defaults on `import.meta.env.VITE_*` reads (or an equivalent required-build-time-config check) found nothing in src/frob.

FINDING THIS WOULD HAVE CAUGHT: an unguarded `??`/`||` fallback default for a REQUIRED build-time config value (e.g. `import.meta.env.VITE_TURNSTILE_KEY ?? "dummy-key"`) -- if the real env var is ever unset at build time, the app silently ships with the fallback instead of failing the build. This is a missing-required-config-at-build-time defect, distinct from and untouched by the secret-material check that correctly passed on this same line.

Proposed rule, per the consumer's own two options: (a) a check that every `import.meta.env.VITE_*` read either has no `??`/`||` default at all, or has one explicitly guarded by `import.meta.env.DEV` (so the fallback is legitimately dev-only); or (b) a strata `attr flag=`-style declaration for required frontend build config, checked at build time the same way the backend's LOGAND_KILL_SWITCH_EXEC attr already is (verify that attr= mechanism's existence and shape before designing (b), since it is proposed as symmetrical to something that already exists on the backend side). Decide between (a) lint-only and (b) a strata construct before implementing -- (a) is cheaper and frontend-specific; (b) generalizes but requires strata language work.
