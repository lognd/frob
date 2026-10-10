+++
id = "01M4H2C3YV4ZDRNNTVKKYD6J5K"
title = "frob serve: expose the ticket and lease read verbs (ticket show|list|doable|brief|doctor|triage list, lease list, ticket contention, ticket evidence list) as MCP tools"
type = "story"
category = "todo"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-09T19:31:22Z"
updated = "2026-10-09T19:31:26Z"
scope = ["crates/frob/src/ticket/**", "crates/frob-lease/src/**", "crates/frob-evidence/src/**", "changelog.d/**"]

[[links]]
kind = "blocked-by"
target = "01M4BMRX5T7R0BH9P7HZZQ6PA9"

[[links]]
kind = "blocked-by"
target = "01M4FDPNXX3X842GBA3FP0SDK3"

[[acceptance]]
text = "Given frob serve, when tools/list runs, then the ticket, lease and evidence read verbs are listed with schemas, and a frob_ticket_doable call returns the same envelope as the CLI"
bound = false
+++

Deferred from ~MQ1NM4Q (files leased by ~ZZQ6PA9 and ~FP0SDK3); patch at the coordinator scratchpad mq1nm4q-deferred-read-only.patch. Needed before switching the owner's MCP server from frob-v1 serve (v1 exposes frob_doable_tickets).
