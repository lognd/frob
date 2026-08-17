---
id: T-2227
title: 'A spinning agent is invisible: a branch of ledger-only commits with uncommitted
  source reads as healthy on every liveness signal (90min lost)'
state: dropped
kind: bug
origin: human
created: '2026-08-16'
priority: medium
blocked_by:
- T-2200
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- scripts/fleet_status.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
acceptance:
- text: 'A worktree whose branch commits touch only tickets/** while src/** is modified-but-uncommitted
    is reported as not-progressing (fails today: every signal reports healthy)'
  evidence: []
- text: An agent that HAS committed source changes is STILL reported healthy -- must-still-pass
    control against a detector that flags everyone
  evidence: []
- text: A legitimately ledger-only ticket with a CLEAN working tree is NOT flagged;
    the uncommitted-source half is required
  evidence: []
- text: Classification derives from commit-touched PATHS via diff-tree, never from
    commit message text
  evidence: []
- text: 'Strictly read-only: reports, never kills, restarts, or modifies a worktree'
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
# An agent spinning on ledger bookkeeping without committing code is invisible; nothing distinguishes it from an agent making progress

## Measured evidence (2026-08-16)

T-2215's agent ran ~90 minutes without landing. Every existing liveness signal
reported it HEALTHY the whole time: the worktree existed, processes were
cwd'd into it, and `git log -1` showed a commit 2 minutes old. By every check
the coordinator has, it was working.

Its actual branch state:

    2 minutes ago  | chore(tickets): T-2215 Done report
    11 minutes ago | chore(tickets): record evidence for T-2215
    18 minutes ago | chore(tickets): T-2215 Done report        <- again
    36 minutes ago | chore(tickets): record evidence for T-2215
    37 minutes ago | chore(tickets): record evidence for T-2215
    38 minutes ago | chore(tickets): scope T-2215
    50 minutes ago | chore(tickets): T-2215 Done report        <- and again

    9 commits on the branch, ALL ledger files.

    Working tree, meanwhile:
      M src/frob/app/ticket_runner/_close_cmd.py
      M src/frob/tickets/_land.py
      ?? tests/unit/test_ticket_land_bug003_t2215.py    (untracked)

Three Done reports written while the code was never committed. The repro test
was never committed, so the mandatory repro-alone-then-fix sequence had not
started and `frob ticket evidence --check-repro` could not read
FAILED_AT_PARENT -- which plausibly explains a land refusing repeatedly.

Cost: ~90 minutes of one agent, plus everything waiting on its lease. T-2215
holds `src/frob/tickets/_land.py`, which T-2220 needs, so the spin blocked a
second ticket too. It was found only because a human-equivalent operator
manually ran `git log` and `git status` inside the worktree on a hunch.

## Why the existing signals all miss it

- worktree exists -> yes
- processes cwd'd into it -> yes
- `last-commit Nm ago` -> 2 minutes, looks great
- lease fresh -> yes

Every one of these is satisfied by an agent committing ledger churn in a loop.
"Recent commit" is not "progress"; it is only "recent commit".

## The discriminating signal

A branch whose commits touch ONLY ledger paths (`tickets/**`, `rapid-debt.jsonl`)
while source files are modified-but-uncommitted in the working tree. A healthy
agent commits a repro, then a fix; a spinning one accumulates Done reports.
Repeated `Done report` commits on one branch are a second, independent
indicator -- a Done report is supposed to be terminal.

## Do NOT fix it this way

- **Do NOT kill or auto-restart a suspected-spinning agent.** A false positive
  destroys real in-flight work, and an agent legitimately doing a
  ledger-only ticket (a docs or scope-only change) would trip this. REPORT it;
  let the operator decide.
- **Do NOT classify by parsing commit MESSAGE text for "Done report".** That
  is a lexical match on prose that any commit could contain. Classify by the
  PATHS each commit touches -- `git show --stat` / `git diff-tree --name-only`
  is structured data and is the authority here. Standing user directive:
  token/grammar, never lexical.
- **Do NOT use a wall-clock timeout alone** ("no land in N minutes = stalled").
  Legitimate tickets here run over an hour; T-1696 is explicitly a
  multi-session job. Time is not the signal; the commit/working-tree shape is.
- **Do NOT count ledger commits as progress and stop there.** That is exactly
  the bug: the current report treats any commit as liveness.

## Acceptance criteria

1. (MUST FAIL FIRST) A fixture worktree whose branch commits touch only
   `tickets/**` while `src/**` files are modified-but-uncommitted is reported
   as not-progressing. Fails today: every signal reports it healthy. Confirm
   `--check-repro` reads FAILED_AT_PARENT before the fix commit.
2. An agent that HAS committed source changes is STILL reported healthy
   (must-still-pass control). A detector that flags every working agent is
   worse than none -- it would train the operator to ignore it.
3. A legitimately ledger-only ticket (docs-only or scope-only work, with a
   CLEAN working tree) is NOT flagged. The uncommitted-source half of the
   condition is required, not optional.
4. Classification derives from commit-touched PATHS, never from commit message
   text.
5. Read-only: it reports, and never kills, restarts, or modifies an agent's
   worktree.

## Scope note

`scripts/fleet_status.py` is now carrying five separate items (T-2200, T-2213,
T-2222, T-2225, and this), which serializes all of them behind one lease. That
is worth stating out loud rather than discovering again: if the implementer
finds the file wants splitting first, say so -- T-2213 already covers
splitting `ticket_readiness`, whose 80-line body is also a live ARCH001
finding in the current floor.

## Drop reason
- 2026-08-16: PREMISE FALSIFIED by the subject agent's own testimony, before any implementer time was spent. I filed this claiming T-2215's agent spun for 90min on ledger churn. It did not: each of the 9 ledger commits followed a DISTINCT named gate finding it had just fixed (COV002 -> frob:ticket comments, SCOPE001 -> scope add, DUP002 -> merge duplicate tests, WIRE001 -> permanent waiver, TEST016/TEST018 -> a real 4th test class after its evidence killed 0/2 and 0/3 mutants). That is productive iteration, not a loop. Both of my proposed signals are wrong: (1) repeated 'Done report' commits are frob ticket done-report's OWN re-render after each fix, not the agent re-declaring done; (2) 'ledger-only commits + uncommitted source' is the NORMAL shape of an agent iterating through close-gate findings before committing -- T-2215 closed successfully and is landing now. A detector built to this spec would flag exactly this healthy agent, which acceptance criterion 2 forbids. No measured instance of a real spin exists, and I will not keep a ticket whose evidence I misread. The genuine lesson (recent-commit != progress) is real but I have no measured case, and filing on a hypothesis violates the evidence bar I hold agents to.
