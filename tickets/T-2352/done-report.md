## Done report

Producer-side half of T-2342/T-2308's incident. Root cause confirmed by
reading src/frob/app/ticket_runner/_rapid_sweep.py::_file_regression_
ticket: `scope=tuple(sorted({file for _, file in unfiled_pairs}))` used
each finding's `.file` as-is, with no relativization against `root` --
when the upstream diagnostic collection reported an absolute path (as it
did for T-1753, T-1756, T-2308), that absolute path was written directly
into the newly-filed ticket's `scope:`, which crashed `frob ticket new`
fleet-wide (T-2342's reader-side fix already lands the immediate
mitigation; this closes the actual source).

Fix: added `_relativize_regression_scope_file(root, file) -> str`,
applied at the `scope=` construction boundary -- the exact producer's own
return boundary, same posture as T-2314's `_relativize_perf_violation_
file` fix for the analogous `perf_gate` defect. Relativizes an absolute
path under `root`; is a no-op for an already-relative path; and for the
anomalous case of an absolute path that does NOT resolve under `root` at
all, keeps it as-is and logs a WARNING naming the path rather than
silently coercing it into a wrong-but-plausible relative path (the
must-still-pass control).

Verified against a genuine repro, not just logical inspection: committed
the repro tests alone (a9f9888c0), confirmed the whole test module fails
to COLLECT at that commit against the pre-fix source (ImportError: the
new helper does not exist yet -- a stronger signal than an assertion
failure, since the test module cannot even import), restored the fix
(00923d214), re-ran -- all 11 tests (3 unit + 1 end-to-end + 7 pre-
existing TestFileRegressionTicket) pass. `--check-repro`/
`--designate-repro` against base-ref a9f9888c0 confirms FAILED_AT_PARENT.

The end-to-end test (test_filed_ticket_scope_is_relative_end_to_end)
exercises the real T-2308 incident shape through the actual filer, not
just the helper in isolation: files a regression ticket for an ABSOLUTE
finding path and asserts the resulting ticket's `scope:` is relative.

Changed:
- src/frob/app/ticket_runner/_rapid_sweep.py::_relativize_regression_scope_file (new)
- src/frob/app/ticket_runner/_rapid_sweep.py::_file_regression_ticket (scope= construction now relativizes)

Evidence:
- tests/unit/test_rapid_sweep.py::TestRelativizeRegressionScopeFile::test_absolute_under_root_is_relativized
- tests/unit/test_rapid_sweep.py::TestRelativizeRegressionScopeFile::test_already_relative_is_unchanged
- tests/unit/test_rapid_sweep.py::TestRelativizeRegressionScopeFile::test_absolute_outside_root_is_kept_and_logged
- tests/unit/test_rapid_sweep.py::TestRelativizeRegressionScopeFile::test_filed_ticket_scope_is_relative_end_to_end (designated repro, FAILED_AT_PARENT @ a9f9888c0)

Filed: none -- this closes T-2342's own deferred producer half; no new
follow-up needed.

### Changed
```
 src/frob/app/ticket_runner/_rapid_sweep.py | 38 ++++++++++++++++-
 tests/unit/test_rapid_sweep.py             | 68 ++++++++++++++++++++++++++++++
 tickets/T-2352/ticket.md                   | 11 ++++-
 3 files changed, 114 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/unit/test_rapid_sweep.py::TestRelativizeRegressionScopeFile::test_absolute_under_root_is_relativized` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestRelativizeRegressionScopeFile::test_already_relative_is_unchanged` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestRelativizeRegressionScopeFile::test_absolute_outside_root_is_kept_and_logged` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestRelativizeRegressionScopeFile::test_filed_ticket_scope_is_relative_end_to_end` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, AFFECT001@src/frob/app/ticket_runner/_rapid_sweep.py, ARCH103@scripts/fleet_status.py, ARCH103@src/frob/release/_cli.py, COV001@scripts/fleet_status.py, COV001@src/frob/tickets/_land_git_ops.py, COV001@src/frob/verify/_drain.py, COV001@src/frob/verify/_quarantine.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, DOC001@docs/commands/release.md, DOC002@scripts/fleet_status.py, DOC002@src/frob/app/verify_runner.py, DOC002@src/frob/verify/_drain.py, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2352/src/frob/app/ticket_runner/_rapid_sweep.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2352/src/frob/verify/_worker.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF004@src/frob/app/ticket_runner/_new.py, PRE001@tickets/T-2352, RENDER001@src/frob/release/_cli.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE003@docs/modules/cli.md
