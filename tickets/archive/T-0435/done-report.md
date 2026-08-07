## Done report

DOC005 binds README.md's command table to the LIVE argparse subcommand
registry, reusing DOC004's existing `[[docblocks.commands]]`-configured
parser-walk machinery (`_console_command_sources` / `_load_parser_factory`
/ `_subparser_tree`, now shared via a new `_console_trees` helper) instead
of a second, parallel registry-reading mechanism.

Two checks, both new rule DOC005, ERROR severity, wired into the existing
"docblocks" gate name alongside DOC004:

1. A README.md table row `| \`<prog> <name>\` | ... |` naming a
   subcommand that no longer exists in the live tree -- STALE.
2. A real top-level subcommand with no table row anywhere in README.md --
   MISSING.
3. A "N commands"/"N total commands" prose count claim whose N does not
   equal the live top-level command count -- COUNT MISMATCH.

Real drift caught and fixed in this repo's own README.md: the live
top-level subcommand registry (frob.__main__._build_parser) has 30
subcommands; README's table was missing 5 of them (`clean`, `debt`,
`doctor`, `pool`, `registry`) before this change. Added the 5 missing
rows and a "30 total commands" checkable count claim under the Commands
heading, cross-linked to the new gate's docs section.

Mechanism documented in docs/modules/gates.md (rule table row + a new
"### DOC005 README command-table drift-lock T-0435" section mirroring
the DOC004 section's format).

REL001 required a version bump (0.76.0 -> 0.77.0) for the new public
`doc005_gate` symbol; pyproject.toml/CHANGELOG.md/.frob-release.json/
uv.lock added to ticket scope for that mechanical follow-through.

### Changed
```
 .frob-release.json           |   1 +
 CHANGELOG.md                 |   1 +
 README.md                    |  10 +++
 docs/modules/gates.md        |  41 +++++++++
 src/frob/gates/__init__.py   |  13 ++-
 src/frob/gates/_docblocks.py | 199 ++++++++++++++++++++++++++++++++++++++++---
 tests/test_docblocks_gate.py | 149 +++++++++++++++++++++++++++++++-
 tickets.md                   | 112 +++++++++++++++++++++++-
 8 files changed, 509 insertions(+), 17 deletions(-)
```

### Evidence
- `tests/test_docblocks_gate.py::TestDoc005ReadmeTableDrift::test_missing_row_for_real_command_fails` (pytest node id, verified passing when recorded)
- `tests/test_docblocks_gate.py::TestDoc005ReadmeTableDrift::test_stale_row_for_removed_command_fails` (pytest node id, verified passing when recorded)
- `tests/test_docblocks_gate.py::TestDoc005ReadmeTableDrift::test_fully_covered_table_passes` (pytest node id, verified passing when recorded)
- `tests/test_docblocks_gate.py::TestDoc005ReadmeTableDrift::test_count_claim_mismatch_fails` (pytest node id, verified passing when recorded)
- `tests/test_docblocks_gate.py::TestDoc005ReadmeTableDrift::test_count_claim_matching_passes` (pytest node id, verified passing when recorded)
- `tests/test_docblocks_gate.py::TestDoc005ReadmeTableDrift::test_no_config_means_no_readme_checking` (pytest node id, verified passing when recorded)
