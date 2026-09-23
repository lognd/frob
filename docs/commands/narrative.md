# frob narrative

Detector and author-invoked migration for `# T-####:` narrative comment
blocks (T-2993, child of the T-2994 doctrine epic): code and docs carry
UTILITY -- what a reader about to modify or reuse this needs to know;
tickets carry NARRATIVE -- why we arrived here, what a prior attempt got
wrong. `frob narrative move` relocates the NARRATIVE half of one block
into the ticket it already names, leaving the UTILITY half (if any) in
place plus a one-line reference.

Deliberately NOT part of `frob ticket land` (T-2994's own doctrine: land
may CHECK, never REWRITE -- see `src/frob/narrative/_migrate.py`'s module
docstring for the full reasoning). This is an author/agent-invoked verb,
reviewable in the diff like any other source edit.

## Usage

```
frob narrative move FILE LINE [--keep-file PATH] --reason TEXT [--dry-run]
```

- `FILE`/`LINE`: the source file and the 1-indexed line the `# T-####:`
  comment block starts on.
- `--keep-file`: a text file containing the exact lines (verbatim,
  including the leading `#`) to leave in place -- the caller's own
  KEEP/MOVE judgement (T-2993/T-2994 are explicit this is not something
  the tool decides for you). Omit to move the whole block, leaving only
  the one-line reference.
- `--reason`: required, forwarded to `frob.tickets.set_body`'s own
  `--reason` requirement for the ticket-body append.
- `--dry-run`: print what would change without writing anything.

The moved text is appended to the named ticket's body via
`frob.tickets.set_body`, prefixed with an idempotency marker, so running
the same move twice is a no-op rather than a duplicate append. See
T-2678 for the history behind this.

**Directive lines are always kept (T-5108).** A `# frob:<verb>` line
inside the moved extent -- `frob:doc`, `frob:ticket`, `frob:tests`,
`frob:waive`, `frob:invariant`, and any backslash-continued payload
lines under it -- is NEVER moved into the ticket body, whether or not
`--keep-file` named it: `run_narrative_command` (`_directive_keep_lines`,
`src/frob/narrative/_cli.py`) auto-detects every such line in the block
and treats it as an implicit `--keep-file` entry before calling
`migrate_block`. These lines are graph-load-bearing edges/waivers/
invariants, never change-narrative prose, and the default (no
`--keep-file`) move used to delete them along with the rest of the
block -- the measured incident this fix exists for: `frob:doc` anchors,
a `frob:waive PII012`, and a `frob:invariant` block, all lost across
three separate moves and restored by hand before commit.

## Bulk mode (T-4697)

The single-block form above is the precise escape hatch; it does not
scale to T-4691's own measured 507 over-cap comment runs, each of which
would otherwise need a hand-typed `file line` invocation and a manual
search for the block's start line. Bulk mode (`frob.narrative._bulk`)
sweeps a FILE or a DIRECTORY (recursive) in one pass:

```
frob narrative move PATH [--apply] --reason TEXT
```

- `PATH`: a file or a directory. A directory is walked recursively over
  every `.py`/`.strata`/`.md` file (`discover_targets`).
- Discovery reuses NARR001's own `# T-####:`-lead comment-run detector
  (`frob.gates._narrative_blocks._iter_blocks`) for source files, and a
  blank-line-delimited-paragraph scan for markdown (mirroring
  `_migrate.paragraph_at`'s per-call shape, T-2995).
- Omitting `--apply` (the default) prints the PLAN -- every block found
  and the ticket id it resolves to -- and writes neither a source file
  nor a ticket body.
- `--apply` performs the moves: `frob.narrative._migrate.migrate_block`
  plus `frob.tickets.set_body` (T-2678's archived-ticket-safe front
  door, the identical engine the single-block path already uses) for
  each block whose cited ticket actually exists (live OR archived).
- CONDENSING IS THE AUTHOR'S JOB: bulk mode moves each block VERBATIM,
  no `keep_lines` split -- the existing `file line` + `--keep-file` form
  is still how a caller keeps a load-bearing sentence in place for one
  block; bulk mode does not replace it, only the "find and invoke 507
  times by hand" cost.
- A block citing NO ticket, or a ticket id that resolves to nothing at
  all, is SKIPPED and reported -- never deleted, never invented a
  destination for.
- IDEMPOTENT: a block's own one-line replacement (`# see T-####` /
  "See T-#### for the history behind this.") is excluded from
  re-detection, so a second `--apply` over the same tree is a no-op.

