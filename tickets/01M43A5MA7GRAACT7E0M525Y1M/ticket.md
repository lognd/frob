+++
id = "01M43A5MA7GRAACT7E0M525Y1M"
title = "pytest evidence provider and Python test selection for frob test"
type = "story"
category = "todo"
priority = "high"
points = 3
parent = "01M43A5349M17PED730HKNM4VV"
reporter = "lognd"
created = "2026-10-04T11:18:16Z"
updated = "2026-10-04T11:18:16Z"
scope = ["crates/frob-evidence/src/provider.rs", "crates/frob-tests/**", "docs/design/tickets.md"]

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
