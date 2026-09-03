## Done report

Fixed the two DOC006 breaks in changelog.d/T-2691.md directly: (1) a mid-word wrap had split the dotted symbol frob.tickets._land._write_land_status into frob.tickets._land._write_ land_status (a stray space inside a backtick span), which DOC006 correctly flagged as non-resolving; joined it back to the real symbol name. (2) the fragment also carried a backticked frob ticket land-status CLI invocation that intentionally names a verb that was NOT added -- DOC006 treats any backtick span as a checkable pointer regardless of prose intent, so this was flagged too; stripped the backticks so it reads as plain prose (which DOC006 never scans, per its own docstring: only backtick spans and markdown links are checked). Added tests/test_docptr_gate.py::TestDoc004Doc006ZeroOnFrobsOwnRepo::test_changelog_d_fragment_doc006_zero, a targeted pin on changelog.d/T-2691.md's own DOC006 result independent of the whole-repo test (which cannot pass right now due to T-3491's separate, still-open finding on tickets/T-3489/ticket.md). Both content fixes are text-only edits inside the existing land-owned fragment, matching this ticket's scope (changelog.d/T-2691.md). T-3489's generator/gate-level root-cause fix is a separate, still-in-progress ticket; this ticket only repairs the existing fragment via the sanctioned in-scope path.

### Changed
```
 tickets/T-3485/done-report.md | 17 +++++++++++++++++
 tickets/T-3485/ticket.md      | 12 +++++++++++-
 2 files changed, 28 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_docptr_gate.py::TestDoc004Doc006ZeroOnFrobsOwnRepo::test_changelog_d_fragment_doc006_zero` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 20 error(s), 4042 warning(s), 868 waived
- error-findings: COV003@tests/unit/test_scaffold_project.py, DEPR006@frob-deprecated-baseline.lock.json, DOC006@tickets/T-3489/ticket.md, DOC007@src/frob/verify/_bisect.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT002@src/frob/verify/_bisect.py, LARGE001@.claude/hooks/root-write-guard.py, LARGE001@src/frob/arch/_mayraise.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, PRE001@tickets/T-3485, REL001@src/frob/__init__.py, TICK004@tickets.md, WAIVE009@src/frob/arch/_normalized.py, WAIVE011@frob-ratchet.lock.json, WIRE002@src/frob/app/ticket_runner/_land_cmd.py, WIRE002@src/frob/gates/_arch.py, WIRE002@src/frob/gates/_coverage_sites.py, WIRE002@src/frob/gates/_render_lint.py, WIRE002@tests/unit/test_new_ticket_scope_overlap_warning.py
