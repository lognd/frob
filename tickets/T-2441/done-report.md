## Done report

Changed: src/frob/gates/_waive.py (_KNOWN_GATE_RULES: registered bare
"PORT001" alongside the pre-existing PORT001-PATH/PORT001-IDENT pair)

Evidence: tests/gates/test_rule_id_scan_branches.py::TestFindUnregisteredRuleIds::test_real_repo_registry_is_complete
(the repo-wide completeness check this fix restores against the real
tree). Also verified via a direct find_unregistered_rule_ids(root=.)
call: {} (empty) after the change.

Also, per the coordinator's own follow-up request: ran
find_unregistered_rule_ids across every live worktree in the fleet to
check for other unregistered rule ids beyond PORT001. Found one more:
CLAUDE001 at src/frob/app/check_runner.py:481, in the live
rule-bookkeeping worktree (owned by in-progress T-1686/T-1970, not
touched here -- filed as T-2447 instead). Also filed T-2448: a proposal
to wire find_unregistered_rule_ids into `frob check`/`frob verify` as a
standing repo-wide gate, since right now it is only ever consulted
scope-limited at one ticket's own close/land time (T-1956's deliberate
design), so a gap in an unlanded branch nobody is currently landing is
invisible until someone tries -- exactly the "detected but not
surfaced" shape T-2387 named. Left the wiring-point decision to
whoever picks up T-2448 rather than deciding it inline here.

Filed: T-2447 (register CLAUDE001), T-2448 (gate-ify
find_unregistered_rule_ids)

Gates: tests/test_gates.py -k waive 60/60 pass;
tests/gates/test_rule_id_scan_branches.py 14/14 pass, both locally.

### Changed
(no changed files detected)

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@.claude/hooks/root-write-guard.py, ARCH103@src/frob/release/_cli.py, COV001@src/frob/gates/_refs_schema.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/gates/_fix_engine.py, DRIFT002@docs/modules/arch.md, DRIFT002@docs/modules/vet.md, E501@/home/logan/projects/frob/src/frob/app/ticket_runner/_mutate.py, E501@/home/logan/projects/frob/src/frob/app/ticket_runner/_query.py, E501@/home/logan/projects/frob/src/frob/gates/__init__.py, E501@/home/logan/projects/frob/src/frob/verify/_worker.py, F401@/home/logan/projects/frob/src/frob/vet/_capability.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, RENDER001@src/frob/release/_cli.py, SEC110@.claude/hooks/root-write-guard.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE003@docs/modules/cli.md
