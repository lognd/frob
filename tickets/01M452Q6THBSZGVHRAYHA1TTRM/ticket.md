+++
id = "01M452Q6THBSZGVHRAYHA1TTRM"
title = "Wheel dry run 2: Linux target-dir permission, Windows uv-tool sibling discovery"
type = "bug"
category = "in-progress"
priority = "high"
parent = "01M4065Y4N6DQG30TRSP2QNP8T"
reporter = "lognd"
created = "2026-10-05T03:46:32Z"
updated = "2026-10-05T03:52:37Z"
scope = [".github/workflows/build-smoke.yml", "crates/frob-release/tests/release_workflow.rs", "crates/gob-exec/src/discover.rs", "crates/gob-exec/src/lib.rs", "crates/gob-exec/tests/discover.rs", "crates/gob-dev/src/wheel_smoke.rs", "docs/design/products.md", "packaging/pypi/BUILDING.md"]

[[acceptance]]
text = "Given the manylinux container wheel step, when cargo dev wheel runs on the Linux runners, then the gob-dev tool build and the wheel build use separate target directories and no Permission denied occurs"
bound = true

[[acceptance]]
text = "Given a frob installed by uv tool install on Windows (trampoline exe in the tool bin dir), when frob doctor runs, then grimble and crunk installed in the same tool environment are found, covered by a unit test of the Windows layout"
bound = false

[[acceptance]]
text = "Given the wheel-smoke scenario c on Windows, when it runs, then it proves sibling discovery through the trampoline layout"
bound = true
+++

Found on dry run 37259741701 after ~1T8TCTA landed. (1) Linux x86_64/aarch64 wheel jobs: cargo dev wheel fails creating target/debug with Permission denied: the manylinux container step wrote target/ as root. Fix structurally (separate CARGO_TARGET_DIR for the gob-dev tool build or one place for the step). (2) Windows wheel-smoke scenario c: after uv tool install frob, frob doctor reports grimble and crunk absent, because uv puts a trampoline exe in the tool bin dir, so beside-the-executable discovery (D87, products.md section 6) finds nothing. Product bug for every Windows uv/pipx user: discover siblings in the same Python environment (venv Scripts dir) without relying on PATH; unit test for the Windows layout; update products.md section 6 if the rule changes.
