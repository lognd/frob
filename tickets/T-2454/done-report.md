## Done report

_KNOWN_GATE_RULES (src/frob/gates/_waive.py) is compared against on
THREE independent gate-blocking call sites, all through
find_unregistered_rule_ids or a direct known_gate_rule_ids() read:
GATERULE001 (standing, T-2448), the T-0756/T-1956 close/land preflight
(unregistered_rule_ids_in_scope), and -- the one that actually
serialized the four deadlocked tickets, since it is DIFF-scoped and
fires the instant a ticket's own diff constructs a new rule="..."
literal -- WIRE001 case 2 (_wire001_rule_id_violations, T-1421's BUG002
shape). All three compared only against the hand-maintained literal.

Fix: find_unregistered_rule_ids and _wire001_rule_id_violations now
union `known` with a fresh generated_gate_rule_ids(root) scan --
already-existing, tested T-1010 machinery that reads live rule="..."/
rule=CONST_NAME constructions under SCANNED_BASES (src/frob/gates,
src/frob/strata). A ticket adding a standard-shape new gate rule in
its own module (the shape all four deadlocked tickets used --
PORT001/GATESSCHEMA001/TESTRUNNERSCHEMA001/DUPSCHEMA001/GRAPHSCHEMA001)
now passes all three checks without touching _waive.py at all, so no
scope-lease collision on that file for this class of work.

Must-still-refuse preserved: the disclosed residual gap
(_rule_id_scan's own module docstring -- bare positional args,
dict-literal values, ids outside SCANNED_BASES) is NOT covered by
generated_gate_rule_ids, so those shapes still require the hand
literal exactly as before. Verified with two paired tests per call
site: a standard-shape id recognized with known=frozenset() (nothing
hand-registered), and a disclosed-gap-shape id still reported missing
with the same empty known=.

Auditability (acceptance[2]): _KNOWN_GATE_RULES stays hand-maintained
(T-1010's own design choice, preserved -- frob.tickets.
_new_gate_rule_acceptance still scrapes its SOURCE TEXT and that
consumer is untouched). `frob registry audit --sync-gate-rules` now
ALSO logs the full live registered set (hand literal | generated scan)
as the one-place, generated answer to "what is the complete list of
registered rule ids" -- documented in
docs/design/registry/EXHAUSTIVENESS-GATE.md#reg010-gate-rule-staleness-t-0560.

Found and filed separately (not fixed here, out of scope): T-2458
(already filed and being worked by another agent) -- a pre-existing
false positive in scan_candidate_rule_id_literals against
src/frob/gates/_gates_schema.py's own docstring prose (a deliberately
misspelled "COV0011" example), confirmed failing on main independent
of this ticket's diff.

AFFECT001 on wire_gate (docs/modules/gates.md) is waived: that doc is
under a concurrent T-2466 lease this ticket cannot take, and the
change is purely internal (the documented WIRE001 case 2 behavior is
unchanged from a caller's perspective) -- same T-1371/T-1372 disclosed-
gap precedent this file already carries. AFFECT001 on registry_runner.
run's docs/modules/app.md and docs/guides/exhaustive-research.md
references is also waived (unrelated sections, no content change
needed); the one doc genuinely describing this change
(EXHAUSTIVENESS-GATE.md#reg010) IS updated in this same diff.

### Changed
```
 tickets/T-2454/ticket.md | 96 ++++++++++++++++++++++++++++++++++++++++++++++--
 1 file changed, 92 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/gates/test_rule_id_scan_branches.py::TestFindUnregisteredRuleIds::test_new_standard_shape_rule_recognized_without_hand_registration` (pytest node id, verified passing when recorded)
- `tests/gates/test_rule_id_scan_branches.py::TestFindUnregisteredRuleIds::test_disclosed_gap_shape_still_requires_hand_registration` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestWire001RuleIdViolationsUnion::test_standard_shape_new_rule_not_flagged_without_hand_registration` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestWire001RuleIdViolationsUnion::test_shape_outside_scanned_bases_still_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_t0875_leaf_collision.py::TestRegistryRunnerRun::test_sync_gate_rules_logs_the_full_generated_rule_id_set` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@.claude/hooks/root-write-guard.py, ARCH103@src/frob/release/_cli.py, COV001@src/frob/gates/_port_selfcheck.py, COV001@src/frob/gates/_refs_schema.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_port_selfcheck.py, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC007@tests/test_gates.py, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, DRIFT002@tests/test_gates.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2454/src/frob/app/ticket_runner/_query.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2454/src/frob/gates/__init__.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2454/src/frob/gates/_dup_graph_schema.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2454/src/frob/verify/_worker.py, F401@/home/logan/projects/frob/.claude/worktrees/t-2454/src/frob/vet/_capability.py, GATERULE001@src/frob/gates/_gates_schema.py, LEXCHECK001@src/frob/vet/_supplychain.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PRE001@tickets/T-2454, RENDER001@src/frob/release/_cli.py, SEC110@.claude/hooks/root-write-guard.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE003@docs/modules/cli.md, missing-argument@tests/unit/test_ticket_runner_land_release.py
