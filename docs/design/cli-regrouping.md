# CLI regrouping: verb-group taxonomy (T-1238)

REVERTED (T-4690/T-4687, 2026-09-2x): the three groups this doc's own
"Method"/"Candidate taxonomy" sections below justify and mark
IMPLEMENTED -- `frob quality`, `frob design`, `frob ops` -- are DELETED
(deprecation shims, sunset 2026-12-01), not kept as permanent aliases.
MEASURED reason (T-4690's own ticket body): each group verb ADDED four
top-level names (the group itself plus zero net reduction in the flat
surface, since this doc's own "Migration / alias policy" section below
required every member's standalone top-level form to ALSO stay a
permanent alias) and REMOVED zero -- `_mirror_subparser` (T-4520)
literally wrote the same `ArgumentParser` object into two `choices`
dicts, proving the duplication in code, not just in this doc's own
taxonomy exercise. `frob explore` (this section's own T-1238 slice) is
the ONE exception and the surviving verb group: T-4690's coordinator
amendment (2026-09-19) kept it as the single "read-only analysis" verb
and T-4695 later added `gitlog`/`stats`/`graph-query`/`graph-why`/
`graph-affects`/`debt`/`deprecated` onto it, the same way this doc's own
"Migration / alias policy" section describes -- just with a sunset
clock on the OLD spelling instead of a permanent alias. The sections
below are preserved as the historical record of why the groups were
built; they are not a description of the live CLI surface.

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

### `frob ticket` -- the ticket queue, plus `debt`/`deprecated` (T-1570, RESOLVED/IMPLEMENTED)

`ticket` already IS a verb group (`frob ticket new/start/close/...`) --
no top-level regrouping needed, it is the existing precedent this whole
epic generalizes from. `debt`, `deprecated` are ticket-adjacent
(disclosed-and-tracked deferred work, same shape as a ticket queue
without the lifecycle) and are now `frob ticket debt` / `frob ticket
deprecated`, siblings of every other `frob ticket` subcommand.

DECISION (T-1570): fold under the EXISTING singular `ticket` verb, not a
new plural `tickets` parent. <!-- frob:waive DOC006 reason="frob tickets (plural) is a rejected, never-built candidate this DECISION explicitly argues AGAINST -- per this doc's own module docstring, every not-yet-built candidate verb group is waived DOC006 individually" -->A `frob tickets` (plural) top-level command
whose only job is containing the existing singular `frob ticket` verb
group would read as confusing near-duplication right next to it (<!-- frob:waive DOC006 reason="same rejected-candidate reasoning as the frob tickets waiver immediately above" -->`frob
tickets ticket new`?) for zero benefit over just adding two more
subcommands to the verb group that already exists -- worse than the
status quo by this epic's own "delete or simplify, never add a
mechanism to manage sprawl" standing directive. Standalone `frob debt`/
`frob deprecated` stay permanent aliases, same migration policy as every
other regrouped member in this doc.

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

## Help-surface rework (T-1571, IMPLEMENTED)

Acceptance[0] on T-1238 wants the top-level `frob --help` output itself
to present the small set of verb groups first, with the still-supported
flat top-level commands demoted to a "also available directly" style
listing rather than intermixed alphabetically. Implemented as a custom
`argparse.HelpFormatter` subclass (`_GroupedHelpFormatter`, `frob.
__main__`): argparse's own subparsers action does not natively support
named groups, so this overrides `_format_action` to intercept only the
root parser's `_SubParsersAction` and render its choice pseudo-actions in
two labeled sections (`_VERB_GROUP_NAMES` first, everything else after)
instead of one flat block. Only the ROOT parser is built with this
formatter -- `add_parser()`-created nested subparsers (`frob quality
--help`, ...) do not inherit `formatter_class`, so every subgroup's own
`--help` stays the ordinary flat argparse listing, correctly scoped to
just the top-level surface this acceptance criterion is actually about.
`_VERB_GROUP_NAMES` is `explore`/`quality`/`design`/`ops` (T-1238/T-1567/
T-1568/T-1569) plus the pre-existing "already atomic" verb groups this
doc names elsewhere (`ticket`/`vet`/`serve`).

T-1697 added `frob verify` as an ordinary flat top-level command (not a
new verb group) -- it renders in the "also available directly" section
alongside every other still-supported flat command, no
`_GroupedHelpFormatter`/`_VERB_GROUP_NAMES` change needed.

## Generation rule -- groups are DERIVED, never hand-mirrored (T-4520)

OWNER DECISION 2026-09-16: the four verb groups (`explore`/`quality`/
`design`/`ops`) stay -- they are the approachable surface this whole
doc exists to design -- but a group's subcommand list must never again
be a second, hand-typed enumeration of its flat twin's subcommands.
Measured 2026-09-16 (full CLI surface audit): flat `sys` had 9 subverbs,
`design sys` mirrored 4 of them -- `_add_design_parser` (`_design.py`)
wired only two of the seven `_add_sys_*_parser` helpers `_add_sys_parser`
(the flat builder, `_misc.py`) itself calls, because nothing forced the
two lists to move together. 30 group leaves were separate
`ArgumentParser` objects from their flat twins repo-wide; 19 had zero
references anywhere (dead surface presented as implemented).

Rejected: deleting the groups (option a) -- the July 2026 directive this
doc opens with is still live, and the groups are the more approachable
surface for a new user/agent even though the flat forms carry the
overwhelming majority of real usage (measured: `sys audit` 266 doc / 28
commit references vs `design sys audit` 0/0; `natives build` 121/4 vs
`ops natives build` 0/0).

Chosen: option b, generate every group leaf from the flat verb's own
definition, by one of two mechanisms depending on how the flat verb
itself is built (T-4520 applied both, across `_design.py`/`_ops.py`/
`_explore.py`):

1. **Call the same `_populate_*`/`_add_*_sub_parser` helper(s) the flat
   builder calls, in the same order** -- the right mechanism whenever the
   flat verb is itself composed from already-factored helper functions
   (e.g. `_add_sys_parser`'s seven `_add_sys_*_parser` calls, `_misc.py`).
   `design sys` (T-4520) now calls all seven, matching `_add_sys_parser`
   call-for-call; `tests/unit/test_cli_group_parity.py` is the guard that
   turns a future missed helper back into a caught regression instead of
   a silent one. This does not make ADDING an eighth helper to the flat
   side fully automatic (the group module still needs its own matching
   call added, since the helper list itself is out of a generic
   registry's reach without owning the flat builder's file too) -- but it
   collapses the divergence to one line per helper instead of a
   full flag-by-flag re-declaration, and the parity test makes a missed
   line loud rather than silent.
2. **Reuse the flat twin's already-built `ArgumentParser` object outright**
   -- the mechanism for a flat verb whose flags are declared inline
   (`map`/`outline`/`xref`, `_core.py`'s `_add_map_parser`/
   `_add_outline_parser`/`_add_xref_parser`, which have no `_populate_*`
   split to call a second time) and for the two verbs that used to be
   group-only (`ops process reap`, `explore docs-search` -- both now have
   flat twins, `_add_process_parser` in `_ops.py` and
   `_add_docs_search_parser` in `_explore.py`, making the mapping total).
   `_explore._mirror_subparser` writes the flat parser instance directly
   into the group's own `_SubParsersAction.choices`/`_choices_actions`
   bookkeeping, so the group leaf IS the flat parser -- option strings,
   help text, and dispatch dest by construction, with zero risk of
   divergence ever, at the cost of `_root._build_parser` having to
   register every flat leaf a group mirrors BEFORE building that group
   (see `_root._add_analysis_subparsers`'s ordering comment).

`frob design docs` stays the one deliberate, documented exception to
"identical to the flat twin": it omits `--search` on purpose (stays
exclusive to `frob explore docs-search`, matching this doc's own bucket
split above) -- `_populate_docs_args(docs_p, include_search=False)`
(`_core.py`, out of T-4520's scope to restructure) rather than either
generation mechanism, and
`TestDesignGroupParity.test_docs_deliberately_omits_search` asserts the
subset relationship explicitly instead of silently excluding `docs` from
the parity sweep.

`frob --help`'s top-level listing (the `_GroupedHelpFormatter` section
above) is unchanged by T-4520 -- the generation rule is about how each
group's SUBCOMMANDS are built, not the root `--help` grouping itself.

## Ticket breakdown

- T-1238 (this epic) -- design doc (this file) + `frob explore` group,
  DONE.
- Follow-on tickets filed for the remaining groups (`quality`, `design`,
  `ops`, the `tickets`/`ticket` naming question) and for the help-surface
  rework: see the epic's Done report for the exact ids filed alongside
  this doc.
- T-4520 -- generation rule above: `design sys`'s missing subverbs, flat
  twins for `ops process reap`/`explore docs-search`, and
  `tests/unit/test_cli_group_parity.py` as the standing regression guard.
