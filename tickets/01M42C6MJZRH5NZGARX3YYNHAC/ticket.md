+++
id = "01M42C6MJZRH5NZGARX3YYNHAC"
title = "Windows CI still locks gob-dev.exe: the self-copy cannot work under cargo run; isolate the dev tool on Windows only"
type = "bug"
category = "todo"
priority = "critical"
points = 2
reporter = "lognd"
created = "2026-10-04T02:34:31Z"
updated = "2026-10-04T02:35:01Z"
scope = [".cargo/config.toml", "crates/gob-dev/**", ".github/workflows/ci.yml", "CONTRIBUTING.md", "docs/design/build-test-ci.md"]

[[acceptance]]
text = "Given the windows-latest job, when it runs cargo dev-isolated ci --step nextest, then the build can rebuild target/debug/gob-dev.exe because the running tool lives in target/dev-tool"
bound = false

[[acceptance]]
text = "Given ci.yml, when the parity test runs, then Linux steps use cargo dev and Windows steps use cargo dev-isolated with the same step names and order"
bound = false

[[acceptance]]
text = "Given Windows and the shared target dir, when a rebuilding task starts, then gob-dev fails fast naming cargo dev-isolated"
bound = false
+++

CI run on 2026-10-04 (after ~J9BCSXD): windows-latest nextest step fails again with "failed to remove file target\debug\gob-dev.exe: Access is denied (os error 5)". The self-copy re-exec cannot work under cargo run: the original gob-dev.exe must stay alive to wait for the copy and relay its exit code, and Windows keeps a running executable's file locked; exiting early would make cargo run return before the work finishes.

Fix: Linux and macOS keep the shared target dir (`cargo dev`, no double build). A second alias, `dev-isolated = "run -p gob-dev --target-dir target/dev-tool --"`, is used where the tool's own binary would be rebuilt while running: the windows-latest CI job calls `cargo dev-isolated ci --step NAME`, the Linux job keeps `cargo dev ci --step NAME`, and CONTRIBUTING.md tells Windows developers to use `cargo dev-isolated ci`. Remove the self-copy module and its tests (it is dead and misleading). gob-dev on Windows, when running from the shared target dir for a rebuilding task, fails fast with a remedy naming `cargo dev-isolated` instead of a cargo file-lock error. Update the parity test to accept the per-OS invocation (Linux steps through `cargo dev`, Windows through `cargo dev-isolated`, same step names and order) and the regression tests, and the build-test-ci.md paragraph. The GC (~BZXZK29) treats target/dev-tool as build output of the checkout.
