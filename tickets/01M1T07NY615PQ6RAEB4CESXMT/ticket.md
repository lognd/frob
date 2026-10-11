+++
id = "01M1T07NY615PQ6RAEB4CESXMT"
title = "unpaired resource acquisition: known acquire/release API table"
type = "security"
category = "done"
outcome = "done"
priority = "medium"
points = 5
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "agent"
created = "2026-09-06T00:00:00Z"
updated = "2026-10-11T04:04:51Z"
aliases = ["T-4038"]
labels = ["v1-cluster:B4", "triage:accepted"]
scope = ["crates/grimble-lints/**", "Cargo.lock"]

[[acceptance]]
text = "Given the design note comment on this ticket settling the acquire/release pair table shape (and that the v1 _protocol_summary.py logic is not reusable: it no longer exists in this tree), when implementation starts, then the note is attached to the ticket"
bound = true

[[acceptance]]
text = "Given TypeScript or JavaScript source with performance.mark(), a Map.set() on a receiver built by new Map, or a bound setTimeout() and no paired release in the scope, when grimble_lints::res::scan runs, then one site per acquire with the pair id and Certainty::Certain"
bound = true

[[acceptance]]
text = "Given the same acquires with the paired release (clearMarks, delete, clearTimeout) in scope, when scanned, then no site"
bound = true

[[acceptance]]
text = "Given the table rows for addEventListener, setInterval, URL.createObjectURL and new AbortController, when scanned without and with the paired release, then a site and no site; adding a row is a data change to the PAIRS table"
bound = true
+++

Item 2, the highest-value new rule kind in this list. VERIFIED: src/frob/gates/_protocol_summary.py already implements a related but DIFFERENT mechanism -- a manually-annotated frob:acquire/release-postdominance check requiring an explicit frob:acquire directive on the resource. This item needs NO annotation: it is a fixed known-API table of acquire/release pairs (performance.mark/performance.clearMarks, Map.set/Map.delete, setTimeout/clearTimeout) recognized structurally, with no directive required. Confirm during design whether the existing release-postdominance logic in _protocol_summary.py is reusable machinery for the "does a release call exist on all exit paths" half of this check, even though the pairing itself is looked up in a table rather than declared.

FINDING THIS WOULD HAVE CAUGHT (three findings, one rule): performance.mark() called with no corresponding performance.clearMarks(), leaking marks across the page's lifetime; a Map.set() with no corresponding delete() outside a test helper (a production memory-leak shape); setTimeout() with no corresponding clearTimeout() on the relevant exit/cleanup path. All three are the same missing rule -- an acquire/release API pair where a scope (function, component lifecycle, class) contains the acquire call with no matching release call anywhere in the same scope.

GENERALIZES CLEANLY, per the consumer, to: addEventListener/removeEventListener, URL.createObjectURL/revokeObjectURL, and an AbortController whose controller is created but never had .abort() called or was never passed to a signal that gets cleaned up. Design the rule as a table of (acquire_method, release_method, scope_kind) triples so adding a new pair later is a data change, not a new detector.

STRUCTURAL, NO TAINT ANALYSIS NEEDED per the consumer's own framing -- this is a pure AST-shape check (a call to the acquire method with no reachable call to its paired release method in the same enclosing scope), the cheapest class of rule this repo builds.
