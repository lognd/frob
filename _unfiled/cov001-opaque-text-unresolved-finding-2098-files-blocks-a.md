+++
id = "01M6HFDQJM7S1TBKXJ2B3XPXBG"
title = "COV001: opaque-text Unresolved finding (2098 files) blocks a zero-finding check"
type = "bug"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-11-03T19:50:50Z"
updated = "2026-11-03T19:50:50Z"
+++

found while working ~3T6JNG5. frob check --only COV001 reports 'N opaque text file(s) (no adapter, first Cargo.lock) were not examined: no adapter provides what the rule reads: repository'. Cause: Cov001 in crates/frob-obligations/src/legacy.rs uses the plain Rule derive, whose default applies reads comments/directives, so gob-check pipeline opaque_repo_findings (crates/gob-check/src/pipeline.rs) marks it Unresolved while any adapter-less text file exists. Pack/CI repo rules avoid this with 'applies = project' but that field is not accepted by the Rule derive Cov001 uses ('Unknown field applies'). Fix: give the legacy repo rules (COV001, TODO002) a project-level applies, or teach the derive to accept it. COV001 only reads Rust symbol graph and frob:tests directives from adapter-backed files.
