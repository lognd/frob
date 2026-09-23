---
id: T-4667
title: 'Story D: DECISIONS the owner must record before any strata grammar or semantics
  work'
state: queued
kind: docs
origin: agent
created: '2026-09-19'
priority: high
parent: T-4662
tier: story
sprint: null
runs_last: false
milestone: 1.1.0
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: true
no_scope_declared_reason: '2026-09-19: story container under T-4662; its children
  are decision records, which legitimately change no files'
triage_changes:
- field: sprint
  old_value: v0.536.0
  new_value: v1.1.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-20'
designated_repro_test: null
acceptance:
- text: Given six findings (SF-08, SF-09, SF-10, SF-12, SF-21, SF-22) whose fix surface
    is the grammar or semantics the owner is personally rethinking, when this story
    closes, then every child carries an owner-recorded decision in its body and no
    child was implemented before its decision was recorded.
  evidence: []
threat: null
component: strata
anchor: false
anchor_reason: null
land_commit: null
---
Story D of T-4662. Covers SF-08, SF-09, SF-10, SF-12, SF-21, SF-22.

WHY THESE ARE DECISIONS AND NOT WORK
The owner is personally rethinking strata grammar and semantics. Every finding
in this story has a fix surface that is the grammar or the semantics, so filing
implementation work against it would pre-empt that rethink and would very likely
be thrown away. Each child here is kind=docs, titled "DECISION: ...", carries the
evidence table rows verbatim plus the 2-3 options the evidence actually supports
and what each option would have to change, and its single acceptance criterion is
that the OWNER RECORDS A DECISION IN THE BODY. No child under D may be
implemented before its decision is recorded.

| id | finding | fix surface per the audit |
|---|---|---|
| SF-08 | 33/33 assumes are one boilerplate shape, one owner, one date | grammar/semantics |
| SF-09 | 56 of 139 parser keywords used nowhere; 19 more only in litmus | scope (retire or exercise) plus docs |
| SF-10 | design/frob.strata is 70% comment prose; 15.4% of declarations are literal duplicates | grammar (defaults/inheritance) plus where rationale lives |
| SF-12 | T-3920's eight recorded expressiveness gaps from a real threat-model pass | grammar and semantics (item 6 especially), gate (item 8), diagnostics (item 2) |
| SF-21 | kernel.md says "six primitives"; the parser accepts 139 keywords | doc-vs-implementation framing |
| SF-22 | T-3822 (attr IDENT form) and T-3823 (secret rotate within/revoke) documented-vs-implemented mismatches | doc or grammar, owner's call which moves |

Two of these already have open tickets and are ATTACHED here rather than
duplicated: T-3920 (SF-12) and T-3822 + T-3823 (SF-22).

MEASUREMENT CAVEAT the owner should know before deciding SF-09/SF-21: the 139
keywords were extracted from at_keyword / eat_keyword / expect_keyword literals
in strata-core/src/parse/*.rs. A construct reached only through a non-keyword
token path would be missed. So 139 is a LOWER bound on the grammar, and
"56 unused" is an UPPER-bound claim on deadness within those 139.
