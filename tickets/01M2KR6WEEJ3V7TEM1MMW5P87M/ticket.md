+++
id = "01M2KR6WEEJ3V7TEM1MMW5P87M"
title = "iter_identifiers._IDENTIFIER_TYPES missing java/cuda/kotlin/bash/zig/typescript entries"
type = "bug"
category = "done"
outcome = "wont-fix"
priority = "medium"
reporter = "human"
created = "2026-09-16T00:00:00Z"
updated = "2026-10-04T21:06:48Z"
aliases = ["T-4558"]
labels = ["milestone:0.540.0", "v1-cluster:C4a"]
scope = ["src/frob/lang/_extract.py"]
+++

found while working T-3232: frob.xref's parsed-usage lookup (iter_identifiers) returns () for any language not in _extract.py's _IDENTIFIER_TYPES table. T-3232 added a 'csharp' entry (measured against tests/fixtures/lang/sample.cs) as the proven case; python/c/cpp/rust/csharp are covered, java/cuda/kotlin/bash/zig/typescript are not -- xref definitions still resolve for those (RawSymbol-based) but usages silently come back empty. Each grammar's own leaf-node type name for identifiers needs measuring against a fixture (see T-3232's _IDENTIFIER_TYPES edit for the pattern) before adding an entry; do not guess node type names.
