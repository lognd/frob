---
id: T-1982
title: Land-time ty check passes explicit paths, bypassing the tests/fixtures exclude,
  so detector fixtures can refuse a land
state: done
kind: bug
origin: human
created: '2026-08-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/check/
- src/frob/app/ticket_runner/_land_cmd.py
- tests/test_ticket_work_and_land_finish.py
- rapid-debt.jsonl
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/app/ticket_runner/_land_cmd.py
  reason: the actual bug and fix live in the land-time ty invocation (_land_cmd.py),
    not src/frob/check/ as originally filed; test coverage lives in the existing land-finish
    test module; rapid-debt.jsonl is the standing rapid-profile debt log every land
    under this profile appends to
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tests/test_ticket_work_and_land_finish.py
  reason: the actual bug and fix live in the land-time ty invocation (_land_cmd.py),
    not src/frob/check/ as originally filed; test coverage lives in the existing land-finish
    test module; rapid-debt.jsonl is the standing rapid-profile debt log every land
    under this profile appends to
  actor: logan
  at: '2026-08-10'
- op: add
  glob: rapid-debt.jsonl
  reason: the actual bug and fix live in the land-time ty invocation (_land_cmd.py),
    not src/frob/check/ as originally filed; test coverage lives in the existing land-finish
    test module; rapid-debt.jsonl is the standing rapid-profile debt log every land
    under this profile appends to
  actor: logan
  at: '2026-08-10'
evidence:
- tests/test_ticket_work_and_land_finish.py::TestAssertTouchedFilesTypeCheckPreLand::test_a_fixture_file_excluded_by_pyproject_is_not_type_checked
- tests/test_ticket_work_and_land_finish.py::TestAssertTouchedFilesTypeCheckPreLand::test_a_bad_file_outside_fixtures_still_refuses_with_exclude_configured
- tests/test_ticket_work_and_land_finish.py::TestAssertTouchedFilesTypeCheckPreLand::test_dup_region_fixture_is_covered_by_the_exclude
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
`pyproject.toml` excludes `tests/fixtures/**` from type checking, but the
land-time `ty check` invocation passes EXPLICIT PATHS, and an explicit
path overrides the config exclude. So fixture files -- which are
deliberately malformed, duplicated, or otherwise non-conforming BY
DESIGN, because they exist to be detected -- get type-checked anyway and
can refuse a land.

MEASURED, 2026-08-10, while landing T-1957: the new fixture
`tests/fixtures/dup_type_name/src/{mod_a,mod_b}.py` (a deliberate
type-name-only clone pair, the whole point of the fixture) was
type-checked at land time despite the exclude. The agent confirmed the
same exposure applies to the PRE-EXISTING sibling fixture
`tests/fixtures/dup_region/`, so this is not specific to the new files.

It was worked around by making the fixture self-contained rather than by
touching the exclude config -- a good local call, since editing the
exclude to satisfy a checker invocation that ignores excludes would not
have worked anyway. But the workaround does not generalize: every future
fixture under `tests/fixtures/` inherits the same trap, and a fixture
that CANNOT be made type-clean (one whose entire purpose is to be
ill-typed) has no workaround at all.

WHY IT MATTERS: fixtures are how detectors are regression-tested here.
T-1957 exists precisely because a detector gap needed a corpus. If
adding a corpus can refuse a land, the cost of testing a detector goes
up exactly when we most want it down -- and the failure appears at LAND
time, after all the work, not at authoring time.

DO NOT FIX IT THIS WAY:
- Do NOT add per-file `# type: ignore`-style suppressions across
  fixtures. A suppression must target any consumer's checker, not just
  the one this repo runs, and blanketing fixtures with them hides real
  problems in non-fixture code if a path is ever mis-globbed.
- Do NOT delete or weaken the `tests/fixtures/**` exclude. It is correct;
  the defect is that the land-time invocation bypasses it.
- Do NOT special-case the two known fixture directories by name. The next
  fixture will not be in the list, which is the same
  exemption-by-enumeration trap that leaves guards silently narrow.

FIX DIRECTION: make the land-time checker invocation honor the project's
configured excludes -- either by not passing explicit paths that fall
inside an excluded glob, or by filtering the explicit path list against
the exclude set before invoking. One place, applies to every fixture that
will ever exist.

