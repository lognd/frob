---
id: T-1234
title: fix LANG002 rationale text still naming kotlin as unregistered
state: done
kind: bug
origin: human
created: '2026-07-29'
priority: low
parent: T-1226
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_lang_conformance.py
- tests/test_lang_conformance_gate.py
- tests/unit/test_check.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/test_lang_conformance_gate.py
  reason: 'kotlin was the LANG002 false-unregistered example fixed by T-1234; test
    must use a still-unregistered language instead

    '
  actor: logan
  at: '2026-07-29'
- op: add
  glob: tests/unit/test_check.py
  reason: 'T-1234 as a ticket id is a coincidental literal match in an unrelated illustrative
    example, which blocks LiveTrackerCited close of the real T-1234 ticket; retargeting
    the example to the repo convention placeholder T-9999 to unblock close

    '
  actor: logan
  at: '2026-07-29'
body_changes:
- mode: append
  reason: 'T-4709: preserve per-language grammar-registration symbol names trimmed
    from _lang_conformance.py'
  actor: logan
  at: '2026-09-19'
  old_length: 197
  new_length: 824
evidence:
- tests/test_lang_conformance_gate.py::TestProjectLangConformanceGate::test_kotlin_file_no_longer_flagged_by_lang002
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
src/frob/gates/_lang_conformance.py:62-70 LANG002 rationale still names kotlin as unregistered (registered since T-0723). Behavior coincidentally right, rationale stale -- fix rationale text/logic.


T-4709 follow-up (condensed from _UNREGISTERED_CANDIDATE_LANGUAGES's
comment block in src/frob/gates/_lang_conformance.py, trimmed for
DOCARCH002's 12-line cap): kotlin (.kt/.kts), csharp (.cs), and java
(.java) each had a real `frob.lang` grammar registration land
(`frob.lang._walk_kotlin`/`_walk_csharp`/`_walk_java`,
`frob.lang.__init__._EXTENSION_TABLE`) after this dict was originally
written. This repo's own tree happened to contain no files of those
extensions, so the stale entries never actually fired here -- the
"coincidentally right" behavior T-1234 was filed to close before some
future repo/file tripped it.