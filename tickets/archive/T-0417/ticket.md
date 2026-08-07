---
id: T-0417
title: 'Evidence integrity round 2: close still not converged -- empty-scope bypass,
  no re-verify-at-close, vacuous-test passes (docs/audits/tickets-testing-round2.md)'
state: done
kind: security
origin: human
created: '2026-07-20'
priority: medium
parent: T-0398
tier: ticket
sprint: null
scope:
- src/frob/tickets/
- src/frob/gates/
- src/frob/app/ticket_runner.py
- src/frob/testing/
- docs/modules/tickets.md
- tests/test_evidence_integrity.py
- tests/test_ticket_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/modules/tickets.md
  reason: N-02 fix touches transition()'s doc anchor and adds regression tests for
    close-time re-verify
  actor: logan
  at: '2026-07-27'
- op: add
  glob: tests/test_evidence_integrity.py
  reason: N-02 fix touches transition()'s doc anchor and adds regression tests for
    close-time re-verify
  actor: logan
  at: '2026-07-27'
- op: add
  glob: tests/test_ticket_land.py
  reason: N-02 fix touches transition()'s doc anchor and adds regression tests for
    close-time re-verify
  actor: logan
  at: '2026-07-27'
evidence:
- tests/test_evidence_integrity.py::TestT0417ReverifyEvidenceOnClose::test_transition_rejects_when_evidence_reverified_false
- tests/test_evidence_integrity.py::TestT0417ReverifyEvidenceOnClose::test_transition_allows_when_evidence_reverified_true
- tests/test_evidence_integrity.py::TestT0417ReverifyEvidenceOnClose::test_transition_permissive_when_evidence_reverified_none
- tests/test_ticket_land.py::TestReverifyEvidenceForClose::test_no_non_cmd_evidence_returns_none
- tests/test_ticket_land.py::TestReverifyEvidenceForClose::test_collection_failure_returns_false
- tests/test_ticket_land.py::TestReverifyEvidenceForClose::test_still_passing_returns_true
- tests/test_ticket_land.py::TestReverifyEvidenceForClose::test_no_longer_passing_returns_false
designated_repro_test: null
threat: null
component: null
---
Convergence re-audit of the tickets/testing subsystem AFTER T-0398 landed (docs/audits/tickets-testing-round2.md): D-01..D-12 genuinely fixed EXCEPT the subsystem is NOT converged -- 3 new HIGH CLI-reachable bypasses (no --force needed): N-01 omitting --scope skips the D-02 covers_scope binding entirely (a code ticket with no scope closes on any passing evidence); N-02 frob ticket close does NOT re-run the evidence tests -- it trusts the pass status recorded at evidence-record time, so a test recorded green then later broken still closes (TOCTOU); N-03/N-04 pass == pytest exit 0, so a VACUOUS test (asserts nothing) or a self-scoped no-op test satisfies the gate -- the exact vacuous-test class the review loop keeps catching. Plus D-03 is only a 3-char floor (weak done-report substance) and D-10/D-12 unchanged. FIX the RIGHT way: (N-01) fail-CLOSED on empty scope for CODE-kind tickets (a code ticket MUST declare scope + have covering evidence); (N-02) RE-VERIFY evidence at close the way land already does (re-run the evidence tests at close, not just trust record-time status); (N-03/04) detect vacuous/no-assertion evidence tests (a test that passes but asserts nothing / never exercises the scope symbol should not count -- reuse the covers_scope graph binding to require the evidence actually reaches a touched symbol, and consider an assertion-presence check); strengthen D-03 beyond a char floor (require the real sections). Re-audit again after -- converged only when a pessimistic pass finds nothing. Full findings + repros: docs/audits/tickets-testing-round2.md. QUEUED behind T-0343/T-0415 (gates/app overlap) to avoid merge conflict.