## Done report

B9 was PARTIALLY closed on main before this ticket, not fully closed.

Main already had a loud SCOPE001/PRE001 violation for the primary B9 shape
(off-convention branch or `main` with a diff that touches real source and
no `--ticket`/no `T-####-` branch prefix) via `_build_ticket_scoped_jobs`'s
`no_ticket_blocks` path and `_no_active_ticket_violation`, with existing
tests in `TestRunGates` (`test_run_gates_blocks_scope_and_prework_when_no_
ticket_touches_source`, `test_run_gates_still_skips_scope_and_prework_for_
ledger_only_diff`). SCOPE001 additionally already had a separate,
unconditional `diff_load_failed` check (T-0550/B8) that fires loudly
regardless of ticket presence whenever the working diff itself fails to
load (detached HEAD, bad `--base`, no merge-base).

The remaining gap: PRE001 had NO equivalent `diff_load_failed` check. When
the working diff fails to load AND no ticket is derivable, `_load_diff`
degrades to an empty placeholder `Diff`. `no_ticket_blocks` (the shared
condition both scope's and prework's no-ticket branches consult) asks that
degraded diff what it touched, sees zero touched files, and silently
skipped PRE001 -- the exact B9 escape (loud-blocking is required, not a
skip), reached through the diff-load-failure door instead of the
branch-naming door. Reproduced directly before the fix: a repo with no git
history at all (`working_diff` has no merge-base, fails outright) and no
ticket derivable skipped `prework` while `scope` correctly blocked with
SCOPE001.

Fix: added a `st.diff_load_failed` branch to the `prework` job assembly in
`_build_ticket_scoped_jobs`, mirroring SCOPE001's existing pattern --
fires `_diff_load_failed_violation("PRE001", ...)` when no ticket is
derivable and the diff genuinely failed to load, instead of falling
through to the empty-diff no_ticket_blocks check. Scoped to the no-ticket
case only, since `prework_gate` itself does not consult the diff at all
when a valid ticket IS present (diff_load_failed is irrelevant there,
same as before).

The other two edge cases the ticket named were checked and found already
closed on main, with no code change needed:
- `--ticket` pointing at a nonexistent ticket id: `_resolve_ticket` looks
  the id up in the queue, finds nothing, logs a warning, and returns
  `ticket=None` -- which then routes through the same no-ticket-blocks
  loud-violation path as an off-convention branch. It does not silently
  skip (the violation message's "pass --ticket" wording is a little
  imprecise for this specific sub-case, since a --ticket WAS passed, but
  it still blocks, which is the actual B9 requirement).
- genuinely empty diff with no ticket: `no_ticket_blocks` is False and
  scope/prework are legitimately skipped (nothing touched, nothing to
  enforce) -- not a gap, this is correct behavior for e.g. a clean working
  tree on main.

No files outside src/frob/gates/ or tests/test_gates.py needed touching;
no scope extension was required.

### Changed
(no changed files detected)

### Evidence
- `tests/test_gates.py::TestRunGates::test_run_gates_blocks_prework_when_diff_load_fails_with_no_ticket` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestRunGates::test_run_gates_blocks_scope_and_prework_when_no_ticket_touches_source` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestRunGates::test_run_gates_skips_scope_without_ticket` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestRunGates::test_run_gates_still_skips_scope_and_prework_for_ledger_only_diff` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 0 error(s), 1200 warning(s), 211 waived
