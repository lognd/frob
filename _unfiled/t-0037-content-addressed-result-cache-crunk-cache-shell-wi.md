+++
id = "01M1QDTV15N0TWQVWNK2GVF83C"
title = "content-addressed result cache: crunk.cache + shell wiring (CR-16)"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
reporter = "human"
created = "2026-09-05T00:00:00Z"
updated = "2026-09-05T00:00:02Z"
aliases = ["crunk:T-0037"]
labels = ["component:crunk", "source:crunk"]
scope = ["src/crunk/cache/**", "src/crunk/app/**", "src/crunk/__main__.py", "src/crunk/scaffold/write.py", "invariants/INV-009.md", "tests/unit/test_cache.py", "tests/unit/test_app.py", "tests/unit/test_scaffold.py", "tests/unit/test_main.py", "tests/integration/test_int_09_cache.py", "tests/system/test_e2e_17_cache.py", "docs/design/subsystems/cache.md", "docs/design/subsystems/shell.md", "docs/commands/*.md", "README.md", "docs/index.md"]

[[links]]
kind = "blocked-by"
target = "01M1QDTV11YBN4ZWJ0J4H8A2Q4"

[[acceptance]]
text = "given an unchanged fixture tree, when check runs twice, then the warm run is byte-identical to cold and served from .crunk-cache; a one-byte edit to a stylesheet or crunk.toml yields the fresh answer; --no-cache bypasses (E2E-17, INT-09, INV-CACHE-01)"
bound = false
+++

Per r4 cache.md and shell.md: cache/store.py (cache_key length-prefixed sha256, CacheStore with atomic put + prune, every failure degrades to miss); shell _styles_cached wraps ingest_tree for check/fix/map (key: schema const, crunk version, crunk.toml bytes, sorted (relpath, sha256) inventory, ungoverned relpaths; value: ProjectStyles.model_dump_json); --no-cache global on pipeline commands; PATH-narrowed runs uncached; init appends .crunk-cache/ to .gitignore exactly once (UT-SH-07); INV-009 invariant file + anchors per the established invariants/ used-by pattern. UT-CACHE-01..04, INT-09, E2E-17.
