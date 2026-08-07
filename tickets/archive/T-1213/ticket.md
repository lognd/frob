---
id: T-1213
title: 'natives: auto-rebuild stale frob_core/strata_core instead of NATIVE001 reminder'
state: done
kind: feature
origin: human
created: '2026-07-29'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/natives/**
- src/frob/gates/__init__.py
- src/frob/natives/_build.py
- src/frob/app/config.py
- docs/modules/gates.md
- tests/test_natives.py
- tests/test_doctor.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/gates/**
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: remove
  glob: src/frob/app/**
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: remove
  glob: docs/**
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: remove
  glob: tests/**
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/gates/__init__.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/natives/_build.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/app/config.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: docs/modules/gates.md
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: tests/test_natives.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: tests/test_doctor.py
  reason: same worktree/branch as the earlier T-1218 ticket in this series; tests/test_doctor.py's
    T-1218 changes are already committed and show up in T-1213's diff-vs-main even
    though T-1213 itself never touches this file
  actor: logan
  at: '2026-08-03'
evidence:
- tests/test_natives.py::TestNativeAutorebuild::test_stale_native_triggers_autorebuild
- tests/test_natives.py::TestNativeAutorebuild::test_missing_but_buildable_native_triggers_autorebuild
- tests/test_natives.py::TestNativeAutorebuild::test_disabled_via_env_var_skips_autorebuild
- tests/test_natives.py::TestNativeAutorebuild::test_disabled_via_frob_toml
- tests/test_natives.py::TestNativeAutorebuild::test_enabled_by_default_with_no_frob_toml
- tests/test_natives.py::TestNativeAutorebuild::test_build_failure_falls_through_to_native001
- tests/test_natives.py::TestNativeAutorebuild::test_build_natives_err_falls_through_to_native001
- tests/test_natives.py::TestNativeAutorebuild::test_nothing_stale_or_missing_skips_build
designated_repro_test: null
acceptance:
- text: GIVEN NATIVE001/StaleNative detects a source-newer-than-artifact native WHEN
    any frob command that needs the native runs THEN the rebuild happens automatically
    (T-0732 shared CARGO_TARGET_DIR makes warm builds ~11s) with the build disclosed
    in output, and NATIVE001 remains only for the cannot-build case (missing toolchain),
    which stays fail-closed
  evidence:
  - tests/test_natives.py::TestNativeAutorebuild::test_stale_native_triggers_autorebuild
  - tests/test_natives.py::TestNativeAutorebuild::test_missing_but_buildable_native_triggers_autorebuild
  - tests/test_natives.py::TestNativeAutorebuild::test_disabled_via_env_var_skips_autorebuild
  - tests/test_natives.py::TestNativeAutorebuild::test_disabled_via_frob_toml
  - tests/test_natives.py::TestNativeAutorebuild::test_enabled_by_default_with_no_frob_toml
  - tests/test_natives.py::TestNativeAutorebuild::test_build_failure_falls_through_to_native001
  - tests/test_natives.py::TestNativeAutorebuild::test_build_natives_err_falls_through_to_native001
  - tests/test_natives.py::TestNativeAutorebuild::test_nothing_stale_or_missing_skips_build
- text: GIVEN a fresh worktree with no built natives THEN first frob invocation builds
    them automatically rather than degrading -- the recurring worktree-natives false-failure
    class disappears
  evidence:
  - tests/test_natives.py::TestNativeAutorebuild::test_missing_but_buildable_native_triggers_autorebuild
threat: null
component: null
---
Derived-state auto-refresh sweep 2026-07-29 (user directive: nothing frob-managed is refreshed manually). Natives staleness is DETECTED (src/frob/strata/_native_staleness.py, mtime+content-hash discrimination) but the refresh is a manual make core / frob natives build; T-0248 automated only the reminder. Sibling of T-1205 (coverage). Guard: never auto-build when the toolchain is absent -- disclose and fail closed as today.