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

The moved text is appended to the named ticket's body (via
`frob.tickets.set_body`, T-2678's archived-ticket-safe front door -- most
cited tickets are archived, and this route is what avoids the DuplicateId
hazard a raw `tickets/<id>/ticket.md` write previously produced) prefixed
with an idempotency marker, so running the same move twice is a no-op
rather than a duplicate append.

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

**Wiring status**: `narrative_blocks_gate` is implemented and unit-tested
but NOT YET wired into `frob check`'s live gate set -- `src/frob/gates/
__init__.py` was held by another ticket's in-progress lease for the whole
of T-2993's work window. See the `frob:waive WIRE001` directive on
`narrative_blocks_gate` for the tracking ticket.
