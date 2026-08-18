---
id: T-2350
title: TICK006 auto-filer twice cited a real, just-filed sibling ticket as phantom
  (possible stale ledger read at land time)
state: dropped
kind: bug
origin: human
created: '2026-08-17'
priority: low
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/_land_cmd.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
attachments:
- path: T-2350/attachments/01-diagnosis-timing-visibility-race-not-identity-matching-both-candidate-fix-files-leased-by-t-2351-no-edit-attempted.md
  caption: 'diagnosis: timing/visibility race, not identity-matching; both candidate
    fix files leased by T-2351, no edit attempted'
  sha256: b3a7b8213809ef02953e6b71c57a160caf80ba3cfa2def601a6255867de200f9
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 56f4c2209992b106c6da563c762ab359405b0d20
---
Observed twice in one session, both self-resolved as duplicates but
worth tracking as a pattern: TICK006's Tier-A auto-filer ("Recovered
from <ticket>'s phantom TICK006 citation of <cited-id>") fired against a
citation that WAS a real, existing, queued ticket at land time:

- T-2343: claimed T-2313's Done report cited a phantom
  "T-draft-2e335e20" -- but that was a stray draft I had already deleted
  from the worktree before landing (a separate leftover from an earlier
  FAILED land attempt, not a live citation in the final Done report body
  TICK006 should have checked).
- T-2349: claimed T-2313's Done report cited a phantom "T-2345" -- but
  T-2345 was a real ticket, filed moments before this land ran (visible
  in tickets/T-2345/ticket.md, state=queued, verified directly).

Both were dropped as duplicates/false-positives by hand. The T-2349 case
in particular suggests TICK006's own ledger read at land time may be
racing a JUST-created sibling ticket -- filed via `frob ticket new`
seconds before the citing ticket's land, in the same worktree session,
but possibly not yet visible to whatever ledger snapshot TICK006's
citation-resolution step reads.

WANTED: investigate whether TICK006's citation check reads a stale/
cached ledger view during land, and if so, whether it should re-read
fresh immediately before firing (the same class of staleness this
session's design/frob.strata lease-collision investigation, T-2328,
already found in a DIFFERENT Tier-A check -- worth checking if there is
a shared stale-read helper between the two). Not filed as high priority
-- both observed instances were self-resolving false positives, not
silent data loss -- but the pattern recurring on the very next land
after the first instance is enough to track.

## Drop reason
- 2026-08-17: Measured on current main (T-2351 landed, 4d1f69916): reproduced the flagged mechanism (disqualified Tier-A revert of tickets.md wiping an uncommitted just-filed ticket line) directly -- it now SURVIVES. Existing regression test_uncommitted_in_scope_edit_survives_a_disqualified_tier_a_revert (1 passed) covers the identical generic code path. Cannot reproduce a phantom TICK006 citation via this mechanism. See attachment for full repro. T-2351 already closed this.
