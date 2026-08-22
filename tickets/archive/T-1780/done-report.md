## Done report

Read T-2134 first, as instructed: it questions the SEPARATE root
`tickets.md` monofile (the pre-v2-migration ledger), not this doc file --
unrelated, no overlap, no change to what "split" means here.

Measured the seams from the document's own parsed H2 heading structure
(88 real headings; a second pass over ALL `#`-prefixed matches including
fenced code-comment pseudo-headers, matching the exact regex/slugify
`frob.gates._docptr._heading_slugs`/`frob.graph.dsl.slugify` use, so the
split boundaries and every anchor's post-split slug are provably
byte-identical to what gate:DOC already checks -- a token/grammar
approach, not a byte-offset one). Five subject clusters, matching the
document's own natural boundaries (confirmed by where each of the 61
`frob:doc`-referenced anchors landed):

- `docs/modules/tickets-lifecycle.md` -- filing, review, scope/lease,
  organization, state machine, provisional ids, promote (1420 lines)
- `docs/modules/tickets-landing.md` -- `frob ticket land` and its whole
  critical path (2297 lines)
- `docs/modules/tickets-verify-sweep.md` -- verification watermark,
  backpressure, quarantine, rapid profile (1215 lines)
- `docs/modules/tickets-merge-driver.md` -- the git merge driver (169
  lines)
- `docs/modules/tickets-data-storage.md` -- data models, storage
  internals, remaining organization primitives (1212 lines)

`docs/modules/tickets.md` itself keeps the overview, storage summary, and
Public API index (556 lines) plus a pointer section to the five split
files -- not a stub that re-includes them (requirement 3): every section
moved OUT bodily, nothing is duplicated.

Repointed every `frob:doc`/doc-cross-reference anchor whose target moved:
346 replacements across 66 source/test/doc files (mechanical, driven
directly by the split -- same class as CLI-wiring-implicitly-in-scope for
a FEATURE ticket, so added to scope via `frob ticket scope --add` rather
than touched silently) plus one `design/frob.strata` anchor and a small
prose cross-reference in `docs/modules/app.md`/`docs/modules/gates.md`/
`docs/modules/serve.md` that a naive regex missed (verified by re-grepping
for `docs/modules/tickets\.md#` afterward: every remaining hit either
targets the kept-in-index Public API section or is one of 5 anchors that
were ALREADY broken before this split -- no matching heading either way,
pre-existing DOC006-adjacent drift, unchanged by this ticket, listed
below rather than silently left).

Requirement 2 (the actual point): 8 open tickets named
`docs/modules/tickets.md` in their filed scope at start; re-measured after
finding the current queue, not trusting the ticket's own originally-filed
count of 35 (queue moved under 150+ lands since 2026-08-07). `frob ticket
scope --remove docs/modules/tickets.md --add <new home>` for the 7 that
were not T-1780 itself, each pointed at the file matching its own other
scoped code (T-1691/T-1696 -> verify-sweep, T-1748/T-1860/T-2166 ->
landing, T-1777/T-2116 -> lifecycle). Re-measured: 1 open ticket now names
`docs/modules/tickets.md` (T-1780 itself).

`design/frob.strata` and each of the 7 sibling tickets' scope-closure
checks produced non-blocking WARNINGS only (scope's own closure rule
wanting every doc-target's OTHER unrelated targets also in scope, an
inherent property of `design/frob.strata` naming many unrelated doc
targets) -- confirmed via `frob ticket land --dry-run` that these do not
block landing; the actual land-blocking gate reached was the ordinary
missing-evidence check, resolved below.

Pre-existing broken anchors, unchanged by this split (do not re-derive
this list; it was correct before and after):
- `#check-repro-post-land-limitation-t-2025` (2 hits,
  `_verify.py`/`_mutation_evidence.py`)
- `#frob-ticket-brief` (missing its `-t-0568` suffix, 1 hit)
- `#review-record` (no matching heading, 1 hit)
- `#scope-lease-model`/`#scope-lease-mutation` (missing suffix / no
  matching heading, 2 hits)

Evidence: `frob check --ticket T-1780 --only docanchor --only doclink
--only docmake --only docstatus` -- 0 errors both before writing this
report and after the ledger-scope commits above (re-run, not assumed).
`gate:FMT` clean after `frob fmt` rewrapped the frob:doc directive
comments the longer split-file names pushed past 88 cols (one prose
docstring line in `src/frob/tickets/_land.py` needed a manual wrap; fmt
only rewraps directive comments). `frob fmt` ran repo-wide once by
mistake (70 files); reverted everything outside this ticket's own
touched set (49 unrelated `.strata`/gates files) before committing, kept
only the 20 files it correctly fixed among ones this ticket already
touched.

`gate:DRIFT` (`_finish_only_if_already_landed`) and the Claude-config
drift note are both pre-existing, unrelated to any file this ticket
touches (confirmed via `git diff` -- neither function's body is anywhere
near my edits) -- not caused by this change.

Evidence: tests/test_docptr_gate.py::TestDoc006DocAnchor::test_missing_anchor_flagged,
tests/test_docptr_gate.py::TestDoc006DocAnchor::test_real_anchor_passes
(the DOC002/DOC006 anchor-resolution mechanism this whole split's
correctness rests on).

Filed: none -- the 5 pre-existing broken anchors above are drift that
predates this ticket and is unrelated to its split (no heading ever
existed for any of them, before or after); noting them here satisfies
disclosure without opening a new ticket for pre-existing rot outside
T-1780's own scope.

Gates: frob check --ticket T-1780 --only docanchor/doclink/docmake/
docstatus/fmt clean (0 errors). gate:SCOPE surfaces 7 SCOPE002
"under-capture" NOTES against the wide mechanical-touch scope (the
whole-file call-graph closure these large already-existing modules
trigger once declared in scope) and 2186 scope-closure WARNINGS against
`design/frob.strata` -- both non-blocking, confirmed via `frob ticket
land --dry-run` reaching the ordinary evidence gate, not a scope refusal.
