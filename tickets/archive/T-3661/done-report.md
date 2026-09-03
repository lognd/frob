## Done report

Windows CI run 33521416410 (T-3659's campaign): `_REF_ALLOWLIST_RE`'s POSIX-only charset in src/frob/tickets/_leases.py silently dropped every lease record whose `worktree` field carried Windows path syntax (drive-letter colon + backslash separators), since `_lease_shape_is_safe` rejected it as an unsafe argv operand. This broke `_rel001_land_owned` (REL001 never suppressed as land-owned on win32) and `_other_ticket_holding_live_lease` (a narrowed live lease silently ignored in favor of the stale declared scope) -- confirmed via tests/gates_suite/test_debt.py::TestDebtGate::test_rel001_land_owned_via_ticket_lease and tests/gates_suite/test_fix_engine.py::TestFixEngineScopeLease::test_narrowed_live_lease_wins_over_stale_declared_scope_lease_filter's tracebacks.

Fix: a dedicated, wider `_WORKTREE_PATH_ALLOWLIST_RE`/`_looks_like_a_safe_worktree_path_operand` for the `worktree` field only (adds `:`/`\` to the charset, keeps the leading-`-` injection guard intact) -- `branch` keeps the original, narrower check since a git ref name never legitimately needs those characters on any platform.

Evidence: 3 new tests in tests/test_tickets_leases.py::TestLeaseShapeValidation exercise the widened admission check directly (a pure-function unit case plus two `read_all_leases` integration cases simulating a Windows-shaped worktree path via a POSIX directory literally named with backslash/colon characters, since `PurePath`/`PosixPath` never treats those as separators). `--check-repro` confirmed a genuine repro against the test-only commit (63e0c885d), before the fix commit (d0b4cc1b4).

This only fixes 2 of T-3659's 6 filed win32 buckets (T-3661 itself); the other 4 (T-3662/T-3664/T-3665/T-3667) and the out-of-scope conftest.py bucket (T-3666) are separate tickets in the same series. CI's next win32 leg is this fix's real end-to-end verifier, since the bug is in what a regex admits, not something a POSIX Path object reproduces identically.

### Changed
```
 src/frob/tickets/_leases.py  | 44 +++++++++++++++++++++++++++--
 tests/test_tickets_leases.py | 66 ++++++++++++++++++++++++++++++++++++++++++++
 tickets/T-3661/ticket.md     | 14 +++++++++-
 3 files changed, 121 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/test_tickets_leases.py::TestLeaseShapeValidation::test_read_all_leases_admits_a_windows_style_worktree_path` (pytest node id, verified passing when recorded)
- `tests/test_tickets_leases.py::TestLeaseShapeValidation::test_read_all_leases_still_drops_a_dash_prefixed_windows_style_worktree` (pytest node id, verified passing when recorded)
- `tests/test_tickets_leases.py::TestLeaseShapeValidation::test_worktree_operand_check_admits_windows_paths_directly` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 17 error(s), 4356 warning(s), 896 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV003@tests/test_ci_workflow_matrix.py, COV007@src/frob/strata/_capacity.py, DEPR006@frob-deprecated-baseline.lock.json, DOC007@tests/test_tickets_leases.py, DRIFT001@src/frob/process/_derived_lock.py, DRIFT002@docs/modules/process.md, DRIFT002@tests/test_tickets_leases.py, LARGE001@src/frob/refactor/_scan.py, LARGE001@src/frob/refactor/_verify.py, OPAQUE001@src/frob/app/_config_external.py, PRE001@tickets/T-3661, REF002@src/frob/process/_lock_msvcrt.py, REL001@src/frob/__init__.py, SEC110@tests/ticket_land_suite/test_wip.py, TEST001@src/frob/strata/_models.py, WAIVE011@frob-ratchet.lock.json
