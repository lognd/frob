+++
id = "01M7ETK8WHHFV8590QXMH57TRZ"
title = "crunk check: schema-invalid component/screen/content files must fail, not be skipped"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-11-15T05:24:04Z"
updated = "2026-11-15T06:07:06Z"
labels = ["no-story"]
scope = ["crates/crunk-rules/**", "crates/crunk/tests/it/common/mod.rs"]

[[acceptance]]
text = "An unparsable component file yields a SPEC001 Error finding"
bound = true

[[acceptance]]
text = "An unparsable screen file yields a SPEC001 Error finding"
bound = true

[[acceptance]]
text = "An unparsable content file yields a SPEC001 Error finding"
bound = true

[[acceptance]]
text = "An unparsable voice.toml yields a SPEC001 Error finding"
bound = true

[[acceptance]]
text = "Valid design files and projects without design files produce no SPEC001 finding"
bound = true
+++

Crunk audit2 H4. See /home/logan/projects/frob-audit2-crunk.md for evidence and remedy; verify against HEAD first (audit binary was 10 commits stale).
