---
id: T-1381
title: frob release stamp must refuse to absorb an un-bumped API change
state: done
kind: bug
origin: human
created: '2026-08-01'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/release/**
- src/frob/app/release_runner.py
- tests/unit/test_release_stamp_guard.py
- src/frob/_cli_parsers/_misc.py
- src/frob/app/config.py
- pyproject.toml
- .frob-release.json
- uv.lock
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_release_stamp_guard.py
  reason: the guard needs a CLI flag, an AppConfig field, its own tests, and its own
    REL001 bump
  actor: logan
  at: '2026-08-01'
- op: add
  glob: src/frob/_cli_parsers/_misc.py
  reason: the guard needs a CLI flag, an AppConfig field, its own tests, and its own
    REL001 bump
  actor: logan
  at: '2026-08-01'
- op: add
  glob: src/frob/app/config.py
  reason: the guard needs a CLI flag, an AppConfig field, its own tests, and its own
    REL001 bump
  actor: logan
  at: '2026-08-01'
- op: add
  glob: pyproject.toml
  reason: the guard needs a CLI flag, an AppConfig field, its own tests, and its own
    REL001 bump
  actor: logan
  at: '2026-08-01'
- op: add
  glob: .frob-release.json
  reason: the guard needs a CLI flag, an AppConfig field, its own tests, and its own
    REL001 bump
  actor: logan
  at: '2026-08-01'
- op: add
  glob: uv.lock
  reason: the guard needs a CLI flag, an AppConfig field, its own tests, and its own
    REL001 bump
  actor: logan
  at: '2026-08-01'
evidence:
- tests/unit/test_release_stamp_guard.py::TestStampRefusesUnbumped::test_refuses_when_api_changed_and_version_not_bumped
- tests/unit/test_release_stamp_guard.py::TestStampRefusesUnbumped::test_allow_unbumped_is_an_explicit_override
- tests/unit/test_release_stamp_guard.py::TestStampRefusesUnbumped::test_allows_when_version_is_bumped
- tests/unit/test_release_stamp_guard.py::TestGuardIsOnByDefault::test_appconfig_default_does_not_allow_unbumped
- tests/unit/test_release_stamp_guard.py::TestGuardIsOnByDefault::test_cli_without_the_flag_does_not_allow_unbumped
designated_repro_test: null
acceptance:
- text: GIVEN the public API changed since the last stamp AND the version has not
    been bumped WHEN frob release stamp runs THEN it refuses, names the required version,
    and writes nothing
  evidence:
  - tests/unit/test_release_stamp_guard.py::TestStampRefusesUnbumped::test_refuses_when_api_changed_and_version_not_bumped
- text: GIVEN the same state WHEN frob release stamp --allow-unbumped runs THEN it
    stamps and logs a loud justification-required override
  evidence:
  - tests/unit/test_release_stamp_guard.py::TestStampRefusesUnbumped::test_allow_unbumped_is_an_explicit_override
- text: GIVEN the version HAS been bumped to at least the required level WHEN frob
    release stamp runs THEN it stamps exactly as before
  evidence:
  - tests/unit/test_release_stamp_guard.py::TestStampRefusesUnbumped::test_allows_when_version_is_bumped
threat: null
component: null
---
Hit by the coordinator 2026-08-01, in this exact order: REL001 said 'public API changed (minor) since 0.293.0; bump the version to >= 0.294.0, then run: frob release stamp'. Running 'frob release stamp' at the UNCHANGED 0.293.0 made REL001 go quiet -- because stamping rebaselines the recorded public API at whatever version is current. The gate was satisfied and the minor bump silently never happened. Caught only by noticing afterwards; reverted, bumped, re-stamped.

The remedy text itself invites the mistake: it names bump-then-stamp as one instruction, and stamp alone is the half that appears to work.

stamp already has everything needed to refuse: it computes the public-API diff against the recorded manifest, which is exactly what REL001 uses to decide the required bump level. It should compare the current version against that required level and refuse when it is short, with the same loud, justification-required override shape the repo already uses for --skip-mutation-evidence and --allow-cross-ticket.

This is the standing systematize-friction rule: a footgun the tool can detect must be made impossible rather than left to reviewer attention.