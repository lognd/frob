+++
id = "01M43ARZ3VCNDX20C9BZZCCYHY"
title = "crunk-ingest: Tailwind config ingest and theme mapping"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
parent = "01M43ANVJYA7GHN0Y8GX0SN72M"
reporter = "lognd"
created = "2026-10-04T11:28:49Z"
updated = "2026-10-09T16:13:48Z"
idempotency_key = "crunk-plan-twcfg"
labels = ["area:crunk", "creates:crates/crunk-ingest/src/tailwind/**", "creates:crates/crunk-ingest/tests/tailwind*.rs", "creates:crates/crunk-ingest/tests/fixtures/tailwind/**", "creates:crates/crunk-ingest/tests/fixtures/dump_tailwind.py"]
scope = ["crates/crunk-ingest/src/tailwind/**", "crates/crunk-ingest/tests/tailwind*.rs", "crates/crunk-ingest/Cargo.toml", "crates/crunk-ingest/src/lib.rs", "Cargo.lock", "crates/crunk-ingest/tests/fixtures/tailwind/**", "crates/crunk-ingest/tests/fixtures/dump_tailwind.py"]

[[links]]
kind = "blocked-by"
target = "01M43ARY91XZ35DN9SCHRHS033"

[[links]]
kind = "blocked-by"
target = "01M43ARYX61ESX3S9XG1WS0DQ4"

[[acceptance]]
text = "Given the tailwind_v4 fixture, when ingested, then the theme map equals the Python output"
bound = true

[[acceptance]]
text = "Given a theme.extend spacing key that collides with a default, when ingested, then the collision is reported and can be waived (v1 T-0179)"
bound = true

[[acceptance]]
text = "Given no tailwind section, when ingested, then nothing runs and no process is spawned"
bound = true
+++

Port ingest/tailwind.py: read theme and theme.extend from the config through the runtime, namespace keys, alpha-channel companions, v3 and v4. Port tests/unit/test_ingest_tailwind.py, fixture tailwind_v4.
