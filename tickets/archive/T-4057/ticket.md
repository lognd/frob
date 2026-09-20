---
id: T-4057
title: 'Windows CI cluster B: ~/.claude HOME-relative fixtures use HOME env (ignored
  by Path.home() on Windows); stale-guard also has a CRLF/autocrlf false-negative'
state: done
kind: bug
origin: human
created: '2026-09-06'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/test_telemetry.py
- tests/unit/test_skills_sync.py
- tests/unit/test_sync_claude_config_stale_guard_t3408.py
- .claude/hooks/sync-claude-config.py
- src/frob/scaffold/_skills_sync.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/test_telemetry.py::test_redundant_rerun_not_flagged_when_home_claude_config_changed
- tests/test_telemetry.py::test_redundant_rerun_still_flags_when_nothing_changed_at_all
- tests/unit/test_skills_sync.py::TestRun::test_run_defaults_to_home_claude_when_no_override_given
- tests/unit/test_sync_claude_config_stale_guard_t3408.py::TestStaleManagedSourcesAndWriteRefusal::test_stale_file_skipped_forward_file_synced
- tests/unit/test_sync_claude_config_stale_guard_t3408.py::TestIsSourceStaleVsMain::test_crlf_working_tree_copy_is_not_mistaken_for_an_edit
- tests/unit/test_sync_claude_config_stale_guard_t3408.py::TestIsSourceStaleVsMain::test_crlf_working_tree_own_edit_still_reads_as_an_edit
designated_repro_test: tests/unit/test_sync_claude_config_stale_guard_t3408.py::TestIsSourceStaleVsMain::test_crlf_working_tree_copy_is_not_mistaken_for_an_edit
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-3936 Cluster B: two root causes. (1) test_telemetry.py's home_claude_config_changed
test and test_skills_sync.py's defaults-to-home test monkeypatch.setenv(HOME) but
production reads Path.home() (src/frob/app/telemetry/_state.py, src/frob/scaffold/
_skills_sync.py) which on Windows resolves via ntpath.expanduser: USERPROFILE or
HOMEDRIVE+HOMEPATH only, HOME is never consulted. So the fixture's fake home is
silently ignored on real Windows and the code touches the runner's real profile
dir instead -- a TEST-FIXTURE bug, fix by monkeypatch.setattr(Path, "home",
staticmethod(lambda: fake_home)) matching the pattern test_sync_claude_config_
stale_guard_t3408.py already uses correctly elsewhere in the same file.
(2) test_sync_claude_config_stale_guard_t3408.py's stale_file_skipped test already
uses that Path.home patch (not HOME env) so it is a DIFFERENT mechanism: stale_
managed_sources() in .claude/hooks/sync-claude-config.py compares source_path.
read_text() (working tree, CRLF under Windows autocrlf) against git show output
(LF-normalized blob content), so source_text != merge_base_text is spuriously
true on Windows and the T-3408 stale-source guard never fires there -- a real
consumer-affecting bug, fix by normalizing line endings before comparison in
_is_source_stale_vs_main plus a CRLF regression test. The CRLF claim still needs
confirmation on real Windows CI.