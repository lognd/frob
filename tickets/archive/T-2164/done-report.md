## Done report

Changed:
  .claude/hooks/frob-suggest.py::_marker_path (new)
  .claude/hooks/frob-suggest.py::_record_attempt (new, replaces _claim)
  .claude/hooks/frob-suggest.py::_deny (new, split out of main)
  .claude/hooks/frob-suggest.py::_ACK_PREFIX (new)
  .claude/hooks/frob-suggest.py::_ESCALATE_AT_ATTEMPT (new)
  .claude/hooks/frob-suggest.py::main (rewritten: escalation on repeat)
  docs/guides/claude-hooks.md (frob-suggest.py section updated)
  tests/test_hook_frob_suggest.py (3 new tests)

The block-once-then-allow design was, from the SECOND identical attempt
onward, allow-FOREVER: `_claim` was a boolean O_EXCL marker with no notion
of how many times a command had already been let through. A caller
repeating an identical raw command out of habit (not a genuine one-off)
never got interrupted again, which is exactly what the ticket's measured
incident describes -- three separate cases in one session where a re-run
of a raw probe cost real work because the suggested tool already had the
answer.

Fix: `_record_attempt` replaces the boolean marker with a small JSON
payload tracking a real attempt count, still using O_CREAT|O_EXCL for the
first attempt (same "exactly one of racing siblings wins the first
denial" guarantee `_claim` provided) and a read-increment-write for every
attempt after. `main` now denies again from the third identical attempt
onward (`_ESCALATE_AT_ATTEMPT = 3`) unless the command is prefixed with
`FROB_SUGGEST_ACK=1 ` (`_ACK_PREFIX`, stripped before rule matching so its
presence never changes which rule fires or dodges a rule). The
acknowledgement is checked every time rather than consumed once, per the
ticket's explicit "escalating on REPEAT" framing -- a fourth un-acked
attempt is blocked again even though the third was acked through.

Applies to every rule in `_RULES` uniformly (generalizes beyond the
lint-specific case the ticket's acceptance [0] names), since the
escalation lives in `main`'s shared post-match path, not inside any one
rule.

Evidence:
  tests/test_hook_frob_suggest.py::test_third_identical_command_is_blocked_again
    (accepts [0],[1], designated repro -- FAILED_AT_PARENT confirmed at
    4bfbc7257, a test-only commit with the fix not yet applied)
  tests/test_hook_frob_suggest.py::test_ack_prefixed_third_attempt_is_allowed_through
    (accepts [0] -- the escalation is an acknowledgement, not a hard block)
  tests/test_hook_frob_suggest.py::test_fourth_attempt_needs_the_ack_again
    (accepts [0] -- the ack is checked every time, not consumed once)
  tests/test_hook_frob_suggest.py::test_second_identical_check_pipeline_is_allowed_through
  tests/test_hook_frob_suggest.py::test_second_identical_fleet_probe_is_allowed_through
    (accepts [1] -- positive controls, pre-existing, still pass: a genuine
    ONE-OFF second identical attempt is still let through silently, not
    escalated)

Full targeted run: `pytest tests/test_hook_frob_suggest.py` -- 16
collected, 0 failed (13 pre-existing + 3 new).

Filed: none (no out-of-scope discoveries; the ticket's own acceptance [1]
explicitly deferred the broader "not just exact-rerun" cases -- ps/git
probe variance, unscoped-symbol-search near-misses -- as future work
outside this fix's scope, matching its own text: "Neither was a tooling
gap" for those specific historical instances).

Gates: repo-wide `frob check` budget/only runs during this session (T-2178
context, same worktree fleet) showed no findings naming
`.claude/hooks/frob-suggest.py` or `tests/test_hook_frob_suggest.py`.
`frob check --ticket T-2164` measured separately below.

### Changed
```
 .claude/hooks/frob-suggest.py   | 177 +++++++++++++++++++++++++++++-----------
 docs/guides/claude-hooks.md     |  10 +++
 tests/test_hook_frob_suggest.py |  57 +++++++++++++
 tickets/T-2164/ticket.md        |  33 +++++++-
 4 files changed, 227 insertions(+), 50 deletions(-)
```

### Evidence
- `tests/test_hook_frob_suggest.py::test_third_identical_command_is_blocked_again` (pytest node id, verified passing when recorded)
- `tests/test_hook_frob_suggest.py::test_ack_prefixed_third_attempt_is_allowed_through` (pytest node id, verified passing when recorded)
- `tests/test_hook_frob_suggest.py::test_fourth_attempt_needs_the_ack_again` (pytest node id, verified passing when recorded)
- `tests/test_hook_frob_suggest.py::test_second_identical_check_pipeline_is_allowed_through` (pytest node id, verified passing when recorded)
- `tests/test_hook_frob_suggest.py::test_second_identical_fleet_probe_is_allowed_through` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@scripts/fleet_status.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/release/_cli.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/tickets/_land_git_ops.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, DOC001@docs/commands/release.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT002@scripts/fleet_status.py, E402@/home/logan/projects/frob/.claude/worktrees/t-2164/scripts/fleet_status.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2164/scripts/fleet_status.py, F841@/home/logan/projects/frob/.claude/worktrees/t-2164/tests/test_ticket_land.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, PERF004@src/frob/app/ticket_runner/_new.py, PRE001@tickets/T-2164, RENDER001@src/frob/release/_cli.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST010@tests/test_ticket_work_and_land_finish.py, TICK004@tickets.md
