---
id: T-0128
title: extend rust [[test.runner]] coverage to frob-core (second PyO3 crate)
state: done
kind: feature
origin: agent
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- frob.toml
- src/frob/testing/**
- docs/modules/testing.md
- tests/test_testing.py
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_testing.py::TestMultipleRunnersPerLanguage::test_routes_each_crate_to_its_own_runner
- tests/test_testing.py::TestMultipleRunnersPerLanguage::test_unowned_item_is_hard_error_not_vacuous_skip
- tests/test_testing.py::TestMultipleRunnersPerLanguage::test_all_sentinel_runs_every_same_language_runner
designated_repro_test: null
threat: null
component: null
---
T-0092 wired a cargo [[test.runner]] and collect_rust_tests for strata-core only, since one [[test.runner]] entry maps to exactly one language today and there is no root workspace Cargo.toml unifying the two crates. collect_rust_tests already discovers and collects BOTH crates generically (93 ids across frob-core + strata-core), but frob test's selection+run path only has a runner entry for strata-core. Either allow multiple [[test.runner]] entries per language (cwd-scoped) or add a workspace Cargo.toml so one runner covers both crates.

Scope note (implementer, 2026-07-18): widened scope to include docs/modules/testing.md, tests/test_testing.py, and tickets.md (this file) -- the original scope (frob.toml, src/frob/testing/**) covers the code change but not its doc update or its test evidence, both required by the Done report / gates. Design chosen: multiple `[[test.runner]]` entries per language, cwd-scoped, rather than a root workspace Cargo.toml -- collect_rust_tests already emits root-relative symrefs per crate, so routing a selected item to the runner whose cwd prefixes its path is a pure function of data already in hand; a workspace Cargo.toml would couple frob-core's and strata-core's build/CI/maturin tooling for no selection-side benefit. Re-run frob ticket sweep T-0128 after this scope edit before closing.
## Done report

Multiple [[test.runner]] entries per language, cwd-scoped: a second
rust entry covers frob-core; run_selected groups specs by language and
routes each selected item to the runner whose cwd prefix owns it
(trailing-slash-anchored, so sibling-name prefixes cannot collide).
Zero or multiple owners is a loud TestingError.UnroutedItem, never a
skip; ALL_SENTINEL runs every same-language runner and any failure
fails the whole report. The workspace-Cargo.toml alternative was
rejected to keep the crates' build tooling independent. Reviewer
APPROVED; verified at merge: 37 testing tests green, main exit 0.