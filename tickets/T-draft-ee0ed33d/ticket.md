---
id: T-draft-ee0ed33d
title: 'SF-19: two PII rule families, one permanently dead -- strata PII001-004 (0
  fires) vs gates PII010-012 (2,208 fires)'
state: queued
kind: docs
origin: agent
created: '2026-09-19'
priority: low
parent: T-4665
tier: ticket
sprint: v0.536.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/strata/_pii.py
- tests/unit/strata/test_pii_family_identity.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: Given src/frob/strata/_pii.py's PII001-004 have fired 0 times and are a permanent
    zero by construction (design/frob.strata declares PII posture EXPLICITLY ZERO
    and a test asserts it), while src/frob/gates/_pii_structural/'s PII010/011/012
    fired 276/92/1840, when this lands, then a test asserts every PII rule id defined
    in _pii.py carries a description naming its evaluation domain and disambiguating
    it from the structural family -- a positive control that fails at HEAD c8f56ef10
    because no such text exists.
  evidence: []
- text: Given docs/modules/gates.md's rule table is a shared registry file named by
    T-4598, when its rule descriptions also need this change, then it is recorded
    as a follow-up in the done-report and NOT edited in this ticket.
  evidence: []
threat: null
component: strata
anchor: false
anchor_reason: null
land_commit: null
---
SF-19 (LOW). Leaf of story B (T-4665) under epic T-4662. Story points: 1.
IMMEDIATELY DISPATCHABLE -- no blockers.

EVIDENCE. Two rule families share three letters and have opposite signal:
- src/frob/strata/_pii.py implements PII001-004 over `carries`/`may`.
  Telemetry fires: 0. design/frob.strata's header (lines ~40-55) declares PII
  posture EXPLICITLY ZERO and a test asserts zero PII findings -- so the strata
  PII family is a PERMANENT ZERO BY CONSTRUCTION, not an unlucky one.
- src/frob/gates/_pii_structural/ (planner-verified: _crosslang.py,
  _declared_surface.py, _emails.py, _env_access.py, _keywords.py) implements
  PII010/011/012, which fired 276 / 92 / 1,840 times in telemetry.

So "PII0xx" in a frob finding means one of two unrelated things depending on the
last digit, and the family a reader is most likely to look up first is the one
that has never fired.

WHAT TO BUILD
At minimum a naming and documentation fix so the two families are not
confusable: the strata family's docstrings and rule descriptions must state that
it is a MODEL-LEVEL family evaluated against `carries`/`may` declarations, that
frob's own model declares zero PII by construction, and where the structural
family lives. A merge of the two families is the larger option and should NOT be
attempted in this leaf -- if the implementer concludes a merge is the right
answer, record that and file it, do not build it.

The rule table in docs/modules/gates.md is a SHARED REGISTRY FILE named by
T-4598 (whole-file lease serialises the fleet). It is deliberately kept OUT of
this leaf's scope; if the rule descriptions there must change, do it as a
follow-up once T-4598 lands, and say so in the done-report.

POSITIVE CONTROL (the test that fails today)
A test asserting every PII rule id defined under src/frob/strata/_pii.py carries
a description that names its evaluation domain and disambiguates it from the
structural PII010-012 family. It fails at HEAD -- no such text exists.
