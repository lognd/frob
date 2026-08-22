## Done report

Added a second, independent filter to `_raise_quarantine_for_red_batch`
(alongside the existing T-1847 warm-tree native-noise filter): any pair
attributed to a still-open ticket (`_ticket_is_open`, reused from
`_partition_findings_by_attribution` -- no second predicate written) is
dropped from the set that raises quarantine. Filing is unaffected: the
filing path already skipped re-filing an open-ticket-owned pair (T-1690),
and this change touches only whether the circuit breaker trips, not
whether the finding is recorded.

Two pre-existing tests encoded the bug as expected behavior
(`TestRaiseQuarantineForRedBatch::test_raised_even_when_every_pair_already_has_an_open_ticket`
and `test_warm_tree_recheck_never_drops_an_attributed_finding`'s use of an
open-ticket owner) and were rewritten: the former replaced by
`test_open_ticket_attribution_clears_the_quarantine_raise` (positive
control: open-ticket attribution no longer raises, still filed/recorded);
the latter's owner ticket switched from open to closed so it keeps testing
its own real subject (the T-1847 warm-tree filter must never drop an
ATTRIBUTED finding) without being confounded by the new open-ticket
filter.

`TestAutoDisposeFiledFindings::test_leaves_quarantine_raised_when_other_findings_remain_undisposed`
also relied on an open-ticket-attributed pair to construct "a finding this
call's own filing never covers" -- exactly the scenario T-2604 makes
unreachable via `_file_regression_ticket`'s attribution path. Rewrote it
to call `_auto_dispose_filed_findings` directly against a record raised
independently, which tests the same real subject (clear_quarantine's
atomic all-or-nothing contract) without depending on attribution mechanics.

Added three new positive-control tests:
`test_closed_ticket_attribution_still_raises` (closed/dropped attribution
still trips quarantine -- without this the fix would be indistinguishable
from disabling quarantine), and
`test_unattributed_still_raises_alongside_open_ticket_finding` (a batch
mixing one open-ticket finding with one unattributed finding still raises,
naming only the unattributed one).

## Done report

Changed:
- src/frob/app/ticket_runner/_rapid_sweep.py::_raise_quarantine_for_red_batch

Evidence:
- tests/unit/test_rapid_sweep.py::TestRaiseQuarantineForRedBatch::test_open_ticket_attribution_clears_the_quarantine_raise (designated repro, FAILED_AT_PARENT verified against ee851389c)
- tests/unit/test_rapid_sweep.py::TestRaiseQuarantineForRedBatch::test_closed_ticket_attribution_still_raises
- tests/unit/test_rapid_sweep.py::TestRaiseQuarantineForRedBatch::test_unattributed_still_raises_alongside_open_ticket_finding
- tests/unit/test_rapid_sweep.py::TestRaiseQuarantineForRedBatch::test_warm_tree_recheck_never_drops_an_attributed_finding
- tests/unit/test_rapid_sweep.py::TestAutoDisposeFiledFindings::test_leaves_quarantine_raised_when_other_findings_remain_undisposed

Full tests/unit/test_rapid_sweep.py: 147 passed, 0 failed (measured, no FROB_WORKTREE lease env set -- with it set, unrelated tests that create their own tmp_path git-less repos spuriously fail on a worktree-lease guard; a pre-existing environmental artifact of this test file, not caused by this change).

Filed: none. Widened T-2604's own scope to include tests/unit/test_rapid_sweep.py (via `frob ticket scope --add`) since evidence required editing existing tests in that file, not just the source module.

Gates: `frob check --budget 480 --ticket T-2604` and a full unscoped `--only gates-fast --delta` run both show 35 errors/358 warnings, matching pre-existing repo-wide counts unrelated to src/frob/app/ticket_runner/_rapid_sweep.py or tests/unit/test_rapid_sweep.py (grepped the full output for both filenames: zero hits). No stamped baseline was available in this worktree to diff against, so --delta showed "no baseline found, showing all violations" -- counts were cross-checked instead against the unscoped --budget run's identical totals for the same gate groups.

### Changed
```
 src/frob/app/ticket_runner/_rapid_sweep.py |  42 ++++-
 tests/unit/test_rapid_sweep.py             | 247 +++++++++++++++++++++--------
 tickets/T-2604/ticket.md                   |  17 +-
 3 files changed, 240 insertions(+), 66 deletions(-)
```

### Evidence
- `tests/unit/test_rapid_sweep.py::TestRaiseQuarantineForRedBatch::test_open_ticket_attribution_clears_the_quarantine_raise` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestRaiseQuarantineForRedBatch::test_closed_ticket_attribution_still_raises` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestRaiseQuarantineForRedBatch::test_unattributed_still_raises_alongside_open_ticket_finding` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestRaiseQuarantineForRedBatch::test_warm_tree_recheck_never_drops_an_attributed_finding` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestAutoDisposeFiledFindings::test_leaves_quarantine_raised_when_other_findings_remain_undisposed` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH001@src/frob/app/ticket_runner/_rapid_sweep.py, ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/app/fmt_runner.py, COV001@src/frob/gates/_refs_schema.py, COV001@src/frob/gates/_rule_id_scan.py, COV001@src/frob/strata/_multifile.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-1791, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC006@tickets/T-2570/ticket.md, DOC008@docs/modules/gates.md, DOCENUM001@docs/modules/gates.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, PRE001@tickets/T-2604, RENDER001@src/frob/release/_cli.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
