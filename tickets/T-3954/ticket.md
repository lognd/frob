---
id: T-3954
title: frob:tests covers= failure-path binding
state: queued
kind: security
origin: agent
created: '2026-09-06'
priority: high
parent: T-3928
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_coverage.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given a docstring containing a conditional-behavior claim (a failure/error-path
    sentence) and a frob:tests directive with no covers=failure-path evidence, when
    frob check runs, then a new rule reports the missing failure-path coverage
  evidence: []
- text: given frob:tests <symbol>::<test> covers=failure-path pointing at a test that
    actually exercises the failure branch, when frob check runs, then the finding
    is satisfied
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Convergence 1 of T-3928 (backend audit item 4 + frontend audit item 3, arrived independently). Also T-3919 item 4 and T-3942 item 6 -- do NOT file separate tickets on those epics for this ask, cite this one. FINDING THIS WOULD HAVE CAUGHT: backend -- docstrings claiming 'in one transaction', 'can be reached', 'per-IP lockout check', 'no loop is ever nested' that were all FALSE; frontend item 3 -- a docstring stating a FAILURE behaviour ('cleared on failure so the next mutation gets to retry') that the code does not implement, with frob:tests satisfied by a HAPPY-PATH test only. PREFER THE FRONTEND FRAMING per T-3928's own guidance: it binds a SENTENCE to a TEST rather than inferring an invariant from keywords, which is more implementable. Add a 'covers="failure-path"' (or similar) attribute to frob:tests, and a rule flagging a symbol whose docstring states a conditional/failure behaviour with no covers=failure-path evidence. Verify against what exists first: git grep confirms no covers= attribute on frob:tests today.