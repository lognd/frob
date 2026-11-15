+++
id = "01M7EXVW0VW4FA29JE0NYW4RMJ"
title = "Per-platform sha256 download install recipe behind gob-trust"
type = "task"
category = "todo"
priority = "medium"
points = 5
reporter = "lognd"
created = "2026-11-15T06:21:12Z"
updated = "2026-11-15T06:21:17Z"
idempotency_key = "static-research-k14"
labels = ["no-story"]

[[links]]
kind = "blocked-by"
target = "01M7EXT3X9DSSHYJWNQ4ZQPV00"

[[acceptance]]
text = "A download recipe with a wrong sha256 is refused with a named error and nothing is executed"
bound = false

[[acceptance]]
text = "A correct recipe installs to a trust-bound path and the stage runs from it"
bound = false

[[acceptance]]
text = "Non-install steps run with network denied by default"
bound = false
+++

Source: ~/projects/frob-research-static-analysis.md section 6 item 13, sections 4.2 and 4.3. Rationale: reproducible tool install in the aqua style: pinned version plus digest per platform, download hermetically and verify before running, behind the existing ToolTrust (tree digest) in gob-trust; decided as a later option in rules.md section 13 per the report. Aqua/mise/Trunk facts are [M]: verify first. Remedy: [meta] install recipe download{url,sha256,platform}; refuse on digest mismatch; no network for non-install steps. Crates/files: crates/gob-check/src/tool_def.rs, crates/gob-trust, gob-exec limits. Large: split further if the design needs more than the recipe and verify path.
