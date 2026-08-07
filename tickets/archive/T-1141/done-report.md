## Done report

Generalized T-1112's check_*-registry exclusion pattern to also exempt
frob.gates's own gate/rule-builder convention: added
`_GATE_RULE_BUILDER_RETURN_TYPES` (`Violation`, `list[Violation]`,
`tuple[Violation, ...]`) and `_is_gate_rule_builder_family(ret)` in
src/frob/arch/_python.py, wired into `_check_abstraction_opportunities`
alongside `_is_dispatch_family`/`_is_language_parity_family`/
`_is_check_registry_family`. Structural (return-type-based), not
name-based, since gate/rule-builder function names in frob.gates do
not share one fixed prefix/suffix the way check_*/run_*_checks do --
`Violation` is frob.gates's own domain type, so any function returning
one of these three shapes participates in the same gate contract by
construction.

Measured before/after over src/frob/gates (post-T-1140's TICK00x
split): 25 -> 12 abstraction-opportunity findings. The 13 groups
dropped are exactly the ones the ticket named -- all Violation-return-
type groups ((Path, GraphSnapshot) -> tuple[Violation, ...] 17
members, (Path) -> tuple[Violation, ...] 19 members, (GraphSnapshot) ->
tuple[Violation, ...] 11 members, (GraphSnapshot) -> list[Violation] 4
members, (str, str) -> Violation 5 members, (str, int, str) ->
Violation 8 members, (str) -> Violation 3 members, plus (str, str) ->
list[Violation] 4 members) -- confirmed by diffing the printed
group list before/after this change (script run via
frob.arch.analyze_project(Path("src/frob/gates"))). The remaining 12
findings are unrelated to this exclusion (utility-signature
collisions: load_baseline/load_coverage_lock/load_stamp,
_debt_edges/_deprecated_edges/_establishes_claims/_waive_edges
returning tuple[Edge, ...] -- deliberately NOT exempted, since Edge is
not part of the gate/rule-builder Violation-return convention this
ticket scopes to -- ast-node predicate/tracked-file helper groups,
etc.) and were present identically before this change.

Project-wide (src/frob) abstraction-opportunity count after this
change: 68 findings (measured directly, not a claimed estimate).

Added tests/unit/test_arch.py::TestGateRuleBuilderExclusion (3 cases:
a Violation-returning 3-member group is suppressed; a same-shaped
non-Violation-returning group still flags; the return-type-membership
predicate itself matches the three declared shapes and rejects a
non-member type and the sibling Edge-returning shape), mirroring
TestCheckRegistryExclusion's structure.

Verification: ruff check clean (both `ruff` and `uv run ruff`) on
src/frob/arch/_python.py and tests/unit/test_arch.py. Full
tests/unit/test_arch.py run: 290 passed (no regressions).

Filed: none.

### Changed
```
 tickets.md | 3 +--
 1 file changed, 1 insertion(+), 2 deletions(-)
```

### Evidence
- `tests/unit/test_arch.py::TestGateRuleBuilderExclusion::test_violation_returning_group_not_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestGateRuleBuilderExclusion::test_non_violation_returning_group_still_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestGateRuleBuilderExclusion::test_return_type_membership_matches_all_three_shapes` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 23 error(s), 777 warning(s), 431 waived
- error-findings: ARCH001@src/frob/app/ticket_runner/_close_cmd.py, ARCH001@src/frob/doctor.py, ARCH001@src/frob/tickets/__init__.py, COV001@src/frob/gates/_tracked_files.py, COV003@tickets/T-0138, COV003@tickets/T-0226, COV003@tickets/T-0629, COV003@tickets/T-0700, COV003@tickets/T-0702, E501@/home/logan/projects/frob/.claude/worktrees/w18-gates3/src/frob/doctor.py:243, E501@/home/logan/projects/frob/.claude/worktrees/w18-gates3/src/frob/vet/_capability.py:5338, E501@/home/logan/projects/frob/.claude/worktrees/w18-gates3/src/frob/vet/_supplychain.py:154, E501@/home/logan/projects/frob/.claude/worktrees/w18-gates3/src/frob/vet/_supplychain.py:168, E501@/home/logan/projects/frob/.claude/worktrees/w18-gates3/src/frob/vet/_supplychain.py:209, E501@/home/logan/projects/frob/.claude/worktrees/w18-gates3/src/frob/vet/_supplychain.py:267, E501@/home/logan/projects/frob/.claude/worktrees/w18-gates3/src/frob/vet/_supplychain.py:295, INV006@src/frob/app/stats_runner.py, INV006@src/frob/gates/_tickets_gate.py, PII012@src/frob/gates/_tickets_gate.py, PII012@tests/system/test_cli_doctor.py, PRE001@tickets/T-1141, REG002@docs/design/registry/check-coverage.yaml, SELFAUDIT001@design
