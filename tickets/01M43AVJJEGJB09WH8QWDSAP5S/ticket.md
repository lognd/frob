+++
id = "01M43AVJJEGJB09WH8QWDSAP5S"
title = "crunk-web family SEO: first slice of rules in GRL"
type = "story"
category = "todo"
priority = "medium"
points = 5
parent = "01M43ANVJYA7GHN0Y8GX0SN72M"
reporter = "lognd"
created = "2026-10-04T11:30:15Z"
updated = "2026-10-04T11:30:15Z"
idempotency_key = "crunk-plan-web_SEO"
labels = ["area:crunk"]
scope = ["packs/crunk-web/rules/seo/**", "packs/crunk-web/tests/seo/**"]

[[links]]
kind = "blocked-by"
target = "01M43AVHX91K72WYKYFX5W2SPP"

[[acceptance]]
text = "Given a TSX file violating the first rule of the family, when `crunk check` runs, then the finding fires with its teaching text and fix suggestion if any"
bound = false

[[acceptance]]
text = "Given the clean example, when `crunk rule test` runs, then it passes"
bound = false

[[acceptance]]
text = "Given a file type with no adapter, when the family runs, then the result is NotApplicable or Unresolved with the reason"
bound = false
+++

Follow-up to the crunk-web scaffold: document metadata, headings, canonical and structured-data rules on markup and route files. Take the requirement-bearing v1 tickets of the family (imported under area:crunk by ~TM4E1PN, catalog in notes/v1/gates-and-rules.md section 11) and write the first slice as GRL rules with examples; split this ticket per rule group at pickup if the slice exceeds 8 points. Adapter gaps (no HTML adapter) are reported as Unresolved, never clean.
