## Done report

T-4657 -- Typed ledger store API: one module every frob module reads and
writes tickets through

## WHAT changed

- src/frob/tickets/_store_api.py (NEW): the seam. Six thin, logged,
  Result-returning functions wrapping the existing mode-dispatched
  _store.py implementation:
    get_ticket / list_tickets / put_ticket           (live ledger)
    get_archived_ticket / list_archived_tickets / put_archived_ticket
                                                       (archive)
  Every function takes/returns pydantic Ticket models (never raw dicts),
  returns typani Result[T, TicketError] on the fallible path (no
  exceptions), logs each read/write at DEBUG with the ticket id and
  operation name, and logs each refusal at WARNING before returning Err.
  Each public function carries its own "# frob:doc
  docs/modules/tickets-data-storage.md#store-api-seam-t-4657" anchor.

- tests/unit/test_ledger_store_api.py (NEW): 5 tests.
    test_no_module_opens_ticket_md_directly -- the POSITIVE CONTROL named
      in the ticket. An AST scan over every src/frob/**/*.py file flags a
      raw open()/read_text()/write_text() touching a ticket.md path,
      exempting a fixed, explicit allowlist of the pre-existing direct
      accessors measured on dev at filing time (_store.py/_store_migrate.py
      as the wrapped implementation, plus every other module found by
      `grep -rln "ticket.md" src/frob | grep -v _store.py/_store_migrate.py`
      at the time this leaf was filed). New sites outside that allowlist
      fail the test; the allowlist can only shrink (as follow-up tickets
      migrate callers onto _store_api), never grow silently. On dev BEFORE
      this leaf the test fails trivially (ImportError: frob.tickets.
      _store_api does not exist) -- it passes once the module exists and
      no new bypass has appeared.
    test_ast_scan_catches_a_planted_violation -- companion control proving
      the AST scan actually fires on a real violation shape (not a
      never-matches no-op).
    test_missing_ticket_is_a_result_error -- get_ticket on an unknown id
      returns Err(TicketError.NotFound), never raises.
    test_put_then_get_round_trips -- put_ticket then get_ticket/
      list_tickets agree with each other.
    test_docs_name_store_api_as_the_entry_point -- docs/modules/
      tickets-data-storage.md actually says "_store_api" and "single entry
      point".

- docs/modules/tickets-data-storage.md: new "## Store API seam (T-4657)"
  section, with frob:describes anchors for all six functions, naming
  _store_api.py the single entry point going forward and explaining the
  seam's scope (does not migrate the existing direct callers -- that is
  deliberately left to follow-ups under T-4652/T-4656).

## WHY

