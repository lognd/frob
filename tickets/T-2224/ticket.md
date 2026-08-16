---
id: T-2224
title: Via-less grants on fail-closed capability kinds (exec/eval/install-hook/ffi)
  are WARN-only, never enforced
state: queued
kind: security
origin: human
created: '2026-08-16'
priority: critical
parent: T-1623
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/strata/_selfconform.py
- design/frob.strata
- docs/strata/selfconform.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
Measured: SYS107 (T-1451, _selfconform.py) is the only check covering a via-less (whole-file/whole-node) grant, and its own docstring states it is 'Deliberately WARN, not ERROR' for every kind, including exec/eval/install-hook/ffi -- the kinds that let a node run attacker-influenced code or persist beyond itself. Today a node can carry an unbounded, ever-growing via-less exec/eval/install-hook/ffi grant indefinitely: nothing in frob check --only sys fails closed on it, so it never blocks a land. (SYS101 stale-design already prunes grants for capabilities that stop being observed, which is a genuinely separate and already-closed problem -- this ticket is only about via-less breadth on the fail-closed kinds, not staleness.) Acceptance: a positive-control test-only strata fixture (do not edit design/frob.strata's real declarations for this) with a node declaring a via-less may "exec" grant MUST be reported at ERROR severity by the selfconform check, not WARN; this test must FAIL against current main (SYS107 currently returns WARN for exactly this case) and pass after the fix. Scope the upgrade explicitly to exec/eval/install-hook/ffi -- do not touch net/fs.read/fs.write severity, which stay WARN-appropriate at this breadth per SYS107's existing rationale, to avoid mass unrelated churn across design/frob.strata's existing declarations. If any of design/frob.strata's REAL existing nodes already carries a via-less grant on one of these four kinds, narrowing it to via globs (or filing a follow-up per node if narrowing needs deeper investigation) is in scope as a consequence of turning the check to ERROR, and must not be silently waived to make the gate pass.