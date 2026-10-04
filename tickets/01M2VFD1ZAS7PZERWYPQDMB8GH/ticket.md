+++
id = "01M2VFD1ZAS7PZERWYPQDMB8GH"
title = "frob-suggest: log every block/allow/ignored-ack decision to .frob/telemetry.jsonl"
type = "bug"
category = "triage"
priority = "low"
parent = "01M2VFD1ZDWWNTW1FFGKHCKTS3"
reporter = "human"
created = "2026-09-19T00:00:00Z"
updated = "2026-10-04T21:08:28Z"
aliases = ["T-5098"]
labels = ["v1-cluster:E1", "triage:accepted"]
scope = [".claude/hooks/*", "tests/test_hook_frob_suggest.py"]

[[acceptance]]
text = "every block, allow, and ignored-ack decision appends a kind=hook row to .frob/telemetry.jsonl with hook, rule, agent, command shape, and decision"
bound = false

[[acceptance]]
text = "logging uses the repo logging conventions and is proven by a test"
bound = false
+++

Leaf 4 of T-5101. See scratchpad/HOOK-AUDIT.md section 3.3.

ORDERING NOTE (coordinator via planner, 2026-09-19): T-4689 (story T-4687, CLI debloat) also edits .claude/hooks/tool-call-telemetry.py, which this ticket's scope glob .claude/hooks/* covers, and T-4689 LANDS FIRST. It adds verb and subverb fields to the telemetry rows this hook writes. Build the kind=hook decision rows on those fields rather than defining a second row shape for the same stream.
