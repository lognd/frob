## Done report

Changed: strata-core/src/parse.rs (policy grammar, dotted idents, `>=`),
src/frob/strata/_ast.py (ScopeSpec/ForbidCall/ForbidImport/ConfineUse/
AtCallRequire/Mediate/PolicyRule/PolicyDecl, Module.policies), new
src/frob/strata/_policy.py (CompiledPolicy/CompiledPolicies/
compile_policies), src/frob/strata/__init__.py exports.
Evidence: 65 cargo tests green (not listed per policy: COV003 cannot
resolve cargo ids); 3 pytest node ids above out of 19 new tests, all
green; full `tests/unit/strata` suite (154 tests) green.
Filed: none.
Correction (post-review): the evidence block originally used mapping
syntax (`- pytest_node_id: ...`), which broke `frob ticket show`
(MalformedFrontmatter) and made every subsequent `frob check` run
against an unloadable queue -- the "gates clean" claim below was never
actually verified. Fixed to plain string node ids; re-ran for real
after `frob graph build` + `frob ticket sweep T-0067` (T-0068 swept
last). `frob check --ticket T-0067` now actually executes the gates
stage (clones/coverage/decisions/doclink/drift/fuzz/invariant/perf/
policy/release/test all ran, exit 0, no skip) and shows `pass gates
118 violation(s), 6 waived`. Plain `frob check` also exit 0, gates
stage executed. ruff format/check and ty remain clean.
