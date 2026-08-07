## Done report

REL37x CLOCK/ORDERING-ASSUMPTIONS obligation across distributed flows
(T-0657), mirroring _retry.py/REL22x's flow-scoped three-rule shape
(registered in _waive.py::MULTI_INSTANCE_WAIVER_FAMILIES, since a node
can originate several clock_dependent flows).

- New module src/frob/strata/_clock_ordering.py:
  - REL370 missing ordering strategy: a `clock_dependent` flow with no
    `ordering_strategy` attr.
  - REL371 unproven ordering strategy: declared but no bound endpoint's
    code has any real ordering-shaped token at all (proof-against-code,
    T-0331 PROVABILITY CONSTRAINT, T-0758 either-endpoint anchoring via
    `bound_endpoints`, same as REL222).
  - REL372 wall-clock-only discharge: declared, bound code exists, but
    the ONLY evidence is a bare wall-clock read (time.time()/
    datetime.now()-shaped) with no vector/logical-clock or sequence-
    number construct -- flagged distinctly from REL371's honest silence,
    since this is a modeler who declared the obligation and then
    re-implemented the exact clock-drift hazard it exists to catch.
- Registered REL370/REL371/REL372 in src/frob/strata/_waive.py::
  MULTI_INSTANCE_WAIVER_FAMILIES (in scope: src/frob/strata/**).
- Updated docs/strata/waive.md's sub-targets section to list the new
  REL370/371/372 multi-instance family (satisfies gate:AFFECT's
  AFFECT001 doc-drift requirement on MULTI_INSTANCE_WAIVER_FAMILIES).
- Wired __init__.py exports (CLOCK_ORDERING_RULES,
  REL_MISSING_ORDERING_STRATEGY, REL_UNPROVEN_ORDERING_STRATEGY,
  REL_WALL_CLOCK_ONLY, ClockOrderingReport, ClockOrderingViolation,
  check_clock_ordering_obligations).
- New docs/strata/reliability.md REL37x section.
- New tests/unit/strata/test_clock_ordering.py, 7 tests, all pass.

Filed: none (no out-of-scope findings; ticket was not pre-implemented).

Gates: frob check --ticket T-0657 clean across lint/static/gates-fast/
gates-native/gates-security (chunked --only loop). gate:AFFECT (AFFECT001)
fired once for the MULTI_INSTANCE_WAIVER_FAMILIES change with no matching
docs/strata/waive.md touch -- fixed by updating that doc section, then
re-swept clean. gate:PRE refreshed via `frob ticket sweep T-0657`.

DELETION-FILTER NOTE (section 9, same as T-0656's): `git diff main
--diff-filter=D --stat` shows tests/test_arch_near_duplicate_native.py
because main advanced past this worktree's base mid-session (T-0953
landed a new file after this batch started) -- not anything this ticket
touched or removed. Learned from the T-0656 round: attempting `git merge
main` mid-session here would risk losing uncommitted ticket state again
(a real incident this session: T-0655's close and T-0656's first
evidence/done-report pass were both silently reverted by a `git merge
--abort` after the land-owned-files pre-commit guard refused the merge
commit, T-0731) -- recovered by re-running `frob ticket close T-0655`/
`frob ticket evidence T-0656`/`done-report T-0656` and committing
immediately each time. For this ticket I did NOT attempt the merge at
all: nothing in this ticket's own diff deletes or reverts already-landed
work, and the coordinator's own land/merge onto current main will pick
up T-0953 via a normal 3-way merge with no special handling needed.

### Changed
```
 docs/strata/reliability.md                   | 282 ++++++++++++++++++
 docs/strata/threat.md                        |  11 +
 src/frob/strata/__init__.py                  |  56 ++++
 src/frob/strata/_delivery_semantics.py       | 343 ++++++++++++++++++++++
 src/frob/strata/_distributed_txn.py          | 320 ++++++++++++++++++++
 src/frob/strata/_shared_state.py             | 235 +++++++++++++++
 src/frob/strata/_sync_depth.py               | 277 ++++++++++++++++++
 tests/unit/strata/test_delivery_semantics.py | 175 +++++++++++
 tests/unit/strata/test_distributed_txn.py    | 193 +++++++++++++
 tests/unit/strata/test_shared_state.py       | 150 ++++++++++
 tests/unit/strata/test_sync_depth.py         | 110 +++++++
 tickets.md                                   | 418 ++++++++++++++++++++++++++-
 12 files changed, 2560 insertions(+), 10 deletions(-)
```

### Evidence
- `tests/unit/strata/test_clock_ordering.py::TestMissingOrderingStrategy::test_clock_dependent_flow_without_ordering_strategy_fires` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_clock_ordering.py::TestMissingOrderingStrategy::test_discharged_and_non_clock_dependent_flows_clean` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_clock_ordering.py::TestMissingOrderingStrategy::test_waiver_discharges_finding` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_clock_ordering.py::TestUnprovenOrderingStrategy::test_declared_with_no_code_evidence_fires` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_clock_ordering.py::TestUnprovenOrderingStrategy::test_declared_with_real_code_evidence_discharges` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_clock_ordering.py::TestUnprovenOrderingStrategy::test_declared_with_no_bound_code_is_uncheckable_not_a_violation` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_clock_ordering.py::TestWallClockOnly::test_bare_wall_clock_read_fires_rel372` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 7 passed (from 7 evidence id(s))
- gates: 0 error(s), 4235 warning(s), 219 waived
- error-findings: none (measured, zero errors)
