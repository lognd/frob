# CLI regrouping: verb-group taxonomy (T-1238)

User directive 2026-07-29: `frob`'s top-level surface is intimidating (36
entries as of this writing -- `docs/modules/cli.md`'s generated table).
Group related commands under a small number of intent-named verb groups
instead of a flat list, without dropping any existing invocation. This
is the design phase T-1238's acceptance criteria require BEFORE any group
beyond `frob explore` is implemented.

## Method

Every current top-level command (the live generated table in
`docs/modules/cli.md`) sorted into one candidate bucket below. A command
appears in exactly one bucket -- the plumbing tier (`docs/modules/cli.md`'s
"Plumbing tier -- kept, unchanged" section) is not exempt from having a
home, it just does not need a NEW group of its own.

## Candidate taxonomy

Every `frob <group>` invocation named below (through the end of this
section) is a NOT-YET-BUILT candidate verb group this doc is proposing,
not a live CLI surface -- `frob explore`, marked IMPLEMENTED, is the sole
exception. Each is waived DOC006 individually below with this same
reasoning, since that is the point of a design doc.

### `frob explore` -- navigation (T-1238, IMPLEMENTED this ticket)

`map`, `outline`, `xref`, `docs-search` (from `frob docs --search`). The
epic's first concrete slice -- see `docs/modules/cli.md`'s "Navigation
commands" section for the un-deprecation this required.

### `frob quality` -- correctness/hygiene gates (T-1567, IMPLEMENTED)

`check`, `test`, `dup`, `arch`, `bind`, `cycle`, `mutate`, `perf` --
`frob quality check`, `frob quality test`, `frob quality dup`, `frob
quality arch`, `frob quality bind`, `frob quality cycle`, `frob quality
mutate`, `frob quality perf`. A standalone `fix` verb is not, and never
was, a live top-level command -- `frob check`'s auto-fix handlers cover
that ground already, so it was never added under this group either.
Follows the `frob explore` migration policy below: every member's
standalone top-level form stays a permanent alias. `bind` is dispatched
directly by `frob.__main__._dispatch` (mirroring top-level `bind`'s own
special case, T-0355) rather than through `quality_runner.run`, since
`bind_runner.run` takes raw argv, not an `AppConfig`.

<!-- frob:waive DOC006 reason="T-1238 design proposal: not-yet-built candidate verb group name, not a live CLI surface" -->
### `frob tickets` -- the ticket queue

`ticket` already IS a verb group (`frob ticket new/start/close/...`) --
no top-level regrouping needed, it is the existing precedent this whole
epic generalizes from. `debt`, `deprecated` are ticket-adjacent
(disclosed-and-tracked deferred work, same shape as a ticket queue
<!-- frob:waive DOC006 reason="T-1238 design proposal: candidate subcommand names for the not-yet-decided 'frob tickets' regrouping" -->
without the lifecycle) -- candidates for `frob tickets debt` / `frob
tickets deprecated` as siblings of `frob ticket`, pending a decision on
whether folding them under the existing `ticket` verb (`frob ticket
<!-- frob:waive DOC006 reason="T-1238 design proposal: candidate subcommand names for the not-yet-decided 'frob tickets' regrouping" -->
debt`) or a new parent `tickets` (plural) that CONTAINS `ticket` reads
better; this doc does not resolve that naming question, a later
implementation ticket does.

### `frob design` -- design-knowledge surfaces (T-1568, IMPLEMENTED)

`sys` (strata design-model applications), `registry` (unified
design-knowledge registry), `docs` (bare extract/`--overview`, NOT
`--search`, which stays exclusive to `frob explore docs-search`),
`graph` (obligation graph queries), `exports` -- `frob design sys`,
`frob design registry`, `frob design docs`, `frob design graph`, `frob
design exports`. Follows the `frob explore`/`frob quality` migration
policy below: every member's standalone top-level form stays a
permanent alias.

### `frob vet` -- supply-chain

Already effectively its own concern (`frob vet` today: lockfile allow
conformance, quarantine, typosquat, lifecycle scripts, osv advisories).
No regrouping needed -- it is a single command with its own internal
subcommand structure already, same precedent as `frob ticket`.

