+++
id = "01M42M1KK02KFZG39CXKAD47SZ"
title = "Unreadable tracked files (non-UTF-8) vanish silently from frob check; make them a required Unresolved finding"
type = "bug"
category = "in-progress"
priority = "critical"
points = 2
reporter = "lognd"
created = "2026-10-04T04:51:35Z"
updated = "2026-10-04T06:01:35Z"
scope = ["crates/gob-symbols/src/pipeline.rs", "crates/gob-check/src/**", "crates/frob-check/src/**", "crates/frob-check/tests/**", "crates/gob-symbols/src/lib.rs", "crates/gob-symbols/tests/symbols.rs", "crates/gob-symbols/tests/gaps.rs", "docs/design/architecture.md", "docs/reference/rules/README.md", "docs/reference/rules/READ001.md"]

[[acceptance]]
text = "Given a tracked non-UTF-8 markdown file, when frob check runs, then the report has a required Unresolved finding naming the file and the decode error, and the gate fails under the default fail_on_unresolved"
bound = false

[[acceptance]]
text = "Given the fidelity section, when files were skipped, then their count and reasons appear"
bound = false
+++

Reproduced by the v1 gap analysis (notes/review/v1-gap/C-features.md P-02): a tracked non-UTF-8 .md file produces identical frob check --json output to the repository without it; the only trace is a stderr log line, and the skipped counter in gob-symbols/src/pipeline.rs is never read. A file the gates never read must never look clean (v2 principle: Unknown is never a pass). Fix: every file the walk includes but cannot read or decode becomes a required Unresolved finding naming the file and the reason (encoding, permission, size), counted in fidelity; the skipped counter feeds the report. Decide and document whether a declared binary or generated file is excluded instead (then it is never read and never reported).
