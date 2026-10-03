+++
id = "01M41PEAN0RE8DBEKQ1RBF6057"
title = "CI run 2 fails: ci.yml pins a nonexistent actionlint-py version, and Windows-only gob-trust code fails clippy"
type = "bug"
category = "todo"
priority = "critical"
points = 2
reporter = "lognd"
created = "2026-10-03T20:14:15Z"
updated = "2026-10-03T20:14:15Z"
scope = [".github/workflows/ci.yml", "crates/gob-trust/src/key.rs", "crates/frob-release/tests/**"]

[[acceptance]]
text = "Given ci.yml and frob.toml, when the pin test runs, then every tool version in ci.yml equals the one frob.toml uses"
bound = false

[[acceptance]]
text = "Given the workspace, when clippy runs for the Windows target with -D warnings, then it is clean, or the report states why it cannot run on this host"
bound = false
+++

Run https://github.com/lognd/frob/actions/runs/37150145973 (2026-10-03): ubuntu tests passed, then two failures.

(1) The ci.yml step 'Fetch zizmor and actionlint (versions match frob.toml)' ran uvx --from actionlint-py==1.7.12, which does not exist on PyPI; frob.toml binds actionlint-py==1.7.12.25. Fix the pin and add a test that every tool version pinned in ci.yml equals the one frob.toml's tool stage uses (parse both; one source of truth or a checked pair).

(2) windows-latest clippy -D warnings: crates/gob-trust/src/key.rs:169 fn check_mode(_path, _meta) -> Result<(), TrustError> on non-unix trips clippy::unnecessary_wraps. Keep the signature identical to the unix variant (callers use ?) and allow the lint on that cfg with a reason, or restructure so both cfgs share one signature without the lint.

Also make Windows-only code checkable on this aarch64 host: if rustup target add x86_64-pc-windows-msvc plus cargo clippy --workspace --all-targets --target x86_64-pc-windows-msvc -- -D warnings works check-only without a linker, run it and fix what it finds; report if it cannot run (build scripts or proc macros needing a target C toolchain).
