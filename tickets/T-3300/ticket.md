---
id: T-3300
title: LiveTrackerCited forces late out-of-scope edits at close when an earlier ticket's
  waiver cites the closer
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
- src/frob/gates/_waive.py
- src/frob/gates/_waive_comments.py
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
REPORTED FROM REAL CONSUMER USE (../diax FROBLEMS.md F-040, F-044).

ROOT CAUSE: `frob:waive ... follow_up="T-XXXX"` directives landed by an
EARLIER ticket can name a LATER ticket as the one responsible for
re-resolving them. When that later ticket closes, LiveTrackerCited refuses
because those waivers still cite it -- correct behavior -- but the files
holding the waivers are routinely OUTSIDE the closing ticket's own declared
scope (they belong to whatever module the earlier ticket touched), so
resolving the citation requires a manual, late, out-of-scope `scope --add`
discovered only at the close step, after the gate loop already reported 0
errors.

TWO REPORTS OF THE SAME SHAPE:
  - F-040: T-0022 blocked closing by four WIRE001 waivers in files landed by
    an earlier ticket, outside T-0022's scope. Reporter's own suggested fix:
    a `frob ticket close --repoint <ticket>` helper, or auto-resolving an
    unwaived-because-now-wired symbol instead of requiring manual scope
    expansion.
  - F-044: same shape, worse cascade -- T-0024 hit seven WIRE001 waivers
    citing it from src/diax/geom/point.py (outside scope). Fixing it required
    `scope --add` on that file, which then tripped AFFECT001 demanding
    docs/subsystems/geom.md, which then tripped 46 SCOPE002 warnings because
    that doc's other anchors describe src/diax/geom/zoom.py (see the
    SCOPE002 doc-anchor-fanout ticket filed alongside this one -- same
    downstream mechanism, do not re-fix it here, just note the interaction).
    All of this surfaces only at close time, never during the gate loop.

WHAT NOT TO DO: do not make LiveTrackerCited advisory/non-blocking -- the
whole point is that an unresolved waiver citing a ticket as its resolver must
actually get resolved by that ticket, or the citation rots. Do not
auto-resolve waivers just because the cited ticket closed, either, without
checking the underlying finding is actually gone -- that reintroduces exactly
the "waiver claims fixed but isn't" failure this repo has been bitten by
before (WAIVE004).

WHAT TO BUILD:
  1. Surface citing waivers as a `frob check --ticket` finding from the
     START of the gate loop (a WARNING, naming the citing file(s) and the
     original ticket), not only as a hard refusal discovered at `close`.
     This alone converts an ambush into visible, plannable work.
  2. Either build the reporter's suggested `close --repoint <ticket>` (a
     narrow, ledger-only re-pointing operation that does not require file
     scope) for the case where the fix really is "point this waiver at a
     different follow-up ticket", or treat a waiver whose follow_up is the
     CLOSING ticket's own id as resolvable by that ticket's declared scope
     grant without a separate `scope --add` on the waiver's file.

MUST-FIRE FIXTURE: a ticket about to close is cited by a waiver in a file
outside its scope -- `frob check --ticket` (run at the START of work, before
close) must show a WARNING naming the citing waiver, not silence until close.

MUST-STAY-QUIET FIXTURE: a ticket with no citing waivers anywhere -- 0 new
findings, close behaves exactly as before.
