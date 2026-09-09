## Done report

Changed:
- src/frob/gates/__init__.py::_subject_ticket_refs
- src/frob/gates/__init__.py::_commit_attribution_subjects
- src/frob/gates/__init__.py::_commit_exempts_file

Evidence:
- tests/gates_suite/test_prework.py::TestScopePrework::test_scope001_exempts_promoted_drafts_pre_promotion_filing_commit
- tests/gates_suite/test_prework.py::TestScopePrework::test_scope001_unresolved_draft_reference_does_not_exempt

Filed: none

Gates: frob check --ticket T-4362 clean except gate:TICK:TICK010 on
/home/logan/projects/frob/.git/frob-leases/T-4346.json, which names
T-4346 (a different in-progress ticket's stale lease) and is outside
T-4362's declared scope -- unrelated to this ticket's diff.
