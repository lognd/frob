+++
id = "01M5GA77VTC3VDYVZ2HBZNRM2K"
title = "GRL lowering: count compared with a knob-times-count ratio (NEAT031)"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
parent = "01M3ZWPE0CNFWB4PTW3D05GDWP"
reporter = "lognd"
created = "2026-10-21T22:44:58Z"
updated = "2026-10-22T00:02:05Z"
idempotency_key = "neat031-count-ratio"
scope = ["crates/gob-plan/src/lower/convert.rs", "crates/gob-plan/tests/ten_rules/main.rs", "crates/gob-plan/src/**", "crates/gob-plan/tests/**", "docs/**", "changelog.d/01M5GA77VTC3VDYVZ2HBZNRM2K.*"]

[[acceptance]]
text = "a count compared against a scaled count lowers, and the NEAT031 lines leave KNOWN_ENGINE_GAPS or are narrowed to the remaining exec blockers"
bound = true

[[acceptance]]
text = "Scaled-count semantics: Count.compare_scaled is sound over negative, zero and fractional scales and open counts"
bound = true

[[acceptance]]
text = "Lowering: count(..) vs scale*count(..) (either side, int/decimal literal or knob, nested counts) lowers to CountPair; non-count scaled forms and over-wide decimals are refused"
bound = true

[[acceptance]]
text = "Plan format: CountPair round-trips through the codec and validate rejects bad scale, var, kind and cond"
bound = false

[[acceptance]]
text = "Alternatives of plain kind words lower to an any-node find with an or of kind tests"
bound = false

[[acceptance]]
text = "End to end: a python ratio rule runs its examples correctly, including zero counts and zero or negative ratios"
bound = false
+++

Found while working ~R3AHZ1T. NEAT031 lowers its relation object and roles snippet now, but its find clause 'count(...) >= knob.ratio * count(...)' is refused with Unsupported 'a count compared with this term'. Lower a count against a scaled count, then delete the NEAT031 lines from KNOWN_ENGINE_GAPS. Exec-level blockers may follow: no stmt KindTest, adapter-op branches (python if_statement) not matched by branch, directly inside is parent-only.
