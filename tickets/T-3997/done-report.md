## Done report

T-3997: TESTMOCK001: fully-mocked subjects need a non-mocked companion
worktree: /home/logan/projects/frob/.claude/worktrees/t-3997
HEAD: 267102027

UPDATE (after the checklist below first ran): the first coverage check
run (against a truncated log) missed that it also reported COV001/COV002
against my own new symbols -- a `frob:doc <file>` with no `#anchor`
fragment never resolves (`_docanchor_check_edge` requires `<file>#<slug>`;
COV001 does not count an unresolved edge as documentation), and none of
the new private helpers carried a `frob:ticket T-3997` edge. Fixed in a
follow-up commit (2d2fd5575): the `frob:doc` directive now names the
real heading slug (`docs/modules/gate-testmock001.md#testmock001-fully-
mocked-subjects-need-a-non-mocked-companion-t-3997`, verified via
`frob.gates._doclink_docanchor._doc_anchor_slugs`), and every new private
symbol carries `# frob:ticket T-3997`. Evidence was then EXPLICITLY
removed and re-added (`--remove` + `--reason`, then re-bind) so the
evidence commit sits AFTER the fix commit, per the playbook's "bind
evidence after the last commit" rule -- see commit list below.

## WHAT changed

- src/frob/gates/_coverage.py: added `testmock001_violations(root, snapshot)`
  plus its private helpers (`_testmock001_find_node`,
  `_testmock001_call_target_name`, `_testmock001_collaborators`,
  `_testmock001_patch_target_name`, `_testmock001_monkeypatch_target_name`,
  `_testmock001_mocked_names`) and the `_TESTMOCK001_BUILTIN_NAMES`/
  `_TESTMOCK001_SELF_NAMES` constants. `testmock001_violations` is exported
  in `__all__`.
- tests/gates_suite/test_coverage.py: added `TestTestmock001` with 5 tests
  covering the fire/silent/companion/T-3933-shape cases.
- docs/modules/gate-testmock001.md (new): standalone rule doc, since
  docs/modules/gates.md is leased by T-3259 and T-draft-a62505d4 for this
  ticket's whole duration. Notes the fold-in is tracked, and documents the
  actual `frob:tests` edge direction I verified empirically (src=subject
  symbol, target=pytest node id string) -- `frob.graph.dsl.parse_directives`
  confirmed against a real parse of `src/frob/graph/affects.py`, which
  disagrees with what `frob.graph.affects._test_refs_for`'s own docstring
  suggests; I built `testmock001_violations` against the verified real
  direction, not the docstring's claim.
- tickets/T-3997/ticket.md: scope now includes docs/modules/gate-testmock001.md
  (mirrored via `frob ticket scope T-3997 --add ...` from the worktree),
  and evidence recorded for all 3 acceptance items.

## WHY

