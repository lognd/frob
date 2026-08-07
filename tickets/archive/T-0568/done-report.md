## Done report

Added `frob ticket brief <id>` (frob.tickets.brief_ticket, delegating to
new frob/tickets/_brief.py) which composes the whole per-ticket dispatch
briefing a coordinator otherwise hand-types: body+acceptance, declared
scope plus any active lease collision (leased_by), the agent playbook's
own hard-rule sections, inferred verify commands, a gate-baseline
summary, and the REL/land rules with the live pyproject.toml version
filled in.

The playbook section is genuinely data-driven, per the ticket's explicit
requirement: parse_playbook_sections regex-parses every numbered
`## N[letter]. Title` heading out of docs/guides/agent-playbook.md at
brief time and renders each verbatim -- nothing is hand-copied, so a
future renumber/add/remove in the playbook is picked up automatically
with no matching change needed here. A repo missing the playbook file
gets an empty section rather than a hard failure.

infer_verify_commands is a real heuristic, not a static string: if the
ticket's scope already names a tests/ path it is used directly; otherwise
root/tests is walked (rglob) for a test file whose stem contains a scope
entry's own stem. gate_baseline_summary and current_version degrade
gracefully (missing .frob/baseline or pyproject.toml) rather than
erroring, since a briefing with one section blank is still useful.

Wired frob ticket brief into __main__.py's ticket subparser and
ticket_runner.py's dispatch table/usage strings; docs/modules/tickets.md
gained a "frob ticket brief (T-0568)" section plus the CLI-list and
public-API entries.

### Changed
```
 CHANGELOG.md                    |  12 +++
 docs/commands/cli-vocabulary.md |  65 +++++++++++
 docs/modules/tickets.md         |  80 +++++++++++++-
 pyproject.toml                  |   2 +-
 src/frob/__main__.py            | 152 +++++++++++++++++++++++++-
 src/frob/app/config.py          |   4 +
 src/frob/app/ticket_runner.py   |  58 ++++++++--
 src/frob/tickets/__init__.py    |  78 ++++++++++++++
 src/frob/tickets/_brief.py      | 233 ++++++++++++++++++++++++++++++++++++++++
 src/frob/tickets/_models.py     |   4 +
 tests/test_tickets.py           |  98 +++++++++++++++++
 tests/test_tickets_brief.py     | 226 ++++++++++++++++++++++++++++++++++++++
 tests/unit/test_main_entry.py   |  62 ++++++++++-
 tickets.md                      | 144 +++++++++++++++++++++++--
 14 files changed, 1194 insertions(+), 24 deletions(-)
```

### Evidence
- `tests/test_tickets_brief.py::TestParsePlaybookSections::test_parses_numbered_headings_only` (pytest node id, verified passing when recorded)
- `tests/test_tickets_brief.py::TestParsePlaybookSections::test_body_stops_at_next_heading_numbered_or_not` (pytest node id, verified passing when recorded)
- `tests/test_tickets_brief.py::TestParsePlaybookSections::test_empty_text_yields_no_sections` (pytest node id, verified passing when recorded)
- `tests/test_tickets_brief.py::TestLoadPlaybookSections::test_missing_file_returns_empty` (pytest node id, verified passing when recorded)
- `tests/test_tickets_brief.py::TestLoadPlaybookSections::test_reads_real_file` (pytest node id, verified passing when recorded)
- `tests/test_tickets_brief.py::TestInferVerifyCommands::test_scope_naming_tests_dir_is_used_directly` (pytest node id, verified passing when recorded)
- `tests/test_tickets_brief.py::TestInferVerifyCommands::test_matches_test_file_by_stem` (pytest node id, verified passing when recorded)
- `tests/test_tickets_brief.py::TestInferVerifyCommands::test_no_scope_yields_only_check_command` (pytest node id, verified passing when recorded)
- `tests/test_tickets_brief.py::TestGateBaselineSummary::test_missing_baseline` (pytest node id, verified passing when recorded)
- `tests/test_tickets_brief.py::TestGateBaselineSummary::test_present_baseline` (pytest node id, verified passing when recorded)
- `tests/test_tickets_brief.py::TestCurrentVersion::test_missing_pyproject_is_none` (pytest node id, verified passing when recorded)
- `tests/test_tickets_brief.py::TestCurrentVersion::test_reads_project_version` (pytest node id, verified passing when recorded)
- `tests/test_tickets_brief.py::TestBriefTicket::test_composes_full_briefing` (pytest node id, verified passing when recorded)
- `tests/test_tickets_brief.py::TestBriefTicket::test_unknown_ticket_not_found` (pytest node id, verified passing when recorded)
- `tests/test_tickets_brief.py::TestBriefCli::test_cli_prints_briefing` (pytest node id, verified passing when recorded)
- `tests/test_tickets_brief.py::TestBriefCli::test_cli_requires_id` (pytest node id, verified passing when recorded)
