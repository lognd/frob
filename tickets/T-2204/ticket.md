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
land_commit: null
---
## Done report

Changed:
- src/frob/app/telemetry.py::_EXTERNAL_PATH_EXCLUDE_DIRS -- new: generic
  churn-dir names to prune while walking an arbitrary external path
  argument.
- src/frob/app/telemetry.py::_looks_like_path_token -- new: whitespace-
  split token classifier (path separator, or exists on disk relative to
  cwd) used to find candidate PATH arguments inside a redacted args_head.
- src/frob/app/telemetry.py::_walk_external_path_state -- new: on-disk
  state (file size/mtime, recursive dir walk, or a MISSING sentinel) for
  one resolved external path.
- src/frob/app/telemetry.py::_external_path_arg_hash -- new: combines the
  above into a single digest over every args_head token that resolves
  OUTSIDE the repo tree; "none" when nothing qualifies.
- src/frob/app/telemetry.py::record_cli_event -- now also records
  "external_path_hash" per event.
- src/frob/app/telemetry.py::_tip_redundant_rerun -- REDUNDANT_RERUN's key
  now also requires external_path_hash to match (added `root` parameter).
- src/frob/app/telemetry.py::detect_footguns -- passes `root` through to
  _tip_redundant_rerun.
- src/frob/app/telemetry.py::_redundant_rerun_totals -- usage_report's
  corpus-wide redundant-rerun count now keys on the same 5-tuple.

Evidence:
- tests/test_telemetry.py::TestExternalPathArgHash::test_a_deleted_external_fixture_changes_the_hash
  (DESIGNATED REPRO, BUG002) -- directly reproduces the measured live
  incident (frob cycle against an external fixture whose pyproject.toml
  gets deleted between two identical invocations): asserts REDUNDANT_RERUN
  must NOT fire once the fixture's state has genuinely changed. Checked
  FAILED_AT_PARENT against ffa295177 (the repro committed alone, before
  the fix): `uv run frob ticket evidence T-2204 --check-repro ... --base-ref
  ffa295177` -> "FAILED_AT_PARENT: ... genuinely fails ... this is what
  BUG002 wants". Watched fail directly too: pytest -o addopts="" showed
  "assert 'REDUNDANT_RERUN' not in ['REDUNDANT_RERUN']" against the
  pre-fix code.
- tests/test_telemetry.py::TestExternalPathArgHash::test_still_flags_when_the_external_fixture_is_unchanged
  -- positive case: an unchanged external fixture still lets
  REDUNDANT_RERUN fire (the fix does not blunt the detector).
- tests/test_telemetry.py::TestExternalPathArgHash::test_no_path_looking_argument_yields_none
  -- a subcommand with no PATH-shaped argument (plain "check") is
  unaffected.

Measured: `pytest tests/test_telemetry.py -o addopts="" -q` ->
"SUITE-RESULT: exitstatus=0 collected=40 failed=0" (40 passed: 37
pre-existing + 3 new, no regression). `ruff check src/frob/app/telemetry.py
tests/test_telemetry.py` clean under both PATH ruff and `uv run ruff`.

Filed: none. Acceptance [2] explicitly asks NOT to add a second hardcoded
digest -- this fix derives coverage from the args_head text itself
(any PATH-shaped token, not a per-verb allowlist), so no follow-up ticket
for "cover frob outline/map too" is needed; they are already covered by
the same generic mechanism, verified by inspection (record_cli_event is
the single call site for every subcommand, unconditional on which verb ran).

Gates: `frob check --only gates-fast --ticket T-2204 --json` -- no SCOPE001,
no COV002 introduced by this diff. Every remaining error (gate:COV COV001
on scripts/fleet_status.py::ticket_readiness and COV004 attachment-sha
mismatches on T-2195/T-2197, gate:DOC DOC011 stale draft citations,
gate:DRIFT DRIFT001 on two unrelated symbols, gate:TEST TEST010 on
tests/test_lang.py [T-2203's scope] and one pre-existing malformed-
directive line in tests/test_ticket_work_and_land_finish.py, gate:TICK
TICK004 rot warnings) is repo-wide pre-existing floor debt, confirmed
unrelated to any file/line this ticket touches.

### Changed
```
 src/frob/app/telemetry.py | 212 +++++++++++++++++++++++++++++++++++++++++-----
 tests/test_telemetry.py   | 107 +++++++++++++++++++++++
 tickets/T-2204/ticket.md  |  32 +++++--
 3 files changed, 324 insertions(+), 27 deletions(-)
```

### Evidence
- `tests/test_telemetry.py::TestExternalPathArgHash::test_a_deleted_external_fixture_changes_the_hash` (pytest node id, verified passing when recorded)
- `tests/test_telemetry.py::TestExternalPathArgHash::test_still_flags_when_the_external_fixture_is_unchanged` (pytest node id, verified passing when recorded)
- `tests/test_telemetry.py::TestExternalPathArgHash::test_no_path_looking_argument_yields_none` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH001@scripts/fleet_status.py, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, COV001@scripts/fleet_status.py, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md, COV004@tickets/T-draft-0bd874ac/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-draft-0bd874ac/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_land_cmd.py, DRIFT001@src/frob/lang/_nodes.py, E501@/home/logan/projects/frob/.claude/worktrees/t2201-series/src/frob/lang/_nodes.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, SELFAUDIT001@design, TEST010@tests/test_lang.py, TEST010@tests/test_ticket_work_and_land_finish.py, TICK004@tickets.md