### `frob ops` -- release/fleet/infra plumbing (T-1569, IMPLEMENTED)

`release`, `natives`, `doctor`, `clean`, `fleet`, `deploy`, `scaffold`,
`gitlog`, `stats` -- `frob ops release`, `frob ops natives`, `frob ops
doctor`, `frob ops clean`, `frob ops fleet`, `frob ops deploy`, `frob ops
scaffold`, `frob ops gitlog`, `frob ops stats`. `registry` stayed under
`frob design` (T-1568), not duplicated here -- the "could go either way"
note above is resolved in favor of the design-knowledge bucket, since
`frob registry` is a read-only design-knowledge inspection tool, not an
operational/infra action. Follows the `frob explore`/`frob quality`/
`frob design` migration policy below: every member's standalone
top-level form stays a permanent alias.

### `frob serve` -- already a single verb

MCP stdio adapter; stays top-level, single command, no subgroup needed
(same "already atomic" reasoning as `vet`).

### Unsorted / kept top-level (deliberately, not an oversight)

- `frob ack` -- acknowledges doc-drift digests; small, frequent,
  cross-cutting (used by `check`, `document` workflows alike) -- stays
  top-level rather than nested under any one group.
- `frob agent` -- dispatched-agent guard env; infra glue, not a
  developer-facing analysis/workflow verb, stays top-level.
- `frob worktree` -- dispatched-agent worktree management; same
  reasoning as `agent`.
- `frob parse` -- tool-output adapter (pytest/ruff/ty/...); used as a
  pipe target by other tooling, changing its invocation shape has the
  widest blast radius of any command here -- stays top-level.
- `frob fmt` -- `frob:` directive canonical-form rewrite; small,
  frequent, cross-cutting like `ack`.

## Migration / alias policy

Every regrouped command's standalone top-level form is kept as a
PERMANENT alias onto the identical runner code -- not a time-boxed
transition shim, no sunset date, no deprecation warning. This is the
concrete lesson T-1238 itself encodes: the T-0580/T-0802 navigation
sunset was rescinded specifically because a real sunset with a real
deletion date creates exactly the kind of "lazy developer" footgun this
project's other tooling exists to prevent -- a user or agent muscle-
memory invocation silently breaking on a date nobody was tracking.
`frob explore`'s implementation (this ticket) is the concrete precedent
every later group in this taxonomy should follow:

1. Add the new verb-group subparser with subcommands that reuse the
   EXACT SAME `AppConfig` dests as the existing top-level parsers (no new
   fields beyond the one `<group>_command: str | None` dispatch dest).
2. Add a `<group>_runner.py` that dispatches on `<group>_command` straight
   into the existing per-command runner's `run(cfg)` -- no duplicated
   business logic, ever.
3. Remove any `frob:deprecated` directive and runtime sunset warning from
   the members being un-deprecated by the regrouping (only applies to
   `explore`'s members; other groups below were never deprecated).
4. Leave the standalone top-level parser and runner in place, unchanged
   in behavior, permanently.
5. Regenerate `docs/modules/cli.md`'s command table
   (`frob docs --sync-commands .`) and update this doc's own prose
   pointers in the same change.

## Help-surface rework (acceptance[0], not yet implemented)

Acceptance[0] on T-1238 wants the top-level `frob --help` output itself
to present the small set of verb groups first, with the still-supported
flat top-level commands demoted to a "also available directly" style
listing rather than intermixed alphabetically. That is a `_build_parser`/
`argparse` formatting change (custom `HelpFormatter` or grouped
`add_argument_group`-equivalent for subparsers -- argparse's own
subparsers action does not natively support named groups, so this needs
either a custom formatter or restructuring the subparser registration
order with section-header pseudo-entries) -- left to its own
implementation ticket rather than folded into `explore`'s launch, per
this epic's own instruction to do the design phase for the FULL taxonomy
before implementing anything beyond `explore`.

## Ticket breakdown

- T-1238 (this epic) -- design doc (this file) + `frob explore` group,
  DONE.
- Follow-on tickets filed for the remaining groups (`quality`, `design`,
  `ops`, the `tickets`/`ticket` naming question) and for the help-surface
  rework: see the epic's Done report for the exact ids filed alongside
  this doc.
