+++
id = "01M7BYRY2QA3VWYMCWRKM15MK2"
title = "Fix COH001/ERR003 errors in crunk-tailwind node helper.mjs"
type = "bug"
category = "done"
outcome = "done"
priority = "high"
points = 3
reporter = "lognd"
created = "2026-11-14T02:39:21Z"
updated = "2026-11-14T02:51:59Z"
idempotency_key = "helper-mjs-coh001-err003"
labels = ["crunk"]
scope = ["crates/crunk-tailwind/node/**"]

[[acceptance]]
text = "given crates/crunk-tailwind/node/helper.mjs, when frob check runs, then it reports no COH001 or ERR003 error for that file"
bound = true
+++

CI run 43543048550 failed frob check: COH001 on runV3, runV4, runV3Theme, runV4Theme (2 jobs each; extract each job) and ERR003 on three catch-all handlers (log to stderr or rethrow). Keep the stdout JSON wire protocol unchanged; crunk-tailwind tests must still pass.
