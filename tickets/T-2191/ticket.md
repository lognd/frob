---
id: T-2191
title: REDUNDANT_RERUN asserts 'this run could not have produced a different result'
  from the repo tree hash alone, but verbs like claude sync --check read state outside
  the repo and legitimately change verdict
state: done
kind: bug
origin: human
created: '2026-08-16'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/telemetry.py
- tests/test_telemetry.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_telemetry.py
  reason: add coverage for the external-state REDUNDANT_RERUN fix
  actor: logan
  at: '2026-08-16'
- op: add
  glob: docs/guides/agentic-time-profiling.md
  reason: document the new home-config state digest fold-in
  actor: logan
  at: '2026-08-16'
- op: add
  glob: docs/modules/stats.md
  reason: close pre-existing SCOPE002 gaps in telemetry.py's declared scope
  actor: logan
  at: '2026-08-16'
- op: add
  glob: design/frob.strata
  reason: close pre-existing SCOPE002 gaps in telemetry.py's declared scope
  actor: logan
  at: '2026-08-16'
- op: add
  glob: src/frob/telemetry/__init__.py
  reason: close pre-existing SCOPE002 gaps in telemetry.py's declared scope
  actor: logan
  at: '2026-08-16'
- op: add
  glob: src/frob/app/doctor_runner.py
  reason: close pre-existing SCOPE002 gaps in telemetry.py's declared scope
  actor: logan
  at: '2026-08-16'
- op: remove
  glob: design/frob.strata
  reason: revert -- design/frob.strata pulls in a 159-warning transitive closure unrelated
    to this ticket's telemetry.py fix
  actor: logan
  at: '2026-08-16'
- op: remove
  glob: src/frob/telemetry/__init__.py
  reason: revert -- design/frob.strata pulls in a 159-warning transitive closure unrelated
    to this ticket's telemetry.py fix
  actor: logan
  at: '2026-08-16'
- op: remove
  glob: src/frob/app/doctor_runner.py
  reason: revert -- design/frob.strata pulls in a 159-warning transitive closure unrelated
    to this ticket's telemetry.py fix
  actor: logan
  at: '2026-08-16'
- op: remove
  glob: docs/modules/stats.md
  reason: revert -- making the new helper private avoids the doc-closure pull entirely
  actor: logan
  at: '2026-08-16'
- op: remove
  glob: docs/guides/agentic-time-profiling.md
  reason: revert -- making the new helper private avoids the doc-closure pull entirely
  actor: logan
  at: '2026-08-16'
evidence:
- tests/test_telemetry.py::test_redundant_rerun_not_flagged_when_home_claude_config_changed
- tests/test_telemetry.py::test_redundant_rerun_still_flags_when_nothing_changed_at_all
designated_repro_test: tests/test_telemetry.py::test_redundant_rerun_not_flagged_when_home_claude_config_changed
acceptance:
- text: 'Reproduced live: ''frob claude sync --check'' reported 1 drifted; ''frob
    claude sync'' then wrote ~/.claude/refs/agent-playbook.md; the next ''frob claude
    sync --check'' emitted REDUNDANT_RERUN claiming ''nothing has changed since --
    this run could not have produced a different result'' and then reported ''6 file(s)
    in sync''. The verdict changed. src/frob/app/telemetry.py:489 keys the rule on
    (subcommand, args_head, tree_hash) where tree_hash covers the REPO tree only,
    while this verb''s inputs live in ~/.claude. This test MUST fail against current
    main.'
  evidence:
  - tests/test_telemetry.py::test_redundant_rerun_not_flagged_when_home_claude_config_changed
  - tests/test_telemetry.py::test_redundant_rerun_still_flags_when_nothing_changed_at_all
- text: 'Derive the answer from what the verb actually READS, not from a repo-wide
    hash: a verb whose inputs are not covered by tree_hash must be excluded from the
    rule, or the rule must incorporate that verb''s own input digest. Do NOT fix this
    by softening the message wording to ''may not have changed'' -- the value of REDUNDANT_RERUN
    is that it is a definite claim, and a hedged version is noise everyone learns
    to ignore. Do NOT hardcode a name list of exempt subcommands; that rots the moment
    a verb gains an out-of-repo input.'
  evidence:
  - tests/test_telemetry.py::test_redundant_rerun_not_flagged_when_home_claude_config_changed
  - tests/test_telemetry.py::test_redundant_rerun_still_flags_when_nothing_changed_at_all
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## Done report

`REDUNDANT_RERUN` keyed solely on `(subcommand, args_head, tree_hash)`
where `tree_hash` covers the repo tree only -- wrong for a verb like
`frob claude sync --check` whose real input also lives under `~/.claude`.
Reproduced live and via a new test: `--check` reports drifted, `sync`
writes `~/.claude/refs/*`, and the next `--check` used to claim "nothing
has changed since" -- false, because `~/.claude` had.

