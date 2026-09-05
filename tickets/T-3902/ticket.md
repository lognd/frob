---
id: T-3902
title: SCOPE002=error makes docs/modules/gates.md unaddable to any ticket scope (3143-warning
  closure explosion)
state: queued
kind: bug
origin: human
created: '2026-09-05'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## Description
Found while working T-3315 (frob ticket sweep refuses on a done ticket).
frob.toml:690 sets `SCOPE002 = "error"` (promoted from the rule's own
documented WARN default, src/frob/gates/__init__.py::_scope002_violation's
docstring still says "WARN turn-on"). SCOPE002 (T-0998) fires per SYMBOL
declared in a ticket's scope whose own frob:doc/frob:tests/private-helper
edges point outside that scope -- so it fires for EVERY symbol in a
file, not just the ones a given diff actually touches.

`src/frob/app/ticket_runner/_lifecycle.py` (a large, multi-command
module: plan/start/requeue/sweep/reconcile/attach/block) has one function,
`_warn_scope_breadth_on_start`, whose `frob:doc` anchor points at
`docs/modules/gates.md` -- the repo's own giant shared gates design doc.
Adding `docs/modules/gates.md` to ANY ticket's scope (to close that one
edge) pulls in that doc's own closure requirements: MEASURED during
T-3315, `frob ticket scope T-3315 --add docs/modules/gates.md` alone
produced 3143 additional scope-closure warnings (`consider --add ...`)
naming dozens of unrelated gates/*.py source files, each themselves
pulling in more docs/tests transitively.

Net effect: SCOPE002=error + `_lifecycle.py` (or any other file whose
frob:doc anchor touches docs/modules/gates.md) makes that file
effectively unscopable without an unbounded scope-widening cascade -- a
ticket doing a genuinely small, single-function fix cannot reach a clean
`frob check --ticket` without either (a) widening scope to an
unreasonable fraction of the whole gates subsystem, or (b) leaving
SCOPE002 as an unresolved error and accepting a red ticket-scoped check.

T-3315 worked around this by reverting to a minimal, sane scope
(`_verify.py` + `_lifecycle.py` + its own test file) and leaving the
`_warn_scope_breadth_on_start` -> `docs/modules/gates.md` SCOPE002 finding
unresolved rather than chasing the cascade -- filed here instead of
silently widening or silently ignoring it.

## Plan
- Confirm whether SCOPE002's promotion to error (frob.toml:690) was
  measured clean against a representative sample of tickets BEFORE
  promotion, per the T-0756 promotion playbook
  (docs/modules/gates.md#new-gate-rule-acceptance-policy-t-0756) -- this
  finding suggests it was not measured against a large multi-purpose
  module referencing the shared gates design doc.
- Consider: (a) demoting SCOPE002 back to warn until closure-cascade
  cases like this one are addressed, (b) capping SCOPE002's own closure
  walk so a single doc target this large/shared is exempted (a doc this
  broadly cited is closer to "always in scope" than "needs an explicit
  add" -- similar to how the ledger/tickets/<id>/ shard are already
  always-in-scope exemptions elsewhere in this codebase), or (c) leaving
  error severity but adding a documented, first-class escape hatch (a
  `frob ticket scope --scope002-ack` parallel to `scope_breadth_ack`)
  for exactly this "the doc is too broadly shared to close" shape.
