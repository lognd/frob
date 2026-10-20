+++
id = "01M12TN64ZEWJ5GWV8579C7XZT"
title = "EPIC refactor multi-language: per-language reference scanners"
type = "epic"
category = "done"
outcome = "wont-fix"
priority = "medium"
reporter = "human"
created = "2026-08-28T00:00:00Z"
updated = "2026-10-04T21:08:46Z"
aliases = ["T-3231"]
labels = ["milestone:1.1.0", "v1-cluster:D2"]
scope = ["src/frob/refactor/**"]
+++

T-2996 found frob.refactor (move-module/move-symbol) is Python-only: _MODULE_LANGUAGE_ADAPTERS has one entry (python) and _scan.py's symbol-move engine is Python AST-specific. Tracks widening to typescript/rust/c/cpp/kotlin/csharp/bash per T-2996's FACET_REFACTOR known-gap cells. strata is a design DSL without an established symbol-move convention; revisit if one emerges.
