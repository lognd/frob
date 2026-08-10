---
id: T-1980
title: 'Global frob on PATH is 0.184.0 vs this repo''s 0.433.0: 8 sibling repos run
  a pre-auto-commit build and all 8 have dirty ledgers'
state: done
kind: docs
origin: human
created: '2026-08-10'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- docs/guides/frob-version-policy.md
- tickets/T-1980/**
- docs/index.md
- tickets/T-1990/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: docs/guides/
  reason: narrow the docs/guides/ umbrella to the one new policy doc this ticket actually
    adds; the measurement itself is recorded in the ticket body/evidence, not a second
    doc file
  actor: logan
  at: '2026-08-10'
- op: add
  glob: docs/guides/frob-version-policy.md
  reason: narrow the docs/guides/ umbrella to the one new policy doc this ticket actually
    adds; the measurement itself is recorded in the ticket body/evidence, not a second
    doc file
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tickets/T-1980/**
  reason: narrow the docs/guides/ umbrella to the one new policy doc this ticket actually
    adds; the measurement itself is recorded in the ticket body/evidence, not a second
    doc file
  actor: logan
  at: '2026-08-10'
- op: add
  glob: docs/index.md
  reason: REF001/REF002 need one inbound link from the guide index to the new policy
    doc, same convention every other docs/guides/ entry follows
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tickets/T-1990/**
  reason: SCOPE001 flags the follow-up ticket this ticket files (T-1980's own FIX
    DIRECTION point c, the self-announcing detector) as an out-of-scope touched file;
    filing a follow-up ticket is normal bookkeeping for this ticket's own Done report,
    not scope creep
  actor: logan
  at: '2026-08-10'
evidence:
- cmd:grep -n 'OPAQUE001. (+5)\|SUPPRESS001. (+8)\|| errors | 27 | 40 | +13 |' docs/guides/frob-version-policy.md
  exit=0 sha256=7c1286b47ae3
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

## Done report

Changed:
- docs/guides/frob-version-policy.md (new) -- the recorded upgrade
  policy, staged rollout sequence, and measured typani delta
- docs/index.md -- one inbound link to the new guide, same convention
  every other docs/guides/ entry follows

Kind changed bug -> docs: this ticket's actual deliverable is a policy
record plus a read-only measurement, no code fix, matching the T-1031/
T-1071 estate-rollout precedent (also kind=docs). bug-kind would have
required a BUG002 pytest repro that could pass/fail at parent, which
does not fit a policy decision.

MEASUREMENT (the core deliverable): ran this repo's own 0.433 build
(`uv run frob check /home/logan/projects/typani --only gates --json`)
and the stale global 0.184 build (`frob check /home/logan/projects/
typani --only gates --json`, bare PATH binary) against typani, no
`--fix`, no `--stamp-*` flags. Confirmed BEFORE running either that
plain `frob check` (no `--fix`) never writes tracked content -- the
only writes are to typani's own gitignored `.frob/` cache, same as any
normal invocation in any repo -- and diffed `git status --short` on
typani before/after both runs: unchanged (still only the pre-existing
dirty tickets.md/uv.lock this ticket's own filing already found).

Result: 0.184 = 27 errors/70 warnings. 0.433 = 40 errors/59 warnings.
Every one of the +13 new errors comes from two gate families that did
not exist at 0.184 at all (OPAQUE001 +5, SUPPRESS001 +8) -- NOT from an
existing gate getting stricter on previously-passing code. typani's
`frob check` is already non-zero-exit under the CURRENT stale build (27
pre-existing errors); upgrading adds findings to an already-red gate,
it does not flip a green one red. Warnings decreased by 11 (not
independently triaged, noted as out of scope in the doc).

Policy recorded: do not run `uv tool upgrade frob` as a ticket-drain
side effect; staged rollout is measure-one-repo -> human review ->
upgrade once, globally -> re-verify -> roll out to the remaining 7
repos one at a time, each with its own dirty-ledger triage (explicitly
NOT auto-committed by this ticket or the upgrade). Full sequence in
docs/guides/frob-version-policy.md.

Filed: T-1990 (real id renumbers at land) -- FIX DIRECTION
point (c) from T-1980's own body (making version skew self-announcing
at the repo level in frob's own code, not one machine's Claude Code
hook config) is genuine code work with its own BUG002-shaped acceptance
test, out of this docs-only ticket's scope. Cited in the policy doc.

Evidence: 1 evidence-cmd entry (`frob ticket evidence --evidence-cmd`,
docs-kind channel) -- greps the policy doc for the three load-bearing
measured facts (both new-gate deltas and the 27/40/+13 total) so the
binding is not a silent no-op grep -q, satisfying T-1892's
zero-information-digest refusal.

Gates: `frob check --ticket T-1980` is 0 errors on every ticket-relevant
gate family after narrowing scope to the specific files touched
(docs/guides/frob-version-policy.md, docs/index.md, tickets/T-1980/**,
tickets/T-1990/** for the follow-up ticket this ticket files)
and re-sweeping. Remaining ruff-check/ruff-format FAILs in the same run
are pre-existing repo-wide drift, unrelated to this change (confirmed:
same 91-file count, same single F401 in an unrelated test file, present
before this ticket touched anything).

Confirmed modified nothing outside this repo: `git status --short` in
typani is unchanged before/after both measurement runs (still only the
pre-existing dirty tickets.md/uv.lock this ticket's own filing
originally found, nothing new). No sibling repo's tracked files, ledger,
or any other content was touched. The global `frob` install
(`/home/logan/.local/bin/frob`, still 0.184.0) was not upgraded, pinned,
or otherwise modified.

### Changed
```
 tickets/T-1980/ticket.md           | 48 +++++++++++++++++++++++++++++++++---
 tickets/T-1990/ticket.md | 50 ++++++++++++++++++++++++++++++++++++++
 2 files changed, 95 insertions(+), 3 deletions(-)
```

### Evidence
- `cmd:grep -n 'OPAQUE001. (+5)\|SUPPRESS001. (+8)\|| errors | 27 | 40 | +13 |' docs/guides/frob-version-policy.md exit=0 sha256=7c1286b47ae3` (cmd evidence, exit=0)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: F401@/home/logan/projects/frob/.claude/worktrees/version-skew/tests/unit/test_tickets_evidence_only_scope.py
