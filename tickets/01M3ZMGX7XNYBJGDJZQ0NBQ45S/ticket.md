+++
id = "01M3ZMGX7XNYBJGDJZQ0NBQ45S"
title = "Capabilities deny by default; excuses only in matrix-build templates; CAP004 excused-but-used"
type = "docs"
category = "in-progress"
priority = "high"
points = 3
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-03T01:02:13Z"
updated = "2026-10-03T01:08:55Z"
idempotency_key = "m2-deny-default"
labels = ["milestone:2"]
scope = ["docs/design/**"]

[[acceptance]]
text = "Given the design set, when grepped for node-level excuses and CAP003, then no regular node can excuse an atom, CAP003 is marked retired, CAP004 is defined, and binding.md 7.2 evaluates observed uses before any excuse"
bound = false
+++

Owner decision 2026-10-04. (1) Deny by default: a regular node's capability that is not granted is denied; observed use without a grant is CAP001 (Error); a blank cell means denied, not unconsidered; CAP003 (CAP-UNEXCUSED, model completeness) is retired. (2) Excuses are removed from regular .grmb nodes (no node-level excuses clause; MDL error if written) and exist only in matrix-build templates: declarations, living with atoms and detectors in packs or a template section of the model, that shape how atoms apply across languages and unit kinds in the grimble IR (for example an atom that does not apply to generated code of a given kind), each with a mandatory reason, reviewed and counted. (3) CAP004 excused-but-used (Error, P+): code covered by a template excuse is observed using the excused atom; uncertain detection yields Unresolved, never a pass; the matrix cell is no longer computed with excused before uses. (4) SYS012 is redefined as a matrix-build check: a template excuse that contradicts a grant in the model. (5) not-applicable stays detector-declared only. Propagate to binding.md (6.12, 7.2 cell order, 9, 10, 11 open question resolved), grimble-model.md (rule table, CAP003 retired, CAP004 added, 9.6 cell set), grmb-spec.md (excuses clause removed from nodes, template construct specified with grammar and U encoding, MDL rule for a node-level excuse), packs.md (template excuses in packs), code-model.md section 7, rules.md and boundaries.md family rows, and a README decision row D75 with this text.
