---
id: T-1748
title: Two tickets sharing one fix mechanism cannot land from one worktree without
  disabling PassengerTickets and BUG002
state: dropped
kind: bug
origin: agent
created: '2026-08-07'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_land.py
- src/frob/gates/_mutation_evidence.py
- tests/test_ticket_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: docs/modules/tickets.md
  reason: premise looks stale (reachability fix T-1720/T-2173 + pre-existing frob:no-behavior-change
    already cover WANTED items 1/2); expect to close with evidence, not write a doc
    section -- freeing this file for T-1780's split, which it blocks live
  actor: logan
  at: '2026-08-16'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Two tickets that share one fix mechanism cannot both be landed cleanly
from one worktree. Both agents who hit it today reached for a different
workaround, and neither is what the tool should require.

The shape: an agent is given two related tickets (correctly -- they share
a mechanism, so one agent holding both avoids a lease fight and avoids
two people building the same primitive). It implements the shared piece,
lands ticket A, and then ticket B's land refuses, because:

- `PassengerTickets` scans the WHOLE BRANCH DIFF for `frob:ticket <id>`
  additions, not the per-ticket diff. B's branch still carries A's
  commits, so A rides along as an undisclosed passenger -- and
  symmetrically, landing B first makes A the passenger. There is no
  order that avoids it.
- BUG002 then refuses B on its own terms: B's designated repro
  necessarily ALREADY PASSES at main, because A's land carried the shared
  code. The repro cannot fail-at-parent when the parent already contains
  the fix.

Observed twice on 2026-08-07, with two different escapes:

1. One agent isolated ticket A's commits into a FRESH worktree
   (`git worktree add` at a specific sha), landed A independently, then
   merged B's backup branch onto the post-land state and landed B. Manual,
   fiddly, and it invented a worktree the lease model knows nothing about.
2. The other used `--allow-cross-ticket` on BOTH lands plus a
   `frob:waive BUG002` on the second. Each override is individually
   documented and justified, but the combination means two tickets landed
   with the passenger check and the repro check both disabled -- which is
   most of what those gates exist for.

Neither agent did anything wrong. The tool made them choose between
tedium and turning off the checks.

The second agent judged this "not reproducible as a general defect,
happened inside my own worktree". It is general: it follows mechanically
from stacked commits on one branch plus a whole-branch passenger scan,
and it will recur every time a coordinator groups related tickets --
which is the dispatch strategy this drive uses deliberately, because
ungrouped related tickets fight over leases instead.

WANTED:

1. `PassengerTickets` should evaluate the diff attributable to THE
   TICKET BEING LANDED against main, not the whole branch diff. A commit
   already landed on main is not a passenger; that is exactly what
   "already on main" means. Check reachability rather than scanning the
   branch's accumulated text.
2. BUG002's repro check needs a defined answer for "the fix reached main
   via a sibling ticket in this same series". Passing at parent is
   correct here and not evidence of a bad repro. Either detect the
   sibling-land case explicitly, or make `frob:no-behavior-change`'s
   sibling analogue the documented disposition -- but do not leave
   `frob:waive BUG002` as the only route, because a waiver records
   "we decided to skip this" when the truth is "this check is not
   applicable in this configuration". Those are different facts and the
   ledger should not conflate them.
3. Whatever the fix, `frob ticket land` should be able to land a series
   of related tickets from ONE worktree in dependency order without
   overrides. That is the normal case for grouped dispatch, not an edge
   case.

Evidence must include the real shape: two tickets sharing a mechanism,
stacked on one branch, landed in order, with no `--allow-cross-ticket`
and no BUG002 waiver.

## Drop reason
- 2026-08-16: Stale premise, re-measured with direct evidence, not implemented.

T-1748 was filed 2026-08-07 describing two incidents where a stacked-sibling land required either a fiddly manual worktree split, or --allow-cross-ticket on BOTH lands plus a frob:waive BUG002 on the second -- both checks disabled for the whole series. The three WANTED items asked for: (1) reachability-based passenger detection instead of a whole-branch diff scan, (2) a non-waiver BUG002 disposition for the sibling-already-landed-the-fix case, (3) landing a related series from one worktree without overrides.

I hit this exact class first-hand today landing T-2179 (promoted from T-draft-05563e8d) and T-2174 from one worktree/branch (t-2129), both sharing a fix (fleet_status.py plus callgraph.py touched together). Real commits, not a synthetic repro:

- T-2179 landed first: commit 97fbf751deca456af7ce5557da8ee36cd1b94814, carrying T-2174 as a passenger, ONE explicit --allow-cross-ticket disclosure (the flag named exactly T-2174, nothing else).
- T-2174 landed second: commit 7f088c06e395bcbc72f6abdfe01238ba974c0f10, with NO --allow-cross-ticket and NO frob:waive BUG002 at all. Its own BUG002 obligation used the pre-existing frob:no-behavior-change reason=... disposition (T-1616, predates this ticket), which is exactly WANTED item 2's ask (the frob:no-behavior-change sibling analogue) -- already the documented route, not a new mechanism.

Both LAND-PROOF lines read verified=True; git show HEAD:tickets/T-2179/ticket.md and T-2174/ticket.md both read state: done on main.

Why the second land needed zero overrides: frob ticket land's CLI wrapper (_land_cmd.py's auto-sync step, T-1720/T-2173, landed 2026-08-11 -- AFTER this ticket was filed) merges main back into the worktree immediately after every successful land. By the time T-2174 landed, T-2179's commits (and its own directive comment naming T-2179, the passenger-scan pattern) were common ancestors of the worktree's own HEAD, so the passenger-directive diff scan no longer contained them at all -- reachability, not a text scan of the whole branch, exactly WANTED item 1.

What is NOT fixed, and should not be: the FIRST land of a stack still requires one --allow-cross-ticket (T-2179's land named T-2174 explicitly). This is correct, not residual: the passenger's code is genuinely not on main yet at that point, so disclosing it is the guard doing its job. I looked at whether PassengerTickets could auto-exempt a same-worktree lease holder (same_worktree_lease already exists and is used for the unrelated doable/scope --add collision check, T-1883) to remove even this first disclosure -- and stopped: T-1967 is the direct, on-the-nose lesson against exactly this shape (CrossTicketLeakage once exempted same-worktree siblings, which is the standard dispatch pattern, and the exemption silently disabled the guard for the common case). A same-worktree auto-exemption on PassengerTickets would repeat that mistake on a sibling gate. One disclosed flag on the series' first land is the guard functioning as designed, not a defect WANTED item 3 is asking to remove.

Net: WANTED 1 done via T-1720/T-2173. WANTED 2 already available pre-ticket via T-1616's frob:no-behavior-change, demonstrated working in production today. WANTED 3 achieved in the form that does not conflict with T-1967 (one disclosed override on the series first land, zero on every subsequent one) -- not the literal zero-overrides-ever the title implies, which would require re-introducing a guard hole this repo already paid to close once.

No code change filed. If a future incident shows the single first-land disclosure is still causing friction (a 3+-ticket stack where every member needs its own disclosure, not just the first), that is a different, narrower question and should be a fresh ticket citing the actual repro, not a reopening of this one.
