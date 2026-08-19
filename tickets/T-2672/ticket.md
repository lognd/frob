---
id: T-2672
title: 'sweep attributes findings to lands that never touched the flagged files: 6
  of 6 tickets, including two filed after T-2571 and T-2595'
state: in-progress
kind: bug
origin: human
created: '2026-08-19'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/verify/_attribution.py
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
## Measured across six independent tickets

A triage pass ran `git show --stat` on the blamed land for all six
outstanding sweep-filed regression tickets. **All six failed the check** --
in every case the blamed land touched NONE of that ticket's own flagged
files:

    T-2591  blamed T-2197 (bfa7803ff6d1 -- a single-file
            `chore(tickets): record T-2569 start transition`)
    T-2592  blamed T-2197 (696659925a62)
    T-2594  blamed T-2582 (62007fc8d8e1, real 17-file land, 0 of 34 flagged)
    T-2597  blamed T-2588 (18de7953cf1f, real 8-file land, 0 of 2 flagged)
    T-2643  blamed T-2606 (9f0c8562e924, real 9-file land, 0 of 2 flagged)
    T-2653  blamed T-2638 (ce3f40932b9a, real 8-file land, 0 of 45 flagged)

## This is NOT what T-2571 or T-2595 fixed

Filing dates against the two prior fixes (T-2571 landed 01:31:35, T-2595
landed 03:27:15, all 2026-08-19):

    T-2591 00:39  before both     T-2597 01:37  after T-2571 only
    T-2592 00:39  before both     T-2643 06:16  AFTER BOTH
    T-2594 01:22  before both     T-2653 07:22  AFTER BOTH

Two tickets filed after BOTH fixes show the identical false attribution. So
whatever produces it is a distinct, still-live defect -- not a regression of
T-2571's phantom-deleted-path filter, and not the baseline race T-2595's
CAS write closed.

## The correction that matters more than the bug

I have repeatedly characterised this class as "the sweep is wrong ~99% of
the time", from an earlier measurement of 155 identities with 2 genuine.
That is true of the ATTRIBUTION and FALSE of the FINDINGS.

The same triage checked whether each flagged identity still reproduces on
current main. For the three tickets it kept, **34 of 35 distinct (rule,
file) pairs reproduce right now** -- COV001 on four files, ARCH103 on two,
COV003 on six ticket dirs, DOC001/002/005/008, DOCENUM001, PERF002-004,
TICK003/004, and more. That is real, currently-red repo debt.

The mechanism is now clear: the debt has never been fixed, so every sweep
correctly re-notices it is still there and re-files it against whichever
land happened to run next. The findings are true; only the blame is false.

Dropping those tickets on "the attribution is wrong" would have destroyed
34 live findings. Any future work on this class must separate the two
questions: is the finding real (does it reproduce?), and is the blame right
(did the land touch the file?). They have different answers and different
remedies.

## Fix

Find why a land is named for findings in files it never touched. The
`git show --stat` check is cheap, decisive, and evidently not being applied
-- a finding whose file is untouched by the candidate commit cannot have
been caused by it, and that alone would have suppressed the false blame on
all six.

Note the attribution engine already reports `UNATTRIBUTED` with an empty
candidate list in these cases. Filing an unattributed finding is CORRECT and
must not change -- an unexplained finding is still a finding. What must
change is naming a specific land as the cause when the evidence contradicts
it, because a wrong cause sends the next reader to the wrong diff.

## Positive controls, both directions

- a finding in a file the blamed land never touched is NOT attributed to it
  (reported unattributed instead, still filed)
- a finding in a file the land DID touch is still attributed to it --
  without this the fix is indistinguishable from disabling attribution
- an unattributed finding is still FILED, with its unattributed status
  stated
- pre-existing debt that merely persists does not accumulate a new ticket
  per subsequent land. Three near-duplicate 30-45-item tickets for one
  unfixed debt set is the visible cost of this bug
