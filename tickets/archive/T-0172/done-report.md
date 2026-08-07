## Done report

Changed:
- strata-core/src/parse/mod.rs::Parser::parse_node (managed bare marker, node_prop)
- strata-core/src/parse/mod.rs::Parser::parse_store (managed bare marker, store_prop -- store is a node too per surface.md#key-construct-semantics)
- src/frob/strata/_ast.py::NodeDecl.is_managed
- src/frob/strata/_ast.py::StoreDecl.is_managed
- src/frob/strata/_elaborate.py::_elaborate_node (managed -> "managed" node attr, mirrors _ABSTRACT_ATTR)
- src/frob/strata/_infra.py::_elaborate_store (managed -> "managed" node attr)
- src/frob/strata/_code_binding.py::is_managed (new public helper)
- src/frob/strata/_code_binding.py::check_import_conformance (skips a managed node's owned files, same as FOREIGN)
- src/frob/strata/_threat.py::_check_one_discharge (managed node skips the boundary-KIND `_mitigation_is_chokepoint` proof, same exemption an assumed claim already gets -- the claim still has to exist and prove a chokepoint shape)
- docs/strata/surface.md (node_prop/store_prop grammar gains `managed`; added `<a id="key-construct-semantics">` anchor -- was referenced nowhere before, so no `frob:doc` pointed at it validly until now)
- editors/vscode-strata/syntaxes/strata.tmLanguage.json (clause-keywords gains `managed` -- tmLanguage drift-lock test caught the omission on first run, fixed per its own failure message)

Resolution of ambiguity: surface.md's only normative sentence on `managed` was "marks external infrastructure (no tier-2 conformance; obligations shift to config evidence or assumes)". Interpreted minimally and operationally: (1) tier-2 code-binding conformance (`check_import_conformance`) treats a managed node's owned files like `FOREIGN` -- no crossing-import violation can fire against them; (2) THREAT003 discharge for a fired obligation on a managed node still requires an existing claim proving a chokepoint shape (`_discharges_as_chokepoint`) at or above the catalog rung, but is exempted from the stricter boundary-KIND match (`_mitigation_is_chokepoint`) a code-modeled node needs -- the SAME exemption an `assume` claim already gets, operationalizing "obligations shift to config evidence or assumes" without inventing a new claim form. This was disclosed as part of implementing rather than left ambiguous.

Evidence: fresh `pytest tests/unit/strata/test_managed.py --collect-only` (8 collected) confirms every id above resolves; `uv run pytest tests/unit/strata/test_managed.py -q` -> 8 passed; `uv run pytest tests/unit/test_strata_tmlanguage.py -q` -> 12 passed (drift-lock, confirms the tmLanguage sync).

Filed: none -- no out-of-scope work discovered. (An earlier round filed a draft ticket for the SYS100 finding below; superseded by main's own T-0201, filed independently while this ticket was in flight -- dropped my duplicate during the tickets.md merge per the ledger-conflict splice rule, kept T-0201.)

REVIEWER REJECT ROUND 1 fixes, final re-verification at delivered HEAD (commit 41d1729, main@63ba545 -- main moved four times total during this session; merged forward each time per the deletion-filter land rule):
1. E501: the `frob:waive PERF003` comment on `check_import_conformance` was 90 chars, failing ruff-check. Shortened to `# frob:waive PERF003 reason="dict-comp build plus owned-files loop, not nested"`. Re-verified clean under BOTH `uv run ruff check .` (All checks passed!) and bare `ruff check .` (All checks passed!), and BOTH `uv run ruff format --check` and bare `ruff format --check` on every file this ticket touched (7 files already formatted, both invocations) -- re-run after each subsequent merge, still clean.
2. Evidence re-run at final HEAD, exact numbers:
   - `uv run frob check`: `FAIL gates 2 violation(s), 186 waived`. The 2 unwaived: `COV003` on `tickets/T-0168:0` (a stale evidence id on unrelated ticket T-0168, not touched by T-0172) and `TEST006` (`.frob/coverage-stamp:0`, no coverage stamp -- campaign-wide pre-existing, standing instruction is never to run `make coverage`). Zero violations attributable to T-0172's diff.
   - `uv run frob test --base main`: `[PASS] python exit=0`, `[FAIL] strata exit=1` -- the strata-language suite fails ONLY on `tests/unit/strata/test_selfconform.py::TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant` (5 SYS100 violations: stratamod 'fs' x2, stratamod 'deserialize'+'sql', vet 'html_render'). This is T-0201's finding ("selfconform self-match: pattern-catalog data files observed as live capabilities -- main red"). A partial T-0201 fix landed in this session's later main merges (`_selfconform.py`/`_capability.py` changed) but the test still fails with the identical 5 violations post-merge. Re-verified it reproduces on UNMODIFIED main at its CURRENT tip (worktree `/home/logan/projects/frob`, commit 63ba545, clean working tree): `cd /home/logan/projects/frob && uv run pytest tests/unit/strata/test_selfconform.py::TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant -q` -> same `FAILED`, same 5 SYS100 violations logged. T-0172 touches none of T-0201's scope (`_selfconform.py`, `_effects.py`, `_capability.py`) and this failure is not new, not caused by, and not fixable within T-0172's declared scope -- NOT mine to fix here.
   - `git diff main --diff-filter=D --stat` -> empty at final HEAD.

NOT closing this ticket per workflow instruction (review-gated; leave for reviewer/closer).
