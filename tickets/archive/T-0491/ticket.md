---
id: T-0491
title: extend T-0423 run-scoped memoization to frob.dup.find_duplicates
state: done
kind: bug
origin: human
created: '2026-07-21'
priority: medium
parent: T-0423
tier: ticket
sprint: null
scope:
- src/frob/dup/
- tests/unit/test_memo.py
- pyproject.toml
- .frob-release.json
- uv.lock
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_memo.py
  reason: test proving find_duplicates memoization + REL001 version bump/stamp required
    for the memoize_per_run docstring/decorator change
  actor: logan
  at: '2026-07-21'
- op: add
  glob: pyproject.toml
  reason: test proving find_duplicates memoization + REL001 version bump/stamp required
    for the memoize_per_run docstring/decorator change
  actor: logan
  at: '2026-07-21'
- op: add
  glob: .frob-release.json
  reason: test proving find_duplicates memoization + REL001 version bump/stamp required
    for the memoize_per_run docstring/decorator change
  actor: logan
  at: '2026-07-21'
- op: add
  glob: uv.lock
  reason: test proving find_duplicates memoization + REL001 version bump/stamp required
    for the memoize_per_run docstring/decorator change
  actor: logan
  at: '2026-07-21'
evidence:
- tests/unit/test_memo.py::test_find_duplicates_second_call_is_memo_hit
- tests/unit/test_memo.py::test_find_duplicates_no_cross_run_leak
designated_repro_test: null
threat: null
component: null
---
T-0423 added run-scoped @memoize_per_run memoization for build_graph and analyze_project (src/frob/check/_memo.py), but find_duplicates was left un-memoized: it lives in src/frob/dup/_legacy.py, which is outside T-0423's declared scope and was under concurrent active rework (sibling agent editing src/frob/dup/_template.py) at the time. Once that rework settles, decorate find_duplicates (or its _pipeline.find_clones successor) with frob.check._memo.memoize_per_run at its definition site, matching the build_graph/analyze_project precedent -- covers every caller (frob.check._python._run_dup, frob.gates._prework, frob.gates._arch, frob.app.dup_runner) automatically with no call-site edits. Verify with a call-counter test mirroring tests/unit/test_memo.py::test_build_graph_second_call_is_memo_hit.