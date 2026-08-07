## Done report

Investigated both halves before writing any code, since the ticket names two distinct problems.

Problem (1), the code-side endpoint: turned out to be ALREADY covered by the generic `DRIFT002` dangling-edge check (`frob.graph.lock._vanished_endpoint`, invoked from `drift_gate`) -- it inspects every edge's `src`/`target` for an unresolved `path::qualname`, not just `frob:describes`. I proved this empirically (both a same-package Python target and a cross-package `strata-core/src/parse/mod.rs::parse_program`-shaped target with a dead symref both produce a real `DRIFT002` violation today) and pinned it down as a regression guard: `tests/test_gates.py::TestTest010KindValidation::test_dangling_tests_endpoint_still_caught_by_drift002`. No new resolver was written -- writing a TESTS-specific one would have duplicated `_vanished_endpoint`, which the ticket explicitly warned against ("reuse the resolver, don't duplicate"). Separately (out of scope for this ticket, `src/frob/lang/**`), I confirmed the *original* T-0159 repro (`tests/unit/test_strata_tmlanguage.py:13`) never produced an edge at all in the first place, dangling or otherwise -- `frob.lang`'s Python walker does not scan module-docstring text for `frob:` directives, only `#`/`//`-style comments, so that line was dead on arrival regardless of DRIFT002. That is a `frob.lang` gap, not a `frob.gates`/`frob.graph` one, and stays out of this ticket's declared scope; noting it here rather than silently fixing or silently dropping it.

Problem (2), `kind=`: `frob.graph.dsl._parse_attrs` already rejected an invalid `kind=` (not unit/integration/e2e) by turning the line into a `MalformedDirective` rather than an `Edge` -- but nothing ever surfaced that `MalformedDirective` as a reported gate violation; it stayed a `_log.warning` only `WAIVE001` had this treatment (for `frob:waive`), and `frob:tests` had no equivalent. Fixed by: (a) `src/frob/graph/dsl.py::_parse_attrs` -- the invalid-kind reason string now literally contains `frob:tests` (`f"frob:tests invalid kind={attrs['kind']!r}; must be one of {sorted(_TESTS_KINDS)}"`), mirroring how `frob:waive requires reason="..."` already lets `WAIVE001` filter `GraphSnapshot.malformed` by substring; (b) new `src/frob/gates/__init__.py::_test010_violations` (rule `TEST010`, `Severity.ERROR`, wired into `test_gate`), directly modeled on `_waive001_violations`, filtering `snapshot.malformed` for `"frob:tests" in md.reason`; (c) `TEST010` added to `_KNOWN_GATE_RULES` so `frob:waive TEST010 reason="..."` is a real, matchable waiver channel, not a `WAIVE002` typo-trap.

Changed:
- src/frob/graph/dsl.py::_parse_attrs
- src/frob/gates/__init__.py::_test010_violations (new)
- src/frob/gates/__init__.py::test_gate (wired TEST010 in, docstring updated)
- src/frob/gates/__init__.py::_KNOWN_GATE_RULES (added "TEST010")
- tests/test_gates.py::TestTest010KindValidation (new class, 3 tests)
- tests/test_graph.py::TestDsl::test_tests_verb_invalid_kind_is_malformed (new)

Evidence (recorded via `frob ticket evidence T-0237`, all pass under `uv run pytest`):
- tests/test_gates.py::TestTest010KindValidation::test_invalid_kind_reported
- tests/test_gates.py::TestTest010KindValidation::test_valid_kind_not_reported
- tests/test_gates.py::TestTest010KindValidation::test_dangling_tests_endpoint_still_caught_by_drift002
- tests/test_graph.py::TestDsl::test_tests_verb_invalid_kind_is_malformed

Also ran full `tests/test_gates.py tests/test_graph.py tests/unit/graph/` (176 tests) and `frob test --base main` (touched-set selection, 7 node ids incl. the above): all pass, exit=0.

Filed: none -- the docstring-directive-scanning gap noted above (`frob.lang` not treating module docstrings as comment sources) is a real, separate, out-of-scope-for-this-ticket finding, but I did not have time in this pass to file a fresh ticket for it before writing this report; it should be filed as a `frob.lang`-scoped bug by whoever picks this Done report up next if not already tracked. Disclosing rather than silently omitting.

Gates: `frob check --ticket T-0237` clean of anything new -- remaining violations (`TEST001` on `_prework.py::sweep_ticket`, two `DOC001`s, several `SEC001`s in fixture/example slack-token-shaped strings, `PRE001`/`TEST006` baseline state) all pre-date this change and lie outside the `src/frob/graph/dsl.py`/`src/frob/gates/__init__.py` diff introduced here (confirmed via `git diff --stat HEAD` scoped to touched files). No REL001 bump performed -- `pyproject.toml` is out of scope for this ticket; coordinator to bump at land per standing instruction.
