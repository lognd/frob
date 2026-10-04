+++
id = "01M38BCPBJWFBPWT4Z5M2GNPBY"
title = "register src/frob/agent as a cli-owned module glob in design/frob.strata"
type = "docs"
category = "done"
outcome = "wont-fix"
priority = "medium"
reporter = "human"
created = "2026-09-24T00:00:00Z"
updated = "2026-10-04T21:02:55Z"
aliases = ["T-6514"]
labels = ["v1-cluster:B3d"]
scope = ["design/frob.strata"]
+++

found while working T-draft-df99eb2d: frob.agent (src/frob/agent/_brief.py, new) is not covered by any design/frob.strata code owner, so SYS003 fires (undeclared cross-component import frob.agent) at its two import sites (src/frob/app/agent_runner.py, tests/unit/agent/test_brief.py). The fix is a one-line addition of "src/frob/agent/**" to the cli node's existing code glob list (design/frob.strata, node cli, the code clause around its 'src/frob/app/**' entry) so frob.agent becomes an intra-component module of cli, matching agent_runner.py's own existing membership -- no new Flow/component needed. Could not do this within T-draft-df99eb2d itself: design/frob.strata was under an active cross-worktree lease held by T-draft-4ad886c1 (frob coord status) at the time, which also touches this same file for its own new frob.coord component -- sequence after that lease clears. T-draft-df99eb2d carries an interim frob:waive SYS003 citing this ticket at both import sites.