Positive control (T-4697's own acceptance): a fixture directory of
three files -- one citing a live ticket, one citing an archived ticket,
one citing no ticket. `--apply` moves the first two into their ticket
bodies (leaving pointers), skips and reports the third, `frob ticket
list` exits 0 afterward, and a second `--apply` changes nothing.

Registration note (T-4697): wiring `PATH`/`--apply` onto the `frob
narrative move` argparse subcommand in `src/frob/narrative/_cli.py` is
deferred -- that file is leased by T-4546. `src/frob/narrative/_bulk.py`
is otherwise complete and independently tested; see T-4697's Done
report for the exact CLI-wiring hunk.

## DOCARCH002 check 2's Tier-A auto-fix (T-4694)

`frob check --fix` performs the move automatically for DOCARCH002 check 2
findings (`src/frob/gates/_docarch_structural.py::scan_citation_shape` --
a `T-####` citation with 2+ plain comment lines under it, not itself a
`frob:ticket`/`frob:todo` directive or a single-line `# see T-####`
pointer): `frob.gates._fix_engine.fix_docarch002_narrative_move` is
registered in `TIER_A_HANDLERS` under rule id `DOCARCH002`, using the
SAME `migrate_block`/`set_body` engine this page's single-block form
already uses.

**THE SPLIT IS A JUDGEMENT, NOT A REGEX (T-2994 constraint 2).** This
Tier-A fix always moves the WHOLE cited comment run -- it has no
`--keep-file` equivalent and cannot decide that some of the run's prose
is load-bearing utility worth keeping in place. Do not run `frob check
--fix` repo-wide expecting it to preserve a load-bearing sentence inside
a flagged run; that split is a human/agent review, done via this page's
single-block `--keep-file` form, not an unattended auto-fix.

The ledger write (`set_body`) happens BEFORE the file rewrite, so a
ticket-body write failure leaves the source file completely untouched
(T-2994 constraint 1: MOVE, NEVER DELETE) rather than losing the
narrative from both places. Archived-ticket-safe (T-2994 constraint 3,
the DuplicateId hazard `set_body`'s own T-2678 routing already handles)
and idempotent (T-2994 constraint 4: `migrate_block`'s own marker check
makes a second `--fix` pass a no-op). A citation whose lead line is
already a `frob:ticket`/`frob:todo` directive is never a DOCARCH002 check
2 finding in the first place, so this handler never touches it.

## NARR001 (the detector)

`src/frob/gates/_narrative_blocks.py::narrative_blocks_gate` flags any
`# T-####:`-led comment block over `NARR001_THRESHOLD_LINES` (12) lines
in a tracked `.py`/`.strata` file. It flags candidates for review, it does
NOT decide the keep/move split itself -- a short block that explains
something load-bearing (the `_socketd.py`/T-2961 example this ticket was
built around: "a CLASS statement referencing a missing base at module
scope raises AttributeError at IMPORT time, not when the daemon is used")
must stay quiet regardless of how many tickets it cites, and a long block
that is pure cross-reference archaeology must fire regardless of how
short its sentences are.

Ships at WARN (T-2993 acceptance: the existing ~1,728 blocks are a
burn-down, not a day-one failure); promote to ERROR only after that
burn-down, mirroring the TICK011/T-2372 precedent.

`narrative_blocks_gate` is wired into `frob check`'s live gate set as
`NARR001` (`--only narrative_blocks`), T-3014.

T-3020: `narrative_blocks_gate`'s own repo-wide `fs.read` (every tracked
`.py`/`.strata` file's text) is declared on the `gates` strata node's
`may "fs.read"` via-list (`design/frob.strata`) -- T-3029 had already
added `src/frob/gates/_narrative_blocks.py` there, so the SELFAUDIT001
waiver this function used to carry (recorded as blocked on
`design/frob.strata`'s lease state) was stale by the time this ticket
picked it up, and is now removed outright rather than re-justified.
