---
id: T-1359
title: Make FMT001/REG010/REL002 Tier-A handlers' delegated writes crash-safe
state: done
kind: bug
origin: human
created: '2026-07-31'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_fmt_directives.py
- src/frob/registry/_staleness.py
- src/frob/release/**
- tests/test_gates_fmt_directives.py
- tests/test_registry_staleness.py
- tests/test_release.py
- docs/design/registry/EXHAUSTIVENESS-GATE.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_gates_fmt_directives.py
  reason: 'T-1359: crash-safety unit tests for the three write sites this ticket touches'
  actor: logan
  at: '2026-08-04'
- op: add
  glob: tests/test_registry_staleness.py
  reason: 'T-1359: crash-safety unit tests for the three write sites this ticket touches'
  actor: logan
  at: '2026-08-04'
- op: add
  glob: tests/test_release.py
  reason: 'T-1359: crash-safety unit tests for the three write sites this ticket touches'
  actor: logan
  at: '2026-08-04'
- op: add
  glob: docs/design/registry/EXHAUSTIVENESS-GATE.md
  reason: 'T-1359: SCOPE002 closure -- doc anchors on symbols already in this ticket''s
    scope'
  actor: logan
  at: '2026-08-04'
evidence:
- tests/test_gates_fmt_directives.py::TestWriteFormattedCrashSafety::test_leaves_original_on_replace_failure
- tests/test_gates_fmt_directives.py::TestWriteFormattedCrashSafety::test_preserves_crlf_newline
- tests/test_registry_staleness.py::TestSyncGateRuleEntriesCrashSafety::test_leaves_original_on_replace_failure
- tests/test_release.py::TestCrashSafeReleaseWrites::test_stamp_leaves_original_manifest_on_replace_failure
- tests/test_release.py::TestCrashSafeReleaseWrites::test_rewrite_pyproject_version_leaves_original_on_replace_failure
- tests/test_release.py::TestCrashSafeReleaseWrites::test_changelog_skeleton_entry_leaves_original_on_replace_failure
- tests/test_release.py::TestCrashSafeReleaseWrites::test_set_manifest_version_leaves_original_on_replace_failure
designated_repro_test: null
threat: null
component: null
---
T-1348 made every in-place file rewrite living directly in
src/frob/gates/_fix_engine.py (DOC007/DOC002/INV006-carry rewrites,
WAIVE004's waiver-line removal) crash-safe via atomic_write (temp file +
fsync + os.replace). Three OTHER Tier-A handlers -- FMT001, REG010,
REL002 -- delegate their actual disk writes to functions in different
modules that were out of T-1348's declared scope:

- FMT001 -> frob.gates._fmt_directives.format_paths (bare
  path.write_text)
- REG010 -> frob.registry._staleness.sync_gate_rule_entries (writes
  check-coverage.yaml)
- REL002 -> frob.release.rewrite_pyproject_version /
  changelog_skeleton_entry (writes pyproject.toml / CHANGELOG.md)

None of these route through a crash-safe write primitive today -- a land
killed mid-FMT001/REG010/REL002 could still leave one of THESE files
half-rewritten, the same T-1338 hazard class T-1348 closed for the other
three handlers. Convert these three write sites to
frob.tickets._store.atomic_write (or an equivalent local primitive) the
same way T-1348 did for _fix_engine.py's own direct writes.