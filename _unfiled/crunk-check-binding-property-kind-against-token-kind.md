+++
id = "01M7EXTCF2PMWZVXDW0SJCNR5X"
title = "crunk: check binding property kind against token kind"
type = "task"
category = "todo"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-11-15T06:20:23Z"
updated = "2026-11-15T06:20:23Z"
idempotency_key = "crunkplan-2cb106f690c4"
labels = ["no-story"]

[[acceptance]]
text = "binding a colour token to padding raises a finding"
bound = false
+++

Source: /home/logan/projects/frob-audit2-crunk.md, finding M2.
Evidence: a colour token can be bound to a spacing property
Remedy: compare property kind with token kind at binding validation
Crates/files: crates/crunk-rules binding rules
Verify against HEAD first; the audit ran on a stale binary.
