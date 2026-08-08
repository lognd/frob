---
id: T-1880
title: frob ticket start grants a lease without checking cross-ticket scope collision
  at grant time
state: queued
kind: bug
origin: human
created: '2026-08-08'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/_lifecycle.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
acceptance:
- text: 'GIVEN T-1868 landed and closed the `scope --add` door (a ticket can no longer
    widen its own scope into a path another in-progress ticket''s live cross-worktree
    lease already covers) WHEN a ticket instead declares a colliding path in its ORIGINAL
    FILED scope and simply runs `frob ticket start` THEN nothing refuses it today
    -- `start`''s own guard chain (`_refuse_if_terminal`, `_refuse_if_foreign_live_lease`,
    T-1866''s `_refuse_over_broad_scope_on_start`) never checks the ticket''s declared
    scope against any OTHER in-progress ticket''s live lease. This is the door every
    real dispatch goes through, not an edge case: the T-1851/T-1870 collision on `src/frob/app/config.py`
    proves it was granted exactly this way, live, on this repo''s own main, in the
    same session T-1868 landed. Anyone reading "T-1868 fixed lease conflicts" should
    not assume the class is closed -- it is one of two doors, and only one is shut.'
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
---
CONFIRMED via `.git/frob-leases/*.json` on main (T-1868 investigation
follow-up), both still live at filing time:

    CONFLICT T-1822 T-1873 ['design/frob.strata']
    CONFLICT T-1851 T-1870 ['src/frob/app/_config_external.py', 'src/frob/app/config.py']

Root-cause split by WHICH PATH granted each, traced via git history of
each ticket's own tickets/<id>/ticket.md:

- T-1822/T-1873's design/frob.strata collision: BOTH sides added it via
  `frob ticket scope --add` AFTER their own `start` (T-1822 at
  2026-08-08 10:29:17, T-1873 at 12:28:02; both started earlier, neither
  declared it at filing). This shape is T-1868's own fix
  (`_scope_add_live_lease_conflict`, landed 1d376d5f4218...) -- confirm
  after this ticket that a NEW instance of this exact shape cannot recur.

- T-1851/T-1870's src/frob/app/config.py collision: DIFFERENT shape.
  T-1870 declared config.py in its ORIGINAL FILED scope and started at
  2026-08-08 11:40:53. T-1851 was filed with config.py ALREADY in its
  own declared scope and started LATER, at 2026-08-08 12:38:02 -- so
  `frob ticket start T-1851` granted a lease over a path T-1870 already
  held live, and nothing refused it. `_start`'s own guard chain
  (`_refuse_if_terminal`, `_refuse_if_foreign_live_lease`,
  `_refuse_over_broad_scope_on_start` (T-1866)) checks whether THIS
  ticket already holds a lease elsewhere, and whether its scope is
  itself over-broad -- but never whether its declared scope OVERLAPS
  another ALREADY-in-progress ticket's live lease. `doable`/`leased_by`
  filter collisions out of the OFFERED list, but nothing stops a direct
  `frob ticket start <id>` (bypassing `doable`) from granting a
  colliding lease anyway.

This is genuinely a different hole from T-1868's (which fixed `scope
--add` reading a stale LOCAL queue instead of the live cross-worktree
lease side-channel): T-1851/T-1870's collision was possible even with a
perfectly up-to-date local ledger, because `start` simply never checks
collision against sibling leases at all, at either the queue level or
the live-lease level.

REQUIRED: `frob ticket start` (or the shared lease-acquisition primitive
it and `scope --add` both eventually call) must refuse when the
ticket's OWN scope (at the moment of granting the IN_PROGRESS lease)
overlaps ANOTHER in-progress ticket's live lease -- checked via
`read_all_leases` (live, cross-worktree, no merge needed) using
`scope_overlap_globs` (semantic glob-expansion matching, NOT a literal
string/set comparison -- `src/frob/app/config.py` vs `src/frob/app/**`
is the same defect this repo already treats as one class, T-1868's own
review comment). Consider whether the check belongs in ONE shared
helper both `_start` and `mutate_scope` call, rather than two separate
copies that can drift.

Do not resolve the two currently-live conflicts (T-1822/T-1873,
T-1851/T-1870) as part of this ticket -- the coordinator is sequencing
those agents by hand.
