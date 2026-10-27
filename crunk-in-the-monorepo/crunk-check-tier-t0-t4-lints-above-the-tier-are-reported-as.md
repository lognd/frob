+++
id = "01M5XCXV02ZVYV71DFY08R5Y3H"
title = "crunk check --tier T0..T4: lints above the tier are reported as not run, never clean"
type = "task"
category = "in-progress"
priority = "medium"
points = 5
parent = "01M4CXRV40WWJQKHWJJBKJT1HZ"
reporter = "lognd"
created = "2026-10-27T00:42:23Z"
updated = "2026-10-27T00:44:46Z"
labels = ["area:crunk"]
scope = ["crates/crunk-check/src/tier.rs, crates/crunk-check/tests/tier.rs", "crates/crunk-check/src/lib.rs", "crates/crunk-check/src/sibling.rs"]

[[acceptance]]
text = "Given a project and --tier T1, when check runs, then every rule whose declared tier is T2 or above is listed as not run with its tier and the exit code is unaffected by them; given the default, then the tier is T1. Edge cases: an unknown tier value exits 2 listing T0-T4; a must_measure rule above the tier is Unresolved not run, never green; --tier T0 skips solver-backed rules and says so; rules with no declared tier default to T0; the not-run list is stable-ordered; --family F combined with --tier filters both"
bound = false
+++

Design crunk.md section 4 (D112). The tier attribute already exists on the rule macros (tier = Universal in gx_pack.rs); this ticket reads it. Touch the check driver minimally; the not-run report is a separate envelope section.
