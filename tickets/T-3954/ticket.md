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
- src/frob/graph/dsl.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/graph/dsl.py
  reason: narrow to the actual frob:tests directive parser; original scope (_coverage.py)
    was picked from a plausible module name, not the real parse site
  actor: logan
  at: '2026-09-06'
body_changes:
- mode: append
  reason: T-4036 item 3 is the fourth arrival of docstring-claims-as-obligations;
    cross-referencing per the coordinator's instruction, with a narrower numeric-literal-buffer-size
    first slice worth folding into design
  actor: logan
  at: '2026-09-06'
  old_length: 1032
  new_length: 2130
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

T-4036 item 3 is the FOURTH independent arrival of docstring-claims-as-obligations (T-3919 item 4, T-3928's own convergence 1 which is this ticket, T-3942 item 6, now this). Cross-referenced, not refiled. NEW MOTIVATING DETAIL from this arrival: gate:DOC verifies pointer FRESHNESS (does the anchor still resolve), never CLAIM TRUTH (is the sentence still accurate) -- the consumer concedes the fully general form (any docstring claim) is out of reach today, but proposes a NARROW, more tractable first slice worth folding into this ticket's design: a numeric literal in a docstring naming a buffer stride or size. In their own pass this narrow rule would have caught the same bug TWICE, eight ABI functions apart -- a docstring numeric claim (e.g. "returns a 16-byte buffer") that the actual return size no longer matches. Worth considering as the FIRST shippable slice of this ticket rather than trying the fully general keyword-based form first, since a numeric-literal-vs-actual-size mismatch is a much narrower, more mechanical check than inferring intent from words like atomic/idempotent.
