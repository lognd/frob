---
id: T-0320
title: 'COV002 grace: require an actual open->done ticket transition, not just marker-in-hunk'
state: done
kind: bug
origin: auditor
created: '2026-07-19'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/__init__.py
- tests/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestCoverageGate::test_cov002_done_ticket_covers_own_closing_diff
- tests/test_gates.py::TestCoverageGate::test_cov002_marker_touch_without_state_transition_still_fires
- tests/test_gates.py::TestCoverageGate::test_cov002_done_ticket_without_grace_still_fires
- tests/test_gates.py::TestCoverageGate::test_cov002_stale_done_ticket_unrelated_tickets_md_touch_still_fires
designated_repro_test: null
acceptance:
- text: given a symbol bound to an ALREADY-DONE (stale) ticket and a diff that edits
    that same ticket entry for a non-close reason (typo fix / evidence append touching
    its marker line), when COV002 runs, then grace is NOT granted (it still fires)
    -- grace requires the ticket to transition open->done in THIS diff
  evidence: []
- text: given a ticket genuinely closing in this diff (open before, done after), then
    grace is granted (catch-22 stays fixed)
  evidence: []
threat: null
component: null
---
Follow-up from T-0214 (reviewer-recommended, not blocking). T-0214 closed the exploitable COV002 grace bypass by requiring the bound DONE tickets own <!-- ticket:T-#### --> marker line to fall inside the diffs tickets.md hunk. That closes the easy/invisible case (unrelated ticket close elsewhere in the commit). Residual narrow gap: marker-in-hunk is a PROXY for "closing" -- it does not verify a state TRANSITION, so any edit to a stale DONE tickets own entry that touches its marker line (typo fix in its Done report, evidence append, reformat) grants grace to a bound-but-uncovered stale symbol. Narrow + visible in diff review, hence not blocking, but should be tightened: compare the tickets state in the diffs BEFORE vs AFTER tickets.md (open-before / done-after) rather than mere marker-span overlap. Requires diffing ledger state pre/post within the gate.