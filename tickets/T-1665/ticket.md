---
id: T-1665
title: 'REF001: decide inbound references from resolved imports and calls, not path/basename
  text mentions'
state: planned
kind: bug
origin: human
created: '2026-08-06'
priority: high
blocked_by:
- T-1663
- T-1985
parent: T-1662
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/_refs.py
- src/frob/graph/**
- docs/modules/gates.md
- tests/unit/gates/test_refs.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: tests/**
  reason: 'narrow the tests/** umbrella to the one test file REF001''s change needs.
    This was the last outstanding TICK009 breadth nudge and it collapses the wave
    partition: with it present, frob ticket wave --agents 4 folds nearly every ticket
    into one group. T-1985 (the resolved-import substrate this ticket depends on)
    has landed, so T-1665 is now startable and the umbrella would lease the entire
    test tree.'
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tests/unit/gates/test_refs.py
  reason: 'narrow the tests/** umbrella to the one test file REF001''s change needs.
    This was the last outstanding TICK009 breadth nudge and it collapses the wave
    partition: with it present, frob ticket wave --agents 4 folds nearly every ticket
    into one group. T-1985 (the resolved-import substrate this ticket depends on)
    has landed, so T-1665 is now startable and the umbrella would lease the entire
    test tree.'
  actor: logan
  at: '2026-08-10'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
REF001 decides whether a file has any inbound reference by searching other files' TEXT for its full repo-relative path or its BARE BASENAME. Its own module docstring says so: "by file Y if Y names X (full repo-relative path or bare basename) in a ... literal, a backtick-wrapped MULTI-COMPONENT path mention".

That is wrong in both directions:
- FALSE POSITIVE (reports dead when live): a module reached through an import alias, a constructed path (`root / "sub" / name`), a dynamic import, a registry/dispatch table, or a plugin entry point is never NAMED anywhere, so it reads as unreferenced.
- FALSE NEGATIVE (reports live when dead): a file merely mentioned in prose, a changelog entry, or a comment counts as referenced. A genuinely dead module stays hidden as long as some document names it.

Both matter. The false positives generate waivers that then have to be maintained forever (REF002 is at 51 findings largely for this reason), and the false negatives defeat the rule's entire purpose.

Raise it to semantics:
- For code targets, an inbound reference means a resolved IMPORT or a resolved call/attribute reference reaching that module -- frob.graph.callgraph and the snapshot's edges already model this.
- Keep an explicit, NARROW textual channel for the genuinely non-code cases the rule must still cover: a config file named in a template, a data file read by path. Those should be an explicit declared-reference form (`frob:used-by`, which already exists) rather than an accidental substring hit.
- Per T-1664, a target whose reachability cannot be resolved must report UNRESOLVED, not "referenced" and not "dead".

Expect the finding set to CHANGE substantially in both directions, not merely shrink. Report before/after with a classification of everything that appears and disappears -- a file that stops being flagged because it is genuinely imported is a fix; one that starts being flagged because only prose named it is the rule finally working.

While here, check whether the existing REF001 waivers were compensating for the lexical gap. If most of them say some version of "reached dynamically", that is direct evidence for the semantic model and those waivers should be REMOVED, not migrated.

## Failure log
- 2026-08-10 attempt 1: investigated, not landed: no resolved-import substrate exists in frob.graph (EdgeKind is directive-edges-only; callgraph.py excludes public/exported symbols by design); measured today's REF001 findings (2, both non-code, 0 waived) -- semantic rewrite would not change either. Design + prerequisite filed as T-1985, blocking this ticket.
