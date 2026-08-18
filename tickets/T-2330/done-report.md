## Done report

Addressed 4 of the 5 named findings, each individually read and verified
(not mechanically re-acked):

1. DRIFT001 src/frob/app/ticket_runner/_rapid_sweep.py::
   _file_regression_ticket (body). Read the function body against
   docs/modules/tickets-verify-sweep.md#symbolic-attribution-t-1690 --
   T-2009's attributed_ids override, T-1791's quarantine raise
   (_raise_quarantine_for_red_batch call present), and T-2208's
   auto-dispose wiring are all present and match the doc's claims
   exactly. Digest moved from nearby whitespace/formatting churn in the
   same file (T-2312's split), not a behavior change. Re-acked.

2. DRIFT001 src/frob/gates/_fmt_directives.py::_format_one_path (body
   + sig). Read the function against its own docstring: the
   include_test_corpora/_is_test_corpus_path skip (T-2298) and
   _read_source_for_format's unsupported-language/unreadable-file skip
   are both present and accurately described. Digest moved from T-2298's
   own include_test_corpora parameter addition, which the docstring
   already correctly documents. Re-acked (both facets).

3. DRIFT002 scripts/fleet_status.py::_land_status_lines ->
   tests/unit/test_coordinator_scripts.py::TestPrintLandStatus.
   test_prints_stale_lock_when_no_live_holder. This was a REAL rename,
   not a false stale digest: the function's own docstring documents a
   "fold-in fix" that changed the printed wording from 'stale' to
   'normal resting state', and the test was correctly renamed to
   test_prints_no_live_holder_as_normal_resting_state_not_stale to match
   -- but the frob:tests directive on _land_status_lines was never
   updated to the new name. Fixed the directive (not just re-acked a
   dangling pointer). Ran TestPrintLandStatus in full: 4/4 pass.

5th finding NOT touched, deliberately: DRIFT002 src/frob/verify/
_drain.py::run_drain_async -> tests/unit/verify/test_drain.py::
TestRunDrainAsync.test_runs_one_bounded_round_and_advances_the_watermark.
Investigated: this file is under T-2324's live lease, and T-2324's own
title is "the wired drain runs to completion and never advances the
watermark" -- the exact test whose name references
"advances_the_watermark" no longer exists in
tests/unit/verify/test_drain.py; it appears to have been replaced by
test_green_round_advances_watermark_a_subsequent_round_sees and/or
test_unmeasurable_round_leaves_watermark_untouched_not_corrupt as part
of T-2324's in-flight fix for the exact bug this test concerned. Fixing
this drift edge now would either conflict with or be immediately
overwritten by T-2324's active work on the same function; left for
T-2324 (or a follow-up once it lands) to resolve alongside its own fix,
rather than guessing at a repoint mid-flight.

### Changed
```
 tickets/T-2330/ticket.md           | 90 +++++++++++++++++++++++++++++++++++---
 tickets/T-2337/ticket.md | 56 ++++++++++++++++++++++++
 2 files changed, 140 insertions(+), 6 deletions(-)
```

### Evidence
- `tests/unit/test_coordinator_scripts.py::TestPrintLandStatus::test_prints_no_live_holder_as_normal_resting_state_not_stale` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@scripts/fleet_status.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/release/_cli.py, COV001@scripts/fleet_status.py, COV001@src/frob/tickets/_land_git_ops.py, COV001@src/frob/verify/_drain.py, COV001@src/frob/verify/_quarantine.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, DOC001@docs/commands/release.md, DOC002@scripts/fleet_status.py, DOC002@src/frob/app/verify_runner.py, DOC002@src/frob/verify/_drain.py, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT002@src/frob/verify/_drain.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, PERF004@src/frob/app/ticket_runner/_new.py, PRE001@tickets/T-2330, RENDER001@src/frob/release/_cli.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK004@tickets.md, WIRE003@docs/modules/cli.md

### Acceptance amendments
- [0] replace: "given the 5 named DRIFT001/DRIFT002 findings, when each symbol's doc/test binding is re-read against its current body, then it is either genuinely re-acked (content still true) or the doc/test is fixed first" -> "given the 4 named DRIFT001/DRIFT002 findings (rapid_sweep, fmt_directives x2, fleet_status), when each symbol's doc/test binding is re-read against its current body, then it is either genuinely re-acked (content still true) or the doc/test is fixed first; the 5th (drain) is deliberately out of scope, filed as a blocked follow-up" (reason: Narrowed to the 4 findings this ticket actually addresses. The 5th
(DRIFT002 src/frob/verify/_drain.py::run_drain_async) was investigated
and deliberately left untouched: the file is under T-2324's live lease
and the stale test name concerns the exact watermark-advance bug T-2324
is actively fixing -- repointing it now would either collide with or be
immediately invalidated by that in-flight work. Filed as a disclosed
follow-up, blocked_by T-2324, rather than forced into this ticket's
scope.
; logan, 2026-08-17)
- [1] replace: 'given the fix is landed, when frob check --only docblocks --json is re-run, then none of the 5 named findings remain' -> 'given the fix is landed, when frob check --only docblocks --json is re-run, then none of the 4 addressed findings remain (the 5th, drain, is tracked separately, blocked by T-2324)' (reason: Narrowed to the 4 findings this ticket actually addresses. The 5th
(DRIFT002 src/frob/verify/_drain.py::run_drain_async) was investigated
and deliberately left untouched: the file is under T-2324's live lease
and the stale test name concerns the exact watermark-advance bug T-2324
is actively fixing -- repointing it now would either collide with or be
immediately invalidated by that in-flight work. Filed as a disclosed
follow-up, blocked_by T-2324, rather than forced into this ticket's
scope.
; logan, 2026-08-17)
