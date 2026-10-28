+++
id = "01M5XCVZFESE41V1GVEYC5VP5X"
title = "crunk export figma-variables plus the Figma plan-limit check"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M4CXQTERP5YASZGVEAH6KG4H"
reporter = "lognd"
created = "2026-10-27T00:41:22Z"
updated = "2026-10-28T12:56:06Z"
labels = ["area:crunk", "no-story"]
scope = ["crates/crunk-tokens/src/export/figma.rs, crates/crunk-rules/src/export_figma.rs"]

[[acceptance]]
text = "Given a token set with 5 modes and a configured plan allowing 4, when checked, then an EXPORT finding names the plan and the limit; given a set within limits, then the Figma variables JSON is deterministic and byte-identical on two runs; given an alias cycle or a token without a Figma type, then it is skipped with a named warning not a panic"
bound = false
+++

Design crunk.md section 9 item 2 ("USS and C# exporters with the Figma plan-limit check"). Add Target::FigmaVariables (collections=tiers, modes=modes, variables=tokens) and the plan-limit rule (variables per collection and modes per collection by plan tier from crunk.toml). Register via the export verb ticket when it lands; do not edit export/mod.rs beyond the enum variant.

no-story: internal engineering task in crunk-tokens; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
