+++
id = "01M5XDN67KE9HCKFSX3CDS3X1G"
title = "crunk-scene: expose selector-to-element association for style rules and @media"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-27T00:55:08Z"
updated = "2026-11-15T10:52:30Z"
labels = ["no-story"]
scope = ["crates/crunk-scene/**"]

[[acceptance]]
text = "Given a scene with <style> rules, when it is parsed, then SceneDoc::rules exposes each selector with the element indices it matches (type, class, id, descendant, compound, comma lists), flags other selectors unsupported, and links rules to their enclosing @media at-rule"
bound = true
+++

Style mapping currently uses inline style only; <style> rules yield StylesheetNotApplied findings. Found while working QPY31M6.

no-story: internal engineering task in crunk-scene; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
