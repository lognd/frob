---
id: T-3059
title: Split __main__.py and stats/_agentic.py under LARGE001's 800-line threshold
state: queued
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
