# TESTMOCK001: fully-mocked subjects need a non-mocked companion (T-3997)

Standalone page -- `docs/modules/gates.md` is leased by T-3259 and
T-draft-a62505d4 for this ticket's entire duration (the same lease-conflict
shape T-4605's own body already tracks for T-4114/T-4115/T-4221/T-3962/
T-3961). Once `docs/modules/gates.md` is free: fold this section into it
next to the other `COV0*` rule-catalog rows and delete this file; a
fold-in item has been appended to T-4605's body so the fold happens the
same way every other lease-blocked gates.md doc addition has.

## Problem (F-207, T-3984 item 12)

T-3933 documents a live instance in this repo's own history: a
`frob:tests`-bound test (`TestTicketEvidenceVitestOracle`) proved that a
pytest node id RESOLVES against `frob.testing.LANGUAGE_COLLECTORS`, but
every single collaborator that node's own subject calls was mocked out
(`monkeypatch.setitem(testing_mod.LANGUAGE_COLLECTORS, "ts", lambda ...)`)
-- the real, non-mocked collector code path never ran under that binding.
The gap sat invisible until a separate consumer report (F-171) surfaced
it. A green `frob:tests` edge and a green `pytest` run both looked
identical to the genuinely-exercised case; nothing distinguished "this
symbol's real code has been proven to work" from "this symbol's binding
shape has been proven to resolve".

## Fix: `testmock001_violations` (`frob.gates._coverage`)

For every `frob:tests` edge (`src` = the Python subject symbol the
directive sits on, `target` = the pytest node id it names, T-3997's own
verified read of `frob.graph.dsl`'s actual edge direction -- NOT
`frob.graph.affects._test_refs_for`'s inverted-looking filter, which
answers a different query), grouped by subject:

- The subject's own AST body is walked for **collaborator calls**: every
  `name(...)`, `obj.name(...)`, and dynamic-dispatch `TABLE[key](...)`
  call target, excluding builtins and `self`/`cls` calls -- the set a
  test would need to mock EVERY member of for this rule to have anything
  to fire about. A subject with zero collaborators (e.g. pure arithmetic)
  is silent: nothing to protect against.
- Each binding test's AST is walked for **mocked names**: `mock.patch(...)`
  / `@patch(...)` / `patch.object(...)` targets (the dotted string's last
  segment, or the literal attribute-name argument), and
  `monkeypatch.setattr(...)`/`monkeypatch.setitem(...)` targets (the
  attribute-name argument for `setattr`, the CONTAINER expression's own
  name for `setitem` -- matching T-3933's own `LANGUAGE_COLLECTORS`
  shape, where the mocked collaborator is the table itself, not the
  `"ts"` key passed alongside it).
- The subject fires `Severity.ERROR` iff it has at least one collaborator,
  at least one binding test resolved to a real AST node, and EVERY
  resolved binding test's mocked-names set covers every collaborator.
  Leaving even one collaborator un-mocked in even one binding test
  satisfies the rule.
- A `frob:tests` target that cannot be resolved to a real test AST node
  (moved, renamed, non-Python) contributes nothing either way -- an
  honest "measured nothing" for that one binding, never a false "fully
  mocked" claim (matching T-1664's `Severity.UNRESOLVED` doctrine's
  posture even though this rule reports via a plain silent skip rather
  than a separate UNRESOLVED violation, since the SUBJECT's own other
  bindings may still resolve and answer the question).

## Positive controls

- A subject with exactly one binding test that mocks its only
  collaborator fires (`tests/gates_suite/test_coverage.py::
  TestTestmock001.test_fires_when_the_only_binding_test_mocks_every_collaborator`).
- A second, real-call binding test for the same subject satisfies the
  rule (`tests/gates_suite/test_coverage.py::TestTestmock001.
  test_satisfied_by_a_companion_test_leaving_one_collaborator_real`).
- T-3933's own dynamic-dispatch-table shape
  (`monkeypatch.setitem(module.TABLE, key, ...)`) fires
  (`tests/gates_suite/test_coverage.py::TestTestmock001.
  test_t3933_shaped_dynamic_dispatch_table_scenario_fires`).
- A collaborator-free subject, and a subject whose only `frob:tests`
  target does not resolve to a real test, are both silent
  (`tests/gates_suite/test_coverage.py::TestTestmock001.
  test_silent_when_the_symbol_has_no_collaborators`,
  `tests/gates_suite/test_coverage.py::TestTestmock001.
  test_silent_when_no_test_resolves_at_all`).

## Known scope limit (out of this ticket's scope: `src/frob/gates/_coverage.py` only)

`testmock001_violations` is implemented and tested standalone; wiring it
into `frob check`'s actual job list (`frob.gates.__init__._build_jobs`,
plus the rule-severity table and `design/frob.strata`/
`docs/design/registry/check-coverage.yaml` entries) requires editing
`src/frob/gates/__init__.py`, which is leased by T-3962 for this ticket's
entire duration -- `frob ticket scope T-3997 --add src/frob/gates/
__init__.py` was refused on that lease. A follow-up ticket
(T-3997-wiring, filed against `src/frob/gates/__init__.py` +
`design/frob.strata` + `docs/design/registry/check-coverage.yaml`,
blocked_by T-3962) tracks wiring this detector into the live `frob check`
job list once that lease clears.
