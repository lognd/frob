## Done report

Triaged all 6 sub-items:

1. export_golden k8s/iam drift -- ALREADY RESOLVED upstream by the time
   this worktree synced to dev (both tests pass with no local change).

2. websec_rls_llm webesc417 missing finding -- FIXED. _SYSTEM_PROMPT_RE
   in src/frob/webapp/_websec_rls_llm.py required the role/content dict
   keys on the same line ([^\n]*); a multi-line dict literal (the
   webesc417_positive fixture's own shape, and the common Python
   formatting convention) never matched, so WEBSEC417 silently never
   fired on it. Widened the gap to [\s\S]*? to cross a newline.

3. TICK008 on the live ledger -- ALREADY RESOLVED upstream (passes with
   no local change; the ledger schema drift that produced the earlier
   'due'/'rank' unknown-field warnings has since been migrated, per
   T-5751's landing visible in this worktree's dev merge).

4. scaffold_dx python-tool template failing frob check -- FIXED. Two
   real template bugs: (a) __main__.py.j2 put a frob:doc anchor
   directly on the PRIVATE _build_parser helper (COV007) instead of its
   already-documented public caller main(); (b) logger.py.j2's
   get_root_logger had no unit test (TEST001), unlike its sibling
   get_logger. Removed the anchor, added the missing test.

5. SELFAUDIT001 SYS119 templated-assume warnings -- NOT a small fix.
   34 self-audit assume entries across 7 CWE families (CWE-502/639/78/
   79/89/918/94) are copy-pasted across modules with only the node name
   substituted; each needs a real module-owned rationale, which is
   content-writing across the strata self-model corpus, not a
   verifiable code change. Filed T-draft-09d74d21.

6. check-coverage registry count 666 vs 664 -- same gap T-6525 is
   already fixing (docs/design/registry/check-coverage.yaml is leased
   by T-6525's in-progress worktree); not touched here, no new ticket
   filed since it is already tracked (T-6525's own done-report and its
   follow-up T-draft-3fa4f67b cover the residual count/registry debt).

### Changed
```
 .../scaffold/data/types/python-tool/__main__.py.j2 |  1 -
 .../python-tool/tests/unit/test_logging.py.j2      |  9 ++++-
 src/frob/webapp/_websec_rls_llm.py                 |  8 ++++-
 tickets/T-6528/ticket.md                           | 30 ++++++++++++++--
 tickets/T-draft-09d74d21/ticket.md                 | 40 ++++++++++++++++++++++
 5 files changed, 82 insertions(+), 6 deletions(-)
```

### Evidence
- `tests/unit/test_websec_rls_llm.py::test_websec_rls_llm_findings_fixture[webesc417_positive-WEBSEC417-True]` (pytest node id, verified passing when recorded)
- `tests/system/test_scaffold_dx.py::test_python_toolchain_scaffold_passes_check_immediately[python-tool]` (pytest node id, verified passing when recorded)
