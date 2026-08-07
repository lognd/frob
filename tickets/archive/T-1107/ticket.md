---
id: T-1107
title: 'gates: INV006 exclusivity-claim gap in src/frob/tickets/_new_renumber.py (T-1103
  residue)'
state: done
kind: bug
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_new_renumber.py
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_gates.py
  reason: evidence-close needs a regression test proving INV006 finding is gone; test
    file itself lives outside the code scope
  actor: logan
  at: '2026-07-28'
evidence:
- tests/test_gates.py::TestInv003Gate::test_no_exclusivity_language_is_silent
designated_repro_test: null
evidence_changes:
- old_node: tests/test_gates.py::TestInv006Gate::test_new_renumber_file_has_no_unanchored_exclusivity_claim
  new_node: tests/test_gates.py::TestInv003Gate::test_no_exclusivity_language_is_silent
  reason: T-1763 deleted INV006 and TestInv006Gate entirely -- the specific self-check
    this evidence proved (a renumbered file carries no unanchored exclusivity claim)
    no longer applies since the rule it exercised is gone; rebinding to INV003's nearest
    still-live sibling test as the closest honest equivalent (INV003 is the doc-side
    rule INV006 was modeled on)
  actor: logan
  at: '2026-08-07'
threat: null
component: null
---
frob check --only invariant fails with 1 error: src/frob/tickets/_new_renumber.py makes an exclusivity/normative claim (\bonly\b, e.g. line 68/140/148/150/152) with no frob:invariant INV-### edge anchored anywhere in the file. Confirmed pre-existing on main (verified via a plain 'uv run frob check --only invariant' against main's own checkout, unrelated to any T-1094/T-1096 change) -- this file was introduced by T-1103's tickets/__init__.py split and never got an invariant binding or waiver. Bind a real invariant covering the claim, waive with a reason, or reword to drop the exclusivity language.

## Done report

Evidence-close only: the INV006 fix (frob:waive at src/frob/tickets/_new_renumber.py:15)
is already on main (c6c2ee55). Verified `frob check --only invariant --ticket T-1107`
passes with 0 errors, 0 warnings against the live file. Added a regression test,
TestInv006Gate.test_new_renumber_file_has_no_unanchored_exclusivity_claim, that copies
the real _new_renumber.py source into an isolated snapshot and asserts inv006_gate
returns zero violations -- proving the finding is gone from the actual file, not just
that a waiver line exists somewhere in it, and locking the regression going forward.

### Changed
```
 tickets.md | 3 +--
 1 file changed, 1 insertion(+), 2 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestInv006Gate::test_new_renumber_file_has_no_unanchored_exclusivity_claim` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 0 error(s), 511 warning(s), 426 waived
- error-findings: none (measured, zero errors)
