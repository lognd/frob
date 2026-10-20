+++
id = "01M3AXSDBMG2ZAEHTQ6JHA8CYK"
title = "land: stacked successor hunks silently dropped after the base squash-lands; verify hunk presence post-merge"
type = "bug"
category = "todo"
priority = "medium"
reporter = "agent"
created = "2026-09-25T00:00:00Z"
updated = "2026-10-09T20:42:26Z"
aliases = ["T-6516"]
labels = ["v1-cluster:C1a", "triage:accepted"]
scope = ["src/frob/tickets/_land.py", "src/frob/tickets/_land_verify.py", "src/frob/coord/_status.py", "tests/unit/tickets/test_land_hunk_presence.py", "docs/design/tickets.md"]
+++

Measured 2026-09-25 on the ledger-tiers stack (T-5748): after T-5749 (A1)
squash-landed on dev, EVERY stacked successor worktree (T-5751, T-5756,
T-5765, T-5757, T-5755, T-5760, T-5763, T-5780, T-5774, T-5758, T-5761,
T-5766, T-5776, T-5770, T-5771 -- 15 worktrees) lost the content of the
A2 feature commit 2fa3164a9b (due/rank fields in _models.py and the
TestDueAndRank class in tests/test_tickets.py) and A3's derived_scope
hunks, while that commit stayed an ANCESTOR of each branch:

  git merge-base --is-ancestor 2fa3164a9b HEAD   -> true
  git show HEAD:src/frob/tickets/_models.py | grep -c 'due:'  -> 0

The first land attempt of T-5751 then refused with "evidence no longer
resolves post-merge" naming the four TestDueAndRank node ids -- the bound
evidence pointed at tests that had silently vanished from the tree. No
commit on the first-parent line removes the lines; the drop happened in
a merge of dev (the land engine's own "merge dev into worktree for
landing" / align step, or the coordinator's hygiene merge) where dev
carried A1's squash-landed rewrite of the same regions and the
successor's adjacent hunks were resolved away as if dev had deleted
them. This is the content-level twin of the LAND-PROOF ancestry gap
(land-verification memory): ancestry says the work is there, the tree
says it is not.

Repair applied by hand: cherry-pick -n of the dropped commit onto each
worktree, evidence tests re-run, committed (T-5751: 88170760b2).

Deliver:
1. Land-side: after the pre-land merge of dev, verify that every hunk of
   the ticket's own non-merge commits (dev..HEAD, excluding chore(tickets)
   and passenger commits whose patch-id or added lines already exist on
   dev) is still present in the merged tree; refuse with the list of
   dropped hunks and the merge commit that dropped them, instead of the
   downstream "evidence no longer resolves" symptom.
2. Same check as a `frob ticket` verb or `frob coord status` row for
   queued worktrees (probably-safe tier: report + exact cherry-pick
   command to restore), so a stack can be audited before its turn.
3. Root cause: reproduce with a fixture of base -> A1 branch -> A2 stacked
   on A1 -> squash-land A1 -> merge dev into A2, and show which merge
   step (engine merge strategy/-X theirs, ledger align, hygiene) drops
   A2's hunks; fix the strategy so a stacked successor survives its
   base's squash-land.
4. Positive control: the fixture above lands A2 with its hunks intact and
   its evidence resolving.
