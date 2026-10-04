+++
id = "01M1T07NWK81XW0XJB4F7RBEX4"
title = "cmd: evidence: reproducibility hardening (cwd, re-run, empty-output)"
type = "security"
category = "todo"
priority = "low"
parent = "01M1T07NWGXQV249M3HN5DQV9V"
reporter = "agent"
created = "2026-09-06T00:00:00Z"
updated = "2026-10-04T22:22:21Z"
aliases = ["T-3987"]
labels = ["v1-cluster:B4", "triage:accepted"]
scope = ["src/frob/tickets/_evidence.py"]

[[acceptance]]
text = "given a cmd: evidence entry with an absolute path outside the repo as cwd, when it is registered, then it is refused"
bound = false

[[acceptance]]
text = "given a cmd: evidence entry, when a ticket closes or lands, then the command is re-run or explicitly reported as claimed-not-reproduced rather than silently trusted"
bound = false

[[acceptance]]
text = "given a cmd: evidence command that produces no output at all, when it runs, then the empty-output digest is flagged"
bound = false
+++

F-198 (T-3984 item 3). VERIFIED: src/frob/tickets/_evidence.py is the cmd: evidence channel implementation; --check-repro already exists (per this repo's own "check-repro is pre-land only" lesson) but is pre-land only, and is a different check than what this item asks for.

FINDING THIS WOULD HAVE CAUGHT: a cmd: evidence citation whose command was never actually re-run against the current tree at the moments that matter (ticket close, land) -- it is trusted as "claimed" evidence indefinitely. Proposed hardening, four parts:
1. cmd: evidence must carry a repo-relative cwd (no absolute paths escaping the repo -- refuse them outright).
2. The command is re-run (or explicitly reported as "claimed, not reproduced" if genuinely not re-run) at close and at land, not only pre-land via --check-repro.
3. An empty-output digest (a command that produces no stdout/stderr at all) is flagged rather than silently accepted as a pass.
4. This is itself a subject-count instance (T-3985): "claimed but never reproduced" is exactly a zero-subjects-examined state for the evidence-verification gate.
