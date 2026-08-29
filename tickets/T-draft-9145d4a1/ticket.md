---
id: T-draft-9145d4a1
title: 'Fix gate:TICK006/TICK011 errors: correct phantom-draft citations and disclosure-window
  vicinity'
state: queued
kind: bug
origin: human
created: '2026-08-29'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tickets/T-3227/**
- tickets/T-3236/**
- tickets/T-3238/**
- tickets/archive/T-2978/**
- tickets/archive/T-3031/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'BUG002: no genuine before/after repro exists for a ticket-prose-only diff;
    declaring no-behavior-change per BUG002 remedy (2)'
  actor: logan
  at: '2026-08-29'
  old_length: 1661
  new_length: 2097
evidence:
- tests/test_gates.py::TestFixEngineTierA::test_tick006_genuinely_lost_draft_still_caught_no_rename_no_duplicate
- tests/test_gates.py::TestFixEngineTierA::test_tick006_already_recovered_citation_rewritten_not_refiled_again
- tests/test_gates.py::TestTick011DisclosedCutWithoutTicket::test_disclosure_with_a_real_citing_id_is_silent
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Sub-ticket of T-3343 (triage). Fixes 5 of the 9 gate:TICK errors, measured via frob check --only tickets --json:

TICK006 (4): T-3227/T-3236/T-3238's Done reports each claimed 'Filed: T-draft-e1bca269 (close-time disclosure check false-positives...)' -- that draft never survived land (T-0577 draft-loss class). The real ticket for this exact defect is T-3285 (done) -- T-3219's own Done report already correctly cites it for the identical bug. Corrected all three to cite T-3285 instead of the phantom draft.

T-3031's archived Done report claimed 'Filed: T-draft-36006d55 (...)' for a test failure (TestGitlessTargetGateSeverity::test_render_lint_gate_warns_not_errors_on_gitless_root). That draft also never survived land, but the real ticket exists: T-3091, filed with the identical title, explicitly noting it was 'Found while working T-3031'. Corrected the Done report to cite T-3091, and rephrased the earlier 'filed here as T-draft-...' prose sentence (which independently re-triggered TICK006 on the same phantom id via a second unrelated 'filed' occurrence) to avoid the trigger word entirely.

TICK011 (1): T-2978's Done report disclosed a SCOPE CUT and did cite a real follow-up ticket (T-2998), but the citation sat outside TICK011's 300-char vicinity window from the 'SCOPE CUT' trigger phrase. Added a closer citation immediately after the trigger phrase, redundant with (not replacing) the existing later citation.

Re-measured: gate:TICK 9 -> 4 (the remaining 4 are TICK004 aging-ticket findings needing real owner triage decisions -- re-prioritize/work/drop across T-0969/T-1273/T-1382/T-1686 -- reported separately, not mechanically fixable).

frob:no-behavior-change reason="ledger-text-only fix: corrects prose in five archived/queued Done reports (phantom draft-id citations rebound to their real ticket ids, one disclosure citation moved closer to its trigger phrase) -- no application code, gate logic, or test file touched anywhere in this diff. The cited evidence tests exercise the TICK006/TICK011 detection mechanisms this fix relies on (unmodified), not new behavior."