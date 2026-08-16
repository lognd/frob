---
id: T-2204
title: 'REDUNDANT_RERUN''s out-of-repo input digest is hardcoded to ~/.claude, but
  frob cycle takes an arbitrary external path whose contents decide the result: measured
  a false ''nothing has changed'' when the verdict flipped'
state: done
kind: bug
origin: human
created: '2026-08-16'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/telemetry.py
- tests/test_telemetry.py
evidence_scope:
- tests/test_telemetry.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_telemetry.py
  reason: own repro/regression tests for the external-path digest fix live here
  actor: logan
  at: '2026-08-16'
evidence:
- tests/test_telemetry.py::TestExternalPathArgHash::test_a_deleted_external_fixture_changes_the_hash
- tests/test_telemetry.py::TestExternalPathArgHash::test_still_flags_when_the_external_fixture_is_unchanged
- tests/test_telemetry.py::TestExternalPathArgHash::test_no_path_looking_argument_yields_none
designated_repro_test: tests/test_telemetry.py::TestExternalPathArgHash::test_a_deleted_external_fixture_changes_the_hash
acceptance:
- text: Measured live while verifying T-2195. Ran 'frob cycle <fixture>/srclayout'
    with a pyproject.toml declaring [tool.setuptools] packages.find.where=['src']
    -> reported a cycle. Deleted that pyproject.toml and re-ran the identical command
    -> REDUNDANT_RERUN fired claiming 'you ran this at this exact tree state (tree_hash=f56c66f03)
    before; nothing has changed since -- this run could not have produced a different
    result'. The verdict genuinely flipped to 'no cycles found'. The fixture lives
    outside the repo, so tree_hash cannot cover it. This test MUST fail against current
    main.
  evidence:
  - tests/test_telemetry.py::TestExternalPathArgHash::test_a_deleted_external_fixture_changes_the_hash
  - tests/test_telemetry.py::TestExternalPathArgHash::test_still_flags_when_the_external_fixture_is_unchanged
  - tests/test_telemetry.py::TestExternalPathArgHash::test_no_path_looking_argument_yields_none
- text: 'Derive the redundancy key from the inputs the VERB actually reads, not from
    a hardcoded list of known out-of-repo locations. _home_config_state_hash (src/frob/app/telemetry.py:189)
    covers ~/.claude only, and its own docstring calls that ''this repo''s one existing
    out-of-repo materialized-copy target'' -- a premise this measurement falsifies.
    A positional PATH argument is the obvious second class: frob cycle, frob outline,
    frob map and any verb taking a path all decide from a tree tree_hash does not
    describe.'
  evidence:
  - tests/test_telemetry.py::TestExternalPathArgHash::test_a_deleted_external_fixture_changes_the_hash
  - tests/test_telemetry.py::TestExternalPathArgHash::test_still_flags_when_the_external_fixture_is_unchanged
  - tests/test_telemetry.py::TestExternalPathArgHash::test_no_path_looking_argument_yields_none
- text: 'Do NOT fix this by adding a second hardcoded digest for path arguments --
    that is the third instance of the same one-at-a-time shape this session (T-1907
    type family then T-2114 doc/test family with ARCH/lint still open; T-2156 one
    graph consumer then T-2188 the rest). Either incorporate the resolved argument
    paths generically, or SUPPRESS the tip for any verb whose key cannot be shown
    to cover its inputs. A wrong ''could not have produced a different result'' is
    worse than no tip: it is a definite claim that stops a reader re-running, which
    is exactly what it did to me.'
  evidence:
  - tests/test_telemetry.py::TestExternalPathArgHash::test_a_deleted_external_fixture_changes_the_hash
  - tests/test_telemetry.py::TestExternalPathArgHash::test_still_flags_when_the_external_fixture_is_unchanged
  - tests/test_telemetry.py::TestExternalPathArgHash::test_no_path_looking_argument_yields_none
threat: null
component: null
anchor: false
anchor_reason: null
---
