---
id: T-4094
title: 'H3-7: empty catch/degrade path with no logging in src/'
state: queued
kind: feature
origin: agent
created: '2026-09-06'
priority: medium
parent: T-4089
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/arch/_logging_checks.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: verified via reading _logging_checks.py that check_unlogged_error_path (T-0622)
    already implements the exact proposed shape language-agnostically; correcting
    before an implementer builds a duplicate
  actor: logan
  at: '2026-09-06'
  old_length: 1574
  new_length: 2488
designated_repro_test: null
acceptance:
- text: given an empty catch block or null-returning degrade branch in src/** with
    no console.*/logger call, when the new rule runs, then it is flagged regardless
    of what the comment attributes the degrade to
  evidence: []
- text: given a degrade branch that does log, when the rule runs, then it stays quiet
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
H3-7 (F-296). VERIFIED: git grep for an empty-catch/silent-degrade-path logging check found nothing in src/frob/arch/_logging_checks.py (frob's own logging-discipline check family, which already has check_print_as_diagnostic for a related but different shape).

FINDING THIS WOULD HAVE CAUGHT: a docstring naming an ENVIRONMENT (jsdom) where the spec actually wanted a CONDITION (no 2D canvas context) -- gate:DOC cannot tell the difference between "this degrades because we are in jsdom" (an environment-attribution comment, potentially masking a real runtime gap) and "this degrades because the 2D context is genuinely absent" (the actual intended condition), because both read as prose to a doc-pointer-freshness check. The GENERAL rule worth shipping, per the consumer, sidesteps the environment-vs-condition ambiguity entirely: a degrade path whose comment attributes itself to the test environment must STILL LOG -- an empty catch/null-branch with no console.* (or logger call) in a src/ file is a finding regardless of what the comment claims, directly encoding this repo's own "log everything worth logging" principle.

Proposed: a cheap tree-sitter pattern flagging an empty catch block or a null-returning degrade branch in src/** with no console.*/logger call inside it. Structural, no data-flow needed -- this is squarely the same shape as this repo's own dictConfig/module-logger discipline (CLAUDE.md: "LOG EVERYTHING WORTH LOGGING... never skip adding a log line"), just checked mechanically for TS/JS src/ files rather than relied on as a Python convention.


CORRECTION after filing: src/frob/arch/_logging_checks.py already implements check_unlogged_error_path (T-0622), which flags exactly this shape -- a catch clause with no nearby log call -- and is written once against NormalizedModule so it fires for EVERY LanguageAdapter, TS/JS included, per run_logging_checks' own docstring. So the proposed rule is ALREADY IMPLEMENTED, not missing. This ticket's remaining scope narrows to: (1) verify this check actually fires on the consumer's own TS repro (a jsdom-attributed empty catch in src/) -- if it already does, no frob work is needed here at all, only pointing the consumer at the existing check; (2) if it does NOT fire on their repro, find out why (a TS-specific gap in NormalizedFunction.catches population, or a severity/wiring gap keeping this check off by default) and fix that specific gap rather than building new detection. Do not build a duplicate rule.