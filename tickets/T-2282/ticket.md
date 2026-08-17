---
id: T-2282
title: 'Agents strand themselves ending a turn with a pending background task: the
  guard enumerates slow commands instead of catching the stranding (3 stalls this
  session)'
state: done
kind: bug
origin: human
created: '2026-08-17'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- .claude/hooks/frob-timeout-guard.py
- .claude/settings.json
- .claude/hooks/pending-background-guard.py
- tests/test_hook_frob_timeout_guard.py
- tests/test_hook_pending_background_guard.py
- docs/guides/claude-hooks.md
evidence_scope:
- tests/test_hook_pending_background_guard.py
- tests/test_hook_frob_timeout_guard.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: .claude/hooks/pending-background-guard.py
  reason: 'T-2282: widen scope to the new Stop hook, its tests, the extended timeout-guard
    tests, and the doc anchors both hooks'' frob:doc lines resolve against'
  actor: logan
  at: '2026-08-17'
- op: add
  glob: tests/test_hook_frob_timeout_guard.py
  reason: 'T-2282: widen scope to the new Stop hook, its tests, the extended timeout-guard
    tests, and the doc anchors both hooks'' frob:doc lines resolve against'
  actor: logan
  at: '2026-08-17'
- op: add
  glob: tests/test_hook_pending_background_guard.py
  reason: 'T-2282: widen scope to the new Stop hook, its tests, the extended timeout-guard
    tests, and the doc anchors both hooks'' frob:doc lines resolve against'
  actor: logan
  at: '2026-08-17'
- op: add
  glob: docs/guides/claude-hooks.md
  reason: 'T-2282: widen scope to the new Stop hook, its tests, the extended timeout-guard
    tests, and the doc anchors both hooks'' frob:doc lines resolve against'
  actor: logan
  at: '2026-08-17'
evidence:
- tests/test_hook_pending_background_guard.py::test_auto_backgrounded_task_with_no_resolution_is_blocked
- tests/test_hook_pending_background_guard.py::test_explicit_run_in_background_with_no_resolution_is_blocked
- tests/test_hook_pending_background_guard.py::test_resolved_via_completion_notification_is_not_blocked
- tests/test_hook_pending_background_guard.py::test_reentrant_stop_does_not_block_twice
- tests/test_hook_pending_background_guard.py::test_reentrant_stop_with_real_pending_task_does_not_block_twice
- tests/test_hook_pending_background_guard.py::test_no_background_task_normal_stop_is_not_blocked
- tests/test_hook_pending_background_guard.py::test_missing_transcript_file_fails_open
- tests/test_hook_pending_background_guard.py::test_malformed_stdin_fails_open
- tests/test_hook_pending_background_guard.py::test_single_event_described_by_both_start_patterns_is_not_self_resolved
- tests/test_hook_frob_timeout_guard.py::test_explicit_run_in_background_blocked_for_agent_regardless_of_command
- tests/test_hook_frob_timeout_guard.py::test_explicit_run_in_background_allowed_for_coordinator
- tests/test_hook_frob_timeout_guard.py::test_run_in_background_false_not_blocked_for_agent
- tests/test_hook_frob_timeout_guard.py::test_ticket_land_still_blocks_under_min_timeout
- tests/test_hook_frob_timeout_guard.py::test_ticket_done_report_still_blocks_under_min_timeout
- tests/test_hook_frob_timeout_guard.py::test_check_still_blocks_under_min_timeout
- tests/test_hook_frob_timeout_guard.py::test_test_verb_still_blocks_under_min_timeout
- tests/test_hook_frob_timeout_guard.py::test_prose_heredoc_mentioning_guarded_verb_is_not_blocked
- tests/test_hook_frob_timeout_guard.py::test_quoted_string_command_is_not_blocked
designated_repro_test: tests/test_hook_pending_background_guard.py::test_auto_backgrounded_task_with_no_resolution_is_blocked
acceptance:
- text: Establish and state with evidence whether the Stop payload exposes pending
    background tasks; if not, say so and fall back rather than fabricating a signal
  evidence:
  - tests/test_hook_pending_background_guard.py::test_auto_backgrounded_task_with_no_resolution_is_blocked
  - tests/test_hook_pending_background_guard.py::test_explicit_run_in_background_with_no_resolution_is_blocked
  - tests/test_hook_pending_background_guard.py::test_resolved_via_completion_notification_is_not_blocked
