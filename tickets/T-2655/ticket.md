---
id: T-2655
title: T-2651 landed new fleet_status symbols without test/doc edges (COV001+DOC002),
  raising quarantine
state: done
kind: bug
origin: human
created: '2026-08-19'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- scripts/fleet_status.py
evidence_scope:
- tests/unit/test_coordinator_scripts.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'record honest BUG002 waiver: fix is a missing frob:tests edge + missing
    frob:doc anchor sections, no runtime behavior change, so evidence is confirmatory-only
    by construction

    '
  actor: logan
  at: '2026-08-19'
  old_length: 2298
  new_length: 2621
evidence:
- tests/unit/test_coordinator_scripts.py::TestInProgressTicketScopeLeases::test_no_worktree_flagged_as_leak
- tests/unit/test_coordinator_scripts.py::TestInProgressTicketScopeLeases::test_live_worktree_named_not_leaked
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 5231b7830a1f693360843cb84f23719cfced0a69
---
## Measured

The post-land sweep for T-2651 (`3481c2a1`, the fleet_status lease-reporting
fix) raised quarantine with two findings, both on the file it changed:

    COV001: scripts/fleet_status.py   (commit=3481c2a1, ticket=T-2651)
    DOC002: scripts/fleet_status.py   (commit=3481c2a1, ticket=T-2651)

Attribution is CORRECT here -- both the commit and the owning ticket are
named, unlike the several misattributed findings seen earlier tonight. The
sweep did its job: T-2651 added new symbols (`_leaked_lease_rows` and
siblings, per its own report) without the required test and doc edges.

Quarantine raising is also correct: T-2651 is `done`, and T-2604's rules
state that a finding attributed to a CLOSED ticket must still raise -- that
is a regression against work believed finished, which is exactly what
quarantine exists for. I disposed it to this ticket so the fleet is not
stuck on fully-synchronous lands, but the findings are real and this ticket
owns them.

## Fix

- COV001: bind test coverage for the new symbols. `tests/unit/
  test_coordinator_scripts.py` already covers this module and T-2651 added
  tests there; the gap is the `frob:tests` edge on the specific new
  symbol(s), not necessarily missing tests. Check which before writing new
  ones -- an unnecessary duplicate test is its own debt.
- DOC002: `docs/guides/coordinator-scripts.md` is this module's documented
  home and T-2651 touched it. Determine what the gate actually wants
  (`uv run frob check --only gates --ticket T-2652` will name the symbol
  and the expected anchor) rather than guessing at prose.

Do NOT waive either finding. Both are the ordinary, satisfiable kind -- a
missing edge on a symbol the author just wrote -- and a waiver here would be
precisely the cop-out class T-1614's audit exists to catch.

## Positive controls, both directions

- `frob check --only gates` reports zero COV001/DOC002 for
  `scripts/fleet_status.py` afterward
- the lease-leak reporting T-2651 landed still behaves identically:
  `fleet_status` still prints the `(N live, M leaked)` counts, and an
  in-progress ticket with no worktree is still flagged as a probable leak.
  Without this control the fix could satisfy the gate while breaking the
  feature it documents
- `frob verify status` shows quarantine clear

frob:waive BUG002 reason="docs/edge-only fix (missing frob:tests edge + missing frob:doc anchor sections) -- no behavior changed, so the bound evidence tests already PASS at the parent commit (--check-repro confirmed PASSED_AT_PARENT); no repro is possible for a defect with no runtime symptom, per the T-2613 precedent"