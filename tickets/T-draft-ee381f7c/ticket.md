---
id: T-draft-ee381f7c
title: 'Windows-only: POSIX-path assumptions break config_path_defaults, narrative
  bulk, token_usage, docarch_structural'
state: queued
kind: bug
origin: agent
created: '2026-09-24'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: v0.534.0
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: null
branch: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while draining CI run 35951365410 (dev 9e0c89bb19), windows-latest job
only (does not reproduce on ubuntu/macos). Windows-only failures sharing a
POSIX-path-assumption root cause:

- tests/gates_suite/test_config_path_defaults.py::TestConfigPathDefaultGate::test_absolute_path_default_is_silent
  fires CONFIGPATH001 on a fixture default path literal '/abs/dir/state.json'
  -- this is a POSIX-absolute path, but on Windows os.path.isabs() (or
  whatever CONFIGPATH001's detector uses) returns False for it since it has
  no drive letter, so the detector wrongly calls it "relative".

- tests/narrative/test_bulk.py::TestApplyBulk::test_apply_moves_live_and_archived_skips_untargeted
  KeyError: 'live.py' -- the statuses dict is keyed by a path string that on
  Windows likely uses backslashes (or a different normalization) than the
  forward-slash key the test looks up.

- tests/unit/test_token_usage.py::TestCollectTicketUsage::test_sums_assistant_usage_fields
  KeyError: '\\tmp\\a.jsonl' -- the test's fake harness stores usage keyed by
  a posix-style str(Path) the code under test builds with a leading
  '/tmp/a.jsonl' literal; on Windows str(Path('/tmp/a.jsonl')) or similar
  produces backslashes, so the lookup key never matches the fixture's key.

- tests/gates/test_docarch_structural.py::TestDocarch002RatchetSeverity::test_baselined_finding_stays_warn_new_one_errors
  asserts new_file_violations is non-empty and gets [] -- likely the same
  class: a baseline/finding keyed or matched by a POSIX-style path string
  that never matches on Windows.

All four are cross-platform correctness bugs (whatever code under each test
builds/keys paths needs to use os-appropriate separators or PurePosixPath
consistently, not hardcode forward slashes and assume they match on
Windows) -- likely 4 separate small fixes in 4 different files sharing one
diagnosis category, not necessarily one shared code path. May need
splitting into per-file tickets once someone reads each implementation;
filed together here since the drain pass that found them ran out of time
to read all four production implementations.