- text: 'An agent ending its turn with a background task it is waiting on is stopped
    and told what to do instead (fails today: marked complete, silently stalls)'
  evidence:
  - tests/test_hook_pending_background_guard.py::test_auto_backgrounded_task_with_no_resolution_is_blocked
  - tests/test_hook_pending_background_guard.py::test_explicit_run_in_background_with_no_resolution_is_blocked
  - tests/test_hook_pending_background_guard.py::test_reentrant_stop_does_not_block_twice
  - tests/test_hook_pending_background_guard.py::test_reentrant_stop_with_real_pending_task_does_not_block_twice
  - tests/test_hook_pending_background_guard.py::test_no_background_task_normal_stop_is_not_blocked
- text: Explicit run_in_background on a status/verification command is refused at
    PreToolUse, keyed on the structured parameter not a command-name pattern
  evidence:
  - tests/test_hook_pending_background_guard.py::test_auto_backgrounded_task_with_no_resolution_is_blocked
  - tests/test_hook_pending_background_guard.py::test_explicit_run_in_background_with_no_resolution_is_blocked
  - tests/test_hook_pending_background_guard.py::test_resolved_via_completion_notification_is_not_blocked
  - tests/test_hook_pending_background_guard.py::test_reentrant_stop_does_not_block_twice
  - tests/test_hook_pending_background_guard.py::test_reentrant_stop_with_real_pending_task_does_not_block_twice
  - tests/test_hook_pending_background_guard.py::test_no_background_task_normal_stop_is_not_blocked
  - tests/test_hook_pending_background_guard.py::test_missing_transcript_file_fails_open
  - tests/test_hook_pending_background_guard.py::test_malformed_stdin_fails_open
  - tests/test_hook_pending_background_guard.py::test_single_event_described_by_both_start_patterns_is_not_self_resolved
  - tests/test_hook_frob_timeout_guard.py::test_explicit_run_in_background_blocked_for_agent_regardless_of_command
- text: 'MUST-STILL-PASS: coordinator can still background a long measurement; T-2248''s
    four verbs still block; both recorded false-positive shapes still do not fire;
    report-and-stop remains reachable'
  evidence:
  - tests/test_hook_frob_timeout_guard.py::test_explicit_run_in_background_blocked_for_agent_regardless_of_command
  - tests/test_hook_frob_timeout_guard.py::test_explicit_run_in_background_allowed_for_coordinator
  - tests/test_hook_frob_timeout_guard.py::test_run_in_background_false_not_blocked_for_agent
  - tests/test_hook_frob_timeout_guard.py::test_ticket_land_still_blocks_under_min_timeout
  - tests/test_hook_frob_timeout_guard.py::test_ticket_done_report_still_blocks_under_min_timeout
  - tests/test_hook_frob_timeout_guard.py::test_check_still_blocks_under_min_timeout
  - tests/test_hook_frob_timeout_guard.py::test_test_verb_still_blocks_under_min_timeout
  - tests/test_hook_frob_timeout_guard.py::test_prose_heredoc_mentioning_guarded_verb_is_not_blocked
  - tests/test_hook_frob_timeout_guard.py::test_quoted_string_command_is_not_blocked
- text: State the residual gap -- if auto-backgrounding at 120s is only caught by
    the Stop hook, say so plainly
  evidence:
  - tests/test_hook_frob_timeout_guard.py::test_explicit_run_in_background_allowed_for_coordinator
  - tests/test_hook_frob_timeout_guard.py::test_run_in_background_false_not_blocked_for_agent
  - tests/test_hook_frob_timeout_guard.py::test_ticket_land_still_blocks_under_min_timeout
  - tests/test_hook_frob_timeout_guard.py::test_ticket_done_report_still_blocks_under_min_timeout
  - tests/test_hook_frob_timeout_guard.py::test_check_still_blocks_under_min_timeout
  - tests/test_hook_frob_timeout_guard.py::test_test_verb_still_blocks_under_min_timeout
  - tests/test_hook_frob_timeout_guard.py::test_prose_heredoc_mentioning_guarded_verb_is_not_blocked
  - tests/test_hook_frob_timeout_guard.py::test_quoted_string_command_is_not_blocked
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
# Agents strand themselves by ending a turn with a pending background task; the guard enumerates slow commands instead of catching the actual failure

## The failure mode, precisely

1. An agent runs a long command.
2. It becomes a background task -- either because the agent passed
   `run_in_background: true`, or because the harness AUTO-BACKGROUNDS any
   foreground Bash call at ~120s.
3. The agent's turn ends while that task is pending, expecting to be resumed
   when it completes.
4. It is not resumed. It is marked COMPLETE. Its remaining context is spent and
   its ticket stalls until a human-equivalent operator notices and nudges it.

Step 4 is the whole defect. The agent's belief -- "I'll be notified" -- is
reasonable and wrong.

## Measured: three stalls this session, all step 4

