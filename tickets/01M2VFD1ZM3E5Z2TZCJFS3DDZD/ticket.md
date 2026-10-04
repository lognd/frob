+++
id = "01M2VFD1ZM3E5Z2TZCJFS3DDZD"
title = "narrative move deletes directive lines inside the moved comment run"
type = "bug"
category = "done"
outcome = "done"
priority = "high"
points = 3
parent = "01M2VFD1JK8W1752V73ERRYJS9"
reporter = "human"
created = "2026-09-19T00:00:00Z"
updated = "2026-09-19T00:00:02Z"
aliases = ["T-5108"]
labels = ["milestone:0.534.0"]
scope = ["src/frob/narrative/_cli.py", "tests/test_narrative_migrate.py", "docs/commands/narrative.md"]

[[links]]
kind = "blocked-by"
target = "01M2VFD1JPTVZ2HMYZGVBJGP4Q"
+++

Measured 2026-09-19 by the narrative cluster agent working T-4719, T-4723 and T-4715: the narrative move verb's default mode (without keep-file) deletes the entire contiguous comment run it is pointed at, including directive lines that sit inside that run next to the prose. Lost in three separate runs and restored by hand before commit: frob:doc anchors, a frob:waive PII012, and a frob:invariant INV-042 block.

Why this is structural: the DOCARCH cleanup moves hundreds of runs, and the planned Tier-A auto-fix (T-4694) will call the same path unattended, so every directive adjacent to prose would silently vanish and the graph would lose edges, waivers and invariants with no gate firing.

Fix: when moving a run, split it at token level into prose lines and directive lines (any line whose first token after the comment marker is a frob: directive, plus the continuation lines of a multi-line directive block) and keep the directive lines in place; only the prose leaves. Positive control: a fixture run containing prose plus one frob:doc, one frob:waive and one multi-line frob:invariant must, after move, still contain all three directives byte-for-byte and none of the prose. Also cover the agent's detection recipe as a regression test: the diff of a moved file must contain no removed directive lines.
