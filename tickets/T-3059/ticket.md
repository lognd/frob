---
id: T-3059
title: Split __main__.py and stats/_agentic.py under LARGE001's 800-line threshold
state: done
kind: feature
origin: human
created: '2026-08-26'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/__main__.py
- src/frob/stats/_agentic.py
- docs/commands/cli-vocabulary.md
- docs/modules/app.md
- docs/modules/stats.md
- src/frob/_cli_parsers/_root.py
- src/frob/stats/_agentic_dispatch.py
- src/frob/stats/_agentic_shared.py
- tests/test_stats_agentic.py
- tests/integration/test_interfaces.py
- frob.lock
- tickets/T-3409/ticket.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: docs/commands/cli-vocabulary.md
  reason: T-3059's real LARGE001 split moved code out of __main__.py/_agentic.py into
    new sibling modules (_root.py, _agentic_dispatch.py, _agentic_shared.py) and updated
    the doc/test anchors the move invalidated
  actor: logan
  at: '2026-08-29'
- op: add
  glob: docs/modules/app.md
  reason: T-3059's real LARGE001 split moved code out of __main__.py/_agentic.py into
    new sibling modules (_root.py, _agentic_dispatch.py, _agentic_shared.py) and updated
    the doc/test anchors the move invalidated
  actor: logan
  at: '2026-08-29'
- op: add
  glob: docs/modules/stats.md
  reason: T-3059's real LARGE001 split moved code out of __main__.py/_agentic.py into
    new sibling modules (_root.py, _agentic_dispatch.py, _agentic_shared.py) and updated
    the doc/test anchors the move invalidated
  actor: logan
  at: '2026-08-29'
- op: add
  glob: src/frob/_cli_parsers/_root.py
  reason: T-3059's real LARGE001 split moved code out of __main__.py/_agentic.py into
    new sibling modules (_root.py, _agentic_dispatch.py, _agentic_shared.py) and updated
    the doc/test anchors the move invalidated
  actor: logan
  at: '2026-08-29'
- op: add
  glob: src/frob/stats/_agentic_dispatch.py
  reason: T-3059's real LARGE001 split moved code out of __main__.py/_agentic.py into
    new sibling modules (_root.py, _agentic_dispatch.py, _agentic_shared.py) and updated
    the doc/test anchors the move invalidated
  actor: logan
  at: '2026-08-29'
- op: add
  glob: src/frob/stats/_agentic_shared.py
  reason: T-3059's real LARGE001 split moved code out of __main__.py/_agentic.py into
    new sibling modules (_root.py, _agentic_dispatch.py, _agentic_shared.py) and updated
    the doc/test anchors the move invalidated
  actor: logan
  at: '2026-08-29'
- op: add
  glob: tests/test_stats_agentic.py
  reason: T-3059's real LARGE001 split moved code out of __main__.py/_agentic.py into
    new sibling modules (_root.py, _agentic_dispatch.py, _agentic_shared.py) and updated
    the doc/test anchors the move invalidated
  actor: logan
  at: '2026-08-29'
- op: add
  glob: tests/integration/test_interfaces.py
  reason: T-3059's real LARGE001 split moved code out of __main__.py/_agentic.py into
    new sibling modules (_root.py, _agentic_dispatch.py, _agentic_shared.py) and updated
    the doc/test anchors the move invalidated
  actor: logan
  at: '2026-08-29'
- op: add
  glob: frob.lock
  reason: frob.lock is the append-only ack ledger frob ack writes to when re-verifying
    doc anchors after the move; tickets/T-3409/ticket.md is the follow-up
    ticket this ticket filed for the out-of-scope design/frob.strata SYS100 update
  actor: logan
  at: '2026-08-29'
- op: add
  glob: tickets/T-3409/ticket.md
  reason: frob.lock is the append-only ack ledger frob ack writes to when re-verifying
    doc anchors after the move; tickets/T-3409/ticket.md is the follow-up
    ticket this ticket filed for the out-of-scope design/frob.strata SYS100 update
  actor: logan
  at: '2026-08-29'
evidence:
- tests/unit/test_main_entry.py::TestDidYouMean::test_unrecognized_flag_suggests_closest_known_flag
- tests/unit/test_main_entry.py::TestGroupedHelpFormatter::test_verb_groups_listed_before_also_available_directly_section
- tests/test_stats_agentic.py::TestDispatchCostReport::test_empty_stream_yields_empty_report
- tests/integration/test_interfaces.py::TestInterfaces::test_version_flag_prints_version_and_exits_zero
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## Problem

Two files are over LARGE001's 800-line threshold, pre-existing before
the T-3006/T-2995/T-3014 batch (verified via git history at T-3026 time):

- `src/frob/__main__.py` (845 lines before the batch, 852 after)
- `src/frob/stats/_agentic.py` (802 lines before the batch, unchanged)

T-3026 recorded both as `frob:debt LARGE001` (this ticket) rather than
waiving permanently, since a real split is the right fix, just too large
for a bugfix-scoped ticket to do safely as a drive-by.

## Plan

- `src/frob/__main__.py`: split subcommand-parser wiring out of the
  top-level CLI entrypoint (candidate: a new `_cli_parsers` module for
  whichever subcommand groups are largest, mirroring the existing
  `src/frob/_cli_parsers/` package).
- `src/frob/stats/_agentic.py`: split the report-aggregation logic from
  its rendering/formatting half.

## Acceptance

- Both files under LARGE001's threshold (800 lines) with no LARGE001
  waiver/debt remaining at either site.
- No behavior change; existing test coverage for both modules stays
  green with node ids unchanged where possible.