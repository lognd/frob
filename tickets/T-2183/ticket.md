---
id: T-2183
title: 'Passenger-directive detection regexes raw diff lines, so the words ''frob:ticket
  T-xxxx'' inside a ticket''s own prose refuse the land: an agent had to reword a
  drop-reason sentence to get T-1748 landed'
state: queued
kind: bug
origin: human
created: '2026-08-16'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
acceptance:
- text: Recognise a frob:ticket directive from the file's GRAMMAR, not from diff text.
    A directive is only meaningful in a comment position of a source file in a supported
    language; the repo already has frob.lang comment/AST extraction used by extract_imports
    and the comment DSL. Today _directive_ticket_ids_in_diff (src/frob/tickets/_land.py:3468)
    runs _DIRECTIVE_TICKET_ID_RE.findall on every '+'/'-' line of 'git diff base...HEAD'
    with no notion of comment position or file type. This test MUST fail against current
    main.
  evidence: []
- text: Given a diff that adds the literal text 'frob:ticket T-2179' inside prose
    in tickets/T-1748/ticket.md, when the passenger check runs, then no passenger
    is reported -- reproducing the real incident where an agent's drop-reason sentence
    citing another ticket triggered a PassengerTickets refusal and had to be reworded
    to land.
  evidence: []
- text: Given a diff that adds a genuine '# frob:ticket T-xxxx' comment to a .py source
    file, when the passenger check runs, then that id IS still reported. Do NOT fix
    this by excluding tickets/** by path alone -- that is another lexical rule and
    would miss the same false match in docs/**, CHANGELOG.md, or a docstring. Do NOT
    weaken T-1618's deliberate blindness to the sibling's ledger state, and do NOT
    re-introduce a DONE/DROPPED exemption; the defect is WHERE a directive is recognised,
    not WHICH ids are exempt.
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
---
