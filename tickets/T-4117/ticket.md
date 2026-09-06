---
id: T-4117
title: 'H3-9: a module docstring''s claim about its own module''s code is never checked
  against that code'
state: queued
kind: docs
origin: human
created: '2026-09-06'
priority: critical
blocked_by:
- T-4116
parent: T-4109
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_module_docstring_drift.py
- tests/gates_suite/test_module_docstring_drift.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
F-307 H3-9 (verbatim, quoted at the bottom of T-4109's body). Same claim-in-
prose-with-no-binding class as H3-4, but a DIFFERENT comparison, per the
parent epic's explicit instruction not to collapse the two without checking:
this one is a MODULE docstring's claim about a router-level dependency
(described in module-level prose, never bound to a directive) versus its own
module's actual code. DRIFT001 (verified: src/frob/graph/lock.py's DESCRIBES-
anchor digest mechanism, see _facets_for_ref/_edge_endpoints) compares doc
FILES against acked refs via frob:doc/frob:describes anchors -- it has no
path at all for a bare MODULE docstring (the triple-quoted string at the top
of a .py file) making a claim about that SAME file's code, because a module
docstring is not itself an anchored, ackable ref the way a docs/*.md
section is.

Work:
- for each module's top-of-file docstring, detect never/always/idempotent-
  or dependency-shaped claim language the same way H3-4's lint does for
  symbol docstrings (share the keyword-scan helper if H3-4 lands first and
  exposes one cleanly, otherwise duplicate the minimal matcher rather than
  taking a hard dependency on H3-4's ticket landing first for what should
  be a small, easily-shared regex)
  -- NOTE: this leaf is blocked_by H3-4 specifically to reuse that keyword
  matcher rather than to gate on any shared runtime dependency; if H3-4's
  matcher is not cleanly reusable when this leaf starts, drop the block and
  file a follow-up ticket for the duplication instead of stalling this leaf
- compare the claim's target dependency/behavior against the MODULE's own
  code (e.g. a claim like "every route in this module requires
  authentication" checked against the module's actual route-decorator
  usage) -- this is the genuinely new check DRIFT001 structurally cannot do
- new rule id (suggest DOC010 or similar module-docstring-drift family,
  distinct from DRIFT001)

Fixture note: fires cleanly in frob's own tree structurally (frob has module
docstrings making claims -- this ticket's own H3-4 sibling grounding search
found several), but the SPECIFIC claim shape H3-9 names (a router-level
auth dependency) is backend-shaped and has no frob analog. Use a synthetic
fixture module in the test file:
- must-fire: a module docstring claiming "every function in this module
  validates its own input" while the module's code contains a function with
  no validation call
- must-stay-quiet: the same claim, but every function in the fixture module
  does call a validation helper
- third: a module docstring with ordinary prose (no claim language) --
  must stay quiet regardless of the module's actual code, matching H3-4's
  claim-triggered (not universal) posture

frob:ticket T-4109