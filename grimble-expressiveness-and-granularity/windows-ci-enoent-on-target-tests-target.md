+++
id = "01M69P2ZTX0MK8VEEYNFRZWR2J"
title = 'Windows CI ENOENT on target\tests\target'
type = "bug"
category = "todo"
priority = "high"
points = 2
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-10-31T19:13:22Z"
updated = "2026-10-31T19:39:26Z"
idempotency_key = "ci-win-enoent"
scope = [".github/workflows/ci.yml", "crates/frob-tests/**"]

[[acceptance]]
text = 'rust (windows-latest) nextest passes without ENOENT on target\tests\target'
bound = false
+++

CI run 41221220516 windows job failed after ~40min with ENOENT D:\a\frob\frob\target\tests\target; investigate which test creates or reads that path.
