---
id: T-0399
title: 'AUDIT: green must claim quality -- promote quality gates from WARN to blocking
  (docs/audits/gates-quality.md)'
state: done
kind: security
origin: human
created: '2026-07-20'
priority: medium
parent: T-0397
tier: ticket
sprint: null
scope:
- src/frob/gates/
- src/frob/app/config.py
- frob.toml
- docs/modules/gates.md
- docs/audits/gates-quality.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/modules/gates.md
  reason: 'T-0399: document the DUP003 fail-closed rule + record the executed promotion
    plan, as the ticket body requires'
  actor: logan
  at: '2026-07-27'
- op: add
  glob: docs/audits/gates-quality.md
  reason: 'T-0399: document the DUP003 fail-closed rule + record the executed promotion
    plan, as the ticket body requires'
  actor: logan
  at: '2026-07-27'
evidence:
- tests/test_gates.py::TestOptInGates::test_dup_gate_fails_closed_when_enforced_but_core_missing
- tests/test_gates.py::TestKnownGateRuleIds::test_every_emitted_rule_literal_is_known
designated_repro_test: null
acceptance:
- text: given [dup].enforce=true and frob-core unavailable, dup_gate FAILS closed
    with a DUP003 ERROR through the production `dup_gate` invocation (before this
    change it silently returned no violations -- a FAIL/PASS fixture proof, not merely
    a unit test of a pure function); PASSES after this ticket's change (test_dup_gate_fails_closed_when_enforced_but_core_missing
    exercises dup_gate itself, the real production entrypoint gates registers).
  evidence:
  - tests/test_gates.py::TestOptInGates::test_dup_gate_fails_closed_when_enforced_but_core_missing
  - tests/test_gates.py::TestKnownGateRuleIds::test_every_emitted_rule_literal_is_known
threat: null
component: null
---
See docs/audits/gates-quality.md. HIGH: entire quality surface is non-blocking (PERF/PII010/SEC110/ARCH001/DUP/lower-secrets are WARN, frob check exits 0 on them) -- green makes NO quality claim; DUP fails open (default-off AND no-op without natives); frob:secret-fake suppresses real secrets with no accountability/reason/ledger. RIGHT-WAY fix: decide per rule which are error-tier (and default DUP on / fail-closed when natives missing); give secret suppression the same reasoned-waiver accountability as frob:waive. Expect the build to red -- that red is honest. Then re-audit until empty. MED/LOW in the doc.