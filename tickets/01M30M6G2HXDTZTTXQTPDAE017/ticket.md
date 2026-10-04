+++
id = "01M30M6G2HXDTZTTXQTPDAE017"
title = "explore_runner.py: open parse-artifact cache read-only for single-process explore commands"
type = "bug"
category = "done"
outcome = "done"
priority = "medium"
reporter = "human"
created = "2026-09-21T00:00:00Z"
updated = "2026-09-21T00:00:02Z"
aliases = ["T-5201"]
scope = ["src/frob/app/explore_runner.py", "tests/unit/test_explore_runner_parse_artifact_cache.py", "design/frob.strata", "docs/design/registry/capability-via-ratchet.lock.json"]
+++

found while working T-5135 (perf audit H-item, xref/map 11s): lang._parse_file_with_artifact_cache is a passthrough whenever PARSE_ARTIFACT_CACHE_ENV is unset, which is every single-process command including frob explore -- 1643 uncached parses measured on frob explore xref. Fix direction: stamp/open the artifact cache read-only for explore commands, same as gate workers do. Could not fix under T-5135: explore_runner.py was removed from T-5135's scope due to a live cross-worktree lease collision with T-4690.
