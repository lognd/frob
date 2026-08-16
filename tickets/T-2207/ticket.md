---
id: T-2207
title: 'A malformed empty-identity finding makes quarantine PERMANENTLY unclearable:
  dispose rejects it as malformed while clearing requires every finding disposed,
  so deferred landing stays off fleet-wide with no recovery path'
state: queued
kind: bug
origin: human
created: '2026-08-16'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/verify/_quarantine.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
acceptance:
- text: 'Reproduced live and confirmed unrecoverable. .frob/quarantine.json holds
    a record with rule_id='''', file='''', line=None, commit_sha=None -- every identity
    field empty. ''frob verify dispose --dismiss ::=<reason>'' fails with ''malformed
    --dismiss''; disposing only the well-formed siblings fails with ''FindingsNotDisposed:
    one or more recorded findings have no filed ticket or dismissal yet''. So the
    finding cannot be disposed and quarantine cannot clear, leaving deferred landing
    OFF fleet-wide with every land forced onto ~208s synchronous verification. There
    is no CLI recovery path. This test MUST fail against current main.'
  evidence: []
- text: 'Two distinct defects, fix BOTH. (1) PRODUCER: something persisted a finding
    with an entirely empty identity into the quarantine store -- reject or normalise
    it at write time, since a finding that names no rule and no file is not actionable
    by construction. (2) CONSUMER: dispose must be able to retire any record the store
    can hold, including malformed ones -- a state the system can ENTER but not LEAVE
    is the defect regardless of how it got there. Fixing only the producer leaves
    existing stuck stores unrecoverable.'
  evidence: []
- text: Do NOT fix this by making clear_quarantine skip undisposable findings silently
    -- that reopens the hole T-1693 closed, where a real unaddressed finding stops
    gating landing. Do NOT require hand-editing .frob/quarantine.json as the recovery
    path either; that is what I had to do here, it is untracked local state with no
    audit trail, and an operator doing it under pressure can lose real findings. Provide
    an explicit, logged verb for retiring an unidentifiable record.
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
---
