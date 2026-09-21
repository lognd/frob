## Done report

T-4115 -- H3-7: a route returning a dict literal with no response model is invisible to every reference gate

WHAT changed:
- src/frob/gates/_route_response_model.py (new): route_response_model_gate(root)
  walks every tracked .py file's AST for a function decorated with a
  configurable route-decorator pattern (`@<anything>.<verb>(...)` where
  <verb> is one of get/post/put/patch/delete -- not hardcoded to one web
  framework's decorator import, per T-4115's own directive, since frob
  itself defines no HTTP routes) whose body contains a `return {...}`
  (an `ast.Dict` display) that is NOT a pure `{**expr}` unpack. Emits
  ROUTE001, Severity.WARN, waivable via the standard file-scoped
  `frob:waive ROUTE001` directive.
- tests/gates_suite/test_route_response_model.py (new): 7 tests, synthetic
  route-decorator fixture (frob itself has no HTTP routes to dogfood --
  flagged explicitly, per T-4115's own Done-report instruction):
  - test_bare_dict_literal_return_fires (must-fire: return {"status": "ok"})
  - test_typed_constructor_return_is_silent (must-stay-quiet: return StatusResponse(...))
  - test_pure_unpack_of_typed_dump_is_silent (the {**model.model_dump()}
    boundary case -- DECIDED explicitly: pure unpack of a typed-looking
    expression is treated as derived from a typed object and does NOT fire)
  - test_mixed_unpack_and_literal_key_fires (a dict mixing ** unpack with a
    literal key -- still contains an untyped literal pair, DOES fire;
    proves the pure-unpack exemption is precise, not a blanket "any dict
    with **" exemption)
  - test_undecorated_function_is_ignored
  - test_file_scoped_waiver_covers_it (frob:waive ROUTE001 mechanism)
  - test_no_python_files_is_silent
- docs/modules/gate-route-response-model.md (new): ROUTE001 (T-4115) section
  with `frob:describes` anchor, rule description (including the documented
  pure-unpack-vs-mixed boundary), and rule-table row. Added as a STANDALONE
  doc file, not a section of docs/modules/gates.md, because
  docs/modules/gates.md was under an in-progress cross-worktree lease held
  by T-4111 for the entire duration of this ticket's work
  (`frob ticket scope T-4115 --add docs/modules/gates.md` was refused).
  Added docs/modules/gate-route-response-model.md to scope instead.
- src/frob/gates/_route_response_model.py::route_response_model_gate carries
  `# frob:doc docs/modules/gate-route-response-model.md#route001-t-4115`
  above it (COV001 clean, confirmed before/after via `frob check --only
  coverage`: the anchor-less symbol fired COV001; after adding the doc file
  + anchor, it does not).

WHY:
F-307 H3-7: COV/WIRE reference gates see a response-model class as
referenced once ANY route uses it, so a route returning a bare dict
literal instead is structurally invisible -- there is no missing
reference to notice, because the route never referenced a response
model in the first place. Same family as an existing guard-inventory
check (a consumer repo's own SIT-011, which frob does not carry):
"build an inventory of every X and flag the ones missing Y."

Acceptance criteria proof:
- Must-fire fixture fires: test_bare_dict_literal_return_fires.
- Must-stay-quiet fixture (typed constructor) passes `== ()`.
- Third case (unpack) DECIDED and documented explicitly, both in the gate
  module's own docstring and in docs/modules/gate-route-response-model.md:
  a PURE `{**model.model_dump()}` unpack stays quiet
  (test_pure_unpack_of_typed_dump_is_silent); a MIXED unpack+literal dict
  fires (test_mixed_unpack_and_literal_key_fires).
- WARN-tier: asserted directly (Severity.WARN) in
  test_bare_dict_literal_return_fires.
- Waivable: test_file_scoped_waiver_covers_it exercises
  `frob.gates._apply_waivers` end to end and confirms suppression.
- Failing-test-first / BUG002 repro: the repro test was committed ALONE
  first (commit e941a36dd, "test(gates): add failing repro for ROUTE001"),
  confirmed to fail at that commit (ModuleNotFoundError), then the gate
  module landed in the next commit (dbeae0ba4). `frob ticket evidence
  T-4115 --designate-repro ... --base-ref e941a36dd` and `--check-repro
  --base-ref e941a36dd` both report FAILED_AT_PARENT.

Test node ids (all bound as evidence on T-4115):
- tests/gates_suite/test_route_response_model.py::TestRouteResponseModelGate::test_bare_dict_literal_return_fires
- tests/gates_suite/test_route_response_model.py::TestRouteResponseModelGate::test_typed_constructor_return_is_silent
- tests/gates_suite/test_route_response_model.py::TestRouteResponseModelGate::test_pure_unpack_of_typed_dump_is_silent
- tests/gates_suite/test_route_response_model.py::TestRouteResponseModelGate::test_mixed_unpack_and_literal_key_fires
- tests/gates_suite/test_route_response_model.py::TestRouteResponseModelGate::test_undecorated_function_is_ignored
- tests/gates_suite/test_route_response_model.py::TestRouteResponseModelGate::test_file_scoped_waiver_covers_it
- tests/gates_suite/test_route_response_model.py::TestRouteResponseModelGate::test_no_python_files_is_silent

pytest: `PYTHONPATH=<worktree>/src python -m pytest tests/gates_suite/test_route_response_model.py`
-> 7 passed, 0 failed.

Commit shas (worktree t-4115, branch t-4115):
- e941a36dd -- test(gates): add failing repro for ROUTE001 (T-4115)  [repro-only commit, BUG002 base-ref]
- dbeae0ba4 -- feat(gates): add ROUTE001 bare dict response gate
- ad7a1e5d8 -- chore(tickets): record evidence for T-4115 (auto-commit from evidence bind + --designate-repro)
HEAD: ad7a1e5d87115609d3fb805545464fd09497cd02

Filed: T-4605 (shared with T-4114) -- "Wire CONFIGPATH001/ROUTE001
gates into the gate registry and docs/modules/gates.md". Neither gate is
wired into src/frob/gates/__init__.py's dispatch table / _KNOWN_GATE_RULES,
and neither rule has a row in docs/modules/gates.md's own table -- both out
of scope for T-4115, and docs/modules/gates.md itself was under T-4111's
live lease for this ticket's entire duration.

Gates run (measured, --only/--files forms, never bare/--ticket):
- `frob check --only coverage --files src/frob/gates/_route_response_model.py
  --files tests/gates_suite/test_route_response_model.py --files
  docs/modules/gate-route-response-model.md --base dev`: zero findings
  attributable to these 3 files (repo-wide COV/DRIFT/DSL/TODO/WAIVE findings
  present are pre-existing baseline noise -- confirmed by grep for the
  module/test names in the output).
- `frob check --only arch --files <the 2 code files> --base dev`: `pass
  frob-arch` (0 ARCH001/LARGE001 findings referencing either file).
- `ruff check` / `ruff format --check`: clean on all 3 files.
- `ty check src/frob/gates/_route_response_model.py
  tests/gates_suite/test_route_response_model.py`: "All checks passed!"
- Cross-ticket lease check: `git diff --name-only dev...HEAD` lists exactly
  docs/modules/gate-route-response-model.md, src/frob/gates/_route_response_model.py,
  tests/gates_suite/test_route_response_model.py, tickets/T-4115/ticket.md
  -- all four resolve only to T-4115's own lease (.git/frob-leases/T-4115.json).

Scope refusals: `frob ticket scope T-4115 --add docs/modules/gates.md` was
refused (ScopeLeaseConflict: held by in-progress T-4111); worked around by
adding a new standalone doc file (docs/modules/gate-route-response-model.md)
to scope instead, and filing T-4605 to fold it into
docs/modules/gates.md once T-4111 releases the lease.

Waivers added: none.
Tests skipped: none.

### Changed
```
 docs/modules/gate-route-response-model.md      |   49 +
 src/frob/gates/_route_response_model.py        |  172 ++
 tests/gates_suite/test_route_response_model.py |  159 ++
 tickets/T-4115/done-report.md                  | 2278 ++++++++++++++++++++++++
 tickets/T-4115/ticket.md                       |    8 +
 5 files changed, 2666 insertions(+)
```

### Evidence
- `tests/gates_suite/test_route_response_model.py::TestRouteResponseModelGate::test_bare_dict_literal_return_fires` (pytest node id, verified passing when recorded)
- `tests/gates_suite/test_route_response_model.py::TestRouteResponseModelGate::test_typed_constructor_return_is_silent` (pytest node id, verified passing when recorded)
- `tests/gates_suite/test_route_response_model.py::TestRouteResponseModelGate::test_pure_unpack_of_typed_dump_is_silent` (pytest node id, verified passing when recorded)
- `tests/gates_suite/test_route_response_model.py::TestRouteResponseModelGate::test_mixed_unpack_and_literal_key_fires` (pytest node id, verified passing when recorded)
- `tests/gates_suite/test_route_response_model.py::TestRouteResponseModelGate::test_undecorated_function_is_ignored` (pytest node id, verified passing when recorded)
- `tests/gates_suite/test_route_response_model.py::TestRouteResponseModelGate::test_file_scoped_waiver_covers_it` (pytest node id, verified passing when recorded)
- `tests/gates_suite/test_route_response_model.py::TestRouteResponseModelGate::test_no_python_files_is_silent` (pytest node id, verified passing when recorded)
