---
id: T-4025
title: 'F-236+: frontend delta audit -- substring-as-prefix is now a measured cross-language,
  cross-repo recurrence'
state: queued
kind: security
origin: human
created: '2026-09-06'
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
no_scope_declared: true
no_scope_declared_reason: 'tier=epic: decomposition container for the sixth consumer
  audit list; scope lives on the children, which must be filed before any code is
  written'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Consumer logand.app-v2, F-236 onward, verbatim from their
docs/security/audit-2026-09-06-frontend-delta.md. SIXTH audit list from that
repo. The first five are T-3919, T-3920, T-3928, T-3942 and T-3984 -- the first
four now decomposed into 23 children, the fifth into 12.

THE ITEM THAT MATTERS MOST IS 2, AND NOT FOR THE REASON THEY GIVE.

  "Substring-as-prefix has now appeared independently in two subsystems.
   auth/csrf.py's _is_exempt and ImageCarousel.tsx's toNocookie are the same bug
   written in two languages. The threat model's learn-item 5 proposed a
   'known-dangerous comparison idiom' rule kind speculatively; this pass is the
   second independent instance, which promotes it from speculation to a measured
   recurrence."

They are right that two instances promote it from speculation. What they cannot
see is that THIS IS THE SAME CLASS FROB ITSELF KEEPS SHIPPING. This queue tracks
it as the lexical-hook class and it stands at NINE internal instances --
hand-rename-sed (x3), ack line-anchoring, the root-write guard, handrolled floor
count, retry re-block, protect-secrets, and most recently T-4015 (a ticket-id
regex with no left boundary, so UT-2207 reads as a citation of T-2207). Their
POL-raw-client-ip glob failure (T-4013, fnmatch treating `**` as at-least-one
directory) is a third arrival in their repo.

So this is not a frontend nicety. It is a bug shape that recurs across
languages, across repos, and across the tool that is supposed to catch it. That
makes their proposed trigger set the single most valuable item in the list:
String.replace / `in` / .includes() where the receiver is a URL, path or host,
and the enclosing function name matches to*/is_*/normalize*/check_*. It is
cheap, syntactic, and would fire on our own code today. WHOEVER DECOMPOSES THIS
SHOULD RUN THAT TRIGGER SET AGAINST src/frob/ BEFORE FILING and report the count
-- if it finds live instances here, that is the strongest possible motivating
evidence and it changes the priority.

THE ITEM MOST LIKELY TO SHIP THIS WEEK is 3: dangerouslySetInnerHTML containing
a direct JSON.stringify call. Their words: "not a taint-analysis problem and
needs no data-flow ... a JSX attribute containing a direct call expression, four
occurrences, one repo ... writable today". A concrete, bounded policy.pattern
with a known non-zero subject count. Note it depends on T-4013 landing first --
a policy pattern whose glob silently under-matches is worse than none.

THE REST, in their order:
1  A component can be fully implemented, tested, V-model-closed AND NEVER
   INVOKED. frob knows package.json is an entrypoint and knows the script names;
   it does not model REACHABILITY from a declared entrypoint. This is a
   vacuous-pass shape and belongs with T-3985's subject-count work -- three
   green components that nothing calls is a gate reporting on an empty set.
4  The `may` capability atom has presence but no MAGNITUDE. Granting
   html_render or frame-src says nothing about the seven permissions delegated
   in an iframe's allow= attribute. Pairs with T-3990 (SYS111 must digest the
   declared via-glob list, not just count it) -- same defect, different atom.
5  Comments asserting facts about ANOTHER FILE are outside the drift graph, so
   DRIFT001 cannot see them. Proposes a frob:claim directive, or guidance that
   any comment naming another path must be a frob:doc.
6  Frontend a11y has NO obligation kind. axe-core is an installed devDependency
   that nothing imports; WCAG conformance is modelled as class-string constants
   frob can check for existence but not effect. Proposes frob:tests kind="a11y".
7  THE CADDYFILE BLIND SPOT PRODUCED A REAL OUTAGE, not spec drift. It was
   filed as harmless because no consumer existed; the consumer then landed on a
   different branch in a different language and nothing connected them. Note
   this is a measured instance of the cross-language desync T-3928 already
   records as frob:mirror.
8  NO ARTIFACT-SHAPE OBLIGATIONS: a post-build step deletes the entry bundle,
   and 138MB of tracked binaries ship in dist/. Both are properties of build
   OUTPUT, entirely outside frob's graph. Pairs with T-3976 (refs.artifact) --
   check whether that construct subsumes this before filing a second one.

GUIDANCE, as with the previous five epics: DO NOT BUILD ALL OF IT. Decompose into
leaves, keep the audit's ordering, name the finding each child would have caught,
and VERIFY EACH AGAINST WHAT EXISTS FIRST -- four items across the earlier epics
turned out to be already implemented, and a ticket for existing work is worse
than no ticket.

ACCEPTANCE
- The item-2 trigger set run against src/frob/ and the count reported BEFORE
  filing it, since we are a likely offender.
- Children filed in the audit's order, each naming its finding.
- Items 1, 4 and 8 cross-referenced to T-3985, T-3990 and T-3976 rather than
  duplicated.
- Item 3 sequenced after T-4013.