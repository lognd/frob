---
id: T-3885
title: 'a land in another repository blocks this one''s ledger writes: the T-1619
  process scan matches any frob ticket land, ignoring its target repo'
state: in-progress
kind: bug
origin: human
created: '2026-09-05'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_leases.py
- tests/test_ticket_leases.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_leases.py
  reason: cross-repo/self-deadlock process-scan fix lives in this module and its own
    test file
  actor: logan
  at: '2026-09-09'
- op: add
  glob: tests/test_ticket_leases.py
  reason: cross-repo/self-deadlock process-scan fix lives in this module and its own
    test file
  actor: logan
  at: '2026-09-09'
body_changes:
- mode: append
  reason: 'F-098: the same T-1619 scan also matches the lands own child pid, a self-deadlock;
    the marker-based fix already specified solves both over-matches'
  actor: logan
  at: '2026-09-05'
  old_length: 4291
  new_length: 6765
- mode: set
  reason: 'converts this ticket from reasoning to measurement: caught a live land
    whose working directory and worktree argument both name another repository being
    reported as an in-flight land of this one. Adds the id-collision fact -- this
    repo has its own archived ticket with the same number -- which turns the false
    positive into a false but resolvable explanation, and separates the confirmed
    detection defect from the unconfirmed blocking claim'
  actor: logan
  at: '2026-09-07'
  old_length: 6765
  new_length: 9879
