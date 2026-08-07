---
id: T-0735
title: 'frob natives build: frob-owned native compilation with shared cache -- Makefiles
  become one-line shims (parent)'
state: done
kind: feature
origin: human
created: '2026-07-22'
priority: high
blocked_by:
- T-0864
- T-0865
parent: null
tier: ticket
sprint: null
scope:
- src/frob/**
- docs/**
- tests/unit/test_natives_build.py
- tests/unit/test_scaffold_natives_shim.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_natives_build.py
  reason: 'D-02: scope-add the evidence test files used to verify T-0735''s acceptance
    criterion at epic-close time'
  actor: logan
  at: '2026-07-27'
- op: add
  glob: tests/unit/test_scaffold_natives_shim.py
  reason: 'D-02: scope-add the evidence test files used to verify T-0735''s acceptance
    criterion at epic-close time'
  actor: logan
  at: '2026-07-27'
- op: add
  glob: tests/unit/test_natives_build.py
  reason: 'D-02: scope-add the evidence test files used to verify T-0735''s acceptance
    criterion at epic-close time'
  actor: logan
  at: '2026-07-27'
- op: add
  glob: tests/unit/test_scaffold_natives_shim.py
  reason: 'D-02: scope-add the evidence test files used to verify T-0735''s acceptance
    criterion at epic-close time'
  actor: logan
  at: '2026-07-27'
evidence:
- tests/unit/test_natives_build.py::TestBuildNatives::test_builds_declared_rust_natives
- tests/unit/test_natives_build.py::TestMakefileCoreShim::test_core_recipe_is_one_line_natives_build_shim
- tests/unit/test_scaffold_natives_shim.py::TestMakefileCoreShimTemplate::test_applying_to_fresh_repo_installs_one_line_shim
- tests/unit/test_scaffold_natives_shim.py::TestLegacyCoreCacheDrift::test_legacy_unmanaged_core_target_reports_stale
designated_repro_test: null
acceptance:
- text: GIVEN any frob-enabled repo with [natives] WHEN uv run frob natives build
    runs THEN natives compile with the shared per-clone cache and the repo Makefile
    contains no cache logic
  evidence:
  - tests/unit/test_natives_build.py::TestBuildNatives::test_builds_declared_rust_natives
  - tests/unit/test_natives_build.py::TestMakefileCoreShim::test_core_recipe_is_one_line_natives_build_shim
  - tests/unit/test_scaffold_natives_shim.py::TestMakefileCoreShimTemplate::test_applying_to_fresh_repo_installs_one_line_shim
  - tests/unit/test_scaffold_natives_shim.py::TestLegacyCoreCacheDrift::test_legacy_unmanaged_core_target_reports_stale
threat: null
component: null
---
User directive 2026-07-22: T-0732's shared CARGO_TARGET_DIR fix lives in THIS repo's Makefile -- wrong layer; fix ALL repos structurally. frob.toml [natives] already declares the native crates (load_natives); the build logic belongs in frob: a "frob natives build" subcommand that does what make core does (maturin develop per declared native) WITH the shared-cache mechanism (git-common-dir keyed CARGO_TARGET_DIR, cargo's own locking -- T-0732's verified design) built in. Every repo's Makefile core target becomes "uv run frob natives build" -- one line, zero per-repo cache logic, upgraded by upgrading frob. Doctor integration: the existing native-staleness fingerprint check points at the new command as remedy. Children: (1) the subcommand + this repo's Makefile shim conversion; (2) scaffold template + conformance drift check; estate rollout via fleet at close.