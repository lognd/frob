+++
id = "01M43AXZRK62S6DATKMBQGCFRG"
title = "grimble-websec family ROUTE: first slice of rules in GRL"
type = "story"
category = "in-progress"
priority = "medium"
points = 5
parent = "01M43AWG308SDDDQTE35NR79CM"
reporter = "lognd"
created = "2026-10-04T11:31:34Z"
updated = "2026-10-21T11:54:04Z"
idempotency_key = "crunk-plan-g_ROUTE"
labels = ["area:grimble"]
scope = ["packs/grimble-websec/rules/route/**", "packs/grimble-websec/tests/route/**", "packs/grimble-websec/pack.toml", "crates/grimble-check/src/websec_pack.rs", "crates/grimble-check/tests/websec_pack.rs", "docs/grimble/packs/grimble-websec.md", "changelog.d/01M43AXZRK62S6DATKMBQGCFRG.added.md"]

[[links]]
kind = "blocked-by"
target = "01M43AWPD2DYMS2CVTJRD56D5R"

[[acceptance]]
text = "Given code violating the first rule, when `grimble check` runs, then the finding fires with teaching text"
bound = true

[[acceptance]]
text = "Given the clean example, when `grimble rule test` runs, then it passes"
bound = true

[[acceptance]]
text = "Given a language without an adapter, when the family runs, then it is NotApplicable or Unresolved with the reason"
bound = false
+++

Follow-up to the grimble-websec scaffold: framework-specific route rules (auth on routes, method and handler exposure); needs framework adapters, report Unresolved where absent. Source: requirement-bearing v1 tickets of the family imported by ~TM4E1PN and the catalog in notes/v1/gates-and-rules.md section 11. Write the first slice in GRL with examples; split per rule group at pickup if above 8 points. Unsupported languages are Unresolved, never clean.
