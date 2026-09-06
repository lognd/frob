---
id: T-4083
title: re-indenting an existing frob:ticket directive reads as adding a foreign edge,
  so a pure formatting move is refused as an undisclosed passenger
state: queued
kind: bug
origin: human
created: '2026-09-06'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_land_cmd.py
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
Consumer apollo, 2026-09-06:

  "T-1618 PassengerTickets land refusal: RE-INDENTING an existing frob:ticket
   edge (T-0104 moved from column 0 to method indentation) reads as a directive
   ADDITION naming another ticket, and the land refuses as an UNDISCLOSED
   PASSENGER. Fix: restore the original indentation so the diff carries no
   foreign-edge addition (cleaner than --allow-cross-ticket for a pure move)."

A WHITESPACE-ONLY CHANGE IS READ AS A SEMANTIC ONE. The directive already
existed, already named T-0104, and was neither added nor altered in meaning --
only its leading whitespace changed when it moved to method indentation. The
passenger check compares DIFF LINES, so a removed line at column 0 plus an added
line at column 4 reads as "this ticket added a directive naming another ticket",
which is the exact shape an undisclosed passenger takes.

THIS IS THE LEXICAL-HOOK CLASS, ELEVENTH INSTANCE, and it violates the standing
directive of this project directly: checks must parse and compare SYMBOLS, never
raw text. The queue already tracks hand-rename-sed (x3), ack line-anchoring
(T-3851), the root-write guard's `>=` (T-3421), handrolled floor count, retry
re-block (F-078), protect-secrets (T-3924), the ticket-id regex with no left
boundary (T-4015), and the secrets hook matching `import.meta.env` (T-4082).
Every one compares text where structure was meant.

THE FIX IS TO COMPARE PARSED DIRECTIVES, NOT DIFF HUNKS. frob already parses
frob: directives out of source -- that is what builds the obligation graph. The
passenger check should ask "does the set of foreign ticket edges in this file
differ before and after?" rather than "does the diff contain an added line that
looks like a foreign edge?". A pure move produces an identical set and must be
silent.

NOTE THE COST SHAPE AND WHY THEIR WORKAROUND IS THE RIGHT ONE TO PREFER: the
available escape is `--allow-cross-ticket`, which DISCLOSES a passenger that does
not exist -- recording a false statement in the ledger to satisfy a false
detection. Apollo instead restored the original indentation, i.e. they REVERTED A
LEGITIMATE FORMATTING IMPROVEMENT to appease a lexical check. Both routes are
damage: one corrupts the record, the other the code. That is the same
wrong-incentive property filed as T-4069 today (three gates satisfied by making
the code worse), and this is a fourth instance for that ticket's audit.

WORTH CHECKING WHILE IN THERE: whether the same diff-line comparison is used for
OTHER directive-shaped detections (a moved frob:waive, a re-wrapped frob:tests
line, a directive whose continuation backslash placement changed). `frob fmt`
canonicalises directive wrapping, so a formatter run could plausibly trigger the
same false passenger refusal -- and F-279 already reports TDD001 misfiring after
land's own `frob fmt` canonicalisation commit, which may share this root.

MUST-FIRE FIXTURE: genuinely ADDING a frob:ticket directive naming another
ticket still refuses the land as an undisclosed passenger.
MUST-STAY-QUIET: re-indenting, re-wrapping, or moving an existing directive
within a file produces no passenger finding.
THIRD FIXTURE: a directive whose ticket id actually CHANGES is still detected.

ACCEPTANCE
- The passenger check compares parsed directive sets, not diff lines.
- Other directive-shaped diff comparisons audited for the same defect, with
  F-279's TDD001-after-fmt report checked as a possible shared root.
- All three fixtures committed.