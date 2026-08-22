---
id: T-2875
title: 'frob.graph.dsl._RESERVED_MARKER_VERBS omits callee-raises, so a real # frob:callee-raises
  call-site marker fires DSL001 unknown-verb'
state: in-progress
kind: bug
origin: human
created: '2026-08-22'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/graph/dsl.py
- tests/unit/graph/test_dsl.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/graph/test_dsl.py
  reason: T-2875's own regression test lives here
  actor: logan
  at: '2026-08-22'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while satisfying FFI002 on src/frob/process/_reap.py's real libc.prctl(...) call in T-2849 (the first genuine, non-test, non-docstring-prose production use of the frob:callee-raises call-site marker in this repo).

frob.graph.dsl._RESERVED_MARKER_VERBS = frozenset({"secret-fake", "used-by", "raises"}) explicitly documents why "callee-raises" (T-0931's call-site sibling of the standalone "raises" verb, owned by frob.arch._python/frob.arch._ffi/frob.gates._ffi_boundary) is NOT listed: its own comment claims callee-raises is "a same-line trailing comment the DSL line-based scan never matches in the first place, so only the standalone-line raises verb needs listing here."

Reproduced directly against frob.graph.dsl.parse_directives: this claim is false for a comment whose FULL text is exactly "frob:callee-raises" (nothing else on the comment) -- confirmed identically for BOTH a same-line trailing placement (lib.do_thing(1)  # frob:callee-raises) and a standalone full-line placement, each producing MalformedDirective(reason="unknown verb 'callee-raises'"). The one-verb-string difference from the already-exempted "raises" entry appears to be a simple oversight, not a deliberate omission -- the position-based reasoning in the comment does not hold either way.

Fix: add "callee-raises" to _RESERVED_MARKER_VERBS (with an updated comment correcting the stale "never matches" claim), matching the existing "raises"/"used-by"/"secret-fake" precedent exactly. Add a regression test exercising a bare-text "# frob:callee-raises" comment (both placements) through parse_directives, asserting no MalformedDirective -- the existing ffi_boundary_gate tests never exercise frob.graph.dsl's own DSL001 path for this marker, which is how this went unnoticed.

Positive controls both directions: a genuinely unknown verb (anything not in _VERB_TABLE or _RESERVED_MARKER_VERBS) must still report DSL001.

Workaround applied at the T-2849 call site in the meantime: frob:waive DSL001 on that one line, citing this ticket as follow_up.