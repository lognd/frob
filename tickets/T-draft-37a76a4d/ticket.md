---
id: T-draft-37a76a4d
title: 'DECISION: SF-09 -- 56 of 139 parser keywords are used nowhere and 19 more
  only in litmus; retire or exercise?'
state: queued
kind: docs
origin: agent
created: '2026-09-19'
priority: high
parent: T-4667
tier: ticket
sprint: v0.536.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: true
no_scope_declared_reason: '2026-09-19: DECISION ticket -- its deliverable is an owner
  decision recorded in the body, which legitimately changes no files'
designated_repro_test: null
acceptance:
- text: 'Owner records a decision in the body: which of the three options (retire
    the dead surfaces, exercise them via diagnostics and docs, or split by surface),
    and what it changes. Nothing is deleted before that decision is recorded, and
    any deleting option first re-derives the dead set by a second independent method,
    since 139 is a lower bound from keyword-literal extraction only.'
  evidence: []
threat: null
component: strata
anchor: false
anchor_reason: null
land_commit: null
---
DECISION TICKET. SF-09 (MEDIUM). Child of story D (T-4667) under epic T-4662.
NOT implementation work. Do not build, and do not DELETE, anything until the
owner records a decision in this body.

EVIDENCE TABLE ROW, VERBATIM FROM scratchpad/STRATA-FRICTION.md:
| SF-09 | 40% of the implemented grammar is used nowhere; 54% is used nowhere outside litmus fixtures | 139 parser keywords extracted from strata-core/src/parse/*.rs; 56 appear in neither design/frob.strata nor design/litmus/*.strata; 19 more only in litmus | 75/139 | MEDIUM |

FULL EVIDENCE (SF-09 section, verbatim):
139 keywords extracted from `strata-core/src/parse/*.rs`
(`at_keyword`/`eat_keyword`/`expect_keyword` literals). Usage over the repo's
entire .strata corpus (design/frob.strata + 7 design/litmus files, 460 litmus
lines total):

- 56 USED NOWHERE: abstract, acl, admit, arbitrated_by, arg, atomic,
  authenticates_via, bin_path, code_ref, confine, delegation, delivery, dst,
  enables, entity, errors_total, exclusive, forbid, frame, gmsa, group, judge,
  kdc, keyed_by, listens, log, managed, max_size, mediate, modifies, ordering,
  panics_contained_by, pipe, platform, policy, rate_limit, realm, refuse,
  remove, require, residence, respond, rpo, runnable, runs_as, scale,
  service_account, size, spn, src, sticky, sudoers, time, transitive, use, users.
- 19 MORE USED ONLY IN LITMUS FIXTURES, never in a real model: audience, canary,
  capacity, declassify, endorsed_by, fanout, immutable, issued_by, lifetime,
  provider, replicas, revoke, rollback, service, skew,
  tls_terminates_at_provider, unlimited, within, zipf.

Note `confine` and `forbid` in the dead list: T-3920 item 1 reports a consumer
GERRYMANDERING GLOBS because they could not say "ban X except in Y" -- while
`confine` is documented in docs/strata/policy.md and implemented in the parser.
That is a discoverability/reachability gap, exactly as T-3920 guessed.

Also dead: the whole std.krb surface (kdc, realm, spn, gmsa, sudoers, delegation
-- archive/T-0262) and the observability surface (log, listens, errors_total,
panics_contained_by -- archive/T-0070).

A fix would have to change: scope (retire or exercise), plus docs.

MEASUREMENT CAVEAT THE OWNER MUST WEIGH BEFORE DECIDING
The extraction is from at_keyword / eat_keyword / expect_keyword literals only.
A construct reached only through a NON-KEYWORD token path would be missed. So
139 is a LOWER bound on the grammar, and "56 unused" is an UPPER-BOUND claim on
deadness within those 139. Per memory/verify-premise-before-filing.md, any option
that DELETES must first re-derive the dead set by a second, independent method.

OPTIONS THE EVIDENCE SUPPORTS

Option 1 -- retire the dead surfaces.
Remove std.krb (6 keywords, archive/T-0262) and observability (4 keywords,
archive/T-0070) and the rest of the 56. Would have to change: the parser, the
elaborator, docs/strata/krb.md and the observability docs, and every consumer
model that might use them -- which is the risk, since the corpus measured here
is frob's OWN model plus litmus, NOT consumer repos. A consumer census is a
precondition for this option.

Option 2 -- exercise, do not retire: make the dead constructs reachable.
The `confine` case shows the failure is DISCOVERABILITY, not uselessness: a real
consumer gerrymandered globs rather than use a construct that exists, is
implemented, and is documented. Would have to change: diagnostics (suggest
`confine` when a policy pattern is being gerrymandered), docs, and the litmus
corpus (promote the 19 litmus-only constructs into a real model). Costs nothing
in compatibility.

Option 3 -- split the decision by surface.
Retire std.krb and observability (both already have ARCHIVE tickets, so the
intent to drop them is on record), and take option 2 for the security-relevant
remainder (confine, forbid, frame, declassify, mediate, refuse). Would have to
change: both of the above, scoped smaller.

A NOTE ON LITMUS, so nobody chases it: the audit found all 7 design/litmus/*.strata
parse cleanly and collectively exercise 19 constructs the self-model never uses
-- they are the ONLY thing keeping those alive. They are under-used, NOT broken.
Retiring litmus coverage as part of any option above would silently widen the
dead set.

ACCEPTANCE
Owner records a decision in the body: which option, and what it changes.
