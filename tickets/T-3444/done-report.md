## Done report

src/frob/gates/_refs.py's _DEFAULT_ROOT_MANIFEST_EXEMPT now exempts tickets-archive.md alongside tickets.md (T-3249's sibling), mirroring T-3249's reasoning: it is ledger-v1's own sibling ledger file, spliced/updated by _land_squash.py's T-0959 splice the first time any ticket in a project completes, read only by frob ticket/frob check tooling and never referenced from other tracked source files. Added two REF001 tests mirroring T-3249's tickets.md coverage (root exemption must-fire, nested-path must-stay-quiet regression), and removed T-3442's xfail(strict=True) on test_cli_land_invoked_with_root_equal_to_worktree_still_verifies, which now genuinely passes (was XPASSing under the xfail). Evidence: all 3 tests pass locally, node-id run -p no:xdist, exitstatus=0. Filed T-3457 for an unrelated out-of-scope finding (strata_core native extensions never release the GIL) discovered while working the preceding ticket in this series (T-3449), not part of this ticket's scope. Gates: frob check --ticket T-3444 --budget 300 -- gate:REF passes (0 errors, 2 warnings, 4 waived); other gate families show repo-wide pre-existing failures unrelated to this two-file change, per the tool's own note that --ticket scoping does not filter those counts to this ticket's touched set.

### Changed
```
 tickets/T-3444/ticket.md | 6 +++++-
 1 file changed, 5 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_refs_gate.py::TestDefaultRootManifestExempt::test_root_tickets_archive_md_is_exempt_with_no_declaration` (pytest node id, verified passing when recorded)
- `tests/test_refs_gate.py::TestDefaultRootManifestExempt::test_nested_tickets_archive_md_still_subject_to_ref001` (pytest node id, verified passing when recorded)
- `tests/test_ticket_work_and_land_finish.py::TestLandProofAndFinish::test_cli_land_invoked_with_root_equal_to_worktree_still_verifies` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 14 error(s), 4040 warning(s), 855 waived
- error-findings: COV001@src/frob/tickets/_scope.py, COV003@tickets/T-3410, DEPR006@frob-deprecated-baseline.lock.json, DOC006@tickets/T-3411/ticket.md, DOC007@tests/unit/test_main_entry.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/tickets/_scope.py, DRIFT002@tests/unit/test_main_entry.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, PRE001@tickets/T-3444, REL001@src/frob/__init__.py, SELFAUDIT001@design, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json
