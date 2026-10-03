+++
id = "01M3ZTAV8SXD9C6G4A42WY14K9"
title = "gob-symbols: lift the 160 term-depth cap now that gob-ir is stack-safe"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-03T02:43:46Z"
updated = "2026-10-03T02:43:58Z"
idempotency_key = "m2-gobsym-depth-cap"
labels = ["milestone:2"]
scope = ["crates/gob-symbols/**"]

[[links]]
kind = "blocked-by"
target = "01M3ZR5KCPY3E3NFCVFS404RDJ"

[[acceptance]]
text = "Given a generated Rust file nested 5000 levels deep, when gob-symbols lowers it on a 2 MiB stack, then it completes without opaque(depth-limit) and symref storage is linear in nesting depth"
bound = false
+++

Follow-up of ~7QWX8P1 (gob-ir printer, symrefs, scope graph and free_vars are iterative; a 1e6-deep term works on a 2 MiB stack). gob-symbols still caps lowering at depth 160 and collapses deeper subtrees to opaque(depth-limit). Before lifting: make the gob-symbols lowering itself stack-safe (its Rust lowering and any syn traversal); then remove or raise the cap to a materialized knob, keeping opaque(depth-limit) only as the honest fallback past the knob. Also fix Symref::child cloning the whole qualified name (quadratic symref storage under deep nesting): share prefixes (Arc path segments or an interned parent link). Test: a deeply nested Rust source (generated, thousands of levels) lowers without stack overflow on the default stack, and symref memory grows linearly.
