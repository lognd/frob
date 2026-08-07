---
id: T-1502
title: WIRE001 text-scan misses memoize_per_run(_target)-shaped wiring (false positive
  on wrapper-bare-name callees)
state: done
kind: bug
origin: human
created: '2026-08-04'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_wire.py
- src/frob/gates/_cache_gate.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_wire.py
  reason: 'T-1502: narrow WIRE001 wrapper-bare-name detector fix scope'
  actor: logan
  at: '2026-08-05'
- op: add
  glob: src/frob/gates/_cache_gate.py
  reason: waiver-removal proof surface for the detector-shape fixes
  actor: logan
  at: '2026-08-05'
evidence:
- tests/test_gates.py::TestWireGate::test_new_function_passed_bare_to_a_wrapper_marker_is_not_flagged
- tests/test_gates.py::TestWireGate::test_new_function_named_like_a_wrapper_argument_but_never_passed_is_flagged
- tests/unit/test_lang_artifact_cache.py::TestParseFileArtifactCache::test_hit_skips_extract
- tests/unit/test_lang_artifact_cache.py::TestParseFileArtifactCache::test_miss_populates_cache
designated_repro_test: null
threat: null
component: null
---
WIRE001's _is_reached_outside_diff_tests requires a name( call-shaped occurrence and has no allowance for the bare-name-argument-to-a-wrapper shape frob.graph.callgraph._called_names already special-cases for DEAD001 (_WRAPPER_MARKER_NAMES, T-0583). Teach the WIRE001 text scan the same wrapper shapes so genuinely-wired functions like frob.lang._parse_file_with_artifact_cache (wrapped via memoize_per_run) stop needing frob:waive WIRE001 false-positive waivers. Refiled from w18p-artifacts draft T-draft-bbdfffa7, which died when that worktree was removed.