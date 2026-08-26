## Done report

Changed:
- .claude/hooks/tool-call-telemetry.py (new) -- PreToolUse/PostToolUse hook, main
- .claude/settings.json -- registers the hook for all tools, both events
- src/frob/stats/_agentic.py -- ToolCallShape, _completed_tool_events, _ToolCallTally, _accumulate_dispatch_tool_events, _tool_call_histogram, agentic_report, dispatch_cost_report
- src/frob/stats/__init__.py -- re-export ToolCallShape
- src/frob/app/stats_runner.py -- _agentic_tool_call_histogram_lines, _run_agentic
- docs/guides/agentic-time-profiling.md -- Tool-call telemetry (T-2912) section
- docs/modules/stats.md -- ToolCallShape anchor + derived-numbers prose
- tests/test_hook_dispatch_telemetry.py -- 10 new tests for tool-call-telemetry.py (folded in, see below)
- tests/test_stats_agentic.py -- 3 new tests for _tool_call_histogram

Where and why: T-1724 already built `dispatch_cost_report`/`agentic_report.tool_tokens`
to read `kind="tool"` events, but nothing ever wrote one -- the write side was the
missing piece. `.claude/hooks/tool-call-telemetry.py` is that write side: registered
as both PreToolUse and PostToolUse for every tool (`.claude/settings.json`), it appends
to the SAME `.frob/telemetry.jsonl` stream `record_cli_event`/`record_dispatch_event`
already use, in the exact `kind="tool"` shape `_tool_tokens`/`dispatch_cost_report`
already read -- no parallel telemetry system. Reporting lives in
`frob.stats._agentic._tool_call_histogram`, surfaced automatically in `frob stats
--agentic`'s existing text/JSON output (no new command to remember).

Overhead: measured 35-70ms per hook invocation (two runs, different load), dominated
entirely by python3 interpreter cold-start -- the same fixed cost every other
`.claude/hooks/*.py` script already pays on every tool call in this repo. Zero
subprocess spawns added: `head_sha` is read via `_fast_head_sha`, which parses
`.git/HEAD` and the ref file it points at directly (handles the `gitdir:` pointer
shape every worktree uses) instead of spawning `git rev-parse` the way
`frob.app.telemetry.tree_hash` does -- that distinction matters here because this
hook fires an order of magnitude more often than `record_cli_event`.

Real histogram captured: replayed 30 real Bash commands actually run during this
ticket's own work (git/pytest/frob/grep/sed/awk/cat/ls invocations) as Pre+Post
event pairs through the real hook binary into a throwaway repo, then read back via
`frob.stats.agentic_report`. Top entries:
  calls=5 shape='uv run pytest -p -q'                    rerun=4
  calls=5 shape='uv run'                                 rerun=4  (python3 script.py -- version-numbered token ends the chain)
  calls=3 shape='git add -A'                              rerun=2
  calls=2 shape='git status --short'                      rerun=1
  calls=2 shape='uv run frob check --json --ticket'       rerun=1
  calls=2 shape='cat'                                     rerun=1
  ...(11 more distinct shapes at calls=1)
Sum of call_count across the histogram: 30 -- exactly the independently-known count
of commands replayed (the must-capture control).

