---
id: T-1852
title: Extend WIRE002's permanent=true escape hatch to dispatch-bypassed production
  CLI dests
state: dropped
kind: feature
origin: human
created: '2026-08-08'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/_wire.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
T-1820 documented that frob quality bind's argparse dests
(--list-bindings/--list-sources/--json in src/frob/_cli_parsers/
_quality.py) are permanently, by-design unwired: frob.__main__._dispatch
special-cases 'quality bind' before AppConfig is ever built, mirroring
the pre-existing top-level bind_p in _core.py (grandfathered, predates
WIRE001, so it was never flagged). The `frob:waive WIRE001
follow_up="T-1820"` directives on those three dests need to keep citing
a real, open ticket forever (WIRE002, error, unwaivable) because
WIRE002's own `permanent="true"` escape hatch
(`_wire002_is_permanent_test_helper_waiver`) is restricted to private
symbols under `tests/` -- production code has no equivalent, so a
ticket like T-1820 that documents a genuinely-permanent gap has no way
to stop being cited as a live tracker without either staying open
forever or repointing to a fresh successor on every closure (which is
exactly the "placeholder ticket re-orphans WIRE002 the moment it
closes" anti-pattern T-1592 already fixed for the test-tree case).

Real fix: extend `_wire002_is_permanent_test_helper_waiver`
(src/frob/gates/_wire.py) to also recognize a `permanent="true"`
`frob:waive WIRE001` on a PRODUCTION (non-test-tree) CLI dest whose
enclosing parser is dispatch-bypassed before `AppConfig` is built --
the same shape as the test-tree escape, generalized to a second,
narrowly-scoped predicate rather than a blanket "any permanent=true in
src/ is exempt" (which would let real deferred work dodge WIRE002 by
just writing permanent="true"). A reasonable scoping signal: the
enclosing subparser is one `frob.__main__._dispatch` special-cases by
name before parser-tree consultation (grep the dispatch table for a
literal match), so the exemption is anchored to a real, checkable fact
about the dispatch code rather than trusted prose.

Until this lands, src/frob/_cli_parsers/_quality.py's three WIRE001
waivers point at THIS ticket as their live follow_up tracker.

## Drop reason
- 2026-08-08: Coordinator correction: T-1820 is a permanent-by-design waiver anchor (T-1558 precedent) that stays queued/open forever; WIRE002 only requires a non-terminal follow_up target, so no WIRE002 escape-hatch extension is needed. No fix to make.
