+++
id = "01M43AY47AXTWJ4TWG29WTBWT9"
title = "grimble-websec family WEBPERF-server: first slice of rules in GRL"
type = "story"
category = "todo"
priority = "medium"
points = 5
parent = "01M43AWG308SDDDQTE35NR79CM"
reporter = "lognd"
created = "2026-10-04T11:31:38Z"
updated = "2026-10-04T11:31:38Z"
idempotency_key = "crunk-plan-g_WEBPERF-server"
labels = ["area:grimble"]
scope = ["packs/grimble-websec/rules/webperf-server/**", "packs/grimble-websec/tests/webperf-server/**"]

[[links]]
kind = "blocked-by"
target = "01M43AWPD2DYMS2CVTJRD56D5R"

[[acceptance]]
text = "Given code violating the first rule, when `grimble check` runs, then the finding fires with teaching text"
bound = false

[[acceptance]]
text = "Given the clean example, when `grimble rule test` runs, then it passes"
bound = false

[[acceptance]]
text = "Given a language without an adapter, when the family runs, then it is NotApplicable or Unresolved with the reason"
bound = false
+++

Follow-up to the grimble-websec scaffold: server-side WEBPERF (N+1 shapes, unbounded responses, missing caching headers); markup and asset WEBPERF is crunk-web. Source: requirement-bearing v1 tickets of the family imported by ~TM4E1PN and the catalog in notes/v1/gates-and-rules.md section 11. Write the first slice in GRL with examples; split per rule group at pickup if above 8 points. Unsupported languages are Unresolved, never clean.
