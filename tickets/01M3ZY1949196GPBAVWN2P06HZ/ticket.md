+++
id = "01M3ZY1949196GPBAVWN2P06HZ"
title = "Trust review flow and hardened --follow from the trust UX audit"
type = "docs"
category = "in-progress"
priority = "high"
points = 3
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-03T03:48:27Z"
updated = "2026-10-03T03:48:27Z"
idempotency_key = "m2-trust-review-flow"
labels = ["milestone:2", "area:security"]
scope = ["docs/design/**", "notes/review/trust-ux-audit.md"]

[[acceptance]]
text = "Given security.md, when each TUX finding is looked up, then it has a decided mitigation, and the trust flow, --follow rules and process-stage classes are specified"
bound = false
+++

Fold notes/review/trust-ux-audit.md (18 findings: 6 high, 9 medium, 3 low) into security.md: review grants and host-computed flows, never call sites; one fixed summary screen plus at most five type-to-confirm high-risk screens; deny by default and partial trust; a one-second anti-typeahead arm only; verified provenance instead of author names; --follow as a ceremony on a recorded exact ref and tip advanced only by frob, evaluated at the merge base, high-risk widening held pending even on the protected branch, a revocation list; process stages classed runs-repository-code or fetches-and-runs-code with declared inputs; agent-marker refusal and honest TTY claim; rate limits. Records the owner's proposal verdict per element.
