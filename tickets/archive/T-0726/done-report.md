## Done report

Added TICK006 (`frob.gates._tick006_phantom_filing`, wired into `tickets_gate`
alongside TICK001-005) per T-0726's Description: it scans only the substring
of a ticket's body starting at its first "Done report" heading (any markdown
heading whose text contains "done report", case-insensitive), finds every
unnegated occurrence of the word "filed" (a negation window of 40 chars
before it checks for not/never/no/n't), and extracts every
`T-\d{4}`/`T-draft-[0-9a-f]{8}`-shaped token within 300 chars forward of
each such occurrence. Any extracted id that resolves to no block in either
the active queue or `tickets-archive.md` is a TICK006 ERROR. Restricting the
scan to Done-report content (never Description/Plan prose) is deliberate:
this repo's own ledger routinely narrates other tickets' ids in ordinary
Description text, and scanning that would be a false-positive generator on
extremely common, legitimate prose -- verified directly with a real excerpt
as a no-fire fixture (`test_description_prose_mentioning_other_ticket_is_silent`,
using T-0570's actual NOTE text).

Grammar documented in docs/modules/gates.md ("TICK006 (T-0726)" section plus
a rule-catalog row). TICK006 is waivable (not added to `_UNWAIVABLE_RULES`).

10 tests added to tests/test_gates.py::TestTick006PhantomFiling, all pass:
`uv run pytest tests/test_gates.py -k Tick006 -p no:cacheprovider -q`.

### Ledger disposition (initial pass + reviewer-corrected)

Cold-ran TICK006 against this repo's real ledger: 98 pre-existing Done
reports fired. One (T-0367, T-0363's Done report) traced to a genuine
ledger-corruption bug (a missing `<!-- ticket:T-0367 -->` marker had
silently absorbed T-0367's whole yaml block into T-0363's body) -- fixed
directly, filed T-0740 (ex-draft, id lost at land) to investigate whether other blocks share
the defect (kept open, genuinely unresolved). The remaining 97 were the
T-0577 draft-loss shape.

**First disposition pass** used a coordinator-supplied list of 10 already-
refiled successors plus 3 more found by direct ledger cross-reference
(T-0104->T-0107, T-0105->T-0108, T-0727 (ex-draft, id lost at land)->T-0727), rewriting those
13 to name the real id, and negating the remaining 84 (the negation-
grammar word TICK006 recognizes was rewritten in place -- see
docs/modules/gates.md's TICK006 section for the exact recognized forms --
landing a negation inside TICK006's own pre-word window; the dead token
annotated "(never refiled)").

**Reviewer REJECTED on one finding**: the negation at T-0160's Done report
for the draft id ending in `7bae70b7` was FALSE -- tickets-archive.md's
T-0486 (state done, identical scope `src/frob/dup/_legacy_py.py`)
self-identifies as its
recovered successor ("Recovered filing: T-0486 (ex-draft, id lost at land) was filed... its
ledger block was lost in a merge"). My scripted pass had cross-referenced
only the coordinator's known-successor list, never recovered-filing
self-identifications elsewhere in the ledger. Corrected: T-0160's line now
reads "Filed: T-0486 (its original draft id was lost at land; recovered as
T-0486, see T-0486's own body) ..." -- the literal dead draft token is
NOT repeated in the annotation (an earlier version of this same fix did
repeat it, which reintroduced an id-shaped token into TICK006's own
forward-scan window and kept the violation firing; caught by re-running
the gate before finalizing, not assumed clean).

**Systematic re-scan performed** (my own verified sweep, method below, not
inherited from the reviewer's spot-check): for every one of the 82 draft
ids left negation-annotated (84 minus 7bae70b7's correction, minus the
d49c456f/T-0104/T-0105 rewrites which are refiled not negated), grepped
BOTH `tickets.md` and `tickets-archive.md` for the literal id string
appearing ANYWHERE, then inspected every hit that was NOT the id's own
negation line for successor-claim language (`recovered`, `refiled`,
`renumbered`, `absorbed`, plus manual reading of every hit regardless of
keyword match, since keyword matching alone is exactly the blind spot that
caused the 7bae70b7 miss).

- **82 ids scanned.**
- **148 total literal occurrences** of those ids across both ledgers.
- **8 ids had >=1 occurrence outside their own negation line** (the other
  74 ids' only ledger occurrence is their own negation line -- nothing
  further to inspect for those): T-draft-2a3adb6d, T-draft-e6aafc2f,
  T-draft-aa52c66f, T-draft-5443bd5e, T-draft-b4a0b4be, T-draft-94774bc5,
  T-draft-9557a879, a lost draft (its scope is covered by T-0635).
- **All 8 inspected by hand, individually** (not just keyword-matched):
  - T-draft-2a3adb6d: tickets-archive.md prose states it "was resolved
    during T-0253's landing -- coordinator stamped 0.3.0 in that motion --
    so it is dropped here" -- resolved INLINE, never filed as a standing
    ticket; negation correct.
  - a lost draft (its scope is covered by T-0635): tickets.md explicitly states "T-0636's
    a lost draft (its scope is covered by T-0635) duplicated it and needs no refile" -- explicit
    confirmation; negation correct.
  - T-draft-5443bd5e: a separate, unrelated ticket's body mentions being
    "Dropped ... duplicate of T-draft-5443bd5e, same stale-base worktree
    artifact -- T-0416 evidence collects on main" -- describes a SEPARATE
    duplicate attempt that was ALSO dropped, not a successor for this
    draft; negation correct.
  - T-draft-94774bc5: a later, unrelated ticket's body describes this
    exact hex string being involved in a genuine ledger-corruption
    incident (a different ticket's finalized id got overwritten back to
    this draft form by a write-path bug) -- an incident report mentioning
    the string, not a successor filing; negation correct.
  - T-draft-9557a879: two other mentions, both explicitly "(not touched)"/
    "rather" (negative framing, consistent with never-refiled); negation
    correct.
  - T-draft-e6aafc2f, T-draft-aa52c66f, T-draft-b4a0b4be: their only other
    occurrences are inside OTHER tickets' yaml `scope_changes.reason` text
    (e.g. "T-draft-aa52c66f dup work maps to tests/test_dup.py") -- pure
    scope-rationale prose referencing the old draft label, not a filing
    claim, and not inside any Done-report body TICK006 scans; negation
    correct.
  - **0 of the 8 revealed a missed successor.** The reviewer's own sweep
    found exactly one (7bae70b7/T-0486, now fixed); mine independently
    confirms no second one exists among the 82 remaining negations.

### Idempotency bug found and fixed mid-pass

The disposition script's re-run safety check was buggy (it reported
"already fixed, skip" incorrectly in some cases and "needs fixing" in
others without a real basis) -- replaced with a direct before/after text
comparison (apply the transform, keep it only if the text actually
changed), verified by running the script twice back to back with 0 further
changes on the second run. This mattered in practice: `tickets.md`/
`tickets-archive.md` got reverted by an intervening `git merge main` THREE
separate times over the course of this pass (concurrent landings elsewhere
in the ledger), and each time required a clean re-application -- a genuinely
new phantom pair also surfaced this way (T-0587's Done report, landed on
main after this ticket's original scan: T-0730 (ex-draft, id lost at land) and
a lost draft (superseded by T-0730), both already self-disclosed in T-0587's own prose as
lost/mistaken and confirmed to have no real successor in either ledger;
negated the same way).

### Verification (every claim below is a command actually run and read)

- `frob.tickets._store.load_all`/`load_archive` parse clean (209/517 ids)
  after every edit in this final state.
- `git diff -- tickets.md tickets-archive.md` grepped against every
  yaml/state field name (id:/state:/title:/kind:/origin:/created:/
  priority:/blocked_by:/parent:/scope:/scope_changes:/evidence:/
  attachments:/acceptance:/threat:/component:/labels:) returns 0 matches.
- `uv run frob check --only tickets`: **gate:TICK 0 errors, 1 warning
  (pre-existing TICK003), 0 waived.**
- `uv run frob check --ticket T-0726`: **0 errors, 0 FAILing gates at
  all** -- every gate line reads `pass`, including REL001 (resolved by a
  concurrent version bump landing on main during this pass).
- `git diff main --diff-filter=D --stat` empty after every merge.

Dropped T-draft-a7c33c11 (`frob ticket drop ... --absorbed-by T-0726`):
its disposition work is complete here. Kept T-0740 (ex-draft, id lost at land) (missing-
marker ledger-corruption investigation): genuinely unresolved, only one
instance found and fixed.

Gates: `uv run frob ticket sweep T-0726` (fresh pre-work sweep) then
`uv run frob check --ticket T-0726` clean end to end, as above.
`uv run ruff check`/`uv run ruff format --check` clean on
src/frob/gates/__init__.py and tests/test_gates.py.

### Changed
```
 docs/modules/gates.md      |  67 ++++++++++
 src/frob/gates/__init__.py | 132 ++++++++++++++++++-
 tests/test_gates.py        | 195 ++++++++++++++++++++++++++++
 tickets-archive.md         | 316 +++++++++++++++++++++++----------------------
 tickets.md                 | 303 ++++++++++++++++++++++++++++++++++++++-----
 5 files changed, 820 insertions(+), 193 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestTick006PhantomFiling::test_phantom_filed_colon_fires` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestTick006PhantomFiling::test_phantom_filed_as_fires` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestTick006PhantomFiling::test_filed_colon_real_active_id_is_silent` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestTick006PhantomFiling::test_filed_colon_none_is_silent` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestTick006PhantomFiling::test_filed_as_real_archived_id_is_silent` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestTick006PhantomFiling::test_negation_not_filed_is_silent` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestTick006PhantomFiling::test_negation_no_ticket_filed_is_silent` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestTick006PhantomFiling::test_description_prose_mentioning_other_ticket_is_silent` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestTick006PhantomFiling::test_no_done_report_heading_is_silent` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestTick006PhantomFiling::test_filed_bare_draft_without_colon_fires` (pytest node id, verified passing when recorded)
