---
id: T-2248
title: 'frob-timeout-guard misses ticket work and ticket new: both auto-backgrounded
  today, one stalled an agent, one risked a duplicate id allocation'
state: done
kind: bug
origin: human
created: '2026-08-16'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- .claude/hooks/frob-timeout-guard.py
- tests/test_hook_frob_timeout_guard.py
- docs/guides/claude-hooks.md
- frob.lock
evidence_scope:
- tests/test_hook_frob_timeout_guard.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_hook_frob_timeout_guard.py
  reason: T-2248 repro/regression coverage for the PATTERN extension
  actor: logan
  at: '2026-08-16'
- op: add
  glob: docs/guides/claude-hooks.md
  reason: 'T-2248 closure: doc anchor updated for the PATTERN extension'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: frob.lock
  reason: 'T-2248: frob ack on PATTERN writes into frob.lock'
  actor: logan
  at: '2026-08-16'
evidence:
- tests/test_hook_frob_timeout_guard.py::test_ticket_new_under_min_timeout_is_blocked
- tests/test_hook_frob_timeout_guard.py::test_ticket_work_with_large_timeout_is_allowed
- tests/test_hook_frob_timeout_guard.py::test_ticket_new_with_large_timeout_is_allowed
- tests/test_hook_frob_timeout_guard.py::test_ticket_land_still_blocks_under_min_timeout
- tests/test_hook_frob_timeout_guard.py::test_ticket_done_report_still_blocks_under_min_timeout
- tests/test_hook_frob_timeout_guard.py::test_check_still_blocks_under_min_timeout
- tests/test_hook_frob_timeout_guard.py::test_test_verb_still_blocks_under_min_timeout
- tests/test_hook_frob_timeout_guard.py::test_fast_verb_ticket_show_is_not_blocked
- tests/test_hook_frob_timeout_guard.py::test_fast_verb_verify_status_is_not_blocked
- tests/test_hook_frob_timeout_guard.py::test_prose_heredoc_mentioning_guarded_verb_is_not_blocked
- tests/test_hook_frob_timeout_guard.py::test_quoted_string_command_is_not_blocked
- tests/test_hook_frob_timeout_guard.py::test_ticket_work_under_min_timeout_is_blocked
designated_repro_test: tests/test_hook_frob_timeout_guard.py::test_ticket_work_under_min_timeout_is_blocked
acceptance:
- text: 'A Bash call running ''uv run frob ticket work T-XXXX'' under MIN_TIMEOUT_MS
    is blocked (fails today: pattern lacks ''work'')'
  evidence:
  - tests/test_hook_frob_timeout_guard.py::test_ticket_work_under_min_timeout_is_blocked
- text: Same for 'frob ticket new'
  evidence:
  - tests/test_hook_frob_timeout_guard.py::test_ticket_new_under_min_timeout_is_blocked
  - tests/test_hook_frob_timeout_guard.py::test_ticket_work_with_large_timeout_is_allowed
  - tests/test_hook_frob_timeout_guard.py::test_ticket_new_with_large_timeout_is_allowed
  - tests/test_hook_frob_timeout_guard.py::test_ticket_land_still_blocks_under_min_timeout
  - tests/test_hook_frob_timeout_guard.py::test_ticket_done_report_still_blocks_under_min_timeout
  - tests/test_hook_frob_timeout_guard.py::test_check_still_blocks_under_min_timeout
  - tests/test_hook_frob_timeout_guard.py::test_test_verb_still_blocks_under_min_timeout
  - tests/test_hook_frob_timeout_guard.py::test_fast_verb_ticket_show_is_not_blocked
  - tests/test_hook_frob_timeout_guard.py::test_fast_verb_verify_status_is_not_blocked
  - tests/test_hook_frob_timeout_guard.py::test_prose_heredoc_mentioning_guarded_verb_is_not_blocked
  - tests/test_hook_frob_timeout_guard.py::test_quoted_string_command_is_not_blocked
  - tests/test_hook_frob_timeout_guard.py::test_ticket_work_under_min_timeout_is_blocked
- text: 'MUST-STILL-PASS: the four currently-guarded verbs still block; a fast verb
    is still not blocked; both recorded false-positive shapes (prose heredoc, quoted-string
    command) still do not fire'
  evidence:
  - tests/test_hook_frob_timeout_guard.py::test_ticket_new_under_min_timeout_is_blocked
  - tests/test_hook_frob_timeout_guard.py::test_ticket_work_with_large_timeout_is_allowed
  - tests/test_hook_frob_timeout_guard.py::test_ticket_new_with_large_timeout_is_allowed
  - tests/test_hook_frob_timeout_guard.py::test_ticket_land_still_blocks_under_min_timeout
  - tests/test_hook_frob_timeout_guard.py::test_ticket_done_report_still_blocks_under_min_timeout
  - tests/test_hook_frob_timeout_guard.py::test_check_still_blocks_under_min_timeout
  - tests/test_hook_frob_timeout_guard.py::test_test_verb_still_blocks_under_min_timeout
  - tests/test_hook_frob_timeout_guard.py::test_fast_verb_ticket_show_is_not_blocked
  - tests/test_hook_frob_timeout_guard.py::test_fast_verb_verify_status_is_not_blocked
  - tests/test_hook_frob_timeout_guard.py::test_prose_heredoc_mentioning_guarded_verb_is_not_blocked
  - tests/test_hook_frob_timeout_guard.py::test_quoted_string_command_is_not_blocked
