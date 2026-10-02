+++
id = "01M3WYJ806CASHE93J7KMGB72D"
title = "gob-config: ConfigTable derive, layered load, materialized knobs, CFG001"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 5
parent = "01M3WYJ802PGVRR55XCM9C3KV9"
reporter = "agent"
created = "2026-10-02T00:00:00Z"
updated = "2026-10-02T00:00:03Z"
aliases = ["T-0006"]
labels = ["milestone:2.0.0", "component:gob-config"]
scope = ["crates/gob-config/**", "crates/gob-macros/**"]

[[links]]
kind = "blocked-by"
target = "01M3WYJ80546ATY80P3VS9T9XE"

[[acceptance]]
text = "Given a frob.toml missing a materialized knob, when check runs, then CFG001 names the key, the default, and the fix command"
bound = false

[[acceptance]]
text = "Given a frob.toml with comments, when materialize adds knobs, then existing comments and order are preserved (snapshot)"
bound = false

[[acceptance]]
text = "Given an unknown key, when loaded, then the error names the key and the nearest valid key"
bound = false
+++

Implement crates/gob-config and the ConfigTable derive in gob-macros per architecture.md section 6 (config), goals.md principle no invisible variables, D22, D34. Features: #[derive(ConfigTable)] with #[config(table = "tickets", materialize)] and per-field #[config(default = ..., doc from doc comment, enforcement = true)]; a Config loader that reads <product>.toml from the repo root (product name is a parameter, frob.toml for frob), applies layering (defaults < file < explicit CLI overrides passed as a map) and reports unknown keys as errors with a did-you-mean; a materialize function that writes every enforcement knob that is absent from the file with its default and a doc comment, used by frob init, and a check function that returns one CFG001 finding per missing materialized knob (rule declared here with #[derive(Rule)]); a JSON schema export of the whole config (schemars) for frob schema; an inventory of tables so gob-dev can generate the config reference page. Use toml_edit to preserve comments and ordering when materializing. Tests with insta snapshots of materialized output.
