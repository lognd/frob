---
id: T-2723
title: Gate cache is not invalidated by a frob upgrade, so consumers keep seeing pre-fix
  findings on an unchanged tree
state: done
kind: bug
origin: human
created: '2026-08-20'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_gate_cache.py
- tests/test_gate_cache.py
- docs/modules/serve.md
- docs/modules/gates.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_gate_cache.py
  reason: narrow to the cache-key module fixing T-2723 and its test file
  actor: logan
  at: '2026-08-20'
- op: add
  glob: tests/test_gate_cache.py
  reason: narrow to the cache-key module fixing T-2723 and its test file
  actor: logan
  at: '2026-08-20'
- op: add
  glob: docs/modules/serve.md
  reason: doc targets for symbols this ticket edits
  actor: logan
  at: '2026-08-20'
- op: add
  glob: docs/modules/gates.md
  reason: doc targets for symbols this ticket edits
  actor: logan
  at: '2026-08-20'
evidence:
- tests/test_gate_cache.py::TestGateBuildFingerprint::test_upgrade_forces_real_replay_on_unchanged_tree
- tests/test_gate_cache.py::TestGateBuildFingerprint::test_same_build_same_tree_still_replays_twice
- tests/test_gate_cache.py::TestGateBuildFingerprint::test_tree_change_still_invalidates_under_same_build
- tests/test_gate_cache.py::TestGateBuildFingerprint::test_extra_key_changes_when_build_fingerprint_changes
- tests/test_gate_cache.py::TestGateBuildFingerprint::test_extra_key_stable_for_same_build
- tests/test_gate_cache.py::TestGateBuildFingerprint::test_replay_fingerprint_changes_when_build_fingerprint_changes
- tests/test_gate_cache.py::TestGateBuildFingerprint::test_real_fingerprint_is_stable_and_never_raises
designated_repro_test: tests/test_gate_cache.py::TestGateBuildFingerprint::test_upgrade_forces_real_replay_on_unchanged_tree
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: b35f47220b8df35922128690bf88cfc38e48e0dc
---
## Measured, 2026-08-20, in a real downstream consumer repo

T-2706 fixed LANG004 so it no longer reports frob's own `src/frob/` paths
into consumer repos. After landing it AND reinstalling the tool with
`make install-tool`, the consumer repo still reported the identical 4
findings:

    frob check --only lang_conformance --only capability_conformance
      -> 4 LANG004 findings anchored at src/frob/lang/_support.py

    same command with --no-cache
      -> 0

The fix was present in the installed build (verified: the guard
`if not is_frob_own_repo(repo_root):` at `_lang_conformance.py:731`, and
the installed file byte-identical in line count to source). Calling the
gate directly confirms it is correct in both directions:

    capability_conformance_gate: 7 language(s) checked, 4 violation(s)
    /home/logan/projects/frob         -> violations: 4   (still fires, correct)
    /home/logan/projects/aprog-public -> violations: 0   (suppressed, correct)

So the 4 findings were a STALE GATE-CACHE REPLAY.

## The defect

The gate cache keys on TREE CONTENT ("[REPLAY age=..., unchanged tree]"),
but apparently not on the frob version or the gate code that produced the
entry. So upgrading frob does not invalidate cached gate results, and a
consumer with an unchanged tree keeps seeing PRE-FIX findings
indefinitely.

## Why this matters more than an ordinary staleness bug

The whole point of shipping a gate fix is that consumers stop seeing the
false positive. As-is, they upgrade, re-run, see the identical output, and
reasonably conclude the fix did not ship. That is exactly the path I went
down: I had already begun diagnosing this as "the fix does not work in
production", the same shape as T-2690, and only `--no-cache` separated
them.

It also silently undermines every gate fix this drive landed for that
consumer (DOC006, DOC008, DOC010, SYS004) -- those were re-measured with a
warm cache and may have been reporting post-fix numbers only because their
trees had changed.

## Required

The gate cache key must include whatever identifies the producing gate
code -- frob's version, or a hash of the gate implementation. An upgrade
must invalidate entries produced by the previous build.

## Positive controls, both directions

- upgrade frob to a build with a changed gate, re-run on an UNCHANGED
  tree: the new result is produced, not the cached one
- re-run twice on an unchanged tree with the SAME build: the second run
  still replays from cache (do not fix this by disabling caching -- the
  cache is load-bearing for check cost, which is ~71% of agent wall time)
- a tree change still invalidates as it does today

## Note for whoever picks this up

Re-verify the premise first: confirm the cache key genuinely omits a
build/gate identifier rather than inferring it from this one observation.
The observation is solid (cached=4, --no-cache=0, same build) but the
mechanism should be read in the code before designing the fix.