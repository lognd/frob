+++
id = "01M7HNFQ470MGXGSX3K1M61BC6"
title = "Windows CI: twelve_ready_tickets land test exceeds 120s hang guard"
type = "bug"
category = "in-progress"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-11-16T07:52:28Z"
updated = "2026-11-16T08:05:24Z"
idempotency_key = "win-twelve-land-timeout"
labels = ["no-story"]
scope = [".config/nextest.toml"]

[[acceptance]]
text = "The test passes on windows-latest CI within its slow-timeout"
bound = true
+++

no-story: CI flake. frob-land it land::twelve_ready_tickets_with_one_failing_land_eleven_and_return_the_culprit timed out at 120s on windows-latest in the run for daf78349e5 (7968/7969 passed). Add a reviewed [[profile.ci.overrides]] slow-timeout in .config/nextest.toml with reason, or trim the fixture.
