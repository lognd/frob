---
id: T-1584
title: Wire frob profile CLI (show/downgrade) to frob.tickets._profile
state: done
kind: feature
origin: human
created: '2026-08-05'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/_cli_parsers/**
- src/frob/app/config.py
- src/frob/app/app.py
- src/frob/app/__init__.py
- src/frob/app/_config_external.py
- src/frob/app/profile_runner.py
- src/frob/_cli_parsers/__init__.py
- src/frob/_cli_parsers/_reporting.py
- src/frob/__main__.py
- tests/unit/test_profile_runner.py
- docs/modules/tickets.md
- src/frob/tickets/_profile.py
evidence_scope:
- tests/unit/test_app_lazy_dispatch.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/app/**
  reason: 'T-1584: narrow the FEATURE-kind default globs to the actual CLI-wiring
    files touched (frob profile show/downgrade)'
  actor: logan
  at: '2026-08-10'
- op: remove
  glob: docs/**
  reason: 'T-1584: narrow the FEATURE-kind default globs to the actual CLI-wiring
    files touched (frob profile show/downgrade)'
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/app/config.py
  reason: 'T-1584: narrow the FEATURE-kind default globs to the actual CLI-wiring
    files touched (frob profile show/downgrade)'
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/app/app.py
  reason: 'T-1584: narrow the FEATURE-kind default globs to the actual CLI-wiring
    files touched (frob profile show/downgrade)'
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/app/__init__.py
  reason: 'T-1584: narrow the FEATURE-kind default globs to the actual CLI-wiring
    files touched (frob profile show/downgrade)'
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/app/_config_external.py
  reason: 'T-1584: narrow the FEATURE-kind default globs to the actual CLI-wiring
    files touched (frob profile show/downgrade)'
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/app/profile_runner.py
  reason: 'T-1584: narrow the FEATURE-kind default globs to the actual CLI-wiring
    files touched (frob profile show/downgrade)'
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/_cli_parsers/__init__.py
  reason: 'T-1584: narrow the FEATURE-kind default globs to the actual CLI-wiring
    files touched (frob profile show/downgrade)'
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/_cli_parsers/_reporting.py
  reason: 'T-1584: narrow the FEATURE-kind default globs to the actual CLI-wiring
    files touched (frob profile show/downgrade)'
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/__main__.py
  reason: 'T-1584: narrow the FEATURE-kind default globs to the actual CLI-wiring
    files touched (frob profile show/downgrade)'
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tests/unit/test_profile_runner.py
  reason: 'T-1584: narrow the FEATURE-kind default globs to the actual CLI-wiring
    files touched (frob profile show/downgrade)'
  actor: logan
  at: '2026-08-10'
- op: add
  glob: docs/modules/tickets.md
  reason: 'T-1584: narrow the FEATURE-kind default globs to the actual CLI-wiring
    files touched (frob profile show/downgrade)'
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/tickets/_profile.py
  reason: retire the WIRE001 waiver T-1584 was named as the follow_up for -- downgrade_profile_ratchet
    now has a real production caller (profile_runner._run_downgrade)
  actor: logan
  at: '2026-08-10'
evidence:
- tests/unit/test_profile_runner.py::TestProfileRunnerShow::test_show_reports_configured_and_effective
- tests/unit/test_profile_runner.py::TestProfileRunnerShow::test_show_json_mode
- tests/unit/test_profile_runner.py::TestProfileRunnerShow::test_bare_profile_defaults_to_show
- tests/unit/test_profile_runner.py::TestProfileRunnerShow::test_show_reports_a_real_ratchet
- tests/unit/test_profile_runner.py::TestProfileRunnerDowngrade::test_downgrade_requires_a_reason
- tests/unit/test_profile_runner.py::TestProfileRunnerDowngrade::test_downgrade_and_reason_file_are_mutually_exclusive
- tests/unit/test_profile_runner.py::TestProfileRunnerDowngrade::test_downgrade_clears_a_real_ratchet
- tests/unit/test_profile_runner.py::TestProfileRunnerDowngrade::test_downgrade_reason_file_read_verbatim
- tests/unit/test_profile_runner.py::TestProfileRunnerDowngrade::test_downgrade_is_a_noop_when_nothing_ratcheted
- tests/unit/test_app_lazy_dispatch.py::TestResolveRunnerDispatchTotality::test_every_non_bind_subcommand_resolves_a_callable_runner
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
Filed while working T-1575: downgrade_profile_ratchet has no CLI caller yet (WIRE001-waived with this follow_up). Add a top-level 'frob profile show' / 'frob profile downgrade --reason ...' subcommand pair. The downgrade path must stay loudly logged and explicit -- the T-1575 ratchet upgrades automatically but never downgrades on its own.