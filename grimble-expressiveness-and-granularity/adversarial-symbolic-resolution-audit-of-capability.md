+++
id = "01M63ZVCMA9J28JWXJEVNVD3Q1"
title = "Adversarial symbolic-resolution audit of capability detectors and LOG rules"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 5
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-10-29T14:08:32Z"
updated = "2026-10-30T23:21:45Z"
idempotency_key = "adv-symbolic-audit-533"
scope = ["crates/grimble-check/tests/**"]

[[acceptance]]
text = "Findings file triaged: every miss filed as a ticket under the grimble audit epic in milestone 0.533.0"
bound = true

[[acceptance]]
text = "Every caught case is pinned as a regression test; no fix is a lexical patch"
bound = true
+++

Owner requirement: detection must be SYMBOLIC (parse, resolve imports/aliases/receivers/re-exports), never lexical. Evasions risk arbitrary code execution on a victim machine. Audit run by an Opus auditor; ALL findings reported at every severity; findings in the session scratchpad symbolic-audit.md.
