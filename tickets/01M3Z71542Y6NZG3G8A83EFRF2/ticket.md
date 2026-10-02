+++
id = "01M3Z71542Y6NZG3G8A83EFRF2"
title = "GitHub Actions and Dockerfile adapters in gob-languages and gob-symbols"
type = "task"
category = "todo"
priority = "medium"
points = 8
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-02T21:06:26Z"
updated = "2026-10-02T21:06:26Z"
idempotency_key = "m2-actions"
labels = ["milestone:2"]
scope = ["crates/gob-languages/**", "crates/gob-symbols/**"]

[[links]]
kind = "blocked-by"
target = "01M3Z713F6VY15YSMS15033RN1"

[[acceptance]]
text = "Given a workflow using an action pinned to a tag, when the graph is built, then the instantiate edge has status May and the SHA-pinned one Must"
bound = false
+++

cicd.md section 4: workflows, jobs, steps, uses as instantiate edges with Must for SHA pins and May for tags, expressions as embedded regions, run bodies as shell regions; Dockerfile stages, FROM edges, COPY --from; fidelity F3 and F3 with corpora.
