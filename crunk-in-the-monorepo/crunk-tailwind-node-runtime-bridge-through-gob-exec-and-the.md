+++
id = "01M43ARYX61ESX3S9XG1WS0DQ4"
title = "crunk-tailwind: node runtime bridge through gob-exec and the first-run notice"
type = "story"
category = "done"
outcome = "done"
priority = "medium"
points = 5
parent = "01M43ANVJYA7GHN0Y8GX0SN72M"
reporter = "lognd"
created = "2026-10-04T11:28:49Z"
updated = "2026-10-08T14:30:21Z"
idempotency_key = "crunk-plan-twrt"
labels = ["area:crunk", "creates:crates/crunk-tailwind/src/runtime/**", "creates:crates/crunk-tailwind/node/**", "creates:crates/crunk-tailwind/tests/runtime*.rs", "creates:crates/crunk-tailwind/README.md"]
scope = ["crates/crunk-tailwind/src/runtime/**", "crates/crunk-tailwind/node/**", "crates/crunk-tailwind/tests/runtime*.rs", "crates/crunk-tailwind/Cargo.toml", "crates/crunk-tailwind/src/lib.rs", "Cargo.lock", "crates/crunk-tailwind/README.md", "crates/crunk-tailwind/tests/fixtures/**"]

[[links]]
kind = "blocked-by"
target = "01M40VH6HES1X3P57WZS0S9G93"

[[links]]
kind = "blocked-by"
target = "01M43ARVZPN52N6NMB7VRKZYGS"

[[acceptance]]
text = "Given a project with tailwind installed, when the runtime runs, then compiled utilities are returned and cached"
bound = true

[[acceptance]]
text = "Given no node on PATH, when TW rules need the runtime, then the finding state is Unresolved with that reason, never clean"
bound = true

[[acceptance]]
text = "Given a helper that exceeds the timeout or output cap, when run, then it is killed and reported with the cap named"
bound = true
+++

Port tailwind_runtime (1195 LOC, node/helper.mjs): run the project's own tailwindcss out of process behind gob-exec (timeout, scrubbed env via ~S0S9G93, output cap), parse compiled CSS with the CSS adapter, cache results, first-run notice (it executes project code: a trust note per security.md), `doctor` presence table; without node the result is Unresolved 'unresolved-by-tailwind'. Tests that need node are in the optional CI job.
