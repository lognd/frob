## Done report

Changed:
- src/frob/stats/__init__.py::collect (public signature: now takes `queue: TicketQueue | None` as a caller-injected parameter instead of loading it via `load_queue`; import retargeted from `frob.tickets` to `frob.tickets._models` for TicketQueue/TicketState)
- src/frob/app/stats_runner.py::_run_body (loads the queue via `frob.tickets.load_queue` and injects it into `collect()`)
- src/frob/serve/_tools.py::frob_stats (loads the queue via the module's existing top-level `load_queue` import and injects it into `collect()`)
- docs/modules/stats.md#public-api (collect() signature updated)
- docs/modules/serve.md#tools (frob_stats doc note on the injection, closes AFFECT001)
- tests/test_stats.py: updated test_collect_combines_both for the new signature; added test_collect_injected_queue_matches_direct_ticket_stats (positive control: injected queue produces identical StatsReport.tickets to a direct ticket_stats() call) and test_collect_with_no_queue_reports_empty_ticket_stats (queue=None degrade path)

Per owner decision on T-2583 (2026-08-19): break the cycle at candidate 2
only. Candidates 1/3/4/5 were explicitly NOT taken -- each is a separate
architectural decision belonging to the owner, not authorized by this
ticket (confirmed with the coordinator mid-ticket after I found the SCC
persists without them; see below).

Evidence:
- tests/test_stats.py::test_collect_injected_queue_matches_direct_ticket_stats (designated repro; `frob ticket evidence T-2583 --check-repro` reports FAILED_AT_PARENT against b82f0b0c3, the repro-only commit that adds the tests before the fix commit)
- tests/test_stats.py::test_collect_with_no_queue_reports_empty_ticket_stats
- Both-directions positive controls, all measured directly:
  - `frob.stats` is confirmed GONE from the CYCLE001 SCC's node list on all three path shapes (`frob cycle src/frob`, `frob cycle src`, `frob cycle .` -- T-2588 parity holds, all three agree).
  - `collect()` with an injected queue returns IDENTICAL `StatsReport.tickets` to a direct `ticket_stats(queue)` call over the same queue (test_collect_injected_queue_matches_direct_ticket_stats, passing).
  - Negative control: temporarily re-adding `from frob.tickets import load_queue` to stats/__init__.py makes CYCLE001 fire again (`frob cycle src/frob` picked frob/stats back up, 7 hits) -- the detector is still watching this edge, not the waiver. Reverted before committing; final tree has no such import.
- `uv run pytest tests/integration/test_interfaces.py::TestInterfaces::test_app_runner_map tests/integration/test_interfaces.py::TestInterfaces::test_serve_tools tests/test_app_daemon_proxy.py::TestDifferentialParity::test_stats_json_daemon_matches_in_process -q` -- 3 passed (daemon/in-process parity for frob_stats unaffected).
- `uv run frob test --base main` (touched-set selection) -- 7 selected, 6 pass; the 7th (test_collect_combines_both) fails identically on unmodified main (confirmed directly: `git commit -m stats.total==1/commits.total==1` assertion fails with `assert 2 == 1` because `new_ticket()` makes its own auto-commit -- pre-existing, unrelated to this change, not touched by this ticket).

What was NOT done, and why:
- `frob check --only cycle` is NOT clean. Re-measured directly after the
  candidate-2 fix landed in the worktree: the 160-node SCC is still
  present, closed entirely by edges that never route through frob.stats.
  Grepped the current source (not the original ticket's description) to
  confirm which edges are still live: candidate 1 (serve/_tools.py:24,
  top-level `from frob.tickets import doable, load_queue`), candidate 3
  (tickets/_land.py, function-local `from frob.testing._models import
  CollectedTests`), candidate 4 (testing/_coverage_wait.py:163,
  function-local `from frob.app._daemon_proxy import ...`), candidate 5
  (app/_daemon_proxy.py, several function-local `from frob.serve import
  ...`) -- all still present, plus a sixth edge the original T-2363
  analysis never enumerated: serve/_tools.py:606's own independent
  function-local `from frob.testing import ...`. This falsifies the
  ticket's own contingency text, which assumed only candidate 5 would be
  the holdout. Filed as T-2667 (an owner-decision ticket, no
  candidate picked, corrected picture of the remaining edge set).
- The `frob:waive CYCLE001` at src/frob/__init__.py was NOT removed. Per
  coordinator instruction: the SCC is still live, so the waiver's
  underlying finding is still true; removing it would leave a real
  finding unaccounted for. Its premise text is stale (still describes the
  original 5-candidate framing) and needs updating, deferred to whoever
  picks up T-2667.
- Candidates 1/3/4 were not implemented, on direct coordinator instruction
  mid-ticket: each is a separate architectural decision (MCP tool data
  injection, a genuine land-time runtime need, a deliberately-deferred
  daemon-lease fast path) that belongs to the repo owner, not something
  this ticket's "implement candidate 2" decision authorizes.

Filed: T-2667 (residue: owner-decision ticket for the remaining
stats-independent SCC, corrected picture including the sixth edge)

Gates: `uv run frob check --ticket T-2583` clean of anything attributable
to this diff -- SCOPE001/SCOPE002/COV002/AFFECT001 findings against
touched files were addressed (scope widened to the files actually touched:
docs/modules/stats.md, docs/modules/serve.md, src/frob/app/stats_runner.py,
tests/test_stats.py, plus the new draft ticket's own file; frob:ticket
edges added to the 3 stats tests; AFFECT001 closed by the serve.md doc
note). Remaining FAIL rows in the unscoped tool summary (ruff-check,
ruff-format, frob-cycle, gate:COV/DOC/DRIFT/etc.) are repo-wide counts per
the check's own gate:scope-note disclosure, not filtered to this ticket
(playbook section 6c) -- frob-cycle's 1 error is the still-open SCC
documented above, not a new regression.

### Changed
```
 docs/modules/serve.md              |   7 ++-
 docs/modules/stats.md              |   2 +-
 src/frob/app/stats_runner.py       |   5 +-
 src/frob/serve/_tools.py           |   4 +-
 src/frob/stats/__init__.py         |  21 +++++---
 tests/test_stats.py                |  39 +++++++++++++--
 tickets/T-2667/ticket.md | 100 +++++++++++++++++++++++++++++++++++++
 7 files changed, 165 insertions(+), 13 deletions(-)
```

### Evidence
- `tests/test_stats.py::test_collect_injected_queue_matches_direct_ticket_stats` (pytest node id, verified passing when recorded)
- `tests/test_stats.py::test_collect_with_no_queue_reports_empty_ticket_stats` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/app/fmt_runner.py, COV001@src/frob/gates/_refs_schema.py, COV001@src/frob/gates/_rule_id_scan.py, COV001@src/frob/strata/_multifile.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_milestone.py, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC006@tickets/T-2570/ticket.md, DOC008@docs/modules/gates.md, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DUP001@src/frob/stats/__init__.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/gates/_milestone.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, PRE001@tickets/T-2583, RENDER001@src/frob/release/_cli.py, SEC004@tests/test_tickets_organization.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
