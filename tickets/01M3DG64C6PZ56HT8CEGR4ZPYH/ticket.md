+++
id = "01M3DG64C6PZ56HT8CEGR4ZPYH"
title = "WEBSEC/A11Y precision pass: 12 false-positive shapes measured on a real app (about 5 percent true positives)"
type = "bug"
category = "todo"
priority = "low"
parent = "01M2Y1SS0MVHB8M891RN134SE7"
reporter = "agent"
created = "2026-09-26T00:00:00Z"
updated = "2026-10-09T20:42:32Z"
aliases = ["T-6534"]
labels = ["v1-cluster:B2", "area:grimble", "triage:accepted", "milestone:0.538.0"]
scope = ["src/frob/webapp/", "tests/fixtures/webapp/", "tests/unit/test_webapp_precision.py", "docs/modules/webapp.md", "docs/design/crunk.md"]
+++

Source: logand.app-v2 FROBLEMS.md (peer coordinator report, 2026-09-26, frob 0.531.1.dev332). Reproduction lives in that repo (read-only for frob agents); the frob-side positive control must be a fixture here.

F-396: taint_gate + a11y_gate on a demo worktree produced 168 findings, roughly 8 real. Shapes to fix, each with a negative-control fixture:
- WEBSEC416/419 (LLM excessive agency / retrieval scoping, 25 hits) fired on `sessions.delete`, `delete_by_user`, test queries in an app with no LLM: gate on an LLM SDK dependency.
- WEBSEC324 typosquat: 'test' vs 'next' (a `scripts` key read as a dependency), 'vite' vs 'vue': read dependency tables only; never flag a name that is itself on the top list.
- COMPLY101 'no /privacy page' while src/pages/public/Privacy.tsx is routed at /privacy in routes.tsx: resolve routes.
- WEBSEC101 x28: `write(...)` on `outRef.current` (canvas writer) is not document.write: require the receiver to be `document`.
- WEBSEC102: dangerouslySetInnerHTML inside `<script type="application/ld+json">` fed by an escaping serialiser of a module constant: recognise JSON-LD + escaping serialiser.
- WEBSEC208 logout: handler calls `revoke_sessions_for_user(...)`; rule only knows flush()/destroy(): accept configurable/heuristic revoke names.
- WEBSEC230 login rate limit flagged the frontend client and a test file; the backend Redis limiter (`record_failure`/`retry_after_seconds`) was not seen: scope to server routes, recognise limiter calls.
- WEBSEC123 on pydantic-settings config fields (env config, not request input).
- WEBSEC125/227 inside tests/ (recursion guards, http://localhost mocks): exclude test trees by default.
- WEBSEC301-306 headers present in ops/caddy/snippets/10_security_headers.caddy: message must name the searched roots; support Caddy snippets outside the web subtree.
- WEBSEC322 lockfile: frontend/ is a workspace member; package-lock.json lives at the root (ties to F-394).
- A11Y111/112: `<input>` nested inside `<label htmlFor>` and camelCase `autoComplete` missed; A11Y104 'second h1' where the two h1s are in mutually exclusive early-return branches.
Deliver each as a negative-control fixture that must NOT fire plus the matching positive control that still fires; report precision before/after on the fixture set.
