+++
id = "01M1T07NY615PQ6RAEB4CESXMT"
title = "unpaired resource acquisition: known acquire/release API table"
type = "security"
category = "todo"
priority = "medium"
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "agent"
created = "2026-09-06T00:00:00Z"
updated = "2026-10-08T08:13:43Z"
aliases = ["T-4038"]
labels = ["v1-cluster:B4", "triage:accepted"]
scope = ["src/frob/gates/_protocol_summary.py"]

[[acceptance]]
text = "given a design note settling the acquire/release pair table shape and whether the existing release-postdominance logic in _protocol_summary.py is reused, when this ticket's design step completes, then the note is attached before implementation"
bound = false

[[acceptance]]
text = "given a scope containing performance.mark(), Map.set(), or setTimeout() with no reachable paired release call in the same scope, when frob check runs, then the new rule fires"
bound = false

[[acceptance]]
text = "given a properly paired acquire/release call, when frob check runs, then the rule stays quiet"
bound = false
+++

Item 2, the highest-value new rule kind in this list. VERIFIED: src/frob/gates/_protocol_summary.py already implements a related but DIFFERENT mechanism -- a manually-annotated frob:acquire/release-postdominance check requiring an explicit frob:acquire directive on the resource. This item needs NO annotation: it is a fixed known-API table of acquire/release pairs (performance.mark/performance.clearMarks, Map.set/Map.delete, setTimeout/clearTimeout) recognized structurally, with no directive required. Confirm during design whether the existing release-postdominance logic in _protocol_summary.py is reusable machinery for the "does a release call exist on all exit paths" half of this check, even though the pairing itself is looked up in a table rather than declared.

FINDING THIS WOULD HAVE CAUGHT (three findings, one rule): performance.mark() called with no corresponding performance.clearMarks(), leaking marks across the page's lifetime; a Map.set() with no corresponding delete() outside a test helper (a production memory-leak shape); setTimeout() with no corresponding clearTimeout() on the relevant exit/cleanup path. All three are the same missing rule -- an acquire/release API pair where a scope (function, component lifecycle, class) contains the acquire call with no matching release call anywhere in the same scope.

GENERALIZES CLEANLY, per the consumer, to: addEventListener/removeEventListener, URL.createObjectURL/revokeObjectURL, and an AbortController whose controller is created but never had .abort() called or was never passed to a signal that gets cleaned up. Design the rule as a table of (acquire_method, release_method, scope_kind) triples so adding a new pair later is a data change, not a new detector.

STRUCTURAL, NO TAINT ANALYSIS NEEDED per the consumer's own framing -- this is a pure AST-shape check (a call to the acquire method with no reachable call to its paired release method in the same enclosing scope), the cheapest class of rule this repo builds.
