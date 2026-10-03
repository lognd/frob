+++
id = "01M3ZSHSF9CPQ18RZSQJ8PJHKX"
title = "Record owner decisions on mirror, diagnostics and plugins (D76, D78, D79 accepted with changes)"
type = "docs"
category = "in-progress"
priority = "high"
points = 3
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-03T02:30:05Z"
updated = "2026-10-03T02:34:39Z"
idempotency_key = "m2-owner-decisions-1004"
labels = ["milestone:2"]
scope = ["docs/design/**", "docs/schemas/**"]

[[acceptance]]
text = "Given the three design files and the README, when read, then each decision above is stated once, D76, D78 and D79 are marked accepted with the changes, and the issue projection schema exists"
bound = false
+++

Owner decisions 2026-10-04. Mirror (mirror.md, D79): GitHub Issues is the first tracker, but the producer is platform agnostic: frob renders each ticket into a neutral, tracker-independent issue projection (fields, relationships, state, body sections, identity marker, a declared mapping per tracker) and per-tracker adapters only translate that projection; specify the projection schema (docs/schemas/issue-projection.json) so GitLab and Jira adapters route from it without touching the producer. Divergence policy: skip the edited issue and report it LOUDLY: MIR002 is an Error that fails the gate (required), names the issue, the fields, the tracker user and the time, and is resolvable with explicit verbs: frob mirror resolve <ticket> --keep-repo (re-publish the repository version, with a comment), --adopt (turn the tracker edit into a proposal event to accept or decline), or --ignore-field <f> with a reason recorded as an event. Diagnostics (diagnostics.md, D78): first-occurrence inline teaching is ON by default; the long explanation can always be repeated: frob explain RULE and grimble explain RULE print it in full at any time, --teach on check prints full explanations for every finding in that run, and frob teach reset clears the seen state; --fix stays within the current ticket's scope by default. Plugins (plugins.md, D76): one rule language, GRL, for both single-language pattern rules and universal relational rules (no YAML second form), which obliges GRL to be intuitive (specified in a separate ticket); built-in rules are compiled into the binary for performance but treated logically the same as plugin rules: the same GRL source, the same registry, metadata, diagnostics, exceptions, packs manifest and lock entries; built-ins are compiled ahead of time (GRL to Rust at build time) while plugin GRL runs as plans, and a conformance test runs every built-in both ways and requires identical findings; plugin authors may also compile their pack ahead of time to a WASM component for built-in-class speed. Open items left open: whether repository packs may run WASM in version 1, directory-scoped packs, and the SUMMARY.md ticket. Update mirror.md, diagnostics.md, plugins.md and the README rows D76, D78, D79 (accepted with these changes).
