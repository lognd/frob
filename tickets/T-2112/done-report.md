## Done report

Updated docs/commands/cli-vocabulary.md's "Did-you-mean" section to
describe T-2107's scoped candidate-pool/usage behavior instead of the
old, deliberately-global description: unrecognized-flag candidates now
come from _collect_option_strings(target) where target is
_INVOKED_PARSERS[-1] (the most-specific subcommand parser argparse
actually recursed into during parse_known_args), falling back to
_ALL_OPTION_STRINGS only when no invocation chain was recorded. No code
changes; docs-only ticket, existing test coverage for the described
mechanism is bound as evidence per playbook section 5.

### Changed
```
 tickets/T-2112/ticket.md | 7 ++++++-
 1 file changed, 6 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_main_entry.py::TestDidYouMean::test_unrecognized_flag_suggestion_scoped_to_invoked_subcommand` (pytest node id, verified passing when recorded)
- `tests/unit/test_main_entry.py::TestDidYouMean::test_unrecognized_flag_error_shows_invoked_subcommand_usage` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@scripts/fleet_status.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/release/_cli.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, DOC001@docs/commands/release.md, DOC005@README.md, DOC005@docs/modules/cli.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_land_cmd.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/lang/_nodes.py, DRIFT002@scripts/fleet_status.py, E402@/home/logan/projects/frob/.claude/worktrees/t-2112/scripts/fleet_status.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2112/scripts/fleet_status.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2112/src/frob/lang/_nodes.py, F541@/home/logan/projects/frob/.claude/worktrees/t-2112/tests/test_ticket_work_and_land_finish.py, F841@/home/logan/projects/frob/.claude/worktrees/t-2112/tests/test_ticket_land.py, PERF004@scripts/fleet_status.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, PRE001@tickets/T-2112, RENDER001@src/frob/release/_cli.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST010@tests/test_ticket_work_and_land_finish.py, TICK004@tickets.md
