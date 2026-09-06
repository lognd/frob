---
id: T-4033
title: frob:claim directive (or frob:doc guidance) for cross-file comment assertions
state: queued
kind: feature
origin: agent
created: '2026-09-06'
priority: medium
parent: T-4025
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_docenum.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given a design decision between a new frob:claim directive and frob:doc-guidance-plus-lint,
    when this ticket's design step completes, then the choice and its reasoning is
    recorded before implementation
  evidence: []
- text: given a comment asserting a fact about another file/symbol under the chosen
    mechanism, when that other file changes incompatibly, then DRIFT001 (or a sibling
    rule) flags the stale assertion the same way it flags a stale same-file frob:doc
    claim
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Item 5. VERIFIED: git grep confirms frob:claims (plural, DOC003, src/frob/gates/_sys.py) already exists but is a DIFFERENT mechanism -- it proves a strata design-level "view" claim about a system, not a general-purpose cross-file factual assertion. There is no directive for an ordinary comment in file A stating a fact about file B's behavior.

FINDING THIS WOULD HAVE CAUGHT: a comment asserting a fact about ANOTHER FILE (e.g. "this value must match the constant in other_module.py" or "this endpoint is only reachable because auth/csrf.py exempts it") sits entirely outside the drift graph -- DRIFT001 has no way to see it, because DRIFT001 only tracks frob:doc-anchored claims about the symbol/file the comment is actually attached to, not claims a comment makes ABOUT a different path. So a comment can assert something false about another file forever with no gate ever re-checking it.

Proposed: either (a) a new frob:claim <path>[::<symbol>] directive that binds a comment's assertion to the OTHER file/symbol it is actually about, entering it into the drift graph the same way frob:doc does for same-file claims, or (b) guidance-plus-lint: any comment naming another path in its own text must use frob:doc rather than a bare comment (i.e. treat it as a mispositioned frob:doc rather than inventing a new directive). Decide between the two before implementing -- (b) reuses existing machinery entirely; (a) is more precise about what changed. Recommend starting with (b) since it is strictly cheaper and may fully close the gap.
