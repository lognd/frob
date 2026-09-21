## Done report

T-4697: frob narrative bulk mode

WHAT changed
------------
- src/frob/narrative/_bulk.py (new): bulk-mode engine.
  - `discover_targets(target)`: `target` itself if a file, else every
    `.py`/`.strata`/`.md` under it recursively, sorted.
  - `find_blocks(path, text)`: reuses `frob.gates._narrative_blocks.
    _iter_blocks` (NARR001's own `# T-####:`-lead detector) for source
    files, and a new `_find_markdown_paragraphs` for `.md` (blank-line-
    delimited paragraph citing a T-#### id anywhere in it, mirroring
    `_migrate.paragraph_at`'s extent shape). A `_REFERENCE_LINE_RE`
    exclusion keeps the block's own one-line replacement from being
    rediscovered forever -- this is the idempotency mechanism (see
    below), not a second marker check.
  - `plan_bulk(target)`: the dry-run listing -- every block found, its
    resolved ticket id (or `None`), status `"planned"`. Writes nothing.
  - `apply_bulk(target, *, apply, reason, root)`: `apply=False` returns
    `plan_bulk` untouched; `apply=True` walks each file's blocks
    back-to-front (so an earlier move's line-count shrink never
    invalidates an unprocessed block's line numbers) and, per block,
    calls the EXISTING `frob.narrative._migrate.migrate_block` +
    `frob.tickets.set_body` (T-2678's archived-ticket-safe front door --
    reused, not reimplemented) when the cited ticket exists (active or
    archived), or reports `"skipped"` when the block cites no ticket, or
    `TicketError.NotFound` when it cites one that does not exist.
- tests/narrative/test_bulk.py (new): 9 cases -- discovery (source lead
  block + markdown paragraph + reference-line exclusion), target
  resolution (file vs. directory), the dry-run plan, and the ticket's own
  three-file positive control (live/archived/untargeted) for apply,
  idempotency, and `--apply`-omitted-writes-nothing.
- docs/commands/narrative.md: new "Bulk mode (T-4697)" section (usage,
  discovery/reuse notes, idempotency mechanism, the positive control,
  and the CLI-wiring deferral note below).

WHY
---
`frob narrative move` today is `file line` -- one block per invocation,
no directory, no `--apply`. Against T-4691's own measured 507 over-cap
comment runs in src/frob alone, that is 507 hand-typed invocations, each
needing the agent to first find the block's start line -- the cost
T-4691's cluster tickets are sized around. This closes that gap without
touching the existing single-block path (still the precise `--keep-file`
escape hatch) or reimplementing the write/archived-ticket/idempotency
machinery `_migrate.py`/`set_body` already prove out.

Acceptance criteria (T-4697's ticket.md, all five)
--------------------------------------------------
1. Fixture directory (live/archived/no-ticket) + `--apply` -> first two
   in ticket bodies with pointers, third SKIPPED and reported, never
   deleted.
   test_apply_moves_live_and_archived_skips_untargeted
2. Second `--apply` is a no-op (idempotency, T-2994 constraint 4).
   test_second_apply_is_idempotent_noop
3. Archived-ticket block appends to the archived path; `frob ticket
   list` (via `load_all` succeeding) exits clean afterward (T-2994
   constraint 3).
   test_apply_moves_live_and_archived_skips_untargeted (asserts
   `load_all(tmp_path).is_ok` after the sweep)
4. The existing `file line` positional form still works unchanged.
   tests/test_narrative_migrate.py::TestNarrativeCli::test_dry_run_reports_without_writing
   (pre-existing test, unmodified by this ticket -- proves the single-
   block path this ticket does not touch remains green)
5. `--apply` omitted -> plan printed, neither source nor ledger written.
   test_apply_false_writes_nothing

DEFERRED (leased files, per BRIEF's cross-ticket-lease protocol)
------------------------------------------------------------------
Two registration hunks are NOT applied -- both target files were leased
by other in-progress tickets at land time:

1. `src/frob/narrative/_cli.py` (leased T-4546): wire `PATH`/`--apply`
   onto `frob narrative move`'s argparse subcommand and dispatch to
   `apply_bulk` when `args.file` is a directory or `--apply`/no `line`
   is given (keeping the existing `file line` two-positional form as the
   single-block path, matching this module's own docstring's "PATH,
   not FILE LINE" framing for the new form only). `_bulk.py` itself is
   complete and independently tested via direct import, so the CLI
   wiring is a thin dispatch layer once T-4546 lands.
2. `design/frob.strata` (leased T-4112, T-4113): three findings
   surfaced by `frob check --only sys`, all attributable to
   `_bulk.py`, none fixable without editing this leased file:
   - SYS003: undeclared cross-component import (narrative -> gates,
     for `frob.gates._narrative_blocks._iter_blocks`) -- needs a `Flow`
     declared from the `narrative` design node to `gates`.
   - SYS100/THREAT004 (x3): undeclared `fs.read`/`fs.read`/`fs.write`
     capability effects at `_bulk.py:190,300,334` (the `read_text`/
     `write_text` calls `plan_bulk`/`apply_bulk` make) -- needs `via`
     entries on the `narrative` node, mirroring how `_migrate.py`'s own
     file I/O is presumably declared (that module's `_cli.py` caller,
     not `_migrate.py` itself, does the writes today, which is why this
     is new for `_bulk.py`).
   - SYS110 (x2): `apply_bulk`/`plan_bulk` are public in code but not
     declared in the `narrative` node's `interface=` list -- needs
     `attr interface=apply_bulk,plan_bulk` added (or extended) on that
     node.

Land with the cross-ticket-lease flag noted for both. T-4697's own scope
(`_bulk.py`, its tests, and the docs section) is self-contained and
independently tested via direct import even before either wiring lands.

Filed: none (no out-of-scope work found beyond the two deferred hunks
above, which are this ticket's own remaining scope, blocked only by two
leases).

Evidence bound
--------------
- tests/narrative/test_bulk.py::TestApplyBulk::test_apply_moves_live_and_archived_skips_untargeted
- tests/narrative/test_bulk.py::TestApplyBulk::test_second_apply_is_idempotent_noop
- tests/test_narrative_migrate.py::TestNarrativeCli::test_dry_run_reports_without_writing
- tests/narrative/test_bulk.py::TestApplyBulk::test_apply_false_writes_nothing

Commits
-------
- 15a267b6b feat(narrative): add bulk mode over a file or directory (T-4697)
- 19a95f1ce fix(narrative): add frob:doc/frob:ticket edges for COV001/COV002
- d064a728c chore(tickets): record evidence for T-4697 (HEAD)

## Pre-READY checks

`frob check --only sys --files src/frob/narrative/_bulk.py --files tests/narrative/test_bulk.py --files docs/commands/narrative.md --base dev`:
  FAIL overall -- SELFAUDIT001 (x5: SYS100 fs.read x2, fs.write x1, SYS110 x2) and SYS003 (undeclared cross-component import narrative->gates), all attributable to `_bulk.py`, all deferred to design/frob.strata per the leased-file protocol above (leased T-4112/T-4113). No other findings in the "sys" bundle named this ticket's files.

`frob check --only arch --files src/frob/narrative/_bulk.py --base dev`:
  WARN, 0 errors, 21 warnings -- all pre-existing god-module warnings on unrelated files; none on _bulk.py.

`frob check --only coverage --files src/frob/narrative/_bulk.py --base dev` (first pass found COV001 on BulkItem/BulkPlan/moved_count/skipped_count and COV002 on every changed test symbol in test_bulk.py -- fixed in commit 19a95f1ce; second pass below is post-fix):
  Post-fix: `frob check --only coverage --files src/frob/narrative/_bulk.py --files tests/narrative/test_bulk.py --base dev` -- grepped full output for `_bulk.py`/`test_bulk.py`, zero hits in any finding line.

`ruff check src/frob/narrative/_bulk.py tests/narrative/test_bulk.py`: All checks passed!

`ruff format --check` (via `ruff format`, no diff on second run): 2 files already formatted / unchanged

`ty check src/frob/narrative/_bulk.py`: All checks passed!

pytest: `PYTHONPATH=$(pwd)/src .venv/bin/python -m pytest tests/narrative/test_bulk.py -p no:cacheprovider -q` -> 9 passed, 0 failed.

### Changed
```
 docs/commands/narrative.md    |   49 ++
 src/frob/narrative/_bulk.py   |  344 +++++++++++
 tests/narrative/test_bulk.py  |  252 ++++++++
 tickets/T-4697/done-report.md | 1317 +++++++++++++++++++++++++++++++++++++++++
 tickets/T-4697/ticket.md      |   33 +-
 5 files changed, 1980 insertions(+), 15 deletions(-)
```

### Evidence
- `tests/narrative/test_bulk.py::TestApplyBulk::test_apply_moves_live_and_archived_skips_untargeted` (pytest node id, verified passing when recorded)
- `tests/narrative/test_bulk.py::TestApplyBulk::test_second_apply_is_idempotent_noop` (pytest node id, verified passing when recorded)
- `tests/test_narrative_migrate.py::TestNarrativeCli::test_dry_run_reports_without_writing` (pytest node id, verified passing when recorded)
- `tests/narrative/test_bulk.py::TestApplyBulk::test_apply_false_writes_nothing` (pytest node id, verified passing when recorded)