ACCEPTANCE: first test must FAIL before the fix -- add a deliberately
ill-typed file under `tests/fixtures/`, run the land-time check path, and
assert it is NOT type-checked. Then assert a genuinely ill-typed file
OUTSIDE `tests/fixtures/` is still caught (the exclude must not widen),
and confirm `tests/fixtures/dup_region/` and
`tests/fixtures/dup_type_name/` are both covered.

## Done report

The land-time ty invocation (_ty_check_files) passes explicit touched-file paths, which silently overrides pyproject.toml's [tool.ty.src].exclude for ty. Added _ty_configured_excludes (reads that same exclude list) and filtered _touched_py_files through frob.excludes.is_excluded before ty ever sees the path list -- one shared filter point, not a per-fixture-directory special case, so any future fixture under tests/fixtures/** is covered automatically. Confirmed both tests/fixtures/dup_region/ and tests/fixtures/dup_type_name/ are covered by new tests, and a genuinely bad file outside tests/fixtures/ still refuses the land (the exclude does not widen).

### Changed
```
 rapid-debt.jsonl                   |  2 ++
 tickets/T-1982/done-report.md      | 19 +++++++++++++++++++
 tickets/T-1982/ticket.md           | 36 ++++++++++++++++++++++++++++++++++--
 tickets/T-1991/ticket.md | 21 +++++++++++++++++++++
 4 files changed, 76 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_ticket_work_and_land_finish.py::TestAssertTouchedFilesTypeCheckPreLand::test_a_fixture_file_excluded_by_pyproject_is_not_type_checked` (pytest node id, verified passing when recorded)
- `tests/test_ticket_work_and_land_finish.py::TestAssertTouchedFilesTypeCheckPreLand::test_a_bad_file_outside_fixtures_still_refuses_with_exclude_configured` (pytest node id, verified passing when recorded)
- `tests/test_ticket_work_and_land_finish.py::TestAssertTouchedFilesTypeCheckPreLand::test_dup_region_fixture_is_covered_by_the_exclude` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH001@src/frob/graph/__init__.py, DSL001@CHANGELOG.md, DSL001@docs/commands/sys.md, DSL001@docs/design/coding-performance-corpus.md, DSL001@docs/design/cwe-1000-registry.md, DSL001@docs/design/design-pattern-traps-corpus.md, DSL001@docs/design/language-adapter-tier-decision.md, DSL001@docs/design/registry/RECONCILIATION.md, DSL001@docs/design/system-performance-corpus.md, DSL001@docs/guides/coordinator-scripts.md, DSL001@docs/guides/editors.md, DSL001@docs/guides/exhaustive-research.md, DSL001@docs/guides/install.md, DSL001@docs/modules/app.md, DSL001@docs/modules/arch.md, DSL001@docs/modules/bind.md, DSL001@docs/modules/clean.md, DSL001@docs/modules/cli.md, DSL001@docs/modules/cve.md, DSL001@docs/modules/decisions.md, DSL001@docs/modules/deploy.md, DSL001@docs/modules/dup-sota-survey.md, DSL001@docs/modules/dup.md, DSL001@docs/modules/fleet.md, DSL001@docs/modules/fuzz.md, DSL001@docs/modules/gates.md, DSL001@docs/modules/graph.md, DSL001@docs/modules/lang.md, DSL001@docs/modules/logging.md, DSL001@docs/modules/mutate.md, DSL001@docs/modules/perf.md, DSL001@docs/modules/process.md, DSL001@docs/modules/release.md, DSL001@docs/modules/render.md, DSL001@docs/modules/serve.md, DSL001@docs/modules/stats.md, DSL001@docs/modules/strata.md, DSL001@docs/modules/testing.md, DSL001@docs/modules/tickets.md, DSL001@docs/modules/vet.md, DSL001@docs/strata/boundary.md, DSL001@docs/strata/charter.md, DSL001@docs/strata/evidence.md, DSL001@docs/strata/host.md, DSL001@docs/strata/kernel.md, DSL001@docs/strata/krb.md, DSL001@docs/strata/policy.md, DSL001@docs/strata/reliability.md, DSL001@docs/strata/roadmap.md, DSL001@docs/strata/selfconform.md, DSL001@docs/strata/surface.md, DSL001@docs/strata/threat.md, DSL001@docs/strata/waive.md, F401@/home/logan/projects/frob/.claude/worktrees/queue-hygiene/tests/unit/test_tickets_evidence_only_scope.py
