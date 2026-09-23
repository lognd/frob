---
id: T-4665
title: 'Story B: gate signal and false positives -- make the SYS zero legible, then
  fix what consumers report'
state: queued
kind: feature
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
no_scope_declared_reason: '2026-09-19: story container under T-4662; the disjoint
  scopes live on its leaves'
triage_changes:
- field: sprint
  old_value: v0.536.0
  new_value: v1.1.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-20'
designated_repro_test: null
acceptance:
- text: Given 614,294 telemetry rule fires containing zero SYS ids and one SELFAUDIT001,
    when this story closes, then a SYS rule evaluation is provably instrumented (positive
    control), the 570-per-45-lands require_analyzable WARNING is gone, and each of
    T-3821/T-3832/T-3825/T-4127 is closed or carries a recorded owner decision.
  evidence: []
threat: null
component: strata
anchor: false
anchor_reason: null
land_commit: null
---
Story B of T-4662. Covers SF-01, SF-11, SF-15, SF-16, SF-17, SF-18, SF-19.

THE MEASURED PROBLEM
The SYS/SELFAUDIT family costs the most and reports the least, and where it
does report, consumers report it reporting wrongly.

| id | measurement | evidence |
|---|---|---|
| SF-01 | 614,294 rule fires over 82 rule ids in telemetry; ZERO start with SYS; SELFAUDIT001 = 1. 79 rule ids of the SYS/SELFAUDIT/REL/PII/THREAT/VMOD/CLAIM families are defined and none appear in telemetry. For contrast CPLACE002=124,184, CPLACE001=89,963, TICK014=88,050, DOCARCH001=59,362 | .frob/telemetry.jsonl (31,459 rows) |
| SF-11 | require_analyzable WARNs on EVERY design load: 570 occurrences across 45 /tmp/land-T-*.log, ~12.7 per land | src/frob/strata/_packs.py:96-102 |
| SF-15 | SYS101 (declared-never-observed) fires on design-first repos | T-3821 (F-016), queued |
| SF-16 | SYS112 fires under check SELFAUDIT but not frob sys audit; waivers disagree. One rule, two engines, two answers | T-3832 (F-027), queued |
| SF-17 | SYS103/SELFAUDIT001 false-positive on multi-glob code= bindings; the gate cannot go green | T-3825 (F-020), queued |
| SF-18 | SCOPE002 explodes on design/frob.strata: three agents independently measured 140, 345 and 71 on 2026-09-06; 88 open tickets mention SCOPE002 | T-4127, queued |
| SF-19 | strata PII001-004 have fired 0 times; gates PII010/011/012 fired 276/92/1,840. Two families, same three letters, opposite signal | src/frob/strata/_pii.py vs src/frob/gates/_pii_structural/ |

LIVE CORROBORATION OF SF-18, 2026-09-19: filing this epic's own container ticket
(empty scope, no files) emitted 587 scope-closure warnings, "579 more warning(s)
collapsed", every one a design/frob.strata frob:doc anchor into
docs/strata/roadmap.md. That is the explosion reproducing on a ticket that
touches nothing.

CAVEAT A FIXER MUST HONOUR (from the audit, verbatim in spirit): the SYS family
is a SELF-CONFORMANCE gate, so "zero findings" is partly the intended steady
state. The friction is the RATIO -- the cost of holding it at zero is borne on
every land. So B1 is deliberately a MEASUREMENT leaf first: per memory/
silent-zero-is-the-dominant-bug-class.md, a zero is one of four things (clean,
could-not-run, nothing-to-measure, matcher-never-fired) and today we cannot tell
which one this zero is. Nothing else in this story should be re-tuned until B1
can distinguish them.

ACCEPTANCE
B1 lands a positive control proving a SYS evaluation is instrumented; the four
consumer-reported false positives (SF-15/16/17/18) are closed or have a recorded
owner decision; the per-load WARNING is gone from land logs.
