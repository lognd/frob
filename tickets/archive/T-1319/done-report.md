## Done report

Acceptance [0] (restore the 4 deleted runner doc anchors: doctor_runner,
fleet_runner, registry_runner, worktree_runner in docs/modules/app.md):
already satisfied on main. Verified via `git log --oneline -S
"doctor_runner.py::run" -- docs/modules/app.md`: the anchors were
restored by commit 18bd3318 "docs(tickets): land T-1233 fix campaign:
land every confirmed class-A+class-B finding in the 2026-07-29
staleness sweep", which pre-dates this dispatch. All 4 frob:describes
anchors and their prose paragraphs are present and current in
docs/modules/app.md today. No further doc edit was needed or made.

Acceptance [1] (exhaustive parametrized dispatch-totality test): added
TestResolveRunnerDispatchTotality to
tests/unit/test_app_lazy_dispatch.py --
test_every_non_bind_subcommand_resolves_a_callable_runner is
parametrized over every frob.app.config.Subcommand member (sorted by
value), asserting _resolve_runner(subcommand) returns a callable for
every member except Subcommand.bind (excepted by design -- App.__call__
wires bind up separately since it parses a raw argv rather than an
AppConfig). This locks the reviewer's manually-verified 34/34 dispatch
totality into a statically-checked regression: a future Subcommand
member added to the enum without a matching _SUBCOMMAND_RUNNER_NAMES
entry (and _import_runner_module if/elif branch) now fails this test
immediately, by name, instead of only surfacing at first live
invocation.

No source change was needed in src/frob/app -- both parts of this
ticket were either already fixed (doc anchors) or purely additive test
coverage (dispatch totality); _SUBCOMMAND_RUNNER_NAMES already covers
every non-bind Subcommand member correctly, confirmed by the new test
passing without any change to app.py.

### Changed
```
 docs/modules/tickets.md              |  13 +++
 src/frob/tickets/_store.py           |  41 ++++++-
 tests/test_ticket_land.py            |  86 +++++++++++++++
 tests/unit/test_app_lazy_dispatch.py |  41 +++++++
 tests/unit/test_ticket_store.py      |  45 ++++++++
 tickets.md                           | 203 +++++++++++++++++++++++++++++++++--
 6 files changed, 420 insertions(+), 9 deletions(-)
```

### Evidence
- `tests/unit/test_app_lazy_dispatch.py::TestResolveRunnerDispatchTotality::test_every_non_bind_subcommand_resolves_a_callable_runner[bind]` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_lazy_dispatch.py::TestResolveRunnerDispatchTotality::test_every_non_bind_subcommand_resolves_a_callable_runner[ticket]` (pytest node id, verified passing when recorded)
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 2 error(s), 459 warning(s), 694 waived
- error-findings: PRE001@tickets/T-1319, SELFAUDIT001@design