- **T-2239's agent** backgrounded `frob ticket work T-2239` and ended its turn
  reporting only "Waiting for the background task to complete (monitored)".
  Zero progress until nudged.
- **T-2256's first agent** stalled with "no progress for 600s (stream watchdog
  did not recover)" and had to be replaced; its 10 commits survived only
  because worktree commits do.
- **T-2268's agent** backgrounded a land-contention check and ended its turn
  waiting. This one was MY fault: my brief said "check `fleet_status` for LANDS
  IN FLIGHT before landing and WAIT if two or more are running." Telling an
  agent to wait is telling it to poll -- an agent cannot sleep cheaply, so it
  backgrounds a check and idles.

## Why the existing guard does not cover it

`.claude/hooks/frob-timeout-guard.py` denies a Bash call whose
`tool_input.timeout` is under `MIN_TIMEOUT_MS` (300000) when the command matches:

    frob +(ticket +(land|done-report|work|new)|check|test)

T-2248 extended that verb list precisely because of stalls -- and **the very
next stall used a command not on it** (`python3 scripts/fleet_status.py`). That
is the lesson: enumeration is the brittleness. The guard is chasing command
names when the failure has nothing to do with which command ran.

Worse, no PreToolUse guard can prevent the auto-background case at all. The
harness backgrounds at ~120s regardless of what the hook permitted, so a
command the guard approved can still strand the agent.

## The two levers that exist

Both are already wired in `.claude/settings.json` (`PreToolUse` on Bash x2,
`Stop` x2), so neither needs new plumbing:

**(a) Stop hook -- the real fix.** Refuse to let a turn end while a background
Bash task is pending, with a message telling the agent to either wait
synchronously in one foreground call or report-and-stop deliberately. This
catches BOTH paths, including auto-backgrounding, because it fires on the
stranding itself rather than on how the task was created.

**(b) PreToolUse -- secondary.** Deny an explicit `run_in_background: true` for
status/verification commands. `tool_input` already carries `run_in_background`
alongside the `command`/`timeout` fields the guard reads today, so this is a
structured check on the actual risky parameter -- not another name pattern.

## Do NOT fix it this way

- **Do NOT extend the verb list again.** That was T-2248, and the next stall
  bypassed it immediately with a non-frob command. Any fix whose correctness
  depends on enumerating slow commands will be bypassed the same way.
- **Do NOT ban backgrounding globally.** The coordinator legitimately backgrounds
  long measurements, and a blanket denial would break that. Scope the restriction
  to the agent context, or to the stranding condition, not to the capability.
- **Do NOT solve it in dispatch-brief wording.** That is the weakest tier and it
  has already failed measurably: I wrote "wait if two or more are running" and
  directly caused stall #3. A rule that must be recalled correctly by every
  agent on every dispatch is not enforcement.
- **Do NOT make the Stop hook block unconditionally on any pending task.** Some
  legitimately outlive a turn. The condition is a pending task the agent is
  WAITING ON, and the hook must not deadlock an agent that cannot proceed --
  report-and-stop has to remain reachable.

## Acceptance criteria

1. (MUST FIRST ESTABLISH FEASIBILITY) Determine whether the `Stop` payload
   exposes pending background tasks, and state the answer with evidence. The
   payload is known to carry `stop_hook_active` (see
   `.claude/hooks/diagnosis-nudge.py:26`). If pending-task state is NOT
   available, say so explicitly and fall back to (b) plus whatever detection is
   available -- do not fabricate a signal.
2. (MUST FAIL FIRST) An agent that ends its turn with a background task it is
   waiting on is stopped and told what to do instead. Fails today: it is marked
   complete and silently stalls.
3. An explicit `run_in_background: true` on a status/verification command is
   refused at PreToolUse, keyed on the structured parameter, not a command-name
   pattern.
4. MUST-STILL-PASS CONTROLS: the coordinator can still background a long
   measurement; the four verbs T-2248 guards still block under
   `MIN_TIMEOUT_MS`; both recorded false-positive shapes still do not fire (a
   prose heredoc mentioning a guarded verb, and a command carrying
   `uv run frob test` inside a quoted string); and an agent that legitimately
   cannot proceed can still report-and-stop without being blocked.
5. State the residual gap. If auto-backgrounding at 120s remains possible and
   only the Stop hook catches it, say so plainly rather than implying the class
   is closed.

## Scope note

`.claude/hooks/frob-timeout-guard.py` owns the PreToolUse half.
`.claude/settings.json` already registers two `Stop` hooks
(`diagnosis-nudge.py`, `dispatch-telemetry.py`) -- extend one or add a sibling,
and say which and why. NOTE: `.claude/hooks/*` in the REPO is the source of
truth; `~/.claude/hooks/*` are materialized copies. Edit the repo files.