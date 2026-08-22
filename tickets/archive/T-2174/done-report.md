## Done report

Measured at the real path (`uv run frob check --only gates-native --only
gates-fast --json`, parsed via `scripts/check_summary.py` -- never a
copied blob):

- ARCH001 on `build_reference_graph_module_scoped` (74 lines, threshold
  60) -- REPRODUCED. Real: the function's actual logic is short (~15
  lines), but `body_line_count` (`frob.arch._python`) counts physical
  lines including the docstring, and the docstring was ~60 lines of
  rationale.
- DUP001 on `tests/unit/verify/test_attribution_module_scope.py` --
  DID NOT reproduce (0 hits in either measurement pass). Matches the
  ticket's own "1 actual finding(s) across those 2 identit(ies)" note --
  DUP001 was noise at filing time (or fixed by an intervening land) and
  never needed a fix.

Changed:
- src/frob/graph/callgraph.py::build_reference_graph_module_scoped -- the
  extensive rationale (the `_run`/`_commit_all` collision incident, the
  cross-file-import resolution rule, why `build_reference_graph` stays
  unchanged) moved from the docstring into a new
  docs/modules/graph.md#attribution-safe-reference-graph-t-2156 section;
  the docstring itself is now a short pointer plus the essential facts.
  Also added the `frob:tests` edge it was missing (a real test already
  existed at `tests/unit/test_callgraph_module_scoped.py`, the function
  just never pointed at it -- this closed an incidental TEST001 finding
  that showed up during measurement, not one of the two identities this
  ticket named).
- docs/modules/graph.md -- new "Attribution-safe reference graph (T-2156)"
  subsection carrying the moved rationale, with a `frob:describes` anchor.

Evidence:
- tests/unit/test_callgraph_module_scoped.py::TestBuildReferenceGraphModuleScoped::test_does_not_cross_wire_same_named_helpers_in_unrelated_files
  (pre-existing test, newly wired via `frob:tests`).
- `uv run pytest tests/unit/test_callgraph_module_scoped.py
  tests/unit/verify/test_attribution_module_scope.py -o addopts="" -q`:
  4 passed (both test files' full suites, unchanged pass count -- this
  ticket only trimmed a docstring and added a directive, no behavior
  change).
- Post-fix measurement (`uv run frob check --only gates-native --only
  gates-fast --json`): zero ARCH findings and zero DUP findings anywhere
  in `src/frob/graph/callgraph.py` or
  `tests/unit/verify/test_attribution_module_scope.py`.

Filed: none new (DUP001 did not reproduce -- stated explicitly per this
ticket's own instructions, no ticket needed for a non-reproducing
finding).

Gates: `frob check --land-parity`'s remaining errors (measured separately
under T-2179, same tree) are all pre-existing debt outside this
ticket's files.

frob:no-behavior-change reason="ARCH001 was a pure docstring-length finding (body_line_count counts the docstring; the function's actual logic was always ~15 lines and untouched). The fix moves the docstring's rationale into docs/modules/graph.md and adds a frob:tests directive pointing at a pre-existing test -- no change to build_reference_graph_module_scoped's behavior, inputs, or outputs. The bound evidence (a pre-existing test) correctly PASSES at both main and the fix, which is what a behavior-preserving refactor's own evidence should do."

### Changed
```
 docs/guides/coordinator-scripts.md      | 33 +++++++++---
 docs/modules/graph.md                   | 47 +++++++++++++++++
 rapid-debt.jsonl                        |  1 +
 scripts/fleet_status.py                 | 93 ++++++++++++++++++++++++++-------
 src/frob/graph/callgraph.py             | 73 ++++++--------------------
 tests/unit/test_coordinator_scripts.py  | 84 +++++++++++++++++++++++++----
 tickets/T-2171/ticket.md                |  7 ++-
 tickets/T-2174/done-report.md           | 75 ++++++++++++++++++++++++++
 tickets/T-2174/ticket.md                |  6 ++-
 tickets/T-2179/done-report.md | 74 ++++++++++++++++++++++++++
 tickets/T-2179/ticket.md      | 74 ++++++++++++++++++++++++++
 11 files changed, 474 insertions(+), 93 deletions(-)
```

### Evidence
- `tests/unit/test_callgraph_module_scoped.py::TestBuildReferenceGraphModuleScoped::test_does_not_cross_wire_same_named_helpers_in_unrelated_files` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/tickets/_land_git_ops.py, COV001@src/frob/tickets/_land_git_ops.py, DRIFT001@src/frob/app/ticket_runner/_land_cmd.py, SELFAUDIT001@design, TEST001@src/frob/tickets/_land_git_ops.py, TICK004@tickets.md
