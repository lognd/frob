---
id: T-2177
title: 'frob ticket new accepts a scope whose files contain no trace of the ticket''s
  own subject: two tickets were filed against a file with zero matching code, caught
  only by the implementing agent'
state: queued
kind: feature
origin: human
created: '2026-08-16'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/_new.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
acceptance:
- text: 'Scope-plausibility matching MUST be token/grammar based, never lexical. Parse
    the ticket text and each scope file with the language grammar and compare SYMBOL
    sets (identifiers, qualified names, tokenized error-string literals). Never substring
    or regex match: a grep-style ''file contains this text'' check passes on a comment
    merely mentioning the symbol and fails on a re-exported alias -- wrong in both
    directions. This test MUST fail against current main.'
  evidence: []
- text: Given a ticket whose title names a symbol defined in file A, when the declared
    scope lists only unrelated file B, then ticket new refuses or warns loudly --
    reproducing the two real misfilings (T-2157 and T-2173, both scoped to src/frob/tickets/_land_git_ops.py,
    which contains zero matching code; git grep -c rebase on that file returns 0).
  evidence: []
- text: 'Third measured occurrence, all identical in shape: T-2157 and T-2173 were
    filed against src/frob/tickets/_land_git_ops.py (zero rebase code, git grep -c
    rebase = 0), and T-2189 was filed against src/frob/app/ticket_runner/_land_cmd.py
    when the defect is _land_plan_locked/_land_plan_unwind_after_merge in src/frob/tickets/_land.py.
    Every time the coordinator picked a plausible file from the module NAME rather
    than resolving the symbol or error string, and every time the implementing agent
    caught it only after taking a lease and building natives -- so the cost is a full
    dispatch cycle per occurrence, not a moment''s confusion.'
  evidence: []
- text: The check must also run at ticket new time even when the ticket is later re-scoped,
    and re-scoping a LEASED ticket must remain refused (T-1617/T-2079's ownership
    guard correctly blocked the coordinator from fixing T-2189's scope from main).
    So the fix belongs at filing, before a lease exists -- once an agent holds it,
    only that agent can correct it, which is exactly the round-trip this ticket exists
    to prevent.
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
---
