+++
id = "01M43A5MA7GRAACT7E0M525Y1M"
title = "pytest evidence provider and Python test selection for frob test"
type = "story"
category = "in-progress"
priority = "high"
points = 3
parent = "01M43A5349M17PED730HKNM4VV"
reporter = "lognd"
created = "2026-10-04T11:18:16Z"
updated = "2026-10-04T12:16:30Z"
scope = ["crates/frob-evidence/src/provider.rs", "crates/frob-tests/**", "docs/design/tickets.md", "crates/frob-evidence/src/record.rs", "crates/frob-evidence/src/config.rs", "crates/frob-evidence/src/verbs.rs", "crates/frob-evidence/tests/pytest.rs", "docs/reference/config.md", "docs/design/architecture.md", "docs/design/build-test-ci.md", "crates/frob-evidence/src/error.rs", "crates/frob-tests/Cargo.toml", "crates/gob-testsupport/src/lib.rs", "crates/frob-evidence/Cargo.toml", "Cargo.lock", "crates/frob-tests/tests/pytest.rs", "crates/frob-evidence/tests/evidence.rs", "frob.toml", "docs/schemas/config.json"]

[[links]]
kind = "blocked-by"
target = "01M43A5DJT8XBQYEK36F0KSGKF"

[[acceptance]]
text = "Given a pytest test id, when ticket evidence add --provider pytest runs, then a measured record with per-test results is stored"
bound = false

[[acceptance]]
text = "Given a change to a Python function, when frob test runs, then the pytest tests reaching it are selected and run"
bound = false
+++

With Python tests in the graph, evidence and frob test need a runner: an evidence provider 'pytest' (run pytest with junit XML, parse per-test results like the nextest provider, escape and scrub captured text through the shared paths), and frob test selection mapping touched Python symbols to pytest node ids.
