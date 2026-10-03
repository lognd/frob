+++
id = "01M407JYQJZ2BJ842GHAPQCEPT"
title = "A tool stage that cannot run reports nothing: frob check passes while actionlint never ran"
type = "bug"
category = "in-progress"
priority = "high"
points = 3
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-03T06:35:23Z"
updated = "2026-10-03T06:47:46Z"
idempotency_key = "m2-tool-stage-silent-failure"
labels = ["milestone:2", "release:0.532.0"]
scope = ["crates/gob-check/**", "crates/gob-exec/**", "crates/frob-check/**", "frob.toml", ".github/workflows/**", "crates/gob-rules/src/required.rs", "crates/grimble-check/src/sibling.rs", "docs/design/rules.md", "docs/design/sibling-contract.md", "docs/schemas/envelope.json"]

[[acceptance]]
text = "Given a tool stage whose command cannot be resolved, when frob check runs, then a required Unresolved finding names the stage and shows the tool's error"
bound = false

[[acceptance]]
text = "Given this repository with the corrected actionlint pin, when frob check runs, then actionlint runs over the workflows and its findings, if any, are reported"
bound = false
+++

Found 2026-10-03 (via ~XHT82FS): frob.toml pins actionlint-py==1.7.12, which uvx cannot resolve (the published version is 1.7.12.25), so the actionlint stage fails in about 20 ms and frob check reports no finding at all for it: the workflows have been unchecked by actionlint with a green gate. A tool stage whose command fails to run, exits with an unexpected status, or produces output its parser cannot read must produce a loud finding (Unresolved with reason tool-failed and the tool's stderr excerpt; required by default, since a configured check that did not run is not clean evidence), never silence. Fix the stage machinery (gob-exec / gob-check tool stages), add tests for a missing binary, an unresolvable uvx pin, a non-zero exit with empty output and unparseable output, then fix this repository's pin to actionlint-py==1.7.12.25 and re-check the workflows. Also verify the version_args probe catches this at startup.
