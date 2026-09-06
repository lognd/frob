---
id: T-4005
title: 'F-220: land-time RENDER001 fired on a consumer script, a frob:waive did not
  suppress it, and a rename made it vanish (unexplained)'
state: queued
kind: bug
origin: human
created: '2026-09-06'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_land_cmd.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Consumer logand.app-v2 F-220, 2026-09-06. THREE DISTINCT SUB-FINDINGS in one
report. Only the first may already be fixed; the other two are independent and
are the reason this ticket exists.

SUB-FINDING 1: RENDER001 FIRED ON A CONSUMER-REPO SCRIPT AT LAND TIME.
`frob ticket land --dry-run` refused with "scripts/frob_version.py:47 new
RENDER001 finding". They correctly read frob's OWN docs/modules/render.md and
noted RENDER001 is scoped to src/frob/**, .claude/hooks/**, and the single named
scripts/fleet_status.py -- "not every script that happens to live in this
repository".

THIS IS PROBABLY T-3940, WHICH LANDED TODAY (f67f5ad8f). That ticket fixed
exactly this: the land-time `_render001_checker` reused RENDER001's DETECTOR but
not its PATHSPEC, filtering only on `rel_path.endswith(".py")`, so it scanned
every python file in any repo. The consumer is on an installed 0.530.0, which
(see T-4001) can be different software from main's 0.530.0. RULE THIS IN OR OUT
FIRST by reproducing against a build containing f67f5ad8f.

BUT DO NOT CLOSE ON THAT ALONE -- THEIR CONTROLLED EXPERIMENT IS UNEXPLAINED BY
IT. They renamed scripts/frob_version.py to scripts/pinned_frob_version.py, with
NO OTHER CHANGE, and the finding disappeared. Under the pre-T-3940 code the
filter was `endswith(".py")`, which both names satisfy equally, so a rename
should have changed nothing. I traced the current membership test
(`render001_scans` -> `rel_path in _tracked_python_files(root)`, an exact-set
membership over `git ls-files <pathspec>` for src/frob, .claude/hooks and
scripts/fleet_status.py) and it does not explain a basename-sensitive result
either -- and in a consumer repo with no src/frob at all that set is nearly
empty. I CANNOT ACCOUNT FOR THE RENAME RESULT FROM HERE, and it is a clean
controlled experiment, so it must be reproduced rather than explained away. If
some path derives a scan set from a name containing "frob", that is a separate
and worse bug than the one T-3940 fixed.

SUB-FINDING 2: A frob:waive DID NOT SUPPRESS THE LAND-TIME FINDING. They placed
`frob:waive RENDER001 reason=... follow_up="T-0024"` above the function and the
land still refused. Their reading of the error text ("not relaxed by the rapid
profile") is that the does-not-worsen-at-land check ignores waivers for this
rule. IF TRUE THIS IS A NO-EXIT and is independent of sub-finding 1: the rule
fires, the documented escape hatch does not work, and the only remedy left was
renaming a file. VERIFY WHETHER THE LAND-TIME DIFF CHECK CONSULTS WAIVERS AT ALL
-- for RENDER001 or for any rule. If it does not, that is a general defect
affecting every file-local land check, not a RENDER001 quirk.

SUB-FINDING 3: RENDER001 IS INVISIBLE UNTIL LAND. They ran `frob check --only
gates-fast` and `--only sys` in the same worktree and both came back clean;
render_lint is surfaced by neither, only by the full check at land time. So the
first notice of a land-blocking finding arrives at the moment of landing. That is
the "gate arrives at the moment of finishing rather than the moment of writing"
class already recorded on T-3939, T-3950 and T-3951 -- this is its fourth
instance. It also touches T-3995 (a known `--only` stage name does not actually
filter as documented); check whether these are the same defect before fixing
either.

MUST-FIRE FIXTURE: a bare print inside src/frob/ still refuses the land.
MUST-STAY-QUIET: (a) a consumer-shaped repo with no src/frob never fires
RENDER001 at land, for ANY filename -- including one containing "frob"; (b) a
correctly-placed frob:waive suppresses a land-time finding.
THIRD FIXTURE: renaming a file does not change whether a rule fires on it.

ACCEPTANCE
- Sub-finding 1 ruled in or out against a build containing f67f5ad8f.
- The rename experiment REPRODUCED and explained, not assumed stale.
- Whether the land-time diff check consults waivers, answered for all rules.
- The pre-land visibility gap addressed or explicitly deferred with a reason.
- All fixtures committed.