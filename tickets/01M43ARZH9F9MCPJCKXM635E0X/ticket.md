+++
id = "01M43ARZH9F9MCPJCKXM635E0X"
title = "crunk-tokens: export targets css, json, tailwind and `crunk tokens`"
type = "story"
category = "done"
outcome = "done"
priority = "medium"
points = 5
parent = "01M43ANVJYA7GHN0Y8GX0SN72M"
reporter = "lognd"
created = "2026-10-04T11:28:50Z"
updated = "2026-10-09T06:00:29Z"
idempotency_key = "crunk-plan-tokx"
labels = ["area:crunk", "creates:crates/crunk/src/tokens.rs", "creates:crates/crunk/tests/tokens*.rs"]
scope = ["crates/crunk-tokens/**", "crates/crunk/src/tokens.rs", "crates/crunk/tests/tokens*.rs", "crates/crunk/Cargo.toml", "crates/crunk/src/lib.rs", "Cargo.lock", "crates/gob-dev/profile.toml"]

[[links]]
kind = "blocked-by"
target = "01M43ARZAJ8NJ3F38157ERAKR5"

[[acceptance]]
text = "Given the corpus specs, when each target renders, then output is byte-identical to the Python goldens"
bound = true

[[acceptance]]
text = "Given a hand-edited tokens.css, when `crunk tokens --check` runs, then it exits 1 and names the file"
bound = true

[[acceptance]]
text = "Given `--format json` with no --check, when run, then nothing is written to disk"
bound = true
+++

Port tokens renderers (1582 LOC): tokens.css with GENERATED banner and verbatim header, flat JSON, Tailwind theme-mapping JSON; `crunk tokens [--format X] [--check]` (bare writes; --format previews to stdout; --check exits 1 on drift); drift compares CSS byte for byte and JSON after parsing; writes go through gob-fix style atomic write. Port tests/unit/test_tokens*.py, INT-04 goldens, e2e 05 and 13.
