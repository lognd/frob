# CLI hygiene principles (T-1556, T-1271 split)

T-1271's dispatch delivered criterion 0 (an enum-valued flag's error lists
every valid value inline) with bound evidence. This doc is the remainder:
four more criteria, filed as T-1556 so T-1271 could land its own delivered
portion honestly. This is not abstract taste -- every principle below is
backed by a real papercut this fleet actually hit, on this actual repo, in
this actual session, with a real operator or agent paying the cost.

## Principle 1: a destructive verb must not be reachable by simply
## dropping an argument

`frob ticket renumber <old> <new>` rewrites ONE ticket's id everywhere.
`frob ticket renumber` with BOTH positional arguments omitted does
something completely different and far more consequential: it reassigns
EVERY ticket id in the ledger to a contiguous `T-0001..` sequence
(`_add_ticket_renumber_parser`, `src/frob/_cli_parsers/_ticket/
_progress.py`; `_renumber`, `src/frob/app/ticket_runner/_query.py`). Both
positionals are `nargs="?"` -- there is no syntactic difference between
"I deliberately want the whole-ledger renumber" and "I meant to type two
ids and something went wrong" (a truncated paste, a forgotten second
argument, a shell history mis-recall). The safe middle case -- exactly ONE
positional given -- IS caught (`_renumber_one` refuses with "requires both
<old> and <new>, or neither"), which is exactly why the fully-dropped case
reads as more dangerous, not less: the command's own error message on the
partial-drop path proves the author already knew a bare invocation is
easy to reach by accident, and built a safety net for the one-argument
slip -- but not for the zero-argument one, which is the SAME slip
compounded, and the one with no undo.

**The principle**: if a verb has both a narrow, safe, opt-in form and a
broad, destructive, default form, and both are reachable by the SAME
subcommand name with only an argument-count difference, the destructive
form needs an explicit confirmation gate (a required flag, an interactive
prompt, or at minimum a loud "you are about to renumber N tickets, rerun
with --yes to confirm" message -- never a silent go-ahead on zero args).
A verb that already refuses a PARTIAL accidental invocation but not a
COMPLETE one has an inconsistent safety story, not a deliberately
two-tier one.

## Principle 2: two verbs that mutate the same class of ticket state must
## agree on whether a reason is required

`frob ticket scope <id> --add/--remove GLOB --reason TEXT` REQUIRES
`--reason` (`_add_ticket_scope_parser`, `src/frob/_cli_parsers/_ticket/
_metadata.py`) -- the T-0455 audited-mutation precedent: every scope
change is recorded with WHY, because a scope shrink or expansion changes
what a ticket is accountable for. `frob ticket priority <id> <level>` and
`frob ticket kind <id> <kind>` (`_add_ticket_priority_parser`/
`_add_ticket_kind_parser`, same file) mutate different but comparably
consequential ticket metadata -- priority reordering changes what `frob
ticket doable` surfaces first; kind reclassification (T-1616's own
incident, `docs/modules/gates.md`'s BUG002 section) can quietly relax an
evidence obligation a bug-kind ticket already earned -- and neither takes
a `--reason` flag AT ALL. There is no way to record why a priority was
bumped to `critical` or a kind was changed from `bug` to `feature` through
the CLI itself; only `git blame` on `tickets.md` recovers that context,
and only if the operator remembers to write a good commit message.

**The principle**: when two verbs in the same family (here: `ticket
<mutate-metadata>`) carry comparable audit weight, they should carry the
same `--reason` contract -- both required, or both optional with an
equally strong nudge, not an inconsistent mix a caller has to
individually memorize per verb. `frob ticket kind`'s own `kind_history`
mechanism (recorded automatically once a ticket already carries bound
evidence, per T-1616) is exactly the kind of asymmetry that shows the gap
was already noticed for a downstream EFFECT of missing reasons, without
the CLI surface itself closing the gap at the point of mutation.

## Principle 3: a fast nonzero exit must never look like a slow success

A command that exits nonzero in under a second, with output that scrolls
past in a terminal or gets summarized by an agent skimming a long log, is
easy to misread as "ran fine, nothing to report" rather than "refused
before doing any work" -- the exact shape `frob check --ticket T-XXXX`
takes when the ticket has no recorded lease for the current worktree: a
few hundred milliseconds, one `ERROR:` line, exit 1. This fleet hit this
directly this session (`ticket evidence` -- wrong `--ticket`, a stale
worktree lease -- looked identical in a skimmed log to a real, clean,
fast pass until the exit code was read explicitly).

This is not a hypothetical the doc invents a gate for -- it is already a
shipped mitigation elsewhere in this same repo: `frob.app.telemetry`'s
`FAST_EXIT1` rule (`_FAST_EXIT_MS` threshold, `src/frob/app/
telemetry.py`) flags exactly this shape after the fact, in telemetry, with
the message "it did NOT do the work you may think it did -- a fast
failure is not a fast success." That message is the right instinct
applied too late in the pipeline to prevent the misread in the moment --
it is a POST-HOC detector, not a thing the CLI itself surfaces at refusal
time.

**The principle**: a command that refuses before doing its real work
should say so in a way that cannot be mistaken for a quiet, uneventful
success -- loud enough that skimming past it still registers "this
stopped early", not just "this is done." `FAST_EXIT1`'s own framing
("a fast failure is not a fast success") is the right slogan for every
new refusal path this repo adds; a new command whose failure mode is a
sub-second silent-looking exit should either raise its own loud banner at
refusal time or explicitly ride on `FAST_EXIT1`'s existing detection
rather than reinventing a quieter one.

## Checklist (verified by `tests/unit/test_cli_hygiene_checklist_t1556.py`)

- [ ] A destructive/broad-blast-radius form of a verb reachable by
  omitting arguments from its narrow/safe form is confirmed loudly, not
  silently defaulted into.
- [ ] Two verbs mutating comparable ticket-metadata classes carry the
  same `--reason` requirement (both required or both equally nudged).
- [ ] Every flag's help string states its default when the default is
  not the type's own zero-value (`None`/`False`/`[]`) -- a caller reading
  `--help` should never have to read source to know what omitting a flag
  does.
- [ ] No flag silently changes what a SIBLING flag means (the shape
  `renumber`'s own arg-count-dependent behavior takes) without both
  flags' own `help=` text cross-referencing that fact.

This checklist is a starting corpus, not a closed one -- the automated
half (`test_cli_hygiene_checklist_t1556.py`) locks the renumber
positional-contract case concretely (its own `--help` text names the
whole-ledger fallback); extending it to a repo-wide `frob check` gate
rule that walks every registered subparser is real, valuable follow-up
work this ticket's own declared scope (`src/frob/app/ticket_runner/
_new.py`, `_mutate.py`, `_close_cmd.py`, `src/frob/gates/_waive_lease.py`)
could not reach -- a repo-wide linter needs `src/frob/gates/__init__.py`/
`_waive.py` registration for a new rule id, both outside this ticket; see
this ticket's Done report for the filed follow-up.
