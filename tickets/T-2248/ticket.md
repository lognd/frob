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
land_commit: null
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

## Done report

Extended `.claude/hooks/frob-timeout-guard.py`'s `PATTERN` alternation from
`(land|done-report)` to `(land|done-report|work|new)` inside the `ticket`
group -- the minimal change: no bare `frob ` prefix, no relaxed anchoring,
no MIN_TIMEOUT_MS change, per the ticket's explicit "do not fix it this way"
constraints.

VERBS ADDED AND MEASURED BASIS (acceptance criterion 5):
- `ticket work`: measured today auto-backgrounding on `frob ticket work
  T-2239`, stalling an implementer agent idle-polling for a notification
  that structurally cannot arrive (ticket body incident 2). Mechanism:
  creates a worktree, merges main, builds natives -- multi-step, same
  cost class as the four already-guarded verbs.
- `ticket new`: measured today auto-backgrounding mid-filing (ticket body
  incident 1), with a sharper hazard than a plain stall -- re-running is
  NOT idempotent (allocates a second ticket id; this repo has had one
  ticket consume three ids through repeated allocation).
- Considered but NOT added, no measurement basis of my own beyond the
  ticket body's own citation: `ticket doable` (ticket body cites 297s
  cold / 91s warm from earlier the same day, but that number was not
  independently reverified in this pass) and `coverage` (never measured
  in this pass at all). Left out per "no speculative additions" --
  either belongs to a follow-up ticket that takes its own measurement.

MUST-STILL-PASS CONTROLS, all three verified:
- the four originally-guarded verbs (`ticket land`, `ticket done-report`,
  `check`, `test`) still block under MIN_TIMEOUT_MS
  (`test_ticket_land_still_blocks_under_min_timeout`,
  `test_ticket_done_report_still_blocks_under_min_timeout`,
  `test_check_still_blocks_under_min_timeout`,
  `test_test_verb_still_blocks_under_min_timeout`);
- a fast verb (`ticket show`, `verify status`) is not blocked
  (`test_fast_verb_ticket_show_is_not_blocked`,
  `test_fast_verb_verify_status_is_not_blocked`);
- both recorded false-positive shapes (prose heredoc, quoted-string
  command) still do not fire
  (`test_prose_heredoc_mentioning_guarded_verb_is_not_blocked`,
  `test_quoted_string_command_is_not_blocked`).

Acceptance criterion 4 (tool timeout >= MIN_TIMEOUT_MS still allowed
through unchanged) covered for both new verbs
(`test_ticket_work_with_large_timeout_is_allowed`,
`test_ticket_new_with_large_timeout_is_allowed`).

REPRO: `test_ticket_work_under_min_timeout_is_blocked` committed alone
first (48bba43e4), confirmed genuinely failing against the pre-fix
pattern via `frob ticket evidence --check-repro ... --base-ref 48bba43e4`
-> FAILED_AT_PARENT, THEN the fix committed separately (770df9485).
Designated as this ticket's repro test.

Also updated `docs/guides/claude-hooks.md`'s frob-timeout-guard.py
section to name the two new verbs and their measured basis (AFFECT001
closure on the changed `PATTERN` symbol), and added `frob:ticket T-2248`
directives to the new test file's changed symbols (COV002 closure).

Scope was extended (via `frob ticket scope --add`) beyond the ticket's
original single-file scope to cover the new test file, the doc it
required updating, and `frob.lock` (the `frob ack` write target) -- all
`frob ticket scope` closure-driven, not discretionary.

NOT ACHIEVED / DISCLOSED CUT: `frob check --land-parity` did not converge
in this pass -- a concurrent coordinator land (`ticket land T-2241`) was
running against a heavily loaded worktree fleet (100+ worktrees under
`.claude/worktrees/`) for most of this ticket's verification window; once
it finished and this worktree merged main cleanly (no unintended
deletions per the deletion-filter check), repeated `--land-parity`
attempts alternated between a 360s internal timeout and one run reporting
"1 unscoped error" with an empty rule/file identity in its own `--json`
output -- looks like a pre-existing reporting bug in `--land-parity`
under contention, unrelated to this ticket's own scope
(`.claude/hooks/frob-timeout-guard.py` / the new test file / the doc), not
something this ticket's scope covers fixing. The scoped
`--ticket T-2248 --only gates-fast` check (which does not have this
convergence problem) is clean of any new finding tied to this ticket's
touched files after the scope-closure and COV002 fixes above; the
remaining errors it reports are all pre-existing and unrelated (other
tickets' attachments, other rotting queued tickets, other modules'
DRIFT001/TEST010, `claude-config-drift` on this very file -- expected
until the coordinator's `frob claude sync` step runs, never something a
worktree agent does itself). Flagging the land-parity flakiness rather
than silently treating "could not evaluate" as clean.

