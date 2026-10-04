+++
id = "01M421FB3B2P9EMNKPDTPHS84G"
title = "One wheel set per product: grimble standalone on PyPI, frob depends on it at the same version (D87)"
type = "story"
category = "in-progress"
priority = "high"
points = 5
parent = "01M4065Y4N6DQG30TRSP2QNP8T"
reporter = "lognd"
created = "2026-10-03T23:27:02Z"
updated = "2026-10-04T02:57:22Z"
scope = ["packaging/**", ".github/workflows/build-smoke.yml", ".github/workflows/release.yml", "crates/frob-release/**", "docs/guides/release.md", "docs/design/releases.md", "changelog.d/01M421FB3B2P9EMNKPDTPHS84G.changed.md"]

[[links]]
kind = "blocked-by"
target = "01M421F7Q66MW38R7J1JS1VMBC"

[[acceptance]]
text = "Given the built wheels, when grimble is installed alone, then only grimble is installed and runs"
bound = true

[[acceptance]]
text = "Given the built wheels and no network index, when frob is installed into a clean venv, then grimble at the same version is installed with it and both run"
bound = true

[[acceptance]]
text = "Given uv tool install frob from the built wheels, when frob check runs, then it finds grimble without grimble on PATH"
bound = true

[[acceptance]]
text = "Given the release workflow, when its tests run, then the pypi job uploads both products and each wheel set's count is checked"
bound = true
+++

Owner decision D87 (products.md 6, releases.md 6): one binary per package, composed by dependencies. Today packaging/pypi builds one frob wheel that copies grimble into data/scripts (build-wheel.sh), so frob and grimble cannot be installed separately and side-by-side installs would put two grimble executables on PATH.

Build:
1. Two PyPI products from this release: frob and grimble (crunk joins when the Rust crunk exists; design the layout so adding it is one entry, a product list, not copied files). Each wheel carries only its own binary. The frob wheel declares grimble==<same version> as a dependency (the lockstep version from release bump; check it updates both pyprojects and the pin).
2. One packaging definition per product generated or parameterized from one source (no copy-pasted pyproject and build script per product); release bump and REL002 cover every product's version.
3. build-smoke.yml builds wheels per product per target (five targets each), still pinned and hash-checked (maturin requirements, rustup-init), and the smoke job installs: (a) grimble alone, runs grimble --version; (b) frob alone into a clean venv, which pulls grimble from the locally built wheels (pip --find-links / uv --find-links, no network index), then runs frob and grimble; (c) uv tool install frob from the local wheels and checks frob finds grimble without grimble on PATH (needs ~sibling discovery ticket).
4. release.yml's pypi job uploads both products' smoked wheels (each PyPI project already trusts this repository's release.yml, environment pypi); keep skip-existing and the guard on the expected wheel count, now per product.
5. Update packaging/pypi/README.md and BUILDING.md, the runbook (docs/guides/release.md) and the workflow tests in crates/frob-release/tests (wheel names, dependency pin, upload of both products).
