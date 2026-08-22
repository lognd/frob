## Done report

Relocated the two archgate-specific `arch_examined_sites` regression
tests (`test_archgate_examined_sites_include_a_real_python_file`,
`test_archgate_examined_sites_exclude_an_unparseable_file`) from
`tests/unit/gates/test_examined_sites.py::TestAttachExaminedSites` into
a new `tests/test_arch_gate.py::TestArchExaminedSites` class -- that
file is already scoped alongside `src/frob/gates/_arch.py` for every
other `_arch.py`-facing test, so the `frob:tests` edge those two cases
carry to `arch_examined_sites` no longer widens a coverage-family-
extension ticket's scope into `_arch.py`'s full test surface (T-2012's
finding).

Work done:
1. Moved both test bodies verbatim into a new `TestArchExaminedSites`
   class in tests/test_arch_gate.py, with local `attach_examined_sites`/
   `site_examined` imports and a same-shape `_empty_report()` helper
   (deliberately duplicated rather than imported cross-module, matching
   this file's existing style of self-contained helpers).
2. Removed the two tests from `TestAttachExaminedSites` in
   tests/unit/gates/test_examined_sites.py, leaving that class's
   family-agnostic cases (`test_families_this_module_does_not_know_
   about_stay_absent`, `test_preserves_examined_sites_a_prior_caller_
   already_attached`) in place along with the still-used imports.
3. Re-pointed the two `frob:tests` directives on
   `src/frob/gates/_arch.py::arch_examined_sites` (lines 180-181) at the
   new `tests/test_arch_gate.py::TestArchExaminedSites` node ids.
4. Grepped the ledger for both old node ids before moving (per the
   playbook's evidence-orphaning warning) and found T-1921 cites both as
   bound evidence (10 evidence ids each, flat list); T-2012/T-2028 only
   mention them in prose, no evidence binding. Re-pointed T-1921's two
   evidence citations with `frob ticket evidence T-1921 --replace
   <old-node-id> <new-node-id> --reason ...` (atomic rebind across the
   flat evidence list AND any acceptance-criterion binding) rather than
   hand-editing tickets.md.
5. Verified: `frob check --no-cache --json` before my evidence rebind
   showed 3 new COV003 errors (2x T-1921, matching the moved node ids,
   plus a pre-existing T-2365 one); after the rebind, the T-1921 COV003
   findings are gone and the remaining error set (T-1688/T-2365 COV003,
   CYCLE001, COV001, DRIFT001/002, PRE001/SCOPE001 on the uncommitted
   diff, SEC110, TEST001, TICK003/004, CLAUDE001) matches the
   pre-existing baseline this series did not touch.

### Evidence
- tests/test_arch_gate.py::TestArchExaminedSites::test_archgate_examined_sites_include_a_real_python_file
- tests/test_arch_gate.py::TestArchExaminedSites::test_archgate_examined_sites_exclude_an_unparseable_file
- tests/unit/gates/test_examined_sites.py::TestAttachExaminedSites::test_families_this_module_does_not_know_about_stay_absent
- tests/unit/gates/test_examined_sites.py::TestAttachExaminedSites::test_preserves_examined_sites_a_prior_caller_already_attached

### Changed
```
 tickets/T-1820/ticket.md |  8 +++++++-
 tickets/T-1831/ticket.md |  8 +++++++-
 tickets/T-1921/ticket.md | 20 ++++++++++++++++++--
 tickets/T-2301/ticket.md | 12 +++++++++++-
 4 files changed, 43 insertions(+), 5 deletions(-)
```

### Evidence
- `tests/test_arch_gate.py::TestArchExaminedSites::test_archgate_examined_sites_include_a_real_python_file` (pytest node id, verified passing when recorded)
- `tests/test_arch_gate.py::TestArchExaminedSites::test_archgate_examined_sites_exclude_an_unparseable_file` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_examined_sites.py::TestAttachExaminedSites::test_families_this_module_does_not_know_about_stay_absent` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_examined_sites.py::TestAttachExaminedSites::test_preserves_examined_sites_a_prior_caller_already_attached` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 16 error(s), 824 warning(s), 708 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, COV003@tickets/T-1688, COV003@tickets/T-2365, CYCLE001@src/frob/__init__.py, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/tickets-data-storage.md, PRE001@tickets/T-2301, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md
