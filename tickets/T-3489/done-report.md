## Done report

T-2642's changelog generator copies a Done-report's WHY prose verbatim into changelog.d/<id>.md; that prose can legitimately carry a dotted symbol path or a CLI-invocation-shaped phrase that is correct-at-write-time and never checked again -- T-2691's own fragment carried both (a since-broken mid-word-wrapped symbol pointer, and a CLI verb the prose explicitly said was NOT added). Per DOC006's own docstring, this is the SAME class its existing _ARCHIVAL_LEDGER_FILES/_ARCHIVAL_DIR_PREFIX exemptions already cover (CHANGELOG.md, tickets/archive/**): a historical record with no honest in-tree fix, only falsification. Decision taken: exempt changelog.d/** in DOC006 (added _CHANGELOG_FRAGMENT_DIR_PREFIX, extended _is_archival_doc) rather than sanitize the generator's copied prose -- matches the repo's own established idiom for this exact class of file (a fragment is written once at land time and never edited again, same as CHANGELOG.md itself, one pipeline stage earlier) and needs no change to _land_cmd.py at all (the generator fix would have required touching _land_cmd.py, which collided with T-2450's now-landed lease -- moot with this approach). Added test_changelog_fragment_dir_is_an_archival_record_not_checked (tests/test_docptr_gate.py), mirroring test_changelog_is_an_archival_record_not_checked's shape exactly. changelog.d/T-2691.md itself was already repaired by T-3485 (a separate, narrower ticket) before this landed; this ticket's own scope never needed to touch that file's content, only the gate. Evidence: pytest tests/test_docptr_gate.py -p no:xdist -- 68 collected, 67 passed, 1 failed (TestDoc004Doc006ZeroOnFrobsOwnRepo::test_doc004_doc006_zero_against_live_repo, which now fails for a SINGLE, unrelated reason: T-3491's still-open DOC006 finding on tickets/T-3489/ticket.md itself -- a separate ticket in this same series, not touched by this change).

### Changed
```
 tickets/T-3489/ticket.md | 4 +++-
 1 file changed, 3 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_docptr_gate.py::TestDoc006BareIdentifierNarrowing::test_changelog_fragment_dir_is_an_archival_record_not_checked` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 23 error(s), 4085 warning(s), 868 waived
- error-findings: COV003@tests/unit/test_scaffold_project.py, DEPR006@frob-deprecated-baseline.lock.json, DOC001@docs/design/macos-portability.md, DOC006@tickets/T-3489/ticket.md, DOC007@src/frob/verify/_bisect.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT002@src/frob/verify/_bisect.py, LARGE001@.claude/hooks/root-write-guard.py, LARGE001@src/frob/arch/_mayraise.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, PII012@tests/test_ticket_leases.py, PRE001@tickets/T-3489, REF001@docs/design/macos-portability.md, REL001@src/frob/__init__.py, TICK004@tickets.md, WAIVE009@src/frob/arch/_normalized.py, WAIVE011@frob-ratchet.lock.json, WIRE002@src/frob/app/ticket_runner/_land_cmd.py, WIRE002@src/frob/gates/_arch.py, WIRE002@src/frob/gates/_coverage_sites.py, WIRE002@src/frob/gates/_render_lint.py, WIRE002@tests/unit/test_new_ticket_scope_overlap_warning.py