evidence:
- tests/test_ticket_leases.py::TestRefuseIfLandInProgress::test_a_land_targeting_a_different_repo_does_not_block_this_one
- tests/test_ticket_leases.py::TestRefuseIfLandInProgress::test_a_land_does_not_block_on_its_own_descendant
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
A `frob ticket land` running against a DIFFERENT REPOSITORY blocks ledger writes
in this one. T-1619's belt-and-braces process scan matches any `frob ticket
land` process on the machine, without checking which repository it targets.

MEASURED 2026-09-05, directly, in this repo:

    frob ticket new ...
      -> ERROR: ticket new: refused -- LandInProgress: a land is in progress
         for this repository; retry after it completes

    scripts/fleet_status.py, run in /home/logan/projects/frob:
      LANDS IN FLIGHT: 2
        T-0004  pids=1095675  elapsed=86s cpu=3s
        T-3843  pids=1022878,...

    but T-0004 does not exist in this repo (`ls tickets/T-0004` -> absent), and
    the process is:

      /proc/1095675/cmdline
        frob ticket land T-0004
          --worktree /home/logan/projects/logand.app-v2/.claude/worktrees/sub-01
          --allow-cross-ticket
      /proc/1095675/cwd
        /home/logan/projects/logand.app-v2

So a land in ../logand.app-v2 was reported as "a land is in progress FOR THIS
REPOSITORY" and refused writes to frob's ledger. The message is not merely
imprecise; it asserts something false.

IMPACT, MEASURED RATHER THAN ESTIMATED. This blocked four consecutive
`frob ticket new` invocations here over roughly fifteen minutes, including the
attempt to file the ticket describing the very defect. Any machine running frob
in more than one checkout -- which is the normal state for this developer, with
five sibling repos and peer sessions active in each -- has every repo's ledger
gated on every other repo's slowest land.

IT COMPOSES BADLY WITH A KNOWN BLOCKER. logand.app-v2 F-043 reports a land that
SPINS for 45 minutes on an unmeasurable verify. Under this defect, one repo
stuck in that loop freezes ledger writes in every other checkout on the box for
the duration. The two together turn a single stuck land into a machine-wide
outage.

WHY THE SCAN EXISTS, so the fix does not remove the protection. T-1619 added it
as a belt-and-braces check because the land lock alone was insufficient: a land
can be mid-ledger-splice while its flock is not currently held, and a concurrent
ledger write in that window corrupts the splice. That reasoning is sound and
must survive. The bug is the MATCHING PREDICATE, not the existence of the scan.

THE FIX: match on the TARGET REPOSITORY, not on the process name.
  - A land process already knows its root. Determine the candidate process's
    target repo and compare it to ours before treating it as blocking. Options
    in rough order of robustness: read the `--worktree`/`--path` argument from
    the cmdline and resolve it to a repo root; compare `/proc/<pid>/cwd`;
    or -- best -- have the land itself record its target root in the status
    marker that already exists (the `LAND STATUS MARKER` line proves such a
    marker is already written), and scan that instead of cmdlines.
  - Prefer the marker. Parsing another process's argv is fragile and will break
    on the next flag rename; a marker the land writes about itself is
    authoritative.

CHECK fleet_status.py TOO. It reported the foreign land under this repo's
"LANDS IN FLIGHT", so it shares the predicate or has its own copy of it. Both
must be fixed, and if they duplicate the logic, that duplication is itself worth
removing -- two copies of a rule is how they desync.

DO NOT fix this by dropping the process scan and relying on the flock. That
reintroduces exactly the window T-1619 closed.

INCIDENTAL OBSERVATION, not this ticket's business but worth recording: the
blocking process used `--allow-cross-ticket`. That flag carries a sibling's work
to main and strands it; whoever is driving that repo should know.

MUST-FIRE FIXTURES:
  - a land targeting THIS repo still blocks a concurrent ledger write here
  - the status-marker/lock path still refuses a write during a real splice
MUST-STAY-QUIET:
  - a land targeting a DIFFERENT repo root does not block writes here, and does
    not appear in this repo's LANDS IN FLIGHT

ACCEPTANCE
- Matching is by resolved target repo root, ideally via a marker the land writes
  about itself rather than by parsing argv.
- fleet_status.py's listing corrected, and any duplicated predicate unified.
- The T-1619 protection demonstrably intact via the must-fire fixtures.



SECOND DEFECT IN THE SAME SCAN, 2026-09-05. logand.app-v2 F-098: "a land can
block on its own process: the T-1619 belt-and-braces scan finds the land's own
child pid".

So T-1619's process scan has at least TWO independent over-match failures, and
they share a fix site:

  (a) NO TARGET-REPO FILTER (this ticket's original finding). A
      `frob ticket land` running against a DIFFERENT repository blocks ledger
      writes here. Measured: pid 1095675, cmdline naming
      ../logand.app-v2/.claude/worktrees/sub-01, cwd
      /home/logan/projects/logand.app-v2 -- reported as "a land is in progress
      for THIS repository".

  (b) NO SELF/DESCENDANT EXCLUSION (F-098). The scan finds the land's OWN child
      pid and the land blocks on itself.

(b) IS THE WORSE OF THE TWO, because it is a SELF-DEADLOCK: retrying cannot
help, since every attempt recreates the process it trips over. (a) at least
clears when the other repo's land finishes.

CORROBORATING OBSERVATION FROM THIS REPO: fleet_status reports MULTIPLE PIDS PER
LAND -- e.g. "T-3843 pids=1022878,1022880,1022884" and "T-3857
pids=2476745,...". So a land genuinely is a process TREE, and any scan matching
on command shape will find the descendants of the very land asking the question.
That is not an edge case; it is the normal structure of every land.

THIS STRENGTHENS THE FIX ALREADY SPECIFIED and narrows it. The original body
asks for matching on the resolved TARGET REPO rather than the process name,
preferably via a marker the land writes about itself. That marker approach
solves (b) as well, and more cleanly than a pid-exclusion list: if a land
records its own identity, the scan can ask "is there a land for THIS repo whose
identity is not mine" rather than "is there any process that looks like a land".
Pid-based self-exclusion would still be fooled by grandchildren and by pid
reuse -- which this repo already warns about elsewhere ("the recorded pid may be
reused, do not trust it or lock age").

ADD TO THE FIXTURES:
  MUST-STAY-QUIET: a land in progress does not block ITSELF, and does not block
                   on its own descendants.
  MUST-FIRE:       a DIFFERENT land targeting this repo still blocks (the
                   T-1619 protection must survive both fixes).

DO NOT fix (b) alone by excluding the current pid. The measured process trees
show three pids per land, so a naive self-check would still trip on siblings and
children. Fix the predicate, not the symptom.

CONFIRMED LIVE, 2026-09-07, WITH THE PROCESS STILL RUNNING. This ticket was filed
on reasoning; here is the measurement.

This repository's fleet status reported:

    LANDS IN FLIGHT: 1
      T-0412 pids=2075447 elapsed=326s

I inspected the process before it exited:

    /proc/2075447/cwd      -> /home/logan/projects/logand.app-v2
    /proc/2075447/cmdline  -> frob ticket land T-0412 --worktree
                              /home/logan/projects/logand.app-v2/.claude/worktrees

So a land running entirely inside ANOTHER REPOSITORY is reported as an in-flight
land of THIS one. The process scan matches on the command shape and does not
constrain by working directory or by the worktree path the command itself names
-- and that path names the other repository explicitly, so the information needed
to reject the match was present in the matched string.

A SECOND FACT THAT MAKES THIS WORSE AND WAS NOT IN THE ORIGINAL REPORT: TICKET
IDS COLLIDE ACROSS REPOSITORIES. This repository has its own archived T-0412.
Their live T-0412 is a different ticket in a different queue. So a cross-repo
match does not merely produce a spurious "a land is running" -- it produces one
attributed to a REAL, RESOLVABLE id here, which a reader can look up and be
misled by. Anyone diagnosing this would find an archived ticket and reasonably
conclude something had gone wrong with it.

I ALSO SAW THIS EARLIER TODAY AND COULD NOT CONFIRM IT. A fleet status hours ago
reported an in-flight land for another consumer-shaped id; by the time I inspected
the process it had exited, and I recorded that I had no evidence either way rather
than asserting a cross-repo match. This is that same phenomenon, caught while
live.

WHAT THIS TICKET SHOULD NOW REQUIRE
  1. Constrain the scan by repository. The worktree path is already in the matched
     command line, and the process working directory is available -- either is
     sufficient. Prefer checking both, since a land can legitimately run with a
     working directory outside the repo it targets.
  2. Do not resolve a matched ticket id against THIS repository's ledger without
     first establishing the process belongs to this repository. The id collision
     above turns a false positive into a false, plausible-looking explanation.
  3. Re-check what this scan GATES. If a cross-repo land can make a ledger verb
     here refuse with a land-in-progress error, then one repository's work can
     block another's, which is the title of this ticket and now has a confirmed
     mechanism behind it. Establish that by test rather than by inference -- I
     have confirmed the DETECTION is cross-repo, not the blocking.

MUST-FIRE FIXTURE:   a land running in another repository is not reported as an
                     in-flight land of this one.
MUST-STAY-QUIET:     a land running in THIS repository is still detected, including
                     when its working directory differs from the repo root.
THIRD FIXTURE:       a matched ticket id is not resolved against this repository's
                     ledger unless the process is established to belong here.
