---
id: T-0551
title: 'check: nested/top-level-less native sources escape language detection (T-0404
  finding 7)'
state: done
kind: bug
origin: auditor
created: '2026-07-21'
priority: medium
parent: T-0404
tier: ticket
sprint: null
scope:
- src/frob/check/
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_check.py::TestDetectProjectType::test_cargo_toml_is_rust
- tests/unit/test_check.py::TestDetectProjectType::test_cmakelists_is_cpp
- tests/unit/test_check.py::TestDetectProjectType::test_no_sentinel_is_unknown
designated_repro_test: null
threat: null
component: null
---
docs/audits/lang-check-docs.md finding 7. detect_project_type only globs *.cpp/*.cc/*.c at the repo TOP LEVEL and _detected_types requires CMakeLists.txt/Cargo.toml at root. A C/C++ project whose sources live only in src/ with no root CMakeLists returns unknown -> Python pipeline (finding 6), so clang/cmake never run. Fix direction: detect native sources recursively (bounded depth or via the graph's own file walk), or fail loudly on unknown rather than silently skipping native checks.