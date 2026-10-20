+++
id = "01M4D6NR5KWAT0R601B1QDWWPS"
title = "CI dev-publish 'Move the dev tag' fails 403 since 2026-10-06: GITHUB_TOKEN cannot move a ref onto commits that change workflow files"
type = "bug"
category = "done"
outcome = "done"
priority = "critical"
class = "expedite"
points = 2
parent = "01M4CTDVKQVPSY0SF4XTNT2Q1E"
reporter = "lognd"
created = "2026-10-08T07:29:34Z"
updated = "2026-10-08T10:15:10Z"
scope = ["changelog.d/**", ".github/workflows/**", "crates/frob-release/**"]

[[acceptance]]
text = "Given the dev workflow test in frob-release, when run, then it reflects the new mechanism"
bound = true
+++

Run 37729454854 job publish: gh api -X PATCH repos/lognd/frob/git/refs/tags/dev returns 'Resource not accessible by integration'. The dev tag is stuck at 1b5de0433 (2026-10-06 16:25). Hypothesis: updating a ref with GITHUB_TOKEN to a commit whose diff touches .github/workflows needs the workflows permission, which GITHUB_TOKEN cannot have. Find the mechanism that works without a PAT (for example release-based tag creation, or deleting and recreating the tag, verified on a test ref) or record that an owner token is needed. Must land before ~GHMWDGG (land refuses onto a red base).
