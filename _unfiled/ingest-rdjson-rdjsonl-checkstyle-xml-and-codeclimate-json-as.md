+++
id = "01M7EXV84N7ZTK1CXSF7H6MA78"
title = "Ingest rdjson/rdjsonl, checkstyle XML and CodeClimate JSON as tool-stage parsers"
type = "task"
category = "todo"
priority = "medium"
points = 5
reporter = "lognd"
created = "2026-11-15T06:20:51Z"
updated = "2026-11-15T06:20:51Z"
idempotency_key = "static-research-k8"
labels = ["no-story"]

[[acceptance]]
text = "Each of the three formats has a fixture test that parses to RawFinding with path, line, column, code and message"
bound = false

[[acceptance]]
text = "The CodeClimate parser and the existing ty-gitlab parser share one implementation"
bound = false

[[acceptance]]
text = "tool-stages docs list the three parsers"
bound = false
+++

Source: ~/projects/frob-research-static-analysis.md section 6 item 8, section 3. Rationale: many catalogue tools (phpcs, phpstan, ktlint, hadolint, golangci-lint, tflint, ansible-lint) emit checkstyle or CodeClimate and not SARIF; reviewdog's rdjson is a common neutral format. All are [M] claims about which tools emit what: verify first against each tool's docs. Note ty-gitlab already parses a CodeClimate-like variant (crates/gob-check/src/tool_parse.rs). Remedy: three small ToolParser variants (rdjson/rdjsonl, checkstyle, codeclimate) sharing the RawFinding mapping, reusing the ty-gitlab parser for CodeClimate instead of duplicating. Crates/files: crates/gob-check/src/tool_parse.rs, config.rs, new modules next to sarif.rs.
