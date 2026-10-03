+++
id = "01M4069XMEQQ5P082TMA389FFK"
title = "PyPI wheel packaging: maturin bin-bundle wheel for frob"
type = "task"
category = "todo"
priority = "medium"
points = 5
parent = "01M4065Y4N6DQG30TRSP2QNP8T"
reporter = "lognd"
created = "2026-10-03T06:12:59Z"
updated = "2026-10-03T06:12:59Z"
idempotency_key = "m2-rel-wheel-bundle"
labels = ["milestone:2", "area:release", "release:0.532.0"]
scope = ["packaging/pypi/**", "Cargo.toml"]

[[links]]
kind = "blocked-by"
target = "01M4069WNGJ8YR9DTTM9K9K8V5"

[[acceptance]]
text = "Given the wheel built locally, when installed into a clean venv, then frob --version prints 0.532.0"
bound = false

[[acceptance]]
text = "Given the wheel metadata, when inspected, then the name is frob and the linux tag is manylinux_2_28"
bound = false
+++

pyproject for distribution `frob` (PyPI name kept, version 0.532.0, replacing v1's 0.531.0) built with maturin bindings=bin so the wheel installs the frob binary (and grimble when the workspace builds it; products.md 6 says the wheel bundles all three, see open question). Wheel tags manylinux_2_28 on linux, macosx arm64 and x86_64, win_amd64; sdist builds from source and is allowed. A local `uv tool install` of the built wheel runs frob --version.
