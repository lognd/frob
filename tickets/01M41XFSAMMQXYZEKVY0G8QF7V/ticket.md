+++
id = "01M41XFSAMMQXYZEKVY0G8QF7V"
title = "CI clippy-windows fails: the ubuntu runner has no x86_64-w64-mingw32-gcc for libsqlite3-sys"
type = "bug"
category = "in-progress"
priority = "critical"
points = 1
reporter = "lognd"
created = "2026-10-03T22:17:23Z"
updated = "2026-10-03T22:17:35Z"
scope = [".github/workflows/ci.yml", "crates/gob-dev/src/ci.rs", "crates/gob-dev/tests/ci_parity.rs", "CONTRIBUTING.md"]

[[acceptance]]
text = "Given a host without x86_64-w64-mingw32-gcc, when cargo dev ci --step clippy-windows runs, then it fails before building and names the install command"
bound = false

[[acceptance]]
text = "Given ci.yml missing an install for a declared step prerequisite, when the parity test runs, then it fails naming the prerequisite"
bound = false
+++

CI run on 2026-10-03 22:13: cargo dev ci --step clippy-windows fails on ubuntu-latest: libsqlite3-sys build script needs the C compiler x86_64-w64-mingw32-gcc for the x86_64-pc-windows-gnu target (cc-rs ToolNotFound). The local host had MinGW installed, so cargo dev ci passed locally: the step's prerequisites were not declared. Fix structurally: (1) the clippy-windows step in crates/gob-dev/src/ci.rs declares its prerequisites (the rustup target and the MinGW C compiler) and checks them before running, failing with the exact install command (Debian/Ubuntu: sudo apt-get install -y gcc-mingw-w64-x86-64) instead of a build-script error; (2) ci.yml installs gcc-mingw-w64-x86-64 on the Linux job before the step; (3) the parity test asserts ci.yml installs every declared prerequisite of every Linux step, so a new prerequisite cannot be forgotten in CI again; (4) CONTRIBUTING.md lists the prerequisites.
