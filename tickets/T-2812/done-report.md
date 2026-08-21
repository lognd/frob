## Done report

Changed (18 `# frob:enforces <ENTRY-ID>` directives added, one per site):
src/frob/gates/_root_asset_dirs.py::_root001_unresolved_pkg_violation
src/frob/gates/_env_var_docs.py::env_var_doc_gate
src/frob/gates/_lexical_selfcheck.py::_lexcheck001_violation
src/frob/gates/_port_selfcheck.py::_port001_path_violation
src/frob/gates/_port_selfcheck.py::_port001_ident_violation
src/frob/gates/_port_selfcheck.py::_unresolved_project_name_violation
src/frob/gates/_doclink_docanchor.py::_doc013_violation
src/frob/gates/__init__.py::_test006_missing (second entry-id, CHK-THEME-GITIGNORED-TRUST)
src/frob/gates/_milestone.py::_mile001_blocked_by_later_milestone
src/frob/gates/_milestone.py::_mile002_descendant_later_milestone
src/frob/gates/_milestone.py::_mile003_unresolved_milestone
src/frob/gates/_milestone.py::_mile004_pair_violation
src/frob/perf/_dup_spawn.py::_def_violations
src/frob/gates/_policy_weakening_gate.py::policy_weakening_gate
src/frob/gates/_rule_id_scan.py::gate_rule_registry_violations
src/frob/gates/_mutation_evidence.py::mutation_evidence_violations (second entry-id, CHK-GATE-TEST018)
src/frob/gates/_mutation_evidence.py::must_still_pass_violations
src/frob/gates/_fix_engine_sync.py::_apply_capability_ratchet_bumps

Each site: located the rule's real `Violation(rule="<RULE>", ...)`
construction (or its existing sibling `frob:enforces` directive for a
function serving multiple registry entries), confirmed the enclosing
function, and added the missing entry-id directive following the exact
placement convention already established in this file/module (e.g.
COV006's `# frob:enforces CHK-GATE-COV006` above `_cov006`).

Evidence: tests/test_registry_exhaustiveness.py::TestEnforcesConformance::test_handled_by_with_frob_enforces_edge_is_silent
(the existing test covering REG008's own silence condition -- an
enforces edge present makes the disposition non-violating; this is a
frob-internal gate mechanism ticket, not new runtime behavior).

Verification: fresh `frob check --only registry --json` before/after --
REG008 warning count 36 -> 18 (19 fixed at the point of measurement, then
DOC012 reverted to stay disjoint from T-2359's live lease on
_docblocks.py, leaving 18 landed here and 18 remaining including DOC012).
Confirmed each of the 18 entry ids named above individually absent from
the post-fix REG008 output.

Filed: none new (remaining 18 REG008 entries + REF001/REF002 tracked
directly under parent T-2369 for the next batch, not separately filed).

Gates: frob:no-behavior-change declared (comment-only diff, BUG002
remedy option 2) since this is kind=bug with no test that fails at
parent -- the fix adds metadata, not logic.

### Changed
```
 tickets/T-2369/ticket.md |  2 +-
 tickets/T-2812/ticket.md | 31 ++++++++++++++++++++++++++++++-
 2 files changed, 31 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_registry_exhaustiveness.py::TestEnforcesConformance::test_handled_by_with_frob_enforces_edge_is_silent` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 19 error(s), 1333 warning(s), 711 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, CYCLE001@src/frob/__init__.py, DOC001@docs/investigations/T-2790-check-stage-profile.md, DOC001@docs/investigations/T-2796-backlog-reproduction.md, DOC006@docs/audits/test005-zero-classification-t1418.md, DOC011@docs/investigations/T-2796-backlog-reproduction.md, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/tickets-data-storage.md, PERF004@src/frob/tickets/_evidence.py, REG002@docs/design/registry/check-coverage.yaml, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SYS003@src/frob/check/__init__.py, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, TICK006@tickets.md
