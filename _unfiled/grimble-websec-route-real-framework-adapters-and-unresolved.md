+++
id = "01M7DHKG6FAA3ZD1W4ZG2X6W6B"
title = "grimble-websec ROUTE: real framework adapters and Unresolved result for unsupported frameworks (follow-up of AG2MXS9)"
type = "task"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-11-14T17:27:40Z"
updated = "2026-11-14T17:27:40Z"
+++

AG2MXS9 widened the text rules (ROUTE105 verbs, Depends, custom guard names; ROUTE107 return str(e)). Still open: GRL has no adapter mechanism or Unresolved outcome, so Django urlconf, Express, Spring route tables cannot be read and unsupported frameworks are only NotApplicable by example. Needs a route-table adapter API in grimble and a per-file Unresolved finding.
