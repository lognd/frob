---
id: T-2694
title: 'Split src/frob/app/telemetry.py: 3 real seams (event/footgun/usage), T-1656
  successor'
state: done
kind: feature
origin: human
created: '2026-08-19'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/telemetry.py
- src/frob/app/telemetry/**
- design/frob.strata
- docs/modules/app.md
- tests/test_telemetry.py
evidence_scope:
- tests/test_telemetry.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/test_telemetry.py
  reason: 'COV002: retargeted frob:tests anchors in this file per the split -- every
    changed line needs ticket coverage; the file was already legitimately touched
    by the anchor-retarget commit (bb81fb312) and now by this land-fix pass'
  actor: logan
  at: '2026-08-20'
evidence:
- tests/test_telemetry.py::test_redact_command_hides_recognizable_secret
- tests/test_telemetry.py::test_estimate_tokens_is_len_over_four
- tests/test_telemetry.py::test_append_event_writes_one_json_line
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Successor to T-1656 (LARGE001 remainder): a genuine seam identified but not
attempted here, per T-1656's own precedent for rank-1-3 candidates (own
multi-session project, do not force it under time pressure).

src/frob/app/telemetry.py (1135 lines) is NOT a single orchestrator like
check_runner.py/sys_runner.py (both waived by this ticket's own pass with
real reasoning) -- its outline shows three genuinely distinct, separately-
consumed concerns bundled in one file:

1. Event recording: is_disabled, iso_now, redact_command, append_event,
   tree_hash, record_cli_event, record_ticket_event, record_dispatch_event,
   timed_call -- the write path every `frob` subcommand's telemetry hook
   goes through.
2. Footgun tips: Tip, tips_disabled, detect_footguns, render_tips --
   post-command advisory text, a distinct read-then-render concern with
   its own opt-out env var (FROB_NO_FOOTGUN_TIPS vs FROB_NO_TELEMETRY).
3. Usage reporting: usage_report, UsageReport, SubcommandTimeSink --
   corpus aggregation for `frob sys capacity`/reporting-style consumers,
   read-only over the event stream (1) writes.

14 files import from `frob.app.telemetry` today (measured via `git grep`):
.claude/hooks/dispatch-telemetry.py, src/frob/app/__init__.py, src/frob/
app/app.py, src/frob/app/doctor_runner.py, src/frob/app/ticket_runner/
_close_cmd.py, src/frob/app/ticket_runner/_lifecycle.py, src/frob/app/
ticket_runner/_new.py, src/frob/security/_redact.py, src/frob/stats/
_agentic.py, src/frob/telemetry/__init__.py (a DIFFERENT, already-separate
top-level package -- do not conflate), tests/test_telemetry.py, tests/
unit/security/test_redact.py, tests/unit/telemetry/test_rule_counts.py,
tests/unit/test_app_telemetry_branches_t1400.py.

Proposed split: src/frob/app/telemetry/__init__.py (event recording,
keeps the current public names so none of the 14 importers need editing),
src/frob/app/telemetry/_footguns.py (Tip/detect_footguns/render_tips/
tips_disabled), src/frob/app/telemetry/_usage.py (usage_report/
UsageReport/SubcommandTimeSink) -- re-exported from __init__ for the same
import-compatibility reason. Needs the usual side effects every split in
this family has produced (T-1656's own body, carried forward here): a
design/frob.strata code= glob addition, a hand-declared interface= update
(no auto-writer exists per T-1870), and doc anchors moved with their
frob:invariant/frob:doc pointers rather than orphaned.