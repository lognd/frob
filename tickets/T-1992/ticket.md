---
id: T-1992
title: T-1980's policy doc references a sibling-repo path that DOC006 tries (and fails)
  to resolve locally
state: done
kind: docs
origin: human
created: '2026-08-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- docs/guides/frob-version-policy.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- cmd:grep -n 'frob:waive DOC006' docs/guides/frob-version-policy.md exit=0 sha256=48033384818d
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
Regression measured post-land of T-1980: unscoped `frob check --only
gates` on main now includes one real, unwaived DOC006 error:

  docs/guides/frob-version-policy.md:101 DOC006: file/path pointer
  'src/typani/result.py' does not resolve -- not a tracked file

The measured-delta table in that doc names `src/typani/result.py` as
one of the OPAQUE001 finding locations from the typani sibling-repo
measurement -- a real path, but in a different repo, which DOC006
correctly cannot resolve against THIS repo's own tracked file set.
Needs a `frob:waive DOC006` on that line with a reason (intentionally
external -- a sibling-repo path cited in a cross-repo measurement, not
a broken local reference).