+++
id = "01M43ARX764095Q4VWABWXXV5H"
title = "crunk-spec: crunk.toml schema through gob-config, DesignSpec, naming, JSON Schema"
type = "story"
category = "in-progress"
priority = "medium"
points = 5
parent = "01M43ANVJYA7GHN0Y8GX0SN72M"
reporter = "lognd"
created = "2026-10-04T11:28:47Z"
updated = "2026-10-04T13:47:07Z"
idempotency_key = "crunk-plan-spec"
labels = ["area:crunk"]
scope = ["crates/crunk-spec/**", "docs/schemas/crunk.json", "docs/crunk/config.md", "Cargo.lock", "crates/gob-dev/Cargo.toml", "crates/gob-dev/src/lib.rs", "crates/gob-dev/src/render/mod.rs", "crates/gob-dev/src/render/crunk.rs", "crates/gob-dev/tests/generate.rs"]

[[links]]
kind = "blocked-by"
target = "01M43ARVJKKN4EXCQF1NRTJ3KW"

[[links]]
kind = "blocked-by"
target = "01M43ARVS24254G85TMFYH8FGQ"

[[acceptance]]
text = "Given a crunk.toml with an unknown key, when loaded, then the error names the key, its line and a did-you-mean, and the exit is 2"
bound = true

[[acceptance]]
text = "Given each valid fixture config of the corpus, when loaded, then the DesignSpec equals the Python spec dump"
bound = true

[[acceptance]]
text = "Given the crate, when `cargo dev gen --check` runs, then docs/schemas/crunk.json and docs/crunk/config.md are current"
bound = false
+++

Port crunk.spec (load.py, models.py, naming.py: 1836 LOC; docs/design/02-specification.md CR-01) as ConfigTable types in gob-config (deny unknown fields, located errors, schema and reference page emitted by cargo dev gen with GEN001): [project], [palette] and roles, [scales], [breakpoints] (Tailwind v3 defaults when a TW config exists), [typography], [layers], [org], [tokens] and prefixes, [jsx], [tailwind], [lint] (rule levels, fix_tolerance, color_tolerance), [[platform]] and [[screen]] (parsed here, used by the gallery). Keep the path-base law (project *_file keys resolve against css_root, others against the project root) as documented tests. Token naming scheme and presets move here. v1 has no schema for crunk.toml; this adds docs/schemas/crunk.json. Uses crunk-values for color validation. Port tests/unit/test_spec.py and INT-01.
