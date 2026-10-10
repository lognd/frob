+++
id = "01M4GYBNW01DT1MJ6NJN2GX6NN"
title = "Capability grants need human acknowledgement: a new or widened may grant is a finding until acked by an attester, so agents cannot self-approve the ceilings they are checked against"
type = "story"
category = "todo"
priority = "medium"
points = 5
parent = "01M4FGWBHH3K9F2PPFYRGQ353T"
reporter = "lognd"
created = "2026-10-09T18:21:12Z"
updated = "2026-10-09T18:21:12Z"
labels = ["grimble", "adoption:logand-app"]
scope = ["crates/grimble*/**", "changelog.d/**"]

[[acceptance]]
text = "Given a commit that adds or widens a may grant (new atom, broader at selector, new node grant), when grimble check runs, then a finding names the grant change until grimble ack records an attester from the frob [evidence] attesters list (agents refused as with E-ATTEST-NOT-HUMAN); narrowing or removing a grant needs no ack"
bound = false
+++

Owner question 2026-10-09: is grimble a gate or an ever-expanding list of capabilities? logand evidence: grants are added in the same change as the code that needs them and nothing in the tool distinguishes a reviewed grant from a self-approved one; the one rejected grant (T-0425, wont-fix) was caught by process, not by grimble.
