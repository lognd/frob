+++
id = "01M53EVTSACNVDRSKYY4PQX0RF"
title = "COV001 python example 2: unresolved verdict for a call reached through a parameter callee"
type = "bug"
category = "in-progress"
priority = "medium"
points = 3
parent = "01M4Z1KTKEVF53GWM6ZN7PFN4Q"
reporter = "lognd"
created = "2026-10-16T22:55:59Z"
updated = "2026-10-17T05:10:19Z"
scope = ["crates/gob-plan/**", "crates/gob-ir/src/eval/**", "docs/design/grl-spec.md", "changelog.d/01M53EVTSACNVDRSKYY4PQX0RF.fixed.md"]

[[acceptance]]
text = "given the COV001 python example 2, when run, then the engine reports unresolved and the gap entry is gone"
bound = true
+++

found while working ~8KS9TG8: python helper(cb): cb() is marked unknown_out, but test_run -> helper is a Yes edge so COV001 stays clean; the example expects unresolved. Entry (COV001, 2) stays in KNOWN_ENGINE_GAPS and the corpus_tests skip list.