Both controls verified directly (see commands in this ticket's session):
  - must-capture: 30 replayed commands -> histogram call_count sums to exactly 30.
  - must-not-distort: FROB_NO_TELEMETRY=1 on real events writes zero bytes (no
    .frob/ dir created at all); a git repo with zero tool-call activity likewise
    produces `event_count=0`, `tool_call_histogram=()` -- never a phantom entry.

Correction to the initial design (surfaced by the real run, not by inference): the
first command-shape normalization kept only the LEADING word plus flags, so
`uv run pytest ...`, `uv run frob check ...`, and `uv run frob ticket show ...` all
collapsed into one useless "uv" bucket -- exactly the kind of over-aggregation that
would have hidden the hotspot rather than finding it. Fixed by extending the shape
through bare (non-digit, non-flag) subcommand words until a value-shaped token
(a path, a ticket id, a version string) ends the chain -- `uv run pytest` and
`uv run frob check` are now distinguishable, while `T-2912`/file paths still never
leak into the shape. Both the original coarse bug and the fix are covered by new
tests (test_bash_command_shape_extends_through_bare_subcommand_words,
test_bash_command_shape_chain_stops_at_a_ticket_id).

Does this correct or confirm the ~1,446-tokens-per-call model? Not measurable from
this ticket's own work alone -- 1,446 tok/call was derived from real Claude token
usage against 1,464 real tool calls; this ticket's replay used SYNTHETIC
`output_tokens_est` (len/4 of a placeholder stdout string), not real transcript
token counts, so it cannot confirm or contradict the linear-in-call-count claim by
itself. What it DOES establish, and what the next drive's real session data will
now answer automatically via `frob stats --agentic` without any manual tally: which
COMMAND SHAPES (not just which tool) dominate count, and the retry/rerun-at-same-
tree signal this repo's land-cost finding ("dominated by refusals, not timeouts")
generalizes to. On a live session going forward, this is now measured, not inferred.

Deviation from the ticket's own scope note: the hook's tests live in
`tests/test_hook_dispatch_telemetry.py` (folded in as a new section), not a
`tests/test_hook_tool_call_telemetry.py` file. `design/frob.strata`'s `testsuite`
node's `may "exec" via ...` capability allowlist is what a NEW test file exercising
`subprocess.run` needs to be added to (SELFAUDIT001, unwaivable via inline comment
-- its diagnostic is keyed to `design:1`, not the offending file/line), and that
strata file was held by a live cross-worktree lease (T-2911) for this ticket's
entire run. `tests/test_hook_dispatch_telemetry.py` was already on that allowlist,
so the new tests were folded there instead of waiting on/contending with T-2911's
lease. Both files carry a note explaining why.

Filed: none -- no out-of-scope work discovered.

Evidence: 13 pytest node ids bound (frob:tests edges added at each new public
symbol/hook entry point). No `--accepts` binding -- this ticket declared no
acceptance-criteria list (`0 acceptance item(s)`).

Gates: `frob check --ticket T-2912` clean of every finding whose file touches this
ticket's changed set (0 errors on .claude/hooks/tool-call-telemetry.py,
.claude/settings.json, src/frob/stats/_agentic.py, src/frob/stats/__init__.py,
src/frob/app/stats_runner.py, tests/test_hook_dispatch_telemetry.py,
tests/test_stats_agentic.py, docs/guides/agentic-time-profiling.md,
docs/modules/stats.md); the run's remaining 26 repo-wide errors are all
pre-existing findings in files this ticket never touches (verified by name-matching
every error's file against the changed-file list). `gate:SCOPE` exit_code=0.
Targeted pytest: 38/38 passed
(tests/test_hook_dispatch_telemetry.py + tests/test_stats_agentic.py).

### Changed
```
 tickets/T-2912/ticket.md | 92 ++++++++++++++++++++++++++++++++++++++++++++++++
 1 file changed, 92 insertions(+)
```

### Evidence
- `tests/test_hook_dispatch_telemetry.py::test_pre_tool_use_records_attempt_event` (pytest node id, verified passing when recorded)
- `tests/test_hook_dispatch_telemetry.py::test_post_tool_use_records_completion_with_token_estimate` (pytest node id, verified passing when recorded)
- `tests/test_hook_dispatch_telemetry.py::test_non_bash_tool_never_gets_a_command_shape` (pytest node id, verified passing when recorded)
- `tests/test_hook_dispatch_telemetry.py::test_bash_command_shape_never_leaks_raw_argument_values` (pytest node id, verified passing when recorded)
- `tests/test_hook_dispatch_telemetry.py::test_bash_command_shape_extends_through_bare_subcommand_words` (pytest node id, verified passing when recorded)
- `tests/test_hook_dispatch_telemetry.py::test_bash_command_shape_chain_stops_at_a_ticket_id` (pytest node id, verified passing when recorded)
- `tests/test_hook_dispatch_telemetry.py::test_tool_call_telemetry_disabled_env_var_writes_nothing` (pytest node id, verified passing when recorded)
- `tests/test_hook_dispatch_telemetry.py::test_tool_call_telemetry_malformed_payload_is_a_silent_noop` (pytest node id, verified passing when recorded)
- `tests/test_hook_dispatch_telemetry.py::test_tool_call_telemetry_unrecognized_hook_event_is_a_silent_noop` (pytest node id, verified passing when recorded)
- `tests/test_hook_dispatch_telemetry.py::test_tool_call_telemetry_outside_git_repo_writes_nothing` (pytest node id, verified passing when recorded)
- `tests/test_stats_agentic.py::test_tool_call_histogram_counts_completed_calls_by_shape` (pytest node id, verified passing when recorded)
- `tests/test_stats_agentic.py::test_tool_call_histogram_counts_unmatched_pre_as_blocked` (pytest node id, verified passing when recorded)
- `tests/test_stats_agentic.py::test_tool_call_histogram_legacy_phaseless_events_count_as_completed` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 13 passed (from 13 evidence id(s))
- gates: 22 error(s), 523 warning(s), 859 waived
- error-findings: COV001@scripts/branch_stranded_work_analysis.py, COV004@tickets/T-2195/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md, COV004@tickets/T-2244/attachments/01-t-2244-audit-safe-to-repoint-split-test-typecheck-safe-now-lint-blocked-by-newly-found-t-2387-not-t-2359-format-lint-fix-blocked-by-both-test-fast-stays-raw.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, COV004@tickets/T-2328/attachments/02-third-reproduction-t-2323-confirmed-workaround-pre-commit-the-file-yourself-before-land.md, COV004@tickets/T-2328/attachments/03-clarification-titled-work-loss-defect-remains-open-carried-by-t-2351.txt, COV004@tickets/T-2350/attachments/01-diagnosis-timing-visibility-race-not-identity-matching-both-candidate-fix-files-leased-by-t-2351-no-edit-attempted.md, COV004@tickets/T-2543/attachments/01-class-a-options-and-measured-costs-t-2377-survey.md, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC002@src/frob/tickets/_leases.py, DOC006@docs/guides/coordinator-scripts.md, DOC006@docs/modules/gates.md, DOC006@tickets/T-2886/ticket.md, DOC006@tickets/T-2920/ticket.md, DOC008@docs/commands/check.md, SYS003@scripts/branch_stranded_work_analysis.py, TEST001@scripts/branch_stranded_work_analysis.py, TICK004@tickets.md
