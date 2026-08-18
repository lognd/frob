---
id: T-2361
title: 'Profile-collapse: migrate the 5 if-rapid call sites onto LandProfileSettings'
state: queued
kind: feature
origin: human
created: '2026-08-17'
priority: medium
parent: T-1696
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_land.py
- src/frob/app/ticket_runner/_land_cmd.py
- src/frob/tickets/_evidence.py
- src/frob/app/ticket_runner/_close_cmd.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: tickets
anchor: false
anchor_reason: null
land_commit: null
---
Split from T-1696 (queue-depth-dial collapse epic), second leaf --
BLOCKED on the settings-resolver child (files the settings record this
ticket migrates callers onto).

Migrate the 5 live ProfileName branch sites (measured 2026-08-17, see
the settings-resolver child for exact line numbers as of that
measurement -- re-measure via `frob explore xref ProfileName` before
starting, since sibling land-path tickets touch these files often) from
branching on `ProfileName` directly to reading the settings record the
resolver child built:

  src/frob/tickets/_land.py            (_land_is_rapid, TEST016 skip)
  src/frob/app/ticket_runner/_land_cmd.py   (pre-commit sweep skip,
                                              soft backpressure warning --
                                              this one should be DELETED
                                              outright and derived from
                                              `ceilings.max_depth is None`
                                              rather than migrated to a
                                              new field, per the resolver
                                              child's own note)
  src/frob/tickets/_evidence.py        (_is_rapid helper -- callers of
                                        this helper need auditing too;
                                        it may become unnecessary once
                                        callers read the settings record
                                        directly)
  src/frob/app/ticket_runner/_close_cmd.py  (REL001 preflight skip)

Each migration is BEHAVIOR-PRESERVING BY TEST, not by inspection: for
each of the 3 profiles, assert the SAME observable land/close outcome
before and after (existing tests at each site are the starting point --
extend them to assert against the settings record's resolved values
rather than mocking ProfileName directly, so a future settings change is
caught by these tests too).

After migration, `frob explore xref ProfileName` outside
src/frob/tickets/_profile.py and the settings-resolver module (and
tests/) should return nothing in src/frob/ production code. This is the
epic's own stated acceptance ("no land-pipeline module branches on
ProfileName") -- verify it directly as the closing step, do not assume.

Standing constraints from the parent epic apply unchanged.

Acceptance:
- All 5 sites migrated; `frob explore xref ProfileName` shows zero
  production (non-_profile.py, non-test) hits.
- Existing behavior-preserving tests pass for all 3 profiles at every
  migrated site.
- `_land_cmd.py`'s redundant rapid soft-warning branch is deleted, not
  migrated -- derived from the ceilings record instead.
