---
id: T-3920
title: 'what strata could not express in a real threat-model pass: eight expressiveness
  gaps, including trust-as-identity having no construct'
state: queued
kind: security
origin: human
created: '2026-09-05'
priority: high
parent: null
tier: epic
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
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
