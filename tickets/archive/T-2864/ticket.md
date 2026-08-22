---
id: T-2864
title: 'F401/F822: T-2851 split left import/export hygiene debt in _mutation_evidence.py/_bug_repro.py'
state: done
kind: bug
origin: human
created: '2026-08-22'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_mutation_evidence.py
- src/frob/gates/_bug_repro.py
- docs/guides/agent-playbook.md
evidence_scope:
- tests/test_gates_mutation_evidence.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: docs/guides/agent-playbook.md
  reason: 'coordinator directive: record the split-hygiene checklist (REF001/DRIFT002/COV001/TEST001/F401/F822)
    at the point of use in the playbook, not only in this ticket''s Done report'
  actor: logan
  at: '2026-08-22'
body_changes:
- mode: append
  reason: record no-behavior-change rationale before landing (import/export hygiene
    fix, zero behavior change)
  actor: logan
  at: '2026-08-22'
  old_length: 1205
  new_length: 2384
evidence:
- tests/test_gates_mutation_evidence.py::TestBug002Waiver::test_reason_present_suppresses
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: e6baf3b9cf1c0cc87d4d2e5cdaf60f31e7fd5984
---
T-2851 extracted the BUG002/must-still-pass repro-classification family out of src/frob/gates/_mutation_evidence.py into a new src/frob/gates/_bug_repro.py (the split named in T-2827's own waiver text) -- an otherwise excellent split (retargeted 40 mock.patch call sites with a positive control) that shipped without import/export hygiene: 20 F401 (unused-import) findings in _mutation_evidence.py (imports that were only needed by the code that moved out) and 1 F822 (name in __all__ that no longer resolves) in _bug_repro.py. Same class of regression as T-2846 (rust split, fixed by T-2855) and T-2695 (_store.py migration split) -- a file split moves symbols without re-auditing the OLD file's now-dead imports or the NEW file's export surface. Found via unbudgeted 'frob check --json' re-measurement while verifying T-2855's land (main went 115 -> 85 errors; these are part of the remaining 85, unrelated to T-2855's own scope). Fix: for each F401, git grep the name first -- an import kept solely for re-export will look unused to ruff and break a consumer if deleted blind; delete only genuinely-dead ones. For the F822, determine via importers whether to restore the export or drop it from __all__.

frob:no-behavior-change reason="import/export hygiene fix only -- removes 15 genuinely-dead imports (os/re/shutil/subprocess/sys/tempfile/enum.Enum/enum.auto/typani.Ok/Err/Result/frob.gitio.run_argv/frob.process._guard.ProcessGuardError/exec_enabled/guarded_subprocess_run) from _mutation_evidence.py that its own T-2851 split left behind for code that moved to _bug_repro.py, adds a noqa comment documenting the 5 remaining genuinely-used re-export imports, and removes one name (mutation_evidence_violations) from _bug_repro.py's __all__ that was never defined in that file. Verified each F401 name has zero non-import-line occurrences in the file and is not re-exported via __all__ or imported from this module by any other file (git grep across the repo) before deleting. Verified via a full targeted pytest re-run (tests/test_gates_mutation_evidence.py + tests/gates/test_mutation_evidence_err_branches.py + tests/test_tickets_mutation_evidence.py mutation_evidence/bug_repro subset, all passed) and frob check --only lint (ruff-check 0 findings on both files, was 21). BUG002 designated-repro requirement does not apply: there is no behavior to reproduce a failure for."