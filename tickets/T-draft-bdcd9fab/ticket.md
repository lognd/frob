---
id: T-draft-bdcd9fab
title: 'Gate: refuse over-long ticket-citing comment blocks in src, and ticket ids
  outside docs provenance sections'
state: queued
kind: docs
origin: human
created: '2026-08-28'
priority: medium
parent: T-2994
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_comment_placement.py
- tests/gates/test_comment_placement.py
- docs/guides/agent-playbook.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: parent
  old_value: null
  new_value: T-2994
  reason: T-3189 dropped as a duplicate of this epic tree; this is the gate-only child
    T-2994 was missing (T-2987/T-2988/T-3022 cover migration, not enforcement)
  actor: logan
  at: '2026-08-28'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Child of T-2994 (the placement-rule epic): the GATE half specifically.
T-2987 (waiver-reason cap) and T-2988 (docstring standard) cover their
own slices; T-3022 covers the docs-narrative bulk migration. None of
those three is an enforcement rule against new violations reaccumulating
-- they read as migration/standard-setting work, not a gate. This
ticket is that remaining gap, reconciling T-3189 (filed as a duplicate
of this epic tree, now dropped) and T-2987's OWN finding that its
blanket "frob: directives are exempt at any length" position is too
broad.

MEASUREMENTS carried forward (do not lose either set in the merge):

Code (T-3189's numbers, `src/`, 290,150 lines) -- contiguous
ticket-citing comment blocks by length:
    <=3 lines carrying a frob: DSL directive   2891   (legitimate, leave alone)
    <=3 lines prose                             623
    4-10 lines                                 2630
    11-25 lines                                 574
    26+ lines                                   96
Total in 4+ line blocks: 28,273 lines, about 9.7% of src.
Longest: 130 lines at src/frob/vet/_capability_typescript_bindtable.py:18
(a file of 593 lines total). Others over 100:
    src/frob/gates/_waive.py:1461 (107)
    src/frob/gates/_waive.py:2217 (70)

T-2987's own numbers (same code surface, different lens): 12,913
directives -> 18,074 lines; frob:ticket/frob:tests/frob:doc are 86% of
directives and almost all single-line (leave alone); frob:waive is only
8% of directives but IS the long tail -- all five longest directives in
the repo are waivers, 18-20 lines each, worst in
src/frob/tickets/_leases.py. T-2987's own proposed cap: 2 lines, with
anything longer required to move into the referenced ticket (one-line
summary plus ticket pointer stays).

Docs (T-3189's numbers, `docs/`, 71,689 lines, 152 files): 6,283
ticket-id mentions across 143 of 152 files. Worst:
docs/modules/gates.md (884 lines carry a ticket id, file is 7,169).
T-3022's own numbers (same surface, counted slightly differently --
raw T-id occurrence count, 146 files by its own ls-files run): 140 of
146 files, worst docs/modules/gates.md at 869. Use a fresh count at
gate-build time; these are both already slightly stale relative to each
other.

RESOLVED CONFLICT: T-3189, as originally drafted, exempted every
`frob:` DSL directive at ANY length as a must-stay-quiet fixture. T-2987
found that position too broad -- a 20-line `frob:waive reason=` IS
narrative bloat, not enforcement surface. This ticket adopts T-2987's
position: the length cap applies to frob:waive reason prose same as any
other comment prose (T-2987's own proposed threshold: 2 lines, refine
against the measured distribution above rather than picking a round
number). frob:ticket/frob:tests/frob:doc directives (86% of the total,
almost all already single-line) stay exempt at any length -- they are
pure binding syntax, not narrative, and T-2987 does not challenge them.

BUILD:
  1. A gate rule refusing a contiguous comment block over N lines in
     `src/` that cites a ticket id, where N is chosen from the measured
     distribution above and justified in the ticket, not picked to match
     a round number. `frob:waive` reason prose is subject to the SAME
     cap as ordinary prose (T-2987's finding); `frob:ticket`/
     `frob:tests`/`frob:doc` stay exempt at any length (pure binding
     syntax). Start at WARN if burn-down is not immediately achievable,
     with a promotion ticket, matching this repo's own ladder
     (TICK011/T-2372 precedent) -- state which was chosen and why.
  2. A gate rule refusing a ticket id in `docs/modules/**` outside a
     designated provenance section (a table's bare `(T-1234)`-shaped
     citation used as evidence-of-behaviour stays; an elaborated
     narrative paragraph does not).

MUST-FIRE fixtures (one per rule) and MUST-STAY-QUIET fixtures (both
rules):
  - changelog.d/, CHANGELOG.md, docs/decisions/, tickets/** -- provenance
    is the point there, never flagged.
  - `frob:ticket`/`frob:tests`/`frob:doc` directives at any length.
  - A short `# T-1234: keep the sort stable` attribution.
  - An ordinary one-line `frob:waive ... reason="..."` -- proving the
    narrowed exemption still lets a compliant waiver through even though
    the blanket frob:-directive exemption T-3189 originally proposed is
    gone for frob:waive specifically.

MIGRATION IS NOT THIS TICKET'S JOB. T-2987 (waiver prose), T-2988
(docstrings), and T-3022 (docs narrative) already own the respective
migrations under T-2994. This ticket ships the GATE plus its own fixture
set only, so it does not land 96 first-day WARN findings with nowhere to
go -- those findings are exactly the queue T-2987/T-2988/T-3022 already
exist to drain. If gate-build finds the migration tickets have not
landed enough to avoid an immediate noisy WARN flood, say so explicitly
and sequence behind them rather than shipping into it silently.

ACCEPTANCE
- Both gate rules implemented, each with a must-fire and a must-stay-
  quiet fixture (five total, per the list above).
- The chosen line-length N documented and justified against the
  measured distribution, not a round number picked from the title.
- Before/after counts for both surfaces (code contiguous blocks, docs
  ticket-id mentions in docs/modules/**), measured the same way as
  T-3189/T-2987/T-3022 measured them.
- No migration performed under this ticket -- that is T-2987/T-2988/
  T-3022's job; this ticket states explicitly whether it is safe to ship
  the gate ahead of, or must wait behind, their landing.
