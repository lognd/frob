+++
id = "01M4FG41QM8F4BG9CTMJSMN4BH"
title = "DSL002: --fix rewrites v1 ticket aliases (T-####) to the ticket's ULID through the imported aliases, and flags frob:todo as well as frob:ticket"
type = "bug"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-09T04:52:59Z"
updated = "2026-10-09T04:52:59Z"
labels = ["adoption:logand-app"]
scope = ["crates/frob-obligations/**", "crates/gob-directives/**", "changelog.d/**"]

[[acceptance]]
text = "Given imported tickets with v1 aliases and files carrying frob:ticket T-0009 and frob:todo T-0038 note=..., when frob check --only DSL002 --fix runs, then every alias that resolves is rewritten to the full ULID, each site that does not resolve stays as a finding, and frob:todo sites are flagged the same as frob:ticket"
bound = false
+++

logand.app-v2 F-501 (449 sites, 0 fixes applied) and F-502 (18 frob:todo sites not flagged). Complements ~KP5659Y (alias resolution without rewriting).
