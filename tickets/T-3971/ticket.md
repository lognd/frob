---
id: T-3971
title: 'ENVVAR002: every config field has a non-test reader'
state: queued
kind: security
origin: agent
created: '2026-09-06'
priority: medium
parent: T-3919
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/config.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given a config field with a schema/doc entry but no non-test read site anywhere
    in the codebase, when frob check runs, then ENVVAR002 fires naming the field
  evidence: []
- text: given a field read by at least one non-test call site, when frob check runs,
    then the rule stays quiet
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-3919 item 8. Distinct from ENVVAR003 (T-3942 item 8, already filed as T-3966: flags construction of a config class outside its designated site). This one is about READING: every AppConfig-shaped field should have a non-test reader somewhere in the codebase. The existing three-way sync gate (env-var doc/schema/code sync) proves a field is DOCUMENTED, not that it DOES anything -- a field can be declared, synced across all three surfaces, and never actually consulted by any non-test code path.

FINDING THIS WOULD HAVE CAUGHT: a security-relevant config knob that exists on paper (documented, schema-validated) but is dead in practice because nothing reads it, so changing it has no effect -- the auditor's framing is that the existing sync gate creates false confidence here. Proposed: extend (or add alongside) the sync gate a check that every config field has at least one non-test read site, using the same reachability-style analysis already proven out for COV006/similar rules in this repo.
