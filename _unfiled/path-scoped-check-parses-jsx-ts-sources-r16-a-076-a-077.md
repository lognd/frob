+++
id = "01M1T07J44V0BS6B6MF47AKVMS"
title = "Path-scoped check parses jsx/ts sources (r16, A-076/A-077)"
type = "bug"
category = "done"
outcome = "done"
priority = "medium"
reporter = "human"
created = "2026-09-06T00:00:00Z"
updated = "2026-09-06T00:00:02Z"
aliases = ["crunk:T-0132"]
labels = ["component:crunk", "source:crunk"]
scope = ["src/crunk/ingest/walk.py", "tests/unit/test_ingest.py", "tests/system/test_e2e_54_pathmode.py", "docs/commands/tokens.md", "README.md", "frob.lock"]

[[acceptance]]
text = "given a ts class-list file the repo-wide run flags, when check runs on that file and on its directory, then the same TW findings appear at the same lines"
bound = false

[[acceptance]]
text = "given the tokens command doc and README, when read, then the recommended wiring for real size utilities is stated"
bound = false
+++

Implement the r16 design: ingest_paths parses named tsx/ts files and matching files under named directories per the jsx globs, builds tw_theme unconditionally, ungoverned stays empty; plus the A-077 wiring note in the tokens command doc and README describing how adopting the generated theme file wholesale exposes size utilities.
