## Done report

Fixed the four bucket (d) singletons that are not owned elsewhere:

- src/frob/strata/_capacity.py: dropped the redundant frob:doc anchors on
  the two private helpers _resolve_population_scale/_resolve_elapsed_
  seconds -- the public caller project_capacity already carries both
  anchors, resolving COV007 x4.
- src/frob/process/_lock_msvcrt.py: added a module-level frob:waive
  REF002 (fresh Windows-only backend split with one intentional anchor).
- src/frob/app/_config_external.py: added the same
  T-1038/T-1659-shape frob:waive OPAQUE001 its sibling _apply_*_fields
  helpers already carry, on _apply_datetime_fields.
- src/frob/strata/_models.py::Growth.period_seconds: added its first
  unit tests (known unit resolves; unknown unit fails closed with
  StrataError.UnknownUnit) plus the frob:tests binding, resolving
  TEST001.

Not touched: PERF003 at src/frob/refactor/_scan.py:772 -- refactor/**
belongs to another series per fleet discipline.

Evidence: `timeout 300 uv run frob check --only coverage` (no
_capacity.py COV007), `--only refs` (REF002 for _lock_msvcrt.py now
waived), `--only opaque` (OPAQUE001 for _config_external.py:690 now
waived), `--only test` (no period_seconds TEST001). `timeout 300 uv run
pytest tests/unit/strata/test_capacity.py -k TestGrowthPeriodSeconds`
2 passed.

### Changed
```
 src/frob/app/_config_external.py   |  3 +++
 src/frob/process/_lock_msvcrt.py   |  5 +++++
 src/frob/strata/_capacity.py       | 12 ++++++------
 src/frob/strata/_models.py         |  6 ++++++
 tests/unit/strata/test_capacity.py | 26 ++++++++++++++++++++++++++
 tickets/T-3678/ticket.md           | 13 +++++++++++++
 6 files changed, 59 insertions(+), 6 deletions(-)
```

### Evidence
- `tests/unit/strata/test_capacity.py::TestGrowthPeriodSeconds::test_resolves_known_time_unit` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_capacity.py::TestGrowthPeriodSeconds::test_unknown_unit_is_err` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 11 error(s), 4260 warning(s), 903 waived
- error-findings: AFFECT001@src/frob/strata/_models.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV003@tests/test_ci_workflow_matrix.py, DEPR006@frob-deprecated-baseline.lock.json, DRIFT001@src/frob/process/_derived_lock.py, DRIFT002@docs/modules/process.md, PERF003@src/frob/refactor/_scan.py, PERF004@src/frob/refactor/_scan_carry.py, PRE001@tickets/T-3678, REL001@src/frob/__init__.py, WAIVE011@frob-ratchet.lock.json
