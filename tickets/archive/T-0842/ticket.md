---
id: T-0842
title: 'gates: TICK008 -- unknown/extra ledger fields must be a frob check finding
  (T-0838 typo hazard)'
state: done
kind: security
origin: human
created: '2026-07-23'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/__init__.py
- src/frob/tickets/_models.py
- tests/test_gates.py
- docs/modules/gates.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/modules/gates.md
  reason: gates.md needs a TICK008 row + detail section for the new rule, per hard
    convention for new gate rules (TICK004/006/007 precedent); the doc add is minimal,
    precedented, and required by T-0842 Description item 3.
  actor: logan
  at: '2026-07-23'
evidence:
- tests/test_gates.py::TestTick008UnknownLedgerFields::test_fires_on_unknown_field
- tests/test_gates.py::TestTick008UnknownLedgerFields::test_fuzzy_hint_on_near_miss_typo
- tests/test_gates.py::TestTick008UnknownLedgerFields::test_silent_on_clean_ledger
- tests/test_gates.py::TestTick008UnknownLedgerFields::test_real_repo_ledger_is_tick008_clean
- tests/test_gates.py::TestTick008UnknownLedgerFields::test_waivable
designated_repro_test: null
threat: null
component: null
---
T-0838 made the ledger Ticket model tolerate unknown fields (warn +
preserve + round-trip) so schema-extending features stop bricking their
own lands. The disclosed cost: a TYPOED known field (priorty: low) is
now silently treated as an unknown extra -- the intended value is lost
to the schema default and the only signal is a WARNING log line no gate
reads. Reviewer verdict on T-0838 mandates this follow-up.

Fix: new TICK-family gate rule (TICK008) that ERRORs (or at minimum
WARNs as a frob check finding) on any ticket block in the CHECKED
ledger carrying unknown/extra fields. Tolerance remains correct at
LOAD time (that is the forward-compat point); the gate makes the drift
VISIBLE mechanically on main where the ledger must be canonical. Rule
must whitelist nothing by default; a worktree mid-land carrying a
newer-schema field will go green as soon as the schema-owning feature
lands (its model then knows the field). Register CHK-GATE-TICK008 +
gate_rule_total at land per precedent. Include a fuzzy-match hint in
the message (unknown field 'priorty' -- did you mean 'priority'?) via
difflib.get_close_matches.