+++
id = "01M43AXBE0A7W14TH20DP8SN2M"
title = "grimble-websec family SQL: first slice of rules in GRL"
type = "story"
category = "in-progress"
priority = "medium"
points = 8
parent = "01M43AWG308SDDDQTE35NR79CM"
reporter = "lognd"
created = "2026-10-04T11:31:13Z"
updated = "2026-10-21T13:45:42Z"
idempotency_key = "crunk-plan-g_SQL"
labels = ["area:grimble"]
scope = ["packs/grimble-websec/rules/sql/**", "packs/grimble-websec/tests/sql/**", "packs/grimble-websec/pack.toml", "crates/grimble-check/src/websec_pack.rs", "crates/grimble-check/tests/websec_pack.rs", "docs/grimble/packs/grimble-websec.md", "changelog.d/01M43AXBE0A7W14TH20DP8SN2M.added.md"]

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
bound = true
+++

Follow-up to the grimble-websec scaffold: SQL in code: injection by string building, missing parameterization, migration safety, query shape. Source: requirement-bearing v1 tickets of the family imported by ~TM4E1PN and the catalog in notes/v1/gates-and-rules.md section 11. Write the first slice in GRL with examples; split per rule group at pickup if above 8 points. Unsupported languages are Unresolved, never clean.
