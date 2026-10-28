+++
id = "01M5XCWYMSEMEQPNZ7EFHHY9Z7"
title = "crunk render --engine solve and crunk snapshot [--update]: write layout-solve JSON and compare to committed baselines"
type = "task"
category = "todo"
priority = "medium"
points = 5
parent = "01M4CXRC0Z94MGD87PY9NH8B7X"
reporter = "lognd"
created = "2026-10-27T00:41:54Z"
updated = "2026-10-28T12:55:53Z"
labels = ["area:crunk", "no-story"]
scope = ["crates/crunk/src/render.rs, crates/crunk/src/snapshot.rs, crates/crunk/tests/render_solve.rs"]

[[links]]
kind = "blocked-by"
target = "01M5XCWYB9M2YSJ5EGABMREX1B"

[[acceptance]]
text = "Given a scene corpus, when crunk render --engine solve runs, then one layout-solve JSON per screen/state/platform is written. Edge cases: a screen with no scene file exits 2 naming it; --engine browser without the gallery feature reports not built in with the remedy; snapshot without --update on a missing baseline fails and names the path; snapshot --update rewrites only changed baselines; baselines differ only by a changed node and diff lists node id and delta; output order is deterministic across --jobs values"
bound = false
+++

Design crunk.md section 5 render row and section 3 baselines. Baselines are committed under design/baselines/. Reuses crunk diff --layout where it exists.

no-story: internal engineering task in crunk; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
