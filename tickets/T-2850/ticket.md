---
id: T-2850
title: 'root-write-guard cannot see a pre-worktree agent: both its signals are set
  by frob ticket work, so an agent editing the root before creating its worktree is
  indistinguishable from a human'
state: queued
kind: bug
origin: agent
created: '2026-08-22'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- .claude/hooks/root-write-guard.py
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
## Measured: two fleet-blocking incidents in one session

Two dispatched agents edited the PRIMARY CHECKOUT directly, each blocking
every other agent's land until I noticed and issued a manual recovery recipe:

- ~20:40 -- 307 insertions across `src/frob/tickets/_land.py`,
  `docs/modules/tickets-landing.md`, `tests/test_ticket_land.py`
- ~00:33 -- 278 insertions across `src/frob/gates/__init__.py`,
  `src/frob/process/_reap.py`, `tests/unit/test_process_reap.py`

In both cases `.claude/worktrees/*<ticket>*` did not exist -- the agent had
never created a worktree. Both briefs said "NEVER edit the shared root" in
capitals. The instruction is not sufficient.

`root-write-guard.py` IS registered (`.claude/settings.json:34`, PreToolUse
on Write/Edit/NotebookEdit/Bash) and IS the current repo copy, not a stale
materialized one. It did not fire in either case.

## Root cause: the discriminator cannot see a pre-worktree agent

From the hook's own docstring:

    `_is_agent_context` fires when EITHER `FROB_AGENT` is truthy OR the
    worktree fact independently holds ... A coordinator or human shell
    carries neither var -- `frob agent env` is only ever invoked for a
    dispatched worktree agent's own shell -- so neither disjunct fires and
    the guard stays silent, closing acceptance criterion 2.

Both signals are set by `frob agent env`, which runs as part of `frob ticket
work` -- i.e. AFTER the worktree exists. An agent between dispatch and
`ticket work` carries neither var and is therefore, to this guard,
indistinguishable from the coordinator.

That window is precisely when the damage occurs: the agent reads the ticket,
starts implementing, and only later (or never) creates its worktree.

The guard is not buggy against its stated contract. Its CONTRACT is wrong:
it assumes an agent always already has agent context. Acceptance criterion 2
("never fires for the coordinator or a human") is what forces the
default-allow, and no env-var pairing can separate a pre-worktree agent from
a human, because they are environmentally identical.

## Required shape: invert the default

Default-DENY writes to the primary checkout, with an explicit positive
marker for the small set of contexts legitimately allowed to write there --
rather than default-ALLOW with agent detection that cannot see the dangerous
case.

Candidate allowlist, to be established by measurement rather than assumed:
- `FROB_LAND_INTERNAL=1` (already an exemption; land owns those writes)
- ledger paths `tickets.md` / `tickets/**` (already exempt for the `frob
  ticket` CLI's auto-commit machinery)
- an explicit coordinator marker, opt-in and set once per coordinator shell

The asymmetry justifies the inversion: a false block costs one agent one
confused turn and a clear error message. A false allow costs the ENTIRE
FLEET its ability to land until a human notices. Tonight it cost two
multi-hour stalls.

Note the hook's own comment that "a guard that blocks legitimate commands
gets disabled by [users]" -- that risk is real and argues for a precise,
self-explaining refusal message naming the exact recovery, NOT for keeping
default-allow.

## Positive controls, both directions

- A dispatched agent with NEITHER `FROB_AGENT` nor `FROB_WORKTREE` set,
  writing to a primary-checkout source path, is REFUSED. This is the case
  that fails today and is the whole point.
- A coordinator shell with the explicit marker still writes freely.
- An agent writing inside its OWN leased worktree is never touched.
- `tickets/**` and `FROB_LAND_INTERNAL=1` writes still pass.
- The hook still FAILS OPEN on stdin parse error / missing git / non-repo
  cwd -- a hook that crashes a turn is worse than one that misses.

## Recovery recipe that worked, worth documenting in the refusal message

    git diff HEAD -- <paths> > /tmp/rescue.patch   # verify non-empty
    cd <worktree> && git apply --3way /tmp/rescue.patch
    # verify content present, THEN:
    cd <root> && git checkout -- <paths>

Use the bare `git checkout -- <path>` form (restores from index). The
`git checkout <branch> -- <path>` form copies the whole file and can
silently revert fixes landed since divergence.
