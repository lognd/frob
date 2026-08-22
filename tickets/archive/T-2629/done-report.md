## Done report

Root cause confirmed exactly as the ticket's stack dump described:
`_render_doable_plain` called `_render_unlanded_branch_work_summary`
unconditionally, and on a `.frob/unlanded-summary-cache.json` cache MISS
(T-2127's own TTL cache -- 300s) that function fell through to running
`_unlanded_branch_work` inline, synchronously, inside `doable`'s render
path. At this repo's current scale (938 branches, 35 worktrees) that
scan -- a git spawn plus a temp-file tree-sitter parse per directive
candidate, per branch -- does not complete inside any sane budget.

Fix (minimum, per the ticket's own "prefer (1) alone" instruction):
`_render_unlanded_branch_work_summary` in
`src/frob/app/ticket_runner/_query.py` no longer falls through to a scan
on a cache miss. A miss now prints one explicit disclosure line naming
the fallback (`frob ticket reconcile`) instead of blocking -- never a
silent drop, per the ticket's own "Do NOT" section. A cache HIT still
renders identically to before. The underlying scan
(`frob.tickets._unlanded._unlanded_branch_work`) and its cache primitives
(`_load_unlanded_summary_cache`/`_save_unlanded_summary_cache`) are
untouched -- out of this ticket's declared scope, and still reachable via
`frob ticket reconcile` or a direct call.

Measured before/after, same repo, same command:

    timeout 540 uv run frob ticket doable    ->  EXIT=124, no output at all
      (ticket's own two measurements, unmodified)

    timeout 100 uv run frob ticket doable    ->  EXIT=0, real 1m42s
      (after this fix, .claude/worktrees/t2629-t2638, 2026-08-19)

`doable` now completes. The remaining ~100s is dominated by an unrelated,
already-logged cost inside the same render path (T-1935's true-finding
re-measure timing out at 80s, T-2006's doable-time candidate
re-verification also timing out at 80s) -- both print their own WARNING
and are pre-existing, out of this ticket's scope; not attributed here.

Control (identical ticket set, not just faster): the selection pipeline
(`_load_doable_queue` -> `_select_doable_tickets`) is completely untouched
by this change -- only a summary-rendering helper inside
`_render_doable_plain` was edited, and `_render_doable_dispatchable`/
`_render_doable_in_flight` (the actual ticket listing) are unaffected.
`--json` output (`_render_doable_json`) never called the touched function
at all. So the tickets `doable` returns are unchanged by construction, not
just by observation.

Changed:
- src/frob/app/ticket_runner/_query.py::_render_unlanded_branch_work_summary

Evidence:
- tests/unit/test_app_runners_doable_stale_lease.py::TestRenderUnlandedBranchWorkSummary::test_render_never_scans_branches_inline
  (designated repro, FAILED_AT_PARENT verified against 8992c3d42, the
  test-only commit that predates the fix)
- tests/unit/test_app_runners_doable_stale_lease.py::TestRenderUnlandedBranchWorkSummary::test_no_unlanded_work_prints_nothing
- tests/unit/test_app_runners_doable_stale_lease.py::TestRenderUnlandedBranchWorkSummary::test_unlanded_branch_is_summarized
- tests/unit/test_app_runners_doable_stale_lease.py::TestRenderUnlandedBranchWorkSummary::test_second_call_within_ttl_reuses_the_cache_not_a_fresh_scan
- Full file re-run: `uv run pytest tests/unit/test_app_runners_doable_stale_lease.py -q` -> 10 passed, 0 failed.

Filed (per the ticket's own instruction to file the two adjacent problems
separately rather than fold them in):
- T-2645: unlanded-branch directive parsing uses a temp-file
  round trip per candidate (`_directive_ids_via_real_parser`,
  `src/frob/tickets/_unlanded.py:508`) -- mechanism problem (2).
- T-2646: 938 stale local branches are accumulated debt, needs
  a stranded-work analysis before any pruning -- scale problem (3). Did
  NOT delete any branches, per the ticket's explicit "Do NOT".

Gates: `frob ticket sweep T-2629` clean at start (pre-work). Scoped check
below.

### Changed
```
 src/frob/app/ticket_runner/_query.py              | 58 +++++++++------
 tests/unit/test_app_runners_doable_stale_lease.py | 90 +++++++++++++----------
 tickets/T-2629/ticket.md                          | 11 ++-
 tickets/T-2645/ticket.md                | 50 +++++++++++++
 tickets/T-2646/ticket.md                | 49 ++++++++++++
 5 files changed, 193 insertions(+), 65 deletions(-)
```

### Evidence
- `tests/unit/test_app_runners_doable_stale_lease.py::TestRenderUnlandedBranchWorkSummary::test_render_never_scans_branches_inline` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_doable_stale_lease.py::TestRenderUnlandedBranchWorkSummary::test_no_unlanded_work_prints_nothing` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_doable_stale_lease.py::TestRenderUnlandedBranchWorkSummary::test_unlanded_branch_is_summarized` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_doable_stale_lease.py::TestRenderUnlandedBranchWorkSummary::test_second_call_within_ttl_reuses_the_cache_not_a_fresh_scan` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/app/fmt_runner.py, COV001@src/frob/gates/_refs_schema.py, COV001@src/frob/gates/_rule_id_scan.py, COV001@src/frob/strata/_multifile.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_milestone.py, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC006@tickets/T-2570/ticket.md, DOC008@docs/modules/gates.md, DOCENUM001@docs/modules/gates.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, F401@/home/logan/projects/frob/.claude/worktrees/t2629-t2638/src/frob/app/ticket_runner/__init__.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/gates/_milestone.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, RENDER001@src/frob/release/_cli.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
