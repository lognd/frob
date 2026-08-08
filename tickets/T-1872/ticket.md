---
id: T-1872
title: 'Tier-A canonical ordering for interface= : group by resolved symbol kind,
  alphabetical within group, order-only'
state: queued
kind: feature
origin: human
created: '2026-08-08'
priority: medium
blocked_by:
- T-1871
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/_fix_engine.py
- src/frob/gates/_fix_engine_sync.py
- docs/strata/surface.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
OWNER DIRECTIVE, 2026-08-08: "a tier-A format fix should be alphabetizing
the interface (although splitting capital vs. non-capital to make parsing
functions vs. classes easier) in a canonical fashion."

WHY THIS IS NOT A REVIVAL OF sync-interface, and say so in the code. The
distinction is the whole point and a future reader WILL be tempted to
delete this as leftover auto-writing machinery:

- `sync-interface` (deleted by T-1870) DERIVED THE CONTENT: it measured
  the real public surface and wrote it in, so the declaration mirrored
  the code and could never disagree with it. That is accounting, and it
  is why it had to go.
- This handler REORDERS WHAT A HUMAN ALREADY DECLARED. It never consults
  the code to decide membership. Content stays hand-authored; only
  presentation is normalised, exactly like `frob fmt` or ruff-format.

THE LOAD-BEARING INVARIANT: order-only. The handler MUST NOT add an
entry, remove an entry, or dedup. Assert the multiset of values is
identical before and after, and fail the fix rather than write a
different set. Two reasons this is not paranoia:

1. Adding or removing entries is precisely the sync-interface behaviour
   the owner removed.
2. T-1871 makes a duplicate value a PARSE ERROR. A formatter that
   silently dedups would swallow the very error T-1871 exists to raise,
   and the two changes would quietly cancel out. Do not dedup. Ever.

ORDERING, and a genuine design question the implementer must resolve
before coding:

The directive says split capital from non-capital "to make parsing
functions vs. classes easier". Capitalisation is a LEXICAL proxy for
what is actually being asked -- symbol KIND. This repo's deepest standing
rule is SYMBOLIC NEVER LEXICAL (T-1662 is a critical epic devoted to it),
and frob already resolves these names against bound code, so it can know
that `Ticket` is a class and `land` is a function rather than inferring
it from a capital letter.

Preferred: group by RESOLVED SYMBOL KIND -- classes, then functions,
then constants -- alphabetised within each group.

Fallback when a name cannot be resolved: do NOT guess silently. Emit the
unresolved names as a trailing group in stable alphabetical order and
report that they were unresolved, honouring "cannot verify is never
verified". A formatter that quietly guesses is a formatter that lies
about what it knows.

Note that three casing classes exist in Python, not two: `CapWords`
classes, `snake_case` functions, and `SCREAMING_SNAKE` constants -- and
constants are capital-initial, so a naive capital/non-capital split
buckets `REPO` with `Ticket`. That alone shows the lexical split is the
wrong axis. If kind resolution proves impractical, come back with what
you measured rather than shipping the two-way casing split.

WIRING:

- Register in `TIER_A_HANDLERS` (`src/frob/gates/_fix_engine.py`). The
  ordering contract in that module's comment block is load-bearing --
  read it and justify the slot chosen.
- T-1775's lesson is mandatory here: a Tier-A fix runs in ROOT against
  ROOT's PRE-land build, and must subtract paths the landing changeset
  has already staged, or it will overwrite the very change being landed.
  A rule-deleting ticket was structurally unlandable for exactly this
  reason. Reuse `_worktree_touched_paths`.
- Formatting a bracket list means rewriting a `.strata` source line.
  `_render_interface_block`/`NAMES_PER_LINE` in `_sync_interface.py` do
  line-wrapping today and are being deleted by T-1870 -- if that wrapping
  logic is worth keeping, EXTRACT it before T-1870 lands rather than
  reimplementing it afterwards, and coordinate with that ticket.

SEQUENCING: after T-1870 and T-1871.
