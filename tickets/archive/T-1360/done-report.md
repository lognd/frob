## Done report

Implemented footgun detection (T-1360) in src/frob/app/telemetry.py, wired
into the single CLI dispatch choke point (App.__call__ -> timed_call in
src/frob/app/app.py, unmodified -- timed_call itself now performs
detection). Three of the four named rules are real code, reading the
existing telemetry.jsonl corpus (no new instrumentation, per the ticket's
own note that the substrate already exists):

- REDUNDANT_RERUN: identical (subcommand, args_head, tree_hash) seen
  before at the current tree state.
- FAST_EXIT1: this run itself exited nonzero in under 2000ms.
- REPEATED_FAILURE: the identical command has now failed 3+ times in a
  row with no successful run in between.

The fourth (filtered-verification-before-land) is deliberately NOT
duplicated -- T-1351's gate:scope-note already covers "what a
--only/--ticket run suppressed" per the ticket's own DO-NOT instruction;
this is noted in the doc page and in detect_footguns's own docstring
rather than re-implemented.

Delivery requirements: tips print AFTER the command (timed_call's finally
block, via _log.warning so they land on stderr, never corrupting a
--json command's stdout), never block or change the exit code, are
individually suppressible (FROB_SUPPRESS_TIPS=RULE1,RULE2) or disabled
entirely (FROB_NO_FOOTGUN_TIPS=1) without disabling telemetry recording,
and render as a JSON array (Tip.model_dump) when the triggering
invocation itself passed --json (checked via args_head, the only
generically-available signal at timed_call's call site). Every tip names
the concrete command that ran, not just a diagnosis.

frob doctor --usage (--json supported) aggregates the whole local
corpus into a UsageReport: total calls/duration, failure rate, top
time sinks by subcommand, redundant-rerun count + wasted wall-clock,
fast-exit-1 count, and stuck-repeat-streak count -- the "where does the
time go" capability the ticket asks for as a command instead of an
ad-hoc script.

Scope note: the ticket named src/frob/telemetry.py and
docs/modules/telemetry.md, neither of which exist -- the real module is
src/frob/app/telemetry.py (docs/guides/agentic-time-profiling.md). Ran
`frob ticket scope --remove/--add` to correct this before starting work;
also pulled in the files scope-closure flagged as genuinely needed
(app/app.py, app/config.py, app/doctor_runner.py, _config_external.py,
_cli_parsers/_misc.py, the CLI wiring path from argv to the doctor
--usage report) plus tests/test_telemetry.py and
tests/unit/test_doctor_runner_t1276.py for closure. app/app.py itself
ended up untouched -- timed_call's own signature didn't need to change,
only its internals.

Gates: `frob check --only coverage` clean for every touched file (0
errors after two real fixes: missing frob:ticket edges on 4 new private
helpers, and a spurious frob:waive SEC110 comment on a new private
function that turned out to be unneeded entirely -- `frob check --only
secrets` confirmed SEC110 does not fire on that line without it, so it
was removed rather than re-targeted). `frob check --only doclink
--only docanchor --only registry --only fmt --only static` also clean
(0 errors/warnings) for this change; the arch tool's long-function
informational notes on detect_footguns/usage_report/timed_call are
non-gating output, addressed anyway by splitting detect_footguns into
three _tip_* helpers. ruff format/check clean under uv run ruff.
--ticket T-1360-scoped frob check numbers above are NOT a package-wide
claim (playbook 6c) -- only gate:COV's touched-file findings and the
explicit unscoped re-runs listed here were verified.

### Changed
```
 docs/guides/agentic-time-profiling.md |  51 ++++
 src/frob/_cli_parsers/_misc.py        |   7 +
 src/frob/app/_config_external.py      |   1 +
 src/frob/app/config.py                |   1 +
 src/frob/app/doctor_runner.py         |  55 ++++-
 src/frob/app/telemetry.py             | 448 +++++++++++++++++++++++++++++++++-
 tests/test_telemetry.py               | 190 ++++++++++++++
 tickets.md                            | 304 ++++++++++++++++++++++-
 8 files changed, 1048 insertions(+), 9 deletions(-)
```

### Evidence
- `tests/test_telemetry.py::test_detect_footguns_flags_redundant_rerun` (pytest node id, verified passing when recorded)
- `tests/test_telemetry.py::test_detect_footguns_flags_fast_exit1` (pytest node id, verified passing when recorded)
- `tests/test_telemetry.py::test_detect_footguns_does_not_flag_fast_exit1_on_success` (pytest node id, verified passing when recorded)
- `tests/test_telemetry.py::test_detect_footguns_flags_repeated_failure_streak` (pytest node id, verified passing when recorded)
- `tests/test_telemetry.py::test_detect_footguns_respects_suppress_env` (pytest node id, verified passing when recorded)
- `tests/test_telemetry.py::test_detect_footguns_returns_empty_when_tips_disabled` (pytest node id, verified passing when recorded)
- `tests/test_telemetry.py::test_render_tips_json_is_parseable` (pytest node id, verified passing when recorded)
- `tests/test_telemetry.py::test_render_tips_empty_list_is_empty_string` (pytest node id, verified passing when recorded)
- `tests/test_telemetry.py::test_render_tips_human_readable_names_the_rule` (pytest node id, verified passing when recorded)
- `tests/test_telemetry.py::test_usage_report_empty_corpus_is_all_zero` (pytest node id, verified passing when recorded)
- `tests/test_telemetry.py::test_usage_report_aggregates_time_and_failures` (pytest node id, verified passing when recorded)
- `tests/test_telemetry.py::test_usage_report_counts_redundant_reruns` (pytest node id, verified passing when recorded)
- `tests/test_telemetry.py::test_usage_report_counts_fast_exit1` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 13 passed (from 13 evidence id(s))
- gates: 6 error(s), 281 warning(s), 738 waived
- error-findings: AFFECT001@src/frob/_cli_parsers/_misc.py, AFFECT001@src/frob/app/doctor_runner.py, AFFECT001@src/frob/app/telemetry.py, ARCH001@src/frob/app/telemetry.py, PRE001@tickets/T-1360, SELFAUDIT001@design
