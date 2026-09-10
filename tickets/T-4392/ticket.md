---
id: T-4392
title: LARGE001/waiver path-shape mismatch on Windows (backslash vs posix)
state: done
kind: bug
origin: human
created: '2026-09-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_waive.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/gates_suite/test_waive.py::TestMatchWaiverPathShape::test_backslash_waiver_path_still_matches_posix_violation
- tests/gates_suite/test_waive.py::TestMatchWaiverPathShape::test_backslash_waiver_still_matches_package_prefix
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Windows-only CI (run 34415921529, head 7ad69b30f): `[gate:LARGE] src/frob/testing/_collect.py:0  LARGE001  LARGE001: file has 867 lines (threshold: 800)`, not marked waived.

Ubuntu and macOS pass the same gate on the same commit (91 other LARGE001 findings ARE matched to waivers there). Mechanism: `frob:waive` directives are matched to a finding by rule id plus a path key. When that key is built from an OS-native path (`os.sep`-joined, or from a raw `Path` string instead of `.as_posix()`) on one side of the comparison and a POSIX-relative path (as `_check_large_file`'s `rel = path.relative_to(root).as_posix()` produces) on the other, the two never compare equal on Windows, where `os.sep` is `\\` -- the waiver silently fails to attach and the finding surfaces as an unwaived ERROR only on the platform whose native separator differs from the stored/generated key.

Find the LARGE001 waiver-matching path (`frob.gates._waive` or wherever `frob:waive` directives are looked up against `ArchSuggestion.file`/finding `file` keys) and normalize both sides to POSIX-relative form (forward slashes, `Path.as_posix()`) before comparing, so a waiver matches identically regardless of host path separator. Add a test that constructs a finding/waiver pair using a backslash-shaped path on Linux and asserts they still match (no unwaived finding).