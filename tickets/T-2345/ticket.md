---
id: T-2345
title: _parse_error_findings_from_json can add a genuinely identity-less (rule, file)
  pair (T-2313's root cause, out of its scope)
state: done
kind: bug
origin: human
created: '2026-08-17'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/_verify.py
evidence_scope:
- tests/unit/test_ticket_runner_gate_findings.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_ticket_runner_gate_findings.py::TestParseErrorFindingsFromJsonDropsBlankIdentity::test_blank_identity_diagnostic_is_dropped_not_added
- tests/unit/test_ticket_runner_gate_findings.py::TestParseErrorFindingsFromJsonDropsBlankIdentity::test_drop_is_logged_naming_the_emitting_tool
- tests/unit/test_ticket_runner_gate_findings.py::TestParseErrorFindingsFromJsonDropsBlankIdentity::test_a_diagnostic_with_only_file_set_is_kept
designated_repro_test: tests/unit/test_ticket_runner_gate_findings.py::TestParseErrorFindingsFromJsonDropsBlankIdentity::test_blank_identity_diagnostic_is_dropped_not_added
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-2313 fixed the SYMPTOM within its own declared scope
(src/frob/app/ticket_runner/_rapid_sweep.py::_normalize_identities now
drops a genuinely identity-less (rule, file) pair before it can enter a
baseline diff or a filed ticket body). This is a defense-in-depth fix at
the consumer, not the root cause.

Root cause, found during T-2313's investigation, in a DIFFERENT file
(out of T-2313's declared scope, deliberately not touched there):

src/frob/app/ticket_runner/_verify.py::_parse_error_findings_from_json:

    for d in r.get("diagnostics", ()):
        if isinstance(d, dict) and d.get("severity") == "error":
            findings.add((d.get("code") or "", d.get("file") or ""))

Any error-severity diagnostic with BOTH `code` and `file` missing/empty
becomes a genuine `("", "")` member of the returned findings set here --
this is the actual point where an identity-less finding enters the
system, upstream of `_rapid_sweep.py`'s rolling-baseline diff and ticket
filing. T-2313's fix in `_rapid_sweep.py` stops this specific consumer
from acting on it, but:

- Any OTHER caller of `_parse_error_findings_from_json`/`_unscoped_error_
  findings` (grep for callers before assuming there's only one) inherits
  the same bogus identity unless it happens to also filter it.
- The underlying tool that emitted a diagnostic with neither `code` nor
  `file` populated is itself producing malformed output -- worth
  understanding WHICH tool/gate can produce this shape (a stack-trace-only
  crash diagnostic? a renderer bug that drops the fields?) rather than
  only filtering it out downstream.

WANTED: skip (with a loud WARNING log, never silent) any diagnostic
where both `code` and `file` are empty inside `_parse_error_findings_
from_json` itself, and identify which tool/gate is emitting this shape
so the real defect (a diagnostic missing its own identity) can be fixed
at the source, not just filtered at every consumer.