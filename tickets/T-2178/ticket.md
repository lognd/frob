---
id: T-2178
title: 'DEPR call-detection is a self-admitted textual heuristic, not a parse: _looks_like_call
  regexes raw source lines, so a commented-out mention counts as a live call and an
  aliased call is missed'
state: queued
kind: bug
origin: human
created: '2026-08-16'
priority: high
parent: T-1662
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/_debt_deprecated.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
acceptance:
- text: The fix MUST decide from tokens/grammar, never text. Resolve 'is this deprecated
    symbol called here' from the parsed AST (a real ast.Call whose func resolves to
    the symbol) and/or frob.graph's import+call edges, exactly as REF001 was fixed
    under T-1665. Do NOT strip comments and keep regexing -- that patches one direction
    and leaves aliased and attribute calls wrong. This test MUST fail against current
    main.
  evidence: []
- text: Given a file whose ONLY mention of a deprecated symbol is inside a comment
    or string literal, when the DEPR gate runs, then it reports no call site (today
    _looks_like_call matches it -- src/frob/gates/_debt_deprecated.py:503, applied
    at :610 to raw (file,line,ctx) text hits with no comment stripping).
  evidence: []
- text: Given a file that imports a deprecated symbol under an alias and calls it
    through that alias, when the DEPR gate runs, then the call IS reported (today
    the bare-name regex cannot see it).
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
---
