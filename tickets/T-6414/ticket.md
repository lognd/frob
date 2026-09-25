---
id: T-6414
title: close the 13 authority gaps in db-paradigm-research.md with primary sources
state: queued
kind: feature
origin: agent
created: '2026-09-25'
priority: medium
parent: T-6463
tier: ticket
sprint: store-family
runs_last: false
milestone: 0.538.0
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: null
branch: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'DOC006: body names files this ticket will create (T-6448)'
  actor: logan
  at: '2026-09-25'
  old_length: 2934
  new_length: 3072
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
The research corpus's own closing tally (carried verbatim in
T-STORE-EPIC's body, the same way T-5148 carries its lint-authorities
corpus inline rather than as a detached scratch file): "13 individual
rows across the tables carry an explicit inline gap/partial-gap citation
note (verbatim vendor quote not isolated in this pass, or page returned
JS-rendered/empty content) rather than being silently presented as fully
sourced." This leaf re-fetches (or sources an alternate primary
reference for) each of the 13 rows and replaces the gap note with a
verbatim quote plus URL, IN THE EPIC'S BODY via `frob ticket body
<epic-id> --body-file` -- this ticket carries no source/scratchpad scope
of its own; the corpus it edits lives in the epic ticket, not a
repo-tracked scratchpad file:

1. Relational #2 -- EAV modeling (Postgres "Don't Do This" wiki page;
   no EAV-specific quote surfaced)
2. Relational #3 -- DB-as-queue (no Postgres-specific "don't use us as a
   queue" quote sourced)
3. Relational #5 -- unbounded LIKE (no verbatim LIKE-specific quote on
   the "Don't Do This" page)
4. Document #3 -- `$lookup` in hot path (no dedicated warning quote
   sourced, inferred from reference-modeling tradeoff)
5. Document #7 -- DynamoDB single-table design (page fetched, no
   pull-quote distinct from page title/nav)
6. Document #8 -- Scan vs Query (both AWS pages returned JS-rendered/
   empty content on this pass)
7. KV #5 -- large Redis values (no blob-size-limit quote sourced)
8. KV #7 -- blocking commands on shared connection (no dedicated vendor
   quote sourced)
9. Graph #4 -- Cartesian product in disconnected MATCH (no standalone
   verbatim warning extracted)
10. Graph #6 -- graph DB for tabular/OLAP aggregation (no direct "don't
    use us for OLAP" quote sourced)
11. Search #2 -- leading-wildcard queries (dedicated cost caveat not
    isolated verbatim)
12. Search #3 -- script_fields cost (large page, targeted quote not
    isolated)
13. Search #4 -- search index as source of truth (no single vendor
    quote sourced; Elastic's own reindexing/snapshot guidance not
    independently fetched)

Every rule leaf whose row maps to one of these 13 is `blocked_by` this
leaf (see the ticket tree's `blocked_by` edges) and does not ship until
its gap closes -- either with a verbatim quote, or an explicit owner
decision to file the rule at an advisory/lower-confidence tier with the
gap left documented rather than papered over.

Acceptance criteria: epic body updated with primary-source quotes for
all 13 gap rows -- `frob ticket body T-STORE-EPIC --body-file <path>`
(or `--append-file`) lands with either a new verbatim quote + URL for
each of the 13 rows above, or an explicit owner-approved "advisory tier,
gap accepted" note in place of the old gap note, and zero remaining bare
"gap"/"partial gap" strings in the epic body's research-corpus section
that are not accompanied by one of those two outcomes.


frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its scaffold, none exists on dev yet"
