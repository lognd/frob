+++
id = "01M3ZVQAA1DNM1BJ5TZG5B3CFR"
title = "gob-symbols: element and variant type inference to bring COV001 Unresolved below 40"
type = "task"
category = "in-progress"
priority = "medium"
points = 5
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-03T03:08:03Z"
updated = "2026-10-03T03:25:17Z"
idempotency_key = "m2-gobsym-element-types"
labels = ["milestone:2"]
scope = ["crates/gob-symbols/**", "crates/frob-obligations/**", "docs/reference/fidelity.md"]

[[links]]
kind = "blocked-by"
target = "01M3ZVQA77ZEK9DXEN5Z0XMZEG"

[[acceptance]]
text = "Given this repository, when frob check runs, then COV001 Unresolved findings number below 40 and the soundness tests of gob-symbols still pass"
bound = false
+++

Carries the unmet acceptance of ~S404RDJ (284 -> 84; target below 40). Remaining 68 root sites by receiver: for-loop variables over collections (14), let bound to std/chained expressions (11), enum or Some pattern bindings (10), closure parameters in iterator chains (9), parameters of external types (8), path calls through derive-generated impls (7), bare calls through macro-generated items (5), other (4). Work: element types of Vec/slice/HashMap/BTreeMap/Option/Result iteration and iterator adaptors (map, filter, iter, into_iter, values, keys), enum variant field types for match and if-let bindings, a small table of std return types, and derive-generated associated functions for known derives (Default, the repo's own derives) as Must where the derive is unambiguous. Bump EXTRACTOR_VERSION. Soundness first: anything uncertain stays May. Depends on the cross-crate poisoning fix.
