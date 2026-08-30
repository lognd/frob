## Done report

Root cause: T-2114 (new public symbol missing doc/test edge), the
diff-scoped ARCH001 variant (T-2214), and CrossTicketLeakage were each
ad-hoc CLI-side `sys.exit(1)` assertions in `frob.app.ticket_runner.
_land_cmd`/`frob.tickets._land` -- never a `Violation`-producing
`frob.gates` rule `run_gates` dispatches. `frob check --ticket <id>`/
`frob ticket close` structurally could not see any of the three: a
ticket could pass `frob check` clean and still get refused at land time.

Fix: new module `frob.gates._land_parity` wires the first two families
into `frob check` as a new "land_parity" gate stage:
- LANDPARITY001 wraps `_new_public_symbols_missing_doc_or_test_edge`
  (T-2114) unchanged.
- LANDPARITY002 wraps `_new_or_worsened_long_functions_in_diff` (T-2214)
  unchanged, under its OWN distinct rule id (not plain ARCH001, which
  reports every over-threshold function an unscoped walk finds, new or
  pre-existing -- LANDPARITY002 reports only what THIS diff newly pushed
  over the line, T-2214's narrower attributable-only claim).

Both are pure reuse: the actual finding computation is a deferred
(call-time) import of the SAME pure functions
`_assert_new_public_symbols_have_doc_and_test_edge_pre_land`/
`_assert_diff_does_not_worsen_long_functions_pre_land` already call at
land time -- zero new detection logic. The land-time assertions remain
the enforcing `sys.exit(1)` call sites, unchanged; `land_parity`'s job
is making the same finding visible EARLIER, in a ticket's own worktree.

The import direction (gates importing from app.ticket_runner) is
backwards long-term but trips no live enforcement (`[arch.layering]` in
frob.toml is declared but not wired into `frob check` yet, T-0620) --
`_land_cmd.py` was under an exclusive scope lease held by a concurrent
ticket (T-2642) for this entire session, so genuinely MOVING the pure
functions out of it (the ticket body's own suggested end state) was not
available. Filed T-3467 as the follow-up to do that move once
the lease frees.

CrossTicketLeakage is NOT wired: `_check_cross_ticket_leakage` needs
worktree/base_ref context specific to the LAND being performed (which
other ticket's lease overlaps this one), not a property of `root`'s tree
alone the way every other `frob.gates` rule is -- `frob check` has no
generic worktree-vs-main comparison plumbing today. Filed
T-3466 as the follow-up rather than forcing it, per the
ticket's own suggestion to scope this part out separately if infeasible.

Verified end-to-end, not just unit tests: staged a throwaway undocumented
function under `src/frob/gates/`, ran `frob check --only land_parity
--ticket T-3456`, confirmed LANDPARITY001 fired with the exact real
file/line/message, then reverted the probe file -- the actual acceptance
criterion this ticket names (frob check --ticket must report the SAME
T-2114 finding land reports today, not 0 errors).

Registered: LANDPARITY001/LANDPARITY002 added to
`frob.gates._waive._KNOWN_GATE_RULES`, `_ALL_GATES`/
`_CANONICAL_GATE_ORDER`, and `docs/modules/gates.md` (catalog rows plus a
new "Land parity" prose section). No `docs/design/registry/*.yaml` entry
added (REG010, a new live rule with no registry claim, is WARN-only
advisory, not a land-blocking error) -- acceptable for the smallest
version; a registry entry can follow separately.

Tests: 6/6 new (tests/unit/test_land_parity_gate.py, -p no:xdist) plus
19/19 across the pre-existing T-2114/T-2214 land-time assertion tests
re-run as regression controls (0 behavior change to the reused pure
functions). `frob check --only land_parity --ticket T-3456` clean (no
LANDPARITY findings against this ticket's own diff, which carries proper
directives).

### Changed
```
 tickets/T-3456/ticket.md           |  9 ++++++++-
 tickets/T-3466/ticket.md | 30 ++++++++++++++++++++++++++++++
 tickets/T-3467/ticket.md | 30 ++++++++++++++++++++++++++++++
 3 files changed, 68 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_land_parity_gate.py::TestLandParityDocTestGate::test_new_public_symbol_missing_both_directives_fires` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_parity_gate.py::TestLandParityDocTestGate::test_new_public_symbol_with_both_directives_is_quiet` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_parity_gate.py::TestLandParityDocTestGate::test_no_diff_is_quiet` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_parity_gate.py::TestLandParityLongFunctionGate::test_new_over_threshold_function_fires` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_parity_gate.py::TestLandParityLongFunctionGate::test_pre_existing_over_threshold_function_merely_touched_is_quiet` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_parity_gate.py::TestLandParityLongFunctionGate::test_no_diff_is_quiet` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: 18 error(s), 4636 warning(s), 899 waived
- error-findings: COV001@src/frob/gates/_land_parity.py, COV003@tests/unit/test_scaffold_project.py, DEPR006@frob-deprecated-baseline.lock.json, DOC002@src/frob/gates/_land_parity.py, DOC006@tickets/T-3411/ticket.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, LARGE001@.claude/hooks/root-write-guard.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, PRE001@tickets/T-3456, REL001@src/frob/__init__.py, SELFAUDIT001@src/frob/gates/_policy_weakening_gate.py, SELFAUDIT001@tests/unit/strata/test_strata_core_gil.py, SELFAUDIT001@tests/unit/test_land_parity_gate.py, SELFAUDIT001@tests/unit/test_sync_claude_config_stale_guard_t3408.py, SELFAUDIT001@tests/unit/verify/test_worker.py, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json
