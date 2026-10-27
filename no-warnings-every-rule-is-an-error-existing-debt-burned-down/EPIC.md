+++
id = "01M5XETK612GJ5QZZZXBA6CSGY"
title = "No warnings: every rule is an error, existing debt burned down via a baseline"
type = "epic"
category = "todo"
priority = "high"
reporter = "lognd"
created = "2026-10-27T01:15:34Z"
updated = "2026-10-27T01:17:16Z"

[[acceptance]]
text = "Severity collapses to Error (and off); Warn and Advisory are removed; Unresolved stays for cannot-decide results"
bound = false

[[acceptance]]
text = "Gate scoping replaces severity for human-sign-off rules: HUMAN001/HUMAN002 do not block local runs or CI but block at the release (CD) gate, expressed as a gate scope, not a lower severity"
bound = false

[[acceptance]]
text = "The 36 Advisory rules each become Error with findings baselined, or are turned off with a recorded reason"
bound = false
+++

Owner policy (2026-10-26): no warn severity; only errors. Burn existing warnings down slowly. Design questions: (1) the new-rule ramp-in (docs/design/rules.md section 6) deliberately reports Error rules as Warn for one release, and Advisory/release_severity exist; each needs a decision (replace ramp with a per-repo baseline of known findings that only shrinks). (2) 74 of 242 rules are warn-severity today; a full frob check gives per-rule counts. (3) Promote zero-finding rules first.
