---
id: T-1643
title: Wire a real Tier-B --fix handler (T-1262 shipped only the synthetic TIERBDEMO001
  reference handler)
state: done
kind: feature
origin: agent
created: '2026-08-06'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/_fix_engine_tier_b.py
- src/frob/gates/_fix_engine.py
- tests/test_gates.py
- docs/design/check-fix-engine.md
- design/frob.strata
- tickets/T-1643/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/design/check-fix-engine.md
  reason: 'AFFECT001: doc anchor for TIER_B_HANDLERS/new handler; SELFAUDIT001: new
    public symbol needs interface sync via frob sys sync-interface'
  actor: logan
  at: '2026-08-08'
- op: add
  glob: design/frob.strata
  reason: 'AFFECT001: doc anchor for TIER_B_HANDLERS/new handler; SELFAUDIT001: new
    public symbol needs interface sync via frob sys sync-interface'
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tickets/T-1643/**
  reason: 'SCOPE001: ticket''s own per-ticket ledger file, per T-1742/T-1737/T-1483
    precedent'
  actor: logan
  at: '2026-08-08'
evidence:
- tests/test_gates.py::TestFixEngineTierB::test_dead001_removes_unreferenced_private_symbol
- tests/test_gates.py::TestFixEngineTierB::test_dead001_skips_a_waived_finding
- tests/test_gates.py::TestFixEngineTierB::test_dead001_at_most_one_deletion_per_file_per_pass
designated_repro_test: null
threat: null
component: null
---
T-1262's own Done report discloses this as a cut, out of its declared scope: fix_tierbdemo001_marker_rewrite is a deliberately synthetic handler (keyed to a placeholder TIERBDEMO001 id that is never a real frob check rule) proving the snapshot-apply-verify-commit-or-rollback transaction path end-to-end. No real, production Tier-B handler (a handler for an actual gate rule id) exists yet. Pick a real candidate rule currently fixed only at Tier A or not auto-fixed at all, and wire it through the Tier-B transaction machinery T-1262 built, following that ticket's own TIER_B_HANDLERS registration precedent.

## Done report

Wired the first real, production Tier-B `--fix` handler:
`fix_dead001_unreferenced_symbol_removal` in
`src/frob/gates/_fix_engine_tier_b.py`, registered as `"DEAD001":
fix_dead001_unreferenced_symbol_removal` in `TIER_B_HANDLERS`. T-1262
shipped only the synthetic `TIERBDEMO001` reference handler proving the
snapshot-apply-verify-commit-or-rollback transaction path end-to-end
with a placeholder marker-comment rewrite; T-1481 confirmed
`apply_tier_b_fixes` is now genuinely wired into `frob check --fix`
(`src/frob/app/check_runner.py`) but `TIERBDEMO001` stays a permanent
no-op on real source (its marker text never appears in this repo).

Chose DEAD001 (unreferenced private symbol) as the real candidate: the
remedy (delete the symbol's own source span) is mechanical --
`SymbolRecord.span` from the tree-sitter walker already delimits
exactly the lines to remove, decorators through closing line -- but
only SAFE conditionally on the rest of the tree, exactly Tier B's own
characterization: `dead_symbol_gate`'s own docstring discloses a
soundness gap (dynamic/reflective access the call graph cannot see),
so a deletion genuinely needs the re-verify-or-rollback machinery Tier
A cannot provide.

Safety measures, each disclosed in the handler's own docstring:
- Reuses `dead_symbol_gate` (the real gate) and `frob.gates.
  _apply_waivers` directly rather than reimplementing DEAD001's own
  private/uncalled/no-edge detection -- an explicit `frob:waive DEAD001
  reason="..."` is always honored, never silently overridden.
- At most ONE deletion per file per `--fix` invocation, to avoid a
  stale-span double-edit (a second deletion in the same file within one
  pass would need to account for the line-number shift the first one
  just made); a file with several dead symbols drains one per run.
- The post-deletion text must still `ast.parse` cleanly before the file
  is written -- a corrupted span never reaches disk.
- `bound_tests` binds the symbol's own conventional test file
  (`tests/test_<stem>.py` / `tests/unit/test_<stem>.py`, if one exists)
  as a smoke check -- a genuinely dead symbol by definition carries no
  `frob:tests` edge of its own, so there is no specific node id to bind;
  the whole conventional file (pytest accepts a bare path) is the
  closest available real regression signal, and a failure there rolls
  the deletion back byte-for-byte through the same commit-or-revert
  path `TIERBDEMO001` already proved end-to-end.

Split `_dead001_delete_one_symbol` out of the main handler (ARCH001's
60-line ceiling) to own the per-fix disk mechanics; the handler itself
owns finding/filtering candidates and the one-per-file cap.

Scope was declared as `_fix_engine_tier_b.py` + `_fix_engine.py` +
`tests/test_gates.py`; extended (reasons recorded in the scope_changes
audit trail) to `docs/design/check-fix-engine.md` (AFFECT001, the
Tier-B design doc's own "no concrete production handler exists yet"
section needed correcting) and `design/frob.strata` +
`tickets/T-1643/**` (SELFAUDIT001 interface sync via `frob sys
sync-interface`, and SCOPE001 for the ticket's own per-ticket ledger
file). Did not touch `_fix_engine.py` -- no Tier-A handler collision or
change was needed.

Three new tests in `TestFixEngineTierB` exercise the handler directly
(not through the full `apply_tier_b_fixes` transaction, matching the
class's own existing "prove the engine's decision logic, prove handlers
separately" split): a clean deletion removes exactly the dead symbol
and leaves the live one; a `frob:waive DEAD001`-covered finding is
skipped entirely, file untouched; and a file with two dead symbols only
loses one per pass. All 5 pre-existing `TestFixEngineTierB` tests and 8
`TestDeadSymbolGate` tests continue to pass unmodified.

### Changed
```
 design/frob.strata                   |   4 +-
 docs/design/check-fix-engine.md      |  40 +++++++---
 src/frob/gates/_fix_engine_tier_b.py | 151 ++++++++++++++++++++++++++++++++++-
 tests/test_gates.py                  |  93 +++++++++++++++++++++
 tickets/T-1643/done-report.md        |  85 ++++++++++++++++++++
 tickets/T-1643/ticket.md             |  28 ++++++-
 6 files changed, 382 insertions(+), 19 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestFixEngineTierB::test_dead001_removes_unreferenced_private_symbol` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFixEngineTierB::test_dead001_skips_a_waived_finding` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFixEngineTierB::test_dead001_at_most_one_deletion_per_file_per_pass` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 0 error(s), 1349 warning(s), 734 waived
- error-findings: none (measured, zero errors)
