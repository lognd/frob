+++
id = "01M6DPY6VYPQAJ8GP83J0BEQR7"
title = "Crunk guides: say crunk lives in this repo, cross-link docs/migration/crunk-import.md, retarget stale docs/crunk refs"
type = "docs"
category = "in-progress"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-11-02T08:45:12Z"
updated = "2026-11-02T08:54:53Z"
scope = ["docs/guides/crunk.md,docs/guides/crunk-from-python.md,docs/guides/crunk-hullbreach.md,.github/scripts/plan-jobs.py", "changelog.d/J0BEQR7.docs.md", "docs/guides/crunk.md", "docs/guides/crunk-from-python.md", ".github/scripts/plan-jobs.py", "changelog.d/01M6DPY6VYPQAJ8GP83J0BEQR7.changed.md"]
+++

Found while working ~DCZT0SC: docs/crunk was already dissolved into docs/guides and docs/reference by ~XPA3A54 (commit 2f0a87b03e). Remaining from the old acceptance: guides/crunk.md does not state crunk is part of this repo; crunk-from-python.md does not cross-link docs/migration/crunk-import.md; .github/scripts/plan-jobs.py comment and crates/gob-dev/src/render/docs_index.rs:247 still name docs/crunk.
