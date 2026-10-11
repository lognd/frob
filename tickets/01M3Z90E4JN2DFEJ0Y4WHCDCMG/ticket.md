+++
id = "01M3Z90E4JN2DFEJ0Y4WHCDCMG"
title = "gob-languages and gob-directives: YAML comment scanning and key binding so directives and exceptions work in workflow files (tree-sitter F2 split to ~KC4NSBJ)"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 3
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-02T21:40:59Z"
updated = "2026-10-11T03:06:41Z"
idempotency_key = "m2-yaml-directives"
labels = ["milestone:2"]
scope = ["crates/gob-languages/**", "crates/gob-symbols/**", "crates/gob-directives/**"]

[[links]]
kind = "blocked-by"
target = "01M3Z713F6VY15YSMS15033RN1"

[[acceptance]]
text = "Given a frob:accept CI001 directive above a YAML key in a workflow, when frob check runs with the zizmor stage, then the CI001 finding inside that key is suppressed and listed as suppressed, and a directive above a different key does not suppress it"
bound = true
+++

Found by 01M3Z712WWYRXPSWNVDXX6K71R: YAML is not a language the directive scanner reads, so frob:accept on a CI finding inside a workflow file is inert and the existing frob:used-by comment in dependabot.yml is ignored. Add tree-sitter-yaml behind a feature in gob-languages, an F2 adapter in gob-symbols (keys as units, anchors and aliases as references), and hash-comment directive scanning in gob-directives; the GitHub Actions adapter builds on it.
