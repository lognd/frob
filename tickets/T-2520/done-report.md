## Done report

T-2520 was filed by T-1684's post-land sweep against T-2507's commit, claiming
1 new (rule, file) identity: WIRE001 src/frob/graph/summary.py. The ticket's
own body already disclosed an independent re-measurement finding 0 actual
findings, and attribution as UNATTRIBUTED (no candidate commits).

Re-verified today: unscoped frob check --json (FROB_ALLOW_FULL_CHECK=1,
gate-summary present, gate:WIRE family ran as part of a 49-result full pass)
shows 0 WIRE001 diagnostics anywhere in the current tree, and specifically
none against src/frob/graph/summary.py. This matches the documented
stale-baseline-reports-pre-existing-as-new false-positive class that this
ticket class is known to produce.

No code change made -- there is no live finding to fix. Closed via
frob ticket close --no-behavior-change (T-2393's front door for exactly
this shape: a sweep-filed ticket with no reproducible behavioral delta).

### Evidence
tests/unit/gates/test_wire001_cli_dest_semantic.py::TestWire001CliDestViolations
(3 node ids) -- WIRE001's own gate test suite, still green, cited to show
the gate itself is intact and the absence of a finding is not a broken
detector.

### Changed
```
 rapid-debt.jsonl         |  2 ++
 tickets/T-2520/ticket.md | 30 ++++++++++++++++++++++++++++--
 2 files changed, 30 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/unit/gates/test_wire001_cli_dest_semantic.py::TestWire001CliDestViolations::test_dest_wired_only_through_tuple_structure_is_not_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_wire001_cli_dest_semantic.py::TestWire001CliDestViolations::test_dest_mentioned_only_in_a_comment_is_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_wire001_cli_dest_semantic.py::TestWire001CliDestViolations::test_dest_not_wired_at_all_is_flagged` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@src/frob/release/_cli.py, COV001@src/frob/app/fmt_runner.py, COV001@src/frob/gates/_refs_schema.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, E501@/home/logan/projects/frob/.claude/worktrees/t-2520/scripts/fleet_status.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2520/src/frob/graph/summary.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2520/src/frob/testing/_collect_kotlin.py, F401@/home/logan/projects/frob/.claude/worktrees/t-2520/tests/unit/test_ticket_runner_repro_merge_base.py, F811@/home/logan/projects/frob/.claude/worktrees/t-2520/tests/unit/test_app_runners_json_guard_t2492.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, RENDER001@src/frob/release/_cli.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
