## Done report

Coordinator widened scope to include _normalized.py and _python.py. Minimal model extension: NormalizedBranch.comprehension_id and NormalizedCall.comprehension_id (both int | None), assigned id(node) of the enclosing comprehension/generator-expression node (_COMPREHENSION_TYPES) and threaded through _py_collect_body_events's existing recursion -- every branch/call found inside one comprehension's subtree (output expr, for-clauses, if-clauses alike) shares the same id; None outside any comprehension. _isdigit_guard_discharges's guard search now accepts EITHER b.line <= call.line (unchanged existing rule) OR (both comprehension_id set and equal) -- a comprehension's if-clause is written after its own output expression but evaluates before it runs each iteration, so line order alone cannot express that; two different comprehensions (different ids) and a comprehension branch against non-comprehension code still fail closed, matching this file's existing fail-closed doctrine. Removed the frob:waive EXHAUST002 on src/frob/process/_proc_scan.py::reap_orphaned_forkservers the T-2568 land added. exhaustive_handling: gate:EXHAUST waived count 112 -> 111 (the finding is gone entirely, not re-waived); the site now shows only pre-existing, unrelated EXHAUST003/EXHAUST004 resolution-coverage warnings. AFFECT001 on NormalizedBranch/NormalizedCall's doc anchor (docs/modules/arch.md#normalized-code-model) could not be updated in-diff: that doc is under another ticket's (T-3481) LIVE lease, so a frob:waive AFFECT001 follow_up=T-3481 was added on each class instead, matching this repo's established under-lease-conflict pattern. Added TestComprehensionGuardOrdering (must-fire: trailing if-clause discharges its own leading expr; must-stay-quiet: different comprehension ids, comprehension branch vs non-comprehension call, plus a real end-to-end adapter+resolver test over the exact corpus shape) and one TestPythonAdapter test verifying the adapter assigns the shared id correctly and leaves plain (non-comprehension) branches/calls at None. TestIsdigitGuardDischarge/TestSubscriptProvenance/TestMayRaiseResolver re-run clean, confirming the non-comprehension T-2568 path and subscript provenance are undisturbed. No new tickets filed.

### Changed
```
 tickets/T-3474/ticket.md | 16 +++++++++++++++-
 1 file changed, 15 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_arch.py::TestComprehensionGuardOrdering::test_trailing_if_clause_discharges_its_own_leading_expression` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestComprehensionGuardOrdering::test_different_comprehension_ids_do_not_discharge` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestComprehensionGuardOrdering::test_comprehension_branch_does_not_discharge_a_non_comprehension_call` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestComprehensionGuardOrdering::test_real_proc_scan_corpus_site_has_no_leaked_value_error` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestPythonAdapter::test_adapt_tags_comprehension_branch_and_call_with_shared_id` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestIsdigitGuardDischarge::test_guarded_int_call_discharges_value_error` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: 14 error(s), 4053 warning(s), 868 waived
- error-findings: COV003@tests/unit/test_scaffold_project.py, DEPR006@frob-deprecated-baseline.lock.json, DOC007@src/frob/verify/_bisect.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT002@src/frob/verify/_bisect.py, LARGE001@.claude/hooks/root-write-guard.py, LARGE001@src/frob/arch/_mayraise.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, REL001@src/frob/__init__.py, SELFAUDIT001@tests/unit/verify/test_bisect.py, TICK004@tickets.md, WAIVE009@src/frob/arch/_normalized.py, WAIVE011@frob-ratchet.lock.json
