## Done report

T-2606 implemented and unit-tested WAIVE009 (frob.gates._waive.waive009_violations)
but never wired it into `_assemble_gate_report`/`run_gates` -- it enforced
nothing through a real `frob check`. Wired it in alongside WAIVE006/007
(same dependency shape: snapshot waive edges + merged ticket queue only).

Proved the wiring end-to-end, not just at the unit level: added
TestWaive009Wiring to tests/test_waive_gate.py with two tests that go
through `run_gates` (not a direct call to `waive009_violations`) --
one plants an unresolvable promise and asserts WAIVE009 fires, the other
plants the same phrasing backed by a real resolvable ticket id and
asserts it stays silent. Split the repro test into its own commit first
(45ea5284a) to get a genuine FAILED_AT_PARENT verdict via
`frob ticket evidence --check-repro --base-ref 45ea5284a` before
re-applying the fix -- retroactive check-repro against a squashed
ticket's own already-landed history is not achievable (T-2025), so this
is the only way to get a real repro verdict pre-land.

Also manually verified through a real `frob check --only gates` pass in
this worktree (not pytest): planted a scratch symbol with an
unresolvable-promise waiver -- WAIVE009 fired; rewrote its reason to cite
a real resolvable ticket id (T-2639 itself) -- WAIVE009 stayed silent
(confirmed with FROB_NO_GATE_CACHE=1 to rule out a stale cached read).
Scratch file removed before committing; not part of the diff.

Removed the COV001 waiver T-2606 had left on `waive009_violations`
(its stated premise -- T-2639's own wiring+doc work not yet landed --
now resolves) and replaced it with a real `frob:doc` edge into the new
gates.md#rule-catalog row.

Added a WAIVE009 row to docs/modules/gates.md's rule catalog table,
matching the WAIVE006/007 rows' shape (severity, always-on, one-line
description, code pointer).

Scope note: docs/modules/gates.md and tests/test_waive_gate.py were
added to this ticket's scope mid-flight -- the former once T-2613's live
lease on it released (it was the plan's own stated blocker), the latter
to host the end-to-end wiring proof test.

### Changed
```
 docs/modules/gates.md      |  1 +
 src/frob/gates/__init__.py |  5 +++++
 src/frob/gates/_waive.py   | 17 +++++---------
 tests/test_waive_gate.py   | 55 ++++++++++++++++++++++++++++++++++++++++++++++
 tickets/T-2639/ticket.md   | 18 ++++++++++++++-
 5 files changed, 83 insertions(+), 13 deletions(-)
```

### Evidence
- `tests/test_waive_gate.py::TestWaive009Wiring::test_unresolvable_promise_fires_through_run_gates` (pytest node id, verified passing when recorded)
- `tests/test_waive_gate.py::TestWaive009Wiring::test_resolvable_promise_does_not_fire_through_run_gates` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@scripts/fleet_status.py, COV001@src/frob/app/fmt_runner.py, COV001@src/frob/gates/_refs_schema.py, COV001@src/frob/gates/_rule_id_scan.py, COV001@src/frob/strata/_multifile.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC001@docs/commands/release.md, DOC002@scripts/fleet_status.py, DOC002@src/frob/gates/_milestone.py, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC006@tickets/T-2570/ticket.md, DOC008@docs/modules/gates.md, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/gates/_milestone.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, PRE001@tickets/T-2639, RENDER001@src/frob/release/_cli.py, SEC004@tests/test_tickets_organization.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WAIVE006@src/frob/gates/__init__.py, WAIVE006@src/frob/gates/_coverage.py, WAIVE006@src/frob/gates/_decisions_compliance.py, WAIVE006@src/frob/gates/_doclink_docanchor.py, WAIVE006@src/frob/gates/_mutation_evidence.py, WAIVE006@src/frob/gates/_sys.py, WAIVE006@src/frob/gates/_tickets_gate.py, WAIVE006@src/frob/gates/_todo_fmt.py, WAIVE006@src/frob/tickets/_draft_finalize.py, WAIVE006@src/frob/tickets/_evidence.py, WAIVE006@src/frob/tickets/_models.py, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
