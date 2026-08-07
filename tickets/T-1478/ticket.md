---
id: T-1478
title: argument-level may scoping (T-1440 follow-up)
state: queued
kind: feature
origin: human
created: '2026-08-03'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- docs/strata/surface.md
- src/frob/strata/_mutation_audit.py
- src/frob/strata/_native_staleness.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/strata/**
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/strata/_mutation_audit.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/strata/_native_staleness.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
designated_repro_test: null
threat: null
component: null
---
docs/strata/surface.md documents argument-level `may` scoping (e.g.
`may "env.read" of "FROB_*"`, narrowing WHICH env vars/paths/hosts a
grant covers, not just which files) as deliberately deferred by T-1440's
own scope cut, saying "its own follow-up ticket (T-1440's child) rather
than bundled into the grammar/join landing; see tickets.md for its id" --
but no T-1440 child ticket was ever actually filed. File it for real
(this ticket) and build argument-level may scoping. Found while draining
NEGEXIST001 (T-1477): the doc's absence-claim had no
frob:until binding.