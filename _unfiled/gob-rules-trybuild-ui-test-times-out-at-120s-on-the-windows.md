+++
id = "01M7X13TZAFBWXR3J53Y14PGNN"
title = "gob-rules trybuild ui test times out at 120s on the Windows CI runner"
type = "bug"
category = "todo"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-11-20T17:47:20Z"
updated = "2026-11-20T17:47:20Z"
scope = ["crates/gob-rules/tests/**"]

[[acceptance]]
text = "Given the gob-rules ui tests on a loaded Windows runner, when nextest runs them, then none exceeds its time limit, or the slow compile tests carry an explicit longer limit"
bound = false
+++

CI run 44759330887 (rust windows-latest): ui::fix_without_applicability_does_not_compile hit nextest's 120 s limit once, and passed on re-run. Cause is likely a cold trybuild compile under load. Start in .config/nextest.toml: give the ui tests their own slow-timeout override, or share one trybuild target dir.
