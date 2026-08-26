<!-- frob:waive REF002 reason="a dated point-in-time audit snapshot (branch counts change daily, see the doc's own first paragraph), anchored from its generating script's frob:doc directive by design -- a second consumer would not be genuine" -->

# Branch stranded-work analysis (T-2646, 2026-08-25)

Status: 2026-08-25

Report-only, per T-2646's own instruction: nothing here deletes or
prunes a branch. `scripts/branch_stranded_work_analysis.py` is the
tooling this report is generated from; re-run it to refresh these
numbers (branch count changes daily).

## Method

Every local branch except `main` is classified against `main`:

- **merged** -- `git merge-base --is-ancestor <branch> main`, OR the
  branch's tree is byte-identical to `main`'s (diverged history only).
  Provably fully contained in `main`.
- **ticket-done** -- not merged, but every ticket id the branch's own
  changed files signal (a `tickets/T-####/` ledger path, or a
  `frob:ticket T-####` directive-comment mention anywhere in a changed
  non-ticket file) resolves to a terminal (`done`/`dropped`) state on
  `main`, active or archived.
- **stranded** -- not merged, and either no ticket signal resolves to
  terminal on `main`, or there is no ticket signal at all despite a
  non-empty diff. This is the class that can hold real, never-landed
  work.

## Result (1092 local branches scanned against main, 2026-08-25)

| class | count |
|---|---|
| merged | 258 |
| ticket-done | 646 |
| stranded | 188 |
| error | 0 |

Full per-branch detail (all 1092): `/tmp/t2646_branches.json` (not
checked in -- regenerate with `python3 scripts/branch_stranded_work_
analysis.py --json <path>`; the repo-tracked artifact here is this
summary, not the raw dump).

## UPDATE (T-2915, real-parser re-scan)

