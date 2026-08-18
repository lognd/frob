---
id: T-2340
title: design/frob.strata missing capability declarations for tests/unit/verify/test_watermark.py
  (5 undeclared effects, T-2323 residue)
state: queued
kind: bug
origin: human
created: '2026-08-17'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- design/frob.strata
- tests/unit/verify/test_watermark.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-2323's own body flagged these as "may belong here too, confirm current
count first". Confirmed via a fresh `frob check --only sys` in T-2323's
worktree: still present, unchanged count (5 undeclared effects, all on
the testsuite node):

  tests/unit/verify/test_watermark.py:34 exec (subprocess.)
  tests/unit/verify/test_watermark.py:38 exec (subprocess.)
  tests/unit/verify/test_watermark.py:39 exec (subprocess.)
  tests/unit/verify/test_watermark.py:42 env.read (os.environ)
  tests/unit/verify/test_watermark.py:44 exec (subprocess.)

Deliberately left OUT of T-2323's own scope (test_land_sibling_
regression.py and test_new_ticket_scope_overlap_warning.py only) --
adding a third, unrelated test file's capability review mid-ticket
would have expanded scope without a separate reviewed decision. Same
posture as T-2323 itself: read what test_watermark.py's subprocess/env
calls actually do before declaring vs. restructuring, per T-1870's
"deliberate review, not a blind edit" standard.
