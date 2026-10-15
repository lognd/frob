+++
id = "01M41S1KX3ZVF51H8KPJ3YXZF9"
title = "Clippy confinement: path-to-text conversion only in gob-path, with a shrinking allow list"
type = "story"
category = "done"
outcome = "done"
priority = "high"
points = 3
parent = "01M41S1JXXN380WPE29ATR5EP7"
reporter = "lognd"
created = "2026-10-03T20:59:44Z"
updated = "2026-10-15T06:09:21Z"
scope = ["clippy.toml", "Cargo.toml", "crates/gob-path/**", "docs/design/paths.md", "crates/crunk-ingest/src/lib.rs", "crates/crunk-ingest/tests/ingest.rs", "crates/crunk-ingest/tests/jsx_parity.rs", "crates/crunk-ingest/tests/parity.rs", "crates/crunk-rules/src/lib.rs", "crates/crunk-rules/tests/rules.rs", "crates/crunk-spec/src/lib.rs", "crates/crunk-spec/tests/parity.rs", "crates/crunk-tailwind/src/lib.rs", "crates/crunk-tokens/src/lib.rs", "crates/crunk-tokens/tests/export.rs", "crates/crunk-tokens/tests/model.rs", "crates/crunk/src/lib.rs", "crates/crunk/tests/boundary.rs", "crates/frob-ack/tests/ack.rs", "crates/frob-ack/tests/affect001_corpus.rs", "crates/frob-evidence/src/lib.rs", "crates/frob-evidence/tests/dotnet.rs", "crates/frob-evidence/tests/evidence.rs", "crates/frob-evidence/tests/unity.rs", "crates/frob-land/src/lib.rs", "crates/frob-land/tests/land.rs", "crates/frob-lease/src/lib.rs", "crates/frob-ledger/src/lib.rs", "crates/frob-ledger/tests/ledger.rs", "crates/frob-ledger/tests/no_private_commit.rs", "crates/frob-obligations/src/lib.rs", "crates/frob-obligations/tests/corpus.rs", "crates/frob-pm/src/lib.rs", "crates/frob-pm/tests/corpus.rs", "crates/frob-release/src/lib.rs", "crates/frob-release/tests/it/main.rs", "crates/frob-tests/src/lib.rs", "crates/frob-tests/tests/dotnet.rs", "crates/frob-tests/tests/lease_worktree.rs", "crates/frob-tests/tests/selection.rs", "crates/frob-tests/tests/typescript.rs", "crates/frob-worktree/src/lib.rs", "crates/frob-worktree/tests/gc.rs", "crates/frob-worktree/tests/work.rs", "crates/frob/src/lib.rs", "crates/frob/tests/it/main.rs", "crates/frob/tests/siblings/main.rs", "crates/gob-cache/src/lib.rs", "crates/gob-cache/tests/shared.rs", "crates/gob-cli/src/lib.rs", "crates/gob-cli/tests/flags_declared_once.rs", "crates/gob-cli/tests/root.rs", "crates/gob-config/src/lib.rs", "crates/gob-config/tests/cfg001_corpus.rs", "crates/gob-dev/src/lib.rs", "crates/gob-dev/src/main.rs", "crates/gob-dev/tests/ci_plan.rs", "crates/gob-dev/tests/generate.rs", "crates/gob-directives/tests/corpus.rs", "crates/gob-exec/src/lib.rs", "crates/gob-frameworks/tests/routes.rs", "crates/gob-fs/src/lib.rs", "crates/gob-fs/tests/gitdir.rs", "crates/gob-fs/tests/inventory.rs", "crates/gob-git/src/lib.rs", "crates/gob-git/tests/ledger.rs", "crates/gob-git/tests/symlinks.rs", "crates/gob-git/tests/walk_paths.rs", "crates/gob-languages/src/lib.rs", "crates/gob-lock/src/lib.rs", "crates/gob-lock/tests/lock.rs", "crates/gob-macros/src/lib.rs", "crates/gob-mdtest/src/lib.rs", "crates/gob-mdtest/tests/selftest.rs", "crates/gob-plan/src/lib.rs", "crates/gob-plan/tests/check_names.rs", "crates/gob-plan/tests/grl_errors/main.rs", "crates/gob-plan/tests/lower.rs", "crates/gob-plan/tests/print_stability.rs", "crates/gob-product/src/lib.rs", "crates/gob-symbols/src/lib.rs", "crates/gob-symbols/tests/it/main.rs", "crates/gob-time/tests/time.rs", "crates/gob-trust/src/lib.rs", "crates/gob-trust/tests/state.rs", "crates/gob-trust/tests/trust.rs", "crates/gob-walk/src/lib.rs", "crates/grimble-bind/tests/corpus.rs", "crates/grimble-model/tests/corpus.rs", "crates/grimble/src/lib.rs", "crates/grimble/tests/boundary.rs", "crates/gob-packs/src/digest/mod.rs", "crates/gob-packs/src/manifest.rs"]

[[links]]
kind = "blocked-by"
target = "01M41S1KC8PQFTVDETMARHP82G"

[[acceptance]]
text = "Given a new path-to-text call outside gob-path in a crate not on the allow list, when cargo clippy -D warnings runs, then it fails naming the method and the gob-path replacement"
bound = true

[[acceptance]]
text = "Given a crate on the allow list with no remaining conversions, when the list test runs, then it fails asking to remove the entry"
bound = true
+++

paths.md section 3. Workspace clippy.toml disallowed-methods for Path::to_str, to_string_lossy, display, OsStr::to_str, to_string_lossy and their owned forms; disallowed-types for PathBuf in persisted-type modules. gob-path is allowed with #[expect(..., reason)] per site. Every other crate that still converts gets a crate-level #[expect] listed in one place (a checked list in paths.md or a test) so the list can only shrink; a test fails if a crate not on the list converts or a listed crate no longer needs its entry.
