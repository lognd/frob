---
id: T-1218
title: 'doctor: stale-global-frob self-check -- invoked version vs repo floor'
state: done
kind: feature
origin: human
created: '2026-07-29'
priority: low
parent: null
tier: ticket
sprint: null
scope:
- src/frob/doctor.py
- src/frob/app/config.py
- src/frob/app/__main__.py
- docs/modules/app.md
- tests/test_doctor.py
- src/frob/app/_config_meta.py
- tests/unit/test_config.py
- frob.lock
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
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
  glob: src/frob/app/config.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/app/__main__.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: docs/modules/app.md
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: tests/test_doctor.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/app/_config_meta.py
  reason: the actual min-version-floor implementation lives in _config_meta.py (already
    home to stale_install_warning, the same class of check) not doctor.py/app/config.py
    directly; its own unit tests live in tests/unit/test_config.py alongside stale_install_warning's
  actor: logan
  at: '2026-08-03'
- op: add
  glob: tests/unit/test_config.py
  reason: the actual min-version-floor implementation lives in _config_meta.py (already
    home to stale_install_warning, the same class of check) not doctor.py/app/config.py
    directly; its own unit tests live in tests/unit/test_config.py alongside stale_install_warning's
  actor: logan
  at: '2026-08-03'
- op: add
  glob: frob.lock
  reason: frob ack src/frob/doctor.py::run_diagnosis (DRIFT001 fix) writes its new
    digest into frob.lock
  actor: logan
  at: '2026-08-03'
- op: add
  glob: design/frob.strata
  reason: 'land-repair (T-1501): SYS100/SYS104 self-audit fixes required interface=/may-via
    declarations and superseded a T-1113 mechanical AFFECT001 waiver in the touched
    node headers'
  actor: logan
  at: '2026-08-04'
evidence:
- tests/test_doctor.py::test_run_diagnosis_reports_stale_binary_floor
- tests/test_doctor.py::test_run_diagnosis_stale_binary_none_when_no_floor
- tests/unit/test_config.py::test_stale_binary_warning_flags_version_below_floor
- tests/unit/test_config.py::test_stale_binary_warning_none_when_no_floor_declared
- tests/unit/test_config.py::test_stale_binary_warning_none_when_version_meets_floor
designated_repro_test: null
acceptance:
- text: GIVEN a frob invocation in a repo whose frob.toml declares a minimum frob
    version WHEN the invoked frob is older THEN every command prints a prominent stale-binary
    warning naming the upgrade command, and frob doctor reports it as a finding
  evidence:
  - tests/test_doctor.py::test_run_diagnosis_reports_stale_binary_floor
  - tests/test_doctor.py::test_run_diagnosis_stale_binary_none_when_no_floor
  - tests/unit/test_config.py::test_stale_binary_warning_flags_version_below_floor
  - tests/unit/test_config.py::test_stale_binary_warning_none_when_no_floor_declared
  - tests/unit/test_config.py::test_stale_binary_warning_none_when_version_meets_floor
threat: null
component: null
---
Derived-state auto-refresh sweep 2026-07-29: the globally installed frob (uv tool) went stale at 0.9.0 while the repo advanced to 0.277.0, causing wrong gate numbers for anyone invoking bare frob -- a documented recurring papercut. Detection belongs in frob itself: version floor in frob.toml, checked at CLI startup (cheap), doctor finding with the exact uv tool upgrade frob remedy.