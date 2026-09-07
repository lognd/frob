---
id: T-4158
title: route the T-2390-family schema-validator resolve_dotted_symbol sites through
  the project env
state: queued
kind: bug
origin: human
created: '2026-09-07'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_arch_schema.py
- src/frob/gates/_docblocks_schema.py
- src/frob/gates/_dup_graph_schema.py
- src/frob/gates/_gates_schema.py
- src/frob/gates/_native_schema.py
- src/frob/gates/_profile_schema.py
- src/frob/gates/_refs_schema.py
- src/frob/gates/_test_runner_schema.py
- src/frob/gates/_testing_schema.py
- src/frob/gates/_toplevel_scalar_schema.py
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
T-4147's own enumeration instruction ("enumerate every import/exec-in-frobs-interpreter site first, this is likely not the only one") found nine other T-2390-family gate modules calling frob.gates._docblocks_shared.resolve_dotted_symbol the same way FLAGCOV001 did pre-fix: a plain importlib.import_module against FROB's own interpreter, resolving a project-declared schema/validator dotted symbol. Same defect class as T-4147 (a consumer project whose own dependency versions differ from frob's gets a false ImportError/UNRESOLVED forever) -- same fix shape T-4147 landed (_flag_coverage.py's own _spawn_resolver/_RESOLVER_SCRIPT, uv run --project <root> python -c ...) should generalize, likely by moving the resolver mechanism itself into frob.gates._docblocks_shared (or frob.process._project_tool) so all ten call sites share ONE implementation rather than ten copies. Left out of T-4147 itself: that ticket's own scope was FLAGCOV001's parser import specifically, and generalizing the resolver to a shared helper used by nine more gates is a distinctly larger, separately-reviewable change.