---
id: T-3920
title: 'what strata could not express in a real threat-model pass: eight expressiveness
  gaps, including trust-as-identity having no construct'
state: queued
kind: security
origin: human
created: '2026-09-05'
priority: high
parent: T-4662
tier: epic
sprint: v0.536.0
runs_last: false
milestone: 1.1.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: parent
  old_value: null
  new_value: T-4662
  reason: '2026-09-19: SF-12 in the STRATA friction audit; attached directly to epic
    T-4662 rather than to story D (T-4667) because this ticket is itself tier=epic
    and ParentTierInversion refuses a story parenting an epic -- it is grouped WITH
    story D''s decisions, since its fix surface is the grammar and semantics the owner
    is personally rethinking'
  actor: logan
  at: '2026-09-19'
- field: sprint
  old_value: v0.546.0
  new_value: v0.536.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-19'
- field: milestone
  old_value: v0.546.0
  new_value: 1.1.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-20'
body_changes:
- mode: append
  reason: '2026-09-19: attaching SF-12''s evidence row verbatim plus corroboration
    this ticket lacked when filed -- three independent arrivals at item 6''s missing
    axis (T-3919 item 6, T-3961), item 7 being the same finding as T-4598, and item
    1 now measured as a discoverability gap since confine/forbid are implemented but
    among SF-09''s 56 unused keywords'
  actor: logan
  at: '2026-09-19'
  old_length: 4957
  new_length: 7872
- mode: append
  reason: '2026-09-19: correcting the parent named in the SF-12 evidence block just
    appended -- this ticket is tier=epic so it attaches to T-4662 directly, not to
    story T-4667'
  actor: logan
  at: '2026-09-19'
  old_length: 7872
  new_length: 8327
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
A threat-model pass on a consumer repo (logand.app-v2, 2026-09-05) recorded what
frob and strata COULD NOT EXPRESS. Reported as their FROBLEMS F-097, sourced
from docs/security/threat-model.md in that repo (READ-ONLY -- do not write
there). Confirmed findings behind it: raw client IP trusted behind a proxy, CSRF
exemption by substring, R2 credentials in an rclone argv, no proxy connection
timeouts.

THIS IS THE COMPANION TO T-3919 AND A DIFFERENT CLASS. T-3919 is what frob
MISSED -- rules that do not exist yet. This is what frob CANNOT SAY. That is
more fundamental: a missing rule can be added, but a rule cannot be written for
a property the language has no way to describe. File children accordingly and do
not merge the two epics.

