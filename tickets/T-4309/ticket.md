---
id: T-4309
title: Tool summary reports FAIL for a tool whose detail says no issues
state: in-progress
kind: bug
origin: human
created: '2026-09-08'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/check/__init__.py
- tests/unit/test_check_measurement.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_check_measurement.py
  reason: 'T-4309: covering test for the UNRES-not-FAIL fix in check/__init__.py''s
    as_text'
  actor: logan
  at: '2026-09-08'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
A TOOL IS REPORTED AS FAILING IN THE SUMMARY WHILE ITS OWN DETAIL SAYS IT FOUND
NOTHING WRONG ON EVERY PLATFORM.

MEASURED IN THE MACOS INTEGRATION LOG. The tool summary table carries a FAIL
verdict for the type checker, and the detail printed on that same line reads that
each of the three platforms had no issues. A row cannot honestly be both. The same
table shows a second row of the same shape: the formatter marked FAIL with a
detail of zero files that would be reformatted.

WHY THIS IS WORTH FIXING RATHER THAN IGNORING. A summary is what a reader trusts
when they do not read the whole log, and this one is actively misleading in the
direction that costs the most -- it invents a failure. Someone chasing the macos
leg will spend time on a type-checking problem that the tool itself says does not
exist, and the reverse error (a real failure summarised as a pass) is the same bug
with the polarity flipped and much worse consequences.

FIND WHICH OF THE TWO HALVES IS WRONG BEFORE CHANGING EITHER. Either the run
genuinely failed and the detail string is stale or misassembled, or the run
genuinely succeeded and the verdict is derived from something other than the
result -- a nonzero exit code that does not mean failure, an unmeasured or
unavailable condition being folded into FAIL, or an error on one platform's probe
being reported with another's message. The distinction matters: one is a display
bug and the other means the verdict logic is wrong. Say which you found.

CHECK WHETHER "UNMEASURED" IS BEING COLLAPSED INTO "FAILED". This project already
has a separate, deliberate vocabulary for a gate that could not determine an
answer -- the same summary in this log shows a distinct UNRES verdict and a whole
"Unmeasured gates" section explaining that a zero count is not a clean
measurement. If a tool that could not run is being rendered as FAIL instead of as
unmeasured, that is the defect, and the fix should route it into the existing
vocabulary rather than inventing a third state.

COVER IT WITH A TEST THAT FORCES THE CONDITION -- a tool run that produces no
issues but whatever signal is currently driving the FAIL -- and assert on the
summary row itself, not on the underlying result.
