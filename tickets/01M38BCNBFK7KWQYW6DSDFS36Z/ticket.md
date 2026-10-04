+++
id = "01M38BCNBFK7KWQYW6DSDFS36Z"
title = "Wire dotnet/unity test runners into ticket-runner CLI for csharp/Unity node ids"
type = "task"
category = "todo"
priority = "low"
reporter = "human"
created = "2026-09-24T00:00:00Z"
updated = "2026-10-04T22:22:24Z"
aliases = ["T-5487"]
labels = ["v1-cluster:C4a", "triage:accepted"]
scope = ["src/frob/app/ticket_runner/**"]
+++

T-4516's own scope note (WIRE001 waiver on run_dotnet_tests/run_unity_batchmode) said this routing was T-4516's job, but T-4516 closed as a story rollup without actually wiring the CLI: no src/frob/app/** caller of run_dotnet_tests/run_unity_batchmode exists. Route frob's ticket-runner CLI to call these for csharp/Unity node ids (blocked on T-4518's project-model detection, same as the original note). Found while working T-5470.
