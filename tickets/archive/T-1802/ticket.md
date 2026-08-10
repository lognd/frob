---
id: T-1802
title: 'post-land sweep regression from T-1674: 2 new error(s) (ARCH103, SEC110)'
state: dropped
kind: bug
origin: human
created: '2026-08-07'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
`frob check --land-parity` (and therefore the real land sweep every
ticket's land runs) is unscoped-red right now: `_resolve_ticket_root` in
`src/frob/app/ticket_runner/__init__.py:507` (landed by T-1674) trips both
ARCH103 (mixes I/O, string-formatting, and 4 decision points in one body)
and SEC110, neither waived. Confirmed on a fresh `main` tip (verified via
`git diff main -- src/frob/app/ticket_runner/__init__.py` returning empty
against a hard-reset-to-main checkout, and `git log -1` on the file
attributing it to T-1674's own land commit `5df3d4c6`) -- this is not a
lineage/merge artifact, it is genuinely on `main`.

This blocks every ticket's `frob check --land-parity`/real land sweep
fleet-wide until fixed or waived, discovered while landing T-1503 (a
`docs`-kind, unrelated-file ticket) -- reported rather than silently
fixed out-of-scope, per this repo's own scope discipline.

Fix: either split `_resolve_ticket_root` along its real sub-concerns (or
justify why it is one cohesive unit, per the many `frob:waive ARCH103
reason="T-0977: ..."` precedents already in this same file/module for the
CLI-runner-shape functions) and add the matching `frob:waive`s with real
reasons, or a genuine refactor if the mixed concerns are actually
separable.

## Drop reason
- 2026-08-07: Duplicate of the already-dropped T-1797, same two findings from the same T-1674 land. Both were real when filed and both are fixed: T-1801 split _resolve_ticket_root's three decisions (ARCH103) and waived SEC110 with a reason, since FROB_ROOT carries a filesystem path rather than a credential. Verified: 'frob check --only archgate --only secrets' reports 0 errors on main. Worth noting the sweep re-filed an identical ticket for a commit whose findings were already fixed and already ticketed -- it has no memory of what it previously reported. (absorbed by T-1801)
