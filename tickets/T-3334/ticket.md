---
id: T-3334
title: frob-suggest/--json UX gaps for consumer projects (diax F-012)
state: queued
kind: bug
origin: human
created: '2026-08-28'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/check/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found in ../diax FROBLEMS.md (F-012), noted while working T-3277.

Two distinct items, not independently re-verified in this ticket (filing
per T-3277's own instructions to file rather than fold in):

1. frob-suggest hints point consumers at `scripts/check_summary.py` (see
   the "handrolled-floor-count" nudge text) -- that script exists only in
   frob's own tree, not in a scaffolded consumer project, so the
   suggestion is unusable for anyone except frob-on-frob.
2. `frob check --json`'s top-level output carries no `exit_code` field
   (confirmed structurally during T-3277: the JSON is `{"path":...,
   "results": [...]}`, per-result `exit_code` exists but there is no
   overall one) -- a consumer scripting against `--json` has to re-derive
   pass/fail by scanning every result's `exit_code`/severity counts
   instead of reading one field.

Filing so someone can confirm both against src/frob/check/__init__.py's
JSON serialization and the frob-suggest rule definitions, then either add
a top-level `exit_code`, or point the nudge at something that ships to
consumers.
