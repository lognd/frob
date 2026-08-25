---
id: T-2892
title: 'T-2384: bind evidence to acceptance criteria and close epic'
state: done
kind: docs
origin: human
created: '2026-08-25'
priority: high
blocked_by:
- T-2891
parent: T-2384
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tickets/T-2384/ticket.md
evidence_scope:
- tests/integration/test_interfaces.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'BUG002 front door (T-2393): ticket-hygiene only: binds existing test evidence
    to T-2384''s acceptance criteria, no src/ change'
  actor: logan
  at: '2026-08-25'
  old_length: 2863
  new_length: 2995
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
MEASUREMENT (2026-08-25, this ticket's own filing): all four of T-2384's acceptance criteria are already satisfied by landed child tickets, but the epic's acceptance[].evidence arrays are still empty and it remains state=queued.

- Criterion 1 (gates scan declared source roots, must-now-fire + must-still-pass proven per gate): MET. env_var_doc_gate (T-2389/_env_var_docs.py) and root_asset_dir_gate (_root_asset_dirs.py) both retargeted onto frob.lang.declared_source_prefixes/declared_project_package_name; tests/test_gates.py::TestEnvVarDocGate::test_undocumented_env_var_fires_for_a_differently_named_project and TestRootAssetDirGate::test_unreferenced_root_directory_fires_for_a_differently_named_project are the must-now-fire fixtures (lograder-named project, no src/frob/ in the fixture), each paired with a frob-repo must-still-pass control in the same class. tickets/_models.py OVER_BROAD_LITERAL_GLOBS (T-2771) and app/ticket_runner/_new.py's related-check-function suggestion (T-2772) were retargeted the same way. Ran: uv run frob check --only gates --json -- zero ENV001/ROOT001/PORT001 findings on frob's own tree (the must-still-pass control, live).
- Criterion 4 (single public resolver, no second implementation): MET. frob.lang._nodes exposes _declared_python_source_roots (T-2195) plus the public declared_source_prefixes/declared_project_package_name wrappers; PORT001 (src/frob/gates/_port_selfcheck.py, T-2388, widened repo-wide by T-2405) is the durable meta-check against a second implementation reappearing, and currently reports zero findings repo-wide.
- Criteria 2 and 3 (sync-skills cooperative, provenance-aware, idempotent, first-run-against-hand-maintained-dir deletes nothing): MET by T-2386 (src/frob/scaffold/_skills_sync.py's SyncManifest). tests/unit/test_skills_sync.py::test_second_repo_does_not_delete_first_repos_entries, test_hand_maintained_entry_is_never_deleted_or_overwritten, test_hand_maintained_entry_collides_instead_of_being_overwritten, test_same_repo_sync_twice_is_a_no_op_second_run, test_manifest_records_only_this_repos_owned_entries directly cover criteria 2 and 3. Ran: uv run python -m pytest tests/unit/test_skills_sync.py -q -- 24 passed (combined with test_port_selfcheck.py in the same run).

REMAINING WORK (this ticket, scope limited to the ticket file itself): cite the test node ids above against T-2384's four acceptance[].evidence lists via frob ticket evidence, re-verify each --check-repro is not needed (docs-kind, no repro), and close/drop the epic once evidence is bound. Do NOT touch src/ -- no further portability code change is indicated by measurement; this is ticket-hygiene only. If a re-run of frob check --only gates at land time surfaces any non-zero ENV001/ROOT001/PORT001 count against frob's own tree, STOP and re-open scope investigation instead of forcing evidence to close.

frob:no-behavior-change reason="ticket-hygiene only: binds existing test evidence to T-2384's acceptance criteria, no src/ change"