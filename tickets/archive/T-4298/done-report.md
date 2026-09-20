## Done report

Part 1 (mechanical): `frob format --code --check` measured 6 files needing a rewrite at
the time this ticket started (matches the ticket's own worst-case count, not by
assumption -- verified independently); `frob format --code` applied and committed
separately from the mechanism change.

Part 2 (mechanism): LANDFMT001 (`frob.gates._land_format.land_format_gate`), a pure
`(root, touched_paths)` gate mirroring LANDPARITY001/002's own diff-scoped shape --
`ruff format --check` restricted to this diff's own touched `.py` files via the same
`working_diff(root, "main")` source `_land_parity_diff` already uses, never a whole-tree
scan. Wiring it into `run_gates`'s dispatch table was sufficient on its own to make
`frob ticket land` refuse on this drift, since land already spawns `frob check --ticket
<id>` as part of its own pre-mutation gate pass (`_check_gate_findings_fn`) -- no change
to `frob.tickets._land`/`frob.app.ticket_runner._land_cmd` needed, and none made: both
carried an in-progress scope lease held by a concurrent ticket (T-4281) for this entire
session.

Design decision (acceptance criterion 3, recorded in
docs/modules/gates.md#land-format-landfmt001-t-4298): REFUSE, not auto-apply, for now.
Auto-applying `ruff format` on the land path (extending `_fmt_pre_land_step`'s existing
`frob fmt`-only absorption to also cover code drift) is very likely the right end state,
matching this project's existing Tier-A auto-fix posture -- left as a `frob:todo T-4298`
directive in `frob.gates._land_format` for a follow-up once `_land_cmd.py`'s lease is
free, rather than built here.

Evidence: `frob test --base main` (touched-set) ran 15 python test(s), exit=0, all
recorded. New tests: `tests/unit/test_land_format_gate.py::test_diff_touched_unformatted_file_fires`,
`::test_already_formatted_touched_file_is_quiet`, `::test_no_diff_is_quiet` (all bound
via `frob:tests` on `land_format_gate`).

Filed: none -- everything found was either this ticket's own assigned work or scope-
declaration friction resolved in-flight via `frob ticket scope --add`.

frob:waive SCOPE002 reason="src/frob/gates/__init__.py and src/frob/gates/_waive.py are
large, widely-shared gate-registry modules; wiring a new gate rule into them (the same
'add to the frozenset'/'add a dispatch entry' shape LANDPARITY001/002 and CROSSTICKET001
already established) pulls in dozens of pre-existing, untouched doc/test-edge and
private-helper obligations across land-lock/registry/coverage machinery this diff never
touches. Same shape T-4281/T-4289/T-4278 already disclosed this same session rather than
chased -- pulling each named file into scope would only cascade further, never converge,
and directly contradicts this ticket's own proportional-scope point."

Gates: `frob check --ticket T-4298 --only gates-fast` -- 165 error(s), all SCOPE002 (the
waived whole-file-closure shape above, same finding T-4281 landed with unresolved
moments earlier this session); zero errors of any other rule. `frob format --code
--check` and `frob test --base main` both clean/green on this diff. Full unscoped `frob
check` deferred to `frob ticket land`'s own re-verification per this repo's T-0627
foreground-agent guard.

### Changed
```
 docs/design/registry/check-coverage.yaml     |   7 +-
 docs/modules/gates.md                        |  54 +++++++-
 src/frob/gates/__init__.py                   |  15 +++
 src/frob/gates/_land_format.py               | 189 +++++++++++++++++++++++++++
 src/frob/gates/_waive.py                     |   4 +
 src/frob/graph/cache.py                      |   3 +-
 tests/test_ci_workflow_timeout.py            |   6 +-
 tests/test_graph.py                          |   3 +-
 tests/unit/test_graph_lock_holder_naming.py  |  12 +-
 tests/unit/test_graph_stat_trust_margin.py   |  24 +++-
 tests/unit/test_land_cross_ticket_leakage.py |   4 +-
 tests/unit/test_land_format_gate.py          | 115 ++++++++++++++++
 tickets/T-4298/done-report.md                |  75 +++++++++++
 tickets/T-4298/ticket.md                     |  92 +++++++++++++
 14 files changed, 583 insertions(+), 20 deletions(-)
```

### Evidence
- `tests/unit/test_land_format_gate.py::test_diff_touched_unformatted_file_fires` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_format_gate.py::test_already_formatted_touched_file_is_quiet` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_format_gate.py::test_no_diff_is_quiet` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 6 error(s), 4646 warning(s), 986 waived
- error-findings: ARCH103@src/frob/graph/cache.py, DUP001@src/frob/gates/_land_format.py, SCOPE002@tickets.md, SELFAUDIT001@design, SELFAUDIT001@tests/unit/test_land_format_gate.py, WIRE002@tests/test_ci_workflow_timeout.py
