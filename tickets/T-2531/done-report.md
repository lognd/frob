## Done report

Fixed the 4 confirmed-live findings split off T-2526: E501 in
scripts/fleet_status.py (3 sites: 2 over-long def signatures, 1 over-long
call-arg line), E501 in src/frob/graph/summary.py (2 sites: an over-long
ternary assignment, an over-long def signature), E501 in
src/frob/testing/_collect_kotlin.py (2 sites: over-long _log.warning
calls), and F401 in tests/unit/test_ticket_runner_repro_merge_base.py
(unused typani.Ok import, confirmed unused -- no other reference in the
file).

All wraps are mechanical (parenthesized multi-line signatures/calls,
ruff format applied after hand-wrapping to normalize style); no logic
changed. ruff check and ruff format --check are both clean on all 4
touched files. Closed via --no-behavior-change (T-2393): this is a pure
formatting/dead-import fix with no behavioral delta to reproduce.

### Evidence
tests/unit/test_ticket_runner_repro_merge_base.py::TestWarnIfBaseRefNotHonouredExactly
(2 node ids) -- the test file whose unused import was removed; both
still pass, confirming the removal did not break anything.

### Changed
```
 scripts/fleet_status.py                           | 14 +++++++++++---
 src/frob/graph/summary.py                         | 17 ++++++++++-------
 src/frob/testing/_collect_kotlin.py               |  8 ++++++--
 tests/unit/test_ticket_runner_repro_merge_base.py | 11 ++++++++---
 tickets/T-2531/ticket.md                          | 19 ++++++++++++++++++-
 5 files changed, 53 insertions(+), 16 deletions(-)
```

### Evidence
- `tests/unit/test_ticket_runner_repro_merge_base.py::TestWarnIfBaseRefNotHonouredExactly::test_no_warning_when_base_ref_already_matches` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_repro_merge_base.py::TestWarnIfBaseRefNotHonouredExactly::test_warns_when_base_ref_is_not_an_ancestor` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: AFFECT001@scripts/fleet_status.py, AFFECT001@src/frob/graph/summary.py, ARCH103@src/frob/release/_cli.py, COV001@src/frob/app/fmt_runner.py, COV001@src/frob/gates/_refs_schema.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2531/src/frob/app/ticket_runner/_verify.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, RENDER001@src/frob/release/_cli.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
