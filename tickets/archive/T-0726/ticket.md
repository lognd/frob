---
id: T-0726
title: 'gate: every filed-as ticket reference in a Done report must resolve to a real
  ledger block'
state: done
kind: security
origin: agent
created: '2026-07-22'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/**
- src/frob/tickets/**
- tests/test_gates.py
- docs/modules/gates.md
- tickets-archive.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/modules/gates.md
  reason: dispatch explicitly asked for the recognized filing-claim grammar to be
    documented in docs/modules/gates.md; tickets-archive.md needed a one-line marker
    fix (T-0367 was silently absorbed into T-0363's body, corrupting TICK006's own
    measurement) discovered while cold-running the new gate against the real ledger
  actor: logan
  at: '2026-07-22'
- op: add
  glob: tickets-archive.md
  reason: dispatch explicitly asked for the recognized filing-claim grammar to be
    documented in docs/modules/gates.md; tickets-archive.md needed a one-line marker
    fix (T-0367 was silently absorbed into T-0363's body, corrupting TICK006's own
    measurement) discovered while cold-running the new gate against the real ledger
  actor: logan
  at: '2026-07-22'
evidence:
- tests/test_gates.py::TestTick006PhantomFiling::test_phantom_filed_colon_fires
- tests/test_gates.py::TestTick006PhantomFiling::test_phantom_filed_as_fires
- tests/test_gates.py::TestTick006PhantomFiling::test_filed_colon_real_active_id_is_silent
- tests/test_gates.py::TestTick006PhantomFiling::test_filed_colon_none_is_silent
- tests/test_gates.py::TestTick006PhantomFiling::test_filed_as_real_archived_id_is_silent
- tests/test_gates.py::TestTick006PhantomFiling::test_negation_not_filed_is_silent
- tests/test_gates.py::TestTick006PhantomFiling::test_negation_no_ticket_filed_is_silent
- tests/test_gates.py::TestTick006PhantomFiling::test_description_prose_mentioning_other_ticket_is_silent
- tests/test_gates.py::TestTick006PhantomFiling::test_no_done_report_heading_is_silent
- tests/test_gates.py::TestTick006PhantomFiling::test_filed_bare_draft_without_colon_fires
designated_repro_test: null
acceptance:
- text: 'GIVEN a Done report claiming Filed: T-draft-abc123 with no such block WHEN
    close or land runs THEN an error names the phantom reference; GIVEN the block
    exists or the report says no ticket was filed THEN silence'
  evidence: []
threat: null
component: null
---
Two occurrences in one session of a Done report claiming a follow-up was filed when no ledger block exists: T-0707 (invented filed-then-absorbed trail) and T-0615 (invented T-draft id in prose, never filed) -- both caught only by reviewer diligence. Add a gate (TICK-family or DRIFT-family): scan Done-report blocks for filed-as / 'Filed:' / T-draft-XXXX / T-#### reference patterns claiming a filing, and ERROR when the referenced id resolves to no block in tickets.md or the archive. Run it in frob ticket close and frob ticket land preflight so a phantom filing can never reach main. Allow explicit negations ('not filed', 'no ticket filed') to pass -- the gate targets affirmative filing claims only.