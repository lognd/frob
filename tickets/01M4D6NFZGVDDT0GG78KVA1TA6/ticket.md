+++
id = "01M4D6NFZGVDDT0GG78KVA1TA6"
title = "frob-tests: use the shared repository cache for the touched-set graph instead of Cache::null()"
type = "task"
category = "todo"
priority = "high"
points = 2
parent = "01M4D6NB00MBEV0PRHN15CXZP8"
reporter = "lognd"
created = "2026-10-08T07:29:25Z"
updated = "2026-10-09T18:00:16Z"
labels = ["creates:crates/frob-tests/tests/graph_cache.rs"]
scope = ["changelog.d/**", "crates/frob-tests/src/touched.rs", "crates/frob-tests/src/lib.rs", "crates/frob-tests/tests/graph_cache.rs"]

[[acceptance]]
text = "Given a second frob test on an unchanged tree, when timed, then planning reads the cache (counter test)"
bound = false
+++

notes/research/profile-2026-10-07.md section 5 item 5 (touched.rs:64; planning 5.6-7.2 s every run).
