+++
id = "01M41FDWMMZTSHZETC48C6Y5DZ"
title = "Lease overlap treats any two wildcard globs with a shared literal prefix as overlapping (crates/*/Cargo.toml vs crates/x/tests/**)"
type = "bug"
category = "done"
outcome = "done"
priority = "high"
points = 3
reporter = "lognd"
created = "2026-10-03T18:11:40Z"
updated = "2026-10-03T18:31:43Z"
scope = ["crates/frob-lease/src/overlap.rs", "crates/frob-lease/tests/**", "docs/design/tickets.md", "crates/frob-lease/Cargo.toml", "Cargo.lock"]

[[acceptance]]
text = "Given scopes crates/*/Cargo.toml and crates/frob-evidence/tests/**, when overlap is computed, then they do not overlap"
bound = true

[[acceptance]]
text = "Given crates/*/src/** and crates/frob-*/src/lib.rs, when overlap is computed, then they overlap"
bound = true

[[acceptance]]
text = "Given a property test over random path sets and glob pairs from a small alphabet, when the segment test says disjoint, then no generated path matches both globs"
bound = true
+++

Observed 2026-10-03: ~G39YHBW (crates/frob-evidence/tests/**) was refused E-LEASE-HELD against ~AZS0RRT with overlap 'crates/*/Cargo.toml and crates/frob-evidence/tests/**', which no path can match both. globs_overlap in crates/frob-lease/src/overlap.rs, for two wildcard globs, returns true when either literal prefix is a prefix of the other, so any per-crate glob under crates/ collides with every other crates/ glob and serializes parallel tickets. Replace the both-wildcard branch with a segment-wise intersection test over path segments: literal vs literal must be equal; '*' (and segments with wildcards inside, e.g. '*.rs', 'frob-*') matches one segment when the two segment patterns can match a common string (test by matching each literal side, and treat wildcard-vs-wildcard segments as compatible); '**' matches zero or more segments (recursive with memoization). It stays conservative for anything it cannot decide (character classes, braces): those fall back to overlap. Brace alternatives can be expanded first. Keep the repository-walk second stage unchanged.