F-207 (T-3984 item 12): T-3933 is a live, already-shipped instance of the
exact defect this rule exists to catch -- a `frob:tests`-bound test proved
BINDING (node-id resolution against `frob.testing.LANGUAGE_COLLECTORS`)
while every real collaborator the subject calls was mocked out
(`monkeypatch.setitem(testing_mod.LANGUAGE_COLLECTORS, "ts", ...)`), so
real execution went unproven until a separate consumer report (F-171)
surfaced the gap. `testmock001_violations` generalizes the check: for
every `frob:tests` edge, walk the subject's own AST for the collaborator
calls it makes (direct calls, attribute calls, and dynamic-dispatch
`TABLE[key](...)` calls -- T-3933's own shape), walk each binding test's
AST for `mock.patch`/`monkeypatch.setattr`/`monkeypatch.setitem` targets,
and fire `Severity.ERROR` unless at least one binding test leaves at
least one real collaborator un-mocked.

## Acceptance criteria proof

1. "given a frob:tests-bound symbol whose only binding test mocks every
   collaborator, when frob check runs, then TESTMOCK001 fires" --
   `tests/gates_suite/test_coverage.py::TestTestmock001::
   test_fires_when_the_only_binding_test_mocks_every_collaborator`: a
   subject calling one collaborator (`helper()`), bound to one test that
   only ever calls it through `mock.patch("...helper", ...)` -- fires
   exactly one TESTMOCK001 violation naming the collaborator.
2. "given a second test for the same symbol with at least one non-mocked
   binding, when frob check runs, then the rule is satisfied" --
   `tests/gates_suite/test_coverage.py::TestTestmock001::
   test_satisfied_by_a_companion_test_leaving_one_collaborator_real`: the
   same subject/mocked-test pair PLUS a second binding test that calls
   the subject with no patching at all -- zero TESTMOCK001 violations.
3. "given T-3933's own scenario, when this rule ships, then it would have
   flagged the synthetic LANGUAGE_COLLECTORS stand-in before F-171
   surfaced the gap externally" --
   `tests/gates_suite/test_coverage.py::TestTestmock001::
   test_t3933_shaped_dynamic_dispatch_table_scenario_fires`: a subject
   dispatching through a module-level dict (`COLLECTORS[lang](root)`),
   bound to one test using `monkeypatch.setitem(tool_mod.COLLECTORS,
   "ts", ...)` exactly like T-3933's own fixture -- fires, naming
   `COLLECTORS`.

   Two additional non-acceptance-bound tests (not double-counted as
   evidence for the 3 criteria above, but proving the rule does not
   false-fire): `test_silent_when_the_symbol_has_no_collaborators`
   (nothing to mock -> silent) and `test_silent_when_no_test_resolves_at_all`
   (an unresolvable `frob:tests` target contributes nothing, never a
   false "fully mocked" claim).

## Test node ids (evidence, bound with --base-ref dev)

- tests/gates_suite/test_coverage.py::TestTestmock001::test_fires_when_the_only_binding_test_mocks_every_collaborator  (accepts 1)
- tests/gates_suite/test_coverage.py::TestTestmock001::test_satisfied_by_a_companion_test_leaving_one_collaborator_real  (accepts 2)
- tests/gates_suite/test_coverage.py::TestTestmock001::test_t3933_shaped_dynamic_dispatch_table_scenario_fires  (accepts 3)

All 5 tests in TestTestmock001 pass:
`PYTHONPATH=$(pwd)/src .venv/bin/python -m pytest
tests/gates_suite/test_coverage.py::TestTestmock001 -p no:cacheprovider -q`
-> `SUITE-RESULT: exitstatus=0 collected=5 failed=0`

## Commit shas

- 14bf4af4f  feat(gates): add TESTMOCK001 fully-mocked-subject detector (T-3997)
- 18655bdd3  chore(tickets): scope T-3997  (scope mirror, before the code commit)
- a858ff0f1 / 88827c78f / 748b0065d  chore(tickets): record evidence for T-3997
  (bound after 14bf4af4f, but then INVALIDATED by the next commit below --
  superseded by the re-bind after it)
- 2d2fd5575  fix(gates): resolve COV001/COV002 for TESTMOCK001 symbols (T-3997)
  (the doc-anchor-slug + frob:ticket fix)
- ef9bcd3bd  chore(tickets): evidence --remove (explicit re-bind trigger,
  --reason recorded in the ticket's evidence_changes log)
- 267102027  chore(tickets): record evidence for T-3997  (final, all 3
  acceptance items re-bound AFTER 2d2fd5575 -- the current HEAD)

## Scope refusal / follow-up (out-of-scope work, filed as a ticket)

This ticket's own declared scope is `src/frob/gates/_coverage.py` only.
`testmock001_violations` is fully implemented and tested standalone, but
wiring it into the LIVE `frob check` job list requires editing
`src/frob/gates/__init__.py` (its `_build_jobs`/import list and rule-
severity table), plus `design/frob.strata` and
`docs/design/registry/check-coverage.yaml`. `frob ticket scope T-3997
--add src/frob/gates/__init__.py` was refused: that file is leased by
T-3962 for this ticket's entire duration. T-4647 ("wire TESTMOCK001
(T-3997) into the live frob check job list", kind=security, priority=high,
blocked_by T-3962) already exists and tracks this wiring step -- I
attempted to file it and `frob ticket new` detected it as 100% similar
to the already-queued T-4647 and refused the duplicate, so no new ticket
was filed. I did NOT append a fold-in note to T-4605's body (that ticket
is not mine and I did not want to touch another agent's ticket body under
fleet load) -- docs/modules/gate-testmock001.md's own text records the
fold-in intent instead.

