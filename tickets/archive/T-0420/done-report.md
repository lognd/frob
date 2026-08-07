## Done report

Split `frob check`'s single monolithic `gates` line into named per-family
stages plus a trailing summary (T-0420). `_run_gates`/`_gates_success_result`
in `frob.check._python` now group `run_gates`'s violations/waived by rule
family (`_rule_family`: the alpha prefix before the first digit, e.g.
`COV001` -> `COV`, `PII010` -> `PII`) and emit one `gate:<FAMILY>`
`ToolResult` per family plus a trailing `gate-summary` `ToolResult`
carrying the overall totals and the existing per-gate timing blob,
replacing the single `gates` line that used to bury both behind one
combined count. `--delta` still narrows both the per-family lines and the
summary identically (the delta note, when present, is its own
`gate:delta` line). Also (same ticket): pre-summary WARNING/ERROR log
lines on stderr (PII010/SEC110/module-policy warnings, etc.) now go
through a `_ColorizedLevelFormatter` wrapped around the stderr
`StreamHandler`(s) for the duration of a non-`--json` check run
(`_colorized_stderr_logs`), resolved once via `should_color(sys.stderr)`
so a piped/non-TTY run stays byte-plain -- consistent with the final
pass/FAIL summary's coloring instead of printing plain while the summary
was colored.

Verified by eye: `frob check --type python --only gates` under a real TTY
(`script`) now prints a `pass`/`FAIL` line per family (`gate:ARCH`,
`gate:COV`, `gate:DRIFT`, `gate:PERF`, `gate:PII`, `gate:REF`, `gate:REL`,
`gate:SEC`, `gate:TEST`, `gate:WALK`) followed by one `gate-summary` line
with totals + the timing blob, each colored green/red by pass/FAIL.
Updated `tests/unit/test_check.py`'s three call sites that asserted a
single `.tool == "gates"` result and one `tests/system/test_cli_check.py`
grep on the `"[gates]"` diagnostic tag to match the new
`list[ToolResult]`/`"[gate:"` shape -- the underlying `--delta` filtering
behavior these tests exercise is unchanged, only the reporting shape.

### Changed
```
 src/frob/app/check_runner.py          | 271 ++++++++++++++++++++++++++++++++--
 src/frob/app/config.py                |   8 +
 src/frob/check/_python.py             | 127 ++++++++++++++--
 tests/system/test_cli_check.py        |   8 +-
 tests/unit/test_app_runners_batch6.py |  89 +++++++++++
 tests/unit/test_check.py              |  23 ++-
 tickets.md                            |  31 +++-
 7 files changed, 517 insertions(+), 40 deletions(-)
```

### Evidence
- `tests/unit/test_check.py::TestSummarySeverityHonesty::test_warn_only_gate_summary_splits_errors_and_warnings` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestRunGatesDelta::test_no_baseline_falls_back_to_full_set_with_warning` (pytest node id, verified passing when recorded)
