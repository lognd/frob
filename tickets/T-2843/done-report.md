## Done report

Changed:
src/frob/gates/_doclink_docanchor.py::doclink_gate
src/frob/gates/_doclink_docanchor.py::docanchor_gate
src/frob/gates/_doclink_docanchor.py::_line_index
src/frob/gates/_docstatus.py::docstatus_gate
src/frob/gates/_docstatus.py::docmake_gate
src/frob/gates/_docstatus.py::docseverity_gate
src/frob/gates/__init__.py (import block only, re-export unchanged)

Seam verification (before building, per the ticket's own instruction to
verify rather than force): docmake_gate/docseverity_gate call back into
_doclink_config/_obligated_docs/_linked_from_edges (and, previously
undocumented, _line_index) defined in the retained _doclink_docanchor.py
module. This is real cross-module reuse, not zero-coupling -- but it is
the SAME shape _doclink_docanchor.py's own __all__ already discloses for
_sys.py's existing direct import of _doclink_config/_obligated_docs, so
it is a disclosed, pre-existing seam pattern, not a new one introduced by
this split. docstatus_gate itself is fully self-contained (DOC009/DOC011,
no shared helpers). No frob:describes anchor in docs/modules/gates.md
names any of the three moved gates by file path (only doclink_gate/
docanchor_gate are so anchored), so no doc-anchor repointing was needed
-- confirms the seam holds as identified in the ticket body.

Both resulting files are well under frob.toml's max_file_lines=800:
_doclink_docanchor.py 533 lines, _docstatus.py ~570 lines (after adding
frob:ticket directives). Per-file re-measurement (frob.gates._arch.
arch_gate + frob.gates._waive._apply_waivers against a live build_graph
snapshot, not the flat --only arch aggregate) shows ZERO arch findings
(kept or waived) against either file -- the only arch waiver present
repo-wide is gates/__init__.py's own pre-existing LARGE001 waiver,
unrelated to this split.

Found and fixed during verification (not scope creep, required to make
the split behavior-preserving): _line_index was defined only in the
"later" half (used by docmake_gate's DOC010 scan) but was ALSO called by
_doc008_scan_doc in the "documented" half (DOC008, part of doclink_gate).
Moving only the later half would have left doclink_gate broken with
NameError. Moved _line_index to _doclink_docanchor.py (disclosed in both
modules' docstrings) and had _docstatus.py import it -- caught by running
tests/test_gates.py's Doclink suite, not by inspection alone.

Also required: three inline `# frob:tests src/frob/gates/
_doclink_docanchor.py::<gate>` directives embedded inside
tests/test_gates.py (TestDocstatusGate/TestDocmakeGate/
TestDocseverityGate, 18 occurrences) hardcoded the OLD file path and
produced live DRIFT002 findings after the move (confirmed live, not
stale replay cache, by re-running after clearing .frob/gate-cache.db and
.frob/cache.db) -- repointed all 18 to src/frob/gates/_docstatus.py.

Evidence: tests/test_gates.py::TestDoclinkGate.test_orphan_doc_is_error_and_linked_docs_pass (accepts 0),
tests/test_gates.py::TestDocstatusGate.test_missing_status_header_fires_doc009 (accepts 1),
tests/test_gates.py::TestDocmakeGate.test_bogus_make_target_fires_doc010 (accepts 1),
tests/test_gates.py::TestDocseverityGate.test_mismatched_severity_row_fires_doc013 (accepts 1),
tests/test_gates.py::TestDocseverityGate.test_matching_severity_row_passes (accepts 2)

Full suite re-run (unscoped, per T-1030/refactor-invalidates-out-of-scope-edges
discipline): tests/test_gates.py + tests/unit/gates/test_doc011.py, 6
failures both before (on main, unmodified) and after this split, byte
identical (TestWireGate.test_new_cli_dest_present_in_config_external_is_not_flagged,
TestFixEngineTierABatch2.test_docenum001_fails_before_fix_and_passes_after,
TestAutofixManifest.test_killed_mid_handler_leaves_manifest_naming_completed_fixes,
TestOptInGates.test_perf_gate_still_reports_genuine_parse_failure,
TestDoc004ConsoleCommandDrift.test_real_subcommand_unanchored_warns_unbound,
TestKnownGateRuleIds.test_every_emitted_rule_literal_is_known) -- confirmed
pre-existing on main by running each individually there, not caused by
this change. TestKnownGateRuleIds's failure message itself moved (old
file:line -> new file:line for DOC013) but the underlying gap (DOC013
missing from _KNOWN_GATE_RULES) predates this ticket.

Filed: none (no out-of-scope defects found; the AFFECT001 waiver on
docstatus_gate naming T-1205's stale lease was carried forward verbatim
since T-1205 is now done but adding the DOC011 catalog row it references
is outside this ticket's scope)

Gates: frob check --ticket T-2843, scoped families only (gate:SCOPE,
gate:PREWORK, gate:COV's COV002/TODO001 subset, gate:FMT, gate:AFFECT)
clean. Repo-wide gate:COV COV001 (callgraph.py, unrelated file) and
gate:DRIFT (tickets/_store.py migration, unrelated) are pre-existing,
outside this ticket's touched set.

### Changed
```
 tickets/T-2843/ticket.md | 40 ++++++++++++++++++++++++++++++++++++----
 1 file changed, 36 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestDoclinkGate::test_orphan_doc_is_error_and_linked_docs_pass` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestDocstatusGate::test_missing_status_header_fires_doc009` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestDocmakeGate::test_bogus_make_target_fires_doc010` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestDocseverityGate::test_mismatched_severity_row_fires_doc013` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestDocseverityGate::test_matching_severity_row_passes` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 21 error(s), 1500 warning(s), 775 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, CYCLE001@src/frob/__init__.py, DOC006@docs/audits/test005-zero-classification-t1418.md, DOC011@docs/investigations/T-2796-backlog-reproduction.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/tickets-data-storage.md, PERF004@src/frob/strata/_selfconform_binding_rules.py, PERF004@src/frob/strata/_selfconform_surface_rules.py, PERF004@src/frob/tickets/_evidence.py, REG002@docs/design/registry/check-coverage.yaml, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, SYS003@src/frob/check/__init__.py, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, TICK006@tickets.md
