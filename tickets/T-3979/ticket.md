---
id: T-3979
title: DOC006 conflates live pointers with quoted consumer symbols, proposed config
  keys and old_text audit records; amend re-creates the violation
state: in-progress
kind: bug
origin: human
created: '2026-09-06'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_docptr.py
- tests/test_docptr_gate.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/test_docptr_gate.py
  reason: 'T-3979: this ticket''s own new fixtures live in tests/test_docptr_gate.py,
    touched directly by the fix'
  actor: logan
  at: '2026-09-06'
evidence:
- tests/test_docptr_gate.py::TestDoc006OldTextNewTextFieldExclusion::test_old_text_field_not_flagged
- tests/test_docptr_gate.py::TestDoc006OldTextNewTextFieldExclusion::test_new_text_field_not_flagged
- tests/test_docptr_gate.py::TestDoc006OldTextNewTextFieldExclusion::test_open_ticket_body_still_flagged_alongside_old_text_and_new_text
- tests/test_docptr_gate.py::TestDoc006OldTextNewTextFieldExclusion::test_amend_that_removes_a_doc006_violation_leaves_ticket_clean
- tests/test_docptr_gate.py::TestDoc004Doc006ZeroOnFrobsOwnRepo::test_doc004_doc006_zero_against_live_repo
designated_repro_test: tests/test_docptr_gate.py::TestDoc006OldTextNewTextFieldExclusion::test_old_text_field_not_flagged
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
DOC006 TREATS FOUR DIFFERENT KINDS OF TEXT AS ONE, and the one it is right about
is the least common in ticket prose. It has now failed CI on ubuntu AND macOS
against frob's OWN ticket files, twice in one session, written by two different
actors.

THE FOUR MEANINGS OF POINTER-SHAPED TEXT IN A TICKET:
  (a) A LIVE POINTER into this repo -- the case DOC006 exists for. Correct to
      refuse when it does not resolve.
  (b) A CONSUMER'S SYMBOL, quoted from a downstream repo's bug report. It will
      never resolve here and is not supposed to. Measured: T-3931 carried
      scripts/bump_version.py plus its PYPROJECT constant in file-colon-symbol
      form, copied verbatim from kicad-libsync's report.
  (c) A PROPOSED, NOT-YET-EXISTING CONFIG KEY, written in literal TOML section
      form because that is how one naturally writes a proposal. Measured twice:
      the wire.pending proposal on T-3931 and the refs.artifact proposal on
      T-3976. Both are ASKS FOR A FEATURE; by definition the key cannot resolve.
  (d) AN AUDIT RECORD OF TEXT ALREADY CORRECTED -- see the no-exit below.

Only (a) is a defect. (b), (c) and (d) are normal, correct ticket prose, and
under the current rule each one reds the build.

THE NO-EXIT, WHICH IS THE SHARPEST PART AND MAKES THIS MORE THAN AN ANNOYANCE.
`frob ticket accept --amend` records the previous text in an `old_text:` field.
So amending a criterion TO REMOVE a DOC006 violation writes the violating string
verbatim into the ticket's audit trail, where DOC006 finds it again. MEASURED:
after correctly amending T-3976's acceptance[1], tickets/T-3976/ticket.md:46 now
reads `old_text: given [[refs.artifact]] is implemented, ...` and the rule still
fires. THE SANCTIONED MECHANISM FOR FIXING THE VIOLATION RE-CREATES IT. The only
escapes are a waiver or never having written the text at all -- which is the
definition of the no-exit class this queue already tracks (T-3843, T-3852,
T-3855, T-3900, F-067, T-3924, F-080). This is the eighth instance and the first
where the trap is in the REMEDY rather than the rule.

WHY IT MATTERS BEYOND CI COLOUR: this rule fires on TICKET FILES, so the cost
lands on the act of DESCRIBING work -- quoting a consumer's bug report, or
proposing a config key. Those are exactly the things a good ticket does. A rule
that makes accurate problem descriptions fail the build teaches people to write
vaguer tickets.

WHAT TO BUILD -- DO NOT simply exempt tickets/** from DOC006. Case (a) is real
and ticket prose citing a genuinely dead symbol is worth catching; a blanket
exemption is a silent zero over the whole ledger. Options, in preference order:
  1. A LEXICAL FORM THAT MARKS A NON-POINTER, so an author can quote a
     consumer's symbol or propose a key and say so explicitly. This is the
     honest fix: the four meanings need four spellings, not one. Note the owner
     has an OPEN DESIGN QUESTION on exactly this (a do-not-resolve escape hatch,
     the Zig @"" idea) -- consult that decision before inventing a syntax, and
     do not ship a competing one.
  2. EXEMPT THE `old_text:` AUDIT FIELD unconditionally. It is a historical
     record of text that is by construction no longer live, and this half is
     independently correct regardless of which way (1) goes. THIS IS THE
     MINIMUM FIX and it alone closes the no-exit.
  3. Recognise a quoted consumer path (a repo-relative path that does not exist
     here at all, rather than a symbol missing from a file that does exist) as a
     distinct, lower-severity finding.

INTERIM: a waiver on the `old_text` instance is defensible because that field IS
genuinely historical -- but a waiver is not the fix, and (2) should land so no
future author hits the same wall.

MUST-FIRE FIXTURE: a genuinely dead pointer in live ticket prose is still
flagged.
MUST-STAY-QUIET: (a) a quoted consumer symbol; (b) a proposed config key marked
as such; (c) anything inside an `old_text:` audit field.
THIRD FIXTURE: amending a criterion to REMOVE a DOC006 violation leaves the
ticket clean -- the no-exit, made checkable.

ACCEPTANCE
- The old_text exemption lands (the minimum fix), with the no-exit fixture.
- The marked-non-pointer decision consulted, not re-invented.
- tickets/** is NOT blanket-exempted; state how case (a) is preserved.
- All fixtures committed.