## Cross-ticket lease note

`tests/gates_suite/test_coverage.py` (where I appended `TestTestmock001`)
is ALSO leased by T-4420 ("Clean land and gates test-suite docstrings of
change-narrative", a pure docstring-cleanup ticket, in-progress). My
change only appends a new class at the end of the file; it should merge
cleanly, but the coordinator may want `--allow-cross-ticket` or to
sequence the two lands.

## Pre-READY checks (re-run AFTER the COV001/COV002 fix, against HEAD 267102027)

- `frob check --only sys --files src/frob/gates/_coverage.py --files
  tests/gates_suite/test_coverage.py --files docs/modules/gate-testmock001.md
  --base dev`: `UNRES  gate-summary  7 errors, 557 warnings, 0 unresolved,
  5 waived` -- zero of those errors/warnings attributable to my files
  (all are pre-existing DRIFT001/DSL001/DOCARCH001 findings in unrelated
  files, e.g. tests/unit/test_makefile_coverage.py, tests/test_app.py).
  No SELFAUDIT001 findings at all in the run.
- `frob check --only arch --files src/frob/gates/_coverage.py --files
  tests/gates_suite/test_coverage.py --base dev`: `pass  frob-arch  20
  warnings (36 waived), 546 suggestions` -- all pattern-recommendation/
  anti-pattern-escape findings are pre-existing, none against
  `_coverage.py` or `test_coverage.py`'s new symbols. No ARCH001/LARGE001.
- `frob check --only coverage --files src/frob/gates/_coverage.py --files
  tests/gates_suite/test_coverage.py --files docs/modules/gate-testmock001.md
  --base dev`: FIRST run: `FAIL gate:COV 19 errors` -- 10 of those WERE
  mine (COV001 on `testmock001_violations`'s bare-file frob:doc, COV002 on
  9 new symbols with no frob:ticket edge). Fixed (commit 2d2fd5575) and
  RE-RUN: `FAIL gate:COV 9 errors` -- all 9 remaining are pre-existing,
  none against any `testmock`-named symbol (grepped explicitly, zero
  hits). The `gate:TODO` TODO002 finding at `_coverage.py:1493` is the
  PRE-EXISTING `entrypoint_coverage_violations` `frob:todo T-draft-50806633`
  directive (T-4230's own, predates this ticket).
- `ruff check src/frob/gates/_coverage.py tests/gates_suite/test_coverage.py`:
  "All checks passed!" (after one `ruff format` pass earlier).
- `ty check src/frob/gates/_coverage.py`: "All checks passed!"

### Changed
```
 docs/modules/gate-testmock001.md   |   91 ++
 src/frob/gates/_coverage.py        |  279 +++++
 tests/gates_suite/test_coverage.py |  168 +++
 tickets/T-3997/done-report.md      | 2345 ++++++++++++++++++++++++++++++++++++
 tickets/T-3997/ticket.md           |   17 +-
 5 files changed, 2889 insertions(+), 11 deletions(-)
```

### Evidence
- `tests/gates_suite/test_coverage.py::TestTestmock001::test_satisfied_by_a_companion_test_leaving_one_collaborator_real` (pytest node id, verified passing when recorded)
- `tests/gates_suite/test_coverage.py::TestTestmock001::test_t3933_shaped_dynamic_dispatch_table_scenario_fires` (pytest node id, verified passing when recorded)
- `tests/gates_suite/test_coverage.py::TestTestmock001::test_fires_when_the_only_binding_test_mocks_every_collaborator` (pytest node id, verified passing when recorded)
