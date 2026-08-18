## Done report

`scan_candidate_rule_id_literals` skips `#`-prefixed comment lines but
never excludes triple-quoted module docstring prose. `_gates_schema.py`'s
own module docstring quoted `"COV0011"` (a deliberate misspelling of
`COV001`, used as a worked example of exactly the malformed-key bug this
gate exists to catch) inside plain double quotes, which the scanner's
rule-id-shaped-literal regex matches regardless of surrounding context --
producing a false-positive unregistered-rule-id finding.

Per the ticket's own guidance ("prefer the docstring reword if it's a
one-off... the scanner fix if this pattern recurs") and this ticket's
declared scope (`src/frob/gates/_gates_schema.py` only -- the scanner
itself lives in `frob.gates._rule_id_scan`, a different file, out of
scope here): reworded the docstring to reference the misspelling via a
backtick-quoted, non-double-quoted literal (`` `COV0011` ``) instead of
`"COV0011"`, matching this file's own existing style for real rule ids
elsewhere in the same docstring (e.g. `` `COV001 = "error"` ``). No
double-quoted rule-id-shaped literal remains anywhere in the file except
the three genuine `rule="GATESSCHEMA001"` construction sites.

Changed:
- `src/frob/gates/_gates_schema.py` (module docstring wording only, no
  code change)

Evidence:
- `tests/gates/test_rule_id_scan_branches.py::TestFindUnregisteredRuleIds::test_real_repo_registry_is_complete`
  (the exact repo-wide completeness test the ticket cites as currently
  failing on main; ran the full `tests/gates/test_rule_id_scan_branches.py`
  file after the fix -- 18/18 passed, 0 failed)

Filed: none (the fix stayed entirely within this ticket's declared
scope; no other-scope work discovered)

Gates: `frob check --ticket T-2458` clean on
`src/frob/gates/_gates_schema.py` (0 errors attributable to this diff).

### Changed
```
 src/frob/gates/_gates_schema.py | 5 +++--
 tickets/T-2458/ticket.md        | 6 +++++-
 2 files changed, 8 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/gates/test_rule_id_scan_branches.py::TestFindUnregisteredRuleIds::test_real_repo_registry_is_complete` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@.claude/hooks/root-write-guard.py, ARCH103@src/frob/release/_cli.py, COV001@src/frob/gates/_port_selfcheck.py, COV001@src/frob/gates/_refs_schema.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_port_selfcheck.py, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC007@tests/test_gates.py, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, DRIFT002@tests/test_gates.py, E501@/home/logan/projects/frob/.claude/worktrees/gates-schema-cov0011/src/frob/app/ticket_runner/_query.py, E501@/home/logan/projects/frob/.claude/worktrees/gates-schema-cov0011/src/frob/gates/__init__.py, E501@/home/logan/projects/frob/.claude/worktrees/gates-schema-cov0011/src/frob/gates/_dup_graph_schema.py, E501@/home/logan/projects/frob/.claude/worktrees/gates-schema-cov0011/src/frob/verify/_worker.py, F401@/home/logan/projects/frob/.claude/worktrees/gates-schema-cov0011/src/frob/vet/_capability.py, LEXCHECK001@src/frob/vet/_supplychain.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PRE001@tickets/T-2458, RENDER001@src/frob/release/_cli.py, SEC110@.claude/hooks/root-write-guard.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE003@docs/modules/cli.md, missing-argument@tests/unit/test_ticket_runner_land_release.py
