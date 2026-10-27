+++
id = "01M1WJM94DBTPN2PFTFNKB5TT1"
title = "Rename project apollo -> crunk (package, CLI, config, docs, metadata)"
type = "task"
category = "done"
outcome = "wont-fix"
priority = "medium"
reporter = "human"
created = "2026-09-07T00:00:00Z"
updated = "2026-10-27T00:53:43Z"
aliases = ["crunk:T-0141"]
labels = ["v1-cluster:C4", "component:crunk", "source:crunk", "imported:crunk"]
scope = ["src/crunk", "tests", "docs", "invariants", "pyproject.toml", "Makefile", "frob.toml", "README.md", ".github", "tickets/**", "CHANGELOG.md", "CODE_OF_CONDUCT.md", "CONTRIBUTING.md", "LICENSE", "SECURITY.md", ".github/**", "uv.lock"]

[[acceptance]]
text = "given the renamed tree, when 'uv run crunk --version' and 'uv run pytest -q' run, then both succeed and no runtime string still says apollo"
bound = false

[[acceptance]]
text = "given PyPI and npm, when the distribution name crunk is checked, then it is unclaimed on both (verified 2026-09-07), so metadata publishes cleanly and no npx-collision warning is needed"
bound = false
+++

PyPI already has an 'apollo' distribution, so the project cannot publish under its working name. Rename everything in one pass: src/apollo -> src/crunk, imports, frob directives and frob.toml parser/prog/entrypoint refs, apollo.toml -> crunk.toml config, the tool.apollo pyproject table -> tool.crunk, .apollo-cache -> .crunk-cache, APOLLO_CACHE_DIR -> CRUNK_CACHE_DIR, CLI binaries apollo/apl -> crunk/crk, docs, tickets' scope paths, invariants, workflows, Makefile PYPI_NAME, pyproject metadata. The npx/Apollo-GraphQL collision warning is dropped: crunk is free on npm as well.
