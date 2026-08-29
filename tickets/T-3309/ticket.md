---
id: T-3309
title: NEGEXIST001 false positives on rule-description prose and gitignored files
state: queued
kind: bug
origin: human
created: '2026-08-28'
priority: low
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/__init__.py
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
REPORTED FROM REAL CONSUMER USE (../diax FROBLEMS.md F-021, F-027). Two
distinct NEGEXIST001 false positives, same rule, bundle the fixes together.

F-021: NEGEXIST001 fires on ordinary spec prose containing the phrase "does
not exist" that is NOT a claim about a tracked path -- e.g. "a docs.href
path that does not exist" (describing a VALIDATION RULE, not asserting a
specific path's absence) and a sample error message quoted in docs. The
heuristic should not fire inside table cells, code fences, or quoted sample
output/error-message text -- confirm the detector's current scope (does it
already skip fenced code blocks?) before assuming it does not.

F-027: NEGEXIST001 scans FROBLEMS.md itself, a GITIGNORED/untracked file
(the repo's own working convention -- see this file's own header:
"Untracked (gitignored)"). The gate should only scan TRACKED docs; an
untracked scratch file should never be gate input at all. Confirm whether
this is NEGEXIST001-specific or a general "gates should not scan untracked
files" gap that would recur elsewhere (frob's own repo has a "FROBLEMS.md
campaign" precedent of a gitignored friction log -- if other gates ALSO scan
untracked files, note that as worth a broader follow-up, but do not expand
this ticket's scope to fix every gate; just this one, and say what else you
noticed).

MUST-FIRE FIXTURE: prose making a genuine claim about a specific tracked
path not existing, outside a code fence/table/quote -- must still fire.

MUST-STAY-QUIET FIXTURE: (a) the phrase "does not exist" inside a fenced
code block or table cell describing a rule/sample, (b) any NEGEXIST001-
shaped text inside a gitignored/untracked file.
