---
id: T-5477
title: 'ci_report/ghio: unusable against this repo''s real xdist CI logs (T-2982 command-surface
  gap)'
state: queued
kind: bug
origin: agent
created: '2026-09-24'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: v0.534.0
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while draining CI run 35951365410 (dev 9e0c89bb19) as the single CI
drain agent (T-2982's missing command-surface leaf).

frob.ghio.view_run runs `gh run view <id> --json status,conclusion,jobs`;
the gh CLI in this environment refuses that field set outright ("Unknown
JSON field: jobs" -- available fields do not include jobs at all in this
gh version), so view_run (and therefore ci_report.build_run_report) Errs
for every run here. Routing around it (build a JobSummary by hand from
`gh api repos/<owner>/<repo>/actions/runs/<run>/jobs`, call
ci_report.build_job_report directly) works, but the natural documented
entry point is unusable as shipped -- ghio needs either a fallback to the
jobs-list REST route when `gh run view --json jobs` is refused, or its own
positive-control test against a gh version that refuses this field set.

Bigger gap: even routed that way, ci_report.parse_pytest_log NEVER
recovers a result for this repo's own real CI logs. Its _RESULT_LINE /
_SUMMARY_LINE regexes assume vanilla pytest's own end-of-run "=== N
failed, M passed in Ts ===" / "FAILED <nodeid> - <reason>" lines at column
zero. This repo's CI runs pytest with -n auto --dist=loadgroup (xdist)
and tests/conftest.py's own pytest_sessionfinish hook writes a CUSTOM
summary instead (`SUITE-RESULT: exitstatus=N collected=N failed=N`
followed by one `SUITE-RESULT-FAILED: <nodeid> (failed)` line per
failure) specifically BECAUSE xdist's interleaved output cannot be
trusted positionally -- ci_report.py's own module docstring describes
this exact reasoning but the parser was never updated to consume the
SUITE-RESULT lines it describes owning. On top of that, `gh api
.../actions/jobs/<id>/logs` prefixes every line with an ISO timestamp,
which independently defeats the ^-anchored regexes even where literal
pytest text does appear (e.g. inside nested subprocess-captured output
from tests/system/test_scaffold_dx.py, which is NOT the outer run's own
summary and must not be read as one).

Net effect measured directly: build_job_report returns outcome=
"not_recoverable" for every real completed CI job in this repo today,
silently -- exactly the false-negative class the module's own docstring
says it exists to prevent. All 19 ubuntu / 18 macos failures for this
drain were extracted by hand (regex over SUITE-RESULT-FAILED lines after
stripping the gh timestamp prefix), not via this module.

Suggested fix: parse_pytest_log should recognize SUITE-RESULT /
SUITE-RESULT-FAILED lines (with or without a leading ISO-timestamp gh-log
prefix) as an alternate, equally authoritative source of truth alongside
vanilla pytest's own summary, since this repo's own test suite always
runs under xdist and always emits them.