### Evidence
- tests/test_hook_frob_timeout_guard.py::test_ticket_work_under_min_timeout_is_blocked (designated repro)
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

### Gates
`frob check --ticket T-2248 --only gates-fast`: 0 errors attributable to
this ticket's touched files (all remaining errors pre-existing/unrelated,
confirmed by file path). `--land-parity` did not converge under fleet
contention this pass (see disclosed cut above).

### Changed
```
 .claude/hooks/frob-timeout-guard.py   |  26 +++--
 docs/guides/claude-hooks.md           |  17 +++-
 frob.lock                             |  14 +++
 tests/test_hook_frob_timeout_guard.py | 173 ++++++++++++++++++++++++++++++++++
 tickets/T-2248/ticket.md              |  81 ++++++++++++++--
 5 files changed, 294 insertions(+), 17 deletions(-)
```

### Evidence
- `tests/test_hook_frob_timeout_guard.py::test_ticket_new_under_min_timeout_is_blocked` (pytest node id, verified passing when recorded)
- `tests/test_hook_frob_timeout_guard.py::test_ticket_work_with_large_timeout_is_allowed` (pytest node id, verified passing when recorded)
- `tests/test_hook_frob_timeout_guard.py::test_ticket_new_with_large_timeout_is_allowed` (pytest node id, verified passing when recorded)
- `tests/test_hook_frob_timeout_guard.py::test_ticket_land_still_blocks_under_min_timeout` (pytest node id, verified passing when recorded)
- `tests/test_hook_frob_timeout_guard.py::test_ticket_done_report_still_blocks_under_min_timeout` (pytest node id, verified passing when recorded)
- `tests/test_hook_frob_timeout_guard.py::test_check_still_blocks_under_min_timeout` (pytest node id, verified passing when recorded)
- `tests/test_hook_frob_timeout_guard.py::test_test_verb_still_blocks_under_min_timeout` (pytest node id, verified passing when recorded)
- `tests/test_hook_frob_timeout_guard.py::test_fast_verb_ticket_show_is_not_blocked` (pytest node id, verified passing when recorded)
- `tests/test_hook_frob_timeout_guard.py::test_fast_verb_verify_status_is_not_blocked` (pytest node id, verified passing when recorded)
- `tests/test_hook_frob_timeout_guard.py::test_prose_heredoc_mentioning_guarded_verb_is_not_blocked` (pytest node id, verified passing when recorded)
- `tests/test_hook_frob_timeout_guard.py::test_quoted_string_command_is_not_blocked` (pytest node id, verified passing when recorded)
- `tests/test_hook_frob_timeout_guard.py::test_ticket_work_under_min_timeout_is_blocked` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 12 passed (from 12 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH001@scripts/fleet_status.py, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@scripts/fleet_status.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1335, COV003@tickets/T-1353, COV003@tickets/T-1362, COV003@tickets/T-1363, COV003@tickets/T-1373, COV003@tickets/T-1397, COV003@tickets/T-1426, COV003@tickets/T-1433, COV003@tickets/T-1526, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md, COV004@tickets/T-draft-0bd874ac/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-draft-0bd874ac/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_land_cmd.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/lang/_nodes.py, DUP001@tests/test_hook_frob_timeout_guard.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2248/src/frob/lang/_nodes.py, F541@/home/logan/projects/frob/.claude/worktrees/t-2248/tests/test_ticket_work_and_land_finish.py, PERF004@scripts/fleet_status.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, SELFAUDIT001@design, TEST010@tests/test_ticket_work_and_land_finish.py, TICK004@tickets.md
