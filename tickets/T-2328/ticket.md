---
id: T-2328
title: frob ticket land silently discarded T-2194's in-scope design/frob.strata edit
  under a stale/already-cleared lease collision
state: queued
kind: bug
origin: human
created: '2026-08-17'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_land.py
- src/frob/app/ticket_runner/_land_cmd.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
attachments:
- path: T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md
  caption: second live reproduction (T-2329's own land) + root-cause narrowing
  sha256: 4aa18accafecb3a575c5c162b99a3c736c516c9c9b359db67b51f58e420d90d1
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-2194's own declared scope included `design/frob.strata` -- it added a
`may "exec"`/`may "fs.read"` capability grant for
`tests/unit/test_lang_strata.py` (the new corpus-wide regression test
needs `subprocess.run` for `git ls-files '*.strata'` and `.read_text()`
to load each file). That edit was made, verified locally (ran the new
test against it, confirmed pass/fail behavior), and was present on disk
in the T-2194 worktree right up to the pre-land WIP snapshot step.

`frob ticket land T-2194` logged, repeatedly, during its Tier-A pass:
"WARNING: tier-a fixes: SKIPPED SYS100 design/frob.strata:0 --
design/frob.strata is under T-2303's live lease" -- and the resulting
"wip: pre-land snapshot for T-2194" commit (d21e0fcd4) contains ONLY
`tests/unit/test_lang_strata.py`, not `design/frob.strata` at all. The
file was silently reset back to main's content somewhere in land's
pipeline -- not merely skipped-and-reported, actually discarded with no
error, no refusal, and no line in the land output naming
`design/frob.strata` as a dropped in-scope change (only the Tier-A
AUTO-FIX skip warning appeared, which reads as "land's own sync fixer
didn't touch this file", not "your own edit to this file is being
thrown away").

Confirmed consequence on main after the land (commit
230828040a32f2cfa430472caf98f6102ba63134): `design/frob.strata` has
ZERO `may` grants for `tests/unit/test_lang_strata.py` beyond a
pre-existing `fs.write` entry -- the `exec`/`fs.read` grants T-2194 added
are entirely absent. `frob check --only gates-security` on main now logs
(not yet gated as an error, but a real, measured drift):

  WARNING: strata effects: undeclared capability effect
  tests/unit/test_lang_strata.py:423 exec (subprocess.) on testsuite
  WARNING: strata effects: undeclared capability effect
  tests/unit/test_lang_strata.py:439 fs.read (read_text() on testsuite

Timeline note: by the time T-2194's land actually ran (commit
timestamps ~2026-08-18T00:05-00:07 UTC), T-2303's OWN cross-worktree
lease file (`.git/frob-leases/T-2303.json`) already showed
`"scope": []`, `recorded_at` 2026-08-17T23:45:32 UTC -- i.e. ~20 minutes
BEFORE the land ran. Either the collision check land actually used was
stale/cached, or there was a narrower timing window this session's own
retries did not observe directly; this ticket's scope is diagnosing
which.

WANTED:
1. Root-cause why `frob ticket land`'s in-scope-file handling under a
   (possibly already-stale) cross-worktree lease collision resulted in
   silent content loss rather than either (a) a hard refusal naming the
   file, or (b) proceeding with the file since the lease was in fact
   already clear.
2. Whatever the mechanism, a genuinely in-scope file's own worktree edit
   must never be silently discarded by `land` -- either land refuses
   loudly and leaves the ticket unlanded, or it correctly detects the
   lease is stale/cleared and carries the change through. Silent data
   loss on a successful, `verified=True` land is the failure mode to
   fix, matching the class of defect T-2286 fixed for
   `reclaim_orphaned_squash_residue`.

Filed by T-2194's own Done report/implementer session as a direct,
observed consequence -- not speculative.
