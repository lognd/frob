+++
id = "01M4GKDSGA7ZSF99T7M5S319B4"
title = "Tool stages and evidence in fresh worktrees: uv run --no-sync fails with no .venv, vitest provider lacks node_modules/.bin on PATH, E-ATTEST-NOT-HUMAN fallback unclear"
type = "bug"
category = "done"
outcome = "done"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-09T15:10:08Z"
updated = "2026-10-23T14:58:00Z"
labels = ["adoption:logand-app", "creates:crates/frob-worktree/tests/python_env.rs", "creates:crates/frob-worktree/src/python_env.rs"]
scope = ["changelog.d/**", "crates/gob-check/src/tools.rs", "crates/frob-worktree/src/work.rs", "crates/frob-worktree/tests/python_env.rs", "crates/frob-worktree/src/lib.rs", "crates/frob-worktree/src/python_env.rs", "crates/frob-evidence/src/provider.rs", "crates/frob-evidence/src/error.rs", "crates/frob-evidence/tests/providers.rs", "crates/gob-check/src/config.rs", "crates/gob-check/src/pipeline.rs", "crates/gob-check/src/fmt_fix.rs", "crates/gob-check/src/tool_parse.rs", "crates/gob-check/src/type_parse.rs", "crates/frob-obligations/src/native.rs", "crates/gob-check/tests/boundary.rs", "crates/gob-check/tests/config_docs.rs", "crates/gob-check/tests/fixtures", "crates/gob-check/tests/oracle_gate.rs", "crates/gob-check/tests/oracle_live.rs", "crates/gob-check/tests/pipeline.rs", "crates/gob-check/tests/product_rules", "crates/gob-check/tests/product_rules.rs", "crates/gob-check/tests/rule_defs.rs", "crates/gob-check/tests/ui_product", "crates/gob-check/tests/ui_product.rs", "crates/frob-check/tests/corpus.rs", "crates/frob-check/tests/it", "crates/frob-check/tests/mdtest", "crates/frob-check/tests/rule_coverage.rs", "crates/frob-check/tests/rule_matrix.rs", "crates/frob-check/tests/snapshots", "docs/README.md", "docs/assets", "docs/crunk", "docs/decisions", "docs/grimble", "docs/migration", "docs/reference", "docs/schemas", "crates/gob-check/tests/tool_requires.rs", "docs/design/tool-stages.md", "docs/guides/tool-stages.md", "crates/gob-check/src/prereq.rs", "crates/gob-check/src/lib.rs", "crates/frob-check/tests/it/check.rs", "docs/reference/config.md", "docs/reference/tool-stages.md", "docs/schemas/config.json"]

[[acceptance]]
text = "Given a fresh ticket worktree or land base checkout without .venv, when a uv-run tool stage runs, then frob syncs the environment first (or the stage reports Unresolved with the remedy), never a red gate"
bound = true

[[acceptance]]
text = "Given a vitest project, when the vitest evidence provider runs, then node_modules/.bin is on PATH"
bound = true

[[acceptance]]
text = "Given an agent actor, when attestation evidence is refused, then the message names the agent-usable providers to use instead"
bound = true

[[acceptance]]
text = "Given a ticket worktree of a uv/venv Python project whose shared .venv is an editable install of the main checkout, when frob work creates the worktree, then tests in that worktree import the worktree's code (a per-worktree venv or an editable re-point), never the main checkout's (logand F-560)"
bound = true

[[acceptance]]
text = 'Given a tool stage that needs gitignored build output (e.g. a wasm-pack package or a generated setup file), when it declares requires = ["<command>"] or the repository declares [check] setup steps, then land checkouts and fresh worktrees run them before the stage, and a stage whose prerequisite failed reports Unresolved naming the prerequisite instead of passing failures as pre-existing (logand F-567)'
bound = true
+++

logand.app-v2 F-558.
