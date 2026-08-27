---
id: T-3022
title: 'Docs narrative bulk migration: 140 files still cite tickets in prose, split
  by file'
state: queued
kind: docs
origin: human
created: '2026-08-26'
priority: medium
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
no_scope_declared_reason: 'Epic rollup enumerating per-file docs-narrative migration
  work; each child ticket declares its own file scope when dispatched, not this one.

  '
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-2995 proved the approach on one representative file (docs/commands/narrative.md):
extended src/frob/narrative (paragraph_at + a markdown-aware reference line in
migrate_block) so the SAME T-2993 machinery -- no second detector, no second
migration path -- handles a markdown paragraph citing a ticket id exactly like
it handles a `# T-####:` code comment block. Ran `frob narrative move` for real
against T-2678 (archived), proving the archived-ticket-safe write path a second
time on a different ticket/file pair, and verified idempotency (a second run is
a no-op) and `frob ticket list` exits 0 afterward.

This is the bulk: 140 of 146 doc files (git ls-files docs/**/*.md) contain at
least one T-id citation; the worst offenders by raw T-id occurrence count
(a cheap proxy for "how many paragraphs to read", not a promise every citation
is narrative -- the split is a judgement call per T-2994, not a regex):

  869 docs/modules/gates.md
  342 docs/modules/tickets-landing.md
  215 docs/modules/tickets-lifecycle.md
  214 docs/modules/arch.md
  198 docs/guides/coordinator-scripts.md
  192 docs/modules/tickets-verify-sweep.md
  192 docs/modules/tickets-data-storage.md
  150 docs/strata/surface.md
  122 docs/modules/serve.md
  121 docs/strata/host.md
  121 docs/guides/agent-playbook-appendix.md
  116 docs/strata/reliability.md
  108 docs/modules/graph.md
  99  docs/modules/app.md
  92  docs/modules/vet.md
  87  docs/modules/testing.md
  81  docs/modules/perf.md
  78  docs/modules/tickets.md
  75  docs/modules/cli.md
  68  docs/modules/lang.md
  (120 more files below this line, smaller counts)

Full per-file counts were captured during T-2995's work session
(`git ls-files 'docs/**/*.md' | xargs grep -c 'T-[0-9]\{2,6\}'`, non-zero rows
only, 140 files, sorted descending) -- re-run that command for the current
state before dispatching, since docs keep moving under this repo's own drive.

PLAN (do not dispatch this whole ticket as one unit -- split by file or small
file group, each its own ticket, scope-disjoint so multiple agents can work in
parallel without lease collisions):

1. For each file, walk its T-id-citing paragraphs. For each: decide (a judgement,
   not mechanical) whether it is narrative (why we got here, what a prior
   attempt got wrong) or current-behavior utility (what a reader needs to know
   to use/modify this now). Bare citations ("(T-1234)") stay in place --
   T-2994's doctrine explicitly allows a reference, only the elaborated STORY
   moves.
2. For a genuinely narrative paragraph, `frob narrative move FILE LINE
   --keep-file ... --reason ...` (extended by T-2995 to handle a `.md`
   paragraph the same as a `# T-####:` code block) moves it into the cited
   ticket. Most cited tickets are archived -- this is proven safe (T-2678,
   twice now).
3. `frob ticket list` must exit 0 after every batch (the DuplicateId regression
   check T-2994 flagged as the standing hazard).
4. MOVE, NEVER DELETE. If a paragraph's ticket is ambiguous or the citation is
   stale/wrong, flag it in the Done report rather than guessing.
5. Idempotent: re-running a move on an already-migrated paragraph is a no-op
   (verified in T-2995).

Do NOT attempt a single land touching all 140 files -- unreviewable, and would
lock every doc file's lease against the rest of the fleet for however long that
took. Split into per-file or small-file-group tickets as this ticket's own
children, largest files first.
