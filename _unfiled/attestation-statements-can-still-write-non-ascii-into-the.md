+++
id = "01M415HTAQ7YSKXW09DG39YHBW"
title = "Attestation statements can still write non-ASCII into the ledger"
type = "bug"
category = "done"
outcome = "done"
priority = "low"
points = 1
reporter = "lognd"
created = "2026-10-03T15:19:03Z"
updated = "2026-10-03T18:43:54Z"
scope = ["crates/frob-evidence/src/attestation.rs", "crates/frob-evidence/tests/**", "crates/frob-evidence/src/error.rs", "crates/frob/tests/attestation.rs"]

[[acceptance]]
text = "Given an attestation statement containing a non-ASCII character, when evidence add --provider attestation runs, then it exits 2 naming the character and nothing is written under tickets/"
bound = true
+++

Left over from ~G31XEZ3: the non-ASCII backstop skips the attestation table because its digest covers the raw statement. Refuse a non-ASCII statement at input with a usage error naming the first offending character and its \\u{XXXX} escape (the attester types it, so they can retype it), rather than changing the digest scheme.