Kernel decoupling epic T-4651 (LEDGER story T-4652): ticket data was
reached a dozen different ways with no single seam, which is why the
ledger, leases and land pipeline could not be pulled apart from each
other. This leaf is the rederivation step that introduces the seam without
touching the on-disk ticket.md format, the CLI surface, or the comment
DSL -- migrating the rest of the direct readers is explicit future work
(T-4656's layering leaf, T-4663, is what turns "should go through
_store_api" into an enforced rule).

## Acceptance criteria -> evidence

[1] Given _store_api.py exists, callers import it instead of opening
    ticket.md directly
    -> tests/unit/test_ledger_store_api.py::test_no_module_opens_ticket_md_directly
[2] POSITIVE CONTROL, fails on dev today, passes after this leaf
    -> tests/unit/test_ledger_store_api.py::test_no_module_opens_ticket_md_directly
[3] A fallible store operation returns Result, never raises
    -> tests/unit/test_ledger_store_api.py::test_missing_ticket_is_a_result_error
[4] docs/modules/tickets-data-storage.md names _store_api as the entry point
    -> tests/unit/test_ledger_store_api.py::test_docs_name_store_api_as_the_entry_point

All four bound via `frob ticket evidence T-4657 <node> --accepts <n> --base-ref dev`,
rebound after the LAST commit (fe0aad1de) per the pre-READY checklist's item 8.

## Commits (this ticket's own, on branch t-4657)
ac88f1335 chore(tickets): record T-4657 start transition
61e324f30 feat(tickets): add typed ledger store API seam (T-4657)
b3f2e6b9c/e158f7fca chore(tickets): record evidence for T-4657 (initial)
f9d721d71 test(tickets): add doc-contract test for _store_api entry point
c1e7d672c/81d030b42/47893f853/7fd53e729 chore(tickets): record evidence for T-4657 (corrected binding)
fe0aad1de fix(tickets): add frob:doc anchors on _store_api public functions
  (shared final commit with T-4658, same worktree/series; see T-4658's own
  why-file for its half)

## Filed
none -- no out-of-scope work discovered.

## Pre-READY checks

`frob check --only sys --files src/frob/tickets/_store_api.py --files
tests/unit/test_ledger_store_api.py --files
docs/modules/tickets-data-storage.md --base dev`:
  pass gate:DOCARCH, pass gate:PROFILE, pass gate:WAIVE
  FAIL gate:DRIFT (6 errors, all 5 waived + 1 pre-existing on
    src/frob/gates/invariants.py::load_invariants, none touching this
    ticket's files)
  FAIL gate:DSL (1 error, tests/test_app.py:387, pre-existing, not this
    ticket's file)
  FAIL gate:SELFAUDIT (1 error, design:1 SYS111 "testsuite" via-count,
    repo-wide pre-existing ratchet note, not attributable to _store_api.py)
  -> zero findings attributable to src/frob/tickets/_store_api.py,
     tests/unit/test_ledger_store_api.py, or
     docs/modules/tickets-data-storage.md.

`frob check --only arch --files <same three>`:
  pass gate:frob-arch (20 warnings, 36 waived, 549 suggestions -- all
    pre-existing repo-wide pattern-recommendations, e.g. Err(...)
    constructed in 181 files; none reference _store_api.py or its test/doc)
  -> clean, no ARCH001/LARGE001 on this ticket's files.

`frob check --only coverage --files <same three, plus T-4658's files>`
  (run jointly since both tickets share this worktree):
  Before the frob:doc fix: 6x COV001 on _store_api.py's 6 public functions
    (missing source-side frob:doc edge -- the doc-side frob:describes
    alone is not sufficient).
  Fixed by adding "# frob:doc docs/modules/tickets-data-storage.md
    #store-api-seam-t-4657" above each of the 6 functions (commit
    fe0aad1de).
  After the fix: gate:COV FAIL count dropped from 15 errors to 9, and
    zero of the remaining 9 COV001s reference _store_api.py, _new_renumber
    .py, or _renumber_v2.py (all pre-existing, in unrelated files:
    _cli_parsers/_check.py, graph/dsl.py, strata/_effects.py,
    strata/_unity_asmdef.py x2).
  -> clean for this ticket's files after the fix.

`ruff check src/frob/tickets/_store_api.py
  tests/unit/test_ledger_store_api.py`: All checks passed!
`ruff format --check` (both files): already formatted.
`ty check src/frob/tickets/_store_api.py
  tests/unit/test_ledger_store_api.py`: All checks passed! (one round-trip
  fix: `_mentions_ticket_md_literal`'s parameter narrowed from `ast.AST` to
  `ast.Call`).

Cross-ticket lease scan: `git diff --name-only dev...HEAD` for this
worktree contains only files declared in T-4657's or T-4658's own scope
(plus their own tickets/<id>/ticket.md); `grep -l "<path>"
.git/frob-leases/*.json` for every touched path returns only T-4657.json/
T-4658.json -- no cross-ticket lease conflicts.

### Changed
```
 docs/modules/tickets-data-storage.md |   41 +
 src/frob/tickets/_new_renumber.py    |   43 +
 src/frob/tickets/_renumber_v2.py     |   13 +-
 src/frob/tickets/_store_api.py       |  178 +++
 tests/unit/test_ids_assigned_once.py |  116 ++
 tests/unit/test_ledger_store_api.py  |  238 ++++
 tickets/T-4657/done-report.md        | 2351 ++++++++++++++++++++++++++++++++++
 tickets/T-4657/ticket.md             |   17 +-
 tickets/T-4658/done-report.md        | 2350 +++++++++++++++++++++++++++++++++
 9 files changed, 5342 insertions(+), 5 deletions(-)
```

### Evidence
- `tests/unit/test_ledger_store_api.py::test_no_module_opens_ticket_md_directly` (pytest node id, verified passing when recorded)
- `tests/unit/test_ledger_store_api.py::test_missing_ticket_is_a_result_error` (pytest node id, verified passing when recorded)
- `tests/unit/test_ledger_store_api.py::test_docs_name_store_api_as_the_entry_point` (pytest node id, verified passing when recorded)
- `tests/unit/test_ledger_store_api.py::test_put_then_get_round_trips` (pytest node id, verified passing when recorded)
- `tests/unit/test_ledger_store_api.py::test_archived_put_then_get_round_trips` (pytest node id, verified passing when recorded)
