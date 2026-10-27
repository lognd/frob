+++
id = "01M1QDTV2Q4X0HTDMQ80VK9XXX"
title = "orphan-copy warning + loud path-base rule (A-030)"
type = "bug"
category = "done"
outcome = "done"
priority = "medium"
reporter = "human"
created = "2026-09-05T00:00:00Z"
updated = "2026-10-27T00:53:37Z"
aliases = ["crunk:T-0087"]
labels = ["component:crunk", "source:crunk", "imported:crunk"]
scope = ["src/crunk/tokens/io.py", "src/crunk/scaffold/presets.py", "tests/unit/test_tokens.py", "tests/unit/test_scaffold.py", "tests/system/test_e2e_33_orphan.py", "docs/commands/tokens.md"]

[[acceptance]]
text = "given a stale same-named generated file at the other resolution base, when tokens or tokens --check runs, then a warning names both paths; the scaffolded crunk.toml comments state the path-base rule (E2E-33)"
bound = false
+++

Per r8 tokens.md (Orphan-copy warning) and 02 (Path-base rule): [project] keys resolve against css_root, every other *_file key against project root -- compat law, not rebased. write/check warn (never error) when a same-basename file exists at the other base; scaffold preset comments state the rule beside tokens_file.
