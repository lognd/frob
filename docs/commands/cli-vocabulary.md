# CLI vocabulary + did-you-mean (T-0578)

Two cross-cutting CLI conveniences, not tied to one subcommand: a
"did you mean" suggestion on an unknown subcommand/flag, and a small set
of back-compat flag aliases for observed misuses.

## Did-you-mean

<!-- frob:describes src/frob/__main__.py::_SuggestingArgumentParser -->
<!-- frob:describes src/frob/__main__.py::_did_you_mean -->
<!-- frob:waive DOC004 reason="deliberate typo illustrating the did-you-mean suggestion itself, not a real subcommand reference" -->
```bash
frob tikcet list
# frob: error: argument subcommand: invalid choice: 'tikcet' (choose from
# 'scaffold', 'cycle', ..., 'ticket', ...) (did you mean: ticket?)

frob ticket list --statuz queued
# frob: error: unrecognized arguments: --statuz queued (did you mean: --status?)
```

Every parser and subparser built by `frob.__main__._build_parser` is a
`_SuggestingArgumentParser`; `argparse.add_subparsers` defaults
`parser_class` to `type(self)`, so the root parser being this class is
enough to propagate it to every nested subcommand level with no per-parser
wiring. Two argparse error shapes get a suggestion appended:

- **Invalid subcommand/choice**: candidates come straight out of
  argparse's own error message text (it already lists every valid choice).
- **Unrecognized flag**: candidates are every `--flag` string registered
  anywhere in the whole CLI (`_collect_option_strings`, walked once after
  `_build_parser` assembles the full subcommand tree) -- deliberately
  global rather than per-subcommand, since one flag name per concept
  across subcommands is this same ticket's other half (below), so a
  cross-subcommand suggestion is the intended behavior, not noise.

`difflib.get_close_matches` (cutoff 0.6, top-1) decides whether a
candidate is close enough to suggest at all; a wildly different token
(`--zzzzzzzzzzz`) gets no suggestion rather than a useless one.

## Vocabulary normalization + back-compat aliases

Two observed misuses (real dispatch sessions, not hypothetical) named in
T-0579's origin ticket:

- `frob ticket list --status` -- the canonical name is `--state` (matches
  the `ticket_state` field and the ledger's own `state:` key everywhere
  else). `--status` is now accepted as a deprecated alias on the same
  argparse action (`add_argument("--state", "--status", dest=
  "ticket_state", ...)`), so the guess works instead of erroring.
- `frob ticket done-report --body` -- the canonical name is `--why` (the
  Done-report narrative). `frob ticket new --body` is a DIFFERENT concept
  (the ticket's initial description) that keeps its own name -- this is
  exactly the cross-subcommand naming drift the ticket exists to close,
  not a case to unify further. `--body` is now accepted as a deprecated
  alias for `--why` on `done-report` only.

Both aliases share one dest with their canonical flag (last flag wins if
both are passed on the same invocation, an edge case not worth rejecting)
and are documented as deprecated in `--help` rather than hidden, so
`frob ticket done-report --help` names the canonical flag to migrate to.

## See also

- `docs/modules/tickets.md` -- `frob ticket drop` (T-0579), the ticket
  state machine, and the full CLI surface these aliases sit inside.
