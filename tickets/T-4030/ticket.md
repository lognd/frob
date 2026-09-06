---
id: T-4030
title: 'policy.pattern: dangerouslySetInnerHTML with direct JSON.stringify'
state: queued
kind: security
origin: agent
created: '2026-09-06'
priority: high
blocked_by:
- T-4013
parent: T-4025
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/policy/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given a JSX dangerouslySetInnerHTML attribute whose value is a direct JSON.stringify(...)
    call expression, when the new policy.pattern runs, then it fires
  evidence: []
- text: given the pattern ships, when it lands, then it lands after T-4013's fnmatch
    glob fix, not before
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Item 3, the most shippable item in this list per the consumer's own words: "not a taint-analysis problem and needs no data-flow ... a JSX attribute containing a direct call expression, four occurrences, one repo ... writable today." VERIFIED: git grep for dangerouslySetInnerHTML across src/frob found nothing -- no existing rule.

FINDING THIS WOULD HAVE CAUGHT: a JSX dangerouslySetInnerHTML attribute whose value is a direct JSON.stringify(...) call expression -- e.g. dangerouslySetInnerHTML={{__html: JSON.stringify(data)}} -- which is unescaped HTML built from a JSON serialization that does not escape </script>-breaking sequences, a well-known XSS vector distinct from ordinary unescaped-HTML injection. Four occurrences in the consumer's one repo. Purely structural (a JSX attribute containing a specific call-expression shape), no data-flow analysis required.

MUST SEQUENCE AFTER T-4013 (F-226, fnmatch policy-glob under-matching), per the epic's own explicit instruction: this item is implemented as a policy.pattern, and shipping a policy pattern whose glob silently under-matches (T-4013's own finding) is worse than shipping no pattern at all -- the pattern would report clean over a glob set that never covered all the real files. Filed with blocked_by=T-4013 to enforce the sequencing at the ticket-graph level, not just in prose.
