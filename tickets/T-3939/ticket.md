---
id: T-3939
title: COV002 provenance edges should be enforced at WRITE time, not refused at land
  time (apollo)
state: queued
kind: feature
origin: human
created: '2026-09-05'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_coverage.py
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
Consumer apollo, 2026-09-06 (r9 wave). Their verified-land recipe now holds
across 8 consecutive lands, so the mechanical land failures are gone. What
remains is a single recurring class, in their words:

  "the remaining friction is all COV002 provenance edges (agents miss a few
   per ticket despite explicit briefs -- write-time enforcement in frob would
   beat land-time refusal)"

READ THAT CAREFULLY: they are NOT reporting that COV002 is wrong. They are
reporting that it is correct and arrives too late. Agents who were explicitly
briefed to add provenance edges still miss a few per ticket, every ticket. When
an explicit brief reliably fails, the brief is not the fix -- the feedback loop
is in the wrong place.

THIS IS THE STANDING "AUTOMATIC OVER COMMANDS" DOCTRINE, arrived at
independently by a consumer: a rule that requires the author to REMEMBER a
command has a failure rate no amount of instruction drives to zero. The gate
should tell the author at the moment they write the symbol, not at the moment
they try to land an hour of work.

WHAT TO DETERMINE FIRST. Establish where a provenance edge could be demanded
earlier than land. Candidates, in increasing order of value: during
frob check on the touched set (does this already exist?); at the point the
symbol is added, via the same path that already knows a symbol is new; or as a
write-time interception the way frob-suggest already intercepts commands.
VERIFY WHAT ALREADY EXISTS BEFORE BUILDING -- "nothing enforces X earlier" is a
claim about code and must be grepped, not assumed. It is entirely possible part
of this is already reachable and simply not surfaced by default.

DO NOT weaken COV002 itself, and do not make the land-time check advisory. The
land-time refusal is the backstop and must stay exactly as strict; this ticket
ADDS an earlier signal, it does not move the existing one.

NOTE THE CEILING ON THE WIN: an earlier signal the author can ignore reproduces
the current problem one stage sooner. Whatever is built has to be hard to not
notice at the moment of writing.

ACCEPTANCE
- The earliest point at which a missing provenance edge is detectable is
  identified and stated, with existing coverage grepped rather than assumed.
- An author writing a symbol without its provenance edge learns of it before
  attempting a land.
- COV002 land-time strictness is unchanged, demonstrated by a fixture.