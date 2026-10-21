+++
id = "01M5GCNBD6AT6HNQKF3MQTXQC5"
title = "Feed BuildStats.malformed_projects into frob-check's Product::malformed_projects"
type = "task"
category = "in-progress"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-21T23:27:37Z"
updated = "2026-10-21T23:45:20Z"
scope = ["crates/frob-check/src"]

[[acceptance]]
text = "FrobProduct::malformed_projects returns the malformed project files recorded by the build"
bound = false
+++

found while working ~YTG1ZYC: gob-check now has Product::malformed_projects (default empty). frob-check must store built.malformed_projects in FrobShared (snapshot.rs) and return it from FrobProduct::malformed_projects (product.rs).
