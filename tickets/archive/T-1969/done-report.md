## Done report

Added "CLAUDE001" to _KNOWN_GATE_RULES (src/frob/gates/_waive.py), the
one hand-edit this ticket required.

Plan item 2 (document CLAUDE001 in docs/modules/gates.md): confirmed the
DEPLOY001-003/BUDGET001/CHECK001 precedent first, per the ticket's own
instruction to check before assuming a section is needed -- none of
those `code="..."` (outside SCANNED_BASES) rule ids has a dedicated
prose section in gates.md, only DERIVED001 does. CLAUDE001 matches that
no-section precedent. The one place gates.md DOES need to change (the
`frob:enumerates` member list at gates.md:13, DOCENUM001) is a Tier-A
auto-fix (fix_docenum001_enumerates_sync, T-1974) absorbed automatically
by `frob ticket land` -- no hand edit made or needed.

Plan item 3 (verify frob.tickets._new_gate_rule_acceptance recognizes
CLAUDE001): confirmed. That module reads _KNOWN_GATE_RULES directly via
known_gate_rule_ids(), so step 1 alone is sufficient;
tests/test_tickets_new_gate_rule_acceptance.py passes unchanged (16/16).

Measurement requested by the coordinator: how many places a new gate
rule id must still be registered by hand today. For a rule id shaped
like CLAUDE001 (check_runner `code="..."` extra stage, not a
strata-pipeline gate, not capability/registry-backed): exactly ONE
(_KNOWN_GATE_RULES itself). Everything else is either a Tier-A auto-fix
absorbed at land (DOCENUM001/gates.md enumerates) or does not apply to
this rule shape (REG010 registry sync, SYS111 capability-ratchet sync,
and no gates.md prose section is expected per the confirmed precedent).
Full list and method in the finding recorded below -- nothing
unautomated remained to file as a follow-up ticket for this rule shape;
a rule id constructed via frob.gates' own pipeline or one that IS
capability/registry-backed was not re-measured here (T-1974/T-2001's
own Done reports cover those families).

### Changed
```
 tickets/T-1969/ticket.md | 9 ++++++++-
 1 file changed, 8 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_check_runner.py::TestClaudeConfigDriftStage::test_reports_drift_when_managed_copy_absent` (pytest node id, verified passing when recorded)
- `tests/test_check_runner.py::TestClaudeConfigDriftStage::test_clean_when_in_sync` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestKnownGateRuleIds::test_returns_known_rule_id` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: COV003@tickets/T-0907, DOCENUM001@docs/modules/gates.md, F401@/home/logan/projects/frob/.claude/worktrees/t1969-series/tests/test_gates_fmt_directives.py, F401@/home/logan/projects/frob/.claude/worktrees/t1969-series/tests/unit/test_tickets_evidence_only_scope.py
