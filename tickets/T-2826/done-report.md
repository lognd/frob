## Done report

Changed:
- src/frob/strata/__init__.py (waiver only, comment added)
- src/frob/strata/_ast.py (waiver only, comment added)
- src/frob/strata/_audit.py (waiver only, comment added)
- src/frob/strata/_compliance.py (waiver only, comment added)
- src/frob/strata/_effects.py (waiver only, comment added)
- src/frob/strata/_elaborate.py (waiver only, comment added)
- src/frob/strata/_host_isolation.py (waiver only, comment added; real seam identified but blocked -- see below)
- src/frob/strata/_infra.py (waiver only, comment added)
- src/frob/strata/_mode_conformance.py (waiver only, comment added)
- src/frob/strata/_threat.py (waiver only, comment added)
- src/frob/app/_check_chunking.py (real split: --stamp-baseline half moved out, 979 -> 770 lines)
- src/frob/app/_check_chunking_baseline.py (new file, ~250 lines: the moved --stamp-baseline cluster)

Per-file disposition:

- __init__.py: pure re-export surface (zero top-level defs/classes, one
  import block per submodule + one __all__ list) -- no logic to seam.
- _ast.py: 41 frozen pydantic AST classes mirroring the Rust parser's JSON
  shape one-for-one, one surface grammar the elaborator treats as a whole.
- _audit.py, _threat.py, _compliance.py: strata obligation-catalog phase
  modules (already phase-split at the package level: _threat.py = phases
  A-C, _compliance.py = phase F) -- each is one catalog family whose
  per-check helpers share one violation model and one aggregator.
- _effects.py: three capability-effect checks sharing one via-glob/
  via-symbol matching substrate -- same shared-helper non-seam shape
  T-2829's _new.py/_verify.py waivers established.
- _elaborate.py, _infra.py: single-vocabulary elaborator pipelines
  (std.trust, std.infra) -- one linear pipeline per file, same
  orchestrator shape as check_runner.py/sys_runner.py's T-1651 precedent.
- _mode_conformance.py: one conformance proof aggregating per-mode
  violation helpers sharing one observation model.
- _host_isolation.py: a REAL seam exists here (three independent checks:
  lateral/vertical/movement isolation, each with its own helper cluster,
  sharing only the violation model) -- NOT split under this ticket because
  this module carries via-scoped capability grants in design/frob.strata,
  and this repo has a live incident record (T-2729's own selfconform split
  needed a via-list update when code moved between files) showing that
  moving code between strata-adjacent files can require a via-declaration
  update that needs its own dedicated, careful review pass, not a batch
  LARGE001 judgment call. Filed T-2844 (real id) to do that split properly.
- src/frob/app/_check_chunking.py: a REAL seam, split -- confirmed via
  `git grep` BEFORE splitting that every external caller
  (check_runner.py, _land_cmd.py, _rapid_sweep.py, _land.py, tests) reaches
  only the two top-level entry points (_run_stamp_baseline/
  _run_budgeted_check, both re-exported unchanged) or budget-side helpers
  (_derive_post_land_sweep_budget_s, _budget_timing_path,
  _load_budget_timing) -- nothing reaches into the baseline cluster's own
  internals. Moved the --stamp-baseline cluster (gate-id batching, its own
  .frob/-scratch accumulator file, _run_stamp_baseline) verbatim to a new
  _check_chunking_baseline.py. RESULT: both files disappear from LARGE001
  entirely (979 -> 770 + 249 lines, both under the 800 threshold) -- no
  waiver needed for either, the split alone resolved the finding.

Verified for the split (unlike the comment-only waivers, this one moves
real code): full syntax check, `uv run python -c "from frob.app._check_
chunking import _run_budgeted_check, _run_stamp_baseline"` plus
`check_runner.run` still import cleanly; ran tests/unit/test_check_budget.py
+ tests/unit/test_check.py (152 tests, all pass); ran ruff check (caught
and fixed one now-unused `import sys` in the trimmed file) and ruff format.

Also verified per the coordinator's caution about via-scoped capability
grants: `frob check` shows zero new SYS003/SYS100/CYCLE001 findings
touching _check_chunking.py or _check_chunking_baseline.py (checked, not
assumed) -- this split does not touch strata's design/frob.strata surface
at all, unlike _host_isolation.py's deferred split which does.

Filed:
- T-2844 (real id) -- split _host_isolation.py along its lateral/vertical/
  movement seam, blocked on a dedicated via-scope migration review; scope
  includes design/frob.strata.

Also picked up (per coordinator's ask): src/frob/app/_check_chunking.py
was T-2830's own dropped-scope file (T-2369's lease at the time). Confirmed
the lease cleared (T-2369 re-homed it to child T-2832, which is done; no
in-progress ticket currently lists it in scope; `frob doctor --leases`
shows no live lease) and added it to this ticket's scope before splitting.

Evidence:
- tests/test_arch_gate.py::TestArchGateLargeFile::test_large_file_fires_large001_warn
  (docs-only/waiver-only convention, for the 10 strata comment-only files)
- tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_stamp_baseline_only_chunk_completes_and_stamps
  (directly exercises the moved --stamp-baseline code path; collected and
  passed fresh this session)

Gates: `frob check --json --ticket T-2826` (unbudgeted, FROB_NO_GATE_CACHE=1,
gate-summary present) -- 41 error-severity findings repo-wide, ZERO of them
in any of this ticket's files. All 10 strata files' own LARGE001 findings
read severity=note (waived); both _check_chunking* files disappear from
LARGE001 entirely. Re-measuring unscoped in the series report.

Do NOT promote LARGE001 WARN->ERROR here (T-2831's job, blocked on all 9
siblings).

### Changed
```
 rapid-debt.jsonl                         |   2 +
 src/frob/app/_check_chunking.py          | 234 ++--------------------------
 src/frob/app/_check_chunking_baseline.py | 251 +++++++++++++++++++++++++++++++
 src/frob/strata/__init__.py              |   7 +
 src/frob/strata/_ast.py                  |   7 +
 src/frob/strata/_audit.py                |   9 ++
 src/frob/strata/_compliance.py           |   9 ++
 src/frob/strata/_effects.py              |   9 ++
 src/frob/strata/_elaborate.py            |   8 +
 src/frob/strata/_host_isolation.py       |  13 ++
 src/frob/strata/_infra.py                |   8 +
 src/frob/strata/_mode_conformance.py     |   8 +
 src/frob/strata/_threat.py               |   9 ++
 tickets/T-2826/done-report.md            | 124 +++++++++++++++
 tickets/T-2826/ticket.md                 |  45 +++++-
 15 files changed, 520 insertions(+), 223 deletions(-)
```

### Evidence
- `tests/test_arch_gate.py::TestArchGateLargeFile::test_large_file_fires_large001_warn` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_stamp_baseline_only_chunk_completes_and_stamps` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 21 error(s), 1072 warning(s), 785 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, CYCLE001@src/frob/__init__.py, DOC006@docs/audits/test005-zero-classification-t1418.md, DOC011@docs/investigations/T-2796-backlog-reproduction.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/tickets-data-storage.md, PERF004@src/frob/strata/_selfconform_binding_rules.py, PERF004@src/frob/strata/_selfconform_surface_rules.py, PERF004@src/frob/tickets/_evidence.py, REG002@docs/design/registry/check-coverage.yaml, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, SYS003@src/frob/check/__init__.py, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, TICK006@tickets.md
