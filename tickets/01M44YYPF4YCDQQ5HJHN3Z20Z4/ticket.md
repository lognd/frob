+++
id = "01M44YYPF4YCDQQ5HJHN3Z20Z4"
title = "frob migrate directives and exceptions: rewrite v1 frob:ticket ids and frob:waive into v2 forms"
type = "story"
category = "todo"
priority = "high"
parent = "01M44YYN4E7SXWHQB3H7EHD37P"
reporter = "lognd"
created = "2026-10-05T02:40:43Z"
updated = "2026-10-05T02:40:43Z"

[[acceptance]]
text = "Given v1 source with frob:ticket T-ids and frob:waive comments, when frob migrate directives and exceptions --apply run, then ids are ULIDs, waivers are exceptions, and every dropped waiver is reported"
bound = false

[[acceptance]]
text = "Given a file changed since the plan, when apply runs, then it refuses with a stale error"
bound = false
+++

migration.md section 1 rows for directives and frob:waive: directives rewritten to full ULIDs on request (aliases keep working otherwise, with a TICK note), waivers rewritten into exceptions (exceptions.md section 7) through the rule id map docs/migration/rule-ids.md, merged ids mapped, waivers for dropped rules deleted and reported. Writes through the atomic write helper (gob-fs) with the digest guard pattern of check --fix.
