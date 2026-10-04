+++
id = "01M421PY49MQ5WX8RGQ36ZXTMR"
title = "Warm frob check still assembles the whole symbol graph (0.7 s release): link_calls is sequential and the assembled graph is not cached"
type = "bug"
category = "done"
outcome = "done"
priority = "medium"
reporter = "lognd"
created = "2026-10-03T23:31:11Z"
updated = "2026-10-04T05:50:18Z"
scope = ["crates/gob-symbols/src/graph.rs", "crates/gob-symbols/src/pipeline.rs", "crates/gob-symbols/tests/gaps.rs"]

[[acceptance]]
text = "Given the same repository, when the symbol graph is built with 1, 2, 4 and 8 threads, then the graph is identical and the warm graph stage is faster than before"
bound = true
+++

found while working ~A8AMNGF. Release, warm, nothing changed: per-file stage 0.22 s (1163 cached, 0 extracted), then SymbolGraph::from_files_with_deps takes 0.71 s, of which link_calls is about 0.9 s of a 1.0 s cumulative total under -vv (add_file 39 ms, index_of 31 ms, imports 4 ms). Options: parallelise link_calls resolution over files (resolve_site reads the graph, record_call mutates), or cache the assembled graph keyed by the digest of all file digests plus the Cargo manifests CrateDeps reads. Acceptance: warm graph stage under 0.25 s in release on this repository with identical findings.
