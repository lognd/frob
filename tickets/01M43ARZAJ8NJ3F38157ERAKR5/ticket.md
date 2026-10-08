+++
id = "01M43ARZAJ8NJ3F38157ERAKR5"
title = "crunk-tokens: the token model and naming"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
parent = "01M43ANVJYA7GHN0Y8GX0SN72M"
reporter = "lognd"
created = "2026-10-04T11:28:50Z"
updated = "2026-10-08T08:04:24Z"
idempotency_key = "crunk-plan-tokm"
labels = ["area:crunk", "creates:crates/crunk-tokens/src/lib.rs", "creates:crates/crunk-tokens/tests/**", "creates:crates/crunk-tokens/README.md"]
scope = ["crates/crunk-tokens/src/model.rs", "crates/crunk-tokens/src/naming.rs", "crates/crunk-tokens/Cargo.toml", "Cargo.lock", "crates/crunk-tokens/src/lib.rs", "crates/crunk-tokens/tests/**", "crates/crunk-tokens/README.md"]

[[links]]
kind = "blocked-by"
target = "01M43ARVZPN52N6NMB7VRKZYGS"

[[links]]
kind = "blocked-by"
target = "01M43ARX764095Q4VWABWXXV5H"

[[acceptance]]
text = "Given the corpus specs, when the model is built, then names and values equal the Python token list"
bound = true

[[acceptance]]
text = "Given alpha_channels is on, when built, then each color has an -rgb companion"
bound = true

[[acceptance]]
text = "Given two palette names that collide after prefixing, when built, then a typed error names both"
bound = true
+++

The token set derived from DesignSpec: names from the spec naming scheme and [tokens.prefixes], -rgb alpha companions, namespaced keys, Tailwind theme mapping inputs; one model all exporters, `explain` and `query` read. Boundaries 2.4 (crunk_tokens).
