---
id: T-2487
title: add a post-Bash root-cleanliness detector for agent context (complementary
  to T-2481's guard)
state: queued
kind: feature
origin: human
created: '2026-08-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- .claude/hooks/
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
A fourth root-dirtying incident occurred during T-2481's own work (fresh
evidence from the coordinator): another agent's Bash cwd silently reset
to the primary checkout and it edited/appended there. This one was
caught FAST -- the agent ran `git status` immediately afterward, saw the
dirt within a minute, and reverted with `git checkout --` before
anything was staged or committed. Contrast the three incidents T-2481
fixed, all caught LATE, at land time, via a DirtyMain refusal naming
files the agent did not recognise.

That timing difference is the useful data point: detection at the
moment of the write is strictly better than refusal inferred from shell
text, and it sidesteps the whole "Bash write targets are not a declared
field" problem T-2481 had to work around.

PROPOSED FIX SHAPE: a PostToolUse hook (or a lightweight periodic check)
in agent context that runs `git status --porcelain` against the primary
checkout immediately after a Bash tool call and REPORTS (does not
refuse) if it finds unexpected dirt outside the ticket's own scope --
surfacing it to the agent in the same turn, before a commit can happen,
rather than only at the next `frob ticket land`.

This is a detector, not a guard: it has no "block legitimate work on a
guess" failure mode (T-2481's acceptance 4 concern) because it never
refuses anything -- it only shortens the feedback loop from "next land"
to "next tool call". It composes with T-2481's Bash-matcher guard (which
still refuses the two narrow shapes it can positively identify) and with
the complementary idea of pushing the check into `frob`'s own
ticket-mutating verbs (T-2481 declined that as the PRIMARY fix to keep
scope narrow, but it remains a good idea for a future ticket).

Filed by T-2481 per its Done report -- out of scope for that ticket
(different mechanism: PostToolUse detection, not PreToolUse inference)
but a strong complementary follow-up given the fourth incident happened
during T-2481's own dispatch window.
