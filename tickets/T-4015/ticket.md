---
id: T-4015
title: 'F-228: ticket-id matching has no token boundary, so UT-2207 reads as a citation
  of T-2207 and the sweep auto-files tickets about the phantoms'
state: queued
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
- src/frob/verify/_attribution.py
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
Consumer logand.app-v2 F-228, 2026-09-06:

  "Agents copy frob's own ticket ids ('WARN-only per T-3057', 'T-2207
   retire-unidentifiable') into comments and done reports; TICK006 then flags
   them as citations of non-existent local tickets and the post-land sweep filed
   T-0198 and T-0202 about them. Ids above the local allocator's range, or
   prefixed 'frob T-xxxx', should be recognised as foreign; and the sweep should
   not file a ticket for a rule finding that a text fix resolves."

THIS VIOLATES A STANDING DIRECTIVE OF THIS PROJECT: checks must parse and compare
SYMBOLS, never substrings. It is the ninth instance of the lexical-hook class
(hand-rename-sed x3, ack line-anchoring T-3851, the root-write guard T-3421,
handrolled-floor-count, retry re-block F-078, protect-secrets T-3924).

MEASURED IN OUR OWN SOURCE, not inferred. src/frob/verify/_attribution.py:351:

    _TICKET_ID_IN_SUBJECT = re.compile(r"T-[0-9]{4,}")

There is no left boundary. Demonstrated:

    "UT-2207"          -> matches T-2207
    "see UT-2207 row"  -> matches T-2207
    "frob T-3057"      -> matches T-3057

So any identifier ENDING in the ticket-id shape is silently read as a citation.
The consumer's spec row ids (UT-nnnn) are the reported case; the general form is
every X-T-nnnn, UT-nnnn, PT-nnnn or similar scheme any repo might use. FIND EVERY
SUCH PATTERN, not only this one -- the grep above found this call site, but
TICK006's own path should be checked directly rather than assumed to share it.

TWO DISTINCT DEFECTS, and the second is worse than the first:

1. THE LEXICAL MATCH. Fix with a token boundary. Note a bare \b is NOT enough:
   \b matches between "U" and "T" only if... actually it does not, but a hyphen
   and preceding letter make boundary reasoning subtle -- so ASSERT the fix with
   the UT-nnnn case as a fixture rather than reasoning about \b semantics. Also
   handle the deliberate foreign-citation case the consumer names: a
   "frob T-3057" prefix, or ids above the local allocator's high-water mark,
   should read as FOREIGN, not as dangling.

2. THE SWEEP AUTO-FILES TICKETS ABOUT THE PHANTOMS. This is the amplifier and it
   is the part that makes the bug expensive rather than annoying: a false finding
   does not merely print, it MANUFACTURES QUEUE ENTRIES (their T-0198, T-0202).
   So a lexical false positive converts directly into permanent backlog that a
   human must triage and close. Any rule whose findings are auto-filed needs a
   higher precision bar than one that only prints, and the sweep should not file
   for a finding class that a text edit resolves. STATE THAT POLICY EXPLICITLY --
   which finding classes are auto-fileable -- rather than fixing this one rule.

RELEVANT TO US DIRECTLY: this repo carries 243 distinct T-draft-* ids cited under
tickets/, a population I measured while checking whether agent-filed drafts
survived a land. If the citation scanner has no token boundary, some fraction of
any dangling-citation count here may be phantom too. Re-measure that population
AFTER fixing the boundary, and report the before/after -- the number that
justifies work on T-3893's draft-citation retargeting may be smaller than
believed.

MUST-FIRE FIXTURE: a genuine dangling citation T-9999 in a comment is still
flagged.
MUST-STAY-QUIET: UT-2207 in a spec row id is not flagged, and neither is a
deliberately foreign "frob T-3057".
THIRD FIXTURE: the post-land sweep does not auto-file a ticket for a finding of
this class.

ACCEPTANCE
- Token-boundary matching, proven by the UT-nnnn fixture rather than by
  reasoning about regex semantics.
- Foreign-id recognition (prefix and/or allocator range) implemented.
- An explicit, stated policy for which finding classes the sweep may auto-file.
- The local dangling-citation population re-measured after the fix.
- All three fixtures committed.