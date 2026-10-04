+++
id = "01M43ARWCVRCE25KDZC8CRC1ZH"
title = "Register crunk as a product: release list, PyPI products, dist opt-in, workflows"
type = "story"
category = "todo"
priority = "medium"
points = 5
parent = "01M43ANVJYA7GHN0Y8GX0SN72M"
reporter = "lognd"
created = "2026-10-04T11:28:47Z"
updated = "2026-10-04T12:35:39Z"
idempotency_key = "crunk-plan-reg"
labels = ["area:crunk"]
scope = ["frob.toml", "packaging/pypi/products.toml", "packaging/pypi/**", "packaging/smoke/**", "crates/crunk/Cargo.toml", "dist-workspace.toml", ".github/workflows/release.yml", ".github/workflows/build-smoke.yml", "crates/frob-release/tests/products.rs", "crates/frob-release/tests/release_workflow.rs"]

[[links]]
kind = "blocked-by"
target = "01M43ARVS24254G85TMFYH8FGQ"

[[acceptance]]
text = "Given the workspace, when the products test runs, then the binary set, dist set, archive names and PyPI product list each contain exactly frob, grimble and crunk"
bound = false

[[acceptance]]
text = "Given a dev build of the release workflow, when it runs, then it produces one crunk archive per target with a .sha256 and nothing else new"
bound = false

[[acceptance]]
text = "Given the wheel set, when smoke runs from the directory only, then crunk installs alone and `frob` pulls crunk at the same version"
bound = false
+++

products.md 6 and releases.md 6 and 6a: add crunk to [release] products and preview in frob.toml (preview until parity); one more [[product]] in packaging/pypi/products.toml (name crunk, package crunk, depends []); `frob` wheel depends = ["grimble", "crunk"] only when the preview release is cut (guard it behind the release ticket, keep a test pinning both); [package.metadata.dist] dist = true in crates/crunk; archive crunk-<target> and the count steps in release.yml, ci.yml and build-smoke.yml (three-product loops, `frob-cli-*|grimble-*|crunk-*` allow pattern); crunk-v tag pattern; archive-smoke.sh crunk runs `crunk --version` and doctor; wheel smoke for crunk alone. crates.io reservation stays with `cargo dev publish --reserve` (name already reserved, products.md 5). Never touch the PyPI side of lognd/crunk (owner steps are in their own tickets).
