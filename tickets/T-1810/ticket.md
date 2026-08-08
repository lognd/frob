---
id: T-1810
title: T-1508's land dropped pyproject.toml's own edit while keeping uv.lock's derived
  fix -- main is now source/lock inconsistent
state: done
kind: bug
origin: human
created: '2026-08-08'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- pyproject.toml
- uv.lock
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: uv.lock
  reason: uv.lock already carries the fixed specifier text from T-1508's own land
    (a derived artifact that landed correctly); this ticket's own scope needs it declared
    so a no-op re-lock during land is not flagged out-of-scope
  actor: logan
  at: '2026-08-08'
evidence:
- tests/unit/test_dup_smt.py::test_proves_equivalent_bounded_functions
- tests/unit/test_dup_smt.py::test_finds_counterexample_for_non_equivalent_functions
- tests/unit/test_dup_smt.py::test_degrades_to_smt_unavailable_without_z3
designated_repro_test: null
threat: null
component: null
---
T-1508's own land (`frob ticket land T-1508`, commit
`48e7a23ed44c3a3d09f6612fb1b9da5ed2c1ec8f`, `LAND-PROOF verified=True
state_on_main=done`) did NOT actually bring `pyproject.toml`'s edit to
main, despite the land reporting success. Confirmed three separate times
against a freshly fetched `main` ref (not a stale local cache): the
landed commit's own diff (`git show 48e7a23ed --stat`) touches only
`tickets/T-1508/done-report.md`, `tickets/T-1508/ticket.md`, and
`uv.lock` -- `pyproject.toml` is absent from the changed-files list
entirely, and `main`'s current `pyproject.toml` still reads
`smt = ["z3-solver>=4.13"]` (the unbounded, broken pin), not
`z3-solver>=4.13,<4.15.5` (the fix).

The stranger half: `uv.lock` WAS updated in that same commit, and its
own `requires-dist` entry for the `smt` extra correctly shows the
BOUNDED specifier (`>=4.13,<4.15.5`) -- a derived artifact landed
correctly while its own source of truth did not. `main` is now in a
genuinely inconsistent state: `uv.lock`'s locked resolution (z3-solver
4.15.4.0) matches the fix, but `pyproject.toml` itself has no record of
why, and a future `uv lock --upgrade` (or anyone editing the `smt` extra
again without noticing the mismatch) would silently re-introduce
T-1508's original failure, because the SOURCE constraint never
tightened.

This is a land-correctness defect, not a re-derivable "maybe I imagined
it" -- reproduced identically across three independent `git fetch . main`
+ `git show`/`git diff` checks in the same session, immediately after
the land itself reported success. Filed rather than silently re-fixed
under a closed ticket's own state, per this repo's evidence-integrity
discipline; the fix itself is trivial (one line), but the ROOT CAUSE
(why did `frob ticket land`'s squash/merge step drop a real, committed
source-file change while keeping its own derived artifact) needs
someone who owns the land pipeline to investigate -- I could not
determine from the CLI's own output which step ate it (no error, no
warning named `pyproject.toml` anywhere in the land transcript).

Immediate fix (this ticket's own scope): re-apply the SAME one-line
`pyproject.toml` change T-1508 already carried, verified correct via
`uv sync --extra smt` end to end in that same session, so `pyproject.toml`
and `uv.lock` agree on main again.