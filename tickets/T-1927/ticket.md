---
id: T-1927
title: design a population/date-projected capacity evaluator for frob sys capacity
state: done
kind: feature
origin: human
created: '2026-08-09'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/strata/_capacity.py
- src/frob/strata/__init__.py
- docs/strata/reliability.md
- src/frob/_cli_parsers/_misc.py
- src/frob/app/sys_runner.py
- docs/commands/sys.md
- tests/unit/strata/test_capacity_projection.py
- src/frob/app/_config_external.py
- tests/unit/test_app_sys_capacity.py
- tickets/T-2016/ticket.md
- src/frob/gates/_waive.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tickets/T-1927/**
  reason: explicit self-scope so SCOPE001's cross-ticket exemption (frob.gates._commit_exempts_file)
    recognizes this ticket's own shard commit and does not flag it against the filing
    ticket T-1480
  actor: logan
  at: '2026-08-09'
- op: remove
  glob: tickets/T-1927/**
  reason: this self-scope grant never actually fixed SCOPE001 (frob.gates.__init__._TICKET_REF_RE
    only matches T-#### 4-digit ids in commit subjects, never a T-draft-<hex> id,
    so the cross-ticket exemption could never engage regardless) and land-parity already
    reports 0 unscoped errors without it; removing to reduce surface for the T-1918
    sibling-draft-finalize lease-collision land bug
  actor: logan
  at: '2026-08-09'
- op: remove
  glob: src/frob/strata/**
  reason: T-1927 is the new _capacity.py module plus its package export and doc anchor
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/strata/_capacity.py
  reason: T-1927 is the new _capacity.py module plus its package export and doc anchor
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/strata/__init__.py
  reason: T-1927 is the new _capacity.py module plus its package export and doc anchor
  actor: logan
  at: '2026-08-10'
- op: add
  glob: docs/strata/reliability.md
  reason: T-1927 is the new _capacity.py module plus its package export and doc anchor
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tests/unit/strata/test_capacity.py
  reason: CLI wiring for frob sys capacity plus its unit test file
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/_cli_parsers/_misc.py
  reason: CLI wiring for frob sys capacity plus its unit test file
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/app/sys_runner.py
  reason: CLI wiring for frob sys capacity plus its unit test file
  actor: logan
  at: '2026-08-10'
- op: add
  glob: docs/commands/sys.md
  reason: CLI wiring for frob sys capacity plus its unit test file
  actor: logan
  at: '2026-08-10'
- op: remove
  glob: tests/unit/strata/test_capacity.py
  reason: fix scope typo -- new tests live in test_capacity_projection.py, not the
    pre-existing test_capacity.py
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tests/unit/strata/test_capacity_projection.py
  reason: fix scope typo -- new tests live in test_capacity_projection.py, not the
    pre-existing test_capacity.py
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/app/_config_external.py
  reason: float CLI flags need an explicit _FLOAT_FIELDS allowlist entry for --population
    to actually reach AppConfig
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tests/unit/test_app_sys_capacity.py
  reason: T-1927 integration test file
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tickets/T-2016/ticket.md
  reason: residue ticket filed mid-ticket via frob ticket new; scope covers its own
    auto-committed file
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/gates/_waive.py
  reason: CAP001 must be registered in _KNOWN_GATE_RULES before this ticket can close
    (T-1937 UnregisteredGateRuleConstructed guard)
  actor: logan
  at: '2026-08-10'
evidence:
- tests/unit/strata/test_capacity_projection.py::TestProjectCapacityUnscaled::test_over_capacity_current_demand_fires
- tests/unit/strata/test_capacity_projection.py::TestProjectCapacityUnscaled::test_within_capacity_is_clean
- tests/unit/strata/test_capacity_projection.py::TestProjectCapacityUnscaled::test_node_with_no_capacity_declared_is_never_checked
- tests/unit/strata/test_capacity_projection.py::TestProjectCapacityUnscaled::test_capacity_scales_with_replicas_max_unlike_rel380
- tests/unit/strata/test_capacity_projection.py::TestProjectCapacityScaled::test_population_scales_demand_linearly
- tests/unit/strata/test_capacity_projection.py::TestProjectCapacityScaled::test_population_with_no_baseline_fails_closed
- tests/unit/strata/test_capacity_projection.py::TestProjectCapacityScaled::test_baseline_population_reported_on_report
- tests/unit/strata/test_capacity_projection.py::TestProjectCapacityScaled::test_no_users_anywhere_baseline_is_none
- tests/unit/test_app_sys_capacity.py::TestSysCapacity::test_no_population_reports_current_violations
- tests/unit/test_app_sys_capacity.py::TestSysCapacity::test_population_scales_and_can_fire
- tests/unit/test_app_sys_capacity.py::TestSysCapacity::test_no_violations_exits_0
- tests/unit/test_app_sys_capacity.py::TestSysCapacity::test_population_with_no_baseline_exits_1
- tests/unit/test_app_sys_capacity.py::TestSysCapacity::test_population_flag_survives_real_argv_parsing
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
docs/strata/roadmap.md's "CLI surface (target)" names `frob sys capacity
[--population N | --at DATE]` as a phase-5 verb. T-1480 investigated and
found: no existing evaluator projects capacity thresholds against a
POPULATION or DATE parameter at all (`_starvation.py`'s capacity checks
are static, not projected) -- this is new modeling work, not a CLI-glue
gap over an existing evaluator (unlike `trace`, which T-1480 built as a
thin wrapper over the already-shipped `FactBase.reachable`).

Needed before a CLI verb here is meaningful: a real
population/date-projected capacity evaluator in `frob.strata`, analogous
to how `FactBase.reachable`/`propagated_demand` already model influence
closure and load propagation. Filed as a residue of T-1480 rather than
folded into it, per that ticket's own scope note on why `capacity` was
cut.

## Done report

Changed:
src/frob/strata/_capacity.py (new module: CAPACITY_PROJECTED_OVER_THRESHOLD,
  CapacityViolation, CapacityReport, project_capacity, _baseline_population,
  _node_capacity_per_second, _capacity_violation)
src/frob/strata/__init__.py (exports the four public symbols)
src/frob/_cli_parsers/_misc.py::_add_sys_parser, _add_sys_capacity_parser
src/frob/app/config.py::AppConfig (sys_command capacity, sys_capacity_population)
src/frob/app/_config_external.py::_FLOAT_FIELDS (regression fix, see below)
src/frob/app/sys_runner.py::_run_capacity, _print_capacity_report, run
docs/strata/reliability.md (new "Population-projected capacity" section)
tests/unit/strata/test_capacity_projection.py (new)
tests/unit/test_app_sys_capacity.py (new)

Design: `project_capacity(model, facts, population=None)` compares every
node declaring a `Capacity` against `FactBase.aggregate_demand` (T-0702's
users/rate propagation closure -- NOT `FactBase.demand`/`propagated_
demand`, which only sums explicit `Flow.rate` and never sees a `users`
declaration; this was caught by live-firing the CLI against a users-only
model, not assumed). Unlike REL380 (`_starvation.py`), which deliberately
compares SINGLE-replica capacity for a serialization point (exclusivity
collapses concurrency to 1 regardless of replica count), this evaluator
compares TOTAL throughput (`service_rate * replicas_max`) -- it answers
"how many replicas would we need at N population", not "is this lock
already overloaded". `population is None` runs unscaled against the
model's own declared demand; a given `population` scales linearly
against `_baseline_population` (the model's own summed `users`
declarations), failing closed (`StrataError.UnknownReference`) when the
model declares no baseline to scale against.

Disclosed scope cut, filed rather than silently dropped: the roadmap
names `frob sys capacity [--population N | --at DATE]`; only
`--population N` is implemented. `--at DATE` needs a growth-rate
declaration on `Node.users`/`rate` the surface grammar does not have
today -- filed as draft T-2016 (renumbers to a real id at
land), noted in both the code and docs/strata/reliability.md.

Live-fire incident (found by actually running the wired verb, not
assuming it worked): `--population` is a float CLI flag, and `AppConfig.
from_external`'s generic argparse-Namespace-to-model copy only forwards
fields listed in `_config_external._FLOAT_FIELDS` -- a value that parses
correctly through argparse was silently dropped to `None` before ever
reaching `AppConfig`, so `frob sys capacity --population N` silently ran
UNSCALED with no error. Root-caused via direct `_build_parser`/
`AppConfig.from_args` probing (not doctest speculation), fixed by adding
`sys_capacity_population` to `_FLOAT_FIELDS`, and locked down with a new
regression test (`test_population_flag_survives_real_argv_parsing`) that
parses real argv through the real parser rather than hand-constructing
`AppConfig` (which every other test in the file does and which cannot
catch this class of bug). Wired `frob sys capacity` (no args) and `frob
sys capacity --population 1000000` against this repo's own design/
frob.strata self-model after the fix: unscaled reports "no violations at
current demand" (measured, not assumed); population-scaled correctly
fails closed with `StrataError.UnknownReference` because this repo's own
model declares no `users` baseline -- both are genuine measured results.

Evidence: 13 pytest node ids -- 8 in tests/unit/strata/test_capacity_
projection.py (direct KernelModel/FactBase unit coverage of
project_capacity, kept separate from the PRE-EXISTING tests/unit/strata/
test_capacity.py, a different file covering capacity ARITHMETIC
primitives, not this module), 5 in tests/unit/test_app_sys_capacity.py
(direct-call `run(cfg)` CLI-wrapper coverage mirroring test_app_sys_
threats.py's pattern, including the real-argv-parsing regression guard
above). Feature-kind ticket, BUG002 repro-at-parent validation does not
apply.

Filed: T-2016 ("design a growth-rate grammar for frob sys
capacity --at DATE"), the --at DATE residue disclosed above.

Gates: `frob check --ticket T-1927` -- gate:SCOPE/COV/AFFECT/FMT/DUP (the
ticket-scoped families) all clean (0 errors) after fixing a genuine
COV001 (missing frob:doc on CAPACITY_PROJECTED_OVER_THRESHOLD), COV002
(missing frob:ticket on AppConfig), and DUP001 (near-duplicate test
shape vs. test_app_sys_threats.py, waived with reasoning -- shared
harness convention, not duplicated checking logic) this ticket's own
diff surfaced. Repo-wide FAILs present in the same run (gate:ARCH 2
errors, gate:DSL 1 error, ruff-check 2 errors, ruff-format) are the same
pre-existing baseline measured before this ticket (T-1925's post-land
floor already carried gate:ARCH/gate:SELFAUDIT churn from the busy
shared repo's SYS111 capability-via-ratchet ceiling, unrelated to any
file this ticket touched) -- confirmed unrelated by inspecting each
FAIL's file paths directly.

### Changed
```
 tickets/T-1927/ticket.md           | 96 +++++++++++++++++++++++++++++++++++++-
 tickets/T-2016/ticket.md | 39 ++++++++++++++++
 2 files changed, 133 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/unit/strata/test_capacity_projection.py::TestProjectCapacityUnscaled::test_over_capacity_current_demand_fires` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_capacity_projection.py::TestProjectCapacityUnscaled::test_within_capacity_is_clean` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_capacity_projection.py::TestProjectCapacityUnscaled::test_node_with_no_capacity_declared_is_never_checked` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_capacity_projection.py::TestProjectCapacityUnscaled::test_capacity_scales_with_replicas_max_unlike_rel380` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_capacity_projection.py::TestProjectCapacityScaled::test_population_scales_demand_linearly` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_capacity_projection.py::TestProjectCapacityScaled::test_population_with_no_baseline_fails_closed` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_capacity_projection.py::TestProjectCapacityScaled::test_baseline_population_reported_on_report` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_capacity_projection.py::TestProjectCapacityScaled::test_no_users_anywhere_baseline_is_none` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_sys_capacity.py::TestSysCapacity::test_no_population_reports_current_violations` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_sys_capacity.py::TestSysCapacity::test_population_scales_and_can_fire` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_sys_capacity.py::TestSysCapacity::test_no_violations_exits_0` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_sys_capacity.py::TestSysCapacity::test_population_with_no_baseline_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_sys_capacity.py::TestSysCapacity::test_population_flag_survives_real_argv_parsing` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 13 passed (from 13 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH001@src/frob/gates/_fix_engine_sync.py, DSL001@CHANGELOG.md, F401@/home/logan/projects/frob/.claude/worktrees/strata-cli-surface/tests/test_gates_fmt_directives.py, F401@/home/logan/projects/frob/.claude/worktrees/strata-cli-surface/tests/unit/test_tickets_evidence_only_scope.py, SELFAUDIT001@design
