+++
id = "01M44M58PKEM2HMKZF2CANFHAW"
title = "CI pytest step uses pip, which helpers refuse (PEP 668); install pytest with uv and declare uv in goway.toml"
type = "bug"
category = "in-progress"
priority = "high"
reporter = "lognd"
created = "2026-10-04T23:32:04Z"
updated = "2026-10-04T23:41:01Z"

[[acceptance]]
text = "Given a host where pip user installs are refused but uv is present, when cargo dev ci --step pytest runs, then pytest is installed at the pinned version and is on PATH"
bound = false

[[acceptance]]
text = "Given the repo root, when goway doctor reads it, then goway.toml declares uv as a required tool"
bound = false

[[acceptance]]
text = "Given the GitHub workflow, when zizmor and actionlint run, then the uv setup step is pinned and clean"
bound = false
+++

The cargo dev ci pytest step installs pytest with `python3 -m pip install pytest==8.4.2` (`py -3 -m pip` on Windows). On the goway helpers (Ubuntu 26.04) user-level pip installs are refused (PEP 668, externally managed) and python3-pip is absent, so the step fails and stops cargo dev ci before nextest. goway-67 (owner approved) will install a pinned, checksum-verified uv/uvx user-level on each Linux helper via `goway doctor --fix`, driven by a goway.toml at the repo root. Change: (1) add goway.toml at the repo root with [toolchain] tools = ["uv"]; (2) make the pytest step install pytest with uv so a pytest executable lands on PATH for the evidence provider and frob test (e.g. `uv tool install pytest==8.4.2`, idempotent), on Linux, macOS and Windows; keep the version pin in one constant; (3) in .github/workflows/ci.yml install uv with a pinned astral-sh/setup-uv action (zizmor clean) instead of relying on pip; (4) the zizmor step already needs uvx, so document that uv is now a declared CI prerequisite in docs/design/build-test-ci.md.
