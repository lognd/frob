+++
id = "01M7EXT8ADBQS8RFVJBZ2AVC7A"
title = "Declarative regex and JSON-pointer parser recipes for tool stages"
type = "task"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-11-15T06:20:18Z"
updated = "2026-11-15T06:20:18Z"
idempotency_key = "static-research-k7"
labels = ["no-story"]
+++

Source: /home/logan/projects/frob-research-static-analysis.md section 6 item 7, section 4.3 step 3. Rationale: tools without SARIF/JSON parsers currently need Rust in crates/gob-check/src/tool_parse.rs. Remedy: parser = "regex" with pattern named groups (path,line,col,severity,code,message) and parser = "json-path" mapping fields by JSON pointers, configured in the stage or tool definition TOML. Errorformat-class tools then need no code. Crates/files: crates/gob-check/src/tool_parse.rs, config.rs (ToolParser enum), docs tool-stages.
