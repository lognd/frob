---
id: T-3429
title: Declare testsuite exec/fs.write/env.read capabilities for tests/system/test_coverage_sigterm.py
state: done
kind: bug
origin: human
created: '2026-08-29'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'BUG002 waiver: fix is a declaratory design-model correction for T-3420''s
    new test fixture'
  actor: logan
  at: '2026-08-29'
  old_length: 715
  new_length: 1636
evidence:
- tests/unit/test_lang_strata.py::TestGrammarAuthoritativeSymbolsCorpusWide::test_every_tracked_strata_file_symbol_count_matches_grammar_declared_count
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
found while working T-3420: the new tests/system/test_coverage_sigterm.py fixture (subprocess spawn, tmp_path writes, os.environ reads for the T-3420 SIGTERM-deadlock repro) trips gate:SELFAUDIT001 (exec/fs.write/env.read observed but not declared on the testsuite node) because it is not listed in design/frob.strata's testsuite node 'may exec/fs.write/env.read via ...' lists. Could not fix directly: design/frob.strata is under a LIVE cross-worktree scope lease held by T-3416 (a different, pre-existing SELFAUDIT001 gap) at the time T-3420 landed. Add tests/system/test_coverage_sigterm.py to the three via-lists (may "exec", may "fs.write", may "env.read") on the testsuite node once T-3416 releases the lease.

frob:waive BUG002 reason="this ticket adds tests/system/test_coverage_sigterm.py to the testsuite node's may exec/fs.write/env.read via-lists in design/frob.strata -- a declaratory design-model correction (T-3420's new test fixture was never added to the model), not a code-behavior defect with its own fail-then-pass unit test. Confirmed by direct re-run: tests/unit/strata/test_selfconform.py::TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant no longer names test_coverage_sigterm.py in its violation list after this fix; the only violations it still reports are the 2 unrelated tests/unit/test_arch_srp.py fs.read sites already tracked at T-3430. test_every_tracked_strata_file_symbol_count_matches_grammar_declared_count (bound as evidence) parses the real design/frob.strata this change edits and passes cleanly against the real repo, guarding against a malformed edit." follow_up="T-3430"