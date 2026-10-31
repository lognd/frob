+++
id = "01M69J39HA547HNNCMCAMNDCCT"
title = "frob attestation evidence: accept design clause anchors as facts (grmb manual verified_by tie)"
type = "task"
category = "in-progress"
priority = "low"
points = 2
parent = "01M67VDQ8WGS0SYG4J4NFXNQJE"
reporter = "lognd"
created = "2026-10-31T18:03:38Z"
updated = "2026-10-31T20:21:09Z"
idempotency_key = "grmb-cycle12-attestation-tie"
scope = ["docs/design/tickets.md", "crates/frob-ledger/**"]

[[acceptance]]
text = "tickets.md lists design clause anchors (KIND/NAME/verified_by[i], grmb-spec 9.1) as an accepted --fact shape of attestation evidence, validated against grimble graph --json like the implements link"
bound = false

[[acceptance]]
text = "frob's overlay reads a passed attestation carrying that anchor on a live ticket implementing the entity or a design ancestor as the pass verdict of that manual verified_by row (grmb-spec 12.8, D202)"
bound = false

[[acceptance]]
text = "frob evidence and attestation records bound to a design entity store that entity's body_digest from grimble graph --json (grmb-spec 12.8 WINDOW, PM048, D207); records without it are outside every WINDOW"
bound = false
+++

Follow-up of ~MHGA5VN cycle 12 M1: the spec states the tie; the frob side (tickets.md and the attestation provider) is outside that ticket's lease.
