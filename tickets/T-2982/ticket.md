---
id: T-2982
title: 'frob.gh_io: a typed GitHub/CI seam with named failure modes, structured failure
  reporting, and CI-result validity'
state: queued
kind: feature
origin: human
created: '2026-08-26'
priority: high
parent: null
tier: epic
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: tier
  old_value: ticket
  new_value: epic
  reason: 'T-2982 decomposition: seam, reporting, validity'
  actor: logan
  at: '2026-08-26'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
frob has no GitHub/CI seam at all -- `git grep` for gh invocations across
`src/frob/` returns ZERO hits. Every interaction with CI in this drive was
hand-rolled by an operator or an agent shelling out to `gh run list`,
`gh run view --job`, `gh run view --log-failed`, and `gh api .../logs`, then
eyeballing or grepping the output.

That cost real time and produced real errors this session:

- Reading job status meant three separate `gh` calls and manual correlation of
  run id -> job id -> step.
- `gh run view --job <id> --log-failed` returned EMPTY for a job that had
  genuinely failed, and a follow-up `--log | grep` returned nothing either, so
  the actual Windows Typecheck error could not be extracted at all and had to
  be deferred to a ticket.
- An agent pulled 156 macOS failure node ids out of a raw job log via
  `gh api .../logs` and hand-clustered them.
- A ~100-failure cluster was mis-attributed as macOS-specific for an entire
  investigation because the ubuntu job had been cancelled mid-run and nothing
  surfaced that fact.

THE SHAPE: a `frob.gh_io` module mirroring the discipline `frob.gitio` already
establishes for git (typed, Result-returning, every fallible operation a value
rather than an exception), plus a thin command surface over it.

PART 1 -- the seam and its failure modes. `gh_io` must treat every one of these
as a TYPED, NAMED error, never a crash and never a silent empty result:
  - `gh` not installed / not on PATH
  - not authenticated (`gh auth status` failing), and expired credentials
  - no GitHub remote / not a GitHub repo (frob must stay useful off-GitHub --
    this is the same portability doctrine as PLATFORM001)
  - rate limited, and network unreachable
  - run/job id not found, or log retrieval returning EMPTY for a job that did
    fail (measured above -- this is a real, reproducible mode, not theoretical)
An empty log MUST be distinguishable from a clean log. That is the silent-zero
class this repo has spent the whole drive eliminating: unmeasured must never
render as nothing-to-report.

PART 2 -- structured CI reporting, so no one greps raw logs again. Parse runs,
jobs, steps and failures into typed records: which job, which step, which test
node ids failed, clustered by failure signature. The operator asks "what is
failing" and gets an answer, not a log dump.

PART 3 -- CI RESULT VALIDITY, which is the part with the most leverage and the
part that is genuinely novel here. A CI run is evidence about ONE commit. The
moment code changes, some of that evidence goes stale -- but today nothing says
which parts. Wanted: for a given CI result, classify each test outcome as
  - STILL VALID: no commit since that run touched code reaching this test, so
    the result stands;
  - STALE: something since changed code this test covers, so the result is
    UNMEASURED for the current tree -- explicitly not "passing";
  - UNKNOWN: reachability could not be determined, stated as such.
frob already owns the substrate for this: `src/frob/graph/affects.py`, the
symbol-level digests, and the rolling-baseline/watermark machinery that
`frob verify` uses for exactly this class of question. This should reuse those,
not invent a parallel notion of freshness.

The doctrine to follow is the one already enforced elsewhere in this repo: a
stale result must announce itself. `frob verify` already refuses to attribute
against a stale baseline (T-2929), and gate results render UNRES rather than
`pass` when unmeasured (T-2891). A CI result whose code has changed underneath
it must be reported the same way -- never as a green tick.

CONSTRAINTS
  - Machine output (`--json`) byte-stable; TTY output legible.
  - Must degrade gracefully with no `gh`, no auth, and no GitHub remote. frob is
    meant to be transferable to other projects and not all of them live on
    GitHub.
  - Do not shell out to `gh` from scattered call sites. One seam, the way
    `gitio` is one seam.
  - Never cache a CI verdict in a way that can outlive its validity without
    saying so.
