## Done report

Delivered the reader-side half only; producer-side half deferred and
filed separately (below) because src/frob/app/ticket_runner/_rapid_sweep.py
(where the producer fix belongs) was under T-2313's live cross-worktree
lease for this ticket's entire working window -- T-2313 is fixing a
DIFFERENT defect in the same file (the blank/degenerate-identity class),
so touching it here would collide rather than coordinate.

READER-SIDE FIX (landed under this ticket):
Root cause, found by tracing the actual crash (not assumed from the
error text): `_expand_scope_globs_to_paths`'s old `try/except` wrapped
only the `root.glob(pattern)` CALL -- but `Path.glob()` returns a LAZY
generator, so the call itself never raises. The real
`NotImplementedError: Non-relative patterns are unsupported` (for an
absolute-path pattern) fires the moment something iterates the
generator, which happened in a `for match in matches:` loop OUTSIDE the
try/except. The guard existed and looked correct on read; it just never
actually caught anything. Fixed by moving the iteration inside the same
try block.

Also added: `_non_relative_scope_patterns()` + a named warning in
`_scope_overlap_warnings` so a malformed row is now surfaced loudly
("T-XXXX (state) has non-relative (absolute) scope entries, skipped for
overlap check: <path> -- repair via `frob ticket scope` (never
hand-edit)") instead of disappearing into the function's existing
best-effort silence -- satisfies the "must-still-pass: rejected loudly,
not silently coerced" control.

Verified against the real crash, not just logical inspection: committed
the repro test alone (5faa93da4), confirmed BOTH new tests genuinely
FAIL at that commit (checked by temporarily restoring main's pre-fix
_new.py into the worktree and re-running -- both failed with the exact
NotImplementedError from the real incident), then committed the fix
(b5fd5b90e) and re-ran -- all 7 tests in the file pass.
`--check-repro`/`--designate-repro` against base-ref 5faa93da4 confirms
FAILED_AT_PARENT (a real repro, not confirmatory-only).

Changed:
- src/frob/app/ticket_runner/_new.py::_expand_scope_globs_to_paths
- src/frob/app/ticket_runner/_new.py::_non_relative_scope_patterns (new)
- src/frob/app/ticket_runner/_new.py::_scope_overlap_warnings

Evidence:
- tests/unit/test_new_ticket_scope_overlap_warning.py::TestNonRelativeScopeDoesNotCrash::test_unrelated_ticket_still_files_despite_one_corrupt_row (designated repro, FAILED_AT_PARENT @ 5faa93da4)
- tests/unit/test_new_ticket_scope_overlap_warning.py::TestNonRelativeScopeDoesNotCrash::test_corrupt_row_is_named_loudly_not_silently_coerced
- tests/unit/test_new_ticket_scope_overlap_warning.py::TestScopeOverlapWarnings::test_overlapping_scope_names_the_other_ticket_and_path
- tests/unit/test_new_ticket_scope_overlap_warning.py::TestScopeOverlapWarnings::test_non_overlapping_scope_is_silent

Filed: T-2352 (producer-side half: normalize
_rapid_sweep.py::_file_regression_ticket's scope construction at its own
return boundary, same posture as T-2314's perf_gate fix; sequenced after
T-2313 since both touch the same file). Renumbers to a real id at land.

### Changed
```
 src/frob/app/ticket_runner/_new.py                 |  43 ++++++++-
 .../unit/test_new_ticket_scope_overlap_warning.py  | 105 +++++++++++++++++++++
 tickets/T-2342/ticket.md                           |  20 +++-
 tickets/T-2352/ticket.md                 |  83 ++++++++++++++++
 4 files changed, 243 insertions(+), 8 deletions(-)
```

### Evidence
- `tests/unit/test_new_ticket_scope_overlap_warning.py::TestNonRelativeScopeDoesNotCrash::test_unrelated_ticket_still_files_despite_one_corrupt_row` (pytest node id, verified passing when recorded)
- `tests/unit/test_new_ticket_scope_overlap_warning.py::TestNonRelativeScopeDoesNotCrash::test_corrupt_row_is_named_loudly_not_silently_coerced` (pytest node id, verified passing when recorded)
- `tests/unit/test_new_ticket_scope_overlap_warning.py::TestScopeOverlapWarnings::test_overlapping_scope_names_the_other_ticket_and_path` (pytest node id, verified passing when recorded)
- `tests/unit/test_new_ticket_scope_overlap_warning.py::TestScopeOverlapWarnings::test_non_overlapping_scope_is_silent` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH103@scripts/fleet_status.py, ARCH103@src/frob/release/_cli.py, COV001@scripts/fleet_status.py, COV001@src/frob/tickets/_land_git_ops.py, COV001@src/frob/tickets/_leases.py, COV001@src/frob/verify/_drain.py, COV001@src/frob/verify/_quarantine.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, DOC001@docs/commands/release.md, DOC002@scripts/fleet_status.py, DOC002@src/frob/app/verify_runner.py, DOC002@src/frob/verify/_drain.py, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, E501@/home/logan/projects/frob/.claude/worktrees/t-2342/src/frob/verify/_worker.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF004@src/frob/app/ticket_runner/_new.py, PRE001@tickets/T-2342, RENDER001@src/frob/release/_cli.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/tickets/_leases.py, TICK003@tickets.md, TICK004@tickets.md, WIRE003@docs/modules/cli.md
