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
- tests/test_gates.py::TestInv006Gate::test_new_renumber_file_has_no_unanchored_exclusivity_claim
designated_repro_test: null
threat: null
component: null
---
frob check --only invariant fails with 1 error: src/frob/tickets/_new_renumber.py makes an exclusivity/normative claim (\bonly\b, e.g. line 68/140/148/150/152) with no frob:invariant INV-### edge anchored anywhere in the file. Confirmed pre-existing on main (verified via a plain 'uv run frob check --only invariant' against main's own checkout, unrelated to any T-1094/T-1096 change) -- this file was introduced by T-1103's tickets/__init__.py split and never got an invariant binding or waiver. Bind a real invariant covering the claim, waive with a reason, or reword to drop the exclusivity language.