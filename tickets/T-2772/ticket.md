---
id: T-2772
title: retarget hardcoded src/frob glob in _new.py's related-check-function suggestion
state: queued
kind: bug
origin: human
created: '2026-08-21'
priority: low
parent: T-2384
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_new.py
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
Child of T-2384 (source-root retarget half, group N).

app/ticket_runner/_new.py:730 hardcodes the glob "src/frob/**/*.py" as the
git grep search path for the 'suggest existing check/refuse functions with
a similar name' heuristic run when filing a new ticket. Off-repo (any
sibling repo whose package is not src/frob/) this glob matches nothing in
THAT repo's own tree, so the suggestion feature silently returns an empty
list every time -- a UX degradation of the same silent-pass shape as the
gate-level findings in T-2384, just in a ticket-authoring helper instead
of a gate.

Fix: replace the literal with frob.lang.declared_source_prefixes(root)
(T-2195/T-2389's promoted resolver), expanding to one glob per declared
source prefix (or a comma-joined git grep pathspec list) instead of the
single src/frob/ literal. Do not add a second resolver.

Verification (both directions):
- must-now-fire fixture: a src-layout project whose package is NOT named
  frob, containing a def _refuse_/_check_ function whose name overlaps a
  new ticket's title words, where the suggestion previously returned ()
  and must now return that match.
- must-still-pass control: this repo's own suggestion output for an
  existing representative ticket title is unchanged after the retarget.