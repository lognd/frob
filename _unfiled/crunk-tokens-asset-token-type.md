+++
id = "01M7EXSE377CJH4XPBBXBK77CE"
title = "crunk tokens: asset token type"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M7ETKA6EFEZGRH2DMQBD8818"
reporter = "lognd"
created = "2026-11-15T06:19:52Z"
updated = "2026-11-15T06:19:52Z"
idempotency_key = "crunkplan-8ecde7103618"
labels = ["no-story"]

[[acceptance]]
text = "a missing asset path produces a finding"
bound = false

[[acceptance]]
text = "an existing asset resolves"
bound = false
+++

Source: /home/logan/projects/frob-audit2-crunk.md, finding H7.
Evidence: images, icons and fonts cannot be tokens
Remedy: add an asset token type with existence check
Crates/files: crates/crunk-tokens, crates/crunk-spec
Verify against HEAD first; the audit ran on a stale binary.
