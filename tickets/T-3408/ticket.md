---
id: T-3408
title: sync-claude-config from a stale worktree silently reverts a sibling agent's
  in-flight fix to the shared global hooks
state: queued
kind: bug
origin: human
created: '2026-08-29'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
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
`sync-claude-config.py`, run from inside an agent worktree, overwrites the
SHARED global `~/.claude/` copies with that worktree's version -- silently
destroying any in-flight edit a sibling agent has made to the same global file.

MEASURED 2026-08-29. Series EQ ran the sync from its own worktree and clobbered
Series ER's in-flight fix to `~/.claude/hooks/frob-suggest.py`. EQ happened to
diff before continuing, noticed the regression, restored the file from
series-er's worktree, and then avoided re-syncing for the rest of its run. The
recovery was luck and an alert agent, not a property of the tool.

WHY THIS IS STRUCTURAL, not an agent mistake. Every worktree carries its own
copy of `.claude/hooks/*`. The global `~/.claude/` tree is materialized FROM
those copies, and it is shared by every process on the machine -- all agents,
the coordinator, and any other session. So the sync is a many-writers/one-
destination operation with no coordination:

  - Worktree A's copy is whatever main looked like when A branched.
  - Worktree B lands a hook fix.
  - Worktree A runs the sync and reverts B's fix globally, with no diff, no
    warning, and no record.
  - Every agent on the box now runs the reverted hook.

The blast radius is larger than one file, because hooks GATE OTHER AGENTS' TOOL
CALLS. A reverted hook changes what every concurrent agent is allowed to do, and
the symptom appears in a different session than the cause.

This is adjacent to the known rule "edit the source in the frob repo, not the
materialized ~/.claude copy" but it is a DIFFERENT failure: here the source was
edited correctly, and the sync from a STALE sibling source undid it.

WHAT TO DECIDE, explicitly. There is a real argument for more than one answer,
so state the choice and the reasoning rather than just implementing one:
  (a) Refuse to sync from a worktree at all -- only main may materialize the
      global copy. Simplest and safest; costs an agent the ability to test a
      hook change in-place.
  (b) Refuse when the worktree's source is behind main for the files being
      synced. Preserves in-place testing, needs an ancestry check per file.
  (c) Diff-and-confirm: show what would be overwritten and require an explicit
      flag when the sync would REVERT content that exists in the destination
      but not in the source. This is the narrowest rule that would have caught
      the measured incident.
Do NOT add a lock and call it solved -- serializing two writers still lets the
stale one win, which is exactly what happened here.

CHECK FIRST, do not assume: confirm whether the sync already has any staleness
or diff guard that simply failed, versus having none at all. "Nothing enforces
this" is a claim about code; grep for the enforcement before asserting it is
missing.

MUST-FIRE FIXTURE:   syncing from a worktree whose source is behind the global
                     destination, where the destination carries content the
                     source lacks, is refused or flagged.
MUST-STAY-QUIET:     syncing an ordinary forward change is unaffected.

ACCEPTANCE
- Existing guards measured and reported before any new one is added.
- The chosen policy stated with reasoning, not silently implemented.
- Both fixtures committed.
