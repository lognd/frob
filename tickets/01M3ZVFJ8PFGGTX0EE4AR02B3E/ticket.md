+++
id = "01M3ZVFJ8PFGGTX0EE4AR02B3E"
title = "Plugin and pack security design from the pessimistic audit (D82)"
type = "docs"
category = "done"
outcome = "done"
priority = "critical"
points = 5
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-03T03:03:49Z"
updated = "2026-10-03T03:07:31Z"
idempotency_key = "m2-plugin-security-design"
labels = ["milestone:2", "security"]
scope = ["docs/design/**", "notes/review/plugin-security-audit.md"]

[[acceptance]]
text = "Given security.md, when each SEC finding of the audit is looked up, then it has a decided mitigation or a recorded owner question, and every critical finding is closed by a stated invariant"
bound = false
+++

Fold notes/review/plugin-security-audit.md (34 findings: 4 critical, 17 high, 10 medium, 3 low; assumes users click yes, copy-paste remedies, approve lock-only PRs, ignore repeated warnings, and agents obey diagnostic text) into the design without banning any capability. Write docs/design/security.md: the invariants I1-I13, the decided mitigation for each SEC finding with its home section and new ids (GATE001, MIR003, PACK010), the mechanisms in full (pack tree digest; derived state outside the work tree with per-machine MAC; base-ref trust and trust --follow; process packs for check.tool stages; sandbox worker and effect broker; effect classes incl. secret-shaped and control-plane; honest gate: required packs, change-delta no-new-unknowns, GATE001 policy-weakened; text origin and escaping; host-owned fixes; mirror marker authentication). Update plugins.md 9, packs.md 2.5, diagnostics.md, mirror.md 3.1 (MIR002 required in the mirror job, advisory in the code gate: flag to the owner as a change to the loud-divergence decision), the README row D82, and commit the audit.