The real-parser path (`_directive_ids_via_real_parser`, mirroring
`frob.tickets._unlanded`'s T-2300 helper) landed and DOES sharpen the
"stranded" classification measurably, but two important caveats from
direct measurement:

1. **The false-positive framing below was partly wrong.** Most of
   `tests/test_gates.py`'s 389 literal "frob:ticket" text occurrences
   are GENUINE directive-position comments (this repo's own convention
   puts `frob:tests`/`frob:ticket` directives densely across a large
   gate-test file), not string-literal noise -- the real parser resolved
   128 real directive edges out of that file's 389 lexical hits, not
   near-zero. The bare regex was still over-counting (261 non-directive
   hits filtered out), just less catastrophically than first assumed.
2. **Measured improvement (same 199-branch sample, before -> after):**
   `stranded` count dropped from 35 to 13 -- branches that used to read
   "stranded" purely because a few non-terminal ticket ids got buried in
   a large regex-inflated id list now correctly resolve to `ticket-done`
   once the noise ids are gone.
3. **The real-parser full-repo re-scan does NOT complete inside a
   reasonable budget.** A full run over all ~1098 branches was killed
   at the 480s mark (still running); the original bare-regex scan
   completes the same set in ~6-7 minutes. Tree-sitter parsing every
   large file (`tests/test_gates.py` alone is ~900KB) once per branch
   that touches it, with no cross-branch content-hash cache, is the
   cost -- `frob.lang.parse_file`'s own per-process cache does not help
   here since each branch's blob is read into a FRESH scratch file path
   whose content-hash key still forces a fresh parse per branch. Running
   the real-parser path is worthwhile for a smaller, human-directed
   re-check (e.g. `--limit N`, or filtered to just the class-(c)
   branches from a prior regex pass) rather than as the default
   full-repo scan.

## IMPORTANT: a known false-positive source in the "stranded" count

The directive-comment signal is a **bare regex** over blob text
(`frob:ticket\s+(T-####)`), deliberately -- this is a standalone audit
script, not a gate, and does not import the repo's tree-sitter parser
(see the script's own docstring). The real gate-facing detector this
idea is borrowed from (`frob.tickets._unlanded._directive_ids_via_real_
parser`, T-2300) exists specifically because the bare regex "cannot
distinguish a directive-POSITION comment from the identical text sitting
inside a string literal" -- and that gap is fully live in this script.

Measured impact: several "stranded" branches carry 50-300+ "ticket ids"
in their `ticket_ids` list purely because they touch `tests/test_gates.
py` (389 literal `frob:ticket` occurrences in its own test fixtures) or
`src/frob/gates/_fix_engine_sync.py` (22 occurrences) -- neither file
change actually anchors real per-ticket work; the regex just fired on
every test-fixture string. Example: branch `t-2101`'s only real diff is
`src/frob/gates/_fix_engine_sync.py` + `tests/test_gates.py` +
`rapid-debt.jsonl` + its own `tickets/T-2101/*`, all legitimate, yet the
directive scan attributes it 300+ unrelated ticket ids because most of
them are `queued`/unresolved on main, which pushed it into "stranded"
rather than "ticket-done".

**Practical read: within the 188 "stranded" branches, prioritize by
signal quality, not by the raw count:**

1. **Highest confidence (26 branches)** -- zero ticket signal AND a
   small diff (mostly 1-5 files). These are the branches most likely to
   hold genuinely stranded, never-landed work with no ledger trace at
   all. Full list:

   `agent/T-1030-stale-base`, `agent/t0701-strata-conformance`,
   `floor-zero`, `t-1899`, `t-2032-addopts`, `t-2253`, `t0936-epic-tier`,
   `t1071-estate`, `t1094-t1096-daemon`, `t1584-residue`,
   `t2046-perf004-fix`, `w11-attribution`, `w14c-tail`, `w15b-tail`,
   `w1b-daemon`, `w1c-wire`, `w2e-coverage`, `w3g-features`,
   `w6p-checkfix`, `worktree-agent-a0e5b055eaf44d62c`,
   `worktree-agent-a7b456f8ad001994d`,
   `worktree-agent-ab1e7a41a5d0ac195`,
   `worktree-agent-abe43f5cc11d8d4e9`,
   `worktree-agent-aca95cad45f89d6a6`,
   `worktree-agent-acc8eee302be18963`,
   `worktree-agent-ad4d34f749af9b292`

2. **Medium confidence** -- a small ticket-id list (1-5 real-looking
   ids, not the 50+ fixture-noise shape) whose id(s) are genuinely
   non-terminal on `main` (`queued`/`in-progress`/unknown). Example
   candidates worth a human look: `agent/t2747-t2746` (T-2700/T-2746,
   plus one id this scan resolved to no real ticket at all -- another
   instance of the false-positive class above, not a real citation),
   `refusal-attrib` (T-1684..T-1852, several `queued`),
   `runner-wiring` (T-1315), `t-2677` (T-2691/T-2697), `t-2711`/`t-2712`/
   `t-2125` (draft ids -- may already be superseded, check whether the
   draft was promoted under a different id first).

3. **Likely false positive (majority of the 188)** -- large ticket-id
   lists (dozens to hundreds) whose branch's own real diff is 1-6 files
   including `tests/test_gates.py` and/or `src/frob/gates/_fix_engine_
   sync.py`. These read as "stranded" only because of the fixture-string
   false-positive above; their actual per-branch diff is almost always a
   single small gate/test change plus that ticket's own `tickets/T-####/`
   files, and MANY of those are very likely already covered by the
   `ticket-done` classification's own false-negative in the other
   direction (a large non-terminal id list from fixture noise can also
   mask a genuinely terminal small id list). Re-running this analysis
   with the real parser (T-2300's own `frob.lang.parse_file` machinery,
   not the bare regex) instead of grep would sharpen this class
   significantly -- filed as a follow-up rather than done here (see
   below).

## What this analysis deliberately does NOT do

- **No branch deletion.** Even the 26 highest-confidence "no ticket
  signal, small diff" branches above are not proven safe to delete --
  "no ticket signal" only means this scan's two signals did not fire,
  not that the diff is worthless or duplicated elsewhere. A human should
  look at each one (`git log <branch> -p` against its merge-base) before
  any `git branch -D`.
- **No scripted bulk action of any kind.** Per T-2646's own instruction,
  this ticket is the analysis step; a pruning mechanism (a `frob
  worktree sweep`-shaped verb extended to branches, or a reviewed
  deletion script) is deliberately left for a follow-up ticket once a
  human has looked at the class-(c) list above.
- **No re-run with the real tree-sitter parser.** Doing so would shrink
  the false-positive class significantly (see above) but means importing
  `frob.lang`, which was under another ticket's (T-1604) scope lease for
  the duration of this ticket's own work -- noted as a follow-up.

## Follow-up ticket

T-2915 (renumbers to a real id at land -- see this ticket's
Done report for the landed id) covers the real-parser re-scan described
above. The reviewed branch-pruning mechanism itself is intentionally
left unfiled here -- it should be scoped AFTER a human has looked at the
sharpened class-(c) list, not before.
