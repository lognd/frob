## Done report

The ticket's premise (that terminal-state work strands invisibly with no
detection or surfacing) was already substantially fixed on main by
T-1934/T-1948/T-1955/T-2125 (all landed 2026-08-10/11, the same day this
ticket was filed): frob.tickets._unlanded._unlanded_branch_work already
does the branch-vs-main terminal-state comparison, and
frob.app.ticket_runner._query._render_unlanded_branch_work_summary
already calls it unconditionally from `doable`'s render path
(_render_doable_plain), plus frob.tickets._leases (sweep's kept:unlanded
verdict) and frob.tickets._reconcile both already consult it too.
Confirmed by direct invocation: _unlanded_branch_work(root) against this
repo's real history found 5 genuine strong (done-report/local-state-done)
findings, e.g. ticket_id='T-1860' branch='t-1860' state_on_main='queued'
-- the detector works and finds real problems.

The remaining, real, in-scope defect: _unlanded_branch_work is a git
spawn per local branch (diff + grep + ls-tree). Measured directly:
94.9s wall against this repo's ~150 local branches. Since
_render_unlanded_branch_work_summary runs this UNCONDITIONALLY on every
`frob ticket doable` call with no caching, and every dispatched agent is
required to run frob verbs under a foreground timeout comfortably under
~120s (docs/guides/agent-playbook.md section 3b), a bare `frob ticket
doable` in this repo now reliably exceeds that budget BECAUSE of this
scan alone -- confirmed directly: `timeout 110 uv run frob ticket
doable` timed out (exit 124) twice. The T-1934 summary line -- the
entire visibility mechanism T-2127 asks for -- is therefore structurally
unreachable in practice: it is correct code a caller times out before
ever executing.

Fix (src/frob/app/ticket_runner/_query.py, the ticket's own declared
scope): _render_unlanded_branch_work_summary now memoizes the branch
list from _unlanded_branch_work in .frob/unlanded-summary-cache.json
for 300s (_UNLANDED_SUMMARY_CACHE_TTL_S). A cache hit within the TTL
skips the scan entirely; a miss runs it once and refreshes the cache.
The detector itself (frob.tickets._unlanded) is untouched -- out of
this ticket's declared scope, and it was not the defect.

Repro: test_second_call_within_ttl_reuses_the_cache_not_a_fresh_scan
committed alone at 006fdbbfb, confirmed FAILED_AT_PARENT via `frob
ticket evidence --check-repro ... --base-ref 006fdbbfb` (ImportError on
the not-yet-existing cache helpers). Fix committed separately at
ba7afe9eb.

Tests: 9 passed in tests/unit/test_app_runners_doable_stale_lease.py
(was 5 before this ticket -- test_no_root_returns_empty and 4 in
TestStaleLeaseReasons were pre-existing, plus the 3 pre-existing
TestRenderUnlandedBranchWorkSummary tests, plus my 4 new ones = 9),
`uv run pytest tests/unit/test_app_runners_doable_stale_lease.py
-o addopts="" -q` -- "9 passed".

MUST-STILL-PASS control: test_unlanded_branch_is_summarized (a
pre-existing test) still passes unmodified -- the cache does not
suppress a real finding on a cold cache, only skips RE-scanning within
the TTL. test_expired_cache_is_ignored confirms a stale cache entry is
never trusted past its TTL.

`frob check --ticket T-2127`: 0 errors attributable to
src/frob/app/ticket_runner/_query.py or
tests/unit/test_app_runners_doable_stale_lease.py (checked directly
against the JSON diagnostics for both file paths). Remaining errors in
the run are pre-existing repo-wide debt (ARCH001 line-count thresholds
on unrelated functions, DOC011 stale ticket-id citations, TICK004
ticket-rot, ruff E501 on unrelated files, frob-cycle import cycles) --
38 errors both before and after this change, none in my two files.

Cut: `frob ticket doable`'s FULL command latency at ~150 branches was
not otherwise reduced -- the cache only removes the unlanded-branch
portion of that cost on repeat calls within 300s; a genuinely cold
`doable` (first call, or after the TTL) still pays the full ~95s scan.
That scan's own per-branch cost is frob.tickets._unlanded's algorithm,
out of this ticket's declared scope (src/frob/app/ticket_runner/
_query.py only) -- noted, not fixed here.

### Changed
```
 src/frob/app/ticket_runner/_query.py              | 98 +++++++++++++++++++++--
 tests/unit/test_app_runners_doable_stale_lease.py | 79 ++++++++++++++++++
 tickets/T-2127/ticket.md                          | 18 ++++-
 tickets/T-2142/ticket.md                          |  7 +-
 tickets/T-2158/ticket.md                          |  7 +-
 tickets/T-2209/ticket.md                          |  7 +-
 6 files changed, 203 insertions(+), 13 deletions(-)
```

### Evidence
- `tests/unit/test_app_runners_doable_stale_lease.py::TestRenderUnlandedBranchWorkSummary::test_second_call_within_ttl_reuses_the_cache_not_a_fresh_scan` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_doable_stale_lease.py::TestRenderUnlandedBranchWorkSummary::test_expired_cache_is_ignored` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_doable_stale_lease.py::TestRenderUnlandedBranchWorkSummary::test_fresh_cache_round_trips` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_doable_stale_lease.py::TestRenderUnlandedBranchWorkSummary::test_unlanded_branch_is_summarized` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH001@scripts/fleet_status.py, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, COV001@scripts/fleet_status.py, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md, COV004@tickets/T-draft-0bd874ac/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-draft-0bd874ac/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_land_cmd.py, DRIFT001@src/frob/lang/_nodes.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2207/src/frob/lang/_nodes.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, SELFAUDIT001@design, TEST010@tests/test_ticket_work_and_land_finish.py, TICK004@tickets.md