Fix: `_home_config_state_hash()` (private, `src/frob/app/telemetry.py`)
digests every regular file's `(relpath, size, mtime_ns)` under
`~/.claude`, excluding Claude Code's OWN well-known runtime/session-state
subdirectories (`_HOME_CLAUDE_RUNTIME_STATE_DIRS`: `projects`, `todos`,
`shell-snapshots`, `logs`, `ide`, `statsig`, `history`, `__pycache__` --
these churn every turn of every session regardless of any `frob` verb,
and including them made the very first version of this fix flaky against
this session's own live `~/.claude` activity, caught by re-running the
pre-existing `test_detect_footguns_flags_redundant_rerun` test
repeatedly). `record_cli_event` now stores `home_config_hash` alongside
`tree_hash` on every recorded event; `_tip_redundant_rerun` and
`_redundant_rerun_totals` both require BOTH digests to match before
calling a re-run redundant.

This generalizes by WHERE a verb's out-of-repo input lives (under
`~/.claude`, this repo's one existing materialized-copy target), not by
WHICH verb it is -- no hardcoded subcommand exemption list, so a future
verb reading/writing under the same directory is automatically covered.
Explicitly NOT a complete fix for every conceivable out-of-repo input (a
verb reading some other external path entirely is still not covered) --
disclosed in `_tip_redundant_rerun`'s own docstring rather than claimed
away. The message itself is UNCHANGED (still a definite "nothing has
changed" claim, never softened to "may not have changed") -- the fix
makes the claim CORRECT more often, it does not hedge it.

Repro (confirmed FAILING against the true parent commit, not just current
main, via `frob ticket evidence T-2191 --check-repro ... --base-ref
fa3944649` which reported `FAILED_AT_PARENT`, then designated): a
`REDUNDANT_RERUN` tip fired even though `~/.claude` content changed
between two identical `claude sync --check` invocations. After the fix,
the same scenario produces no `REDUNDANT_RERUN` tip; a genuinely
unchanged case (both digests identical) still fires it, proven by
`test_redundant_rerun_still_flags_when_nothing_changed_at_all` (must not
blunt the detector into never firing).

Changed:
- src/frob/app/telemetry.py::_HOME_CLAUDE_RUNTIME_STATE_DIRS (new)
- src/frob/app/telemetry.py::_home_config_state_hash (new, private)
- src/frob/app/telemetry.py::record_cli_event (adds `home_config_hash`
  field to every recorded event)
- src/frob/app/telemetry.py::_tip_redundant_rerun (matches on
  `home_config_hash` too, not just `tree_hash`)
- src/frob/app/telemetry.py::_redundant_rerun_totals (same key extension,
  for `usage_report`'s own redundant-rerun accounting)

Evidence:
- tests/test_telemetry.py::test_redundant_rerun_not_flagged_when_home_claude_config_changed
  (designated repro: FAILED_AT_PARENT at fa3944649, --check-repro
  confirmed before designation)
- tests/test_telemetry.py::test_redundant_rerun_still_flags_when_nothing_changed_at_all

Verification:
- `uv run pytest tests/test_telemetry.py -o addopts="" -q` -> 37 passed
  (full file, no regressions), re-run 3x for the two REDUNDANT_RERUN
  tests specifically to confirm no flakiness against this session's own
  live `~/.claude` activity.
- `uv run frob check --ticket T-2191 --only coverage --only scope --only
  prework`: gate:COV has zero findings attributable to this change (the
  new symbol is private, so COV001/COV005/doc-closure never engage); the
  remaining COV006/COV007 findings are pre-existing, unrelated (other
  files' private-symbol doc/reachability debt). gate:SCOPE reports
  SCOPE002 against telemetry.py's PRE-EXISTING public symbols (`iso_now`,
  `redact_command`, `tree_hash`, etc.) whose doc anchors already lived in
  docs/guides/agentic-time-profiling.md and docs/modules/stats.md before
  this ticket touched anything -- this closure debt is inherent to the
  ticket's original declared scope (`src/frob/app/telemetry.py` alone)
  and predates this diff; chasing it fully would pull design/frob.strata
  and src/frob/stats/__init__.py into scope (measured 159 scope-closure
  warnings from design/frob.strata alone), an unrelated multi-file
  expansion this bug-kind ticket's own scope does not license. Disclosed
  here rather than silently worked around.

Filed: T-2192 (already filed by the coordinator against T-2177's own
scope-plausibility check missing the real T-2157/T-2173 mis-scoping
shape) -- taken up next in this same worktree.

Gates: `frob check --ticket T-2191 --only coverage --only scope --only
prework` -- COV clean for this change's own touched symbols; SCOPE002
pre-existing debt disclosed above, not newly introduced.

### Changed
```
 src/frob/app/telemetry.py | 141 ++++++++++++++++++++++++++++++++++++++++++++--
 tests/test_telemetry.py   |  75 ++++++++++++++++++++++++
 tickets/T-2191/ticket.md  |  75 ++++++++++++++++++++++--
 3 files changed, 282 insertions(+), 9 deletions(-)
```

### Evidence
- `tests/test_telemetry.py::test_redundant_rerun_not_flagged_when_home_claude_config_changed` (pytest node id, verified passing when recorded)
- `tests/test_telemetry.py::test_redundant_rerun_still_flags_when_nothing_changed_at_all` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, DOC011@docs/design/gate-semantics-classification.md, DRIFT001@src/frob/app/ticket_runner/_land_cmd.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2177/src/frob/app/ticket_runner/_land_cmd.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, SELFAUDIT001@design, TEST010@tests/test_ticket_work_and_land_finish.py, TICK004@tickets.md
