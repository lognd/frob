---
id: T-3359
title: 'Finalizing a T-draft id leaves its citations dangling: 240 draft-id references,
  some already producing CI-blocking DOC011 errors'
state: queued
kind: bug
origin: human
created: '2026-08-29'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_new_renumber.py
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
MEASURED 2026-08-29. A `T-draft-*` id that gets FINALIZED to a real `T-####`
on land leaves its citations behind, pointing at an id that no longer resolves.

    distinct T-draft-* ids referenced across tickets/, docs/, src/:  240

That count is REFERENCES, not confirmed-dangling references -- some of those
ids may belong to drafts genuinely still in flight, which is legitimate. The
first job of this ticket is to separate the two populations, and the number
that matters is the finalized-and-dangling subset. Do not treat 240 as the
defect count; measure it.

WHY THIS IS NOT COSMETIC:
  - It produces real CI-blocking errors. Series EH's gate:DOC triage found
    DOC011 x3 in `docs/guides/release.md` caused by exactly this: citations to
    `T-draft-13d00ebe`, which had been finalized as T-3337. Those three were
    part of the 188 self-gate errors gating the release.
  - It breaks traceability, which is the whole point of the ledger. A reader
    following a citation to understand why a waiver, a debt entry, or a doc
    paragraph exists hits an id that resolves to nothing, and has no way to
    discover the real ticket short of guessing.
  - It is silent. Nothing fails at finalize time; the stale citations simply
    persist, and only some of them happen to sit somewhere a doc gate looks.

HOW IT WAS FOUND, which shows the accrual is ongoing rather than historical:
three separate agent worktrees for ALREADY-LANDED tickets each independently
contained an uncommitted hand-edit doing this same retarget --

    t-3196   T-draft-e1bca269 -> T-3285   (3 done-report citations)
    t-3254   T-draft-13d00ebe -> T-3337   (2 citations in docs/guides/release.md)
    t-3065   an unrelated claim-line edit, not this class

Three agents hit the same problem, each fixed it by hand locally, and none of
those fixes reached main. That is the signature of a missing mechanism, not of
three careless agents.

WHAT TO BUILD:
  1. Separate live drafts from finalized-and-dangling. Report both counts.
  2. Retarget the dangling ones to the real id they became. The finalize path
     knows the mapping at the moment it renumbers -- the question is whether
     that mapping is recorded anywhere durable. Find out; if it is not, that is
     the deeper finding and worth saying.
  3. Prevent recurrence at the source: when a draft is finalized, either
     rewrite its inbound citations or record the draft->real mapping somewhere
     a gate can resolve through. Choose one and say why.
  4. A gate rule for a citation to a `T-draft-*` id that is neither live nor
     resolvable through the mapping. Without it this simply re-accrues.

DO NOT bulk-rewrite by regex across 240 sites. Some are legitimate live drafts,
some sit in archived done-reports that are historical records, and a blanket
substitution would corrupt both. This repo has already had one near-miss today
where a "mechanical, sed-fixable in one pass" framing rested on a line count
rather than a finding count.

DO NOT rewrite archived done-reports to fix their citations without deciding
that policy explicitly. T-3266 established that landed done-reports are
historical artifacts and are not to be bulk-edited; a dangling citation inside
one may be evidence of what happened rather than something to correct.

MUST-FIRE FIXTURE: a citation to a finalized draft id is flagged.
MUST-STAY-QUIET FIXTURE: a citation to a genuinely live in-flight draft is not.
THIRD FIXTURE: finalizing a draft leaves no dangling inbound citation.

ACCEPTANCE
- Both counts stated (live vs finalized-and-dangling).
- The dangling set retargeted, with the archived-report policy decided and
  stated rather than assumed.
- A recurrence-prevention mechanism at finalize time.
- All three fixtures present.
