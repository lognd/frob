---
id: T-4280
title: policy._compiled_glob's pathspec match_file has the same unpinned-separators
  platform defect T-4155 fixed in excludes.is_excluded
state: queued
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
T-4155 fixed frob.excludes.is_excluded's separator platform-dependence (pathspec.PathSpec.match_file derives its separator-normalization set from os.sep/os.altsep when none is given, so a backslash-joined rel answers differently on linux vs Windows) by pinning separators=("\\",) explicitly. T-4155's own body flagged that src/frob/policy/__init__.py's _compiled_glob (also built via pathspec.PathSpec.from_lines("gitignore", ...)) and its match_file call site have inherited the identical unpinned default, and nothing has measured it on Windows. Apply the same fix (pin separators explicitly on the match_file call in this module) and prove it on real Windows before/after, the same way T-4155 did.