---
id: T-4280
title: policy._compiled_glob's pathspec match_file has the same unpinned-separators
  platform defect T-4155 fixed in excludes.is_excluded
state: in-progress
kind: bug
origin: human
created: '2026-09-08'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/policy/__init__.py
- tests/test_policy.py
scope_breadth_ack: true
scope_breadth_ack_reason: policy/__init__.py's load_policy/policy_gate carry a pre-existing
  frob:doc target on docs/modules/gates.md unrelated to this ticket's fix (the _files_under
  separator-pinning bug and its own frob:tests-bound evidence, both already in scope);
  not chasing that unrelated doc-anchor closure edge to keep this fix's scope minimal.
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/test_policy.py
  reason: 'T-4280: bound evidence for the fix lives in tests/test_policy.py'
  actor: logan
  at: '2026-09-08'
evidence:
- tests/test_policy.py::TestRules::test_backslash_joined_path_matches_a_posix_glob_on_every_platform
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-4155 fixed frob.excludes.is_excluded's separator platform-dependence (pathspec.PathSpec.match_file derives its separator-normalization set from os.sep/os.altsep when none is given, so a backslash-joined rel answers differently on linux vs Windows) by pinning separators=("\\",) explicitly. T-4155's own body flagged that src/frob/policy/__init__.py's _compiled_glob (also built via pathspec.PathSpec.from_lines("gitignore", ...)) and its match_file call site have inherited the identical unpinned default, and nothing has measured it on Windows. Apply the same fix (pin separators explicitly on the match_file call in this module) and prove it on real Windows before/after, the same way T-4155 did.