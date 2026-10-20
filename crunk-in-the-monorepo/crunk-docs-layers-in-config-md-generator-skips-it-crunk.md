+++
id = "01M4DPJNTFFE5HSKBKX764TEH2"
title = "crunk docs: [layers] in config.md (generator skips it), crunk-tokens and crunk-ingest pages, rule pages rendered from #[rule]"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 2
parent = "01M43ANVJYA7GHN0Y8GX0SN72M"
reporter = "lognd"
created = "2026-10-08T12:07:30Z"
updated = "2026-10-12T01:10:16Z"
scope = ["changelog.d/**", "crates/gob-dev/**", "docs/crunk/**", "crates/crunk-spec/**", "crates/crunk-rules/**", "crates/crunk-check/**"]

[[acceptance]]
text = "Given cargo dev gen, when run, then config.md lists [layers] and docs/crunk/rules pages are generated (GEN001)"
bound = true
+++

Follow-ups from ~HRHS033 and ~JY79XVV.
