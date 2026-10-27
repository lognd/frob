+++
id = "01M55TXR3TDT88Z472EH71JQ1Q"
title = "FileRule framework: path and side inputs so TODO001, DOC001, DOC002 and REF001 can migrate"
type = "bug"
category = "todo"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-17T21:05:14Z"
updated = "2026-10-27T02:58:21Z"
scope = ["crates/gob-rules/**", "crates/gob-check/**"]
+++

found while working ~MXXGNZ3: FileCx carries only host and text, so the four frob-obligations file rules stay on the legacy derive in src/legacy.rs.