THE AUDITOR'S LIST, preserved close to verbatim:

  1. NO NEGATIVE/EXCLUSION GLOBS on [[policy.pattern]]. They had to gerrymander
     globs around the sanctioned implementation file instead of saying "ban X
     EXCEPT in Y". Note this is odd given strata's own policy.md documents
     Confinement as a first-class form ("confine use psycopg to
     src/api/db.py") -- so the CONCEPT exists and the pattern surface cannot
     express it. Check whether confinement covers their case before building
     exclusion globs; this may be a discoverability gap rather than a
     capability one.
  2. TREE-SITTER QUERY FIELD ORDER is unforgiving and the compile error does
     not say why. They bisected it OUTSIDE frob. Pure diagnosability, and the
     cheapest item here.
  3. SHELL (ops/*.sh) AND Caddyfile HAVE NO FROB GRAMMAR AT ALL, so two of four
     confirmed findings are STRUCTURALLY INVISIBLE to policy. Related to T-3858
     (frob:waive inert in no-grammar files) but distinct: that one is about
     DIRECTIVES in unparsed files, this is about POLICY over them. A shell
     grammar in particular is worth costing -- ops scripts are where
     credentials and network calls live.
  4. [[policy.norm]] WAS NEVER EXERCISABLE: every finding was a static-file
     property, not a diff-shape property. An entire configuration surface that
     could not be used once in a real security pass. Either the surface is
     mis-aimed or its use case needs documenting with a worked example.
  5. SEMANTIC AUTHORIZATION BUGS (substring vs prefix check) are out of policy
     reach; they propose a "known-dangerous comparison idiom" rule kind and
     call it cheap. This is the same ask as T-3919's item 10, from a second
     direction -- treat the two as one child.
  6. THE DEEPEST ITEM: the capability ratchet polices what code may DO; NOTHING
     POLICES WHAT IT MAY TRUST AS IDENTITY (raw peer address vs proxy header).
     Capability and trust are different axes and strata models only the first.
     This is the language-level statement of T-3919's item 6 (provenance for
     PII atoms, a derived_from edge). Both audits reached it independently from
     opposite ends, which is the strongest signal in either list.
  7. SCOPE COLLISION IS FILE-GRANULAR, NOT SECTION-GRANULAR: another ticket held
     the whole .strata file though its work never touched the added regions.
     THIRD sighting of F-085/F-060, and the first where it blocked a SECURITY
     pass rather than ordinary work. Cite it there rather than filing again.
  8. INV001/INV002 HAVE NO WAIVER PATH (unlike INV003/INV004), so an invariant
     describing a KNOWN, TICKETED-BUT-UNLANDED gap CANNOT BE COMMITTED. Their
     word for it is "backwards" and that is right: the system refuses to record
     a TRUE statement about the code because the thing it describes is not
     fixed yet. That is the no-exit class inverted -- elsewhere a rule demands
     an artifact that cannot exist; here it forbids one that does. It also
     actively discourages writing invariants early, which is when they are most
     valuable.

DECOMPOSITION GUIDANCE:
  - Items 2 and 8 are cheap and independent -- do them first regardless of what
    happens to the rest. Item 8 in particular is a small consistency fix
    (INV003/INV004 already have the path) with an outsized effect on whether
    people write invariants at all.
  - Item 6 is a strata LANGUAGE change and should be scoped with T-3919 item 6
    as one design, not two.
  - Items 1 and 4 need a MEASUREMENT FIRST: is the surface missing, or present
    and undiscoverable? Item 1's interaction with documented Confinement makes
    that a real possibility, and building an exclusion-glob feature that
    duplicates confinement would be exactly the duplication this repo's rules
    forbid.
  - Item 3 is a scoping decision about how many grammars frob carries. Cost it;
    do not assume yes.

DO NOT treat any of this as a specification. It is a competent outside reading
by someone who hit these while doing real security work, written without
knowledge of frob's internals. Verify each against what exists before building;
"search the code, not just the queue" applies fully.


## SF-12 evidence (attached 2026-09-19 by the STRATA friction epic, T-4662)

Recorded in scratchpad/STRATA-FRICTION.md as SF-12, evidence table row verbatim:

| SF-12 | Eight recorded expressiveness gaps from a real threat-model pass, still unbuilt | tickets/T-3920/ticket.md (queued, high, sprint v0.546.0) -- notably #6 "nothing polices what code may TRUST as identity" and #7 file-granular scope collision (3rd sighting) | 8 gaps | MEDIUM |

From the SF-12 section, the corroboration this ticket did not have when it was
filed:

- Item 6 ("the capability ratchet polices what code may DO; NOTHING POLICES WHAT
  IT MAY TRUST AS IDENTITY") is independently corroborated from two other
  directions: T-3919 item 6 (provenance / `derived_from` for PII atoms) and
  T-3961 "provenance / trust-as-identity construct in strata" (queued). THREE
  INDEPENDENT ARRIVALS AT THE SAME MISSING AXIS.
- Item 7 (scope collision is file-granular, not section-granular, "THIRD
  sighting ... and the first where it blocked a SECURITY pass") is the same
  finding as SF-06, which is T-4598 in the KERNEL DECOUPLING epic. Fix it there,
  not here.
- Item 1 (no negative/exclusion globs on [[policy.pattern]], a consumer
  gerrymandering globs because they could not say "ban X except in Y") turns out
  to be a DISCOVERABILITY gap, not a missing feature: SF-09 measured that
  `confine` and `forbid` are both implemented in strata-core's parser and
  `confine` is documented in docs/strata/policy.md -- and both are in the list of
  56 keywords used NOWHERE in the entire .strata corpus. This ticket guessed that
  ("exactly as T-3920 guessed", per the audit); it is now measured. See T-4678
  (DECISION: SF-09).
- Consumer-round corroboration of the same class: T-4157 "consumer round-4 engine
  audit: findings frob or strata should have caught" (H4-1 is a dynamic import by
  source path against design/logand-app.strata; line 115 proposes
  `may: dom.global_key_capture`) and T-4109 "consumer round-3 backend audit: ten
  defects frob or strata should have caught".

WHY THIS IS NOW A CHILD OF T-4667 (story D of epic T-4662) AND NOT OF A BUILD
STORY: the audit records this ticket's fix surface as "the grammar and semantics
(item 6 especially), the gate (item 8), and tooling/diagnostics (item 2)". The
owner is personally rethinking strata grammar and semantics, so T-4662 treats
every grammar-surface finding as a DECISION to be recorded, not as work to be
started. Item 6 in particular is a new axis in the language and must not be
designed ahead of that rethink.

Items 2 (tree-sitter query field order diagnostics) and 8 (INV001/INV002 have no
waiver path) are NOT grammar and could be split into leaves at any time; item 1
is now answered by discoverability work rather than new grammar. This ticket
keeps its existing sprint v0.546.0 commitment; it is attached here so the
decision it needs is visible in one place.


CORRECTION to the SF-12 evidence block above (same day): this ticket is itself
tier=epic, and frob refuses ParentTierInversion (a story cannot parent an epic,
T-0715). It is therefore attached directly to epic T-4662, NOT to story T-4667.
It is grouped WITH story D's decisions for all other purposes: no implementation
ticket should be filed against its grammar-surface items (especially item 6,
trust-as-identity) before the owner records a decision.
