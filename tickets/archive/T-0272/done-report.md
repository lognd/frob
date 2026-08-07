## Done report

Added repeatable `group "NAME"` and `sudoers "RULE"` clauses to
strata-core/src/parse.rs's parse_node AND parse_store (emitted as JSON
arrays, mirroring owns/code's repeatable-STRING shape). Threaded through the
Python side: _ast.py (NodeDecl/StoreDecl gain group/sudoers tuple fields),
_host.py (_host_attrs desugar, HostManifest.group/.sudoers,
_parse_host_attrs/host_manifest_for read-back), _elaborate.py/_infra.py
pass-through.

Efficacy upgrade (the point): _host_isolation.py's HOST001 (shared-group)
and HOST002 (sudoers) sub-targets were ALWAYS-FIRE placeholders (deny-by-
default honest gap). They now derive REAL findings -- HOST001 via
groups_a & groups_b set intersection (fires only on a genuinely shared
group), HOST002 by listing declared sudoers grants (fires only when a grant
is declared). Reviewer verified: disjoint groups do NOT fire, an undeclared
sudoers does NOT fire, and the hardened litmus now passes with ZERO waivers
(the vuln litmus declares a shared group + a sudoers grant and fires). This
is an existence->efficacy conversion, not cosmetic.

Evidence (3 of 11 tests): disjoint-groups-do-not-fire, sudoers-does-not-fire-
when-undeclared, hardened-litmus-discharges. cargo test 117 passed; strata
host suite 54 passed. docs/strata/host.md honest-gap section rewritten to
reflect the closed gap. Reviewer APPROVED.

Follow-up filed T-0451: the tmLanguage grammar
(editors/vscode-strata/syntaxes/strata.tmLanguage.json) needs the group/
sudoers keywords -- the one known-red test
(test_clause_keywords_covered_by_grammar), out of this ticket's scope.
Landed via 3-way + make core.
