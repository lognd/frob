+++
id = "01M3WYJ80G1JFEF6BDDDXP0E6B"
title = "gob-dev: cargo dev gen for rules, directives, config reference pages and schemas; GEN001 check mode"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 5
parent = "01M3WYJ802ZVWE6E3050EVRCSV"
reporter = "agent"
created = "2026-10-02T00:00:00Z"
updated = "2026-10-02T00:00:03Z"
aliases = ["T-0016"]
labels = ["milestone:2.0.0", "component:gob-dev"]
scope = ["crates/gob-dev/**", "docs/reference/**", "docs/schemas/**", ".github/**"]

[[links]]
kind = "blocked-by"
target = "01M3WYJ8062KNPCJ73WBX9JBTT"

[[links]]
kind = "blocked-by"
target = "01M3WYJ808PBE214Y9RH093BQT"

[[links]]
kind = "blocked-by"
target = "01M3WYJ80EPBK0GGD2118X6CDT"

[[links]]
kind = "blocked-by"
target = "01M3WYJ80FD296GC3SAK8MNYRD"

[[acceptance]]
text = "Given a new rule derived in any crate, when cargo dev gen rules runs, then docs/reference/rules/<ID>.md appears with the doc comment explanation"
bound = false

[[acceptance]]
text = "Given a stale generated file, when cargo dev gen all --check runs, then it exits 1 with a diff and CI fails"
bound = false
+++

Implement crates/gob-dev per documentation.md sections 2 to 3 and build-test-ci.md section 3. The cargo dev binary (never shipped) with subcommands gen rules|directives|config|schemas|all [--check], writing docs/reference/rules/<ID>.md (meta table plus explanation plus mdtest examples), docs/reference/directives.md, docs/reference/config.md (from the gob-config inventory with defaults and materialization), docs/schemas/*.json (envelope, config, ticket). --check exits 1 with a unified diff if any generated file differs (this is the GEN001 repo-local tool stage; wire it into CI). Generated files carry a header comment naming the generator. Also gen cli later; leave a stub. Use the inventory registries so adding a rule needs no edit here.
