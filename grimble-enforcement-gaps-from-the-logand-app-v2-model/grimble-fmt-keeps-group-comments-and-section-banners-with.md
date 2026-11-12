+++
id = "01M4FGZB9A3J18R4RP9MDEJDFV"
title = "grimble fmt keeps group comments and section banners with what they describe"
type = "bug"
category = "in-progress"
priority = "low"
points = 2
parent = "01M4FGWBHH3K9F2PPFYRGQ353T"
reporter = "lognd"
created = "2026-10-09T05:08:03Z"
updated = "2026-11-12T19:55:31Z"
idempotency_key = "logand-gaps-E2"
labels = ["adoption:logand-app", "grimble", "no-story"]
scope = ["crates/grimble-model/**", "docs/design/grmb-spec.md", "changelog.d/**", "docs/design/shared/code-model.md"]

[[acceptance]]
text = "Given a section banner followed by a blank line, when grimble fmt runs, then the banner stays above the same first entity or group"
bound = true

[[acceptance]]
text = "Given per-clause comments, when grimble fmt runs, then they still follow their clause"
bound = true

[[acceptance]]
text = "Given fmt run twice, when compared, then output is identical"
bound = true
+++

Repro 19-fmt-comment-reattachment (~/projects/frob-v2-repros/logand-grimble-20261009/19-fmt-comment-reattachment): fmt sorts clauses by key and entities by name and a comment binds to the next item, so a banner or a 'the clauses below' comment is detached. Friction rather than a spec violation (grmb-spec 8.1/9.3): decide a floating-comment rule (blank-line-separated comment sticks to its section or keeps position) and document it in grmb-spec 9.3.
