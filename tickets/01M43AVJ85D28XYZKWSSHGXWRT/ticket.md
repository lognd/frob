+++
id = "01M43AVJ85D28XYZKWSSHGXWRT"
title = "crunk-web family A11Y: first slice of rules in GRL"
type = "story"
category = "todo"
priority = "medium"
points = 8
parent = "01M43ANVJYA7GHN0Y8GX0SN72M"
reporter = "lognd"
created = "2026-10-04T11:30:14Z"
updated = "2026-10-08T08:14:18Z"
idempotency_key = "crunk-plan-web_A11Y"
labels = ["area:crunk"]
scope = ["packs/crunk-web/rules/a11y/**", "packs/crunk-web/tests/a11y/**"]

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

Follow-up to the crunk-web scaffold: accessibility rules on TSX and HTML markup: alt text, labels, roles, contrast of rendered text pairs reuse of CONTRAST, focus order hints, ARIA validity. Take the requirement-bearing v1 tickets of the family (imported under area:crunk by ~TM4E1PN, catalog in notes/v1/gates-and-rules.md section 11) and write the first slice as GRL rules with examples; split this ticket per rule group at pickup if the slice exceeds 8 points. Adapter gaps (no HTML adapter) are reported as Unresolved, never clean.
