---
id: T-3777
title: fix win32 failures in hook-guard test suite
state: in-progress
kind: bug
origin: human
created: '2026-09-04'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/hooks/**
- tests/test_hook_root_write_guard.py
- tests/test_hook_frob_suggest.py
- tests/test_hook_root_cleanliness_detector.py
- .claude/hooks/_root_write_guard_lib.py
- design/frob.strata
- docs/design/registry/capability-via-ratchet.lock.json
- tickets/T-draft-70a3b4d4/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: .claude/hooks/_root_write_guard_lib.py
  reason: escape/tokenization fix in the shared shell-token helper root-write-guard.py
    depends on lives here, not under src/frob/hooks
  actor: logan
  at: '2026-09-04'
- op: add
  glob: design/frob.strata
  reason: SELFAUDIT001/SYS100 env.read capability declaration needs the two new test
    files' os.environ reads added to testsuite's via list
  actor: logan
  at: '2026-09-04'
- op: add
  glob: docs/design/registry/capability-via-ratchet.lock.json
  reason: SELFAUDIT001 SYS111 ratchet bump required alongside the env.read via-list
    addition
  actor: logan
  at: '2026-09-04'
- op: add
  glob: tickets/T-draft-70a3b4d4/**
  reason: filing a new out-of-scope ticket from within this ticket's worktree creates
    its own tickets/ file on this branch; frob:tickets convention exempts tickets/**
    writes generally but gate:SCOPE flags the specific new-ticket dir
  actor: logan
  at: '2026-09-04'
evidence:
- tests/test_hook_frob_suggest.py::TestHandRenameEditMultifile::test_frob_suggest_ack_env_var_bypasses_it
- tests/test_hook_frob_suggest.py::TestHandRenameEditMultifile::test_refactor_residue_prose_fix_never_fires
- tests/test_hook_frob_suggest.py::TestHandRenameEditMultifile::test_second_file_rewriting_same_module_import_fires
- tests/test_hook_frob_suggest.py::TestHandRenameEditMultifile::test_single_file_repeated_edits_never_fire
- tests/test_hook_frob_suggest.py::test_raw_worktree_still_fires
- tests/test_hook_frob_suggest.py::test_third_identical_command_is_blocked_again
- tests/test_hook_frob_suggest.py::test_unacked_first_attempt_is_still_blocked
- tests/test_hook_root_cleanliness_detector.py::test_dirty_root_in_agent_context_is_reported
- tests/test_hook_root_cleanliness_detector.py::test_dirty_root_reported_even_when_cwd_is_the_worktree
- tests/test_hook_root_write_guard.py::test_bash_appending_redirect_into_checkout_is_still_refused
- tests/test_hook_root_write_guard.py::test_bash_heredoc_appending_into_checkout_still_refused_with_delimiter_substring
- tests/test_hook_root_write_guard.py::test_bash_heredoc_redirected_into_checkout_is_still_refused
- tests/test_hook_root_write_guard.py::test_bash_redirect_into_primary_with_no_marker_is_refused
- tests/test_hook_root_write_guard.py::test_bash_redirect_target_inside_primary_via_home_relative_path_is_still_refused
- tests/test_hook_root_write_guard.py::test_bash_relative_redirect_into_checkout_is_still_refused
- tests/test_hook_root_write_guard.py::test_bash_set_prefixed_cd_into_primary_still_refused
- tests/test_hook_root_write_guard.py::test_bash_tee_into_checkout_is_still_refused
- tests/test_hook_root_write_guard.py::test_bash_ticket_land_still_refused_alongside_quoted_prose
- tests/test_hook_root_write_guard.py::test_bash_ticket_verb_with_no_cd_no_path_no_marker_is_refused
- tests/test_hook_root_write_guard.py::test_bash_truncating_redirect_into_checkout_is_still_refused
- tests/test_hook_root_write_guard.py::test_bash_variable_redirect_target_into_checkout_is_still_refused
- tests/test_hook_root_write_guard.py::test_land_with_no_worktree_flag_is_still_refused
- tests/test_hook_root_write_guard.py::test_land_with_unregistered_worktree_path_is_still_refused
- tests/test_hook_root_write_guard.py::test_no_marker_write_to_root_is_refused
- tests/test_hook_root_write_guard.py::test_notebook_edit_to_root_is_refused_with_no_markers
- tests/test_hook_root_write_guard.py::test_refusal_names_the_recovery_recipe
- tests/test_hook_root_write_guard.py::test_stale_agent_env_vars_do_not_exempt_a_root_write
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Windows CI failures in hook_root_write_guard (18), hook_frob_suggest (7), hook_root_cleanliness_detector (2). Likely shared root cause: path normalization / shell-command parsing / backslash vs forward-slash in the hook's checkout-path detection. Fix shared cause if present, confirm each via winrun.