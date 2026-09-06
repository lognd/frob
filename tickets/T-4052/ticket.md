---
id: T-4052
title: frob ticket close succeeds with the ticket's code still uncommitted, so a ticket
  can read done on main with no implementation (3 agents, one session)
state: queued
kind: bug
origin: human
created: '2026-09-06'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_close_cmd.py
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
`frob ticket close` SUCCEEDS WHILE THE TICKET'S ACTUAL CODE IS STILL UNCOMMITTED
IN THE WORKTREE. Three independent agents hit this in one session; two of them
came within one command of landing a ticket that would have read `done` on main
with none of its code present.

MEASURED, FROM OUR OWN FLEET, not a consumer report:

  - Series FY, working T-4018, reported: "TWICE in this session, `frob ticket
    close` followed by `frob ticket land` almost shipped a closed ticket with its
    actual code diff still uncommitted in the worktree (only the ledger/
    done-report commits were made). Caught both times only by explicitly diffing
    main against the worktree HEAD before landing -- rather than trusting `close`
    succeeding as proof the code was committed."
  - I independently observed the same state while triaging that agent: its
    branch carried `chore(tickets): close T-4018` (4aea6a1a9) while
    `git -C <worktree> status --porcelain` showed three modified files:
        M src/frob/dup/_cache.py
        M src/frob/graph/cache.py
        M tests/unit/test_dup_cache.py
  - A third agent (Series FP, T-3936) left verified work committed on a branch
    that never landed at all -- a different failure with the same consequence: a
    ticket's state and its code disagreeing.

WHY close IS THE RIGHT PLACE TO CATCH IT. close is the moment the system records
that the work is finished. It already verifies a great deal at that moment --
evidence resolves, acceptance criteria bind, a Done report exists. It does not
verify the one thing those all describe: THAT THE WORK EXISTS AS COMMITTED CODE.
So every other close-time check is validating claims about a diff that may not be
in any commit.

THE FAILURE IS SILENT AND THE RECOVERY IS EXPENSIVE. Nothing warns; close prints
success. If the land then proceeds, main gets a done ticket with no
implementation -- and this repo has a recorded prior instance of exactly that
outcome (a timed-out land wrote state=done with zero code reaching main). The
only reason it did not happen three times today is that agents were explicitly
briefed to verify lands against git rather than the ledger.

THE FIX: at close, if the ticket's declared scope contains files with
uncommitted modifications in the worktree, REFUSE and name them. A warning is not
enough -- the whole point is that the operator believes the work is done, so a
warning will be read as noise at exactly the moment attention is lowest.

DETERMINE THESE BEFORE IMPLEMENTING:
  - Is there a legitimate close-with-dirty-worktree case? A ticket whose work is
    genuinely all ledger (a docs-only or triage ticket) may have nothing to
    commit -- that must still close cleanly. Scope the refusal to files IN the
    ticket's declared scope, so an unrelated dirty file does not block.
  - Does close already know the worktree path? It writes to the worktree ledger,
    so it probably does; confirm rather than plumbing a new parameter.
  - Interaction with T-3958: close is not mirrored to main, and that ticket is
    already about close's relationship to the primary checkout. A dirty-worktree
    check must not assume it runs where main lives.

DO NOT fix this by making `land` catch it instead. Land already refuses for many
reasons and this repo has measured that land refusals are the dominant cost of
the whole workflow; catching it at close is earlier, cheaper, and closer to the
operator's intent. Catching it at BOTH is acceptable; catching it only at land is
not.

MUST-FIRE FIXTURE: closing a ticket with uncommitted modifications to files in
its own declared scope is refused, naming those files.
MUST-STAY-QUIET: (a) a ticket whose scope files are all committed closes
normally; (b) an unrelated dirty file outside the ticket's scope does not block
the close.
THIRD FIXTURE: a ledger-only ticket with nothing to commit still closes.

ACCEPTANCE
- Refusal (not warning) on uncommitted in-scope changes at close time.
- The ledger-only case explicitly preserved and tested.
- Checked against T-3958 so the fix does not assume it runs against main.
- All three fixtures committed.