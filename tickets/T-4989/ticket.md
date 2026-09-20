---
id: T-4989
title: 'refs gate: reference conventional scaffold files by default'
state: queued
kind: feature
origin: human
created: '2026-09-19'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_refs.py
- tests/test_refs_gate.py
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
T-4761 (scaffold green-day-one) needs a rendered frob.toml to carry ZERO [[refs.entrypoint]] rows for ordinary conventional files (Makefile, make.bat, README.md, docs/index.md, CMakeLists.txt, .github/workflows/*.yml, invariants/.gitkeep, vite.config.ts, index.html, eslint.config.js, .prettierrc.json, src/vite-env.d.ts, tests/setup.ts) instead of the current per-project boilerplate. This is the narrow slice of T-5090 (frob.toml debloat, conventional files referenced by default) that T-4761 depends on; that ticket is still queued/undone. Extend _DEFAULT_ROOT_MANIFEST_EXEMPT / _is_github_convention_file's sibling pattern (T-3019/T-3031/T-4145 precedent) in src/frob/gates/_refs.py to cover this file set, each exempted the same way pyproject.toml/frob.toml/package.json already are, with matching tests in tests/test_refs_gate.py.