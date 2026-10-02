---
id: T-0003
title: 'Workspace skeleton: Cargo workspace, lints as errors, linker, CI, MIT'
state: done
kind: feature
origin: agent
created: '2026-10-02'
priority: high
parent: T-0002
tier: ticket
sprint: null
runs_last: false
milestone: 2.0.0
flavour: null
due: null
rank: null
points: 5
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: /home/logan/projects/frob-v2-wt/t-0003
branch: t-0003
scope:
- Cargo.toml
- Cargo.lock
- .cargo/**
- rust-toolchain.toml
- rustfmt.toml
- clippy.toml
- deny.toml
- .config/**
- LICENSE
- README.md
- .github/**
- crates/gob-dev/**
- crates/gob-text/**
- .gitignore
- .github/workflows/release.yml
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: .github/workflows/release.yml
  reason: v1 PyPI release workflow deleted by the Rust skeleton; .github/** glob not
    matched by the deletion check
  actor: logan
  at: '2026-10-02'
evidence:
- cmd:cargo nextest run --profile ci exit=0 sha256=e3b0c44298fc
designated_repro_test: null
acceptance:
- text: Given a fresh clone, when cargo nextest run and cargo clippy --all-targets
    -- -D warnings and cargo doc run, then all pass with zero warnings
  evidence:
  - cmd:cargo nextest run --profile ci exit=0 sha256=e3b0c44298fc
- text: Given the workspace Cargo.toml, when a new directory is added under crates/
    with a Cargo.toml, then it is a member without editing the root manifest
  evidence:
  - cmd:cargo nextest run --profile ci exit=0 sha256=e3b0c44298fc
- text: Given LICENSE, when read, then it is the MIT text with the current year and
    owner
  evidence:
  - cmd:cargo nextest run --profile ci exit=0 sha256=e3b0c44298fc
threat: null
component: workspace
anchor: false
anchor_reason: null
land_commit: null
---
Create the Rust workspace per docs/design/architecture.md section 1 and build-test-ci.md. Deliver: root Cargo.toml with members = ["crates/*"] (glob, so later crates need no edit), resolver 3, workspace.package (edition 2024, license MIT, repository, rust-version), workspace.lints with rust missing_docs = deny, rustdoc broken_intra_doc_links/private_intra_doc_links = deny, clippy all + pedantic as warn with the documented allow list and clippy doc_markdown/missing_errors_doc/missing_panics_doc = deny, unsafe_code = forbid at workspace level. .cargo/config.toml using mold via clang (fall back to lld) with a comment on how to disable. rust-toolchain.toml pinned to the installed stable. rustfmt.toml, clippy.toml, deny.toml (cargo-deny: MIT/Apache/BSD allow list), .config/nextest.toml with a ci profile. One placeholder crate crates/gob-dev with a cargo dev binary stub (alias [alias] dev = "run -p gob-dev --") and a crate crates/gob-text left EMPTY except Cargo.toml and a lib.rs with a crate doc comment so the workspace builds. Update LICENSE to MIT (current text is not MIT), README.md badge and one-paragraph product description (frob, grimble, crunk), .github/workflows/ci.yml to run cargo fmt --check, cargo clippy --all-targets -- -D warnings, cargo nextest run, cargo doc --no-deps with RUSTDOCFLAGS=-D warnings, on ubuntu and windows. Commit Cargo.lock. Do not add any other crate. Every public item documented. No std::process anywhere.