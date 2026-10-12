+++
id = "01M4M27E8E0DK7XAQ2D7T0Q8TR"
title = "A tool stage that dies on an I/O error (ENOSPC, full disk) is recorded as resolved, so the land gate passes without running the lint"
type = "bug"
category = "done"
outcome = "done"
priority = "high"
points = 3
reporter = "lognd"
created = "2026-10-10T23:26:32Z"
updated = "2026-10-12T08:02:58Z"
scope = ["crates/gob-check/src/tools.rs"]

[[acceptance]]
text = "a tool stage whose process fails to spawn or write because of an I/O error is reported as a required Unresolved or an error, never as resolved, covered by a test with a simulated spawn or write failure"
bound = true
+++

found while draining tickets: during frob land, clippy stages hit ENOSPC and the findings were recorded as resolved, so the clippy gate was silently skipped; the worker had to rerun clippy by hand. A gate that cannot run must not pass.
