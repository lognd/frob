+++
id = "01M3DG64CNAZ8K50HQ046VKHER"
title = "test runners: exit-code-only outcome records PASS when the filter selects nothing; require executed-and-passed per bound id from the runner report"
type = "bug"
category = "todo"
priority = "medium"
reporter = "agent"
created = "2026-09-26T00:00:00Z"
updated = "2026-10-09T20:42:50Z"
aliases = ["T-6549"]
labels = ["v1-cluster:C4a", "triage:accepted"]
scope = ["src/frob/testing/_runners.py", "src/frob/testing/_collect.py", "src/frob/tickets/_land_verify.py", "src/frob/app/config.py", "tests/unit/test_runner_outcome_executed.py", "docs/design/testing.md"]
+++

Source: logand.app-v2 coordinator report, 2026-09-26 (frob 0.531.1.dev332), found while working F-410.

A runner shaped `npx vitest run -t "{regex}"` (today the only way to hand vitest a name filter) receives the full `path::describe > name` id, so vitest matches nothing, prints "Tests 1 skipped", and still exits 0. `_runner_outcome` (testing/_runners.py ~462-482) is exit-code-only, so `frob ticket evidence` would record PASS for a test that never executed, and the land's evidence re-verification would accept it. The agent refused to use it. The same hazard applies to every runner whose exit code is 0 when the filter selects nothing (pytest with -k matching nothing exits 5, but `--deselect`/xdist edge cases and other runners do not).

Deliver:
1. Verification of a bound id requires at least one EXECUTED and PASSED test attributable to that id: parse the runner's machine-readable report (pytest junit/json, vitest --reporter=json, dotnet trx, cargo --format json) and count per id; "0 selected" / "0 passed" / all-skipped is NOT PASSING, reported as EvidenceNotExecuted with the runner's own summary line.
2. Every runner entry in frob.toml declares how frob reads its results (a `report` field); a runner without one is UNMEASURED for granular evidence and only file/suite-level evidence is accepted, loudly.
3. Positive control per runner: a fixture whose filter matches nothing must be reported as not passing; a matching one passes; a skipped-only run is not passing.
4. docs/modules/testing.md documents the executed-and-passed requirement.
