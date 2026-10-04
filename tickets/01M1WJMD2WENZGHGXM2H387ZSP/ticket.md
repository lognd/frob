+++
id = "01M1WJMD2WENZGHGXM2H387ZSP"
title = "frob:invariant call-graph-closure kind: a symbol reading a guard state must have a reachable in-tree writer"
type = "task"
category = "todo"
priority = "low"
parent = "01M1T07P0DHR8Z9D3E3PRGDJ7B"
reporter = "agent"
created = "2026-09-07T00:00:00Z"
updated = "2026-10-04T22:22:22Z"
aliases = ["T-4188"]
labels = ["v1-cluster:B4", "triage:accepted"]
scope = ["src/frob/gates/_wire.py"]
+++

Consumer F-307/H3-1 (T-4109): a rate-limit guard's test trips the lockout by calling the recorder directly, proving the guard reads a lockout without proving anything writes one. Reuses the WIRE001 call-graph resolver for a new invariant kind: every reader of state X has at least one in-tree caller of the writer, reachable from the same entry class as the reader. NOT the same mechanism as T-4151 (T-4151 is WIRE001 false negatives on existing callers; this is a positive effectiveness/closure check using the same resolver). Fixture-testable: the resolver mechanism YES with a synthetic read/write pair in frob's own tree; the rate-limit domain itself does not exist here. Consumer-blocking: latent for us.
