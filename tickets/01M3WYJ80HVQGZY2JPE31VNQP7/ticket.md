+++
id = "01M3WYJ80HVQGZY2JPE31VNQP7"
title = "gob-cli + frob binary: clap root, Command derive, global flags, frob doctor, frob init, frob config"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 5
parent = "01M3WYJ802ZVWE6E3050EVRCSV"
reporter = "agent"
created = "2026-10-02T00:00:00Z"
updated = "2026-10-02T00:00:03Z"
aliases = ["T-0017"]
labels = ["milestone:2.0.0", "component:frob-bin"]
scope = ["crates/gob-cli/**", "crates/gob-macros/**", "crates/frob/**"]

[[links]]
kind = "blocked-by"
target = "01M3WYJ8062KNPCJ73WBX9JBTT"

[[links]]
kind = "blocked-by"
target = "01M3WYJ808PBE214Y9RH093BQT"

[[acceptance]]
text = "Given stdout is a pipe, when frob doctor runs, then output is the JSON envelope and exit is 0"
bound = true

[[acceptance]]
text = "Given a repo without frob.toml, when frob init runs twice, then the second run reports already: true and changes nothing"
bound = true
+++

Implement crates/gob-cli, the Command derive in gob-macros, and crates/frob (binary name frob, package name frob-cli) per cli.md sections 1 to 4 (post-D27 table) and architecture.md section 4. gob-cli: shared clap root builder taking a product name, global flags (--json, --quiet, -v, --color, --cwd, --schema, --dry-run where supported), envelope plumbing (handlers return Result<T, Refusal|Negative|Internal>, the root renders through gob-diagnostics and exits with the table), gob-log init from flags, and #[derive(Command)] that registers a verb with its summary, idempotency flag and exit-code rows into an inventory for cli reference generation. frob binary: verbs doctor (toolchain, git discovery, cache health, config materialization status, ledger ref reachability), init (write materialized frob.toml, .frob/ in .gitignore, install the ledger merge driver config per D33), config show --effective and config sync. Integration tests with assert_cmd and insta snapshots of --json output.
