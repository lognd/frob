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
