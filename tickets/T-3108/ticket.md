---
id: T-3108
title: TICK006 auto-recovery files duplicate tickets for citations of ids minted in
  sibling worktrees
state: in-progress
kind: bug
origin: human
created: '2026-08-27'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_fix_engine.py
- tests/test_gates_tick006_sibling_worktree.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/gates/_fix_engine_text.py
  reason: declared scope named src/frob/gates/_fix_engine_text.py, which has no TICK006
    handling at all (it holds FMT001/SUPPRESS001/E501 text-patch helpers); the real
    TICK006 phantom-citation auto-recovery lives in src/frob/gates/_fix_engine.py
  actor: logan
  at: '2026-08-27'
- op: add
  glob: src/frob/gates/_fix_engine.py
  reason: declared scope named src/frob/gates/_fix_engine_text.py, which has no TICK006
    handling at all (it holds FMT001/SUPPRESS001/E501 text-patch helpers); the real
    TICK006 phantom-citation auto-recovery lives in src/frob/gates/_fix_engine.py
  actor: logan
  at: '2026-08-27'
- op: add
  glob: tests/test_gates_tick006_sibling_worktree.py
  reason: T-3108's own new fixtures module
  actor: logan
  at: '2026-08-27'
body_changes:
- mode: set
  reason: Record the two measured duplicate filings, the mint-vs-land race that causes
    them, and the requirement to treat unresolvable citations as UNKNOWN rather than
    phantom
  actor: logan
  at: '2026-08-27'
  old_length: 0
  new_length: 3306
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED 2026-08-27. The TICK006 Tier-A auto-recovery (T-1544) filed TWO
duplicate tickets during T-3095's land:

    T-3100  "Recovered from T-3095's phantom TICK006 citation of T-3107"
    T-3103  "Recovered from T-3095's phantom TICK006 citation of T-3106"

Both were WRONG. T-3095's Done report cited T-3106 and T-3107, the recovery
resolved neither against `tickets.md` or `tickets-archive.md`, concluded the
filing trail was phantom, and auto-filed replacements quoting the surrounding
prose verbatim. T-3106 and T-3107 BOTH EXIST -- T-3106 queued, T-3107
in-progress -- they simply had not landed from their sibling worktrees at the
moment the recovery took its snapshot. I dropped both duplicates by hand.

THE RACE. Under a multi-agent fleet, a ticket id is minted inside a worktree
and is invisible on main until that worktree lands (T-2197). So a Done report
written in worktree A can legitimately cite an id minted in worktree B that has
not landed yet. The recovery resolves citations against the LANDED ledger only,
so any such cross-worktree citation reads as phantom. The window is exactly the
gap between minting and landing, which under a fleet is routinely minutes.

THIS IS NOT A NEW CLASS. TICK006 auto-recovery was previously measured at 92%
FALSE POSITIVE, on the grounds that a ledger snapshot cannot represent a
rename. This is a second, independent source of the same wrongness, and it is
worse in one respect: a rename false-positive produces a confusing ticket,
whereas this one produces a DUPLICATE of real, active work. T-3100 duplicated a
ticket that was already in-progress.

WHY AUTO-FILING MAKES IT WORSE. A false detection that merely warns costs a
reader ten seconds. A false detection that FILES A TICKET adds permanent noise
to the queue, competes for dispatch, and -- because the auto-filed body quotes
the original prose verbatim -- looks like a genuine, well-specified ticket. Two
of the four tickets this machinery produced today were pure duplicates of
active work. That ratio is consistent with the 92% figure.

WHAT IS WANTED
- The citation check must resolve ids against UNLANDED worktree ledgers as well
  as the landed one, or must treat "not found" as UNKNOWN rather than as
  phantom. This repo's standing doctrine is that UNRESOLVED is a third state and
  is never counted as a violation (T-1664); "cannot see it from here" is exactly
  that state.
- Given the measured false-positive rate, seriously consider whether this
  recovery should FILE anything at all versus reporting for human disposition.
  Auto-filing is only defensible at a much lower error rate than this one has.
- If it keeps filing, an auto-filed recovery ticket must be marked as
  machine-generated and low-confidence, so it is distinguishable from a
  hand-specified ticket at a glance. Today they were not.

ACCEPTANCE
- A Done report citing an id minted in a sibling worktree that has NOT yet
  landed does not produce a recovery ticket. Must-stay-quiet fixture
  reproducing the cross-worktree arrangement.
- A genuinely phantom citation (an id that exists nowhere, landed or unlanded)
  is still detected. Must-fire fixture -- do not solve this by never firing.
- Report the measured false-positive rate before and after, against the same
  corpus that produced the 92% figure.
