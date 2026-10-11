+++
id = "01M43ARWT173GKANZ322H41VF1"
title = "CI: path-filtered crunk jobs and an optional node and playwright job"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 3
parent = "01M43ANVJYA7GHN0Y8GX0SN72M"
reporter = "lognd"
created = "2026-10-04T11:28:47Z"
updated = "2026-10-11T00:55:25Z"
idempotency_key = "crunk-plan-ci"
labels = ["area:crunk"]
scope = [".github/workflows/ci.yml", "docs/crunk/ci.md", ".github/scripts/plan-jobs.py", "crates/gob-dev/tests/ci_plan.rs", "crates/gob-dev/tests/ci_parity.rs", "docs/crunk/README.md", "crates/frob-release/tests/dev_workflow.rs", "crates/frob-release/tests/ci_pins.rs"]

[[links]]
kind = "blocked-by"
target = "01M43ARWCVRCE25KDZC8CRC1ZH"

[[acceptance]]
text = "Given a change only under crates/crunk-values, when CI plans jobs, then crunk tests run and frob and grimble tests do not"
bound = true

[[acceptance]]
text = "Given a change under crates/gob-fix, when CI plans jobs, then all three products' tests run"
bound = true

[[acceptance]]
text = "Given the optional node job is red or skipped, when the merge gate is evaluated, then the merge is not blocked"
bound = true
+++

monorepo.md 4: crates/crunk-* runs the crunk tests, any crates/gob-* change runs all three products; the node Tailwind runtime and gallery tests live in a separate optional job (never required for merge). One `cargo dev gen --check` covers the three products.
