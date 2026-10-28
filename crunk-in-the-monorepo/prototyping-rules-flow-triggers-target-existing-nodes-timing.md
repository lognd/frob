+++
id = "01M5XCZ1K91B012K3QDSH0JBCS"
title = "Prototyping rules: flow triggers target existing nodes, timing within token bounds, reduced-motion twins"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M4CXSAG0YPF18FX3KAPVX45C"
reporter = "lognd"
created = "2026-10-27T00:43:03Z"
updated = "2026-10-28T12:56:01Z"
labels = ["area:crunk", "no-story"]
scope = ["crates/crunk-rules/src/ux/motion.rs, crates/crunk-rules/tests/ux_motion.rs"]

[[links]]
kind = "blocked-by"
target = "01M5XCVZBYWA5WCATMF9QYZAS8"

[[acceptance]]
text = "Given a flow trigger targeting a missing node, when checked, then a UX finding fires; given an animation duration token above the bound, then it fires; given a motion without a reduced-motion twin, then it fires. Edge cases: a duration literal instead of a token is flagged; zero duration is valid; a twin that is itself animated beyond the bound fires; no motion tokens declared is Unresolved"
bound = false
+++

Design crunk.md section 8 prototyping row.

no-story: internal engineering task in crunk-rules; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
