---
id: T-0995
title: pre-existing DUP001 test-body duplication surfaced by T-0988's fmt sweep (test_cli_requires_reason
  / test_transition_allows_when_covers_scope_true)
state: done
kind: bug
origin: human
created: '2026-07-27'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tests/test_tickets_scope_mutation.py
- tests/unit/test_ticket_file_flags.py
- tests/test_evidence_integrity.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_evidence_integrity.py::TestD02ScopeBinding::test_transition_allows_when_covers_scope_true
- tests/test_evidence_integrity.py::TestT0417ReverifyEvidenceOnClose::test_transition_allows_when_evidence_reverified_true
- tests/test_tickets_scope_mutation.py::TestScopeCli::test_cli_requires_reason
designated_repro_test: null
threat: null
component: null
---
T-0988's repo-wide frob fmt recompaction touched these test files' surrounding frob: directive comments (no test-body changes), which surfaced 2 pre-existing DUP001 findings: tests/test_tickets_scope_mutation.py::TestScopeCli.test_cli_requires_reason (100% similar to tests/unit/test_ticket_file_flags.py::TestScopeReasonFile.test_neither_reason_nor_reason_file_errors_cleanly), and tests/test_evidence_integrity.py::TestD02ScopeBinding.test_transition_allows_when_covers_scope_true (95% similar to tests/test_evidence_integrity.py::TestT0417ReverifyEvidenceOnClose.test_transition_allows_when_evidence_reverified_true). Confirmed pre-existing and unrelated to the fmt diff itself (the flagged test bodies are unchanged; DUP001 compares a touched file's symbols against the whole corpus regardless of what changed about them). Extract a shared helper or otherwise dedup, per the gate's own suggestion, in a follow-up -- out of scope for a purely mechanical fmt ticket to fix opportunistically.