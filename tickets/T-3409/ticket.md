---
id: T-3409
title: Update design/frob.strata SYS100 fs.read capability for stats/_agentic split
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
- src/frob/stats/_agentic_shared.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/stats/_agentic_shared.py
  reason: must remove the now-obsolete frob:waive SELFAUDIT001 follow_up=T-3409 comment
    this ticket's own design/frob.strata fix discharges -- land refused close while
    the row still cites T-3409 as a live tracker
  actor: logan
  at: '2026-08-29'
body_changes:
- mode: append
  reason: 'BUG002 waiver: fix is a declaratory design-model correction; closes the
    T-3416/T-3409 SYS100 pair but a new unrelated T-3430 drift now trips the same
    test'
  actor: logan
  at: '2026-08-29'
  old_length: 620
  new_length: 1736
evidence:
- tests/unit/test_lang_strata.py::TestGrammarAuthoritativeSymbolsCorpusWide::test_every_tracked_strata_file_symbol_count_matches_grammar_declared_count
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: dbf327edcdd3d3a0648ee932fb65ae8af4910326
---
T-3059 split src/frob/stats/_agentic.py's fs.read caller (_load_events) out into a new sibling module src/frob/stats/_agentic_shared.py. design/frob.strata's SYS100 fs.read capability list (line ~847) still names src/frob/stats/_agentic.py, which no longer performs any filesystem read directly -- it should be replaced with src/frob/stats/_agentic_shared.py. Could not fix directly under T-3059 because design/frob.strata was held by a live cross-worktree lease (T-3388) at the time; SELFAUDIT001 flags the drift (capability 'fs.read' observed at src/frob/stats/_agentic_shared.py:36 but not declared) until this lands.

frob:waive BUG002 reason="this ticket replaces src/frob/stats/_agentic.py with src/frob/stats/_agentic_shared.py in core's may fs.read via declaration in design/frob.strata -- a declaratory design-model correction, not a code-behavior defect with its own fail-then-pass unit test. Together with T-3416 (already landed, the src/frob/process/_proc_scan.py sites) this closes all 6 SYS100 fs.read violations named in the T-3416/T-3409 pair -- confirmed by direct re-run: after both fixes, test_repo_design_and_declarations_are_self_conformant no longer reports the src/frob/stats/_agentic_shared.py:42 violation at all; the only violations it reports now are 2 NEW, unrelated ones (tests/unit/test_arch_srp.py:616/:650, testsuite node) that appeared from a concurrent land on main after T-3416 landed and are tracked separately at T-3430, filed while working this ticket. test_every_tracked_strata_file_symbol_count_matches_grammar_declared_count (bound as evidence) parses the real design/frob.strata this change edits and passes cleanly against the real repo, guarding against a malformed edit." follow_up="T-3430"