- text: A matching command with tool timeout >= MIN_TIMEOUT_MS is still allowed through
    unchanged
  evidence:
  - tests/test_hook_frob_timeout_guard.py::test_ticket_new_under_min_timeout_is_blocked
  - tests/test_hook_frob_timeout_guard.py::test_ticket_work_with_large_timeout_is_allowed
  - tests/test_hook_frob_timeout_guard.py::test_ticket_new_with_large_timeout_is_allowed
  - tests/test_hook_frob_timeout_guard.py::test_ticket_land_still_blocks_under_min_timeout
  - tests/test_hook_frob_timeout_guard.py::test_ticket_done_report_still_blocks_under_min_timeout
  - tests/test_hook_frob_timeout_guard.py::test_check_still_blocks_under_min_timeout
  - tests/test_hook_frob_timeout_guard.py::test_test_verb_still_blocks_under_min_timeout
  - tests/test_hook_frob_timeout_guard.py::test_fast_verb_ticket_show_is_not_blocked
  - tests/test_hook_frob_timeout_guard.py::test_fast_verb_verify_status_is_not_blocked
  - tests/test_hook_frob_timeout_guard.py::test_prose_heredoc_mentioning_guarded_verb_is_not_blocked
  - tests/test_hook_frob_timeout_guard.py::test_quoted_string_command_is_not_blocked
- text: State which verbs were added and the measured basis for each; no speculative
    additions
  evidence:
  - tests/test_hook_frob_timeout_guard.py::test_ticket_work_under_min_timeout_is_blocked
threat: null
component: null
anchor: false
anchor_reason: null
---
# frob-timeout-guard covers four slow commands and misses `ticket work` and `ticket new`, which stall exactly the same way

## The guard, and its blind spot

`.claude/hooks/frob-timeout-guard.py` blocks a Bash call whose tool-level
`timeout` is under 300000ms when the command matches:

    PATTERN = re.compile(
        r"(?:^|[;&|(]\s*|\buv +run +)(?:timeout +\d+ +)?"
        r"frob +(ticket +(land|done-report)|check|test)\b",
        re.M,
    )

So it guards `ticket land`, `ticket done-report`, `check`, and `test`. It does
NOT guard `ticket work`, `ticket new`, `ticket doable`, or `coverage` -- all of
which routinely exceed the 120s foreground cap. `ticket work` creates a
worktree, merges main, and builds natives. `ticket doable` was measured at
297s cold / 91s warm earlier today. `ticket new` contends for the ledger
allocator lock behind in-flight lands.

The guard's own REASON text names the failure precisely -- "can exceed the 120s
foreground cap and get auto-backgrounded -- the known stall pattern" -- and
that is exactly what the unguarded commands do.

## Measured, both today, both uncaught

1. **`frob ticket new`** (coordinator) exceeded 120s mid-filing and was
   auto-backgrounded. The danger here is specific: a killed or re-run
   `ticket new` allocates a SECOND ticket id, and this repo has already had one
   ticket consume three ids through repeated allocation. I had to wait it out
   rather than re-run, precisely because re-running is not idempotent.

2. **`frob ticket work T-2239`** (implementer agent) was backgrounded, and the
   agent then ended its turn idle-polling for it -- reporting only "Waiting for
   the background task to complete (monitored)". It made no progress until
   nudged. That is a full agent stall on a high-priority ticket.

Both are the identical shape the guard already blocks for four other verbs.

## Why a brief is not the fix

I DID brief that agent with the foreground-plus-timeout rule. It still
backgrounded the command, because my brief illustrated the rule with
`frob check` and the agent was running `frob ticket work`. A rule that must be
generalised correctly at the moment of use is not enforcement -- the guard
exists in the first place because this class of instruction does not stick.
The guard fires on the command; extend the command list.

## Do NOT fix it this way

- **Do NOT match a bare `frob ` prefix and guard everything.** Most frob verbs
  are fast (`ticket show`, `ticket list`, `verify status`, `ticket scope`), and
  forcing a 600000ms tool timeout on every one of them would train the operator
  to pass a huge timeout reflexively -- which defeats the guard everywhere,
  including where it matters. Enumerate the slow verbs.
- **Do NOT relax the command-position anchoring.** The pattern deliberately
  matches only at start-of-line, after a shell connector, or after `uv run`,
  and `strip_quoted()` runs first. Its own comments record two prior false
  positives: a coordinator memory-checkpoint heredoc, and a command carrying
  `uv run frob test` inside a quoted string. Any change must preserve both.
  Standing user directive: token/grammar, never lexical -- the anchoring IS
  that discipline, do not trade it for breadth.
- **Do NOT raise MIN_TIMEOUT_MS.** 300000 is not the problem; coverage is.

## Acceptance criteria

1. (MUST FAIL FIRST) A Bash call running `uv run frob ticket work T-XXXX` with
   a tool timeout under MIN_TIMEOUT_MS is blocked. Fails today: the pattern
   does not include `work`.
2. Same for `frob ticket new`.
3. MUST-STILL-PASS CONTROLS, all three:
   - the four currently-guarded verbs still block (`ticket land`,
     `ticket done-report`, `check`, `test`);
   - a fast verb (e.g. `frob ticket show`, `frob verify status`) is still NOT
     blocked;
   - the two recorded false-positive shapes still do not fire -- a heredoc
     mentioning a guarded verb in prose, and a command carrying
     `uv run frob test` inside a quoted string.
4. Any command matching with a tool timeout >= MIN_TIMEOUT_MS is still allowed
   through unchanged.
5. State which verbs you added and the measured basis for each -- do not add a
   verb speculatively.

## Scope note

`.claude/hooks/frob-timeout-guard.py` is the SOURCE; `~/.claude/hooks/*` are
materialized copies. Edit the repo file, never the materialized one.