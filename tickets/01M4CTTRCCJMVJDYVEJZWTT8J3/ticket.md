+++
id = "01M4CTTRCCJMVJDYVEJZWTT8J3"
title = "frob test runs each test runner from the project root that owns the selected tests (Rust crate in a subdirectory) and prints the cause on failure"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 3
parent = "01M4CTTPJ00PTDE0A1SE4MJFCF"
reporter = "lognd"
created = "2026-10-08T04:02:35Z"
updated = "2026-10-10T16:20:26Z"
scope = ["changelog.d/**", "crates/frob-tests/**", "crates/frob-evidence/**", "crates/frob/**"]

[[acceptance]]
text = "Given a repository with a Rust crate under rs/ and no root Cargo.toml, when frob test selects its tests, then nextest runs in rs/ and passes"
bound = true

[[acceptance]]
text = "Given a runner that exits non-zero before running tests, when frob test runs, then the output shows the runner's stderr tail and exit code"
bound = true
+++

notes/review/adoption-trial-2026-10-07.md HIGH 2: selection is right but nextest runs at the repository root: could not find Cargo.toml, exit 102, cause visible only in the evidence transcript. Resolve the owning Cargo workspace (or pyproject root) per selected test and run there; on a runner failure print the runner's stderr tail and the exit code.
