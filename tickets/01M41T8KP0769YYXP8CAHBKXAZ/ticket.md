+++
id = "01M41T8KP0769YYXP8CAHBKXAZ"
title = "CI-only failures keep surprising lands: rustdoc broken link now; add cargo dev ci that runs exactly the CI checks locally"
type = "bug"
category = "in-progress"
priority = "critical"
points = 5
reporter = "lognd"
created = "2026-10-03T21:21:02Z"
updated = "2026-10-03T21:44:13Z"
scope = ["crates/frob-pm/src/board.rs", "crates/gob-dev/**", ".github/workflows/ci.yml", "crates/frob-release/tests/ci_pins.rs", "CONTRIBUTING.md"]

[[acceptance]]
text = "Given the workspace, when cargo dev ci runs, then it runs every Linux check ci.yml runs, with the same flags, and passes"
bound = true

[[acceptance]]
text = "Given a check added to ci.yml but not to cargo dev ci (or with different flags), when the parity test runs, then it fails naming the check"
bound = true

[[acceptance]]
text = "Given the board module, when cargo doc runs with -D warnings, then it is clean"
bound = false
+++

CI run https://github.com/lognd/frob/actions/runs/37153663616 (2026-10-03): ubuntu fails in the Docs step, cargo doc --no-deps --all-features with RUSTDOCFLAGS=-D warnings: unresolved link to DONE_SHOWN at crates/frob-pm/src/board.rs:24 (from ~4XZVMNC). Every implementer ran fmt, clippy, nextest and gen --check locally but never cargo doc, so CI and the local gate disagree. This is the fourth CI-only surprise today (identity, actionlint pin, Windows clippy, rustdoc).

Fix the root cause, not only the link:
1. Fix the doc link.
2. Add cargo dev ci, one command that runs locally exactly the checks ci.yml runs on Linux, in the same order and with the same flags and environment (fmt --check, clippy -D warnings for the host and the x86_64-pc-windows-gnu target from ~RBF6057, nextest --profile ci, cargo doc with RUSTDOCFLAGS=-D warnings, cargo dev gen all --check, frob check, actionlint and zizmor at the pinned versions), stopping at the first failure with the step name, plus --keep-going.
3. One source of truth: ci.yml invokes cargo dev ci steps (or both read one step list), and a test fails if a check in ci.yml is not in cargo dev ci or the flags differ. The Windows CI job stays the real-platform check.
4. Update the implementer guidance where it lists gates (CONTRIBUTING.md or docs/guides, whichever names the gate commands) to say: run cargo dev ci before reporting.
