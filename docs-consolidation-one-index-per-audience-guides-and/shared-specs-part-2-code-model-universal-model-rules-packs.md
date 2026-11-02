+++
id = "01M4H0X8T4VV6P5SNWB73AS4P7"
title = "shared specs part 2: code-model, universal-model, rules, packs-and-plugins, security, documentation, build-test-ci, grl-spec and sibling-contract under docs/design/shared/"
type = "docs"
category = "in-progress"
priority = "medium"
points = 8
parent = "01M4H0WWHV461NXWVCCNKAH3YP"
reporter = "lognd"
created = "2026-10-09T19:05:46Z"
updated = "2026-11-02T08:01:01Z"
idempotency_key = "docs-consolidation-2026-10-09-p4b"
labels = ["creates:docs/design/shared/**"]
scope = ["docs/design/*.md", "docs/README.md", "crates/gob-mdtest/FORMAT.md", "docs/MOVED.toml", "changelog.d/**", "docs/design/shared/**", "changelog.d/01M6DB73AS4P7SHAREDSPEC2XY.changed.md", "crates/crunk-check/**", "crates/crunk-ingest/**", "crates/crunk-tailwind/**", "crates/frob-check/**", "crates/frob-land/**", "crates/frob-ledger/**", "crates/frob-obligations/**", "crates/frob-pm/**", "crates/frob/**", "crates/gob-caps/**", "crates/gob-check/**", "crates/gob-dev/changes.toml", "crates/gob-dev/src/bench_ic.rs", "crates/gob-dev/src/ci.rs", "crates/gob-dev/src/ecosystem.rs", "crates/gob-dev/src/products.rs", "crates/gob-dev/src/profile.rs", "crates/gob-dev/src/render/inline.rs", "crates/gob-exec/**", "crates/gob-frameworks/**", "crates/gob-ir/**", "crates/gob-macros/**", "crates/gob-mdtest/**", "crates/gob-packs/**", "crates/gob-pattern/**", "crates/gob-plan/**", "crates/gob-rules/**", "crates/gob-symbols/**", "crates/grimble-bind/src/relation.rs", "crates/grimble-capabilities/**", "crates/grimble-check/**", "crates/grimble-lints/**", "crates/grimble-model/tests/stability.rs", "crates/grimble/**", "docs/decisions/decisions.toml", "docs/guides/coverage.md", "docs/reference/tool-stages.md", "docs/design/frob/*.md", "docs/design/grimble/*.md", "changelog.d/01M4H0X8T4VV6P5SNWB73AS4P7.changed.md", "docs/decisions/README.md", "docs/reference/config/frob.md", "docs/schemas/config.json", "docs/schemas/sibling.json", ".github/workflows/*.yml", "crates/crunk-rules/src/lib.rs", "crates/gob-dev/src/**", "crates/gob-dev/tests/fuzz_nightly.rs", "crates/gob-directives/tests/mdtest/parse001.md", "crates/grimble-bind/src/caps.rs", "crates/grimble-model/src/args.rs", "crates/grimble-model/src/model.rs", "docs/grimble/packs/*.md", "docs/reference/**", "packs/**"]

[[links]]
kind = "blocked-by"
target = "01M4H0X5DZZ0DAHBJKD9TGBAW8"

[[links]]
kind = "blocked-by"
target = "01M4H0X78V0F2GV0GW6AZ4P6PQ"

[[acceptance]]
text = "Given code-model 1-4 and 8-10, language-engines 2-5 and dotnet-unity, when phase 4b lands, then docs/design/shared/code-model.md has one adapter chapter for every language including C#"
bound = true

[[acceptance]]
text = "Given rules, rule-authoring, testing, exceptions, tool-binding 2-5 and build-test-ci 6, when phase 4b lands, then docs/design/shared/rules.md states exceptions once and has one 'testing a rule' chapter"
bound = true

[[acceptance]]
text = "Given plugins, packs, security, documentation, doc-consistency and navigation 3-5, when phase 4b lands, then packs-and-plugins.md, security.md and documentation.md under docs/design/shared/ each state their subject once"
bound = true

[[acceptance]]
text = "Given docs/design, when phase 4b lands, then no design file remains at the docs/design top level except README.md, and frob check reports zero DOC002 and zero DRIFT002 findings, and `cargo dev gen --check` is clean"
bound = false
+++

Phase 4b of notes/review/docs-consolidation-2026-10-09.md (sections 3.1, 3.2). Lifts the hold on new frob:doc/frob:describes into docs/design (owner decision 5); ~Y9W8WYP follows. Prose citations ('x.md section N') in crates/ that this phase moves are rewritten by `frob doc remap`; before running it, add the exact files from `frob doc remap --dry-run` to this ticket's scope with `frob ticket update`. Ledger text and notes are never rewritten. No new frob:doc or frob:describes into docs/design until phase 4b lands (owner decision 5).
