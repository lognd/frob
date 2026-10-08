+++
id = "01M4CS7ZMEY096RVK91RWD03DW"
title = "cargo dev profile: time every frob, grimble and crunk command, budget file, CI profile job"
type = "story"
category = "todo"
priority = "high"
points = 8
reporter = "lognd"
created = "2026-10-08T03:34:51Z"
updated = "2026-10-08T03:34:51Z"
scope = ["crates/gob-dev/**", ".github/workflows/ci.yml", "Cargo.toml", "Cargo.lock", "docs/design/build-test-ci.md", "changelog.d/**"]

[[acceptance]]
text = "Given the three binaries, when cargo dev profile runs, then report.json has one entry per leaf command (wall median, cold where set, max RSS, exit) and a test fails naming any leaf command with no scenario and no skip reason"
bound = false

[[acceptance]]
text = "Given a command over its budget_ms times the budget factor, when cargo dev profile runs, then it exits non-zero naming the command, the measured and the budget"
bound = false

[[acceptance]]
text = "Given a push or PR, when CI runs, then a profile job runs cargo dev profile on ubuntu, uploads report.json, and writes the markdown table to the step summary"
bound = false

[[acceptance]]
text = "Given no command ever mutates the primary checkout, when a mutating verb is profiled, then it runs only inside the throwaway clone (test asserts the source checkout's HEAD, index and ledger are unchanged)"
bound = false
+++

Owner request 2026-10-07: profile every command and build the profiling into CI. Design: docs/design/build-test-ci.md section 4 (bench row) and architecture.md section 9 (warm budget). Build a 'profile' subcommand in gob-dev: (1) builds the three product binaries with a release-like profile (add [profile.profiling] inheriting release, lto off, debug line-tables, so perf can attribute); (2) enumerates every leaf command of frob, grimble and crunk from the clap trees (not a hand list) and runs a scenario per leaf from crates/gob-dev/profile.toml (args, fixture: 'repo' = a throwaway local clone of this checkout at HEAD with experimental as a local branch, or 'tmp' = an empty init'd dir; mutating verbs only ever run in the clone); (3) measures warm wall median over N runs after one warm-up, cold wall where the scenario sets cold = true (deletes .frob/ cache first), max RSS of the child, exit code, and captures the --timing stage tree when the verb supports it; (4) writes target/profile/report.json (schema in the gob-dev source, serde) and a markdown table (to GITHUB_STEP_SUMMARY when set); (5) fails when a command exceeds its budget_ms (absolute, from profile.toml; CI uses a --budget-factor knob for slow runners) or exits unexpectedly; (6) --compare BASE.json prints per-command deltas, non-blocking. A unit test fails naming every leaf command that has neither a scenario nor skip = 'reason'. CI: a separate 'profile' job in .github/workflows/ci.yml on ubuntu-latest (parallel with the rust job, pinned toolchain, cache like the rust job) running cargo dev profile, uploading report.json as an artifact, and comparing against the latest experimental artifact when one exists. Seed budgets from the measured numbers with headroom; record the initial table in build-test-ci.md.
