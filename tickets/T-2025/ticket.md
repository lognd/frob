---
id: T-2025
title: 'Post-land --check-repro cannot verify a squashed ticket''s repro test: no
  ref in main history has test-without-fix'
state: queued
kind: bug
origin: human
created: '2026-08-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/_mutation_evidence.py
- src/frob/tickets/_land_git_ops.py
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
Found while working T-2019 (re-verifying 10 BUG002 repro designations
against T-2005's PYTHONPATH fix).

`frob ticket land` squashes every worktree ticket's commits into ONE
commit on main (confirmed: T-1546's own worktree commits, e.g.
086172ad8, are NOT ancestors of main -- only the single "land T-1546"
squash commit 4b6695745 is). This means main's own history never
contains a commit where a ticket's designated repro test exists
WITHOUT that same ticket's fix already applied: the test method and
the fix land together, atomically, in the same commit.

Consequence: `frob ticket evidence <id> --check-repro [NODE-ID]
--base-ref <ref>` run AFTER landing, against ANY ref in main's history
(including the land commit's own immediate parent, main's tip right
before the squash), cannot ever produce a real verdict for a NEWLY
ADDED repro test -- pytest exits 5 ("no tests collected") because the
specific test method does not exist yet at that ref, and the tool
correctly reports this as NO_VERDICT, not a pass or fail.

Measured directly: 9 of the 10 tickets T-2019 asked to re-verify
(T-1546, T-1749, T-1838, T-1841, T-1848, T-1853, T-1861, T-1882,
T-1907; T-1670 excluded as N/A, see T-2019's Done report) all returned
NO_VERDICT this way. Confirmed by direct inspection for T-1546 and
T-1907 that the designated test method is absent from the git blob at
the chosen parent ref, while the surrounding test class is present --
exactly the squash-history shape, not a per-ticket anomaly.

This means `--check-repro`/`--designate-repro`'s parent-commit
classification is ONLY ever meaningfully checkable from INSIDE a
ticket's own worktree, BEFORE it lands (where the test-added-then-fix-
added commit sequence still exists un-squashed) -- once a ticket lands
and its worktree is removed, there is structurally no way to
independently re-verify its BUG002 classification against main alone.
T-2019 needed to fall back to reading whether the tool's OWN validation
ran correctly at designate/land time (audit trail, --designate-repro's
synchronous validation per T-1929) rather than being able to
reproduce the check itself post-land.

Proposed scope: either (a) `frob ticket land` records the pre-squash
parent SHA (the worktree branch point, or the specific commit
immediately after the repro test was added but before the fix) into
the ticket's ledger at land time, so a later `--check-repro --base-ref
<recorded-sha>` has a real ref to check against, or (b) explicitly
document this as a permanent limitation of `--check-repro` post-land,
so a coordinator does not ask an agent to do what T-2019 asked (which
this repo's own review process is going to keep re-discovering
otherwise).
