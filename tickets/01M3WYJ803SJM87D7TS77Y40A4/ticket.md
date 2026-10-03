+++
id = "01M3WYJ803SJM87D7TS77Y40A4"
title = "Workspace skeleton: Cargo workspace, lints as errors, linker, CI, MIT"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 5
parent = "01M3WYJ802ZVWE6E3050EVRCSV"
reporter = "agent"
created = "2026-10-02T00:00:00Z"
updated = "2026-10-02T00:00:03Z"
aliases = ["T-0003"]
labels = ["milestone:2.0.0", "component:workspace"]
scope = ["Cargo.toml", "Cargo.lock", ".cargo/**", "rust-toolchain.toml", "rustfmt.toml", "clippy.toml", "deny.toml", ".config/**", "LICENSE", "README.md", ".github/**", "crates/gob-dev/**", "crates/gob-text/**", ".gitignore", ".github/workflows/release.yml"]

[[acceptance]]
text = "Given a fresh clone, when cargo nextest run and cargo clippy --all-targets -- -D warnings and cargo doc run, then all pass with zero warnings"
bound = true

[[acceptance]]
text = "Given the workspace Cargo.toml, when a new directory is added under crates/ with a Cargo.toml, then it is a member without editing the root manifest"
bound = true

[[acceptance]]
text = "Given LICENSE, when read, then it is the MIT text with the current year and owner"
bound = true
+++

Create the Rust workspace per docs/design/architecture.md section 1 and build-test-ci.md. Deliver: root Cargo.toml with members = ["crates/*"] (glob, so later crates need no edit), resolver 3, workspace.package (edition 2024, license MIT, repository, rust-version), workspace.lints with rust missing_docs = deny, rustdoc broken_intra_doc_links/private_intra_doc_links = deny, clippy all + pedantic as warn with the documented allow list and clippy doc_markdown/missing_errors_doc/missing_panics_doc = deny, unsafe_code = forbid at workspace level. .cargo/config.toml using mold via clang (fall back to lld) with a comment on how to disable. rust-toolchain.toml pinned to the installed stable. rustfmt.toml, clippy.toml, deny.toml (cargo-deny: MIT/Apache/BSD allow list), .config/nextest.toml with a ci profile. One placeholder crate crates/gob-dev with a cargo dev binary stub (alias [alias] dev = "run -p gob-dev --") and a crate crates/gob-text left EMPTY except Cargo.toml and a lib.rs with a crate doc comment so the workspace builds. Update LICENSE to MIT (current text is not MIT), README.md badge and one-paragraph product description (frob, grimble, crunk), .github/workflows/ci.yml to run cargo fmt --check, cargo clippy --all-targets -- -D warnings, cargo nextest run, cargo doc --no-deps with RUSTDOCFLAGS=-D warnings, on ubuntu and windows. Commit Cargo.lock. Do not add any other crate. Every public item documented. No std::process anywhere.
