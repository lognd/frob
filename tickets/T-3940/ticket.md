---
id: T-3940
title: RENDER001 land-time checker ignores the gate pathspec and blocks lands in every
  consumer repo
state: queued
kind: bug
origin: human
created: '2026-09-05'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_land_cmd.py
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
Consumer kicad-libsync, 2026-09-06, frob 0.530.0:

  "frob ticket land refused T-0007 with RENDER001 (bare print bypasses
   frob.render / INV-RENDER-SOLE-STDOUT). That invariant is about frob's OWN
   renderer; a consumer repo has no frob.render to route through. Worked
   around by logging instead of printing, but the rule should not apply
   outside the frob checkout."

They are right, and I verified the exact mechanism in our source rather than
taking the report on trust. It is NOT that RENDER001 is unscoped -- it is that
there are TWO code paths and only one of them carries the scope.

THE GATE IS CORRECTLY SCOPED. src/frob/gates/_render_lint.py:246 scans only:

    for pathspec in ("src/frob", *_EXTRA_SCAN_PATHSPECS):

i.e. src/frob, .claude/hooks, scripts/fleet_status.py -- all frob-repo paths.
The module even exports a public predicate for exactly this purpose,
render001_scans(root, rel_path) at :276, whose own docstring says it exists so
callers avoid "re-deriving or hardcoding RENDER001's pathspec a second time --
T-2719's own root cause". src/frob/app/ticket_runner/_waive_audit.py:1020 uses
it correctly.

THE LAND-TIME CHECKER DOES NOT. _render001_checker in
src/frob/app/ticket_runner/_land_cmd.py:4663 reuses the DETECTOR
(_scan_python_prints / _render001_violation) but never consults the PATHSPEC.
Its only filter is:

    if not rel_path.endswith(".py"):
        return ()

So every .py file in a landing ticket's touched set is scanned for bare prints,
in ANY repository. Its docstring argues its own correctness on the grounds that
it is "the SAME detector render_lint_gate dispatches repo-wide, not a
reimplementation" -- and that is precisely the trap: sharing the detector while
silently dropping the scope predicate produces a checker that agrees with the
gate on WHAT is a violation and disagrees on WHERE the rule applies.

THIS IS THE PORTABILITY-IS-A-GATE-PROPERTY CLASS, with a twist worth recording:
the usual instance is a rule hardcoding src/frob and therefore silently passing
off-repo. This one is the inverse -- a rule whose scoping was correctly
centralised, bypassed by a second consumer of the same detector, so it FALSELY
FIRES off-repo and blocks the land outright. Reusing a detector is not reusing a
rule; a rule is detector plus scope.

SEVERITY: this blocks landing in every consumer repo that prints to stdout,
which is every Python CLI. Their workaround (log instead of print) is a real
behaviour change forced on them by a rule that does not apply to them.

CHECK THE WHOLE FAMILY, DO NOT FIX ONLY RENDER001. _FILE_LOCAL_ERROR_CHECKERS
holds sibling adapters built the same way -- _doc005_checker at least, and
whatever else the tuple carries. For EACH, determine whether the rule it
enforces is frob-repo-specific and whether the adapter honours that scope.
Report the audit even for the ones that turn out fine; "I fixed the reported one"
is not an answer to a class.

MUST-FIRE FIXTURE: a bare print inside src/frob/ still refuses the land.
MUST-STAY-QUIET: a bare print in a consumer-shaped repo (no src/frob, no
frob.render importable) does NOT refuse the land. This is the fixture that
proves the bug fixed, and it must be built from a real off-repo tree shape, not
by monkeypatching the predicate.
THIRD FIXTURE: the land-time checker and render_lint_gate agree on scope for a
path inside AND outside the pathspec -- the desync itself, made checkable.

ACCEPTANCE
- The land-time checker derives its scope from render001_scans, not from a
  second hardcoded condition.
- Every other _FILE_LOCAL_ERROR_CHECKERS adapter audited for the same split,
  with the result stated per adapter.
- All three fixtures committed.