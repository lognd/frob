## Done report

T-1662's own directive #4: a new gate rule constructed from raw text
without a symref/AST binding should itself be a finding. Per the
coordinator's decision, T-1662 stays open until this ticket lands -- this
IS the epic's actual deliverable; the prior 7 instance-fixes were cleanup.

Changed:
- src/frob/gates/_lexical_selfcheck.py (new): `lexical_selfcheck_gate`,
  AST-based, per-function detection (re.search/match/fullmatch/findall/
  finditer -- direct `re.` or a module `_FOO_RE`/`_FOO_PATTERN` compiled
  pattern -- plus a symref-less `Violation(...)` construction in the SAME
  function), `_ALLOWLIST` mirroring docs/design/gate-semantics-
  classification.md's class-(b) table.
- src/frob/gates/__init__.py: wired lexcheck into _ALL_GATES,
  _CANONICAL_GATE_ORDER, the CPU-bound _ProcessJob pool subset list, the
  _ProcessJob dispatch dict, and __all__.
- src/frob/gates/_waive.py: registered LEXCHECK001 in _KNOWN_GATE_RULES.
- src/frob/check/__init__.py: registered "lexcheck" in _STAGE_GROUPS's
  gates-fast set (same "omission -> unreachable via --only <group>" bug
  class already fixed once for ffi_boundary/suppress -- avoided repeating
  it here).
- src/frob/gates/_wire.py: `_wire001_cli_dest_violations` (a genuine,
  self-admitted (c) candidate the new gate found) waived in-file with
  `follow_up="T-2354"` rather than silently allowlisted.
- docs/modules/gates.md: rule-catalog row + full `## LEXCHECK001 (T-2344)`
  section, `_KNOWN_GATE_RULES` frob:enumerates literal updated.
- tests/unit/gates/test_lexical_selfcheck.py (new): 5 tests -- a
  synthetic REF001-pre-fix-shaped fixture IS flagged (proves this is not
  a check that always finds nothing), an allowlisted pair is silent, a
  symref-carrying function with incidental regex is silent, non-gates
  code is never scanned, and the real repo's own src/frob/gates/** scans
  to exactly the one known waived exception.

Filed: T-2354 (WIRE001 case 3's own text-membership tradeoff, a real (c)
candidate this new gate surfaced during development -- not silently
allowlisted, waived in-file citing the ticket per this repo's own WIRE001
convention).

Disclosed limitation (documented in the module docstring, same posture as
RENDER001's shadowed-print gap): detection is per-FUNCTION, so a module
that splits the regex decision and the Violation construction across two
different functions (the render_lint/secrets pattern, both already
allowlisted for other reasons) is not caught by v1. Raising this to a
whole-module call-graph trace is real future work, not attempted here.

### Evidence
- tests/unit/gates/test_lexical_selfcheck.py::TestLexcheck001::test_new_lexical_decider_is_flagged
- tests/unit/gates/test_lexical_selfcheck.py::TestLexcheck001::test_allowlisted_function_is_silent
- tests/unit/gates/test_lexical_selfcheck.py::TestLexcheck001::test_semantic_function_with_incidental_regex_is_silent
- tests/unit/gates/test_lexical_selfcheck.py::TestLexcheck001::test_non_gate_code_never_scanned
- tests/unit/gates/test_lexical_selfcheck.py::TestLexcheck001::test_every_known_gates_module_module_stays_clean

Full file run: `uv run pytest tests/unit/gates/test_lexical_selfcheck.py -p no:cacheprovider -q`
-> SUITE-RESULT: exitstatus=0 collected=5 failed=0

### Gates
`uv run frob check --ticket T-2344 --only gates-fast` -> `gate:LEXCHECK`
0 errors, 0 warnings, 1 waived (the T-2354-cited site). `--only gates-
native --only gates-security` show no unwaived findings in any file this
ticket touched (checked by grep against every touched path). Repo-wide
gate-summary totals (88/39 errors respectively) are this repo's known
pre-existing floor across unrelated files, not attributable here.

### Changed
```
 tickets/T-2344/ticket.md | 36 +++++++++++++++++++++++++++++++++++-
 1 file changed, 35 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/gates/test_lexical_selfcheck.py::TestLexcheck001::test_new_lexical_decider_is_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_lexical_selfcheck.py::TestLexcheck001::test_allowlisted_function_is_silent` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_lexical_selfcheck.py::TestLexcheck001::test_semantic_function_with_incidental_regex_is_silent` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_lexical_selfcheck.py::TestLexcheck001::test_non_gate_code_never_scanned` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_lexical_selfcheck.py::TestLexcheck001::test_every_known_gates_module_module_stays_clean` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH103@scripts/fleet_status.py, ARCH103@src/frob/release/_cli.py, COV001@scripts/fleet_status.py, COV001@src/frob/tickets/_land_git_ops.py, COV001@src/frob/tickets/_leases.py, COV001@src/frob/verify/_drain.py, COV001@src/frob/verify/_quarantine.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, DOC001@docs/commands/release.md, DOC002@scripts/fleet_status.py, DOC002@src/frob/app/verify_runner.py, DOC002@src/frob/verify/_drain.py, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DOC011@docs/modules/gates.md, DUP001@tests/unit/gates/test_lexical_selfcheck.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2344/src/frob/verify/_worker.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF004@src/frob/app/ticket_runner/_new.py, PRE001@tickets/T-2344, RENDER001@src/frob/release/_cli.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/tickets/_leases.py, TICK003@tickets.md, TICK004@tickets.md, WIRE003@docs/modules/cli.md
