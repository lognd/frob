---
id: T-1969
title: Register CLAUDE001 in _KNOWN_GATE_RULES (T-1809's gate registry entry)
state: done
kind: docs
origin: human
created: '2026-08-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/_waive.py
- docs/modules/gates.md
evidence_scope:
- tests/test_check_runner.py
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_check_runner.py::TestClaudeConfigDriftStage::test_reports_drift_when_managed_copy_absent
- tests/test_check_runner.py::TestClaudeConfigDriftStage::test_clean_when_in_sync
- tests/test_gates.py::TestKnownGateRuleIds::test_returns_known_rule_id
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
T-1809 implemented the Claude-config sync drift check (CLAUDE001,
`src/frob/app/check_runner.py::_claude_config_drift_result`) as an opt-in
extra `frob check` stage, following the DEPLOY001-003 precedent
(`_deploy_drift_result`/`_deploy_conformance_result`), because
`src/frob/gates/__init__.py` and `src/frob/gates/_waive.py` were both
under T-1937's live cross-worktree lease for the whole of T-1809's
dispatch window -- registering the rule id in `_KNOWN_GATE_RULES` was not
possible at that time.

T-1937 is now `done` and closed -- it is NOT a queue, so this cannot be
left "for T-1937 to pick up" as T-1809's own Done report originally
assumed. This ticket is the real, doable follow-up:

1. Add "CLAUDE001" to `_KNOWN_GATE_RULES` in `src/frob/gates/_waive.py`.
2. Document CLAUDE001 in `docs/modules/gates.md`'s rule catalog (the
   `claude-config-drift` stage, `src/frob/app/check_runner.py`), matching
   how DEPLOY001-003 are (or are not) documented there -- confirm the
   precedent before assuming a gates.md entry is even the right shape for
   a non-`frob.gates`-pipeline stage.
3. Verify `frob.tickets._new_gate_rule_acceptance`'s literal-scrape
   preflight now recognizes CLAUDE001 as a known rule id (this is the
   actual bug T-1937 fixed for 10 other ids -- CLAUDE001 landed one
   ticket later and was never swept into that fix).

Filed at medium (matching T-1808/T-1809's own priority) rather than a
lower "wire it up" priority -- per the coordinator's T-1960 finding that
under-prioritized "wire X into Y" follow-ups starve while their
higher-priority parents complete, so this stays visible in `frob ticket
doable` at the same weight as the work it completes.

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
