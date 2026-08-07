---
id: T-0274
title: 'fix(graph): file-walking surfaces must consult [graph].exclude'
state: done
kind: bug
origin: agent
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/testing/_collect.py
- src/frob/strata/_code_binding.py
- src/frob/strata/_selfconform.py
- tests/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_testing.py::TestFindCrates::test_find_crates_honors_graph_exclude
- tests/test_testing.py::TestFindCrates::test_walk_test_files_honors_graph_exclude
- tests/unit/strata/test_code_binding.py::TestBindCode::test_graph_exclude_dir_is_never_bound_even_when_glob_matches
- tests/unit/strata/test_selfconform.py::TestNonPythonLanguageWiring::test_sorted_capability_files_honors_graph_exclude
- tests/unit/strata/test_selfconform.py::TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant
designated_repro_test: null
threat: null
component: null
---
Coordinator-reported bug class: two live file-walking surfaces never
consulted `[graph].exclude` (`frob.excludes.load_exclude_globs`/
`is_excluded`), the single home docs/strata/surface.md/T-0080 REJECT
round 1 says every walker must consult. Instance 1: `_find_crates`
(T-0271, this same session) descended into
`/home/logan/projects/lithos/.claude/worktrees/**` stale agent
checkouts even though lithos's frob.toml lists that glob under
`[graph].exclude`. Instance 2: graphite FROBLEMS.md 2026-07-18 #1 --
`frob.strata._selfconform`'s capability-binding walk
(`_sorted_capability_files`) and `_code_binding.bind_code`'s `.py`
walk both only consulted the built-in skip-dir set, never
`[graph].exclude`, so a repo's declared-excluded bundled-frontend
build directory still got attributed to a Python `code=`-globbed
node.