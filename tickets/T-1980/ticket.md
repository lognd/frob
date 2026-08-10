---
id: T-1980
title: 'Global frob on PATH is 0.184.0 vs this repo''s 0.433.0: 8 sibling repos run
  a pre-auto-commit build and all 8 have dirty ledgers'
state: queued
kind: bug
origin: human
created: '2026-08-10'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- docs/guides/
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
The `frob` on PATH is 0.184.0. This repo's own build is 0.433.0 -- a
249-version gap. Every sibling repo invokes the PATH build, so 8 repos
are running frob from hundreds of releases ago.

MEASURED, 2026-08-10:
  which frob            -> /home/logan/.local/bin/frob
  frob --version        -> frob 0.184.0
  uv run frob --version -> frob 0.433.0
  frob ticket new --help | grep -- --no-commit  -> NO MATCH

That last line is the load-bearing one: the global build has no
`--no-commit` flag, so it predates T-1615's uniform auto-commit of
ledger writes. It therefore does NOT commit the ledger edits it makes.

OBSERVED CONSEQUENCE, found while scoping T-1971: ALL EIGHT frob-wired
sibling repos (typani, logand.app, lograder, aprog-private, graphite,
feldspar, aprog-public, lithos) currently have an uncommitted diff on
`tickets.md`. typani, for example, has an appended `T-0006` sitting
uncommitted. This is not eight coincidences -- it is the deterministic
result of a pre-T-1615 build writing the ledger and never committing it.

BLAST RADIUS BEYOND DIRTY TREES: every guard and fix landed in this repo
since 0.184.0 is simply absent in those 8 repos. That includes the
land-accounting work done TODAY -- T-1967 (land silently carrying a
sibling ticket's code), T-1950 (a ticket landing verified=True with an
empty commit), T-1922/T-1955 (branch-own-changed-files diff semantics) --
plus T-1615 auto-commit, the lease model, and the acceptance preflight.
Those repos have the old behavior in all of it.

IT ALSO BLOCKS REAL WORK: T-1971 (migrate siblings off the v1 ledger)
could not run its pilot because every candidate repo was dirty, and
T-1552 (critical) is blocked behind T-1971.

DO NOT FIX IT THIS WAY -- and this is why this ticket exists instead of a
one-line upgrade:
- Do NOT just run `uv tool upgrade frob` and assume it is safe. Those 8
  repos are on the V1 ledger and have never been checked against a
  0.433 gate set. Jumping 249 versions could surface a wall of new gate
  errors, or refuse operations those projects depend on, in EIGHT
  repositories at once, none of which are the subject of this drive.
  The upgrade is the likely right answer but it is an outward-facing
  change to the operator's global tooling and needs a deliberate, staged
  rollout, not a side effect of a ticket drain.
- Do NOT commit the dirty `tickets.md` files in the sibling repos to
  "clean them up". That content is someone else's in-flight work; it
  should be committed by whoever created it, or by the upgraded tool.

FIX DIRECTION:
(a) Decide and record the upgrade policy: pin the global build, or
    upgrade on a schedule, or make the repos use a per-repo build.
(b) Stage the upgrade -- upgrade the tool, then run `frob check` in ONE
    small sibling repo (typani, 6 tickets) and report the delta before
    touching the rest.
(c) Consider making the version-skew condition self-announcing at the
    repo level. A hook already detects it locally (it fired on exactly
    this command and reported both versions correctly) -- that detection
    should not be limited to one machine's hook config.

ACCEPTANCE: first test must FAIL before the fix -- assert that a
frob-wired repo running a PATH build older than the repo's own build is
reported, with both versions named. Then measure and report the
`frob check` delta for one upgraded sibling repo before any broader
rollout. Do not close this by upgrading alone; the deliverable is the
recorded policy plus a measured single-repo result.
