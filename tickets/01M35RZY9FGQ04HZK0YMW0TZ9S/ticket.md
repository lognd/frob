+++
id = "01M35RZY9FGQ04HZK0YMW0TZ9S"
title = "Gate registry derived views are not consumed by the check job runner; @gate registration does not run a detector"
type = "bug"
category = "triage"
priority = "medium"
reporter = "human"
created = "2026-09-23T00:00:00Z"
updated = "2026-09-23T00:00:00Z"
aliases = ["T-5423"]
labels = ["milestone:v0.535.0", "v1-cluster:C4a"]
+++

T-4661 shipped frob.gates._registry (register_gate/@gate, derive_job_names and three other derived views) so a new detector is a one-file change, but src/frob/gates/__init__.py never reads _REGISTRY.by_job: _ALL_GATES/_CANONICAL_GATE_ORDER/_GATE_STAGE_GROUPS remain hand-maintained, so a registered job is catalogued and never run. Observed 2026-09-23: four WEBSEC leaves (T-5306/T-5308/T-5309/T-5311) could not wire without editing _taint_gate.py or gates/__init__.py, both leased; the workaround is per-family module discovery in the taint gate (T-5311). Fix: make the runner derive its job list and stage groups from the registry (legacy seed first, registered jobs appended in registration order), import registered modules through a documented discovery path (frob.gates plus frob.webapp/frob.sql packages), and add a positive control: a test that registers a fake job with a planted finding and asserts that frob check --only <group> reports it. Then retire the per-family discovery hooks or keep them as thin adapters.
