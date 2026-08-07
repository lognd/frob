## Done report

Root cause: an unknown subcommand or a mistyped flag (frob ticket list
--status, done-report --body) produced argparse's bare "invalid choice"/
"unrecognized arguments" error with no hint at the correct name, and the
CLI had genuine cross-subcommand naming drift for the same concept
(--state vs --status, --why vs --body).

Added `_SuggestingArgumentParser` (frob/__main__.py), an ArgumentParser
subclass overriding `error()` to append a "did you mean: X?" suggestion
(difflib.get_close_matches, cutoff 0.6) for two argparse error shapes: an
invalid subcommand/choice (candidates parsed straight out of argparse's
own message) and an unrecognized flag (candidates are every --flag
registered anywhere in the CLI, collected once via `_collect_option_strings`
after `_build_parser` assembles the full tree). The root parser is built as
this class; argparse's `add_subparsers` defaults `parser_class` to
`type(self)`, so every nested subparser inherits the behavior for free --
verified manually against `frob tikcet list`, `frob ticket lst`, and
`frob ticket list --statuz`.

Normalized vocabulary for the two observed misuses: `ticket list --status`
is now a deprecated back-compat alias for the canonical `--state`, and
`ticket done-report --body` is a deprecated alias for the canonical
`--why` (kept distinct from `ticket new --body`, a different concept --
the ticket's initial description, not the Done-report narrative). Both
are documented as deprecated in --help rather than hidden.

docs/commands/cli-vocabulary.md documents both halves with frob:describes
anchors. No public API surface changed (all new symbols are private), so
no REL001 bump was needed for this ticket.

### Changed
```
 CHANGELOG.md                    |  12 ++++
 docs/commands/cli-vocabulary.md |  64 ++++++++++++++++++
 docs/modules/tickets.md         |  27 +++++++-
 pyproject.toml                  |   2 +-
 src/frob/__main__.py            | 142 ++++++++++++++++++++++++++++++++++++++--
 src/frob/app/config.py          |   4 ++
 src/frob/app/ticket_runner.py   |  31 ++++++++-
 src/frob/tickets/__init__.py    |  53 +++++++++++++++
 src/frob/tickets/_models.py     |   4 ++
 tests/test_tickets.py           |  98 +++++++++++++++++++++++++++
 tests/unit/test_main_entry.py   |  62 +++++++++++++++++-
 tickets.md                      |  67 +++++++++++++++++--
 12 files changed, 549 insertions(+), 17 deletions(-)
```

### Evidence
- `tests/unit/test_main_entry.py::TestDidYouMean::test_unknown_subcommand_suggests_closest` (pytest node id, verified passing when recorded)
- `tests/unit/test_main_entry.py::TestDidYouMean::test_unknown_ticket_subcommand_suggests_closest` (pytest node id, verified passing when recorded)
- `tests/unit/test_main_entry.py::TestDidYouMean::test_unrecognized_flag_suggests_closest_known_flag` (pytest node id, verified passing when recorded)
- `tests/unit/test_main_entry.py::TestDidYouMean::test_far_off_flag_gets_no_suggestion` (pytest node id, verified passing when recorded)
- `tests/unit/test_main_entry.py::TestVocabularyAliases::test_ticket_list_status_alias_sets_state_dest` (pytest node id, verified passing when recorded)
- `tests/unit/test_main_entry.py::TestVocabularyAliases::test_ticket_done_report_body_alias_sets_why_dest` (pytest node id, verified passing when recorded)
