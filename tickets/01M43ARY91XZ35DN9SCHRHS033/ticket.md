+++
id = "01M43ARY91XZ35DN9SCHRHS033"
title = "crunk-ingest: ProjectStyles from CSS, bucket and organization model, walk"
type = "story"
category = "todo"
priority = "medium"
points = 5
parent = "01M43ANVJYA7GHN0Y8GX0SN72M"
reporter = "lognd"
created = "2026-10-04T11:28:48Z"
updated = "2026-10-04T11:28:48Z"
idempotency_key = "crunk-plan-ing"
labels = ["area:crunk"]
scope = ["crates/crunk-ingest/**", "Cargo.lock"]

[[links]]
kind = "blocked-by"
target = "01M43ARX764095Q4VWABWXXV5H"

[[links]]
kind = "blocked-by"
target = "01M43ARY26XF7A4MSRAZ8V73JM"

[[acceptance]]
text = "Given the corpus projects, when ingested, then the declaration set and bucket inventory equal the Python ProjectStyles dump"
bound = false

[[acceptance]]
text = "Given a git-ignored build CSS outside css_root passed as a path, when checked, then it is skipped without a crash (v1 T-0292)"
bound = false

[[acceptance]]
text = "Given an unchanged tree, when ingested twice, then the second run reads the cache and gives the same result"
bound = false
+++

Port ingest/ (parse.py, walk.py, models.py: about 900 LOC without jsx and tailwind): css_root walk over gob-walk with [org].ignore, declarations from the CSS adapter into ProjectStyles, bucket placement and the org inventory used by `map`. Contents cached in gob-cache by content hash (replaces crunk.cache store.py). Port tests/unit/test_ingest.py and INT-02.
