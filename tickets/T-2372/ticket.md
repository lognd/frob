---
id: T-2372
title: Burn TICK004/TICK007/TICK011 WARN gates to zero, then promote to error
state: in-progress
kind: bug
origin: agent
created: '2026-08-17'
priority: medium
parent: T-0969
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_tickets_gate.py
- tickets/archive/T-2556/done-report.md
- tickets/archive/T-2653/done-report.md
- src/frob/gates/_waive.py
evidence_scope:
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_tickets_gate.py
  reason: TICK004/TICK007/TICK011 severity promotion lives in this gate module
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tickets/archive/T-2556/done-report.md
  reason: 'TICK011 remediation: repair the two archived Done reports whose disclosures
    needed a nearby citation/no-ticket-needed marker (see gate-code fix in the same
    ticket for why the other 7 were bare-word false positives, not real gaps)'
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tickets/archive/T-2653/done-report.md
  reason: 'TICK011 remediation: repair the two archived Done reports whose disclosures
    needed a nearby citation/no-ticket-needed marker (see gate-code fix in the same
    ticket for why the other 7 were bare-word false positives, not real gaps)'
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/gates/_waive.py
  reason: TICK011 rule-catalog comment needs the WARN->ERROR promotion note
  actor: logan
  at: '2026-08-26'
evidence:
- tests/test_gates.py::TestTick011DisclosedCutWithoutTicket::test_disclosed_follow_up_with_no_citation_fires
- tests/test_gates.py::TestTick011DisclosedCutWithoutTicket::test_numeric_count_residual_is_not_a_disclosure
- tests/test_gates.py::TestTick011DisclosedCutWithoutTicket::test_rule_id_shaped_residue_is_not_a_disclosure
- tests/test_gates.py::TestTick011DisclosedCutWithoutTicket::test_residue_heading_label_with_no_citation_still_fires
- tests/test_gates.py::TestTick011DisclosedCutWithoutTicket::test_residue_heading_label_with_citation_immediately_after_is_silent
- tests/test_gates.py::TestTick011DisclosedCutWithoutTicket::test_ordinary_prose_residue_preceded_by_non_technical_word_is_not_a_disclosure
designated_repro_test: tests/test_gates.py::TestTick011DisclosedCutWithoutTicket::test_ordinary_prose_residue_preceded_by_non_technical_word_is_not_a_disclosure
acceptance:
- text: 'given TICK011''s WARN findings (the residue/residual false-positive

    population this ticket root-caused and fixed), when frob check --json

    runs, then zero findings remain -- confirmed 9 -> 0. TICK004/TICK007

    (the ticket''s original wider family) require real ticket-queue triage

    on unrelated backlog tickets, split out as T-2946, not claimed here.'
  evidence: []
- text: given the family's gate module, when its severity is read, then it is ERROR
    not WARNING
  evidence: []
acceptance_amendments:
- op: replace
  index: 0
  old_text: given the family's WARN codes, when frob check --json runs, then zero
    findings remain
  new_text: 'given TICK011''s WARN findings (the residue/residual false-positive

    population this ticket root-caused and fixed), when frob check --json

    runs, then zero findings remain -- confirmed 9 -> 0. TICK004/TICK007

    (the ticket''s original wider family) require real ticket-queue triage

    on unrelated backlog tickets, split out as T-2946, not claimed here.'
  reason: 'given TICK011''s WARN findings (the residue/residual false-positive

    population this ticket root-caused and fixed), when frob check --json

    runs, then zero findings remain -- confirmed 9 -> 0. TICK004/TICK007

    (the ticket''s original wider family) require real ticket-queue triage

    on unrelated backlog tickets, split out as T-2946, not claimed here.

    '
  actor: logan
  at: '2026-08-26'
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Measured via `uv run frob check --json --budget 500` (full gate-summary coverage,
no BUDGET001 deferral) piped through `scripts/check_summary.py`, 2026-08-18.

WARN-tier finding count, this family (ledger-hygiene checks (rotting tickets, disclosed-cut citations)): 17 across codes TICK004, TICK007, TICK011.

Do NOT hand-count with grep -- this repo has measured false zeros that way, including
one tonight. Re-measure with the same command above before starting and before
claiming done; treat any disagreement with the number in this body as the tree
having moved, not as your measurement being wrong.

Closure is two-part per the epic (T-0969):
1. Zero findings for every code above, verified via the same
   `frob check --json --budget 500 | python3 scripts/check_summary.py` command.
2. Each code above promoted from warning to error severity in its gate module
   (grep the gate module for its severity constant/mapping) -- a burn-down that
   stops at zero and leaves the gate advisory lets the debt silently reaccumulate.
   DOC012 and the T-1662 arc both closed correctly today by doing both; follow
   that shape, not a zero-only burn-down.

Narrow `scope` to the actual files this family's findings live in once you've
run the gate and can see them -- do not take a broad blanket scope; this keeps
you disjoint from sibling children of T-0969.