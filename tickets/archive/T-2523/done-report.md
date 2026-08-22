## Done report

Changed:
- src/frob/strata/_effects.py::check_ambient_capability_reasons (now
  labels each finding with the enclosing node id) + `_NODE_HEADER_RE`
  (new) + `AmbientCapabilityReasonViolation.node` field (new)
- src/frob/gates/_sys_selfaudit.py::_selfaudit_violations -- wires
  check_ambient_capability_reasons in as SYS112, same pattern T-1761/
  T-1977 used for SYS109/SYS111
- src/frob/gates/_waive.py::_KNOWN_GATE_RULES -- SYS112 entry
- docs/modules/gates.md -- SYS112 in the frob:enumerates rule list + a
  descriptive section next to SYS111's fix-handler section
- design/frob.strata -- backfilled `because` reasons on all 27
  pre-existing ambient grants (checker, registry_model, fleet, mutate,
  refactor, natives, serve, deploy, scripts_ops, claude_hooks,
  strata_core_native, frob_core_native)
- tests/unit/strata/test_effects.py -- node-label coverage

Scope widened beyond the ticket's declared
['src/frob/gates/__init__.py', 'design/frob.strata'] to actually wire
the check (mirroring T-2503's own precedent of narrow, reasoned
additions rather than forcing the literal scope or silently expanding
it): src/frob/gates/_sys_selfaudit.py (the ONLY place SYS109/SYS111's
own precedent wires a self-audit sub-check), src/frob/gates/_waive.py
(SYS112 must be in _KNOWN_GATE_RULES or GATERULE001 flags it),
docs/modules/gates.md, src/frob/strata/_effects.py (the ticket's own
new tests import from it directly), and
tests/unit/strata/test_effects.py (node-label test coverage).
docs/strata/surface.md was DELIBERATELY NOT touched -- T-2502 holds a
live cross-worktree lease on it; documented SYS112 in
docs/modules/gates.md instead.

Backfill decision: all 27 pre-existing ambient declarations were judged
to legitimately deserve ambient status (each node's own glob is small
and single-purpose -- e.g. `checker`'s `src/frob/check/**`,
`strata_core_native`'s `strata-core/src/**` which IS the FFI boundary)
-- NONE were converted to enumerated via-lists. Each reason states WHY
the capability is expected across the whole node, not what the grant
does (e.g. "this whole node's code glob IS the PyO3 FFI boundary
strata_core implements -- there is no non-FFI file to scope away from",
not "ffi capability for native code").

Evidence:
- tests/unit/strata/test_effects.py::TestAmbientCapabilityReason::test_missing_reason_is_flagged
- tests/unit/strata/test_effects.py::TestAmbientCapabilityReason::test_node_label_resolves_the_nearest_preceding_header
- Full file run: tests/unit/strata/test_effects.py -q -> 56 collected, 0 failed
- tests/test_gates.py -k "SelfAudit or SysGate" -q -> 31 collected, 0 failed (unaffected by the new sub-family)

POSITIVE CONTROLS, both directions, measured directly against the real
design/frob.strata via `frob check --ticket T-2523 --only sys`:
- wired-but-clean: after the backfill, SYS112 count = 0 (all 27 + T-2503's
  own 3 = 30 ambient grants carry a reason).
- fires when it should: temporarily stripped the `because` comment from
  strata_core_native's `ffi` grant -> `frob check --only sys` produced
  exactly one SYS112 finding naming that node/atom/file/line; restored
  the file, re-ran, back to 0. (Not committed -- a scratch/restore
  cycle, not part of the landed diff.)
- enumerated grants never required a reason: unaffected by this change
  (`_AMBIENT_MAY_RE` structurally cannot match a via-populated line,
  T-2503's own design) -- reconfirmed by
  TestAmbientCapabilityReason::test_enumerated_grant_needs_no_reason,
  already in the suite.

Filed: none (no out-of-scope defects found during backfill).

Gates: `frob check --ticket T-2523 --only scope --only lexcheck --only
capability_conformance` clean (0 errors; SCOPE002 warnings are
pre-existing repo-wide design/frob.strata doc-closure noise, same shape
as T-2503's). `frob check --ticket T-2523 --only sys` shows only
pre-existing SYS107/SYS111 findings unrelated to this change (other
in-flight tickets' via-list growth) -- 0 SYS112 findings.

### Changed
```
 design/frob.strata                | 54 +++++++++++++++++++--------------------
 docs/modules/gates.md             | 23 ++++++++++++++++-
 src/frob/gates/_sys_selfaudit.py  | 32 +++++++++++++++++++++++
 src/frob/gates/_waive.py          |  7 +++++
 src/frob/strata/_effects.py       | 28 ++++++++++++++++++--
 tests/unit/strata/test_effects.py | 25 ++++++++++++++++++
 tickets/T-2523/ticket.md          | 47 +++++++++++++++++++++++++++++++++-
 7 files changed, 185 insertions(+), 31 deletions(-)
```

### Evidence
- `tests/unit/strata/test_effects.py::TestAmbientCapabilityReason::test_missing_reason_is_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_effects.py::TestAmbientCapabilityReason::test_node_label_resolves_the_nearest_preceding_header` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_effects.py::TestAmbientCapabilityReason::test_reason_present_is_silent` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_effects.py::TestAmbientCapabilityReason::test_enumerated_grant_needs_no_reason` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: AFFECT001@src/frob/strata/_effects.py, ARCH103@src/frob/release/_cli.py, COV001@src/frob/app/fmt_runner.py, COV001@src/frob/gates/_refs_schema.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, E501@/home/logan/projects/frob/.claude/worktrees/t-2523/scripts/fleet_status.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2523/src/frob/graph/summary.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2523/src/frob/testing/_collect_kotlin.py, F401@/home/logan/projects/frob/.claude/worktrees/t-2523/tests/unit/test_ticket_runner_repro_merge_base.py, F811@/home/logan/projects/frob/.claude/worktrees/t-2523/tests/unit/test_app_runners_json_guard_t2492.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, PRE001@tickets/T-2523, RENDER001@src/frob/release/_cli.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
