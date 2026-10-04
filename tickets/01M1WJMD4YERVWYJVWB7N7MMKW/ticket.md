+++
id = "01M1WJMD4YERVWYJVWB7N7MMKW"
title = "DRIFT/COV: symbols sharing one frob:doc anchor are one contract -- a ticket touching one should reopen review of all"
type = "task"
category = "done"
outcome = "done"
priority = "high"
parent = "01M1WJMD2PECRZNJSZ2ZEZ45SB"
reporter = "agent"
created = "2026-09-07T00:00:00Z"
updated = "2026-09-07T00:00:02Z"
aliases = ["T-4254"]
scope = ["src/frob/gates/_docblocks_refs.py"]

[[acceptance]]
text = "frob:doc edges sharing the same anchor are grouped into one contract (_shared_doc_anchor_groups), ignoring anchors with only one participant symbol"
bound = false

[[acceptance]]
text = "cov009_violations warns on every untouched sibling in a group once the diff touches at least one other sibling's own line span, and stays silent when the diff touches none or all of them"
bound = false
+++

Consumer F-386 item 4 (T-4182, shell round-5): a shared contract's fix and its miss landed in two different tickets' scopes because frob has no notion that these call sites implement one contract; the frob:doc edges all point at the same anchor, which is the right hook -- a DRIFT/COV rule keyed on symbols sharing one frob:doc anchor could treat that anchor as a single obligation, so touching one participant flags the others for review. Adjacent to T-4252 (AFFECT-style sibling-signature check) -- distinct mechanism (this is anchor-based grouping across possibly-different files/shapes; T-4252 is same-module sibling-signature matching) but both close the same class of gap. Fixture-testable: YES, frob's own frob:doc anchors.
