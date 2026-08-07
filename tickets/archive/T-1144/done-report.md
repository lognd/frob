## Done report

Investigation resolved the T-1124-filed residue: the two ToolResult-
returning abstraction-opportunity groups it named (and two more the
same class covers -- 4 groups, 24 members total measured project-wide)
are frob.process/frob.check's own check-stage-runner return-type
convention, not accidental duplication. `parse_junit_xml` sharing
`(str, str) -> ToolResult` with three trivial synthetic-result builders
purely because its `tool` parameter defaults confirms there is no one
coherent family to extract here beyond what T-1124 already extracted
(`_opt_in_deploy_stage_result`, `_missing_tool_result` forwarding to
`tool_unavailable_result`).

Generalized the exclusion mechanism (T-1141's `_is_gate_rule_builder_
family` for frob.gates's own `Violation` convention) with a mirrored
`_GATE_RULE_BUILDER_RETURN_TYPES`-shaped
`_TOOL_RESULT_BUILDER_RETURN_TYPES`/`_is_tool_result_builder_family` in
src/frob/arch/_python.py, wired into `_check_abstraction_opportunities`
alongside the other three exclusions. Structural (return-type-based):
`ret in {"ToolResult", "ToolResult | None"}`.

The fix lives beside its T-1141 precedent in src/frob/arch/_python.py,
outside T-1144's originally-declared scope (src/frob/check/**,
src/frob/process/parsers/**, docs/modules/arch.md) -- expanded scope
(reasoned, `frob ticket scope T-1144 --add`) to include
src/frob/arch/_python.py and tests/unit/test_arch.py (the new test's
home) after confirming no real extraction was warranted in
check/**/process/parsers/**.

Measured before/after project-wide (src/frob): 68 -> 64
abstraction-opportunity findings (post-T-1141's own 25 -> 12 gates-only
drop already landed) -- exactly the 4 ToolResult-shaped groups
dropped, confirmed by diffing the printed finding list; the remaining
64 have no "ToolResult" in their message.

Added tests/unit/test_arch.py::TestToolResultBuilderExclusion (3
cases, mirroring TestGateRuleBuilderExclusion's structure): a
ToolResult-returning 3-member group is suppressed; a same-shaped
non-ToolResult-returning group still flags; the return-type-membership
predicate matches both declared shapes and rejects a non-member type
and the sibling gate-family's Violation type.

Updated docs/modules/arch.md with a new subsection documenting all
three convention exclusions (check-registry/gate-rule-builder/
tool-result-builder) together, and corrected a stale line in the T-0370
section that claimed the `(Path) -> tuple[Violation, ...]` gate group
"still flags in full" (no longer true after T-1141).

Verification: ruff check clean (both `ruff` and `uv run ruff`) on
src/frob/arch/_python.py and tests/unit/test_arch.py. Full
tests/unit/test_arch.py run: 293 passed (no regressions).
frob check --ticket T-1144 --only docanchor --only doclink: clean (0
errors). frob check --ticket T-1144 --only coverage: no new COV002/
COV006 findings tied to this change (same 2 pre-existing waived COV006
entries as before, unrelated to _tool_result_builder).

Filed: none.

### Changed
```
 docs/modules/arch.md     | 51 +++++++++++++++++++++++++++++++--
 src/frob/arch/_python.py | 43 ++++++++++++++++++++++++++--
 tests/unit/test_arch.py  | 74 ++++++++++++++++++++++++++++++++++++++++++++++++
 tickets.md               | 62 ++++++++++++++++++++++++++++++++++++++--
 4 files changed, 224 insertions(+), 6 deletions(-)
```

### Evidence
- `tests/unit/test_arch.py::TestToolResultBuilderExclusion::test_toolresult_returning_group_not_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestToolResultBuilderExclusion::test_non_toolresult_returning_group_still_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestToolResultBuilderExclusion::test_return_type_membership_matches_both_shapes` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 27 error(s), 1040 warning(s), 431 waived
- error-findings: ARCH001@src/frob/app/ticket_runner/_close_cmd.py, ARCH001@src/frob/doctor.py, ARCH001@src/frob/tickets/__init__.py, COV001@src/frob/gates/_tracked_files.py, COV003@tickets/T-0138, COV003@tickets/T-0226, COV003@tickets/T-0629, COV003@tickets/T-0700, COV003@tickets/T-0702, E501@/home/logan/projects/frob/.claude/worktrees/w18-gates3/src/frob/doctor.py:243, E501@/home/logan/projects/frob/.claude/worktrees/w18-gates3/src/frob/vet/_capability.py:5338, E501@/home/logan/projects/frob/.claude/worktrees/w18-gates3/src/frob/vet/_supplychain.py:154, E501@/home/logan/projects/frob/.claude/worktrees/w18-gates3/src/frob/vet/_supplychain.py:168, E501@/home/logan/projects/frob/.claude/worktrees/w18-gates3/src/frob/vet/_supplychain.py:209, E501@/home/logan/projects/frob/.claude/worktrees/w18-gates3/src/frob/vet/_supplychain.py:267, E501@/home/logan/projects/frob/.claude/worktrees/w18-gates3/src/frob/vet/_supplychain.py:295, F401@/home/logan/projects/frob/.claude/worktrees/w18-gates3/src/frob/tickets/__init__.py:111, F401@/home/logan/projects/frob/.claude/worktrees/w18-gates3/src/frob/tickets/__init__.py:22, F401@/home/logan/projects/frob/.claude/worktrees/w18-gates3/src/frob/tickets/__init__.py:23, F401@/home/logan/projects/frob/.claude/worktrees/w18-gates3/src/frob/tickets/__init__.py:35, F401@/home/logan/projects/frob/.claude/worktrees/w18-gates3/src/frob/tickets/__init__.py:46, INV006@src/frob/app/stats_runner.py, INV006@src/frob/gates/_tickets_gate.py, PII012@src/frob/gates/_tickets_gate.py, PII012@tests/system/test_cli_doctor.py, PRE001@tickets/T-1144, SELFAUDIT001@design
