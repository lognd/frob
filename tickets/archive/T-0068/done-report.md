## Done report

Changed: new src/frob/strata/_packs.py (ANALYZABLE pack data,
require_analyzable auto-inject seam), src/frob/strata/_elaborate.py
(calls require_analyzable), src/frob/strata/_claims.py (evaluate_claims
gains compiled_policies/waived_policies, enables-cascade downgrade
logic), src/frob/strata/__init__.py exports, docs/strata/policy.md
(v0 implementation + auto-inject amendment), docs/strata/evidence.md
(v0 dependency rule).
Evidence: 5 pytest node ids above out of 8 pack tests (2 added in
review round 2: waiving a no-enables policy is a no-op; waiving a
nonexistent policy id is a logged no-op, not a crash), all green;
full `tests/unit/strata` suite green.
Filed: none.
Correction (post-review): the evidence block originally used mapping
syntax (`- pytest_node_id: ...`), which broke `frob ticket show`
(MalformedFrontmatter) and made every subsequent `frob check` run
against an unloadable queue -- the "gates clean" claim below was never
actually verified. Fixed to plain string node ids; re-ran for real
after `frob graph build` + `frob ticket sweep T-0067` then
`T-0068` (sweep last). `frob check --ticket T-0068` now actually
executes the gates stage (clones/coverage/decisions/doclink/drift/
fuzz/invariant/perf/policy/release/test all ran, exit 0, no skip) and
shows `pass gates 118 violation(s), 6 waived`. Plain `frob check` also
exit 0, gates stage executed. ruff format/check and ty remain clean.
