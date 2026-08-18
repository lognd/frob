---
id: T-2467
title: 'Reshape T-1614: periodic watermark-based waiver audit, drop runs_last'
state: done
kind: security
origin: human
created: '2026-08-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- tickets/T-1614/**
- src/frob/gates/_waive_audit_watermark.py
- src/frob/app/ticket_runner/_waive_audit.py
- src/frob/app/ticket_runner/__init__.py
- src/frob/_cli_parsers/_ticket/_closeout.py
- docs/modules/app.md
- docs/modules/tickets.md
- docs/modules/cli.md
- src/frob/app/config.py
- src/frob/_config_schema.py
- src/frob/_cli_parsers/_ticket/__init__.py
- src/frob/app/_config_external.py
- tests/unit/test_waive_audit_watermark.py
- tests/unit/test_waive_audit_runner.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/gates/**
  reason: narrow from 91/63-file globs down to the new watermark module and its CLI
    wiring point per playbook narrow-scope discipline
  actor: logan
  at: '2026-08-18'
- op: remove
  glob: src/frob/app/**
  reason: narrow from 91/63-file globs down to the new watermark module and its CLI
    wiring point per playbook narrow-scope discipline
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/gates/_waive_audit_watermark.py
  reason: narrow from 91/63-file globs down to the new watermark module and its CLI
    wiring point per playbook narrow-scope discipline
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/app/ticket_runner/_waive_audit.py
  reason: narrow from 91/63-file globs down to the new watermark module and its CLI
    wiring point per playbook narrow-scope discipline
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/app/ticket_runner/__init__.py
  reason: wiring the new frob:waive audit subcommand into the ticket CLI dispatch
    table and argparse subparser -- the standalone runner module alone is unreachable
    from the CLI without these two wiring points
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/_cli_parsers/_ticket/_closeout.py
  reason: wiring the new frob:waive audit subcommand into the ticket CLI dispatch
    table and argparse subparser -- the standalone runner module alone is unreachable
    from the CLI without these two wiring points
  actor: logan
  at: '2026-08-18'
- op: add
  glob: docs/modules/app.md
  reason: doc coverage for the new waive-audit runner/subcommand
  actor: logan
  at: '2026-08-18'
- op: add
  glob: docs/modules/tickets.md
  reason: doc coverage for the new waive-audit runner/subcommand
  actor: logan
  at: '2026-08-18'
- op: add
  glob: docs/modules/cli.md
  reason: doc coverage for the new waive-audit runner/subcommand
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/app/config.py
  reason: AppConfig fields for the new waive-audit subcommand (subcommand name, reviewed-count,
    cop-outs-found flags)
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/_config_schema.py
  reason: AppConfig fields for the new waive-audit subcommand (subcommand name, reviewed-count,
    cop-outs-found flags)
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/_cli_parsers/_ticket/__init__.py
  reason: register the new waive-audit subparser in the ticket subcommand tree builder
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/app/_config_external.py
  reason: register the three new AppConfig fields (waive_audit_subcommand/reviewed_count/cop_outs)
    with _build_external_config_kwargs's known-field tuples so the CLI args actually
    reach AppConfig
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tests/unit/test_waive_audit_watermark.py
  reason: the two new test files this ticket adds
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tests/unit/test_waive_audit_runner.py
  reason: the two new test files this ticket adds
  actor: logan
  at: '2026-08-18'
evidence:
- tests/unit/test_waive_audit_watermark.py::TestLoadWatermark::test_missing_file_is_not_found
- tests/unit/test_waive_audit_watermark.py::TestLoadWatermark::test_malformed_json_is_malformed
- tests/unit/test_waive_audit_watermark.py::TestLoadWatermark::test_valid_file_round_trips
- tests/unit/test_waive_audit_watermark.py::TestSaveWatermark::test_round_trips_through_load
- tests/unit/test_waive_audit_watermark.py::TestSaveWatermark::test_creates_frob_dir_if_missing
- tests/unit/test_waive_audit_runner.py::TestRunScan::test_no_watermark_bounds_catchup
- tests/unit/test_waive_audit_runner.py::TestRunScan::test_watermark_malformed_is_unreadable
- tests/unit/test_waive_audit_runner.py::TestRunScan::test_no_new_waivers_when_nothing_changed_since_watermark
- tests/unit/test_waive_audit_runner.py::TestCompletePass::test_reviewed_count_mismatch_refuses
- tests/unit/test_waive_audit_runner.py::TestCompletePass::test_catchup_incomplete_refuses_full_completion
- tests/unit/test_waive_audit_runner.py::TestCompletePass::test_matching_reviewed_count_advances_watermark
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 7f8193fc958ef608da902730128c6278347b3355
---
T-1614 is currently `runs_last`: undispatchable via `frob ticket start`
while any other ticket is queued/in-progress. This repo files new
tickets faster than it drains them on most days (measured: 48 open
tickets at time of filing, continuous inflow) -- so "after all other
work is complete" is a condition that structurally will not hold. This
is not a deferred ticket; it is an unreachable one, and it has sat as
rot-flagged for 13+ days with nobody able to legally start it.

The audit's INTENT is sound (a waiver's honesty can only be judged
against finished code, and judging early condemns honest waivers whose
follow-up has not landed yet) -- the ONE-SHOT TERMINAL SHAPE is what is
wrong, not the goal.

Reshape T-1614 (and retire its `runs_last` flag) into a periodic,
watermark-based audit instead:

1. Add a persisted watermark (e.g. a commit sha or timestamp in
   `.frob/waive-audit-watermark.json`, mirroring the shape of existing
   `.frob/*.json` state files such as baseline-chunks/coverage-stamp)
   recording the last point a full waiver audit completed.
2. A new ticket-filing or gate mechanism scans `frob:waive` directives
   ADDED (via git blame/log, not full-repo re-scan) since the
   watermark, and either (a) opens a narrowly-scoped audit ticket over
   just that incremental set when the count crosses a threshold, or
   (b) folds into a standing gate stage the coordinator runs
   periodically (same operational shape as the existing WAIVE004
   dead-waiver sweep referenced in T-1614's own body).
3. On completion of an audit pass, the watermark advances to the
   current tip -- so the NEXT audit is scoped to what changed since,
   never the whole repo, and never blocked on repo-wide queue-empty.
4. T-1614's own classification rubric (STILL NECESSARY AND HONEST /
   OBSOLETE / COP-OUT / PERMANENT BY DESIGN) carries over unchanged --
   only the triggering/scoping mechanism changes.
5. Drop T-1614's `runs_last` flag once this lands; replace it with
   this periodic mechanism as the ticket's operating mode.

Do not lose the original T-1614 prose (classification rubric, the
specific patterns this drive already learned to look for -- reason-
restates-rule, orphaned follow_up, bulk-waiver clustering, structurally-
unfireable-rule noise) -- fold it into the new periodic ticket's body
rather than discarding it.

This does not retroactively bless every waiver added before the
watermark exists -- the FIRST run of the new mechanism should audit
the full existing set once (a bounded, one-time catch-up pass), then
every subsequent run is incremental.