+++
id = "01M4235FSBRRXMX4Q72QAFRXM3"
title = "land refuses only findings the ticket introduces; pre-existing base findings are reported, not blocking (ratchet)"
type = "story"
category = "todo"
priority = "high"
points = 5
reporter = "lognd"
created = "2026-10-03T23:56:37Z"
updated = "2026-10-03T23:56:37Z"
scope = ["crates/frob-land/**", "crates/frob-check/src/delta.rs", "docs/design/tickets.md", "docs/design/rules.md"]

[[acceptance]]
text = "Given an error present on the base tip and untouched by the ticket, when land runs, then it lands and the report lists the finding as pre-existing"
bound = false

[[acceptance]]
text = "Given the ticket introduces a new error, when land runs, then it refuses naming only the new finding"
bound = false

[[acceptance]]
text = "Given the ticket fixes a pre-existing error, when land runs, then the report shows it resolved"
bound = false
+++

Reported by cloc (FROB_FEEDBACK item 14): an error outside the ticket's diff that already exists on the base (REL001 on old tags) makes land refuse every unrelated ticket (E-LAND-CHECK-RED). verify_check in crates/frob-land/src/land.rs refuses any finding at fail_on in the ticket-scoped report, including findings that are pre-existing repository state.

Land gates on what the ticket changes (rules.md 6, the ratchet): land refuses a finding at or above fail_on only if it is new relative to the base tip, by finding fingerprint (rule id, symref or path, normalized message hash; rules.md 6). Findings present on the base are listed in land's report as pre-existing, never hidden, and still fail frob check, CI and release status. Computing the base side: run the same check on the base tip (cache makes it cheap), or reuse a base fingerprint set cached per base commit under .frob/. A ticket that fixes a pre-existing error shows it as resolved. Document in tickets.md (land) and rules.md 6. Keep SCOPE001 and the done guards exactly as they are; they are about the ticket.
