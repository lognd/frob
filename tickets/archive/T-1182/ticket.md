---
id: T-1182
title: 'arch: abstraction-opportunity detector should skip same-name call-through
  forwarders'
state: done
kind: bug
origin: agent
created: '2026-07-29'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/arch/**
- tests/unit/test_arch.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: condense forwarder-token-budget rationale into T-1182 body
  actor: logan
  at: '2026-09-19'
  old_length: 251
  new_length: 1236
evidence:
- tests/unit/arch_suite/test_abstraction.py::TestCallThroughForwarderExclusion::test_distinct_named_self_forwarders_not_flagged
- tests/unit/arch_suite/test_abstraction.py::TestCallThroughForwarderExclusion::test_group_with_one_non_self_named_member_still_flagged
- tests/unit/arch_suite/test_abstraction.py::TestCallThroughForwarderExclusion::test_forwarder_helper_requires_self_named_short_body
designated_repro_test: null
acceptance:
- text: GIVEN a group whose members are same-name single-statement forwarders to another
    symbol WHEN abstraction-opportunity clusters by signature THEN forwarders are
    excluded (they are deliberate indirection, not duplicated logic), measured before/after
    on the T-1083 finding set
  evidence:
  - tests/unit/arch_suite/test_abstraction.py::TestCallThroughForwarderExclusion::test_distinct_named_self_forwarders_not_flagged
  - tests/unit/arch_suite/test_abstraction.py::TestCallThroughForwarderExclusion::test_group_with_one_non_self_named_member_still_flagged
  - tests/unit/arch_suite/test_abstraction.py::TestCallThroughForwarderExclusion::test_forwarder_helper_requires_self_named_short_body
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Refile from the w20-arch T-1083 disposition pass (draft died with the fail-log; record on branch w20-arch commit a8085d7f): call-through forwarders (one-line delegation wrappers) coincide on signature by construction and are not extraction candidates.

<!-- narrative-moved:src/frob/arch/_abstraction.py:634:T-1182 -->
: T-1182 (refiled from the T-1083 disposition, w20-arch a8085d7f): the
: token budget a call-through forwarder's serialized body
: (`_body_fingerprint`/`_serialize_py_body`) may spend before it no
: longer reads as "single statement". `RenderWriter.heading`'s body --
: `self . _emit ( heading ( _v0 , color = self . color ) )` -- is 14
: tokens; this is a generous but still narrow ceiling meant to admit
: exactly that shape (one attribute-chain call wrapping one delegated
: call, at most a couple of keyword arguments), not an arbitrary
: multi-statement body that merely happens to mention its own name.
frob:waive PII012 reason="'token' here means a normalized body-fingerprint lexical \
token (_serialize_py_body's output), not a credential/auth token -- a name-signature \
false positive, same class as frob.outline's existing PII012 waiver for its own \
unrelated lexical-token vocabulary"
frob:ticket T-1195